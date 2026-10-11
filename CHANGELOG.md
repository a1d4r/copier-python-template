# Changelog

All notable changes to the template are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the template follows
[SemVer](https://semver.org/) (pre-1.0: a minor release may require manual steps, see
*Upgrade notes*).

## [Unreleased] — v0.2.0

The template is now a base for Python **applications**: a typed application core, uv packaging
and tooling that `copier update` keeps up to date. Framework-specific modules (web, bots,
workers, databases) are planned for later releases.

### Added

- Application core (seed files, generated once and never overwritten by `copier update`):
  - `<package>/config.py` — `Settings` on `pydantic-settings` (environment variables and `.env`,
    no prefix, `__` for nested settings), cached `get_settings()`;
  - `<package>/logging_config.py` — `structlog` on top of stdlib `logging` (`ProcessorFormatter`):
    console output for development, JSON lines for production (`LOG_FORMAT=json`), third-party
    stdlib loggers in the same format;
  - `<package>/__main__.py` — `main()` for `python -m <package>` and the `<slug>` console script;
  - `.env.example` and tests for the settings, logging and entry point (`tests/conftest.py`
    isolates them from the environment and the developer's `.env`).
- `project_slug` question (kebab-case, derived from `project_name`): distribution, repository
  and directory name; `package_name` is derived from it.
- Packaging with `uv_build` (flat layout, `module-root = ""`); `.python-version` is generated
  and committed.
- Dependency groups `lint`, `test`, `dev` (PEP 735) with lower bounds only.
- `pip-audit` (`make audit`) over the locked runtime dependencies.
- Makefile: `make` prints help; new targets `audit`, `run`, `docker-build`, `up`, `down`,
  `template-check` and `template-update` (`copier update --conflict inline`, stops on conflict
  markers, re-locks `uv.lock`).
- pre-commit: ruff and mypy run from `uv.lock` (`repo: local`), `uv lock --check`,
  `check-merge-conflict --assume-in-merge` for markers left by `copier update`.
- GitHub: `audit` and `docker-build` jobs, coverage table in the job summary, Dependabot for
  GitHub Actions, `uv.lock` and Docker images.
- GitLab CI: `audit` and `docker-build` (Docker-in-Docker) jobs, `workflow:rules`,
  interruptible jobs, uv cache.
- Copier: `_message_after_copy` / `_message_after_update` with next steps; a copy task formats
  the generated code for the chosen `line_length`.
- Template repository: fast render matrix, `copier update` tests across releases,
  `examples/` snapshot (`make examples`), e2e `make install && make lint test` for every Python
  version and GitLab, this changelog.

### Changed

- Copier `9.15.0` or newer is required; undefined template variables fail rendering
  (`jinja2.StrictUndefined`).
- `python_version` is the runtime version and one of `3.12`, `3.13`, `3.14` (default `3.14`);
  it drives `.python-version`, Docker images, CI, ruff `target-version` and mypy.
- `project_name` must not be empty; `package_name` rejects hyphens and allows short names.
- Copier tasks never fail the generation: `git init --initial-branch=main` (unless already inside
  a repository) and `uv sync` run only on `copier copy`, `uv lock` only on `copier update`.
- mypy: no global `ignore_missing_imports`, configured `files`; pytest: native `[tool.pytest]`,
  strict mode, warnings are errors; `make test` requires 80% coverage (`COV_FAIL_UNDER`,
  `__main__.py` omitted), a partial `pytest` run does not; ruff ignores
  rules that break a fresh project on upgrades (`CPY`, `DOC`, opinionated preview rules).
- Makefile: thin `uv` wrappers; `lint` runs `uv lock --check`, `ruff format --check`,
  `ruff check`, `mypy` and `deptry`; `clean` replaces `cleanup` and no longer walks into `.venv`.
- Dockerfile: uv pinned in one `FROM ghcr.io/astral-sh/uv:X.Y.Z AS uv` stage, Debian trixie,
  locked dependencies in a cached layer, the app installed non-editable; the production image
  contains only `.venv`, runs as `10001:10001` and logs JSON; `CMD ["python", "-m", "<package>"]`.
  `main()` exits on `SIGTERM` (Python as PID 1 ignores it otherwise).
  The development stage keeps root for the bind mount.
- `.dockerignore` is an allowlist (`pyproject.toml`, `uv.lock`, `.python-version`, the package).
- `docker-compose.yml`: development stage, `init: true`, optional `.env`.
- GitHub Actions: `permissions: contents: read`, concurrency (cancels superseded pull request
  runs only), actions pinned to SHAs,
  `setup-uv` with cache instead of `setup-python` and a hand-made `.venv` cache, jobs call
  `make` targets.
- GitLab CI: `ghcr.io/astral-sh/uv` image with a pinned `UV_VERSION` instead of
  `pip install uv`, `uv sync --locked`; jobs call `make` targets.
- `audit` does not block pull/merge requests and fails on the default branch.

### Removed

- `install_pydantic` question: `pydantic`, `pydantic-settings` and the mypy plugin are always installed.
- `<package>/example.py` and `tests/test_example/`.
- `typeguard` (and its `tests/conftest.py` import hook) and `safety`.
- Makefile targets `uv-install` (`curl | sh`), `codestyle`, `check-codestyle`, `check-ruff`,
  `check-ruff-github`, `check-ruff-gitlab`, `check-mypy`, `check-mypy-gitlab`, `static-lint`,
  `check-safety`, `check-uv`, `check-deptry`, `check-dependencies`, `docker-up`, `cleanup` and
  the `*-remove` targets.
- GitHub: `irongut/CodeCoverageSummary` and the sticky PR comment.

### Fixed

- Generated README pointed to missing make targets (`uv-download`, `mypy`) and a wrong
  Makefile link; `.editorconfig` glob `[*.{py, pyi}]` never matched `.pyi`.
- `git init` ran on every `copier update`; a failed task (e.g. no `uv`) made Copier delete the
  freshly generated project.
- The production container ran as root; mypy option `warn_untyped_fields` (pydantic v1) was unrecognized.

### Upgrade notes

From `v0.1.0`, on a clean git tree:

1. Install Copier `>=9.15.0` and run `copier update --trust` (or `make template-update
   COPIER_ARGS=--trust` once the new Makefile is in place). `v0.1.0` has tasks too, so the
   update needs trust; trusting the template once in Copier's settings file is described in the
   [README](README.md#updating-your-project).
2. **`python_version`**: `3.9`–`3.11` (the old default was `3.9`) are no longer valid choices.
   An interactive update asks again; with `--defaults` the default `3.14` is used silently.
   Pass the version explicitly, e.g. `--data python_version=3.12`. It is now the runtime version (Docker, CI, `.python-version`),
   not a minimum.
3. **Answers**: `install_pydantic` is dropped from `.copier-answers.yml` automatically.
   The new `project_slug` collapses every run of characters other than letters and digits into
   `-`, while `v0.1.0` only replaced spaces, so `[project] name` may change for a `project_name`
   with punctuation (`_` vs `-` is the same distribution name after normalization). Override it
   with `--data project_slug=<kebab-case name>` if needed.
4. **Seed files are not updated.** `README.md` and `tests/conftest.py` already existed in
   `v0.1.0`, so `copier update` keeps the old versions:
   - the old `tests/conftest.py` imports `typeguard`, which is no longer installed — replace it
     with the new one (render a fresh project with the same answers, or take it from
     [`examples/`](examples/github/tests/conftest.py)), otherwise `make test` fails;
   - update `README.md` by hand (make targets were renamed), see
     [`examples/github/README.md`](examples/github/README.md).
   The new seed files (`config.py`, `logging_config.py`, `__main__.py`, their tests,
   `.env.example`) are added.
5. `example.py` and `tests/test_example/` are deleted by the update if you did not change them;
   otherwise delete them and their imports yourself.
6. **Lockfile**: `uv lock && uv sync`. If `uv.lock` has conflict markers, do not merge it by hand:
   `git checkout HEAD -- uv.lock && uv lock`.
7. **Make targets** were renamed (`check-*` → `lint`, `codestyle` → `format`, `cleanup` → `clean`,
   `check-safety` → `audit`): update scripts that call the old names.
8. **CI**: job names changed (GitHub: `lint`, `test`, `audit`, `docker-build`; GitLab: `lint`,
   `codequality`, `test`, `audit`, `docker-build`) — update required status checks / branch
   protection rules.
9. Run `make lint test`, then commit.

## [v0.1.0]

First tagged release.

[Unreleased]: https://github.com/a1d4r/copier-python-template/compare/v0.1.0...HEAD
[v0.1.0]: https://github.com/a1d4r/copier-python-template/releases/tag/v0.1.0
