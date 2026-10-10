"""Application entry point.

Run it with
``python -m example_app``
or with the console script
``example-app``.
"""

import structlog

from example_app.config import get_settings
from example_app.logging_config import configure_logging

logger = structlog.stdlib.get_logger(__name__)


def main() -> None:
    """Run the application."""
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    logger.info("application started", log_level=settings.log_level)


if __name__ == "__main__":
    main()
