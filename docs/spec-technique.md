# Spec technique

## Fichiers principaux

- `gitlab-ci.yml` contient le template GitLab CI.
- `scripts/deploy.py` met à jour les tags d'image dans le dépôt manifests.
- `scripts/rollback.py` revert un commit sur la branche `main` du dépôt
  manifests.
- `scripts/gitlab-release-env.js` résout `GITLAB_URL` et récupère le
  certificat auto-signé de GitLab pour le job `semantic-release`.
- `.gitlab-ci-local.yml` facilite l'exécution locale des jobs.

## Jobs

Le template définit les stages `build`, `deploy` et `promote`.

- `semantic-release` utilise Node 20 et les plugins semantic-release. Il
  clone `ci-templates` (comme les jobs `deploy`) pour exécuter
  `scripts/gitlab-release-env.js`, qui détermine `GITLAB_URL` (depuis
  `.releaserc.json` ou `INTERNAL_GITLAB_HOST`) et ajoute le certificat
  auto-signé de l'endpoint HTTPS au trust store si nécessaire, via le
  module `tls` natif de Node (pas de dépendance à `openssl`).
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

Le template dépend de GitLab, de GHCR (`ghcr.io/k8s-gitops-lab`, pas de
registry interne au cluster) et du dépôt manifests. Il ne doit pas connaître
la topologie Kubernetes autrement que par les variables fournies par
l'application et par les environnements GitLab déclarés.
