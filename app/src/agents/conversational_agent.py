"""Conversational agent implementation using microsoft-agent-framework."""

import re
import uuid
from typing import Any

from ..config import LLMConfig
from ..logging_utils import set_correlation_id
from .base_agent import BaseAgent


class ConversationalAgent(BaseAgent):
    """A conversational agent that processes user messages and generates responses.

    This implementation demonstrates the microsoft-agent-framework integration
    following the constitution requirements:
    - Type safety with Pydantic models
    - Structured logging with correlation IDs
    - Response validation and guardrails
    - State management for conversations
    """

    def __init__(
        self,
        name: str = "ConversationalAgent",
        llm_config: LLMConfig | None = None,
        system_prompt: str | None = None,
    ) -> None:
        """Initialize the conversational agent.

        Args:
            name: Name of the agent
            llm_config: Configuration for LLM provider, uses defaults if not provided
            system_prompt: Optional system prompt for the agent
        """
        if llm_config is None:
            llm_config = LLMConfig()

        if system_prompt is None:
            system_prompt = self._get_conversational_prompt()

        super().__init__(name, llm_config, system_prompt)

        # Initialize conversation state
        self.initialize_state()

    def _get_conversational_prompt(self) -> str:
        """Get the conversational agent system prompt.

        Returns:
            System prompt for conversational interactions
        """
        return (
            "You are a helpful and knowledgeable AI assistant. "
            "Provide accurate, clear, and concise responses to user queries. "
            "If you're unsure about something, acknowledge it. "
            "Be professional, respectful, and helpful. "
            "Avoid harmful, offensive, or inappropriate content."
        )

    def process_message(self, message: str) -> str:
        """Process a user message and generate a response.

        This method demonstrates the complete agent workflow:
        1. Validate input
        2. Add to conversation history
        3. Generate response (simulated for framework example)
        4. Validate response
        5. Log interaction

        Args:
            message: User message to process

        Returns:
            Agent's response

        Raises:
            ValueError: If message is empty or response validation fails
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        # Add user message to history
        self.add_to_history("user", message)

        # Log the interaction start
        self.log_interaction(
            "process_message",
            {
                "message_length": len(message),
                "conversation_id": self.state.conversation_id if self.state else "unknown",
                "message_count": self.state.message_count if self.state else 0,
            }
        )

        # Generate response (in production, this would call the actual LLM)
        response = self._generate_response(message)

        # Validate response before delivery
        is_valid, error_message = self.validate_response(response)
        if not is_valid:
            self.logger.warning(f"Response validation failed: {error_message}")
            response = "I apologize, but I cannot provide a response at this time."

        # Add assistant response to history
        self.add_to_history("assistant", response)

        # Log the successful interaction
        self.log_interaction(
            "response_generated",
            {
                "response_length": len(response),
                "conversation_id": self.state.conversation_id if self.state else "unknown",
                "validation_passed": is_valid,
            }
        )

        return response

    def _generate_response(self, message: str) -> str:
        """Generate a response to the user message.

        NOTE: This is a simplified example. In production, this would:
        1. Build the prompt with system message and conversation history
        2. Call the LLM API (OpenAI, Azure OpenAI, etc.)
        3. Handle fallback if primary provider fails
        4. Track token usage for cost monitoring

        Args:
            message: User message

        Returns:
            Generated response
        """
        # For demonstration purposes, we'll create a simple echo-style response
        # In production, this would be replaced with actual LLM API calls

        # Simulate response generation based on message patterns
        message_lower = message.lower()

        if "hello" in message_lower or "hi" in message_lower:
            return (
                "Hello! I'm here to help you. How can I assist you today?"
            )
        elif "how are you" in message_lower:
            return (
                "I'm functioning well, thank you for asking! "
                "I'm ready to help with any questions you have."
            )
        elif "help" in message_lower:
            return (
                "I'm an AI assistant built with the microsoft-agent-framework. "
                "I can help answer questions, provide information, and assist "
                "with various tasks. What would you like to know?"
            )
        else:
            return (
                f"I understand you said: '{message}'. "
                "This is a demonstration of the agent framework integration. "
                "In production, I would provide a more intelligent response "
                "using the configured LLM provider."
            )

    def validate_response(self, response: str) -> tuple[bool, str | None]:
        """Validate an LLM response before delivery.

        This implements guardrails for:
        - Empty or too short responses
        - Harmful content patterns
        - Excessive length

        Args:
            response: Response to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for empty or too short responses
        if not response or len(response.strip()) < 3:
            return False, "Response is empty or too short"

        # Check for excessive length
        max_length = self.llm_config.max_tokens * 4  # Rough character estimate
        if len(response) > max_length:
            return False, f"Response exceeds maximum length of {max_length} characters"

        # Check for harmful content patterns (simplified example)
        harmful_patterns = [
            r"\b(hack|exploit|malware|virus)\b",
            r"\b(steal|fraud|scam)\b",
        ]

        for pattern in harmful_patterns:
            if re.search(pattern, response.lower()):
                return False, f"Response contains potentially harmful content: {pattern}"

        return True, None

    def get_conversation_summary(self) -> dict[str, Any]:
        """Get a summary of the current conversation.

        Returns:
            Dictionary containing conversation summary
        """
        if not self.state:
            return {"error": "No active conversation"}

        return {
            "conversation_id": self.state.conversation_id,
            "message_count": self.state.message_count,
            "history_length": len(self.state.history),
            "context": self.state.context,
        }

    def reset_conversation(self) -> None:
        """Reset the conversation state with a new conversation ID."""
        # Generate a new correlation ID for the new conversation
        new_correlation_id = str(uuid.uuid4())
        set_correlation_id(new_correlation_id)
        self.initialize_state()
        self.logger.info("Conversation reset")
