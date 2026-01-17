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
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from agent_framework.azure import AzureAIAgentClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.logging_utils import setup_logging

# Load environment variables
load_dotenv()

# Setup structured logging
logger = setup_logging()

# Read configuration from environment
endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
deployment_name = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-08-07")
openai_api_key = os.environ.get("OPENAI_API_KEY")


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
    from typing import Union
    
    from agent_framework.openai import OpenAIChatClient

    logger.info("Creating ChatAgent for AG-UI server")

    # Try Azure AI Foundry first, fall back to OpenAI
    chat_client: Union[AzureAIAgentClient, OpenAIChatClient]
    if endpoint and deployment_name:
        logger.info(f"Using Azure AI Foundry client with DefaultAzureCredential (API version: {api_version})")
        
        # Use DefaultAzureCredential for Azure AI Foundry authentication
        # Azure AI Foundry requires the https://ai.azure.com/.default scope
        credential = DefaultAzureCredential()
        
        chat_client = AzureAIAgentClient(
            endpoint=endpoint,
            model=deployment_name,
            credential=credential,
            api_version=api_version,
        )
    elif openai_api_key:
        logger.info("Using OpenAI client")

        chat_client = OpenAIChatClient(
            api_key=openai_api_key,
            model_id="gpt-4o-mini",
        )
    else:
        raise ValueError(
            "Either AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME, "
            "or OPENAI_API_KEY must be set"
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite default dev server
            "http://127.0.0.1:5173",
            "http://localhost:3000",  # Alternative port
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create the agent
    agent = create_agent()

    # Register the AG-UI endpoint at the root path
    add_agent_framework_fastapi_endpoint(app, agent, "/")

    logger.info("FastAPI app created with AG-UI endpoint")
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
