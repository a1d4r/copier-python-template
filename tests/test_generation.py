"""Tests that copier generates a valid project structure."""

from typing import TYPE_CHECKING, Any

import os
import re
import subprocess
import sys
import tomllib

from pathlib import Path

import pytest
import yaml

from tests.conftest import (
    BASE_DATA,
    COPIER_CONFIG,
    PYTHON_VERSIONS,
    TEMPLATE_DIR,
    _generate_project,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _pyproject(project: Path) -> dict[str, Any]:
    return tomllib.loads((project / "pyproject.toml").read_text())


# --- Platform-specific structure ---


def test_github_structure(github_project: Path) -> None:
    assert (github_project / ".github" / "workflows" / "lint-test.yml").is_file()
    assert (github_project / ".github" / "dependabot.yml").is_file()
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
    pyproject = _pyproject(project)
    dockerfile = (project / "Dockerfile").read_text()
    workflow = (project / ".github" / "workflows" / "lint-test.yml").read_text()

    assert (project / ".python-version").read_text() == "3.12\n"
    assert pyproject["project"]["requires-python"] == ">=3.12"
    assert pyproject["tool"]["mypy"]["python_version"] == "3.12"
    assert pyproject["tool"]["ruff"]["target-version"] == "py312"
    assert "FROM python:3.12-slim-trixie AS production" in dockerfile
    # GitHub Actions take the version from .python-version (uv), not from the workflow.
    assert "python-version:" not in workflow


def test_python_version_file_is_not_ignored(default_project: Path) -> None:
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".python-version"], cwd=default_project, check=False
    )

    assert result.returncode == 1, ".python-version must be committed"


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
    assert (default_project / "test_project" / "__main__.py").is_file()

    makefile = (default_project / "Makefile").read_text()
    assert "PACKAGE := test_project" in makefile

    test_main = (default_project / "tests" / "test_main.py").read_text()
    assert "from test_project.__main__ import main" in test_main

    pyproject = _pyproject(default_project)
    assert pyproject["tool"]["coverage"]["run"]["source"] == ["test_project"]
    assert pyproject["tool"]["mypy"]["files"] == ["test_project", "tests"]


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

    assert "codequality" not in makefile


def test_gitlab_make_targets(gitlab_project: Path) -> None:
    makefile = (gitlab_project / "Makefile").read_text()
    gitlab_ci = (gitlab_project / ".gitlab-ci.yml").read_text()

    assert "\ncodequality:" in makefile
    assert "--output-format=gitlab" in makefile
    assert "mypy-gitlab-code-quality" in makefile
    assert "make codequality" in gitlab_ci


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
    assert (default_project / ".python-version").is_file()
    assert (default_project / "test_project" / "__main__.py").is_file()
    assert (default_project / "test_project" / "config.py").is_file()
    assert (default_project / "test_project" / "logging_config.py").is_file()
    assert (default_project / ".env.example").is_file()


# --- Copier tasks ---


def test_copy_tasks_init_repo_and_env(default_project: Path) -> None:
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=default_project,
        capture_output=True,
        text=True,
        check=True,
    )

    assert branch.stdout.strip() == "main"
    assert (default_project / "uv.lock").is_file()
    assert (default_project / ".venv").is_dir()


def test_copy_tasks_do_not_fail_without_uv(tmp_path: Path) -> None:
    # Copier runs tasks through plumbum, which snapshots the environment at import time,
    # so run the CLI in a subprocess to really hide `uv` from PATH.
    path = [
        entry
        for entry in os.environ.get("PATH", "").split(os.pathsep)
        if entry and not (Path(entry) / "uv").exists()
    ]
    project = tmp_path / "test-project"
    data = [f"--data={key}={value}" for key, value in BASE_DATA.items()]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "copier",
            "copy",
            "--trust",
            "--defaults",
            "--vcs-ref=HEAD",
            *data,
            str(TEMPLATE_DIR),
            str(project),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": os.pathsep.join(path)},
    )

    assert result.returncode == 0, result.stderr
    assert "WARNING: uv not found" in result.stderr
    assert (project / "pyproject.toml").is_file()
    assert (project / ".git").is_dir()
    assert not (project / "uv.lock").exists()


# --- Generated docs and editor config ---


def _make_targets(project: Path) -> set[str]:
    makefile = (project / "Makefile").read_text()
    return set(re.findall(r"^([A-Za-z0-9_-]+):", makefile, flags=re.MULTILINE))


def test_readme_make_targets_exist(default_project: Path) -> None:
    readme = (default_project / "README.md").read_text()

    commands = re.findall(r"^make ([^#\n]+)", readme, flags=re.MULTILINE)
    commands += re.findall(r"`make ([^`]+)`", readme)
    used = {
        word
        for command in commands
        for word in command.split()
        if re.fullmatch(r"[a-z][a-z0-9-]*", word)
    }

    assert used, "README does not mention any make targets"
    unknown = used - _make_targets(default_project)
    assert not unknown, f"README mentions unknown make targets: {sorted(unknown)}"


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
