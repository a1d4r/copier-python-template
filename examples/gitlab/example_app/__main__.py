"""Application entry point.

Run it with ``python -m example_app`` or with the
console script ``example-app``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import signal

import structlog

from example_app.config import get_settings
from example_app.logging_config import configure_logging

if TYPE_CHECKING:
    from types import FrameType

# `__name__` is "__main__" under `python -m`.
logger = structlog.stdlib.get_logger("example_app")


def _exit_on_sigterm(signum: int, _frame: FrameType | None) -> None:
    """Exit, running ``finally`` blocks."""
    raise SystemExit(128 + signum)


def main() -> None:
    """Run the application."""
    # In a container the app is PID 1: without a handler it ignores SIGTERM,
    # and `docker stop` kills it after a timeout. Frameworks (uvicorn, aiogram)
    # install their own handlers.
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    logger.info("application started", log_level=settings.log_level)


if __name__ == "__main__":
    main()
