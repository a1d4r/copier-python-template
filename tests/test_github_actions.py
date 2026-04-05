"""GitHub Actions workflow tests via act."""

from typing import TYPE_CHECKING

import subprocess

import pytest

from tests.conftest import check_tool

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_github_actions_pipeline(github_project_committed: Path) -> None:
    check_tool("act")
    check_tool("docker")

    result = subprocess.run(
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
        ],
        cwd=github_project_committed,
    )
    assert result.returncode == 0
