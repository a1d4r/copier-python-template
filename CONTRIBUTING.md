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
