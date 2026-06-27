# PRD

## Intention du projet

`ci-templates` fournit le pipeline GitLab CI partagé du POC. Son
objectif est d'éviter la duplication de logique CI/CD dans chaque application
et de rendre le pattern `build once, promote everywhere` réplicable.

La vision produit complète est dans
`../../platform-cicd/docs/prd.md`.

## Produit attendu

Le projet doit fournir :

- un template GitLab CI versionné ;
- les scripts de déploiement GitOps utilisés par ce template ;
- un contrat clair pour les variables applicatives ;
- un fonctionnement compatible avec les monorepos multi-services.

## Utilisateurs cibles

- Applications qui incluent le template dans leur `.gitlab-ci.yml`.
- Mainteneurs plateforme qui font évoluer la chaîne CI/CD.
- Développeurs qui veulent exécuter certains jobs en local avec
  `gitlab-ci-local`.

## Critères d'acceptation

- Une application peut inclure le template avec une ref versionnée.
- Les builds dev et release utilisent Kaniko sans démon Docker.
- Les promotions mettent à jour le dépôt manifests via Git.
- `HAS_PREPROD` active ou désactive le stade `preprod`.
- Le rollback prod est possible par revert GitOps.

## Non-objectifs

- Fournir un pipeline universel pour tous les langages hors contrat du POC.
- Déployer directement avec `kubectl`.
- Propager automatiquement les changements de template à toutes les apps.
