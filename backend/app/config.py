import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Explicitly load .env from the backend directory
_backend_dir = Path(__file__).resolve().parent.parent
_env_path = _backend_dir / ".env"
if _env_path.exists():
    load_dotenv(str(_env_path), override=True)


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    newsapi_key: str = ""
    database_path: str = "data/signals.db"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://www.jamesincognito.com",
        "https://jamesincognito.com",
    ]
    ingestion_interval_hours: int = 2
    analysis_interval_minutes: int = 15
    aggregation_interval_hours: int = 6
    port: int = 8000

    @property
    def db_path(self) -> Path:
        return _backend_dir / self.database_path

    @property
    def static_dir(self) -> Path:
        """Path to built frontend assets (populated during Railway build)."""
        return _backend_dir / "static"


settings = Settings()
