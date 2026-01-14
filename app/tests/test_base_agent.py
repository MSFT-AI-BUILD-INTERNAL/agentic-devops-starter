"""Tests for base agent class."""

import logging

from src.agents.base_agent import AgentState, BaseAgent
from src.config import LLMConfig


# Concrete implementation of BaseAgent for testing
class ConcreteTestAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing purposes."""

    def process_message(self, message: str) -> str:
        """Process a message and return response."""
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        self.add_to_history("user", message)
        response = f"Echo: {message}"
        self.add_to_history("assistant", response)

        return response

    def validate_response(self, response: str) -> tuple[bool, str | None]:
        """Validate a response."""
        if not response or len(response.strip()) < 3:
            return False, "Response is too short"
        return True, None


def test_agent_state_initialization() -> None:
    """Test AgentState initialization."""
    state = AgentState(conversation_id="test-123")

    assert state.conversation_id == "test-123"
    assert state.message_count == 0
    assert state.context == {}
    assert state.history == []


def test_agent_state_with_context() -> None:
    """Test AgentState with context data."""
    context_data = {"user_id": "user-123", "session": "session-456"}
    state = AgentState(
        conversation_id="test-123",
        context=context_data
    )

    assert state.context == context_data
    assert state.context["user_id"] == "user-123"


def test_base_agent_initialization() -> None:
    """Test BaseAgent initialization."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(
        name="ConcreteTestAgent",
        llm_config=config
    )

    assert agent.name == "ConcreteTestAgent"
    assert agent.llm_config == config
    assert agent.system_prompt is not None
    assert agent.logger is not None
    assert isinstance(agent.logger, logging.Logger)


def test_base_agent_with_custom_system_prompt() -> None:
    """Test BaseAgent with custom system prompt."""
    config = LLMConfig(api_key="test-key")
    custom_prompt = "You are a specialized assistant."

    agent = ConcreteTestAgent(
        name="CustomAgent",
        llm_config=config,
        system_prompt=custom_prompt
    )

    assert agent.system_prompt == custom_prompt


def test_base_agent_default_system_prompt() -> None:
    """Test BaseAgent uses default system prompt."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(
        name="DefaultAgent",
        llm_config=config
    )

    # Should have a default prompt
    assert agent.system_prompt is not None
    assert len(agent.system_prompt) > 0
    assert "helpful" in agent.system_prompt.lower()


def test_initialize_state_with_id() -> None:
    """Test initialize_state with provided conversation ID."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)

    conversation_id = "custom-conversation-123"
    state = agent.initialize_state(conversation_id)

    assert state.conversation_id == conversation_id
    assert state.message_count == 0
    assert agent.state == state


def test_initialize_state_generates_id() -> None:
    """Test initialize_state generates ID if not provided."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)

    state = agent.initialize_state()

    assert state.conversation_id is not None
    assert len(state.conversation_id) > 0


def test_add_to_history() -> None:
    """Test adding messages to conversation history."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)
    agent.initialize_state()

    agent.add_to_history("user", "Hello")
    agent.add_to_history("assistant", "Hi there!")

    assert agent.state is not None
    assert len(agent.state.history) == 2
    assert agent.state.history[0]["role"] == "user"
    assert agent.state.history[0]["content"] == "Hello"
    assert agent.state.history[1]["role"] == "assistant"
    assert agent.state.history[1]["content"] == "Hi there!"
    assert agent.state.message_count == 2


def test_add_to_history_initializes_state() -> None:
    """Test add_to_history initializes state if needed."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)

    # Don't initialize state manually
    assert agent.state is None

    # Adding to history should initialize state
    agent.add_to_history("user", "Test message")

    assert agent.state is not None
    assert len(agent.state.history) == 1


def test_log_interaction() -> None:
    """Test logging LLM interactions."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)

    # Should not raise any exception
    agent.log_interaction(
        "test_operation",
        {"detail": "test detail"}
    )


def test_process_message_abstract_method() -> None:
    """Test that process_message must be implemented."""
    # Verify abstract method is present
    assert hasattr(BaseAgent, "process_message")

    # ConcreteTestAgent implements it
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)

    response = agent.process_message("Hello")
    assert response is not None


def test_validate_response_abstract_method() -> None:
    """Test that validate_response must be implemented."""
    # Verify abstract method is present
    assert hasattr(BaseAgent, "validate_response")

    # ConcreteTestAgent implements it
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)

    is_valid, error = agent.validate_response("Valid response")
    assert is_valid is True
    assert error is None


def test_agent_state_tracks_message_count() -> None:
    """Test that AgentState correctly tracks message count."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)
    agent.initialize_state()

    initial_count = agent.state.message_count

    agent.add_to_history("user", "Message 1")
    assert agent.state.message_count == initial_count + 1

    agent.add_to_history("assistant", "Response 1")
    assert agent.state.message_count == initial_count + 2


def test_agent_state_history_structure() -> None:
    """Test that history messages have correct structure."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)
    agent.initialize_state()

    agent.add_to_history("user", "Test message")

    message = agent.state.history[0]
    assert "role" in message
    assert "content" in message
    assert isinstance(message["role"], str)
    assert isinstance(message["content"], str)


def test_multiple_agents_have_separate_state() -> None:
    """Test that multiple agent instances maintain separate state."""
    config = LLMConfig(api_key="test-key")

    agent1 = ConcreteTestAgent(name="Agent1", llm_config=config)
    agent1.initialize_state("conversation-1")
    agent1.add_to_history("user", "Message to agent 1")

    agent2 = ConcreteTestAgent(name="Agent2", llm_config=config)
    agent2.initialize_state("conversation-2")
    agent2.add_to_history("user", "Message to agent 2")

    # Each agent should have its own state
    assert agent1.state.conversation_id != agent2.state.conversation_id
    assert len(agent1.state.history) == 1
    assert len(agent2.state.history) == 1
    assert agent1.state.history[0]["content"] != agent2.state.history[0]["content"]


def test_agent_logger_configuration() -> None:
    """Test that agent logger is properly configured."""
    config = LLMConfig(api_key="test-key")
    agent = ConcreteTestAgent(name="ConcreteTestAgent", llm_config=config)

    # Logger should be configured
    assert agent.logger is not None
    assert agent.logger.name == "agentic_devops"
    assert agent.logger.level == logging.INFO
