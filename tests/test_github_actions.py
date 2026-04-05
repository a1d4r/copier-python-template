"""GitHub Actions workflow tests via act."""

from typing import TYPE_CHECKING

import os
import subprocess

import pytest

from tests.conftest import _generate_project, check_tool

if TYPE_CHECKING:
    from pathlib import Path


def _git_commit(project: Path) -> None:
    """Create initial commit — act needs a committed repo for actions/checkout."""
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=project,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "t@t",
            "HOME": str(project.parent),
        },
    )


def _run_act(project: Path, job: str) -> subprocess.CompletedProcess[str]:
    """Run act for a specific job in the generated project's workflow."""
    return subprocess.run(
        [
            "act",
            "push",
            "-W",
            ".github/workflows/lint-test.yml",
            "-P",
            "ubuntu-latest=catthehacker/ubuntu:act-22.04",
            # Disable cache server: act caches .venv across runs with different tmp paths,
            # which breaks virtualenv binaries (e.g. deptry not found).
            "--no-cache-server",
            "-j",
            job,
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def github_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a GitHub project with initial commit for act tests. Shared across module."""
    project = _generate_project(
        tmp_path_factory.mktemp("act") / "test-project",
        python_version="3.13",
        git_platform="github",
    )
    _git_commit(project)
    return project


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_github_actions_lint(github_project: Path) -> None:
    check_tool("act")
    check_tool("docker")

    result = _run_act(github_project, "lint")
    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_github_actions_test(github_project: Path) -> None:
    check_tool("act")
    check_tool("docker")

    result = _run_act(github_project, "test")
    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
