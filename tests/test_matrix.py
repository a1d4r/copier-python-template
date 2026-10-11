"""Fast render matrix: named answer combinations, rendered without tasks or network.

Every combination is rendered once per module; the checks only read files, so the
whole matrix takes a few seconds. Add a combination when a new answer changes the
output (a new platform, a name edge case, ...) instead of a cartesian product.
"""

from typing import TYPE_CHECKING, Any

import re
import tomllib

import pytest
import yaml

from tests.conftest import _generate_project

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# id -> answers on top of BASE_DATA (tests/conftest.py).
COMBINATIONS: dict[str, dict[str, Any]] = {
    "github-defaults": {},
    "gitlab-defaults": {"git_platform": "gitlab"},
    "github-py312-spaces": {"python_version": "3.12", "project_name": "My Cool App"},
    "gitlab-py312-long-name": {
        "git_platform": "gitlab",
        "python_version": "3.12",
        "project_name": "Payments-Reconciliation Service v2",
        "line_length": 79,
    },
    "github-py313-custom-names": {
        "python_version": "3.13",
        "project_name": "ACME Billing",
        "project_slug": "acme-billing-api",
        "package_name": "billing",
        "username": "Acme-Corp",
        "line_length": 120,
    },
    "gitlab-py314-max-line": {
        "git_platform": "gitlab",
        "project_name": "x",
        "username": "group",
        "line_length": 300,
    },
}

# Jinja syntax that must not survive rendering. GitHub Actions expressions
# (`${{ ... }}`) are legitimate output of the workflow template.
UNRENDERED = re.compile(r"(?<!\$)\{\{|\{%|%\}|\{#")

ALWAYS = [
    ".copier-answers.yml",
    ".dockerignore",
    ".editorconfig",
    ".env.example",
    ".gitignore",
    ".pre-commit-config.yaml",
    ".python-version",
    "Dockerfile",
    "Makefile",
    "README.md",
    "docker-compose.yml",
    "pyproject.toml",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/test_config.py",
    "tests/test_logging.py",
    "tests/test_main.py",
]
PACKAGE_FILES = ["__init__.py", "__main__.py", "config.py", "logging_config.py"]
GITHUB_ONLY = [".github/workflows/lint-test.yml", ".github/dependabot.yml"]
GITLAB_ONLY = [".gitlab-ci.yml"]


@pytest.fixture(scope="module", params=list(COMBINATIONS), ids=list(COMBINATIONS))
def combo(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    name: str = request.param
    return _generate_project(
        tmp_path_factory.mktemp(name) / "project", skip_tasks=True, **COMBINATIONS[name]
    )


def _answers(project: Path) -> dict[str, Any]:
    answers: dict[str, Any] = yaml.safe_load((project / ".copier-answers.yml").read_text())
    return answers


def _files(project: Path) -> Iterator[Path]:
    return (path for path in sorted(project.rglob("*")) if path.is_file())


def _make_targets(project: Path) -> set[str]:
    makefile = (project / "Makefile").read_text()
    return set(re.findall(r"^([A-Za-z0-9_-]+):", makefile, flags=re.MULTILINE))


# --- Structure ---


def test_expected_files(combo: Path) -> None:
    answers = _answers(combo)
    package = answers["package_name"]
    github = answers["git_platform"] == "github"
    expected = ALWAYS + [f"{package}/{name}" for name in PACKAGE_FILES]
    expected += GITHUB_ONLY if github else GITLAB_ONLY
    missing = [path for path in expected if not (combo / path).is_file()]

    assert not missing, missing
    for path in GITLAB_ONLY if github else [".github"]:
        assert not (combo / path).exists(), path


def test_no_unrendered_jinja(combo: Path) -> None:
    leftovers = [
        f"{path.relative_to(combo)}:{number}: {line.strip()}"
        for path in _files(combo)
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if UNRENDERED.search(line)
    ]

    assert not leftovers, "\n".join(leftovers)
    assert not [path for path in _files(combo) if ".jinja" in path.name or "{" in str(path)]


# --- Config files parse ---


def test_pyproject_parses(combo: Path) -> None:
    answers = _answers(combo)
    pyproject = tomllib.loads((combo / "pyproject.toml").read_text())

    assert pyproject["project"]["name"] == answers["project_slug"]
    assert pyproject["project"]["requires-python"] == f">={answers['python_version']}"
    assert pyproject["project"]["scripts"] == {
        answers["project_slug"]: f"{answers['package_name']}.__main__:main"
    }
    assert pyproject["tool"]["uv"]["build-backend"]["module-name"] == answers["package_name"]
    assert pyproject["tool"]["ruff"]["line-length"] == answers["line_length"]


def test_yaml_files_parse(combo: Path) -> None:
    paths = [
        path
        for path in _files(combo)
        if path.suffix in {".yml", ".yaml"} or path.name == ".gitlab-ci.yml"
    ]

    assert paths
    for path in paths:
        assert yaml.safe_load(path.read_text()) is not None, path


# --- Names and versions are consistent ---


def test_python_version_file(combo: Path) -> None:
    assert (combo / ".python-version").read_text() == f"{_answers(combo)['python_version']}\n"


def test_names_consistent(combo: Path) -> None:
    answers = _answers(combo)
    package, slug = answers["package_name"], answers["project_slug"]
    dockerfile = (combo / "Dockerfile").read_text()
    readme = (combo / "README.md").read_text()
    makefile = (combo / "Makefile").read_text()

    assert f'CMD ["python", "-m", "{package}"]' in dockerfile
    assert f"FROM python:{answers['python_version']}-slim-trixie AS production" in dockerfile
    assert f"!{package}\n" in (combo / ".dockerignore").read_text()
    assert f"PACKAGE := {package}\n" in makefile
    assert f"IMAGE ?= {slug}\n" in makefile
    assert f"cd {slug}\n" in readme
    assert f"git clone {answers['git_repo_url']}.git" in readme
    assert f"`python -m {package}`" in readme
    assert answers["git_repo_url"] == (
        f"https://{answers['git_platform']}.com/{answers['username'].lower()}/{slug}"
    )


def test_readme_make_targets_exist(combo: Path) -> None:
    readme = (combo / "README.md").read_text()

    commands = re.findall(r"^make ([^#\n]+)", readme, flags=re.MULTILINE)
    commands += re.findall(r"`make ([^`]+)`", readme)
    used = {
        word
        for command in commands
        for word in command.split()
        if re.fullmatch(r"[a-z][a-z0-9-]*", word)
    }

    assert used, "README does not mention any make targets"
    unknown = used - _make_targets(combo)
    assert not unknown, f"README mentions unknown make targets: {sorted(unknown)}"
