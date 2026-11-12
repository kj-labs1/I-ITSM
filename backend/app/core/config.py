"""
Application settings using pydantic-settings.

OOP Design: Uses pydantic-settings BaseSettings to provide type-safe,
validated configuration with automatic environment variable loading.
A cached factory function ensures a single settings instance is shared
across the application (singleton pattern via lru_cache).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration.

    All settings can be overridden via environment variables or a `.env` file.
    Sensitive defaults (e.g. JWT_SECRET_KEY) are deliberately insecure to force
    explicit configuration in production.
    """

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "I-ITSM"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+psycopg://iitsm:iitsm@localhost:5432/iitsm"
    DATABASE_ECHO: bool = False

    # ── JWT / Auth ───────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(default="CHANGE-ME-IN-PRODUCTION", repr=False)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── LLM Integration ─────────────────────────────────────────────────
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = Field(default="", repr=False)
    LLM_MODEL: str = ""
    LLM_BASE_URL: str = ""
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_RETRIES: int = 2
    LLM_ENABLED: bool = False

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Using ``lru_cache`` guarantees the ``.env`` file is read only once and the
    same ``Settings`` instance is reused for the lifetime of the process.
    """
    return Settings()
