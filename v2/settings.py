"""Application settings loaded from environment variables."""

from functools import lru_cache
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Optional PostHog settings that keep the service bootable without analytics."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    posthog_project_token: str | None = None
    posthog_host: str | None = None
    environment: str = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))

    @property
    def is_production(self) -> bool:
        """Whether missing optional analytics configuration should remain quiet."""
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for application startup and dependency injection."""
    return Settings()
