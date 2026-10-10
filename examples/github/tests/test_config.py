"""Tests for application settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pydantic
import pytest

from example_app.config import Settings, get_settings

if TYPE_CHECKING:
    from pathlib import Path


def test_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.log_level == "INFO"
    assert settings.log_format == "console"


def test_env_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LOG_FORMAT", "json")

    settings = Settings(_env_file=None)

    assert settings.log_level == "DEBUG"
    assert settings.log_format == "json"


def test_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("LOG_LEVEL=WARNING\nUNKNOWN=1\n")
    monkeypatch.chdir(tmp_path)

    assert Settings().log_level == "WARNING"


@pytest.mark.parametrize(
    ("name", "value"), [("LOG_LEVEL", "verbose"), ("LOG_FORMAT", "xml")]
)
def test_invalid_value(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(pydantic.ValidationError):
        Settings(_env_file=None)


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_FORMAT", "json")

    assert get_settings() is get_settings()
    assert get_settings().log_format == "json"
