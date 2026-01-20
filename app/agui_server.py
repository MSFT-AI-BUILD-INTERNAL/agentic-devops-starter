"""AG-UI server for the Agentic DevOps Starter application.

This module implements an AG-UI (Agent UI) server using FastAPI that exposes
the ConversationalAgent through a web interface with streaming support.

Follows all constitution requirements:
- Python ≥3.12 with type hints
- microsoft-agent-framework integration
- Pydantic models for validation
- Structured logging with correlation IDs
"""

import os
from typing import Annotated

from agent_framework import ChatAgent, ai_function
from agent_framework.azure import AzureAIAgentClient
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.logging_utils import setup_logging

# Load environment variables
load_dotenv()

# Setup structured logging
logger = setup_logging()

# Read configuration from environment
endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
deployment_name = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-08-07")
# azure_client_id is used to specify which managed identity to use in AKS environments
# where multiple managed identities exist
azure_client_id = os.environ.get("AZURE_CLIENT_ID")


# Server-side tool example
@ai_function(description="Get the time zone for a location.")
def get_time_zone(location: Annotated[str, "The city or location name"]) -> str:
    """Get the time zone for a location.

    Args:
        location: The city or location name

    Returns:
        Time zone information for the location
    """
    logger.info(f"[SERVER] get_time_zone called with location: {location}")
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
    result = timezone_data.get(
        location.lower(), f"Time zone data not available for {location}"
    )
    logger.info(f"[SERVER] get_time_zone returning: {result}")
    return result


def create_agent() -> ChatAgent:
    """Create and configure the ChatAgent with appropriate client.

    Returns:
        Configured ChatAgent instance

    Raises:
        ValueError: If required environment variables are not set
    """
    logger.info("Creating ChatAgent for AG-UI server")

    # Validate required environment variables
    if not endpoint or not deployment_name:
        raise ValueError(
            "AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME must be set"
        )

    # Use DefaultAzureCredential or ManagedIdentityCredential for Azure AI Foundry authentication
    # Azure AI Foundry requires the https://ai.azure.com/.default scope
    # When running in AKS with managed identity and multiple identities exist,
    # AZURE_CLIENT_ID environment variable must be set to specify which identity to use
    if azure_client_id:
        logger.info(f"Using ManagedIdentityCredential with client_id: {azure_client_id}")
        credential = ManagedIdentityCredential(client_id=azure_client_id)
    else:
        logger.info("Using DefaultAzureCredential (will try multiple authentication methods)")
        credential = DefaultAzureCredential()

    chat_client = AzureAIAgentClient(
        endpoint=endpoint,
        model=deployment_name,
        credential=credential,
        api_version=api_version,
    )

    agent = ChatAgent(
        name="AGUIAssistant",
        instructions=(
            "You are a helpful AI assistant for the Agentic DevOps Starter application. "
            "You can help users with questions and use available tools to provide information. "
            "Use get_time_zone for time zone information about locations."
        ),
        chat_client=chat_client,
        tools=[get_time_zone],
    )

    logger.info("ChatAgent created successfully")
    return agent


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response with security headers added
        """
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Agentic DevOps Starter AG-UI Server",
        description="AG-UI server for conversational AI agent",
        version="0.1.0",
    )

    # Configure CORS to allow frontend access
    # In production (K8s), requests come through nginx proxy in same pod
    # Allow all origins since we're behind nginx
    allowed_origins = os.environ.get("CORS_ORIGINS", "*")
    if allowed_origins == "*":
        allow_origins = ["*"]
    else:
        allow_origins = [
            origin.strip() for origin in allowed_origins.split(",")
        ]

    # Development origins as fallback
    if allow_origins == ["*"] or not allow_origins:
        allow_origins = [
            "http://localhost:5173",  # Vite default dev server
            "http://127.0.0.1:5173",
            "http://localhost:3000",  # Alternative port
            "http://127.0.0.1:3000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Create the agent
    agent = create_agent()

    # Add health check endpoint for Kubernetes probes
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint for Kubernetes liveness and readiness probes.

        Returns:
            Dictionary with status message
        """
        return {"status": "healthy"}

    # Register the AG-UI endpoint at the root path
    add_agent_framework_fastapi_endpoint(app, agent, "/")

    logger.info("FastAPI app created with AG-UI endpoint and health check")
    return app


# Create the app instance only when this module is run directly or imported for web serving
# This prevents the agent from being created during test imports
app: FastAPI | None = None


def get_app() -> FastAPI:
    """Get or create the FastAPI application instance.

    Returns:
        FastAPI application instance
    """
    global app
    if app is None:
        app = create_app()
    return app


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting AG-UI server on http://0.0.0.0:5100")
    uvicorn.run(
        "agui_server:get_app",
        host="0.0.0.0",
        port=5100,
        log_level="info",
        factory=True,
    )
