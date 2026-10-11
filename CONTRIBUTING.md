# Contributing

## Development

```bash
make install             # uv sync
make pre-commit-install
make lint test           # ruff, mypy and the template tests without Docker
make examples            # after changing template/: re-render examples/ and commit it
```

### Template tests

- `tests/test_matrix.py` renders named answer combinations without tasks or network and
  checks the structure, leftover Jinja syntax, parseable TOML/YAML and consistent names.
  Add a combination when a new answer changes the output.
- `tests/test_update.py` runs `copier update` between two synthetic tags of a throwaway copy of
  the repository (template changes land, user changes and seed files survive, `uv.lock` is
  refreshed) and from the last real release tags to the working tree. It needs the release
  tags locally (`git fetch --tags`).
- `tests/test_examples.py` fails while `examples/` is stale: run `make examples`.
- The other tests generate projects with tasks and run their tooling (`ruff`, `mypy`,
  `pytest`, `zizmor`, `actionlint`, ...).
- `make test-e2e` (Docker): `make install && make lint test` in the uv image for every
  `python_version` and for GitLab (`tests/test_make.py`, without `make format` first),
  the production image, and, when installed, the generated GitHub workflow via `act` and the
  GitLab pipeline via `gitlab-ci-local`. CI runs them in `.github/workflows/e2e.yml`; keep its
  `variant` matrix in sync with `VARIANTS` in `tests/test_make.py`.

Tests render the working tree (`vcs_ref="HEAD"` includes uncommitted changes).

## Versioning & releases

The template uses SemVer git tags so that `copier update` in downstream projects is reproducible. Without tags Copier falls back to `HEAD`, which makes updates unpredictable.

Currently the template is in **pre-1.0** (`0.x.y`):

- `0.MINOR.0` — any change to the template that requires user action on `copier update` (renamed variable, removed file, restructured layout, etc.).
- `0.MINOR.PATCH` — backwards-compatible fixes and additions.

After API stabilizes, switch to standard SemVer (`1.0.0` onward).

### Cutting a release

1. Move the `Unreleased` section of [CHANGELOG.md](CHANGELOG.md) under the new version and date.
   Every minor release has **Upgrade notes**: what users must do by hand after `copier update`
   (seed files are not updated, so describe changes to them there).
2. Tag the merge commit on `main` and push the tag:

```bash
git tag -a v0.2.0 -m "Brief description of changes"
git push origin v0.2.0
```

## Answers and migrations

`_migrations` in `copier.yml` are the last resort. Any applicable migration makes
`copier update` an unsafe operation (it needs `--trust` even for users who never trusted tasks),
and migration commands run on the user's machine and shell. Prefer instead:

- **Removed question** — just delete it: Copier drops answers to unknown questions from
  `.copier-answers.yml` on the next update.
- **Renamed question or changed choices** — users re-answer on an interactive update or pass
  `--data key=value`; describe it in the Upgrade notes.
- **Removed or renamed file** — Copier deletes a file that was removed from the template if the
  user did not change it; otherwise mention it in the Upgrade notes.
- **Text to show on update** — `_message_before_update` / `_message_after_update`.

Add a migration only when a project cannot be updated correctly without changing it first.
Then keep the command portable (POSIX shell or `{{ _copier_python }}` with a script in a
`migrations/` directory at the repository root, never GNU-only flags such as `sed -i`),
make it idempotent, and cover it with a `copier update` test in `tests/test_update.py`
from the previous tag.

## Tool versions in the template

- Dependencies in `template/pyproject.toml.jinja` have **lower bounds only** (`>=`); the exact
  versions live in the generated `uv.lock` and are upgraded by the project (`make update`, bots).
  Raise the lower bounds rarely (at most once per minor release): every bump touches the same
  lines that `uv add` and update bots change, so it conflicts on `copier update`.
- The one exception is `uv_build>=X,<Y` in `[build-system]`: uv recommends an upper bound for its
  build backend.
- `COPIER` in `template/Makefile.jinja` requires the same minimum version as `_min_copier_version`.
- pre-commit runs ruff and mypy as `repo: local` hooks through `uv run`, so their versions come
  from `uv.lock`. Only `pre-commit-hooks` has a pinned `rev`.

### Version bump checklist

Once per minor release (and for security fixes), bump together:

- [ ] **uv** — the `uv` stage of `template/Dockerfile.jinja`
  (`FROM ghcr.io/astral-sh/uv:X.Y.Z AS uv`, a literal line so that Dependabot can bump it) and
  `UV_VERSION` in both CI templates (GitHub `setup-uv`, GitLab image tag; check that the
  `X.Y.Z-pythonV-trixie-slim` tags exist for every `python_version` choice).
  `tests/test_ci.py` checks that they match. On a new uv minor version also raise the
  `uv_build>=X,<Y` range in `template/pyproject.toml.jinja`.
- [ ] **GitHub actions** — in the workflow template and in `.github/workflows/` of this
  repository, pinned to commit SHAs with a `# vX.Y.Z` comment. Resolve a tag with
  `git ls-remote https://github.com/OWNER/REPO refs/tags/vX.Y.Z` (for an annotated tag use the
  `^{}` line) and check the result with `zizmor --persona=pedantic` and `actionlint`.
- [ ] **pre-commit revs** — `pre-commit-hooks` in `template/.pre-commit-config.yaml` and in
  `.pre-commit-config.yaml` (`pre-commit autoupdate` in a generated project shows the new rev).
- [ ] **Lower bounds** of runtime and dev dependencies in `template/pyproject.toml.jinja`,
  if a feature of a newer version is needed.
- [ ] **E2E tools** — `ACT_VERSION`/`ACT_SHA256`, the act runner image and
  `GITLAB_CI_LOCAL_VERSION` in `.github/workflows/e2e.yml`.
- [ ] `make examples`, `make lint test`, a CHANGELOG entry.

## Seed files (application code)

The application code of a generated project (`__main__.py`, `config.py`, `logging_config.py`,
their tests, `tests/conftest.py`, `README.md`, `.env.example`) belongs to the project. These files are
listed in `_skip_if_exists` in `copier.yml`: Copier renders them on `copier copy` and never
overwrites them on `copier update`. Keep `_skip_if_exists` and `SEED_FILES` in
`tests/test_core.py` in sync.

- A seed file deleted in a project comes back on the next update, so do not add empty placeholders.
- Changes to seed files reach only new projects; describe them in the release notes instead.
- The copy task runs `ruff check --fix-only` and `ruff format`, so code adapts to `line_length` and
  long package names, but ruff cannot rewrap comments and docstrings: keep them within 50 columns,
  the smallest allowed `line_length` (`W505` uses it as `max-doc-length`).
