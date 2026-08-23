"""AG-UI server for the Agentic DevOps Starter application."""

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from copilot import CopilotClient, SubprocessConfig
from copilot.client import ModelInfo, TelemetryConfig
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.auth import initialize_session_cipher
from src.api.routes import router
from src.core.config import settings
from src.core.logging_utils import setup_logging
from src.core.observability import configure_observability
from src.runtime.skills import load_skills
from src.runtime.state import (
    AISessionPool,
    FoundrySessionPool,
    SessionPool,
    set_client,
    set_foundry_session_pool,
    set_session_pool,
)
from src.runtime.tools import load_tools

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


async def _idle_cleanup_loop(pool: AISessionPool) -> None:
    """Periodically disconnect idle sessions to free resources."""
    while True:
        await asyncio.sleep(30)
        await pool.cleanup_idle()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        initialize_session_cipher()
        # Discover predefined Agent Skills (SKILL.md open format) so the
        # Copilot SDK can load and apply them across all sessions.
        load_skills()
        load_tools()

        subprocess_config = _build_copilot_subprocess_config()

        # TODO(github-copilot-sdk >1.0.0b3): ModelBilling.from_dict raises ValueError
        # when the Copilot API omits the `multiplier` field. Use the SDK's
        # on_list_models hook to strip the billing sub-object before deserialization
        # so the rest of ModelInfo.from_dict proceeds normally. This relies on the
        # private `client._client` RPC attribute; remove this workaround once the SDK
        # exposes a public hook/method for the raw model payload or tolerates a
        # missing `multiplier`. client is pre-bound to None and reassigned below,
        # before start() can trigger this callback.
        client: CopilotClient | None = None

        async def _on_list_models() -> list[ModelInfo]:
            if client is None:
                raise RuntimeError("CopilotClient not connected")
            rpc = client._client  # noqa: SLF001
            if rpc is None:
                raise RuntimeError("CopilotClient not connected")
            response = await rpc.request("models.list", {})
            return [
                ModelInfo.from_dict({k: v for k, v in m.items() if k != "billing"})
                for m in response.get("models", [])
            ]

        if subprocess_config is not None:
            logger.info(
                "Copilot CLI OTEL telemetry enabled",
                extra={
                    "otlp_endpoint": subprocess_config.telemetry.get("otlp_endpoint") if subprocess_config.telemetry else None,
                    "capture_content": subprocess_config.telemetry.get("capture_content") if subprocess_config.telemetry else None,
                },
            )
            client = CopilotClient(subprocess_config, on_list_models=_on_list_models)
        else:
            logger.info("Copilot CLI OTEL telemetry disabled (no endpoint configured)")
            client = CopilotClient(on_list_models=_on_list_models)
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

    # Anthropic's SDK (used by Claude Code) expects error bodies shaped like
    # {"error": {"type": "error", "message": "..."}}. FastAPI's default
    # {"detail": "..."} shape is not recognized by that SDK, which then
    # treats the (otherwise well-formed) 4xx/5xx response as a connection
    # failure and retries. Only the Anthropic-compatible routes are
    # affected; every other endpoint keeps the standard FastAPI error shape.
    _ANTHROPIC_ERROR_PATHS = ("/v1/messages", "/v1/models")

    @app.exception_handler(HTTPException)
    async def anthropic_aware_http_exception_handler(request: Request, exc: HTTPException) -> Response:
        if request.url.path.startswith(_ANTHROPIC_ERROR_PATHS):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": {"type": "error", "message": str(exc.detail)}},
                headers=exc.headers,
            )
        return await http_exception_handler(request, exc)

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
