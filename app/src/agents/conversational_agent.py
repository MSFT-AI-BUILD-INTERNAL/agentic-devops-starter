"""Conversational agent implementation for demonstration."""

import uuid

from ..config import LLMConfig
from ..logging_utils import set_correlation_id
from .base_agent import BaseAgent

# Response validation constants
MIN_RESPONSE_LENGTH = 3
MAX_RESPONSE_MULTIPLIER = 4


class ConversationalAgent(BaseAgent):
    """Conversational agent that processes messages and generates responses.

    Uses the centralized :class:`~src.prompts.PromptManager` for its system
    prompt, the built-in :class:`~src.agents.tools.SkillRegistry` for skill
    discovery, and runs the :class:`~src.hooks.HarnessHook` after every
    message to ensure harness compliance.
    """

    def __init__(
        self,
        name: str = "ConversationalAgent",
        llm_config: LLMConfig | None = None,
        system_prompt: str | None = None,
    ) -> None:
        super().__init__(name, llm_config or LLMConfig(), system_prompt)
        self.initialize_state()

    def process_message(self, message: str) -> str:
        """Process a user message and generate a response.

        Steps:
        1. Validate input is non-empty.
        2. Run security check on the input.
        3. Generate a response (with skill awareness).
        4. Validate the response quality.
        5. Run post-execution harness hook.
        6. Return the response.
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        # Security check on input
        input_violations = self.validate_input_security(message)
        if input_violations:
            self.logger.warning(
                "Input security violations detected (%d); continuing with caution",
                len(input_violations),
            )

        self.add_to_history("user", message)

        # Generate response (mock implementation with skill awareness)
        response = self._generate_response(message)

        # Validate response quality before delivery
        is_valid, _ = self.validate_response(response)
        if not is_valid:
            response = "I apologize, but I cannot provide a response at this time."

        self.add_to_history("assistant", response)

        # Post-execution harness compliance hook
        self.run_harness_hook(user_input=message, agent_output=response)

        return response

    def _generate_response(self, message: str) -> str:
        """Generate a response with skill-aware routing."""
        msg = message.lower()

        # Skill-aware: route arithmetic queries to the calculator skill
        if any(w in msg for w in ("calculate", "compute", "math", "add", "subtract", "multiply", "divide")):
            skill_hint = self.describe_skills()
            return (
                f"I can help with calculations. {skill_hint}\n"
                "Please provide the operation and operands."
            )

        # Skill-aware: route weather queries to the weather skill
        if "weather" in msg or "temperature" in msg:
            return "I can check the weather for you using the get_weather skill. Which location?"

        if "hello" in msg or "hi" in msg:
            return "Hello! How can I assist you today?"
        elif "how are you" in msg:
            return "I'm functioning well, thank you! Ready to help."
        elif "help" in msg:
            skills_summary = self.describe_skills()
            return f"I'm an AI assistant. I can answer questions and assist with tasks.\n{skills_summary}"
        else:
            return f"I understand: '{message}'. This is a demo response."

    def validate_response(self, response: str) -> tuple[bool, str | None]:
        """Validate response before delivery."""
        if not response or len(response.strip()) < MIN_RESPONSE_LENGTH:
            return False, "Response is too short"
        if len(response) > self.llm_config.max_tokens * MAX_RESPONSE_MULTIPLIER:
            return False, "Response is too long"
        return True, None

    def get_conversation_summary(self) -> dict:
        """Get conversation summary."""
        if not self.state:
            return {"error": "No active conversation"}
        return {
            "conversation_id": self.state.conversation_id,
            "message_count": self.state.message_count,
            "history_length": len(self.state.history),
        }

    def reset_conversation(self) -> None:
        """Reset conversation with new ID."""
        set_correlation_id(str(uuid.uuid4()))
        self.initialize_state()
