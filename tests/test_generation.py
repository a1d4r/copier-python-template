"""Tests that copier generates a valid project structure."""

from typing import TYPE_CHECKING

import re

import pytest
import yaml

from tests.conftest import COPIER_CONFIG, PYTHON_VERSIONS, _generate_project

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


# --- Pydantic (always enabled) ---


def test_pydantic_enabled(default_project: Path) -> None:
    pyproject = (default_project / "pyproject.toml").read_text()

    assert '"pydantic>=' in pyproject
    assert 'plugins = ["pydantic.mypy"]' in pyproject
    assert "[tool.pydantic-mypy]" in pyproject


# --- Variable substitution ---


def test_python_version_in_configs(generate_project: Callable[..., Path]) -> None:
    project = generate_project(python_version="3.12", git_platform="github", skip_tasks=True)
    pyproject = (project / "pyproject.toml").read_text()
    workflow = (project / ".github" / "workflows" / "lint-test.yml").read_text()

    assert 'requires-python = ">=3.12"' in pyproject
    assert 'python_version = "3.12"' in pyproject
    assert "3.12" in workflow


def test_python_version_default_is_latest_choice(default_project: Path) -> None:
    assert COPIER_CONFIG["python_version"]["default"] == PYTHON_VERSIONS[-1]

    pyproject = (default_project / "pyproject.toml").read_text()
    assert f'requires-python = ">={PYTHON_VERSIONS[-1]}"' in pyproject


@pytest.mark.parametrize("bad_version", ["3.9", "3.11", "3.13.1"])
def test_python_version_rejects_unsupported(tmp_path: Path, bad_version: str) -> None:
    with pytest.raises(ValueError, match="python_version"):
        _generate_project(tmp_path / "test-project", python_version=bad_version)


# --- Project slug ---


@pytest.mark.parametrize(
    ("project_name", "slug", "package"),
    [
        ("test-project", "test-project", "test_project"),
        ("My Cool  App!", "my-cool-app", "my_cool_app"),
        ("  Payments API v2 ", "payments-api-v2", "payments_api_v2"),
        ("snake_case_name", "snake-case-name", "snake_case_name"),
    ],
)
def test_project_slug_derived_from_name(
    generate_project: Callable[..., Path], project_name: str, slug: str, package: str
) -> None:
    project = generate_project(project_name=project_name, skip_tasks=True)
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    pyproject = (project / "pyproject.toml").read_text()
    readme = (project / "README.md").read_text()

    assert answers["project_slug"] == slug
    assert answers["package_name"] == package
    assert answers["git_repo_url"] == f"https://github.com/testuser/{slug}"
    assert f'name = "{slug}"' in pyproject
    assert f"cd {slug}\n" in readme
    assert (project / package / "__init__.py").is_file()


@pytest.mark.parametrize("bad_slug", ["My-Project", "-abc", "abc-", "a--b", "1abc", "a_b", "a b"])
def test_project_slug_validator_rejects_invalid(tmp_path: Path, bad_slug: str) -> None:
    with pytest.raises(ValueError, match="project_slug"):
        _generate_project(tmp_path / "test-project", project_slug=bad_slug)


def test_project_name_must_not_be_empty(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="project_name"):
        _generate_project(tmp_path / "test-project", project_name="   ")


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


@pytest.mark.parametrize("bad_name", ["my-pkg", "1abc", "Abc", "ab!"])
def test_package_name_validator_rejects_invalid(tmp_path: Path, bad_name: str) -> None:
    with pytest.raises(ValueError, match="package_name"):
        _generate_project(tmp_path / "test-project", package_name=bad_name)


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
    answers = yaml.safe_load(answers_file.read_text())
    assert answers["project_name"] == "test-project"
    assert answers["project_slug"] == "test-project"
    assert answers["package_name"] == "test_project"
    assert "install_pydantic" not in answers


# --- Common files ---


def test_common_files_exist(default_project: Path) -> None:
    assert (default_project / "Makefile").is_file()
    assert (default_project / "pyproject.toml").is_file()
    assert (default_project / "Dockerfile").is_file()
    assert (default_project / "README.md").is_file()
    assert (default_project / ".pre-commit-config.yaml").is_file()
    assert (default_project / "test_project" / "example.py").is_file()
    assert (default_project / "tests" / "test_example" / "test_hello.py").is_file()


# --- Generated docs and editor config ---


def test_readme_make_targets_exist(default_project: Path) -> None:
    readme = (default_project / "README.md").read_text()
    makefile = (default_project / "Makefile").read_text()

    targets = set(re.findall(r"^([A-Za-z0-9_-]+):", makefile, flags=re.MULTILINE))
    used = {
        target
        for args in re.findall(r"^make ([A-Za-z0-9_ -]+)$", readme, flags=re.MULTILINE)
        for target in args.split()
    }

    assert used, "README does not mention any make targets"
    assert used <= targets, f"README mentions unknown make targets: {sorted(used - targets)}"


def test_readme_links_root_makefile(default_project: Path) -> None:
    readme = (default_project / "README.md").read_text()

    assert "[`Makefile`](Makefile)" in readme


def test_editorconfig_python_section(default_project: Path) -> None:
    editorconfig = (default_project / ".editorconfig").read_text()

    assert "[*.{py,pyi}]" in editorconfig


# --- All Python versions ---


@pytest.mark.parametrize("python_version", PYTHON_VERSIONS)
def test_generation_all_versions(
    generate_project: Callable[..., Path], python_version: str
) -> None:
    project = generate_project(python_version=python_version, skip_tasks=True)
    pyproject = (project / "pyproject.toml").read_text()

    assert f'requires-python = ">={python_version}"' in pyproject
    assert f'python_version = "{python_version}"' in pyproject
