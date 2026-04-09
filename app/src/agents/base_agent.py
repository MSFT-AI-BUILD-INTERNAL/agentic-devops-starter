"""Base agent class for demonstration purposes."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from ..config import LLMConfig
from ..hooks import HarnessHook, HarnessViolationReport
from ..logging_utils import get_correlation_id, setup_logging
from ..prompts import PromptManager
from ..security import SecurityValidator, SecurityViolation
from .tools import SkillRegistry, build_default_registry


class AgentState(BaseModel):
    """State model for agent conversations."""
    conversation_id: str = Field(description="Unique conversation identifier")
    message_count: int = Field(default=0)
    history: list[dict[str, str]] = Field(default_factory=list)


class BaseAgent(ABC):
    """Base class for conversational agents.

    Provides integrated:
    - Prompt management via :class:`~src.prompts.PromptManager`
    - Input/output security validation via :class:`~src.security.SecurityValidator`
    - Skill discovery and invocation via :class:`~src.agents.tools.SkillRegistry`
    - Post-execution harness compliance via :class:`~src.hooks.HarnessHook`
    """

    def __init__(
        self,
        name: str,
        llm_config: LLMConfig,
        system_prompt: str | None = None,
        prompt_manager: PromptManager | None = None,
        skill_registry: SkillRegistry | None = None,
        harness_hook: HarnessHook | None = None,
        security_validator: SecurityValidator | None = None,
    ) -> None:
        self.name = name
        self.llm_config = llm_config
        self._prompt_manager = prompt_manager or PromptManager()
        self._skill_registry = skill_registry or build_default_registry()
        self._harness_hook = harness_hook or HarnessHook(fail_on_violation=False)
        self._security_validator = security_validator or SecurityValidator()

        # Resolve system prompt: explicit arg > prompt manager key > default
        prompt_key = f"{name.lower()}.system"
        if system_prompt is not None:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = self._prompt_manager.get(prompt_key)

        self.logger = setup_logging()
        self.state: AgentState | None = None
        self.logger.info(f"Initialized agent '{name}'")

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------

    def validate_input_security(self, text: str) -> list[SecurityViolation]:
        """Run security validation on user input and return any violations."""
        violations = self._security_validator.validate_input(text)
        for v in violations:
            self.logger.warning(
                "Security violation in input [%s/%s]: %s",
                v.category, v.severity, v.message,
            )
        return violations

    def validate_output_security(self, text: str) -> list[SecurityViolation]:
        """Run security validation on agent output and return any violations."""
        violations = self._security_validator.validate_output(text)
        for v in violations:
            self.logger.warning(
                "Security violation in output [%s/%s]: %s",
                v.category, v.severity, v.message,
            )
        return violations

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    @property
    def skill_registry(self) -> SkillRegistry:
        """Return the agent's skill registry."""
        return self._skill_registry

    def describe_skills(self) -> str:
        """Return a human-readable description of all registered skills."""
        return self._skill_registry.describe()

    # ------------------------------------------------------------------
    # Post-execution hook
    # ------------------------------------------------------------------

    def run_harness_hook(self, user_input: str, agent_output: str) -> HarnessViolationReport:
        """Run the post-execution harness compliance hook."""
        return self._harness_hook.run(user_input=user_input, agent_output=agent_output)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def process_message(self, message: str) -> str:
        """Process a user message and generate a response."""

    @abstractmethod
    def validate_response(self, response: str) -> tuple[bool, str | None]:
        """Validate response before delivery."""
