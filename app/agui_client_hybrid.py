"""AG-UI client with ChatAgent wrapper demonstrating hybrid tool execution.

This client shows the HYBRID pattern where both client-side and server-side tools
can execute in the same conversation:
- Server-side: get_time_zone (executes on server)
- Client-side: get_weather (executes on client)

Follows all constitution requirements:
- Python ≥3.12 with type hints
- microsoft-agent-framework integration
- Pydantic models and type safety
- Structured logging
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Client-side tool - executes locally
@ai_function(description="Get the current weather for a location.")
def get_weather(location: Annotated[str, "The city or location name"]) -> str:
    """Get the current weather for a location.

    This tool executes client-side via @use_function_invocation decorator.

    Args:
        location: The city or location name

    Returns:
        Weather information for the location
    """
    logger.info(f"[CLIENT] get_weather called with location: {location}")
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
    result = weather_data.get(
        location.lower(), f"Weather data not available for {location}"
    )
    logger.info(f"[CLIENT] get_weather returning: {result}")
    return result


async def main() -> None:
    """Demonstrate ChatAgent + AGUIChatClient hybrid tool execution."""
    server_url = os.environ.get("AGUI_SERVER_URL", "http://127.0.0.1:5100/")

    print("=" * 70)
    print("ChatAgent + AGUIChatClient: Hybrid Tool Execution Demo")
    print("=" * 70)
    print(f"\nServer: {server_url}")
    print("\nThis demo shows:")
    print("  1. AgentThread maintains conversation state")
    print("  2. Client-side tools (get_weather) execute locally")
    print("  3. Server-side tools (get_time_zone) execute on server")
    print("  4. HYBRID: Both client and server tools work together\n")
    print("Type ':q' or 'quit' to exit")
    print("=" * 70 + "\n")

    try:
        # Create remote client
        async with AGUIChatClient(endpoint=server_url) as remote_client:
            # Wrap in ChatAgent for conversation history and tool management
            agent = ChatAgent(
                name="remote_assistant",
                instructions=(
                    "You are a helpful assistant. "
                    "Use get_weather for weather information and "
                    "get_time_zone for time zone information. "
                    "Remember user information across the conversation."
                ),
                chat_client=remote_client,
                tools=[get_weather],  # Client-side tools
            )

            # Create a thread to maintain conversation state
            thread = agent.get_new_thread()

            # Interactive conversation loop
            while True:
                user_input = input("\nUser: ")
                if not user_input.strip():
                    print("Message cannot be empty.")
                    continue

                if user_input.lower() in (":q", "quit"):
                    print("Goodbye!")
                    break

                print("Assistant: ", end="", flush=True)

                try:
                    # Stream the agent's response
                    async for chunk in agent.run_stream(user_input, thread=thread):
                        if chunk.text:
                            print(chunk.text, end="", flush=True)
                    print()  # New line after response

                except Exception as e:
                    print(f"\nError: {e}")
                    print("Please check if the server is running.")

    except ConnectionError as e:
        print(f"\nConnection Error: {e}")
        print("\nMake sure the AG-UI server is running:")
        print("  python agui_server.py")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


async def run_demo_conversation() -> None:
    """Run a predefined demo conversation to showcase hybrid tools."""
    server_url = os.environ.get("AGUI_SERVER_URL", "http://127.0.0.1:5100/")

    print("=" * 70)
    print("AUTOMATED DEMO: Hybrid Tool Execution")
    print("=" * 70 + "\n")

    try:
        async with AGUIChatClient(endpoint=server_url) as remote_client:
            agent = ChatAgent(
                name="demo_assistant",
                instructions=(
                    "You are a helpful assistant. "
                    "Use get_weather for weather and get_time_zone for time zones."
                ),
                chat_client=remote_client,
                tools=[get_weather],
            )

            thread = agent.get_new_thread()

            # Demo conversation
            demo_messages = [
                "My name is Alice and I live in Seattle",
                "What's my name?",
                "What's the weather like in Seattle?",
                "What time zone is Seattle in?",
                "How about the weather and time zone in Tokyo?",
            ]

            for message in demo_messages:
                print(f"User: {message}\n")
                print("Assistant: ", end="", flush=True)

                async for chunk in agent.run_stream(message, thread=thread):
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                print("\n")

            print("=" * 70)
            print("Demo complete! Notice how:")
            print("  - get_weather (client tool) executed locally")
            print("  - get_time_zone (server tool) executed on server")
            print("  - Both tools were used seamlessly in the same conversation")
            print("=" * 70)

    except Exception as e:
        print(f"Demo error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run interactive mode by default
    # To run the demo conversation, uncomment the line below:
    # asyncio.run(run_demo_conversation())

    asyncio.run(main())
