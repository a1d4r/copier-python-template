"""Logging: structlog on top of ``logging``.

structlog loggers and stdlib loggers of
third-party libraries share one handler and
one set of processors, so all lines look the
same: human-readable (``console``) for
development or one JSON object per line
(``json``) for log collectors. Logs go to
stdout.

Usage::

    import structlog

    logger = structlog.stdlib.get_logger(__name__)
    logger.info("user created", user_id=42)
"""

from typing import Literal

import logging
import sys

import structlog

type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
type LogFormat = Literal["console", "json"]

_HANDLER_NAME = __name__

# Run for structlog events and stdlib records.
SHARED_PROCESSORS: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.ExtraAdder(),
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
]


def _renderers(fmt: LogFormat) -> list[structlog.typing.Processor]:
    if fmt == "json":
        return [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    # Renders exceptions by itself.
    return [structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())]


def configure_logging(level: LogLevel = "INFO", fmt: LogFormat = "console") -> None:
    """Configure structlog and the root logger.

    Safe to call again: replaces its handler.
    """
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *SHARED_PROCESSORS,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *_renderers(fmt),
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    for old in [h for h in root.handlers if h.get_name() == _HANDLER_NAME]:
        root.removeHandler(old)
        old.close()
    root.addHandler(handler)
    root.setLevel(level)
    # Quiet noisy libraries here, for example
    # set the "httpx" logger to WARNING.
