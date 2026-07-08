# Spec fonctionnelle

## Contrat applicatif

Une application consommatrice inclut les composants et fournit leurs inputs :

- `build-docker` : `dockerfile`, `context_path`, `snapshot_image`,
  `release_image` — un jeu d'inputs par service (voir `README.md` pour le
  cas monorepo multi-service, géré par `parallel: matrix:` côté app, pas par
  le composant) ;
- `deploy-gitops` : `app_name`, `service_name` (service utilisé pour les URLs
  GitLab), `manifests_project_path`, `manifests_path`, `has_preprod` ;
- `promote` : `manifests_project_path`.

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

`docker-publish` ne reconstruit jamais l'image : il copie (Skopeo) l'image
snapshot déjà poussée par `docker-buildah-build` vers le tag `vX.Y.Z`, sans
rebuild.
