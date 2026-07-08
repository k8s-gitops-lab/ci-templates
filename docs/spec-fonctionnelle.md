# Spec fonctionnelle

## Contrat applicatif

Une application consommatrice inclut les composants et fournit leurs inputs :

- `services`, liste `<service>=<image>` séparée par des espaces ;
- `app_name` ;
- `service_name`, service utilisé pour les URLs GitLab ;
- `manifests_project_path` ;
- `manifests_path` ;
- `has_preprod`.

Chaque service listé doit avoir un sous-dossier du même nom et un `Dockerfile`.

`INTERNAL_GITLAB_HOST` n'en fait pas partie : c'est une constante de
plateforme (même instance GitLab in-cluster pour toutes les apps), fournie
par défaut dans les composants qui clonent GitLab. Une app ne la déclare que
si elle cible une autre instance GitLab.

## Flow

Les composants supportent le flow plateforme :

- merge sur `main` : build dev puis déploiement dev automatique ;
- `semantic-release` (automatique après `deploy-dev`) : création du tag
  `vX.Y.Z` si les Conventional Commits mergés le justifient ;
- tag `vX.Y.Z` : build release puis déploiement rec automatique ;
- gate manuel vers preprod si `has_preprod=true` ;
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
