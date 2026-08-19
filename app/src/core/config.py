"""Application configuration via environment variables."""

import logging
import os
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    host: str = "0.0.0.0"
    port: int = 5100
    log_level: str = "INFO"
    session_timeout: float = 120.0
    tool_timeout: float = 10.0
    isolation_session_header: str = "X-Isolation-Session-ID"
    session_config_root_dir: str = ".copilot-session-config"
    github_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("COPILOT_APP_CLIENT_ID", "GITHUB_CLIENT_ID"),
    )
    github_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("COPILOT_APP_CLIENT_SECRET", "GITHUB_CLIENT_SECRET"),
    )
    github_oauth_redirect_uri: str = "https://app-agentic-devops.azurewebsites.net/auth/callback"
    # 공개 테스트용 엔드포인트 (외부 API 연동 예시)
    tool_external_api_url: str = "https://api.github.com/zen"

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

    # Azure App Configuration (optional — used for runtime configuration values
    # such as feature flags).
    # When the endpoint is set the application fetches key-values at startup and
    # applies them with lower precedence than environment variables.
    app_config_endpoint: str = ""
    app_config_label: str = ""

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

    # Remote MCP (Model Context Protocol) server that exposes additional tools.
    # When set, tools are fetched at startup and made available to all sessions.
    mcp_server_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "MCP_SERVER_URL",
            "COPILOT_API_MCP_SERVER_URL",
        ),
    )

    model_config = {
        "env_prefix": "COPILOT_API_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def apply_app_configuration(s: Settings) -> None:
    """Load key-values from Azure App Configuration and apply to *s*.

    Precedence: env vars > App Config > defaults.
    Values whose corresponding environment variable is already present in
    ``os.environ`` are never overwritten — env vars always win.

    The endpoint is read from ``COPILOT_API_APP_CONFIG_ENDPOINT``; an empty
    endpoint makes this function a no-op so callers need not guard.

    App Config keys are expected to use the full environment-variable name
    (e.g. ``COPILOT_API_FOUNDRY_AUTH_MODE``) or the bare form without the
    ``COPILOT_API_`` prefix (e.g. ``FOUNDRY_AUTH_MODE``).  Both are mapped to
    the corresponding ``Settings`` field.
    """
    if not s.app_config_endpoint:
        return

    try:
        from azure.appconfiguration import (
            AzureAppConfigurationClient,  # type: ignore[import-untyped]
        )
        from azure.identity import DefaultAzureCredential

        client = AzureAppConfigurationClient(
            base_url=s.app_config_endpoint,
            credential=DefaultAzureCredential(),
        )
        label_filter = s.app_config_label or None

        for item in client.list_configuration_settings(label_filter=label_filter):
            key: str = item.key
            value: str = item.value or ""

            # Env var takes precedence — skip if the key or any recognised
            # alias form is already present in the environment.
            # App Config keys may omit the COPILOT_API_ prefix, so check both:
            #   e.g. "FOUNDRY_AUTH_MODE" and "COPILOT_API_FOUNDRY_AUTH_MODE".
            bare_key = key.upper().removeprefix("COPILOT_API_")
            if (
                key in os.environ
                or bare_key in os.environ
                or f"COPILOT_API_{bare_key}" in os.environ
            ):
                continue

            # Map App Config key to the Settings field name.
            # Strip the COPILOT_API_ prefix (case-insensitive) when present.
            field_name = key.lower().removeprefix("copilot_api_")
            if not hasattr(s, field_name):
                logger.debug("App Config: unknown key %r — skipped", key)
                continue

            try:
                setattr(s, field_name, value)
                logger.debug("App Config applied: %s = %r", field_name, value)
            except Exception:
                logger.debug("App Config: could not set %r", field_name, exc_info=True)

    except Exception as exc:
        logger.warning("Azure App Configuration load failed (non-fatal): %s", exc)


settings = Settings()
apply_app_configuration(settings)
