from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service configuration read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env")

    database_url: str


settings = Settings()
