"""AG-UI CLI client for the Agentic DevOps Starter application.

Interactive terminal client that communicates with the AG-UI server via
HTTP POST + SSE streaming.  Uses the same protocol the React frontend uses,
so it doubles as a quick smoke-test for the backend.
"""

import asyncio
import json
import logging
import os

import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_weather(location: str) -> str:
    """Get the current weather for a location (client-side demo tool)."""
    logger.info("[CLIENT] get_weather called: %s", location)
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


async def _stream_chat(
    client: httpx.AsyncClient,
    server_url: str,
    messages: list[dict[str, str]],
    thread_id: str,
) -> str:
    """Send messages to the AG-UI server and stream the response."""
    payload = {"messages": messages, "thread_id": thread_id, "stream": True}

    assistant_text = ""
    async with client.stream("POST", server_url, json=payload, timeout=120.0) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            try:
                event = json.loads(line[6:])
            except json.JSONDecodeError:
                continue

            match event.get("type"):
                case "TEXT_MESSAGE_CONTENT":
                    delta = event.get("delta", "")
                    print(delta, end="", flush=True)
                    assistant_text += delta
                case "RUN_ERROR":
                    print(f"\n[ERROR] {event.get('message', 'Unknown error')}")
                case "RUN_FINISHED":
                    break

    print()
    return assistant_text


async def main() -> None:
    """Interactive chat client over AG-UI SSE protocol."""
    server_url = os.environ.get("AGUI_SERVER_URL", "http://127.0.0.1:5100/")

    print("=" * 60)
    print("AG-UI Chat Client (Copilot SDK)")
    print("=" * 60)
    print(f"Server: {server_url}")
    print("Type ':q' or 'quit' to exit")
    print("=" * 60 + "\n")

    messages: list[dict[str, str]] = []
    thread_id = ""

    async with httpx.AsyncClient() as client:
        while True:
            user_input = input("\nUser: ").strip()
            if not user_input:
                continue
            if user_input.lower() in (":q", "quit"):
                print("Goodbye!")
                break

            messages.append({"role": "user", "content": user_input})
            print("Assistant: ", end="", flush=True)

            try:
                assistant_text = await _stream_chat(client, server_url, messages, thread_id)
                if assistant_text:
                    messages.append({"role": "assistant", "content": assistant_text})
            except Exception as e:
                print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(main())
