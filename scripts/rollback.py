#!/usr/bin/env python3
"""Annule un commit sur la branche main du dépôt de manifests (rollback prod).

Usage: python3 rollback.py

Variables d'environnement attendues:
  REVERT_SHA               SHA du commit à annuler sur main
  INTERNAL_GITLAB_HOST     host GitLab in-cluster
  GITLAB_PUSH_TOKEN        token de push
  MANIFESTS_PROJECT_PATH   "infra/helloworld-iac"
"""
import os
import subprocess
import sys
import tempfile


def manifests_url() -> str:
    host = os.environ["INTERNAL_GITLAB_HOST"]
    token = os.environ["GITLAB_PUSH_TOKEN"]
    path = os.environ["MANIFESTS_PROJECT_PATH"]
    return f"http://root:{token}@{host}/{path}.git"


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True)


def main() -> None:
    revert_sha = os.environ.get("REVERT_SHA", "").strip()
    if not revert_sha:
        sys.exit("La variable REVERT_SHA est vide ou absente.")

    project_path = os.environ.get("MANIFESTS_PROJECT_PATH", "")

    with tempfile.TemporaryDirectory(prefix="manifests-rollback-") as tmpdir:
        git("clone", "--branch", "main", manifests_url(), tmpdir)
        git("config", "user.email", "ci@gitlab.local", cwd=tmpdir)
        git("config", "user.name", "GitLab CI", cwd=tmpdir)
        git("revert", "--no-edit", revert_sha, cwd=tmpdir)
        git("push", "origin", "main", cwd=tmpdir)

    print(f"Rollback appliqué sur '{project_path}@main' : revert de {revert_sha}.")


if __name__ == "__main__":
    main()
