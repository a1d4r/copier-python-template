"""Tests for the application entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING

import json
import signal

import pytest

from example_app.__main__ import main

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def restore_sigterm() -> Iterator[None]:
    """Undo the SIGTERM handler of ``main``."""
    handler = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGTERM, handler)


@pytest.mark.parametrize("log_format", ["console", "json"])
def test_main_logs_startup(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], log_format: str
) -> None:
    monkeypatch.setenv("LOG_FORMAT", log_format)

    main()

    assert "application started" in capsys.readouterr().out


def test_main_logger_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LOG_FORMAT", "json")

    main()

    record = json.loads(capsys.readouterr().out)
    assert record["logger"] == "example_app"


def test_main_exits_on_sigterm() -> None:
    main()

    handler = signal.getsignal(signal.SIGTERM)
    assert callable(handler)
    with pytest.raises(SystemExit) as exc_info:
        handler(signal.SIGTERM, None)
    assert exc_info.value.code == 128 + signal.SIGTERM
