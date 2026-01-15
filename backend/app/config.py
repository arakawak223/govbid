from pydantic_settings import BaseSettings
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
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
