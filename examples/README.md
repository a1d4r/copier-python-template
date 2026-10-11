# Examples

Projects rendered from the current template with default answers
(`project_name="Example App"`, `username=acme`) for each `git_platform`:

- [`github/`](github/) — GitHub Actions and Dependabot;
- [`gitlab/`](gitlab/) — GitLab CI.

They are generated, do not edit them by hand. After changing `template/` run
`make examples` and commit the result: `tests/test_examples.py` fails while the
snapshot is stale, and the diff of this directory shows reviewers what generated
projects get. Tasks are skipped (no `uv.lock`, no formatting for other line lengths),
and `_commit`/`_src_path` are removed from `.copier-answers.yml`.
