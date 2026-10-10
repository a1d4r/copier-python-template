# Example App

## Installation

1. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/).
   It also installs the Python version pinned in [`.python-version`](.python-version).

2. Clone the repository:

```bash
git clone https://gitlab.com/acme/example-app.git
cd example-app
```

3. Install dependencies and `pre-commit` hooks:

```bash
make install
make pre-commit-install
```

4. Run formatters, linters, and tests. Make sure there are no errors.

```bash
make format lint test
```

## Usage

Run the application locally:

```bash
make run
```

or with Docker Compose:

```bash
make up
```

The entry point is [`example_app/__main__.py`](example_app/__main__.py):
`python -m example_app` and the `example-app` console script run `main()`.

## Configuration

Settings live in [`example_app/config.py`](example_app/config.py)
(`Settings`, a [`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) model).
Values are read from environment variables, then from the `.env` file in the working directory,
then from the defaults. Variable names have no prefix and are case-insensitive;
nested settings use `__` as a delimiter (`DB__URL` sets `settings.db.url`).

For local development copy the example file (`.env` is git-ignored) and edit it:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Minimum log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | `console` | `console` (human-readable) for development, `json` for production |

Use `get_settings()` to access the settings; in tests set variables with
`monkeypatch.setenv` (the fixtures in `tests/conftest.py` reset the cache between tests).

## Logging

[`example_app/logging_config.py`](example_app/logging_config.py) sets up
[`structlog`](https://www.structlog.org/) on top of the standard `logging` module.
`configure_logging()` is called in `main()`; logs go to stdout.

```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
logger.info("user created", user_id=42)
```

Loggers of third-party libraries (`logging.getLogger(...)`) go through the same processors,
so with `LOG_FORMAT=json` every line is one JSON object with `timestamp`, `level`,
`logger` and `event` keys. Bind request-scoped context with
`structlog.contextvars.bind_contextvars(request_id=...)`.

## Docker

The [`Dockerfile`](Dockerfile) pins uv in its first (`uv`) stage and has three build stages:

- `builder` installs the locked runtime dependencies and the project (as a regular,
  non-editable package) into `/app/.venv` with `uv`;
- `production` (`make docker-build`) copies only `/app/.venv` onto `python:3.14-slim-trixie`,
  runs as the non-root user `10001:10001` and logs JSON (`LOG_FORMAT=json`);
- `development` (`make up`) has all dependency groups and an editable install;
  `docker-compose.yml` mounts `example_app/` into it and reads `.env` if it exists.

[`.dockerignore`](.dockerignore) is an allowlist: only `pyproject.toml`, `uv.lock`,
`.python-version` and `example_app/` get into the build context.
When the image needs another file or directory (e.g. `migrations/`), add a `!path` line there,
otherwise it is silently missing from the image.

## CI

[GitLab CI](.gitlab-ci.yml) runs `make lint`, `make codequality`, `make test` (coverage,
JUnit and Code Quality reports in merge requests), `make audit` and builds the production
image (without pushing it) for merge requests, the default branch and tags. The jobs use
the `ghcr.io/astral-sh/uv` image with Python 3.14; the image build needs a runner
that allows Docker-in-Docker (privileged), like the GitLab.com instance runners.

GitLab has no built-in dependency update bot: run `make update` and `make template-check`
periodically, and add a weekly [pipeline schedule](https://docs.gitlab.com/ci/pipelines/schedules/)
to re-run `audit` on the default branch.

`audit` does not block merge requests (a newly published
vulnerability is not caused by the change under review), but it fails on the default branch.

The uv version is pinned in two places, keep them in sync: the `uv` stage in the `Dockerfile`
and `UV_VERSION` in the CI config.

## Development

The [`Makefile`](Makefile) wraps the common `uv` commands.
Run `make` without arguments to list all targets.

| Command | What it does |
|---|---|
| `make install` | Create `.venv` and install the project with all dependency groups |
| `make format` | Apply safe `ruff` fixes and format the code |
| `make lint` | Check `uv.lock`, run `ruff`, `mypy` and `deptry` |
| `make test` | Run `pytest` with coverage, reports go to `reports/` |
| `make audit` | Check locked runtime dependencies with `pip-audit` |
| `make update` | Upgrade all dependencies in `uv.lock` |
| `make docker-build` | Build the production Docker image |
| `make up` / `make down` | Start / stop Docker Compose services |
| `make clean` | Remove caches, reports and build artifacts |

Dev tools (`ruff`, `mypy`, `pytest`, ...) have only lower bounds in `pyproject.toml`;
the exact versions are locked in `uv.lock`. `ruff` selects all rules, so upgrading it
may report new violations: fix them or add the rule to `ignore`.

The Python version comes from the template answers and is used in
`.python-version`, `pyproject.toml`, CI and the `Dockerfile`.
`uv python pin` changes it only locally; to change it everywhere run:

```bash
make template-update COPIER_ARGS="--data python_version=3.13"
```

## Template updates

This project was generated with [`copier-python-template`](https://github.com/a1d4r/copier-python-template).
To pull in template changes (on a clean git tree):

```bash
make template-check    # is a newer template version available?
make template-update   # copier update, then uv lock && uv sync
```

The template runs tasks (`uv lock`), so Copier asks you to trust it: pass
`COPIER_ARGS=--trust` or add the template to `trust` in Copier's
[settings file](https://copier.readthedocs.io/en/stable/settings/).
Conflicts are written inline (`<<<<<<<` markers): resolve them, then run `uv lock && uv sync`.
