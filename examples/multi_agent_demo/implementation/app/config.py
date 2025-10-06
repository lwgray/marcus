"""
Application configuration management.

This module handles environment variable loading and application settings
using Pydantic Settings for validation.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore[misc]
    """
    Application settings loaded from environment variables.

    Attributes
    ----------
    database_url : str
        PostgreSQL database connection URL
    secret_key : str
        Secret key for JWT token signing
    jwt_algorithm : str
        Algorithm for JWT token encoding (default: HS256)
    jwt_expire_minutes : int
        JWT token expiration time in minutes (default: 60)
    api_v1_prefix : str
        API version 1 URL prefix (default: /api/v1)
    cors_origins : list[str]
        Allowed CORS origins
    debug : bool
        Debug mode flag (default: False)
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Database
    database_url: str = (
        "postgresql://user:password@localhost:5432/taskmanagement"  # pragma: allowlist secret # noqa: E501
    )
    database_pool_size: int = 10

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Application
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns
    -------
    Settings
        Application settings instance

    Notes
    -----
    Settings are cached using lru_cache to avoid re-reading
    environment variables on every access.
    """
    return Settings()
