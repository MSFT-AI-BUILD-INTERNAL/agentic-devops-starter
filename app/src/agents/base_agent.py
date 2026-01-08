"""Base agent class for microsoft-agent-framework integration."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from ..config import LLMConfig
from ..logging_utils import get_correlation_id, log_llm_interaction, setup_logging


class AgentState(BaseModel):
    """State model for agent conversations.

    This tracks the conversation history and context for the agent.
    """

    conversation_id: str = Field(
        description="Unique identifier for the conversation"
    )
    message_count: int = Field(
        default=0,
        description="Number of messages in the conversation"
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context information"
    )
    history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Conversation history"
    )


class BaseAgent(ABC):
    """Base class for all agents using microsoft-agent-framework.

    This class provides the foundation for building conversational agents
    with proper logging, state management, and LLM integration.
    """

    def __init__(
        self,
        name: str,
        llm_config: LLMConfig,
        system_prompt: str | None = None,
    ) -> None:
        """Initialize the base agent.

        Args:
            name: Name of the agent
            llm_config: Configuration for LLM provider
            system_prompt: Optional system prompt for the agent
        """
        self.name = name
        self.llm_config = llm_config
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.logger = setup_logging()
        self.state: AgentState | None = None

        self.logger.info(
            f"Initialized agent '{name}' with provider: {llm_config.provider}"
        )

    def _default_system_prompt(self) -> str:
        """Get default system prompt for the agent.

        Returns:
            Default system prompt
        """
        return (
            "You are a helpful AI assistant. Provide accurate, "
            "helpful, and safe responses to user queries."
        )

    def initialize_state(self, conversation_id: str | None = None) -> AgentState:
        """Initialize or reset agent state.

        Args:
            conversation_id: Optional conversation ID, generates new if not provided

        Returns:
            Initialized agent state
        """
        if conversation_id is None:
            conversation_id = get_correlation_id()

        self.state = AgentState(conversation_id=conversation_id)
        self.logger.info(f"Initialized state for conversation: {conversation_id}")
        return self.state

    def add_to_history(self, role: str, content: str) -> None:
        """Add a message to the conversation history.

        Args:
            role: Role of the message sender (e.g., 'user', 'assistant')
            content: Content of the message
        """
        if self.state is None:
            self.initialize_state()

        if self.state:
            self.state.history.append({"role": role, "content": content})
            self.state.message_count += 1

    def log_interaction(self, operation: str, details: dict[str, Any]) -> None:
        """Log an LLM interaction.

        Args:
            operation: Type of operation being performed
            details: Details about the interaction
        """
        log_llm_interaction(self.logger, operation, details)

    @abstractmethod
    def process_message(self, message: str) -> str:
        """Process a user message and generate a response.

        Args:
            message: User message to process

        Returns:
            Agent's response
        """
        pass

    @abstractmethod
    def validate_response(self, response: str) -> tuple[bool, str | None]:
        """Validate an LLM response before delivery.

        This implements the constitutional requirement for response validation
        to check for harmful content, hallucinations, and off-topic responses.

        Args:
            response: Response to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
