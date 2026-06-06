"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    host: str = "0.0.0.0"
    port: int = 5100
    log_level: str = "INFO"
    session_timeout: float = 120.0

    azure_storage_blob_endpoint: str = ""
    azure_storage_container_name: str = "uploads"

    # Additional directories (os.pathsep- or comma-separated) the Copilot SDK
    # should scan for Agent Skills (SKILL.md files), in addition to the
    # built-in ``app/skills/`` directory. Leave empty to use only built-ins.
    skill_directories: str = ""
    # Comma-separated skill names to disable (passed to the SDK as-is).
    disabled_skills: str = ""

    model_config = {
        "env_prefix": "COPILOT_API_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
