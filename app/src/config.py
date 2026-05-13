"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    host: str = "0.0.0.0"
    port: int = 5100
    log_level: str = "INFO"
    session_timeout: float = 120.0

    model_config = {"env_prefix": "COPILOT_API_"}


settings = Settings()
