from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache
from typing import Any


def parse_cors_origins(v: Any) -> list[str]:
    """Parse CORS origins from string or list."""
    if isinstance(v, str):
        # Handle JSON array format
        if v.startswith("["):
            import json
            return json.loads(v)
        # Handle comma-separated format
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    if isinstance(v, list):
        return v
    return ["*"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_name: str = "GovBid API"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./govbid.db"

    # Authentication
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Email (Resend)
    resend_api_key: str = ""
    email_from: str = "noreply@govbid.example.com"

    # Scraping
    scrape_interval_hours: int = 24
    request_delay_seconds: float = 1.5

    # CORS - stored as string to avoid pydantic-settings JSON parsing issues
    cors_origins_str: str = "*"

    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins as a list."""
        return parse_cors_origins(self.cors_origins_str)

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v):
        if isinstance(v, str):
            # Supabase/Heroku use postgres:// but SQLAlchemy needs postgresql://
            # Use psycopg (psycopg3) instead of asyncpg for better pgbouncer compatibility
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+psycopg://", 1)
            elif v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()
