# Spec technique

## Fichiers principaux

- `gitlab-ci.yml` contient le template GitLab CI.
- `scripts/deploy.py` met à jour les tags d'image dans le dépôt manifests.
- `scripts/rollback.py` revert un commit sur la branche `main` du dépôt
  manifests.
- `.gitlab-ci-local.yml` facilite l'exécution locale des jobs.

## Jobs

Le template définit les stages `prepare`, `build`, `deploy` et `promote`.

- `semantic-release` utilise Node 20 et les plugins semantic-release.
- `build-dev` construit chaque service avec Kaniko et pousse les tags
  `<sha-court>` et `dev`.
- `build-rec` construit chaque service avec Kaniko et pousse le tag `vX.Y.Z`.
- `deploy-dev`, `deploy-rec`, `deploy-preprod` et `deploy-prod` exécutent
  `scripts/deploy.py`.
- `rollback-prod` exécute `scripts/rollback.py`.

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

Le template dépend de GitLab, du registry interne et du dépôt manifests. Il ne
doit pas connaître la topologie Kubernetes autrement que par les variables
fournies par l'application et par les environnements GitLab déclarés.
