"""Tests that copier generates a valid project structure."""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

# --- Platform-specific structure ---


def test_github_structure(github_project: Path) -> None:
    assert (github_project / ".github" / "workflows" / "lint-test.yml").is_file()
    assert not (github_project / ".gitlab-ci.yml").exists()


def test_gitlab_structure(gitlab_project: Path) -> None:
    assert (gitlab_project / ".gitlab-ci.yml").is_file()
    assert not (gitlab_project / ".github").exists()


# --- Pydantic ---


def test_pydantic_enabled(default_project: Path) -> None:
    pyproject = (default_project / "pyproject.toml").read_text()
    example = (default_project / "test_project" / "example.py").read_text()

    assert "pydantic" in pyproject
    assert 'plugins = ["pydantic.mypy"]' in pyproject
    assert "[tool.pydantic-mypy]" in pyproject
    assert "import pydantic" in example
    assert "ExampleModel" in example


def test_pydantic_disabled(generate_project: Callable[..., Path]) -> None:
    project = generate_project(install_pydantic=False)
    pyproject = (project / "pyproject.toml").read_text()
    example = (project / "test_project" / "example.py").read_text()

    assert '"pydantic>=' not in pyproject
    assert 'plugins = ["pydantic.mypy"]' not in pyproject
    assert "[tool.pydantic-mypy]" not in pyproject
    assert "import pydantic" not in example
    assert "ExampleModel" not in example


# --- Variable substitution ---


def test_python_version_in_configs(generate_project: Callable[..., Path]) -> None:
    project = generate_project(python_version="3.11", git_platform="github")
    pyproject = (project / "pyproject.toml").read_text()
    workflow = (project / ".github" / "workflows" / "lint-test.yml").read_text()

    assert 'requires-python = ">=3.11"' in pyproject
    assert 'python_version = "3.11"' in pyproject
    assert "3.11" in workflow


def test_package_name_substitution(default_project: Path) -> None:
    assert (default_project / "test_project").is_dir()
    assert (default_project / "test_project" / "__init__.py").is_file()
    assert (default_project / "test_project" / "example.py").is_file()

    makefile = (default_project / "Makefile").read_text()
    assert "CODE = test_project tests" in makefile

    conftest = (default_project / "tests" / "conftest.py").read_text()
    assert "test_project" in conftest

    test_hello = (default_project / "tests" / "test_example" / "test_hello.py").read_text()
    assert "from test_project.example import hello" in test_hello

    pyproject = (default_project / "pyproject.toml").read_text()
    assert 'source = ["test_project"]' in pyproject


def test_line_length(default_project: Path) -> None:
    pyproject = (default_project / "pyproject.toml").read_text()

    assert "line-length = 88" in pyproject
    assert "max-doc-length = 88" in pyproject


# --- Platform-specific make targets ---


def test_github_make_targets(github_project: Path) -> None:
    makefile = (github_project / "Makefile").read_text()

    assert "check-ruff-github" in makefile
    assert "check-ruff-gitlab" not in makefile
    assert "check-mypy-gitlab" not in makefile


def test_gitlab_make_targets(gitlab_project: Path) -> None:
    makefile = (gitlab_project / "Makefile").read_text()

    assert "check-ruff-gitlab" in makefile
    assert "check-mypy-gitlab" in makefile
    assert "check-ruff-github" not in makefile


def test_gitlab_dev_dependencies(gitlab_project: Path) -> None:
    pyproject = (gitlab_project / "pyproject.toml").read_text()

    assert "mypy-gitlab-code-quality" in pyproject


def test_github_no_gitlab_deps(github_project: Path) -> None:
    pyproject = (github_project / "pyproject.toml").read_text()

    assert "mypy-gitlab-code-quality" not in pyproject


# --- Copier answers file ---


def test_copier_answers_file(default_project: Path) -> None:
    answers_file = default_project / ".copier-answers.yml"

    assert answers_file.is_file()
    content = answers_file.read_text()
    assert "test-project" in content
    assert "test_project" in content


# --- Common files ---


def test_common_files_exist(default_project: Path) -> None:
    assert (default_project / "Makefile").is_file()
    assert (default_project / "pyproject.toml").is_file()
    assert (default_project / "Dockerfile").is_file()
    assert (default_project / "README.md").is_file()
    assert (default_project / ".pre-commit-config.yaml").is_file()
    assert (default_project / "test_project" / "example.py").is_file()
    assert (default_project / "tests" / "test_example" / "test_hello.py").is_file()


# --- All Python versions ---


@pytest.mark.parametrize("python_version", ["3.9", "3.10", "3.11", "3.12", "3.13"])
def test_generation_all_versions(
    generate_project: Callable[..., Path], python_version: str
) -> None:
    project = generate_project(python_version=python_version)
    pyproject = (project / "pyproject.toml").read_text()

    assert f'requires-python = ">={python_version}"' in pyproject
    assert f'python_version = "{python_version}"' in pyproject
