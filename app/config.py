"""
Application configuration management using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core settings for The Blind Spot application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App metadata
    APP_NAME: str = "The Blind Spot"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "testing", "production"] = "production"
    DEBUG: bool = False

    # Server binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Gemini API settings
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 30.0
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_INITIAL_BACKOFF_SECONDS: float = 1.0

    # Security and rate limiting
    RATE_LIMIT_PER_MINUTE: int = 20
    MAX_TEXT_LENGTH: int = 5000
    MAX_DRAWING_FACTORS_LENGTH: int = 2000
    MAX_OPTIONS_LENGTH: int = 2000
    MAX_DEADLINE_LENGTH: int = 1000

    # Cache and Session Limits
    CACHE_TTL_SECONDS: int = 3600
    MAX_SESSION_HISTORY: int = 10
    SESSION_TTL_SECONDS: int = 86400  # 24 hours

    # Safety disclaimer text
    DISCLAIMER_NOTE: str = (
        "The Blind Spot is an analytical thinking aid designed to stimulate your own critical reflection. "
        "It does not provide advice, recommendations, or final answers. For health, legal, financial, or crisis "
        "situations, please consult qualified professionals or trusted counselors."
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
