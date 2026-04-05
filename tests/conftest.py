from typing import TYPE_CHECKING

import os
import shutil
import subprocess

from pathlib import Path

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from copier import run_copy

TEMPLATE_DIR = Path(__file__).parent.parent


def check_tool(name: str) -> None:
    """Skip test if CLI tool is not installed."""
    if shutil.which(name) is None:
        pytest.skip(f"{name} not found")


def git_commit(project: Path) -> None:
    """Create initial commit — act/gitlab-ci-local only sync tracked files."""
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
def default_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Default project (github, pydantic=True, python 3.13). Shared across module."""
    return _generate_project(tmp_path_factory.mktemp("default") / "test-project")


@pytest.fixture(scope="module")
def github_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """GitHub project (pydantic=True, python 3.13). Shared across module."""
    return _generate_project(tmp_path_factory.mktemp("github") / "test-project")


@pytest.fixture(scope="module")
def github_project_committed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """GitHub project with initial commit. For act tests."""
    project = _generate_project(tmp_path_factory.mktemp("github-committed") / "test-project")
    git_commit(project)
    return project


@pytest.fixture(scope="module")
def gitlab_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """GitLab project (pydantic=True, python 3.13). Shared across module."""
    return _generate_project(
        tmp_path_factory.mktemp("gitlab") / "test-project", git_platform="gitlab"
    )


@pytest.fixture(scope="module")
def gitlab_project_committed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """GitLab project with initial commit. For gitlab-ci-local tests."""
    project = _generate_project(
        tmp_path_factory.mktemp("gitlab-committed") / "test-project", git_platform="gitlab"
    )
    git_commit(project)
    return project


@pytest.fixture
def generate_project(tmp_path: Path) -> Callable[..., Path]:
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
