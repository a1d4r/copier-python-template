"""`examples/` must match the current template (see tests/examples.py)."""

from typing import TYPE_CHECKING

import filecmp

import pytest

from tests.examples import EXAMPLES, EXAMPLES_DIR, render

if TYPE_CHECKING:
    from pathlib import Path

# Local artifacts of someone running the example project in place.
LOCAL = [".venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", "reports"]


def _differences(compared: filecmp.dircmp[str], prefix: str = "") -> list[str]:
    names = compared.left_only + compared.right_only + compared.diff_files + compared.funny_files
    found = [prefix + name for name in names]
    for name, sub in compared.subdirs.items():
        found += _differences(sub, f"{prefix}{name}/")
    return found


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_example_is_up_to_date(tmp_path: Path, name: str) -> None:
    fresh = render(name, tmp_path / name)

    stale = _differences(filecmp.dircmp(EXAMPLES_DIR / name, fresh, ignore=LOCAL, shallow=False))

    assert not stale, f"examples/{name} is stale, run `make examples`: {stale}"
