# ci-templates

Composants CI/CD GitLab partagés du POC.

Le projet GitLab interne `shared-ci/ci-templates` est cree par le Terraform de `gitlab-projects-iac` (import depuis GitHub). Chaque composant sous `templates/` est inclus par les applications avec une reference versionnee (tag `vX.Y.Z`).

Contrat principal : build once, promote everywhere via les branches GitOps `dev`, `rec`, `preprod` et `main` du repo manifests applicatif.

## Composants

| Composant | Stage(s) | Rôle |
|---|---|---|
| `templates/build-kaniko` | `build` | Build Kaniko (`build-dev`) + retag release sans rebuild (`build-rec`, via `crane`). |
| `templates/deploy-gitops` | `deploy` | Met à jour le dépôt manifests (`deploy-dev/rec/preprod/prod`), un job par environnement. |
| `templates/promote` | `promote` | `semantic-release` (tag `vX.Y.Z` automatique) et `rollback-prod` (revert GitOps manuel). |

Chaque composant déclare ses inputs typés (`spec:inputs`, avec description,
default et validation `regex`/`type` quand pertinent) — voir le détail dans
chaque `template.yml`.

## Utilisation par une application

Une app consommatrice inclut les 3 composants et déclare elle-même les
stages (les composants ne déclarent pas `stages:` : ce mot-clé ne se fusionne
pas entre fichiers inclus, c'est donc à la pipeline top-level de le faire) :

```yaml
stages:
  - build
  - deploy
  - promote

include:
  - component: $CI_SERVER_FQDN/shared-ci/ci-templates/build-kaniko@v2.0.0
    inputs:
      services: "helloworld-svc=ghcr.io/k8s-gitops-lab/helloworld-svc helloworld-gui=ghcr.io/k8s-gitops-lab/helloworld-gui"
  - component: $CI_SERVER_FQDN/shared-ci/ci-templates/deploy-gitops@v2.0.0
    inputs:
      app_name: helloworld
      service_name: helloworld-gui
      manifests_project_path: hello-groupe/helloworld-iac
      has_preprod: true
  - component: $CI_SERVER_FQDN/shared-ci/ci-templates/promote@v2.0.0
    inputs:
      manifests_project_path: hello-groupe/helloworld-iac
```

Voir `AGENTS.md` pour le détail du contrat (jobs, versioning, exécution locale).
