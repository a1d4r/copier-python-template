"""Fixtures that isolate tests from app state."""

from __future__ import annotations

from typing import TYPE_CHECKING

import logging
import os

import pytest
import structlog

from example_app.config import Settings, get_settings

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def isolate_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Hide env vars and .env, reset settings."""
    # Case-insensitive; DB__URL sets field `db`.
    for name in list(os.environ):
        if name.lower().partition("__")[0] in Settings.model_fields:
            monkeypatch.delenv(name)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def isolate_logging() -> Iterator[None]:
    """Undo ``configure_logging``."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    for handler in set(root.handlers) - set(handlers):
        handler.close()
    root.handlers[:] = handlers
    root.setLevel(level)
    structlog.reset_defaults()
