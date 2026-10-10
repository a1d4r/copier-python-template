"""Docker files of the generated project: Dockerfile, .dockerignore, compose."""

from typing import TYPE_CHECKING, Any

import re
import subprocess

import pytest
import yaml

from tests.conftest import _generate_project, check_tool, dockerfile_uv_version

if TYPE_CHECKING:
    from pathlib import Path


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


def _yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text())


def _stages(dockerfile: str) -> dict[str, str]:
    """Dockerfile body of every named stage."""
    parts = re.split(r"^FROM \S+ AS (\w+)$", dockerfile, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


# --- Docker ---


@pytest.mark.parametrize("platform", ["github", "gitlab"])
def test_dockerfile_stages(tmp_path_factory: pytest.TempPathFactory, platform: str) -> None:
    project = _render(tmp_path_factory, platform)
    dockerfile = (project / "Dockerfile").read_text()
    stages = _stages(dockerfile)

    assert dockerfile.startswith("# syntax=docker/dockerfile:1\n")
    assert list(stages) == ["uv", "builder", "development", "production"]
    dockerfile_uv_version(project)

    builder = stages["builder"]
    assert "uv sync --locked --no-dev --no-install-project" in builder
    assert "uv sync --locked --no-dev --no-editable" in builder
    assert "--mount=type=cache,target=/root/.cache/uv" in builder

    production = stages["production"]
    assert "COPY --from=builder /app/.venv /app/.venv" in production
    assert "COPY . " not in production
    assert "--from=uv" not in production
    assert "uv sync" not in production
    assert re.search(r"^USER 10001:10001$", production, re.MULTILINE)
    assert "PYTHONFAULTHANDLER=1" in production
    assert "LOG_FORMAT=json" in production
    assert production.rstrip().endswith('CMD ["python", "-m", "test_project"]')

    # Sources are bind-mounted into the development stage: no fixed non-root user.
    assert "USER" not in stages["development"]


def test_dockerfile_python_version(tmp_path_factory: pytest.TempPathFactory) -> None:
    project = _render(tmp_path_factory, "github", python_version="3.12")
    dockerfile = (project / "Dockerfile").read_text()

    assert set(re.findall(r"^FROM python:(\S+) AS", dockerfile, re.MULTILINE)) == {
        "3.12-slim-trixie"
    }


def test_dockerignore_is_allowlist(github: Path) -> None:
    lines = [
        line
        for line in (github / ".dockerignore").read_text().splitlines()
        if line and not line.startswith("#")
    ]

    assert lines[0] == "*"
    allowed = [line.removeprefix("!") for line in lines if line.startswith("!")]
    assert set(allowed) == {"pyproject.toml", "uv.lock", ".python-version", "test_project"}
    for path in set(allowed) - {"uv.lock"}:  # uv.lock is created by the copy task
        assert (github / path).exists(), f".dockerignore allows a missing path: {path}"


def test_compose(github: Path) -> None:
    compose = _yaml(github / "docker-compose.yml")

    assert "version" not in compose
    app = compose["services"]["app"]
    assert app["build"]["target"] == "development"
    assert app["init"] is True
    assert app["env_file"] == [{"path": ".env", "required": False}]
    assert app["volumes"] == ["./test_project:/app/test_project"]


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(600)
def test_docker_production_image_runs(github_project: Path) -> None:
    check_tool("docker")
    image = "copier-python-template-e2e:production"

    build = subprocess.run(
        ["docker", "build", "--target", "production", "--tag", image, "."],
        cwd=github_project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stdout + build.stderr

    run = subprocess.run(
        ["docker", "run", "--rm", image], capture_output=True, text=True, check=False
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert '"event": "application started"' in run.stdout
