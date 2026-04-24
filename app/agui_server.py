"""AG-UI server for the Agentic DevOps Starter application.

FastAPI server exposing a ChatAgent through AG-UI protocol with streaming support.
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from ag_ui.core import RunErrorEvent, RunFinishedEvent
from ag_ui.encoder import EventEncoder
from agent_framework import ChatAgent, ai_function
from agent_framework.azure import AzureAIAgentClient
from agent_framework_ag_ui import AgentFrameworkAgent
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Load environment and setup logging
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
DEPLOYMENT = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")

# Default CORS origins for development
DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

# Agent instructions constant — shared by ChatAgent and the Azure agent provisioning step.
_INSTRUCTIONS = (
    "You are a helpful AI assistant. "
    "Use get_time_zone for time zone information about locations."
)


@ai_function(description="Get the time zone for a location.")
def get_time_zone(location: Annotated[str, "The city or location name"]) -> str:
    """Get the time zone for a location (server-side tool)."""
    logger.info(f"get_time_zone called: {location}")
    timezone_data = {
        "seattle": "Pacific Time (UTC-8)",
        "san francisco": "Pacific Time (UTC-8)",
        "new york": "Eastern Time (UTC-5)",
        "london": "Greenwich Mean Time (UTC+0)",
        "tokyo": "Japan Standard Time (UTC+9)",
        "sydney": "Australian Eastern Time (UTC+10)",
        "paris": "Central European Time (UTC+1)",
        "mumbai": "India Standard Time (UTC+5:30)",
    }
    return timezone_data.get(location.lower(), f"Time zone not available for {location}")


def create_agent() -> ChatAgent:
    """Create and configure the ChatAgent."""
    if not ENDPOINT or not DEPLOYMENT:
        raise ValueError("AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME must be set")

    logger.info(f"Creating ChatAgent: endpoint={ENDPOINT}, deployment={DEPLOYMENT}")

    # should_cleanup_agent=False: agent lifecycle is managed by the lifespan below.
    chat_client = AzureAIAgentClient(
        project_endpoint=ENDPOINT,
        model_deployment_name=DEPLOYMENT,
        credential=DefaultAzureCredential(),
        should_cleanup_agent=False,
    )

    return ChatAgent(
        name="AGUIAssistant",
        instructions=_INSTRUCTIONS,
        chat_client=chat_client,
        tools=[get_time_zone],
    )


async def _init_azure_agent(agent: ChatAgent) -> str:
    """Create an Azure AI Agent with explicit null temperature/top_p for o-series model compatibility.

    Root cause: when temperature and top_p are *absent* from the create_agent request (as happens with
    the kwargs overload, which filters ``{k: v ... if v is not None}``), the Azure AI Agents service
    stores server-side defaults (1.0 for both).  On subsequent runs the service injects those stored
    defaults into the model call, and o-series models reject them outright:

        "Unsupported parameter: 'top_p' is not supported with this model."

    Fix: use the **body-dict overload** of ``create_agent``.  The dict is serialized directly with
    ``json.dumps`` (the SDK's None-filtering is *not* applied to a pre-built body dict), so Python
    ``None`` becomes JSON ``null``.  Explicit ``null`` tells the service "no value" — it will not
    fall back to the 1.0 defaults and will not inject these parameters into model calls.
    """
    azure_agent = await agent.chat_client.agents_client.create_agent(
        {
            "model": DEPLOYMENT,
            "name": "AGUIAssistant",
            "instructions": _INSTRUCTIONS,
            "temperature": None,
            "top_p": None,
        }
    )
    agent.chat_client.agent_id = azure_agent.id
    return azure_agent.id


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    raw_agent = create_agent()
    wrapped_agent = AgentFrameworkAgent(agent=raw_agent)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        agent_id = await _init_azure_agent(raw_agent)
        logger.info(f"Azure AI Agent provisioned: {agent_id}")
        yield
        try:
            await raw_agent.chat_client.agents_client.delete_agent(agent_id)
            await raw_agent.chat_client.agents_client.close()
        except Exception:
            logger.warning("Agent cleanup failed on shutdown", exc_info=True)

    app = FastAPI(
        lifespan=lifespan,
        title="Agentic DevOps Starter AG-UI Server",
        description="AG-UI server for conversational AI agent",
        version="0.1.0",
    )

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # CORS configuration
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

    # Health check endpoint for App Service and CI/CD verification
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    # Register AG-UI endpoint with proper error handling so the SSE stream
    # always terminates with RUN_FINISHED, even when run_agent() raises.
    @app.post("/")
    async def agent_endpoint(request: Request) -> StreamingResponse:  # type: ignore[misc]
        """Handle AG-UI agent requests and guarantee stream termination."""
        input_data = await request.json()
        thread_id: str = input_data.get("thread_id") or ""
        run_id: str = input_data.get("run_id") or ""

        async def event_generator() -> AsyncGenerator[str, None]:
            encoder = EventEncoder()
            try:
                async for event in wrapped_agent.run_agent(input_data):
                    yield encoder.encode(event)
            except Exception as exc:
                logger.exception("run_agent raised an exception; terminating stream cleanly")
                yield encoder.encode(RunErrorEvent(message=str(exc)))
                yield encoder.encode(RunFinishedEvent(thread_id=thread_id, run_id=run_id))

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    logger.info("FastAPI app created successfully")
    return app


# App instance (lazy initialization)
app: FastAPI | None = None


def get_app() -> FastAPI:
    """Get or create the FastAPI application instance."""
    global app
    if app is None:
        app = create_app()
    return app


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AG-UI server on http://0.0.0.0:5100")
    uvicorn.run("agui_server:get_app", host="0.0.0.0", port=5100, factory=True)
