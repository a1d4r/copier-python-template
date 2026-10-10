from typing import TYPE_CHECKING, Any

import subprocess

import pytest

from tests.conftest import PYTHON_VERSIONS, check_tool, dockerfile_uv_version

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

# The uv image of the version pinned in the generated Dockerfile.
DOCKER_IMAGE = "ghcr.io/astral-sh/uv:{uv}-python{python}-trixie-slim"

# NOTE: the ids are the `variant` matrix of `make-test` in .github/workflows/e2e.yml;
# update both together.
VARIANTS: dict[str, dict[str, Any]] = {
    **{version: {"python_version": version} for version in PYTHON_VERSIONS},
    "gitlab": {"git_platform": "gitlab"},
}


@pytest.mark.parametrize("answers", list(VARIANTS.values()), ids=list(VARIANTS))
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(300)
def test_make_install_lint_test(
    generate_project: Callable[..., Path], answers: dict[str, Any]
) -> None:
    check_tool("docker")

    # Without tasks: no host .venv in the mounted directory, and the code is
    # checked exactly as rendered — `make lint` runs before any `make format`.
    project = generate_project(skip_tasks=True, **answers)
    python = (project / ".python-version").read_text().strip()
    image = DOCKER_IMAGE.format(uv=dockerfile_uv_version(project), python=python)

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
            "apt-get update -qq && apt-get install -y -qq make > /dev/null"
            " && make install && make lint test",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
