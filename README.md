# ci-templates

Composants CI/CD GitLab partagés du POC.

Le projet GitLab interne `shared-ci/ci-templates` est cree par le Terraform de `gitlab-projects-iac` (import depuis GitHub). Chaque composant sous `templates/` est inclus par les applications avec une reference versionnee (tag `vX.Y.Z`).

Contrat principal : build once, promote everywhere via les branches GitOps `dev`, `rec`, `preprod` et `main` du repo manifests applicatif.

## Composants

| Composant | Stage(s) | Rôle |
|---|---|---|
| `templates/build-docker` | `build`, `package-build`, `package-test`, `publish` | Enrobe [to-be-continuous/docker](https://gitlab.com/to-be-continuous/docker) : build (Buildah par défaut) + retag release sans rebuild (`docker-publish`, via Skopeo). |
| `templates/deploy-gitops` | `deploy` | Met à jour le dépôt manifests (`deploy-dev/rec/preprod/prod`), un job par environnement. |
| `templates/promote` | `promote` | Enrobe [to-be-continuous/semantic-release](https://gitlab.com/to-be-continuous/semantic-release) (tag `vX.Y.Z` automatique) et `rollback-prod` (revert GitOps manuel). |

Chaque composant déclare ses inputs typés (`spec:inputs`, avec description,
default et validation `regex`/`type` quand pertinent) — voir le détail dans
chaque `template.yml`.

Prérequis plateforme : la variable CI/CD `CUSTOM_CA_CERTS` (PEM en clair, CA
du proxy sortant + CA interne auto-signée) doit être provisionnée (voir
`AGENTS.md`) — sans elle, les jobs `build-docker` et `semantic-release`
échouent en TLS sur les registres/hosts externes.

## Utilisation par une application

Une app consommatrice inclut les 3 composants et déclare elle-même les
stages (les composants ne déclarent pas tous `stages:` de la même façon —
`build-docker` et `promote` en héritent de to-be-continuous — c'est donc à
la pipeline top-level de déclarer la liste complète et cohérente) :

```yaml
stages:
  - build          # docker-hadolint
  - package-build  # docker-buildah-build
  - package-test   # docker-trivy, docker-sbom
  - publish        # docker-publish (sur tag, avant les deploys qui en dépendent)
  - deploy         # deploy-dev/rec/preprod/prod
  - promote        # semantic-release (après deploy-dev), rollback-prod

include:
  - component: $CI_SERVER_FQDN/shared-ci/ci-templates/build-docker@v3.0.6
    inputs:
      dockerfile: helloworld-svc/Dockerfile
      context_path: helloworld-svc
      snapshot_image: ghcr.io/k8s-gitops-lab/helloworld-svc/snapshot:$CI_COMMIT_SHORT_SHA
      release_image: ghcr.io/k8s-gitops-lab/helloworld-svc
  - component: $CI_SERVER_FQDN/shared-ci/ci-templates/deploy-gitops@v3.0.6
    inputs:
      app_name: helloworld
      service_name: helloworld-gui
      manifests_project_path: hello-groupe/helloworld-iac
      has_preprod: true
      services: "helloworld-svc=ghcr.io/k8s-gitops-lab/helloworld-svc helloworld-gui=ghcr.io/k8s-gitops-lab/helloworld-gui"
  - component: $CI_SERVER_FQDN/shared-ci/ci-templates/promote@v3.0.6
    inputs:
      manifests_project_path: hello-groupe/helloworld-iac

# Monorepo multi-service (ex: helloworld-svc + helloworld-gui) : le composant
# build-docker ne construit qu'une image par inclusion (limite GitLab :
# include:component ne peut pas itérer dynamiquement sur une liste). Le
# fan-out se fait ici, dans l'app, via parallel:matrix sur les jobs déjà
# fournis par build-docker (redéclarer un job avec le même nom fusionne ses
# clés avec la définition incluse, ça ne l'écrase pas — contrairement à
# stages: ci-dessus) :
docker-buildah-build:
  parallel:
    matrix:
      - DOCKER_CONTEXT_PATH: helloworld-svc
        DOCKER_FILE: helloworld-svc/Dockerfile
        DOCKER_SNAPSHOT_IMAGE: ghcr.io/k8s-gitops-lab/helloworld-svc/snapshot:$CI_COMMIT_SHORT_SHA
        DOCKER_RELEASE_IMAGE: ghcr.io/k8s-gitops-lab/helloworld-svc
      - DOCKER_CONTEXT_PATH: helloworld-gui
        DOCKER_FILE: helloworld-gui/Dockerfile
        DOCKER_SNAPSHOT_IMAGE: ghcr.io/k8s-gitops-lab/helloworld-gui/snapshot:$CI_COMMIT_SHORT_SHA
        DOCKER_RELEASE_IMAGE: ghcr.io/k8s-gitops-lab/helloworld-gui
docker-publish:
  parallel:
    matrix:
      - DOCKER_SNAPSHOT_IMAGE: ghcr.io/k8s-gitops-lab/helloworld-svc/snapshot:$CI_COMMIT_SHORT_SHA
        DOCKER_RELEASE_IMAGE: ghcr.io/k8s-gitops-lab/helloworld-svc
      - DOCKER_SNAPSHOT_IMAGE: ghcr.io/k8s-gitops-lab/helloworld-gui/snapshot:$CI_COMMIT_SHORT_SHA
        DOCKER_RELEASE_IMAGE: ghcr.io/k8s-gitops-lab/helloworld-gui
```

Voir `AGENTS.md` pour le détail du contrat (jobs, versioning, exécution locale).
