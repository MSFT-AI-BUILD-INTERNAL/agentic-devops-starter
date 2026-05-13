"""AG-UI server for the Agentic DevOps Starter application."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from copilot import CopilotClient, SubprocessConfig
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.logging_utils import setup_logging
from src.observability import configure_observability
from src.routes import router
from src.state import set_client

load_dotenv()

logger = setup_logging(settings.log_level)
configure_observability()

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        github_token = os.environ.get("GITHUB_TOKEN")
        config = SubprocessConfig(github_token=github_token) if github_token else None
        client = CopilotClient(config)
        await client.start()
        set_client(client)
        logger.info("CopilotClient started (GitHub Copilot SDK)")
        yield
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
