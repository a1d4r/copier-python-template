from typing import TYPE_CHECKING, Any

import os
import re
import shutil
import subprocess

from pathlib import Path

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Callable

from copier import run_copy

TEMPLATE_DIR = Path(__file__).parent.parent
COPIER_CONFIG: dict[str, Any] = yaml.safe_load((TEMPLATE_DIR / "copier.yml").read_text())
PYTHON_VERSIONS: list[str] = COPIER_CONFIG["python_version"]["choices"]


def check_tool(name: str) -> None:
    """Skip test if CLI tool is not installed."""
    if shutil.which(name) is None:
        pytest.skip(f"{name} not found")


UV_STAGE = re.compile(r"^FROM ghcr\.io/astral-sh/uv:(\d+\.\d+\.\d+) AS uv$", re.MULTILINE)


def dockerfile_uv_version(project: Path) -> str:
    """The uv version pinned in the generated Dockerfile (its single `FROM ... AS uv` stage)."""
    found = UV_STAGE.findall((project / "Dockerfile").read_text())
    assert len(found) == 1, "the Dockerfile must pin uv in exactly one `FROM ... AS uv` stage"
    return str(found[0])


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


BASE_DATA: dict[str, Any] = {
    "project_name": "test-project",
    "username": "testuser",
    "git_platform": "github",
    "line_length": 88,
}


def _generate_project(dest: Path, *, skip_tasks: bool = False, **overrides: Any) -> Path:
    """Render the template (HEAD + uncommitted changes) into ``dest``: BASE_DATA + overrides."""
    run_copy(
        str(TEMPLATE_DIR),
        str(dest),
        data={**BASE_DATA, **overrides},
        defaults=True,
        unsafe=True,
        vcs_ref="HEAD",
        skip_tasks=skip_tasks,
    )
    return dest


@pytest.fixture(scope="module")
def default_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Default project (github, default python version). Shared across module."""
    return _generate_project(tmp_path_factory.mktemp("default") / "test-project")


@pytest.fixture(scope="module")
def github_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """GitHub project (default python version). Shared across module."""
    return _generate_project(tmp_path_factory.mktemp("github") / "test-project")


@pytest.fixture(scope="module")
def github_project_committed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """GitHub project with initial commit. For act tests."""
    project = _generate_project(tmp_path_factory.mktemp("github-committed") / "test-project")
    git_commit(project)
    return project


@pytest.fixture(scope="module")
def gitlab_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """GitLab project (default python version). Shared across module."""
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

    def _generate(**overrides: Any) -> Path:
        return _generate_project(tmp_path / "test-project", **overrides)

    return _generate
