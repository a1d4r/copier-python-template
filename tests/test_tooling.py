"""Tooling of the generated project: packaging, dev tools, Makefile, pre-commit."""

from typing import TYPE_CHECKING, Any

import re
import shutil
import subprocess
import tomllib

import pytest
import yaml

from tests.conftest import _generate_project

if TYPE_CHECKING:
    from pathlib import Path

MAKE_TARGETS = {
    "help",
    "install",
    "pre-commit-install",
    "format",
    "lint",
    "test",
    "audit",
    "run",
    "update",
    "clean",
    "docker-build",
    "up",
    "down",
    "template-update",
    "template-check",
}


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


# --- Dependencies ---


def _requirements(pyproject: dict[str, Any]) -> list[str]:
    groups = pyproject["dependency-groups"]
    return [dep for group in groups.values() for dep in group if isinstance(dep, str)]


def test_dependency_groups(pyproject: dict[str, Any]) -> None:
    groups = pyproject["dependency-groups"]

    assert set(groups) == {"lint", "test", "dev"}
    assert {"include-group": "lint"} in groups["dev"]
    assert {"include-group": "test"} in groups["dev"]


def test_dev_dependencies_have_only_lower_bounds(pyproject: dict[str, Any]) -> None:
    for requirement in _requirements(pyproject):
        assert re.fullmatch(r"[a-z0-9-]+>=[\d.]+", requirement), requirement


@pytest.mark.parametrize("package", ["typeguard", "safety", "pip-audit"])
def test_dropped_dev_dependencies(pyproject: dict[str, Any], package: str) -> None:
    names = {re.split(r"[<>=]", dep)[0] for dep in _requirements(pyproject)}

    assert package not in names


# --- mypy, pytest, coverage, ruff ---


def test_mypy_config(project: Path, pyproject: dict[str, Any]) -> None:
    mypy = pyproject["tool"]["mypy"]

    assert mypy["strict"] is True
    assert "pydantic.mypy" in mypy["plugins"]
    assert "ignore_missing_imports" not in mypy
    assert "warn_untyped_fields" not in pyproject["tool"]["pydantic-mypy"]
    assert "--install-types" not in (project / "Makefile").read_text()


def test_pytest_config(pyproject: dict[str, Any]) -> None:
    pytest_config = pyproject["tool"]["pytest"]

    assert "ini_options" not in pytest_config
    assert pytest_config["strict"] is True
    assert pytest_config["filterwarnings"] == ["error"]
    assert not any("doctest" in option for option in pytest_config["addopts"])


def test_coverage_config(pyproject: dict[str, Any]) -> None:
    coverage = pyproject["tool"]["coverage"]

    # The threshold is checked by `make test` only, so partial runs do not fail on it.
    assert "fail_under" not in coverage["report"]
    assert coverage["run"]["omit"] == ["test_project/__main__.py"]


def test_ruff_survives_upgrades(pyproject: dict[str, Any]) -> None:
    lint = pyproject["tool"]["ruff"]["lint"]

    assert lint["select"] == ["ALL"]
    assert "CPY" in lint["ignore"]
    assert "pydantic.validator" not in lint["pep8-naming"]["classmethod-decorators"]


# --- Makefile ---


def test_make_targets(project: Path) -> None:
    makefile = (project / "Makefile").read_text()
    targets = set(re.findall(r"^([a-z][a-z0-9-]*):", makefile, flags=re.MULTILINE))

    assert targets >= MAKE_TARGETS
    assert ".DEFAULT_GOAL := help" in makefile
    assert "curl" not in makefile
    assert "--trust" not in makefile.replace("COPIER_ARGS=--trust", "")
    assert re.search(r"^COV_FAIL_UNDER \?= [1-9]\d*$", makefile, flags=re.MULTILINE)
    assert "uv run pytest --cov-fail-under=$(COV_FAIL_UNDER)" in makefile


def test_make_help_lists_targets(project: Path) -> None:
    if shutil.which("make") is None:
        pytest.skip("make not found")

    result = subprocess.run(["make"], cwd=project, capture_output=True, text=True, check=True)

    output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    listed = set(re.findall(r"^  ([a-z][a-z0-9-]*) ", output, flags=re.MULTILINE))
    assert listed >= MAKE_TARGETS


# --- pre-commit ---


def test_pre_commit_uses_locked_tools(project: Path) -> None:
    config = yaml.safe_load((project / ".pre-commit-config.yaml").read_text())
    hooks = {hook["id"]: hook for repo in config["repos"] for hook in repo["hooks"]}

    for hook_id in ("ruff-check", "ruff-format", "mypy"):
        assert hooks[hook_id]["entry"].startswith("uv run --frozen "), hook_id
    assert hooks["uv-lock-check"]["entry"] == "uv lock --check"
    assert "--assume-in-merge" in hooks["check-merge-conflict"]["args"]
    assert all(
        repo["repo"] != "https://github.com/astral-sh/ruff-pre-commit" for repo in config["repos"]
    )
