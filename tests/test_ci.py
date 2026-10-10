"""CI of the generated project: GitHub Actions, Dependabot, GitLab CI."""

from typing import TYPE_CHECKING, Any

import re
import shutil
import subprocess

import pytest
import yaml

from tests.conftest import _generate_project, dockerfile_uv_version

if TYPE_CHECKING:
    from pathlib import Path

WORKFLOW = ".github/workflows/lint-test.yml"
SHA_PIN = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}  # v\d+\.\d+\.\d+$")


def _render(tmp_path_factory: pytest.TempPathFactory, platform: str, **data: Any) -> Path:
    return _generate_project(
        tmp_path_factory.mktemp(platform) / "test-project",
        skip_tasks=True,
        git_platform=platform,
        **data,
    )


@pytest.fixture(scope="module")
def github(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _render(tmp_path_factory, "github")


@pytest.fixture(scope="module")
def gitlab(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _render(tmp_path_factory, "gitlab")


def _yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text())


def _make_targets(project: Path) -> set[str]:
    return set(re.findall(r"^([a-zA-Z0-9_-]+):", (project / "Makefile").read_text(), re.MULTILINE))


# --- GitHub Actions ---


def test_github_workflow_permissions(github: Path) -> None:
    workflow = _yaml(github / WORKFLOW)

    assert workflow["permissions"] == {"contents": "read"}
    assert all("permissions" not in job for job in workflow["jobs"].values())
    assert workflow["concurrency"]["cancel-in-progress"] is True


def test_github_workflow_jobs(github: Path) -> None:
    jobs = _yaml(github / WORKFLOW)["jobs"]

    assert set(jobs) == {"lint", "test", "audit", "docker-build"}
    runs = {name: [step.get("run", "") for step in job["steps"]] for name, job in jobs.items()}
    assert "make lint" in runs["lint"]
    assert "make test" in runs["test"]
    assert any("$GITHUB_STEP_SUMMARY" in run for run in runs["test"])
    assert "make audit" in runs["audit"]
    assert "uv sync --locked" in runs["lint"]
    assert "uv sync --locked" in runs["test"]

    (build,) = (
        s for s in jobs["docker-build"]["steps"] if "build-push-action" in s.get("uses", "")
    )
    assert build["with"]["target"] == "production"
    assert build["with"]["push"] is False

    # audit informs on pull requests and fails on main.
    assert jobs["audit"]["continue-on-error"] == "${{ github.event_name == 'pull_request' }}"


def test_github_actions_pinned_by_sha(github: Path) -> None:
    lines = [
        line.strip().removeprefix("- ").removeprefix("uses: ")
        for line in (github / WORKFLOW).read_text().splitlines()
        if "uses:" in line
    ]

    assert lines
    for line in lines:
        assert SHA_PIN.match(line), f"not pinned to a commit SHA with a version comment: {line}"


def test_github_workflow_hardening(github: Path) -> None:
    workflow = (github / WORKFLOW).read_text()
    jobs = _yaml(github / WORKFLOW)["jobs"]

    for job in jobs.values():
        checkout = job["steps"][0]
        assert checkout["uses"].startswith("actions/checkout@")
        assert checkout["with"]["persist-credentials"] is False
    for removed in ("setup-python", "actions/cache", "CodeCoverageSummary", "sticky-pull-request"):
        assert removed not in workflow


def test_github_uv_version_matches_dockerfile(github: Path) -> None:
    workflow = _yaml(github / WORKFLOW)
    setup_uv = [
        step
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if step.get("uses", "").startswith("astral-sh/setup-uv@")
    ]

    assert workflow["env"]["UV_VERSION"] == dockerfile_uv_version(github)
    assert len(setup_uv) == 3
    for step in setup_uv:
        assert step["with"] == {"version": "${{ env.UV_VERSION }}", "enable-cache": True}


def test_dependabot_only_for_github(github: Path, gitlab: Path) -> None:
    config = _yaml(github / ".github" / "dependabot.yml")

    assert config["version"] == 2
    ecosystems = {update["package-ecosystem"] for update in config["updates"]}
    assert ecosystems == {"github-actions", "uv", "docker"}
    for update in config["updates"]:
        assert update["schedule"]["interval"] == "weekly"
    assert not (gitlab / ".github").exists()


def test_github_workflow_static_analysis(github: Path) -> None:
    for tool in ("zizmor", "actionlint"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} not found")

    zizmor = subprocess.run(
        ["zizmor", "--offline", "--persona=pedantic", "--no-progress", ".github"],
        cwd=github,
        capture_output=True,
        text=True,
        check=False,
    )
    assert zizmor.returncode == 0, zizmor.stdout + zizmor.stderr

    actionlint = subprocess.run(
        ["actionlint", WORKFLOW], cwd=github, capture_output=True, text=True, check=False
    )
    assert actionlint.returncode == 0, actionlint.stdout + actionlint.stderr


# --- GitLab CI ---


def test_gitlab_pipeline_structure(gitlab: Path) -> None:
    ci = _yaml(gitlab / ".gitlab-ci.yml")

    assert ci["stages"] == ["lint", "test", "audit", "build"]
    assert ci["default"]["interruptible"] is True
    assert ci["default"]["image"] == "ghcr.io/astral-sh/uv:${UV_VERSION}-python3.14-trixie-slim"
    assert ci["variables"]["UV_VERSION"] == dockerfile_uv_version(gitlab)
    assert ci["variables"]["UV_CACHE_DIR"] == ".uv-cache"

    rules = [rule["if"] for rule in ci["workflow"]["rules"]]
    assert '$CI_PIPELINE_SOURCE == "merge_request_event"' in rules
    assert "$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH" in rules
    assert "$CI_COMMIT_TAG" in rules


def test_gitlab_jobs_call_make_targets(gitlab: Path) -> None:
    ci = _yaml(gitlab / ".gitlab-ci.yml")
    jobs = {name: job for name, job in ci.items() if isinstance(job, dict) and "script" in job}

    assert set(jobs) == {"lint", "codequality", "test", "audit", "docker-build"}
    targets = _make_targets(gitlab)
    for name in ("lint", "codequality", "test", "audit"):
        target = jobs[name]["script"].removeprefix("make ")
        assert target in targets, f"{name}: `make {target}` is not a Makefile target"

    assert "uv sync --locked" in ci[".uv"]["before_script"]
    text = (gitlab / ".gitlab-ci.yml").read_text()
    assert "safety" not in text
    assert "pip install" not in text


def test_gitlab_audit_does_not_block_merge_requests(gitlab: Path) -> None:
    rules = _yaml(gitlab / ".gitlab-ci.yml")["audit"]["rules"]

    assert rules[0] == {"if": '$CI_PIPELINE_SOURCE == "merge_request_event"', "allow_failure": True}
    assert rules[-1] == {"when": "on_success"}


def test_gitlab_docker_build(gitlab: Path) -> None:
    job = _yaml(gitlab / ".gitlab-ci.yml")["docker-build"]

    (command,) = job["script"]
    assert "--target production" in command
    assert "push" not in command


def test_gitlab_image_python_version(tmp_path_factory: pytest.TempPathFactory) -> None:
    project = _render(tmp_path_factory, "gitlab", python_version="3.12")
    ci = _yaml(project / ".gitlab-ci.yml")

    assert ci["default"]["image"].endswith("-python3.12-trixie-slim")
