"""Tests for conversational agent."""

import pytest

from src.agents import ConversationalAgent
from src.config import LLMConfig


def test_agent_initialization() -> None:
    """Test agent initialization."""
    config = LLMConfig(api_key="test-key")
    agent = ConversationalAgent(name="TestAgent", llm_config=config)

    assert agent.name == "TestAgent"
    assert agent.llm_config.api_key == "test-key"
    assert agent.state is not None
    assert agent.state.message_count == 0


def test_agent_process_message() -> None:
    """Test processing a message."""
    config = LLMConfig(api_key="test-key")
    agent = ConversationalAgent(llm_config=config)

    response = agent.process_message("Hello")

    assert isinstance(response, str)
    assert len(response) > 0
    assert agent.state.message_count == 2  # User message + assistant response


def test_agent_empty_message() -> None:
    """Test that empty messages raise ValueError."""
    config = LLMConfig(api_key="test-key")
    agent = ConversationalAgent(llm_config=config)

    with pytest.raises(ValueError, match="Message cannot be empty"):
        agent.process_message("")

    with pytest.raises(ValueError, match="Message cannot be empty"):
        agent.process_message("   ")


def test_agent_conversation_history() -> None:
    """Test conversation history tracking."""
    config = LLMConfig(api_key="test-key")
    agent = ConversationalAgent(llm_config=config)

    agent.process_message("First message")
    agent.process_message("Second message")

    assert len(agent.state.history) == 4  # 2 user messages + 2 responses
    assert agent.state.history[0]["role"] == "user"
    assert agent.state.history[1]["role"] == "assistant"
    assert agent.state.message_count == 4


def test_agent_response_validation() -> None:
    """Test response validation."""
    config = LLMConfig(api_key="test-key")
    agent = ConversationalAgent(llm_config=config)

    # Valid response
    is_valid, error = agent.validate_response("This is a valid response")
    assert is_valid is True
    assert error is None

    # Empty response
    is_valid, error = agent.validate_response("")
    assert is_valid is False
    assert "too short" in error.lower()

    # Too short response
    is_valid, error = agent.validate_response("Hi")
    assert is_valid is False


def test_agent_conversation_summary() -> None:
    """Test getting conversation summary."""
    config = LLMConfig(api_key="test-key")
    agent = ConversationalAgent(llm_config=config)

    agent.process_message("Test message")

    summary = agent.get_conversation_summary()

    assert "conversation_id" in summary
    assert summary["message_count"] == 2
    assert summary["history_length"] == 2


def test_agent_reset_conversation() -> None:
    """Test resetting conversation."""
    config = LLMConfig(api_key="test-key")
    agent = ConversationalAgent(llm_config=config)

    # Process some messages
    agent.process_message("Message 1")
    agent.process_message("Message 2")

    old_conversation_id = agent.state.conversation_id

    # Reset
    agent.reset_conversation()

    # Verify reset
    assert agent.state.message_count == 0
    assert len(agent.state.history) == 0
    assert agent.state.conversation_id != old_conversation_id


def test_agent_greeting_responses() -> None:
    """Test agent responses to greetings."""
    config = LLMConfig(api_key="test-key")
    agent = ConversationalAgent(llm_config=config)

    response = agent.process_message("Hello")
    assert "hello" in response.lower() or "hi" in response.lower()

    response = agent.process_message("Hi there")
    assert len(response) > 0


def test_agent_help_response() -> None:
    """Test agent response to help request."""
    config = LLMConfig(api_key="test-key")
    agent = ConversationalAgent(llm_config=config)

    response = agent.process_message("I need help")
    assert "help" in response.lower() or "assist" in response.lower()
