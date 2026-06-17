"""AG-UI server for the Agentic DevOps Starter application."""

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from copilot import CopilotClient, SubprocessConfig
from copilot.client import TelemetryConfig
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.logging_utils import setup_logging
from src.observability import configure_observability
from src.routes import router
from src.skills import load_skills
from src.state import (
    FoundrySessionPool,
    SessionPool,
    set_client,
    set_foundry_session_pool,
    set_session_pool,
)

load_dotenv()

logger = setup_logging(settings.log_level)
configure_observability()

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def _build_copilot_subprocess_config() -> SubprocessConfig | None:
    """Return CLI subprocess config when GitHub Copilot CLI OTEL export is configured.

    Falls back to environment variables for settings that may be injected at runtime
    by start-backend.sh (after pydantic-settings has already loaded config).
    """
    endpoint = settings.cli_otel_endpoint or os.environ.get("COPILOT_API_CLI_OTEL_ENDPOINT", "")
    file_path = settings.cli_otel_file_path or os.environ.get("COPILOT_API_CLI_OTEL_FILE_PATH", "")

    if not endpoint and not file_path:
        return None

    telemetry: TelemetryConfig = {
        "exporter_type": settings.cli_otel_exporter_type,
        "source_name": settings.cli_otel_source_name,
        "capture_content": settings.cli_otel_capture_content,
    }
    if endpoint:
        telemetry["otlp_endpoint"] = endpoint
    if file_path:
        telemetry["file_path"] = file_path

    return SubprocessConfig(telemetry=telemetry)


async def _idle_cleanup_loop(pool: SessionPool | FoundrySessionPool) -> None:
    """Periodically disconnect idle sessions to free resources."""
    while True:
        await asyncio.sleep(30)
        await pool.cleanup_idle()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        github_token = os.environ.get("GITHUB_TOKEN")
        logger.info(
            "GitHub token configuration loaded",
            extra={"has_github_token": bool(github_token)},
        )

        # Discover predefined Agent Skills (SKILL.md open format) so the
        # Copilot SDK can load and apply them across all sessions.
        load_skills()

        subprocess_config = _build_copilot_subprocess_config()
        if subprocess_config is not None:
            logger.info(
                "Copilot CLI OTEL telemetry enabled",
                extra={
                    "otlp_endpoint": subprocess_config.telemetry.get("otlp_endpoint") if subprocess_config.telemetry else None,
                    "capture_content": subprocess_config.telemetry.get("capture_content") if subprocess_config.telemetry else None,
                },
            )
            client = CopilotClient(subprocess_config)
        else:
            logger.info("Copilot CLI OTEL telemetry disabled (no endpoint configured)")
            client = CopilotClient()
        await client.start()
        set_client(client)
        logger.info("CopilotClient started (GitHub Copilot SDK)")

        pool = SessionPool(idle_timeout=settings.session_timeout)
        set_session_pool(pool)
        foundry_pool = FoundrySessionPool(idle_timeout=settings.session_timeout)
        set_foundry_session_pool(foundry_pool)
        cleanup_tasks = [
            asyncio.create_task(_idle_cleanup_loop(pool)),
            asyncio.create_task(_idle_cleanup_loop(foundry_pool)),
        ]

        yield

        for cleanup_task in cleanup_tasks:
            cleanup_task.cancel()
        await foundry_pool.shutdown()
        await pool.shutdown()
        await client.stop()
        logger.info("CopilotClient stopped")

    app = FastAPI(
        lifespan=lifespan,
        title="Agentic DevOps Starter AG-UI Server",
        description="AG-UI server for conversational AI agent powered by GitHub Copilot SDK",
        version="0.2.0",
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    cors_origins = os.environ.get("CORS_ORIGINS", "").split(",")
    if not cors_origins or cors_origins == [""]:
        cors_origins = DEFAULT_CORS_ORIGINS

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    logger.info("FastAPI app created successfully")
    return app


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting AG-UI server on http://0.0.0.0:%d", settings.port)
    uvicorn.run("agui_server:create_app", host=settings.host, port=settings.port, factory=True)
