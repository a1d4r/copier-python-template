"""GitLab CI pipeline tests via gitlab-ci-local."""

from typing import TYPE_CHECKING

import subprocess

import pytest

from tests.conftest import check_tool

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_gitlab_ci_pipeline(gitlab_project_committed: Path) -> None:
    check_tool("gitlab-ci-local")
    check_tool("docker")

    result = subprocess.run(
        ["gitlab-ci-local", "--file", ".gitlab-ci.yml"],
        cwd=gitlab_project_committed,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
