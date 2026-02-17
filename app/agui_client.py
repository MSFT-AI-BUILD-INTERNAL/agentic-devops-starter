"""AG-UI client for the Agentic DevOps Starter application.

This client demonstrates hybrid tool execution where both client-side and
server-side tools can execute in the same conversation.
"""

import asyncio
import logging
import os
from typing import Annotated

from agent_framework import ChatAgent, ai_function
from agent_framework.ag_ui import AGUIChatClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Client-side tool - executes locally
@ai_function(description="Get the current weather for a location.")
def get_weather(location: Annotated[str, "The city or location name"]) -> str:
    """Get the current weather for a location (client-side tool)."""
    logger.info(f"[CLIENT] get_weather called: {location}")
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


async def main() -> None:
    """Interactive chat client with hybrid tool execution."""
    server_url = os.environ.get("AGUI_SERVER_URL", "http://127.0.0.1:5100/")

    print("=" * 60)
    print("AG-UI Chat Client")
    print("=" * 60)
    print(f"Server: {server_url}")
    print("Tools: get_weather (client), get_time_zone (server)")
    print("Type ':q' or 'quit' to exit")
    print("=" * 60 + "\n")

    try:
        async with AGUIChatClient(endpoint=server_url) as remote_client:
            agent = ChatAgent(
                name="assistant",
                instructions=(
                    "You are a helpful assistant. "
                    "Use get_weather for weather and get_time_zone for time zones."
                ),
                chat_client=remote_client,
                tools=[get_weather],
            )
            thread = agent.get_new_thread()

            while True:
                user_input = input("\nUser: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in (":q", "quit"):
                    print("Goodbye!")
                    break

                print("Assistant: ", end="", flush=True)
                try:
                    async for chunk in agent.run_stream(user_input, thread=thread):
                        if chunk.text:
                            print(chunk.text, end="", flush=True)
                    print()
                except Exception as e:
                    print(f"\nError: {e}")

    except ConnectionError as e:
        print(f"\nConnection Error: {e}")
        print("Make sure the AG-UI server is running: python agui_server.py")


if __name__ == "__main__":
    asyncio.run(main())
