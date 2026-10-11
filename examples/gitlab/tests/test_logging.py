"""Tests for the logging setup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import json
import logging

import structlog

from example_app.logging_config import configure_logging

if TYPE_CHECKING:
    import pytest


def _json_lines(output: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in output.splitlines()]


def test_json_format(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", fmt="json")

    structlog.stdlib.get_logger("app").info("user created", user_id=42)

    (record,) = _json_lines(capsys.readouterr().out)
    assert record["event"] == "user created"
    assert record["user_id"] == 42
    assert record["level"] == "info"
    assert record["logger"] == "app"
    assert record["timestamp"].endswith("Z")


def test_json_format_for_stdlib_loggers(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", fmt="json")

    logging.getLogger("third.party").warning("retry %d", 3)

    (record,) = _json_lines(capsys.readouterr().out)
    assert record["event"] == "retry 3"
    assert record["level"] == "warning"
    assert record["logger"] == "third.party"


def test_json_format_exceptions(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", fmt="json")

    try:
        int("not a number")
    except ValueError:
        structlog.stdlib.get_logger("app").exception("failed")

    (record,) = _json_lines(capsys.readouterr().out)
    assert "ValueError" in record["exception"]


def test_console_format(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", fmt="console")

    structlog.stdlib.get_logger("app").info("user created", user_id=42)
    logging.getLogger("third.party").warning("retry")

    output = capsys.readouterr().out
    assert "user created" in output
    assert "user_id=42" in output
    assert "retry" in output


def test_level_filters_records(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="WARNING", fmt="json")

    logger = structlog.stdlib.get_logger("app")
    logger.info("hidden")
    logger.warning("shown")

    events = [record["event"] for record in _json_lines(capsys.readouterr().out)]
    assert events == ["shown"]


def test_configure_is_idempotent(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", fmt="console")
    configure_logging(level="INFO", fmt="json")

    structlog.stdlib.get_logger("app").info("once")

    (record,) = _json_lines(capsys.readouterr().out)
    assert record["event"] == "once"
