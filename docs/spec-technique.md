# Spec technique

## Fichiers principaux

- `templates/build-kaniko/template.yml` contient le composant de build
  (`build-dev`, `build-rec`).
- `templates/deploy-gitops/template.yml` contient le composant de déploiement
  GitOps (`deploy-dev`, `deploy-rec`, `deploy-preprod`, `deploy-prod`).
- `templates/promote/template.yml` contient le composant de promotion
  (`semantic-release`, `rollback-prod`).
- `scripts/deploy.py` met à jour les tags d'image dans le dépôt manifests.
- `scripts/rollback.py` revert un commit sur la branche `main` du dépôt
  manifests.
- `scripts/gitlab-release-env.js` résout `GITLAB_URL` et récupère le
  certificat auto-signé de GitLab pour le job `semantic-release`.
- `.gitlab-ci-local.yml` facilite l'exécution locale des jobs.

## Composants et jobs

Les composants ne déclarent pas `stages:` : la pipeline applicative top-level
doit déclarer `build`, `deploy` et `promote` dans cet ordre.

Chaque composant déclare son contrat en `spec:inputs`, puis mappe ces inputs
vers les variables attendues par les jobs et les scripts (`SERVICES`,
`APP_NAME`, `SERVICE_NAME`, `MANIFESTS_PROJECT_PATH`, `MANIFESTS_PATH`,
`HAS_PREPROD`).

- `semantic-release` utilise Node 20 et les plugins semantic-release. Il
  clone `ci-templates` (comme les jobs `deploy`) pour exécuter
  `scripts/gitlab-release-env.js`, qui détermine `GITLAB_URL` (depuis
  `.releaserc.json` ou `INTERNAL_GITLAB_HOST`) et ajoute le certificat
  auto-signé de l'endpoint HTTPS au trust store si nécessaire, via le
  module `tls` natif de Node (pas de dépendance à `openssl`).
- `build-dev` construit chaque service avec Kaniko et pousse les tags
  `<sha-court>` et `dev`.
- `build-rec` ne reconstruit rien : il copie (`crane copy`) l'image
  `<sha-court>` déjà poussée par `build-dev` vers le tag `vX.Y.Z` (même
  digest). Si le tag existe déjà sur le registre, le job ne fait rien.
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

Les composants dépendent de GitLab, du registre configuré par `registry_host`
(`ghcr.io` par défaut) et du dépôt manifests. Ils ne doivent pas connaître la
topologie Kubernetes autrement que par les inputs fournis par l'application et
par les environnements GitLab déclarés.
