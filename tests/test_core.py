"""Application core of the generated project: settings, logging, entry point, seeds."""

from typing import TYPE_CHECKING, Any

import os
import re
import shutil
import subprocess
import tomllib

import pytest

from copier import run_copy

from tests.conftest import BASE_DATA, COPIER_CONFIG, TEMPLATE_DIR, _generate_project

if TYPE_CHECKING:
    from pathlib import Path

SEED_FILES = [
    "README.md",
    ".env.example",
    "test_project/__main__.py",
    "test_project/config.py",
    "test_project/logging_config.py",
    "tests/conftest.py",
    "tests/test_config.py",
    "tests/test_logging.py",
    "tests/test_main.py",
]


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Rendered project without tasks (no git init, no uv sync)."""
    return _generate_project(tmp_path_factory.mktemp("core") / "test-project", skip_tasks=True)


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Project with tasks: git init, uv sync and formatting of the seed code."""
    return _generate_project(tmp_path_factory.mktemp("core-installed") / "test-project")


def _run(project: Path, *command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=project, capture_output=True, text=True, check=False)


# --- Dependencies ---


@pytest.mark.parametrize("package", ["pydantic", "pydantic-settings", "structlog"])
def test_runtime_dependencies(rendered: Path, package: str) -> None:
    dependencies = tomllib.loads((rendered / "pyproject.toml").read_text())["project"][
        "dependencies"
    ]

    assert any(re.fullmatch(rf"{package}>=[\d.]+", dep) for dep in dependencies), dependencies


def test_ruff_keeps_pydantic_annotations_at_runtime(rendered: Path) -> None:
    pyproject: dict[str, Any] = tomllib.loads((rendered / "pyproject.toml").read_text())
    type_checking = pyproject["tool"]["ruff"]["lint"]["flake8-type-checking"]

    assert "pydantic_settings.BaseSettings" in type_checking["runtime-evaluated-base-classes"]


# --- Files ---


def test_core_files(rendered: Path) -> None:
    for path in SEED_FILES:
        assert (rendered / path).is_file(), path


@pytest.mark.parametrize(
    "path", ["test_project/example.py", "tests/test_example", "test_project/logging.py"]
)
def test_removed_files(rendered: Path, path: str) -> None:
    assert not (rendered / path).exists()


def test_env_example_documents_settings(rendered: Path) -> None:
    env_example = (rendered / ".env.example").read_text()
    config = (rendered / "test_project" / "config.py").read_text()

    for variable in ("LOG_LEVEL", "LOG_FORMAT"):
        assert re.search(rf"^{variable}=", env_example, flags=re.MULTILINE), variable
        assert f"{variable.lower()}:" in config


def test_env_file_is_ignored(installed: Path) -> None:
    assert _run(installed, "git", "check-ignore", "-q", ".env").returncode == 0
    assert _run(installed, "git", "check-ignore", "-q", ".env.example").returncode == 1


# --- Seed files ---


def test_seed_files_listed_in_copier_config() -> None:
    patterns = [
        pattern.replace("{{ package_name }}", "test_project")
        for pattern in COPIER_CONFIG["_skip_if_exists"]
    ]

    assert sorted(patterns) == sorted(SEED_FILES)


def test_seed_files_are_not_overwritten(tmp_path: Path) -> None:
    project = _generate_project(tmp_path / "test-project", skip_tasks=True)
    for path in [*SEED_FILES, "Makefile"]:
        (project / path).write_text("# changed by the user\n")

    run_copy(
        str(TEMPLATE_DIR),
        str(project),
        data=BASE_DATA,
        defaults=True,
        overwrite=True,
        unsafe=True,
        vcs_ref="HEAD",
        skip_tasks=True,
    )

    for path in SEED_FILES:
        assert (project / path).read_text() == "# changed by the user\n", path
    assert (project / "Makefile").read_text() != "# changed by the user\n"


# --- Generated code works ---


def test_generated_tests_pass(installed: Path) -> None:
    if shutil.which("uv") is None or shutil.which("make") is None:
        pytest.skip("uv or make not found")

    # The developer's .env must not leak into the tests (conftest.py turns it off).
    env_file = installed / ".env"
    env_file.write_text("LOG_LEVEL=ERROR\nLOG_FORMAT=json\n")
    try:
        result = _run(installed, "make", "test")
    finally:
        env_file.unlink()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Required test coverage" in result.stdout


def test_generated_partial_test_run_passes(installed: Path) -> None:
    """The coverage threshold applies to `make test`, not to a subset of the tests."""
    if shutil.which("uv") is None:
        pytest.skip("uv not found")

    result = _run(installed, "uv", "run", "--frozen", "pytest", "tests/test_config.py")

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "command",
    [("ruff", "format", "--check"), ("ruff", "check"), ("mypy",), ("deptry", ".")],
    ids=["ruff-format", "ruff-check", "mypy", "deptry"],
)
def test_generated_code_passes_lint(installed: Path, command: tuple[str, ...]) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not found")

    result = _run(installed, "uv", "run", "--frozen", *command)

    assert result.returncode == 0, result.stdout + result.stderr


def test_entry_point_logs_json(installed: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not found")

    result = subprocess.run(
        ["uv", "run", "--frozen", "test-project"],
        cwd=installed,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "LOG_LEVEL": "INFO", "LOG_FORMAT": "json"},
    )

    assert result.returncode == 0, result.stderr
    assert '"event": "application started"' in result.stdout
    assert '"logger": "test_project"' in result.stdout


def test_seed_code_is_formatted_for_answers(tmp_path: Path) -> None:
    """The copy task reformats the seed code for `line_length` and long package names."""
    if shutil.which("uv") is None:
        pytest.skip("uv not found")
    project = _generate_project(
        tmp_path / "test-project", project_name="Payments Reconciliation Service", line_length=50
    )

    for command in (("ruff", "format", "--check"), ("ruff", "check"), ("mypy",)):
        result = _run(project, "uv", "run", "--frozen", *command)
        assert result.returncode == 0, result.stdout + result.stderr
