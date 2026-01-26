from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
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

    # CORS
    cors_origins: list[str] = ["*"]

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v):
        if isinstance(v, str):
            # Supabase/Heroku use postgres:// but SQLAlchemy needs postgresql://
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
