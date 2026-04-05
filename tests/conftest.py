import shutil

from pathlib import Path

import pytest

from copier import run_copy

TEMPLATE_DIR = Path(__file__).parent.parent


def check_tool(name: str) -> None:
    """Skip test if CLI tool is not installed."""
    if shutil.which(name) is None:
        pytest.skip(f"{name} not found")


def _generate_project(
    dest: Path,
    python_version: str = "3.13",
    git_platform: str = "github",
    install_pydantic: bool = True,
) -> Path:
    run_copy(
        str(TEMPLATE_DIR),
        str(dest),
        data={
            "project_name": "test-project",
            "package_name": "test_project",
            "username": "testuser",
            "python_version": python_version,
            "git_platform": git_platform,
            "install_pydantic": install_pydantic,
            "line_length": 88,
        },
        defaults=True,
        unsafe=True,
        vcs_ref="HEAD",
    )

    return dest


@pytest.fixture(scope="module")
def default_project(tmp_path_factory):
    """Default project (github, pydantic=True, python 3.13). Shared across module."""
    return _generate_project(tmp_path_factory.mktemp("default") / "test-project")


@pytest.fixture(scope="module")
def gitlab_project(tmp_path_factory):
    """GitLab project (pydantic=True, python 3.13). Shared across module."""
    return _generate_project(
        tmp_path_factory.mktemp("gitlab") / "test-project", git_platform="gitlab"
    )


@pytest.fixture
def generate_project(tmp_path):
    """Factory fixture for generating a project with custom parameters."""

    def _generate(
        python_version: str = "3.13", git_platform: str = "github", install_pydantic: bool = True
    ) -> Path:
        return _generate_project(
            tmp_path / "test-project",
            python_version=python_version,
            git_platform=git_platform,
            install_pydantic=install_pydantic,
        )

    return _generate
