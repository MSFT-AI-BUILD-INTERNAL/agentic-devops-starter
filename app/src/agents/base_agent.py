"""Base agent class for demonstration purposes."""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field
from ..config import LLMConfig
from ..logging_utils import get_correlation_id, setup_logging


class AgentState(BaseModel):
    """State model for agent conversations."""
    conversation_id: str = Field(description="Unique conversation identifier")
    message_count: int = Field(default=0)
    history: list[dict[str, str]] = Field(default_factory=list)


class BaseAgent(ABC):
    """Base class for conversational agents."""

    def __init__(self, name: str, llm_config: LLMConfig, system_prompt: str | None = None) -> None:
        self.name = name
        self.llm_config = llm_config
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
        self.logger = setup_logging()
        self.state: AgentState | None = None
        self.logger.info(f"Initialized agent '{name}'")

    def initialize_state(self, conversation_id: str | None = None) -> AgentState:
        """Initialize or reset agent state."""
        self.state = AgentState(conversation_id=conversation_id or get_correlation_id())
        return self.state

    def add_to_history(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        if self.state is None:
            self.initialize_state()
        if self.state:
            self.state.history.append({"role": role, "content": content})
            self.state.message_count += 1

    @abstractmethod
    def process_message(self, message: str) -> str:
        """Process a user message and generate a response."""
        pass

    @abstractmethod
    def validate_response(self, response: str) -> tuple[bool, str | None]:
        """Validate response before delivery."""
        pass
