"""AG-UI server for the Agentic DevOps Starter application.

FastAPI server exposing a ChatAgent through AG-UI protocol with streaming support.
"""

import logging
import os
from typing import Annotated

from agent_framework import ChatAgent, ai_function
from agent_framework.azure import AzureAIAgentClient
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment and setup logging
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
DEPLOYMENT = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-08-07")


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

    chat_client = AzureAIAgentClient(
        endpoint=ENDPOINT,
        model=DEPLOYMENT,
        credential=DefaultAzureCredential(),
        api_version=API_VERSION,
    )

    return ChatAgent(
        name="AGUIAssistant",
        instructions=(
            "You are a helpful AI assistant. "
            "Use get_time_zone for time zone information about locations."
        ),
        chat_client=chat_client,
        tools=[get_time_zone],
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Agentic DevOps Starter AG-UI Server",
        description="AG-UI server for conversational AI agent",
        version="0.1.0",
    )

    # CORS configuration
    cors_origins = os.environ.get("CORS_ORIGINS", "").split(",")
    if not cors_origins or cors_origins == [""]:
        cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check for Kubernetes
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    # Register AG-UI endpoint
    agent = create_agent()
    add_agent_framework_fastapi_endpoint(app, agent, "/")

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
