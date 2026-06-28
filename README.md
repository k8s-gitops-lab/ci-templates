# ci-templates

Templates GitLab CI partages du POC.

Le fichier `gitlab-ci.yml` est seed par `platform-cicd` dans le projet GitLab interne `root/ci-templates`, puis inclus par les applications avec une reference versionnee.

Contrat principal : build once, promote everywhere via les branches GitOps `dev`, `rec`, `preprod` et `main` du repo manifests applicatif.
