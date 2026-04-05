"""GitHub Actions workflow tests via act."""

from typing import TYPE_CHECKING

import subprocess

import pytest

from tests.conftest import check_tool

if TYPE_CHECKING:
    from pathlib import Path


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


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_github_actions_lint(github_project_committed: Path) -> None:
    check_tool("act")
    check_tool("docker")

    result = _run_act(github_project_committed, "lint")
    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_github_actions_test(github_project_committed: Path) -> None:
    check_tool("act")
    check_tool("docker")

    result = _run_act(github_project_committed, "test")
    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
