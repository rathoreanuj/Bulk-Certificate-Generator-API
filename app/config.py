"""
app/config.py - Application settings loaded from environment variables.
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application & Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "sqlite:///./certificates.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800

    # Directory where generated PDF certificates are stored
    CERTIFICATES_DIR: str = "./generated_certificates"

    # Scalability Limits & Protection
    MAX_RECIPIENTS_PER_JOB: int = 10000
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # silently ignore unknown env variables
    }

    def get_certificates_path(self) -> Path:
        """Return an absolute Path object for the certificates directory."""
        path = Path(self.CERTIFICATES_DIR).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
