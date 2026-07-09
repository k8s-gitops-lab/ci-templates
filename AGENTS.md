# AGENTS.md — ci-templates

## Rôle du dépôt

`ci-templates` fournit les composants CI/CD GitLab partagés du POC. Il ne
contient pas de code applicatif : c'est un contrat de pipeline consommé par
inclusion versionnée (`include:component`) depuis les dépôts applicatifs.

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `templates/build-docker/template.yml` | Enrobe [to-be-continuous/docker](https://gitlab.com/to-be-continuous/docker) : `docker-buildah-build` (build) + `docker-publish` (retag release via Skopeo, sans rebuild) |
| `templates/deploy-gitops/template.yml` | Composant `deploy` : `deploy-dev/rec/preprod/prod` (met à jour le dépôt manifests) |
| `templates/promote/template.yml` | Enrobe [to-be-continuous/semantic-release](https://gitlab.com/to-be-continuous/semantic-release) + `rollback-prod` |
| `scripts/deploy.py` | Met à jour `kustomization.yaml` et les HTTPRoutes dans le dépôt manifests |
| `scripts/rollback.py` | Revert GitOps sur la branche `main` du dépôt manifests |
| `.gitlab-ci-local.yml` | Surcharges pour exécution locale avec `gitlab-ci-local` |

Chaque composant a son propre `spec:inputs` (typé, avec `default`/`regex`
quand pertinent) — c'est le contrat d'entrée par app, à la place de
l'ancienne section `variables:` libre. Voir `README.md` pour un exemple
d'inclusion complet.

## Contrat — ne pas casser

- Les noms de jobs (`docker-buildah-build`, `docker-publish`, `deploy-dev`,
  `deploy-rec`, `deploy-preprod`, `deploy-prod`, `semantic-release`,
  `rollback-prod`) sont référencés par `needs:` dans les pipelines
  consommateurs. Les renommer casse les pipelines existants.
  `docker-buildah-build`/`docker-publish` viennent de
  [to-be-continuous/docker](https://gitlab.com/to-be-continuous/docker) : le
  nom dépend de l'outil de build par défaut choisi en amont (`buildah`
  actuellement, `TBC_DEFAULT_DOCKER_BUILD_TOOL`). On ne fixe pas l'input
  `build-tool` explicitement dans `build-docker` — si to-be-continuous change
  son défaut, ces noms de job changent aussi et le contrat doit être mis à
  jour en conséquence (ou fixer `build-tool` explicitement pour s'en isoler).
- `stages:` ne se fusionne jamais entre fichiers inclus — le dernier/top-level
  gagne intégralement, cf. doc GitLab sur `include`. `build-docker` et
  `promote` héritent chacun d'un `stages:` complet de to-be-continuous
  (`build`, `package-build`, `package-test`, ..., `publish`, ...). C'est à la
  pipeline top-level de l'app de déclarer la liste complète et cohérente,
  typiquement `[build, package-build, package-test, deploy, publish,
  promote]` (voir `README.md`).
- À l'inverse, un **job** (pas `stages:`) redéclaré après un `include:` avec
  le même nom **fusionne** ses clés avec la définition incluse (comportement
  standard GitLab pour personnaliser un job de template inclus) — c'est ce
  qui permet à l'app d'ajouter un `parallel: matrix:` sur
  `docker-buildah-build`/`docker-publish` pour un monorepo multi-service sans
  perdre le `script:` fourni par to-be-continuous. Ne pas confondre les deux
  comportements.
- La variable `CI_SCRIPTS_DIR` est le seul point d'extension pour la localisation
  des scripts. Ne pas hardcoder de chemin absolu dans les composants.
- `INTERNAL_GITLAB_HOST`, `CI_SCRIPTS_DIR` et `CUSTOM_CA_CERTS` restent des
  `variables:` (pas des `spec:inputs`) : ce sont des constantes de
  plateforme, pas un contrat par app (cf. axe 2 — contrat de variables
  plateforme). `CUSTOM_CA_CERTS` (PEM en clair : CA du proxy sortant + CA
  interne auto-signée concaténées) est lue automatiquement par les
  composants to-be-continuous (`install_custom_ca_certs`/`install_ca_certs`
  dans leurs scripts communs) — provisionnée en variable de groupe GitLab par
  Terraform dans `gitlab-projects-iac` (même mécanisme que `ZSCALER_CA_B64`
  aujourd'hui, à ajouter côté `gitlab-projects-iac` avant de taguer `v3.0.0`
  ici).

## Versioning

Chaque changement fonctionnel doit être livré sous un tag `vX.Y.Z`. Les apps
incluent chaque composant par ref de tag — une modification sans nouveau tag
est silencieusement ignorée par les consommateurs existants.

`build-docker` et `promote` épinglent chacun une version de composant
to-be-continuous (`@6.1.0`, `@4.3.0` au moment d'écrire ces lignes) — c'est le
seul endroit où la mettre à jour pour toutes les apps. Vérifier le changelog
amont avant de bumper : ces composants ne suivent pas le versioning de
`ci-templates`.

## Exécution locale

```bash
# Valider un composant sans dépendance inter-composants :
gitlab-ci-local --file templates/build-docker/template.yml --preview \
  --input 'release_image=ghcr.io/k8s-gitops-lab/helloworld-svc:$CI_COMMIT_REF_NAME'

# Exécuter un job depuis le repo applicatif (ex. helloworld), qui inclut ces
# composants en local pendant le dev — nécessite CI_SCRIPTS_DIR pointant vers
# ce checkout et les secrets dans .gitlab-ci-local-secrets.yml.
gitlab-ci-local deploy-dev
```

`gitlab-ci-local` résout les composants `gitlab.com/to-be-continuous/...` par
clone SSH (`git archive --remote=ssh://git@gitlab.com`) : nécessite une clé
SSH enregistrée sur un compte gitlab.com (même pour un projet public). Sans
cette clé, `--preview` échoue sur l'étape de fetch du composant — dans ce cas,
valider en inspectant directement le YAML récupéré en HTTPS
(`curl -sL https://gitlab.com/to-be-continuous/docker/-/raw/master/templates/gitlab-ci-docker.yml`)
plutôt qu'en bloquant sur l'exécution locale.

## Ce qu'il ne faut pas faire

- Ne pas déployer directement avec `kubectl` depuis les scripts CI.
- Ne pas ajouter de logique spécifique à une application dans un composant.
- Ne pas committer dans `main` sans tag si des apps doivent consommer le changement.

## Gouvernance du développement

Ce repo fait partie de la plateforme poc-devops : toute contribution suit
les trois axes de maîtrise (produit, code, architecture) définis dans
`cockpit/AGENTS.md`, section « Gouvernance du développement » — PRD et
backlog dans `cockpit/docs/`.
