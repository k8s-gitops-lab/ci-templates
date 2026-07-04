# ci-templates

Templates GitLab CI partages du POC.

Le projet GitLab interne `shared-ci/ci-templates` est cree par le Terraform de `gitlab-projects-iac` (import depuis GitHub). Son fichier `gitlab-ci.yml` est inclus par les applications avec une reference versionnee (tag `vX.Y.Z`).

Contrat principal : build once, promote everywhere via les branches GitOps `dev`, `rec`, `preprod` et `main` du repo manifests applicatif.
