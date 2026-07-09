#!/usr/bin/env python3
"""Met à jour les tags d'image et les hostnames HTTPRoute dans le dépôt de manifests.

Usage: python3 deploy.py <env>    # env = dev | rec | preprod | prod

Variables d'environnement attendues:
  SERVICES                 "svc-a=registry/svc-a svc-b=registry/svc-b"
  CI_COMMIT_SHORT_SHA      tag utilisé pour l'env dev
  CI_COMMIT_TAG            tag utilisé pour rec/preprod/prod (absent sur main si pas de release)
  INTERNAL_GITLAB_HOST     host GitLab in-cluster (pour le clone manifests)
  GITLAB_PUSH_TOKEN        token de push sur le dépôt manifests
  MANIFESTS_PROJECT_PATH   "hello-groupe/helloworld-iac"
  MANIFESTS_PATH           sous-dossier kustomize dans le dépôt manifests (ex: "k8s")
  DOMAIN                   domaine de base pour les HTTPRoutes (ex: 192.168.33.100.nip.io)
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

_ENV_BRANCH = {"dev": "dev", "rec": "rec", "preprod": "preprod", "prod": "main"}


def parse_services(raw: str) -> dict[str, str]:
    """'svc=registry/svc ...' → {svc_name: image_base}"""
    result = {}
    for spec in raw.strip().split():
        svc_name, image_base = spec.split("=", 1)
        result[svc_name] = image_base
    return result


def manifests_url() -> str:
    host = os.environ["INTERNAL_GITLAB_HOST"]
    token = os.environ["GITLAB_PUSH_TOKEN"]
    path = os.environ["MANIFESTS_PROJECT_PATH"]
    return f"http://root:{token}@{host}/{path}.git"


def update_kustomize_images(
    kustomize_dir: Path,
    services: dict[str, str],
    tag: str,
    image_targets: dict[str, str] | None = None,
) -> bool:
    """Met à jour kustomization.yaml avec le nouveau tag. Retourne True si modifié.

    `name` reste le nom d'image tel qu'écrit en dur dans les manifests
    (ex. helloworld-svc-deployment.yaml) : c'est la clé de correspondance
    kustomize, elle ne doit pas changer d'un déploiement à l'autre sous
    peine de ne plus matcher aucune ressource (l'image d'origine, sans tag,
    serait alors laissée telle quelle -> "latest" implicite). Le matching
    se fait sur le nom de service (suffixe après le dernier "/"), pas sur le
    nom d'image complet : si le registre change (ex. migration vers un
    nouvel hôte), l'entrée existante est corrigée en place au lieu d'être
    dupliquée à côté de l'ancienne, qui resterait sinon orpheline.

    `image_targets` (optionnel) redirige un service vers un autre dépôt
    d'image (ex. dev -> image "snapshot") via `newName` — jamais en
    réécrivant `name`, qui casserait le matching ci-dessus.
    """
    def match_key(name: str) -> str:
        # tolere une entree encore taguee vers "<svc>/snapshot" (etat transitoire
        # laisse par une version precedente de ce script) pour l'auto-corriger.
        base = name[: -len("/snapshot")] if name.endswith("/snapshot") else name
        return base.rsplit("/", 1)[-1]

    image_targets = image_targets or {}
    kfile = kustomize_dir / "kustomization.yaml"
    data = yaml.safe_load(kfile.read_text()) or {}
    images: list[dict] = data.setdefault("images", [])
    changed = False

    for svc_name, image_base in services.items():
        target = image_targets.get(svc_name, image_base)
        entry = next(
            (img for img in images if match_key(img.get("name", "")) == svc_name),
            None,
        )
        if entry:
            if entry.get("name") != image_base:
                entry["name"] = image_base
                changed = True
            if target != image_base:
                if entry.get("newName") != target:
                    entry["newName"] = target
                    changed = True
            elif entry.pop("newName", None) is not None:
                changed = True
            if entry.get("newTag") != tag:
                entry["newTag"] = tag
                changed = True
        else:
            new_entry = {"name": image_base}
            if target != image_base:
                new_entry["newName"] = target
            new_entry["newTag"] = tag
            images.append(new_entry)
            changed = True

    if changed:
        kfile.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False))

    return changed


def update_routes(kustomize_dir: Path, svc_names: list[str], env_name: str, domain: str) -> bool:
    """Met à jour les hostnames des HTTPRoutes selon l'environnement. Retourne True si modifié."""
    suffix = "" if env_name == "prod" else f"-{env_name}"
    changed = False

    for svc_name in svc_names:
        route_file = kustomize_dir / f"{svc_name}-route.yaml"
        if not route_file.exists():
            continue

        data = yaml.safe_load(route_file.read_text())
        if not data or data.get("kind") != "HTTPRoute":
            continue

        expected = f"{svc_name}{suffix}.{domain}"
        if data.get("spec", {}).get("hostnames") != [expected]:
            data.setdefault("spec", {})["hostnames"] = [expected]
            route_file.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False))
            changed = True

    return changed


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: deploy.py <env>  (dev|rec|preprod|prod)")

    env_name = sys.argv[1]
    branch = _ENV_BRANCH.get(env_name)
    if branch is None:
        sys.exit(f"Environnement inconnu: {env_name!r}. Valeurs valides: {list(_ENV_BRANCH)}")

    services_raw = os.environ.get("SERVICES", "")
    if not services_raw.strip():
        sys.exit("La variable SERVICES est vide ou absente.")

    services = parse_services(services_raw)
    image_targets: dict[str, str] = {}

    if env_name == "dev":
        tag = os.environ.get("CI_COMMIT_SHORT_SHA") or "local"
        # dev consomme l'image "snapshot" : deploy-dev depend uniquement de
        # docker-buildah-build (pas de docker-publish), donc l'image
        # "release" n'est pas garantie taguee au SHA a ce stade — la
        # referencer ici creerait une course et un tag absent au registre.
        image_targets = {name: f"{base}/snapshot" for name, base in services.items()}
    else:
        tag = os.environ.get("CI_COMMIT_TAG") or sys.exit(f"CI_COMMIT_TAG requis pour l'env {env_name!r}.")

    domain = os.environ.get("DOMAIN", "")
    manifests_path = os.environ.get("MANIFESTS_PATH", "k8s")
    project_path = os.environ.get("MANIFESTS_PROJECT_PATH", "")
    services_label = ", ".join(services.keys())

    with tempfile.TemporaryDirectory(prefix="manifests-") as tmpdir:
        git("clone", "--depth=1", "--branch", branch, manifests_url(), tmpdir)

        kustomize_dir = Path(tmpdir) / manifests_path
        changed = update_kustomize_images(kustomize_dir, services, tag, image_targets)

        if domain:
            changed |= update_routes(kustomize_dir, list(services.keys()), env_name, domain)

        if not changed:
            print(f"Aucun changement sur {env_name} (tag {tag} déjà présent).")
            return

        git("config", "user.email", "ci@gitlab.local", cwd=tmpdir)
        git("config", "user.name", "GitLab CI", cwd=tmpdir)
        git("add", manifests_path, cwd=tmpdir)
        git(
            "commit", "-m",
            f"ci: deploy {services_label} sur {env_name} (tag {tag}) [skip ci]",
            cwd=tmpdir,
        )
        git("push", "origin", branch, cwd=tmpdir)

    print(f"Manifests mis à jour sur '{project_path}@{branch}' avec le tag {tag}.")


if __name__ == "__main__":
    main()
