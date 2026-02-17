"""Demo script for the agent framework integration.

This demonstrates the local ConversationalAgent and tools.
For the actual server, use: python agui_server.py
"""

from src.agents import ConversationalAgent
from src.agents.tools import CalculatorTool, WeatherTool
from src.logging_utils import setup_logging


def main() -> None:
    """Run demonstration examples."""
    logger = setup_logging()
    logger.info("Starting Agent Framework Demo")

    print("\n" + "=" * 50)
    print("Agent Framework Demo")
    print("=" * 50)

    # Demo 1: Conversational Agent
    print("\n--- Conversational Agent ---")
    agent = ConversationalAgent(name="DemoAgent")

    for msg in ["Hello!", "How are you?", "Can you help me?"]:
        print(f"User: {msg}")
        print(f"Agent: {agent.process_message(msg)}\n")

    summary = agent.get_conversation_summary()
    print(f"Summary: {summary['message_count']} messages exchanged")

    # Demo 2: Tools
    print("\n--- Tools Demo ---")
    calc = CalculatorTool()
    result = calc.execute(operation="multiply", a=15, b=7)
    print(f"Calculator: 15 × 7 = {result['result']}")

    weather = WeatherTool()
    w = weather.execute(location="Seattle")
    print(f"Weather: {w['location']} - {w['temperature']}°F, {w['conditions']}")

    print("\n" + "=" * 50)
    print("Demo Complete!")
    print("=" * 50)
    print("\nTo run the actual server: python agui_server.py")


if __name__ == "__main__":
    main()
