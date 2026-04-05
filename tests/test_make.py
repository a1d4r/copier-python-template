from typing import TYPE_CHECKING

import subprocess

import pytest

from tests.conftest import check_tool

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

DOCKER_IMAGE = "ghcr.io/astral-sh/uv:python{version}-bookworm-slim"

DOCKER_SETUP = (
    "apt-get update -qq && apt-get install -y -qq git make > /dev/null"
    " && git config --global --add safe.directory /app"
)


# NOTE: test IDs follow pattern [version-pydantic].
# CI workflow e2e.yml depends on these IDs — update both together.
@pytest.mark.parametrize(
    ("python_version", "install_pydantic"),
    [
        ("3.9", False),
        ("3.10", False),
        ("3.11", False),
        ("3.12", False),
        ("3.13", False),
        ("3.13", True),
    ],
)
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(300)
def test_make_format_lint_test(
    generate_project: Callable[..., Path], python_version: str, *, install_pydantic: bool
) -> None:
    check_tool("docker")

    project = generate_project(python_version=python_version, install_pydantic=install_pydantic)
    image = DOCKER_IMAGE.format(version=python_version)

    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{project}:/app",
            "-w",
            "/app",
            image,
            "bash",
            "-c",
            f"{DOCKER_SETUP} && make install && make format lint test",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
