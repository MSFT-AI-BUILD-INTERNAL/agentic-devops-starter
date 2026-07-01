"""Application configuration via environment variables."""

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    host: str = "0.0.0.0"
    port: int = 5100
    log_level: str = "INFO"
    session_timeout: float = 120.0

    azure_storage_blob_endpoint: str = ""
    azure_storage_container_name: str = "uploads"

    azure_ai_project_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AZURE_AI_PROJECT_ENDPOINT",
            "COPILOT_API_AZURE_AI_PROJECT_ENDPOINT",
        ),
    )
    azure_ai_model_deployment_name: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AZURE_AI_MODEL_DEPLOYMENT_NAME",
            "COPILOT_API_AZURE_AI_MODEL_DEPLOYMENT_NAME",
        ),
    )
    foundry_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "FOUNDRY_API_KEY",
            "AZURE_OPENAI_API_KEY",
            "COPILOT_API_FOUNDRY_API_KEY",
        ),
    )
    foundry_auth_mode: str = Field(
        default="auto",
        validation_alias=AliasChoices("FOUNDRY_AUTH_MODE", "COPILOT_API_FOUNDRY_AUTH_MODE"),
    )
    foundry_wire_api: str = Field(
        default="responses",
        validation_alias=AliasChoices("FOUNDRY_WIRE_API", "COPILOT_API_FOUNDRY_WIRE_API"),
    )

    # Additional directories (os.pathsep- or comma-separated) the Copilot SDK
    # should scan for Agent Skills (SKILL.md files), in addition to the
    # built-in ``app/skills/`` directory. Leave empty to use only built-ins.
    skill_directories: str = ""
    # Comma-separated skill names to disable (passed to the SDK as-is).
    disabled_skills: str = ""

    # OpenTelemetry export from the GitHub Copilot CLI subprocess spawned by
    # the SDK. This is separate from the FastAPI/Azure Monitor instrumentation
    # configured in observability.py.
    cli_otel_endpoint: str = ""
    cli_otel_exporter_type: Literal["otlp-http", "file"] = "otlp-http"
    cli_otel_file_path: str = ""
    cli_otel_source_name: str = "agentic-devops-starter"
    cli_otel_capture_content: bool = True

    model_config = {
        "env_prefix": "COPILOT_API_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
