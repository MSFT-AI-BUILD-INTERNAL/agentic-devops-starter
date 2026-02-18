"""Dev-UI server for the Agentic DevOps Starter application.

Server exposing agents through Dev-UI's built-in web interface.
Dev-UI provides a browser-based UI, OpenAI-compatible API, and entity registry.
"""

import logging
import os

from agent_framework import Agent
from agent_framework.azure import AzureAIAgentClient
from agent_framework.devui import serve
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment and setup logging
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
DEPLOYMENT = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-08-07")
PORT = int(os.environ.get("PORT", "8080"))


def get_time_zone(location: str) -> str:
    """Get the time zone for a location."""
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


def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    logger.info(f"get_weather called: {location}")
    weather_data = {
        "seattle": "Rainy, 55°F",
        "san francisco": "Foggy, 62°F",
        "new york": "Sunny, 68°F",
        "london": "Cloudy, 52°F",
        "tokyo": "Clear, 70°F",
        "sydney": "Sunny, 75°F",
        "paris": "Partly cloudy, 65°F",
        "mumbai": "Hot and humid, 85°F",
    }
    return weather_data.get(location.lower(), f"Weather data not available for {location}")


def create_agent() -> Agent:
    """Create and configure the Agent."""
    if not ENDPOINT or not DEPLOYMENT:
        raise ValueError("AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME must be set")

    logger.info(f"Creating Agent: endpoint={ENDPOINT}, deployment={DEPLOYMENT}")

    chat_client = AzureAIAgentClient(
        endpoint=ENDPOINT,
        model=DEPLOYMENT,
        credential=DefaultAzureCredential(),
        api_version=API_VERSION,
    )

    return Agent(
        name="DevUIAssistant",
        instructions=(
            "You are a helpful AI assistant. "
            "Use get_time_zone for time zone information and get_weather for weather information."
        ),
        client=chat_client,
        tools=[get_time_zone, get_weather],
    )


if __name__ == "__main__":
    logger.info(f"Starting Dev-UI server on port {PORT}")
    
    # Create the agent
    agent = create_agent()
    
    # Start Dev-UI server with the agent
    # This provides:
    # - Web UI at http://0.0.0.0:{PORT}
    # - OpenAI-compatible API at http://0.0.0.0:{PORT}/v1
    # - Health check at http://0.0.0.0:{PORT}/health
    serve(
        entities=[agent],
        host="0.0.0.0",
        port=PORT,
        auto_open=False,  # Don't auto-open browser in container
    )
