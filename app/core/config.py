import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "UnumPay Analytics API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/unumpay_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # On Vercel only /tmp is writable — locally use uploads/
    UPLOAD_DIR: str = os.environ.get("UPLOAD_DIR", "/tmp" if os.environ.get("VERCEL") else "uploads")
    MAX_FILE_SIZE_MB: int = 50

    # Add your Vercel deployment URL here once deployed
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
        "*",  # Allows Flutter mobile/desktop apps — tighten this in production
    ]

    class Config:
        env_file = ".env"


settings = Settings()
