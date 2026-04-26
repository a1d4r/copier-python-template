# Contributing

## Versioning & releases

The template uses SemVer git tags so that `copier update` in downstream projects is reproducible. Without tags Copier falls back to `HEAD`, which makes updates unpredictable.

Currently the template is in **pre-1.0** (`0.x.y`):

- `0.MINOR.0` — any change to the template that requires user action on `copier update` (renamed variable, removed file, restructured layout, etc.).
- `0.MINOR.PATCH` — backwards-compatible fixes and additions.

After API stabilizes, switch to standard SemVer (`1.0.0` onward).

### Cutting a tag

Every merge to `main` that changes the template should be tagged before users run `copier update`:

```bash
git tag -a v0.1.1 -m "Brief description of changes"
git push origin v0.1.1
```

Breaking changes additionally need an entry in `_migrations` of `copier.yml` (see [copier docs](https://copier.readthedocs.io/en/stable/configuring/#migrations)).

Tagging can later be automated via release-please or git-cliff (tracked separately).

## Migrations

Migrations run only on `copier update` when the target version crosses
`new_version >= version > old_version`. They keep downstream projects upgradable across breaking changes.

### When to add a migration

- A question variable in `copier.yml` was renamed or removed.
- A template file was renamed, moved, or removed.
- Project layout / directory structure changed.
- Config keys in generated files moved (and existing user files need patching).

Pure additions (new optional file, new question with sensible default) usually do **not** need a migration.

### Stages

- `_stage == "before"` — runs before the new template is applied. Copier re-reads `.copier-answers.yml` after this stage, so this is where you patch the answers file (e.g. rename a variable).
- `_stage == "after"` — runs after the template update and user-diff reapply. Use it to delete deprecated files or run a cleanup script.

### Inline vs script

- Inline shell commands for one-liners (`sed`, `rm`, `mv`).
- For non-trivial logic create a Python script in a `migrations/` directory at the **template repo root** (outside `template/`, so it is not generated into user projects) and invoke it with `{{ _copier_python }}`.

### Examples

Rename a variable in the answers file before update so Copier picks up the new key:

```yaml
_migrations:
  - version: v0.2.0
    command: "sed -i 's/old_var:/new_var:/' {{ _copier_conf.answers_file }}"
    when: "{{ _stage == 'before' }}"
```

Remove a deprecated file after update:

```yaml
  - version: v0.2.0
    command: "rm -f legacy_file.txt"
    when: "{{ _stage == 'after' }}"
```

Run a Python script for complex logic:

```yaml
  - version: v0.3.0
    command: ["{{ _copier_python }}", "{{ _copier_conf.src_path }}/migrations/v0_3_0.py"]
    when: "{{ _stage == 'after' }}"
```

### Testing migrations

Each migration must be exercised by an automated `copier update` test against a fixture project generated from the previous tag. Add the test alongside the tag bump.
