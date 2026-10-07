from typing import Annotated

import limits
from pydantic import AfterValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def check_rate_limit(value: str) -> str:
    """Return the value if it is a valid rate limit such as "100/minute"."""
    # slowapi disables a limit it can't parse (it only logs); parse here so a typo stops the app at startup.
    limits.parse(value)
    return value


class Settings(BaseSettings):
    """Service configuration read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    rate_limit: Annotated[str, AfterValidator(check_rate_limit)] = "100/minute"


settings = Settings()
