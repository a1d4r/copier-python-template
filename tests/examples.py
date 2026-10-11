"""Canonical renders of the template, committed to `examples/`.

The snapshot shows in every pull request what generated projects get.
`tests/test_examples.py` fails when it is stale; regenerate it with
`make examples` (`uv run python -m tests.examples`).
"""

from typing import TYPE_CHECKING, Any

import re
import shutil
import warnings

from copier import run_copy
from copier.errors import DirtyLocalWarning

from tests.conftest import TEMPLATE_DIR

if TYPE_CHECKING:
    from pathlib import Path

EXAMPLES_DIR = TEMPLATE_DIR / "examples"

COMMON: dict[str, Any] = {"project_name": "Example App", "username": "acme"}
EXAMPLES: dict[str, dict[str, Any]] = {
    "github": {**COMMON, "git_platform": "github"},
    "gitlab": {**COMMON, "git_platform": "gitlab"},
}

# Answers that change with every commit or checkout of the template.
VOLATILE_ANSWERS = re.compile(r"^_(commit|src_path): .*\n", flags=re.MULTILINE)


def render(name: str, dest: Path) -> Path:
    """Render example ``name`` into ``dest`` (no tasks, stable answers file)."""
    run_copy(
        str(TEMPLATE_DIR),
        str(dest),
        data=EXAMPLES[name],
        defaults=True,
        vcs_ref="HEAD",
        skip_tasks=True,
        unsafe=True,
        quiet=True,
    )
    answers = dest / ".copier-answers.yml"
    answers.write_text(VOLATILE_ANSWERS.sub("", answers.read_text()))
    return dest


def main() -> None:
    # Rendering uncommitted template changes is the point here.
    warnings.simplefilter("ignore", DirtyLocalWarning)
    for name in EXAMPLES:
        shutil.rmtree(EXAMPLES_DIR / name, ignore_errors=True)
        render(name, EXAMPLES_DIR / name)


if __name__ == "__main__":
    main()
