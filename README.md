# Python Packages Project Generator

## TL;DR

```bash
copier copy --trust gh:a1d4r/copier-python-template your-project
```

## Features

In this [Copier](https://copier.readthedocs.io/) template we combine state-of-the-art libraries
and best development practices for Python.

### Development features

- Supports `Python 3.9 - 3.13`
- [`uv`](https://docs.astral.sh/uv/) as a package manager.
- Automatic codestyle with [`ruff formatter`](https://docs.astral.sh/ruff/formatter/)
- Linting with [`ruff`](https://github.com/astral-sh/ruff)
- Type checks with [`mypy`](https://mypy.readthedocs.io), security checks
  with [`safety`](https://github.com/pyupio/safety).
- Dependencies check with [`deptry`](https://deptry.com/)
- Testing with [`pytest`](https://docs.pytest.org/en/latest/) and [`coverage`](https://github.com/nedbat/coveragepy).
- Runtime type checking in tests with [`typeguard`](https://github.com/agronholm/typeguard).
- Ready-to-use [`pre-commit`](https://pre-commit.com/) hooks with code-formatting.
- Ready-to-use [`.editorconfig`](template/.editorconfig), [`.dockerignore`](template/.dockerignore), and [`.gitignore`](template/.gitignore).

### Deployment features

- `GitHub Actions` with linters and tests in
  the [workflow](template/%7B%25%20if%20git_platform%20%3D%3D%20'github'%20%25%7D.github%7B%25%20endif%20%25%7D/workflows/lint-test.yml.jinja).
- `GitLab CI` with linters and tests in
  the [pipeline](template/%7B%25%20if%20git_platform%20%3D%3D%20'gitlab'%20%25%7D.gitlab-ci.yml%7B%25%20endif%20%25%7D.jinja).
- Ready-to-use [`Makefile`](template/Makefile.jinja) with
  formatting, linting, and testing. More details in [Makefile usage](#makefile-usage).
- [Dockerfile](template/Dockerfile.jinja) for your package.
- [docker-compose.yml](template/docker-compose.yml.jinja) for local development in Docker.

## How to use it

### Installation

To begin using the template, install `copier`:

```bash
pip install copier
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

### Input variables

Template generator will ask you to fill some variables.

The input variables, with their default values:

|   **Parameter**    |                   **Default value**                    | **Description**                                                                                              |
|:------------------:|:------------------------------------------------------:|--------------------------------------------------------------------------------------------------------------|
|   `project_name`   |                    `python-project`                    | [Check the availability of possible name](http://ivantomic.com/projects/ospnc/) before creating the project. |
|   `package_name`   |              based on the `project_name`               | Name of the python package with source code                                                                  |
|   `git_platform`   |                        `github`                        | Git platform (GitHub/GitLab)                                                                                 |
|     `username`     |                       `username`                       | User or organization name for Git platform                                                                   |
|   `git_repo_url`   | based on `git_platform`, `project_name` and `username` | URL to the git repository                                                                                    |
|  `python_version`  |                         `3.9`                          | Python version. One of `3.9`, `3.10`, `3.11`, `3.12`, `3.13`. It is used for builds, CI and formatters.      |
|   `line_length`    |                           88                           | The max length per line. Must be between 50 and 300.                                                         |
| `install_pydantic` |                          true                          | If `pydantic` with `mypy` plugin should be installed                                                         |

All input values will be saved in the `.copier-answers.yml` file so that you can update the project later.

### More details

Your project will contain `README.md` file with instructions for development, deployment, etc. You can
read [the project README.md template](template/README.md.jinja) before.

### Initial set up

#### Initialize `uv`

By running `make install`

After you create a project, it will appear in your directory with `git init` and `uv sync` already executed.

#### Initialize `pre-commit`

By running `make pre-commit-install`. Git is already initialized by the template.

### Makefile usage

[`Makefile`](template/Makefile.jinja)
contains a lot of functions
for faster development.

<details>
<summary>1. Download uv</summary>
<p>

To download and install uv run:

```bash
make uv-install
```

</p>
</details>

<details>
<summary>2. Install all dependencies and pre-commit hooks</summary>
<p>

Install requirements:

```bash
make install
```

Pre-commit hooks coulb be installed after `git init` via

```bash
make pre-commit-install
```

</p>
</details>

<details>
<summary>3. Codestyle</summary>
<p>

Automatic formatting uses `ruff` formatter

```bash
make codestyle

# or use synonym
make format
```

Codestyle checks only, without rewriting files:

```bash
make check-codestyle
```

Update all libraries to the latest version using one command

```bash
make update
```

</p>
</details>

<details>
<summary>4. Code security</summary>
<p>

This command identifies security issues with `Safety`

```bash
make check-safety
```

</p>
</details>

<details>
<summary>5. Type checks</summary>
<p>

Run `mypy` static type checker

```bash
make mypy
```

</p>
</details>

<details>
<summary>6. Tests with coverage</summary>
<p>

Run `pytest`

```bash
make test
```

</p>
</details>

<details>
<summary>7. All linters</summary>
<p>

Of course there is a command to ~~rule~~ run all linters in one:

```bash
make lint
```

</p>
</details>

<details>
<summary>8. Docker</summary>
<p>

Run with docker compose

```bash
make docker-up
```

</p>
</details>

<details>
<summary>9. Cleanup</summary>
<p>
Delete cache and build files:

```bash
make cleanup
```

</p>
</details>
