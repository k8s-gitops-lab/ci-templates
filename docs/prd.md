# PRD

## Intention du projet

`ci-templates` fournit les composants CI/CD GitLab partagés du POC. Son
objectif est d'éviter la duplication de logique CI/CD dans chaque application
et de rendre le pattern `build once, promote everywhere` réplicable via des
inclusions versionnées `include:component`.

La vision produit complète est dans
`../../cockpit/docs/prd.md`.

## Produit attendu

Le projet doit fournir :

- des composants GitLab CI versionnés sous `templates/` ;
- les scripts de déploiement GitOps utilisés par ces composants ;
- un contrat clair via `spec:inputs` pour les paramètres applicatifs ;
- un fonctionnement compatible avec les monorepos multi-services.

## Utilisateurs cibles

- Applications qui incluent les composants dans leur `.gitlab-ci.yml`.
- Mainteneurs plateforme qui font évoluer la chaîne CI/CD.
- Développeurs qui veulent exécuter certains jobs en local avec
  `gitlab-ci-local`.

## Critères d'acceptation

- Une application peut inclure les composants avec une ref versionnée.
- Le build dev utilise un outil sans démon Docker (Buildah par défaut, Kaniko
  disponible en option) ; la release retague l'image existante (Skopeo) sans
  rebuild.
- Les promotions mettent à jour le dépôt manifests via Git.
- `has_preprod` active ou désactive le stade `preprod`.
- Le rollback prod est possible par revert GitOps.

## Non-objectifs

- Fournir un pipeline universel pour tous les langages hors contrat du POC.
- Déployer directement avec `kubectl`.
- Propager automatiquement les changements de composants à toutes les apps.
