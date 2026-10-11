# Python Application Project Generator

A [Copier](https://copier.readthedocs.io/) template for Python **applications** (services, bots,
workers, CLIs — not libraries published to PyPI): a small typed application core, strict
tooling around it, Docker and CI, and updates of all that tooling with `copier update`.

## TL;DR

```bash
uv tool install copier
copier copy --trust gh:a1d4r/copier-python-template your-project
cd your-project && make lint test
```

See [`examples/`](examples/) for what a generated project looks like.

## Features

### Application core

- Configuration with [`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/):
  `Settings` in `<package>/config.py`, read from environment variables and `.env`
  (documented in `.env.example`).
- Logging with [`structlog`](https://www.structlog.org/) on top of the standard `logging` module:
  human-readable console output for development, JSON lines for production (`LOG_FORMAT=json`,
  the default in the production Docker image); logs of third-party libraries use the same format.
- Entry point `<package>/__main__.py` (`python -m <package>` and a console script) with tests
  for the configuration, logging and entry point.

The application code (`__main__.py`, `config.py`, `logging_config.py`, their tests,
`tests/conftest.py`, `README.md` and `.env.example`) is generated once: `copier update`
never overwrites these files and keeps updating only the tooling
(`pyproject.toml` tool settings, CI, Docker, `Makefile`, pre-commit).

### Development features

- Generated projects run on `Python 3.12`, `3.13` or `3.14` (default), pinned in `.python-version`.
- [`uv`](https://docs.astral.sh/uv/) as a package manager; the app is packaged with
  [`uv_build`](https://docs.astral.sh/uv/concepts/build-backend/) (flat layout) and exposes
  a console script and `python -m <package>`.
- Dev dependencies in [PEP 735](https://peps.python.org/pep-0735/) groups (`lint`, `test`, `dev`)
  with lower bounds only; exact versions live in `uv.lock`.
- Formatting and linting with [`ruff`](https://docs.astral.sh/ruff/) (all rules selected).
- Type checks with [`mypy`](https://mypy.readthedocs.io) in strict mode with the pydantic plugin.
- Unused and missing dependencies are found by [`deptry`](https://deptry.com/).
- Vulnerability checks of the locked runtime dependencies with [`pip-audit`](https://github.com/pypa/pip-audit).
- Testing with [`pytest`](https://docs.pytest.org/en/latest/) (strict mode, warnings are errors)
  and coverage with `fail_under`.
- Ready-to-use [`pre-commit`](https://pre-commit.com/) hooks: ruff and mypy run from `uv.lock`,
  `uv lock --check`, and inline conflicts left by `copier update` are caught.
- Ready-to-use [`.editorconfig`](template/.editorconfig), [`.dockerignore`](template/.dockerignore.jinja), and [`.gitignore`](template/.gitignore).

### Deployment features

- `GitHub Actions` [workflow](template/%7B%25%20if%20git_platform%20%3D%3D%20'github'%20%25%7D.github%7B%25%20endif%20%25%7D/workflows/lint-test.yml.jinja):
  `lint`, `test` (coverage in the job summary), `audit` and `docker-build` jobs,
  read-only permissions, actions pinned to commit SHAs, `setup-uv` with cache;
  [Dependabot](template/%7B%25%20if%20git_platform%20%3D%3D%20'github'%20%25%7D.github%7B%25%20endif%20%25%7D/dependabot.yml)
  for GitHub Actions, `uv.lock` and Docker images.
- `GitLab CI` [pipeline](template/%7B%25%20if%20git_platform%20%3D%3D%20'gitlab'%20%25%7D.gitlab-ci.yml%7B%25%20endif%20%25%7D.jinja)
  on the `ghcr.io/astral-sh/uv` image: `lint`, `codequality`, `test` (coverage, JUnit and
  Code Quality reports), `audit` and `docker-build` (Docker-in-Docker) jobs,
  interruptible, for merge requests, the default branch and tags.
- `audit` (`pip-audit`) does not block pull/merge requests and fails on the default branch.
- Multi-stage [Dockerfile](template/Dockerfile.jinja): the production image contains only
  Python and the virtual environment with the app installed as a package, runs as a non-root
  user (`10001`) and logs JSON; the build context is limited by an allowlist
  [`.dockerignore`](template/.dockerignore.jinja).
- [docker-compose.yml](template/docker-compose.yml.jinja) for local development in Docker
  (development stage, `init: true`, optional `.env`).
- A [`Makefile`](template/Makefile.jinja) of thin `uv` wrappers; `make` lists the targets
  (see [Makefile usage](#makefile-usage)).

## How to use it

### Installation

Install `copier` (version `9.15.0` or newer is required) and [`uv`](https://docs.astral.sh/uv/getting-started/installation/):

```bash
uv tool install copier
# or
pip install "copier>=9.15"
```

then go to a directory where you want to create your project and run:

```bash
copier copy --trust gh:a1d4r/copier-python-template your-project
```

`--trust` is needed because the template runs tasks (see [below](#what-happens-on-copy-and-update)).
Generate projects from the `gh:` (or `https://`) URL, not from a local clone: the source is
saved as `_src_path` in `.copier-answers.yml`, and `copier update` pulls new versions from it.

### Input variables

Copier asks for the following values (defaults in brackets are computed from earlier answers):

| **Parameter**    | **Default value**                                      | **Description**                                                                                                              |
|:----------------:|:------------------------------------------------------:|------------------------------------------------------------------------------------------------------------------------------|
| `project_name`   | `python-project`                                       | Human-readable project name, must not be empty.                                                                              |
| `project_slug`   | based on the `project_name`                            | Kebab-case slug used as the distribution, repository and directory name (e.g. `My App!` → `my-app`).                         |
| `package_name`   | based on the `project_slug`                            | Name of the Python package with source code (e.g. `my_app`).                                                                 |
| `git_platform`   | `github`                                               | Git platform: `github` (GitHub Actions, Dependabot) or `gitlab` (GitLab CI).                                                 |
| `username`       | `username`                                             | User or organization name on the git platform.                                                                               |
| `git_repo_url`   | based on `git_platform`, `username` and `project_slug` | URL of the git repository.                                                                                                   |
| `python_version` | `3.14`                                                 | Python version the application runs on: one of `3.12`, `3.13`, `3.14`. Used in `.python-version`, Docker images, CI and type checking. |
| `line_length`    | `88`                                                   | The max length per line. Must be between 50 and 300.                                                                         |

All answers are saved in `.copier-answers.yml` so that `copier update` can replay them.
Pass answers non-interactively with `--data key=value` (or `--defaults` to accept all defaults).

### What happens on copy and update

`copier copy` runs these tasks in the new project (they never abort the generation: if a tool is
missing, Copier prints a warning and you can run `make install` later):

1. `git init --initial-branch=main`, unless the destination is already inside a git repository;
2. `uv sync`: creates `.venv` and `uv.lock`;
3. `ruff check --fix-only` and `ruff format`, so the generated code fits the chosen `line_length`.

Then make the first commit — `copier update` needs a clean git tree:

```bash
cd your-project
make pre-commit-install
make lint test
git add -A && git commit -m "Initial commit from copier-python-template"
```

`copier update` runs `uv lock` to refresh the lockfile after `pyproject.toml` changes.

### Updating your project

When the template evolves, update the project on a clean git tree:

```bash
make template-check    # is a newer template version available?
make template-update   # copier update --conflict inline, then uv lock && uv sync
```

Copier performs a 3-way merge: template changes are applied, your local changes are kept,
and conflicts are written inline (`<<<<<<<` markers). `make template-update` stops when
markers are left; resolve them, then run `uv lock && uv sync` and `make lint test`.
If `uv.lock` has conflicts, do not edit it by hand: `git checkout HEAD -- uv.lock && uv lock`.

- **Trust.** Because of the tasks, Copier refuses to update without trusting the template.
  Pass `COPIER_ARGS=--trust` to `make template-update`, or trust it once in Copier's
  [settings file](https://copier.readthedocs.io/en/stable/settings/)
  (`~/.config/copier/settings.yml` on Linux, `~/Library/Application Support/copier/settings.yml`
  on macOS, or the path in `COPIER_SETTINGS_PATH`):

  ```yaml
  trust:
    - gh:a1d4r/copier-python-template
  ```

- **Source.** `copier update` fetches the template from `_src_path` in `.copier-answers.yml`.
  It must be a remote URL (`gh:a1d4r/copier-python-template`); a project generated from a local
  clone is updated from that clone, which is usually stale or missing on other machines.
  In that case, set `_src_path: gh:a1d4r/copier-python-template` in `.copier-answers.yml`
  and commit it before the update.
- **Changing answers.** `make template-update COPIER_ARGS="--data python_version=3.13"`.
- **Versions.** `copier update` targets the latest release tag; read the
  [changelog](CHANGELOG.md) (especially *Upgrade notes*) before updating across a minor version.

> **Versioning.** The template follows SemVer and is currently in pre-1.0 (`0.x.y`).
> Until `v1.0.0`, minor bumps may include breaking changes; patches are backwards-compatible fixes.

### More details

Your project will contain `README.md` file with instructions for development, deployment, etc. You can
read [the project README.md template](template/README.md.jinja) before.

### Makefile usage

The generated [`Makefile`](template/Makefile.jinja) is a set of thin wrappers around `uv`.
Run `make` without arguments to list all targets.

| Command | What it does |
|---|---|
| `make install` | Create `.venv` and install the project with all dependency groups |
| `make pre-commit-install` | Install git pre-commit hooks |
| `make format` | Apply safe `ruff` fixes and format the code |
| `make lint` | `uv lock --check`, `ruff format --check`, `ruff check`, `mypy`, `deptry` |
| `make test` | `pytest` with coverage (`fail_under`), reports go to `reports/` |
| `make audit` | `pip-audit` over `uv export --locked` (runtime dependencies) |
| `make run` | Run the application (`python -m <package>`) |
| `make update` | Upgrade all dependencies in `uv.lock` |
| `make docker-build` | Build the production Docker image |
| `make up` / `make down` | Start / stop Docker Compose services |
| `make clean` | Remove caches, reports and build artifacts |
| `make template-check` | Check whether a newer template version is available |
| `make template-update` | `copier update --conflict inline`, check for conflict markers, then `uv lock && uv sync` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how the template is tested and released, and
[CHANGELOG.md](CHANGELOG.md) for the changes between versions.
