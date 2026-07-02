# Spec fonctionnelle

## Contrat applicatif

Une application consommatrice inclut le template et fournit ses variables :

- `APP_NAME` ;
- `SERVICES`, liste `<service>=<image>` séparée par des espaces ;
- `SERVICE_NAME`, service utilisé pour les URLs GitLab ;
- `MANIFESTS_PROJECT_PATH` ;
- `MANIFESTS_PATH` ;
- `HAS_PREPROD`.

Chaque service listé doit avoir un sous-dossier du même nom et un `Dockerfile`.

## Flow

Le template supporte le flow plateforme :

- merge sur `main` : build dev puis déploiement dev automatique ;
- job manuel `semantic-release` : création du tag `vX.Y.Z` ;
- tag `vX.Y.Z` : build release puis déploiement rec automatique ;
- gate manuel vers preprod si `HAS_PREPROD=true` ;
- gate manuel vers prod ;
- rollback prod par revert d'un commit manifests.

## Promotion

La promotion ne reconstruit pas les images après `rec`. Les environnements
suivants réutilisent le même tag `vX.Y.Z` et ne font que mettre à jour l'état
GitOps.

## Idempotence du build release

`build-rec` ne reconstruit jamais l'image : il retag l'image `<sha-court>`
déjà buildée par `build-dev` avec le tag `vX.Y.Z`. Si ce tag existe déjà sur
GHCR (retry du job, ou tag déjà promu), le job ne fait rien et continue
silencieusement — il n'écrase jamais une image existante, mais n'échoue pas
non plus explicitement dans ce cas.
