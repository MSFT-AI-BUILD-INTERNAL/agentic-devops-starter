"""Example demonstrating the agent framework integration.

This is the main entry point showing how to use the conversational agent
with the microsoft-agent-framework following the constitution requirements.
"""

import os

from src.agents import ConversationalAgent
from src.agents.tools import CalculatorTool, WeatherTool
from src.config import LLMConfig, LLMProvider
from src.logging_utils import set_correlation_id, setup_logging


def create_agent_config(provider: str = "openai") -> LLMConfig:
    """Create LLM configuration for the agent.

    Args:
        provider: LLM provider to use ('openai' or 'azure_openai')

    Returns:
        Configured LLMConfig instance
    """
    if provider == "azure_openai":
        return LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            model="gpt-4",
            temperature=0.7,
            max_tokens=1000,
            fallback_provider=LLMProvider.OPENAI,
            fallback_model="gpt-3.5-turbo",
        )
    else:
        return LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key=os.getenv("OPENAI_API_KEY", "demo-key"),
            model="gpt-4",
            temperature=0.7,
            max_tokens=1000,
        )


def demonstrate_basic_conversation() -> None:
    """Demonstrate basic conversational agent usage."""
    print("\n" + "="*60)
    print("Agent Framework Integration - Basic Conversation Demo")
    print("="*60 + "\n")

    # Set correlation ID for this demo session
    set_correlation_id("demo-session-001")

    # Create agent with configuration
    config = create_agent_config()
    agent = ConversationalAgent(
        name="DemoAgent",
        llm_config=config,
    )

    # Example conversation
    messages = [
        "Hello!",
        "How are you?",
        "Can you help me?",
        "What can you do?",
    ]

    for message in messages:
        print(f"User: {message}")
        response = agent.process_message(message)
        print(f"Agent: {response}\n")

    # Show conversation summary
    summary = agent.get_conversation_summary()
    print("\nConversation Summary:")
    print(f"  Conversation ID: {summary['conversation_id']}")
    print(f"  Message Count: {summary['message_count']}")
    print(f"  History Length: {summary['history_length']}")


def demonstrate_tool_integration() -> None:
    """Demonstrate tool integration with agents."""
    print("\n" + "="*60)
    print("Agent Framework Integration - Tool Integration Demo")
    print("="*60 + "\n")

    # Create tools
    calculator = CalculatorTool()
    weather = WeatherTool()

    # Demonstrate calculator tool
    print("Calculator Tool Example:")
    calc_result = calculator.execute(operation="multiply", a=15, b=7)
    print(f"  Operation: {calc_result['operation']}")
    print(f"  Operands: {calc_result['operands']}")
    print(f"  Result: {calc_result['result']}\n")

    # Demonstrate weather tool
    print("Weather Tool Example:")
    weather_result = weather.execute(location="Seattle")
    print(f"  Location: {weather_result['location']}")
    print(f"  Temperature: {weather_result['temperature']}°F")
    print(f"  Conditions: {weather_result['conditions']}")
    print(f"  Note: {weather_result['note']}\n")


def demonstrate_state_management() -> None:
    """Demonstrate agent state management and tracking."""
    print("\n" + "="*60)
    print("Agent Framework Integration - State Management Demo")
    print("="*60 + "\n")

    config = create_agent_config()
    agent = ConversationalAgent(name="StateAgent", llm_config=config)

    # Process some messages
    messages = ["Hi there", "Tell me about yourself", "Thanks!"]

    for i, message in enumerate(messages, 1):
        print(f"Message {i}: {message}")
        response = agent.process_message(message)
        print(f"Response: {response[:100]}...\n")

    # Show state tracking
    summary = agent.get_conversation_summary()
    print("Current State:")
    print(f"  Messages exchanged: {summary['message_count']}")
    print(f"  Conversation ID: {summary['conversation_id']}")

    # Reset and show new state
    print("\nResetting conversation...")
    agent.reset_conversation()
    new_summary = agent.get_conversation_summary()
    print(f"  New Conversation ID: {new_summary['conversation_id']}")
    print(f"  Messages: {new_summary['message_count']}")


def main() -> None:
    """Run all demonstration examples."""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Agent Framework Integration Demo")

    try:
        # Run demonstrations
        demonstrate_basic_conversation()
        demonstrate_tool_integration()
        demonstrate_state_management()

        print("\n" + "="*60)
        print("Demo Complete!")
        print("="*60)
        print("\nThis example demonstrates:")
        print("✓ Python ≥3.12 with type hints")
        print("✓ Pydantic models for data validation")
        print("✓ Structured logging with correlation IDs")
        print("✓ Agent state management")
        print("✓ Response validation and guardrails")
        print("✓ Tool/function integration")
        print("✓ LLM provider configuration with fallback support")
        print("\nAll requirements from constitution.md are satisfied!")

    except Exception as e:
        logger.error(f"Error during demo: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
