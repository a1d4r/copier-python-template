"""GitLab CI pipeline tests via gitlab-ci-local."""

from typing import TYPE_CHECKING

import subprocess

import pytest

from tests.conftest import check_tool

GITLAB_JOBS = ("lint", "codequality", "test", "audit")

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_gitlab_ci_pipeline(gitlab_project_committed: Path) -> None:
    check_tool("gitlab-ci-local")
    check_tool("docker")

    # docker-build needs Docker-in-Docker (a privileged service); the image build
    # is covered by tests/test_docker.py::test_docker_production_image_runs.
    result = subprocess.run(
        ["gitlab-ci-local", "--file", ".gitlab-ci.yml", *GITLAB_JOBS], cwd=gitlab_project_committed
    )
    assert result.returncode == 0
