"""Tooling of the generated project: packaging, dev tools, Makefile, pre-commit."""

from typing import TYPE_CHECKING, Any

import re
import tomllib

import pytest

from tests.conftest import _generate_project

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module", params=["github", "gitlab"])
def project(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Rendered project without tasks (no git init, no uv sync)."""
    platform: str = request.param
    return _generate_project(
        tmp_path_factory.mktemp(platform) / "test-project", skip_tasks=True, git_platform=platform
    )


@pytest.fixture(scope="module")
def pyproject(project: Path) -> dict[str, Any]:
    return tomllib.loads((project / "pyproject.toml").read_text())


# --- Packaging ---


def test_packaged_flat_layout(pyproject: dict[str, Any]) -> None:
    assert pyproject["build-system"]["build-backend"] == "uv_build"
    (requirement,) = pyproject["build-system"]["requires"]
    assert re.fullmatch(r"uv_build>=[\d.]+,<[\d.]+", requirement)

    backend = pyproject["tool"]["uv"]["build-backend"]
    assert backend == {"module-name": "test_project", "module-root": ""}
    assert "package" not in pyproject["tool"]["uv"]

    assert pyproject["project"]["scripts"] == {"test-project": "test_project.__main__:main"}


def test_main_module(project: Path) -> None:
    main = (project / "test_project" / "__main__.py").read_text()

    assert "def main() -> None:" in main
    assert 'if __name__ == "__main__":' in main


def test_dockerfile_runs_package(project: Path) -> None:
    dockerfile = (project / "Dockerfile").read_text()

    assert 'CMD ["python", "-m", "test_project"]' in dockerfile
    assert ".example" not in dockerfile
