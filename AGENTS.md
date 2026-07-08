# AGENTS.md — ci-templates

## Rôle du dépôt

`ci-templates` fournit les composants CI/CD GitLab partagés du POC. Il ne
contient pas de code applicatif : c'est un contrat de pipeline consommé par
inclusion versionnée (`include:component`) depuis les dépôts applicatifs.

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `templates/build-kaniko/template.yml` | Composant `build` : `build-dev` (Kaniko) + `build-rec` (retag `crane`, sans rebuild) |
| `templates/deploy-gitops/template.yml` | Composant `deploy` : `deploy-dev/rec/preprod/prod` (met à jour le dépôt manifests) |
| `templates/promote/template.yml` | Composant `promote` : `semantic-release` + `rollback-prod` |
| `scripts/deploy.py` | Met à jour `kustomization.yaml` et les HTTPRoutes dans le dépôt manifests |
| `scripts/rollback.py` | Revert GitOps sur la branche `main` du dépôt manifests |
| `scripts/gitlab-release-env.js` | Résout `GITLAB_URL` et fait confiance au certificat auto-signé de GitLab pour le job `semantic-release` |
| `.gitlab-ci-local.yml` | Surcharges pour exécution locale avec `gitlab-ci-local` |

Chaque composant a son propre `spec:inputs` (typé, avec `default`/`regex`
quand pertinent) — c'est le contrat d'entrée par app, à la place de
l'ancienne section `variables:` libre. Voir `README.md` pour un exemple
d'inclusion complet.

## Contrat — ne pas casser

- Les noms de jobs (`build-dev`, `build-rec`, `deploy-dev`, `deploy-rec`,
  `deploy-preprod`, `deploy-prod`, `semantic-release`, `rollback-prod`) sont
  référencés par `needs:` dans les pipelines consommateurs. Les renommer casse
  les pipelines existants.
- Les composants ne déclarent volontairement pas `stages:` (ce mot-clé ne se
  fusionne pas entre fichiers inclus — le dernier/top-level gagne intégralement,
  cf. doc GitLab sur `include`). C'est à la pipeline top-level de l'app de
  déclarer `stages: [build, deploy, promote]`, dans cet ordre.
- La variable `CI_SCRIPTS_DIR` est le seul point d'extension pour la localisation
  des scripts. Ne pas hardcoder de chemin absolu dans les composants.
- `INTERNAL_GITLAB_HOST` et `CI_SCRIPTS_DIR` restent des `variables:` (pas des
  `spec:inputs`) : ce sont des constantes de plateforme, pas un contrat par
  app (cf. axe 2 — contrat de variables plateforme).

## Versioning

Chaque changement fonctionnel doit être livré sous un tag `vX.Y.Z`. Les apps
incluent chaque composant par ref de tag — une modification sans nouveau tag
est silencieusement ignorée par les consommateurs existants.

## Exécution locale

```bash
# Valider un composant sans dépendance inter-composants :
gitlab-ci-local --file templates/build-kaniko/template.yml --preview \
  --input 'services=helloworld-svc=ghcr.io/k8s-gitops-lab/helloworld-svc'

# Exécuter un job depuis le repo applicatif (ex. helloworld), qui inclut ces
# composants en local pendant le dev — nécessite CI_SCRIPTS_DIR pointant vers
# ce checkout et les secrets dans .gitlab-ci-local-secrets.yml.
gitlab-ci-local deploy-dev
```

## Ce qu'il ne faut pas faire

- Ne pas déployer directement avec `kubectl` depuis les scripts CI.
- Ne pas ajouter de logique spécifique à une application dans un composant.
- Ne pas committer dans `main` sans tag si des apps doivent consommer le changement.
