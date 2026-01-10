"""AG-UI basic client for the Agentic DevOps Starter application.

This client demonstrates basic interaction with the AG-UI server using AGUIChatClient.
It provides a command-line interface for streaming conversations with the agent.

Follows all constitution requirements:
- Python ≥3.12 with type hints
- Pydantic models for validation
- Structured logging
"""

import asyncio
import os

from agent_framework import TextContent
from agent_framework.ag_ui import AGUIChatClient


async def main() -> None:
    """Main client loop demonstrating AGUIChatClient usage."""
    # Get server URL from environment or use default
    server_url = os.environ.get("AGUI_SERVER_URL", "http://127.0.0.1:5100/")
    print(f"Connecting to AG-UI server at: {server_url}\n")
    print("Type ':q' or 'quit' to exit\n")

    # Create client with context manager for automatic cleanup
    async with AGUIChatClient(endpoint=server_url) as client:
        thread_id: str | None = None

        try:
            while True:
                # Get user input
                message = input("\nUser: ")
                if not message.strip():
                    print("Message cannot be empty.")
                    continue

                if message.lower() in (":q", "quit"):
                    print("Goodbye!")
                    break

                # Send message and stream the response
                print("Assistant: ", end="", flush=True)

                # Use metadata to maintain conversation continuity
                metadata = {"thread_id": thread_id} if thread_id else None

                try:
                    async for update in client.get_streaming_response(
                        message, metadata=metadata
                    ):
                        # Extract thread ID from first update
                        if not thread_id and update.additional_properties:
                            thread_id = update.additional_properties.get("thread_id")
                            if thread_id:
                                print(f"\n[Thread: {thread_id}]")
                                print("Assistant: ", end="", flush=True)

                        # Stream text content as it arrives
                        for content in update.contents:
                            if isinstance(content, TextContent) and content.text:
                                print(content.text, end="", flush=True)

                    print()  # New line after response

                except Exception as e:
                    print(f"\nError getting response: {e}")
                    print("Please check if the server is running.")

        except KeyboardInterrupt:
            print("\n\nExiting...")
        except Exception as e:
            print(f"\nAn error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
