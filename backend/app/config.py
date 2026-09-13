"""
Application settings loaded from environment variables.
Never hardcode secrets here; use .env file.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Groq LLM
    groq_api_key: str = ""
    groq_model: str = "gemma2-9b-it"
    groq_timeout: int = 60

    # Database
    database_url: str = "sqlite:///./aivoa_dev.db"

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Upload
    max_upload_size_mb: int = 10
    allowed_mime_types: str = "application/pdf,text/plain"

    # Duplicate detection
    duplicate_detection_days: int = 90
    duplicate_similarity_threshold: float = 0.75

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def allowed_mime_types_list(self) -> List[str]:
        return [m.strip() for m in self.allowed_mime_types.split(",")]


settings = Settings()
