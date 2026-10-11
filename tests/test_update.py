"""`copier update` of a generated project.

- A synthetic release: a throwaway copy of this repository gets two tags,
  `v0.0.1` (the current template) and `v0.0.2` (a change to managed and seed
  files). A project generated from `v0.0.1` with tasks and edited by the user
  is updated to `v0.0.2`: template changes land, user changes survive, seed
  files are left alone and `uv.lock` is refreshed by the update task.
- Real releases: a project generated from each of the last tags of this
  repository is updated to the working tree and matches a fresh copy.
"""

from typing import TYPE_CHECKING, Any

import filecmp
import shutil
import subprocess
import tomllib

import pytest
import yaml

from copier import run_copy, run_update

from tests.conftest import BASE_DATA, COPIER_CONFIG, TEMPLATE_DIR

if TYPE_CHECKING:
    from pathlib import Path

# Copier runs git and tasks through plumbum, which leaves a pipe for the garbage
# collector; harmless, but `filterwarnings = error` turns it into a failure.
pytestmark = pytest.mark.filterwarnings(
    "ignore:Exception ignored while finalizing file:pytest.PytestUnraisableExceptionWarning"
)

GIT = ["git", "-c", "user.name=Test", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]

# Files that legitimately differ between an updated project and a fresh copy.
VOLATILE = {".git", ".copier-answers.yml", "uv.lock", ".venv"}
SEED_PATTERNS: list[str] = COPIER_CONFIG["_skip_if_exists"]

NEW_DEPENDENCY = "annotated-types"  # already locked (pydantic needs it), so `uv lock` is cheap
NEW_TARGET = "template-v002:"
NEW_SEED_LINE = "# added to the seed in v0.0.2"
USER_IGNORE = "user-local-dir/"
USER_SEED_LINE = "# the user's own code"


def git(project: Path, *args: str) -> str:
    result = subprocess.run([*GIT, *args], cwd=project, check=True, capture_output=True, text=True)
    return result.stdout


def _commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def _template_snapshot(dest: Path) -> Path:
    """Copy the working tree of the template (tracked and new files) into a new repository."""
    files = git(TEMPLATE_DIR, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    for name in filter(None, files.split("\0")):
        source = TEMPLATE_DIR / name
        if source.is_file():
            (dest / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest / name)
    git(dest, "init", "-q", "--initial-branch=main")
    _commit_all(dest, "template")
    return dest


def _conflicts(project: Path) -> list[str]:
    markers = subprocess.run(
        ["git", "grep", "--untracked", "-lE", "^(<<<<<<<|>>>>>>>)( |$)"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    return markers + [str(path) for path in project.rglob("*.rej")]


def _append(path: Path, text: str) -> None:
    path.write_text(path.read_text() + text)


def _locked_dependencies(project: Path, name: str) -> set[str]:
    lock: dict[str, Any] = tomllib.loads((project / "uv.lock").read_text())
    package = next(package for package in lock["package"] if package["name"] == name)
    return {dependency["name"] for dependency in package.get("dependencies", [])}


@pytest.fixture(scope="module")
def released_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Template repository with tags v0.0.1 (current) and v0.0.2 (managed + seed changes)."""
    repo = _template_snapshot(tmp_path_factory.mktemp("template"))
    git(repo, "tag", "v0.0.1")

    _append(
        repo / "template" / "Makefile.jinja", f"\n.PHONY: template-v002\n{NEW_TARGET}\n\t@true\n"
    )
    pyproject = repo / "template" / "pyproject.toml.jinja"
    pyproject.write_text(
        pyproject.read_text().replace(
            "dependencies = [\n", f'dependencies = [\n    "{NEW_DEPENDENCY}>=0.6.0",\n', 1
        )
    )
    _append(repo / "template" / "{{ package_name }}" / "__main__.py.jinja", f"{NEW_SEED_LINE}\n")
    _commit_all(repo, "release v0.0.2")
    git(repo, "tag", "v0.0.2")
    return repo


@pytest.mark.timeout(600)
def test_update_keeps_user_changes(released_template: Path, tmp_path: Path) -> None:
    project = tmp_path / "test-project"
    run_copy(
        str(released_template),
        str(project),
        data=BASE_DATA,
        defaults=True,
        unsafe=True,
        vcs_ref="v0.0.1",
        quiet=True,
    )
    assert (project / "uv.lock").is_file(), "copy tasks did not run"
    _commit_all(project, "initial")
    # The user edits a managed file and a seed file.
    _append(project / ".gitignore", f"{USER_IGNORE}\n")
    _append(project / "test_project" / "__main__.py", f"{USER_SEED_LINE}\n")
    _commit_all(project, "user changes")

    run_update(str(project), defaults=True, overwrite=True, unsafe=True, quiet=True)

    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    assert answers["_commit"] == "v0.0.2"
    assert not _conflicts(project)
    # Template changes are applied to managed files...
    assert f"\n{NEW_TARGET}\n" in (project / "Makefile").read_text()
    assert f'"{NEW_DEPENDENCY}>=0.6.0"' in (project / "pyproject.toml").read_text()
    # ...the user's changes are kept...
    assert f"\n{USER_IGNORE}\n" in (project / ".gitignore").read_text()
    main = (project / "test_project" / "__main__.py").read_text()
    assert USER_SEED_LINE in main
    # ...and seed files are never overwritten.
    assert NEW_SEED_LINE not in main
    # The update task refreshed uv.lock.
    assert NEW_DEPENDENCY in _locked_dependencies(project, "test-project")
    check = subprocess.run(
        ["uv", "lock", "--check"], cwd=project, capture_output=True, text=True, check=False
    )
    assert check.returncode == 0, check.stderr


# --- Real releases of this repository ---


def _release_tags(limit: int = 3) -> list[str]:
    tags = git(TEMPLATE_DIR, "tag", "--list", "v*", "--sort=-v:refname").split()
    return tags[:limit]


def _differences(left: Path, right: Path, ignore: set[str]) -> list[str]:
    def walk(compared: filecmp.dircmp[str], prefix: str) -> list[str]:
        names = compared.left_only + compared.right_only + compared.diff_files
        found = [prefix + name for name in names]
        for name, sub in compared.subdirs.items():
            found += walk(sub, f"{prefix}{name}/")
        return found

    found = walk(filecmp.dircmp(left, right, ignore=list(VOLATILE)), "")
    return [path for path in found if path not in ignore]


@pytest.mark.parametrize(
    "from_tag",
    _release_tags() or [pytest.param("", marks=pytest.mark.skip(reason="no release tags"))],
)
def test_update_from_release_matches_fresh_copy(tmp_path: Path, from_tag: str) -> None:
    data = {**BASE_DATA, "project_name": "demo-app"}
    project, fresh = tmp_path / "updated", tmp_path / "fresh"
    run_copy(
        str(TEMPLATE_DIR),
        str(project),
        data=data,
        defaults=True,
        vcs_ref=from_tag,
        skip_tasks=True,
        unsafe=True,
        quiet=True,
    )
    git(project, "init", "-q")
    _commit_all(project, "initial")

    run_update(
        str(project),
        data=data,
        defaults=True,
        overwrite=True,
        vcs_ref="HEAD",
        skip_tasks=True,
        unsafe=True,
        quiet=True,
    )
    run_copy(
        str(TEMPLATE_DIR),
        str(fresh),
        data=data,
        defaults=True,
        vcs_ref="HEAD",
        skip_tasks=True,
        unsafe=True,
        quiet=True,
    )

    assert not _conflicts(project)
    # Copier drops answers to questions removed since the release (no migrations needed).
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    questions = {key for key in COPIER_CONFIG if not key.startswith("_")}
    assert set(answers) - {"_commit", "_src_path"} <= questions
    # Seed files that existed in the old release stay as they were.
    tracked = set(git(project, "ls-files").split())
    seeds = {path.replace("{{ package_name }}", "demo_app") for path in SEED_PATTERNS}
    assert _differences(project, fresh, ignore=seeds & tracked) == []
