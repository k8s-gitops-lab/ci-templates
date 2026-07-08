# Spec technique

## Fichiers principaux

- `templates/build-docker/template.yml` enrobe le composant
  [to-be-continuous/docker](https://gitlab.com/to-be-continuous/docker)
  (`docker-buildah-build`, `docker-publish`).
- `templates/deploy-gitops/template.yml` contient le composant de déploiement
  GitOps (`deploy-dev`, `deploy-rec`, `deploy-preprod`, `deploy-prod`).
- `templates/promote/template.yml` enrobe le composant
  [to-be-continuous/semantic-release](https://gitlab.com/to-be-continuous/semantic-release)
  (`semantic-release`) et contient `rollback-prod` (propre à ce POC).
- `scripts/deploy.py` met à jour les tags d'image dans le dépôt manifests.
- `scripts/rollback.py` revert un commit sur la branche `main` du dépôt
  manifests.
- `.gitlab-ci-local.yml` facilite l'exécution locale des jobs.

## Composants et jobs

`deploy-gitops` ne déclare pas `stages:` (comme avant). `build-docker` et
`promote` héritent chacun d'un `stages:` complet de to-be-continuous — la
pipeline applicative top-level doit déclarer la liste complète et cohérente
(voir `README.md`), pas seulement `build`/`deploy`/`promote`.

Chaque composant déclare son contrat en `spec:inputs`, puis mappe ces inputs
vers les variables attendues par les jobs et les scripts (`APP_NAME`,
`SERVICE_NAME`, `MANIFESTS_PROJECT_PATH`, `MANIFESTS_PATH`, `HAS_PREPROD`).
`build-docker` ne porte plus de contrat `services` par app : pour un
monorepo multi-service, l'app ajoute directement un `parallel: matrix:` sur
les jobs `docker-buildah-build`/`docker-publish` (GitLab ne permet pas de
faire varier dynamiquement le nombre d'`include:component` à partir d'une
simple liste en input).

- `semantic-release` (to-be-continuous) lit directement le `.releaserc.json`
  de l'app. Chaque app pointe déjà son plugin `@semantic-release/gitlab` sur
  l'endpoint interne HTTP `INTERNAL_GITLAB_HOST` (voir `.releaserc.json` de
  `helloworld`) : pas de certificat auto-signé à faire confiance pour l'appel
  à l'API GitLab. `GITLAB_TOKEN` reste fourni par le composant `promote` via
  `GITLAB_PUSH_TOKEN`.
- `docker-buildah-build` construit l'image avec Buildah (builder par défaut
  de to-be-continuous — Kaniko, abandonné par Google depuis janvier 2025,
  reste disponible via l'input `build-tool`) et pousse l'image "snapshot"
  (`DOCKER_SNAPSHOT_IMAGE`, taguée par défaut avec le SHA court du commit).
- `docker-publish` ne reconstruit rien : il copie (Skopeo) l'image snapshot
  vers l'image "release" (`DOCKER_RELEASE_IMAGE`, tag `vX.Y.Z`) sur tag
  sémantique — même pattern build-once/promote que l'ancien `crane copy`,
  maintenu en amont.
- `deploy-dev`, `deploy-rec`, `deploy-preprod` et `deploy-prod` exécutent
  `scripts/deploy.py`.
- `rollback-prod` exécute `scripts/rollback.py`.

Confiance TLS : les composants to-be-continuous lisent automatiquement la
variable de plateforme `CUSTOM_CA_CERTS` (PEM en clair, pas de
`before_script` à écrire) pour faire confiance au proxy sortant du lab — voir
`AGENTS.md`.

## Scripts Python

`deploy.py` :

- mappe les environnements vers les branches manifests ;
- parse `SERVICES` ;
- clone le dépôt manifests avec `GITLAB_PUSH_TOKEN` ;
- modifie `kustomization.yaml` via PyYAML ;
- committe et pousse avec `[skip ci]`.

`rollback.py` :

- clone la branche `main` du dépôt manifests ;
- exécute `git revert --no-edit` sur `REVERT_SHA` ;
- pousse le revert.

## Contraintes

Les composants dépendent de GitLab, du registre configuré par `registry_host`
(`ghcr.io` par défaut) et du dépôt manifests. Ils ne doivent pas connaître la
topologie Kubernetes autrement que par les inputs fournis par l'application et
par les environnements GitLab déclarés.
