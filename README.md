# Python Packages Project Generator

## TL;DR

```bash
copier copy --trust gh:a1d4r/copier-python-template your-project
```

## Features

In this [Copier](https://copier.readthedocs.io/) template we combine state-of-the-art libraries
and best development practices for Python.

### Application core

- Configuration with [`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/):
  `Settings` in `<package>/config.py`, read from environment variables and `.env`
  (documented in `.env.example`).
- Logging with [`structlog`](https://www.structlog.org/) on top of the standard `logging` module:
  human-readable console output for development, JSON lines for production (`LOG_FORMAT=json`);
  logs of third-party libraries use the same format.
- Entry point `<package>/__main__.py` (`python -m <package>` and a console script) with tests
  for the configuration, logging and entry point.

The application code (`__main__.py`, `config.py`, `logging_config.py`, their tests,
`tests/conftest.py`, `README.md` and `.env.example`) is generated once: `copier update`
never overwrites these files and keeps updating only the tooling
(`pyproject.toml` tool settings, CI, Docker, `Makefile`, pre-commit).

### Development features

- Generated projects run on `Python 3.12`, `3.13` or `3.14` (default), pinned in `.python-version`
- [`uv`](https://docs.astral.sh/uv/) as a package manager; the app is packaged with `uv_build`
  (flat layout) and exposes a console script and `python -m <package>`.
- Dev dependencies in [PEP 735](https://peps.python.org/pep-0735/) groups (`lint`, `test`, `dev`)
  with lower bounds only; exact versions live in `uv.lock`.
- Automatic codestyle with [`ruff formatter`](https://docs.astral.sh/ruff/formatter/)
- Linting with [`ruff`](https://github.com/astral-sh/ruff) (all rules selected)
- Type checks with [`mypy`](https://mypy.readthedocs.io) in strict mode with the pydantic plugin.
- Vulnerability checks of locked dependencies with [`pip-audit`](https://github.com/pypa/pip-audit).
- Dependencies check with [`deptry`](https://deptry.com/)
- Testing with [`pytest`](https://docs.pytest.org/en/latest/) and [`coverage`](https://github.com/nedbat/coveragepy).
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
- Ready-to-use [`Makefile`](template/Makefile.jinja) with
  formatting, linting, and testing. More details in [Makefile usage](#makefile-usage).
- Multi-stage [Dockerfile](template/Dockerfile.jinja): the production image contains only
  Python and the virtual environment with the app installed as a package, runs as a non-root
  user (`10001`) and logs JSON; the build context is limited by an allowlist
  [`.dockerignore`](template/.dockerignore.jinja).
- [docker-compose.yml](template/docker-compose.yml.jinja) for local development in Docker
  (development stage, `init: true`, optional `.env`).

## How to use it

### Installation

To begin using the template, install `copier` (version `9.15.0` or newer is required):

```bash
uv tool install copier
# or
pip install "copier>=9.15"
```

then go to a directory where you want to create your project and run:

```bash
copier copy --trust gh:a1d4r/copier-python-template your-project
```

### Updating your project

When the template evolves, you can update your project to the latest version:

```bash
cd your-project
copier update --trust
```

Copier will perform a 3-way merge, preserving your local changes while applying template updates.

> **Versioning.** The template follows SemVer and is currently in pre-1.0 (`0.x.y`).
> Until `v1.0.0`, minor bumps may include breaking changes; patches are backwards-compatible fixes.
> `copier update` always targets the latest tag.

### Input variables

Template generator will ask you to fill some variables.

The input variables, with their default values:

| **Parameter**    | **Default value**                                      | **Description**                                                                                                              |
|:----------------:|:------------------------------------------------------:|------------------------------------------------------------------------------------------------------------------------------|
| `project_name`   | `python-project`                                       | Human-readable project name. [Check the availability of possible name](http://ivantomic.com/projects/ospnc/) before creating the project. |
| `project_slug`   | based on the `project_name`                            | Kebab-case slug used as the distribution, repository and directory name (e.g. `My App!` → `my-app`).                         |
| `package_name`   | based on the `project_slug`                            | Name of the Python package with source code (e.g. `my_app`).                                                                 |
| `git_platform`   | `github`                                               | Git platform (GitHub/GitLab)                                                                                                 |
| `username`       | `username`                                             | User or organization name for Git platform                                                                                   |
| `git_repo_url`   | based on `git_platform`, `username` and `project_slug` | URL to the git repository                                                                                                    |
| `python_version` | `3.14`                                                 | Python version the application runs on: one of `3.12`, `3.13`, `3.14`. Used for Docker images, CI and type checking.         |
| `line_length`    | 88                                                     | The max length per line. Must be between 50 and 300.                                                                         |

All input values will be saved in the `.copier-answers.yml` file so that you can update the project later.

### More details

Your project will contain `README.md` file with instructions for development, deployment, etc. You can
read [the project README.md template](template/README.md.jinja) before.

### Initial set up

#### Initialize `uv`

By running `make install`

After you create a project, it will appear in your directory with `git init` (branch `main`) and
`uv sync` already executed; the generated code is formatted with `ruff` for the chosen `line_length`. These tasks never abort the generation: if `uv` is not installed, Copier prints a
warning and you can run `make install` later. On `copier update` the template runs `uv lock` to refresh the
lockfile; follow the instructions printed after the update to resolve conflicts.

#### Initialize `pre-commit`

By running `make pre-commit-install`. Git is already initialized by the template.

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
