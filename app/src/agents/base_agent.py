"""Base agent class for demonstration purposes."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from ..config import LLMConfig
from ..hooks.harness_hook import HarnessHook, HarnessReport
from ..logging_utils import get_correlation_id, setup_logging
from ..prompts.prompt_manager import PromptManager
from ..security.validator import SecurityValidator


class AgentState(BaseModel):
    """State model for agent conversations."""

    conversation_id: str = Field(description="Unique conversation identifier")
    message_count: int = Field(default=0)
    history: list[dict[str, str]] = Field(default_factory=list)


class BaseAgent(ABC):
    """Base class for conversational agents.

    Integrates security validation, prompt management, and harness hooks.
    Every subclass **must** call the following in its ``process_message()``
    implementation (in this order):

    1. Validate input is non-empty.
    2. ``validate_input_security(message)``
    3. Generate response.
    4. ``validate_response(response)``
    5. ``run_harness_hook(message, response)``  ← mandatory.
    """

    def __init__(self, name: str, llm_config: LLMConfig, system_prompt: str | None = None) -> None:
        self.name = name
        self.llm_config = llm_config
        self.logger = setup_logging()
        self.state: AgentState | None = None

        # Load system prompt from PromptManager; fall back to explicit arg or default.
        prompt_manager = PromptManager()
        resolved = prompt_manager.get(f"{name.lower()}.system")
        self.system_prompt = system_prompt or resolved

        self._security_validator = SecurityValidator()
        self._harness_hook = HarnessHook()

        self.logger.info("Initialized agent '%s'", name)

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

    def validate_input_security(self, message: str) -> None:
        """Validate user input against security rules.

        Raises:
            SecurityViolationError: If the message contains a blocked pattern.
        """
        self._security_validator.validate_input(message)

    def validate_output_security(self, response: str) -> None:
        """Validate agent output against security rules.

        Raises:
            SecurityViolationError: If the response contains a blocked pattern.
        """
        self._security_validator.validate_output(response)

    def run_harness_hook(self, user_input: str, agent_output: str) -> HarnessReport:
        """Run post-execution harness compliance validation.

        This **must** be called at the end of every ``process_message()`` cycle.

        Args:
            user_input: The original user message.
            agent_output: The agent's response.

        Returns:
            A ``HarnessReport`` describing the outcome.
        """
        return self._harness_hook.run(user_input, agent_output)

    @abstractmethod
    def process_message(self, message: str) -> str:
        """Process a user message and generate a response."""

    @abstractmethod
    def validate_response(self, response: str) -> tuple[bool, str | None]:
        """Validate response before delivery."""
