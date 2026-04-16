"""Conversational agent implementation for demonstration."""

import uuid

from ..config import LLMConfig
from ..logging_utils import set_correlation_id
from .base_agent import BaseAgent

# Response validation constants
MIN_RESPONSE_LENGTH = 3
MAX_RESPONSE_MULTIPLIER = 4


class ConversationalAgent(BaseAgent):
    """Conversational agent that processes messages and generates responses."""

    def __init__(
        self,
        name: str = "ConversationalAgent",
        llm_config: LLMConfig | None = None,
        system_prompt: str | None = None,
    ) -> None:
        super().__init__(name, llm_config or LLMConfig(), system_prompt)
        self.initialize_state()

    def process_message(self, message: str) -> str:
        """Process a user message and generate a response."""
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        self.add_to_history("user", message)

        # Generate response (mock implementation for demo)
        response = self._generate_response(message)

        # Validate before delivery
        is_valid, _ = self.validate_response(response)
        if not is_valid:
            response = "I apologize, but I cannot provide a response at this time."

        self.add_to_history("assistant", response)
        return response

    def _generate_response(self, message: str) -> str:
        """Generate a mock response based on message patterns."""
        msg = message.lower()
        if "hello" in msg or "hi" in msg:
            return "Hello! How can I assist you today?"
        elif "how are you" in msg:
            return "I'm functioning well, thank you! Ready to help."
        elif "help" in msg:
            return "I'm an AI assistant. I can answer questions and assist with tasks."
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
