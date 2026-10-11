"""Application settings.

Values are read from environment variables, then from the ``.env`` file in
the working directory, then from the defaults below. See ``.env.example`` for
the full list.

Names have no prefix (``LOG_LEVEL``): each service runs in its own container
with its own environment, and platform-provided names such as
``DATABASE_URL`` work as they are. Set ``env_prefix`` if the app shares the
environment with other programs.
"""

from typing import Annotated, Any

import functools

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict

from example_app.logging_config import LogFormat, LogLevel


def _upper(value: Any) -> Any:
    return value.upper() if isinstance(value, str) else value


class Settings(BaseSettings):
    """Settings from the environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Nested settings: DB__URL -> settings.db.url
        env_nested_delimiter="__",
        # Skip unknown variables, e.g. ones meant for other tools in .env.
        extra="ignore",
    )

    log_level: Annotated[LogLevel, BeforeValidator(_upper)] = "INFO"
    log_format: LogFormat = "console"

    # Add your settings here. Group related ones into a nested model:
    # `db: DatabaseSettings` with `class DatabaseSettings(BaseModel)`.


@functools.cache
def get_settings() -> Settings:
    """Return the settings, loaded on first use.

    Tests override them with environment variables and
    ``get_settings.cache_clear()``.
    """
    return Settings()
