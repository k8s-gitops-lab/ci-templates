# AGENTS.md — ci-templates

## Rôle du dépôt

`ci-templates` fournit le pipeline GitLab CI partagé du POC. Il ne contient
pas de code applicatif : c'est un contrat de pipeline consommé par inclusion
versionnée depuis les dépôts applicatifs.

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `gitlab-ci.yml` | Template CI inclus par les apps (`include: project/ref/file`) |
| `scripts/deploy.py` | Met à jour `kustomization.yaml` et les HTTPRoutes dans le dépôt manifests |
| `scripts/rollback.py` | Revert GitOps sur la branche `main` du dépôt manifests |
| `.gitlab-ci-local.yml` | Surcharges pour exécution locale avec `gitlab-ci-local` |

## Contrat — ne pas casser

- Les noms de jobs (`build-dev`, `build-rec`, `deploy-dev`, `deploy-rec`,
  `deploy-preprod`, `deploy-prod`, `semantic-release`, `rollback-prod`) sont
  référencés par `needs:` dans les pipelines consommateurs. Les renommer casse
  les pipelines existants.
- Les stages (`build`, `deploy`, `promote`) doivent rester dans cet ordre.
- La variable `CI_SCRIPTS_DIR` est le seul point d'extension pour la localisation
  des scripts. Ne pas hardcoder de chemin absolu dans `gitlab-ci.yml`.

## Versioning

Chaque changement fonctionnel doit être livré sous un tag `vX.Y.Z`. Les apps
incluent le template par ref de tag — une modification sans nouveau tag est
silencieusement ignorée par les consommateurs existants.

## Exécution locale

```bash
gitlab-ci-local deploy-dev   # nécessite CI_SCRIPTS_DIR=$PWD et les secrets dans .gitlab-ci-local-secrets.yml
```

## Ce qu'il ne faut pas faire

- Ne pas déployer directement avec `kubectl` depuis les scripts CI.
- Ne pas ajouter de logique spécifique à une application dans `gitlab-ci.yml`.
- Ne pas committer dans `main` sans tag si des apps doivent consommer le changement.
