"""LLM configuration for agent framework integration."""

import os
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class LLMConfig(BaseModel):
    """Configuration for LLM provider.

    This configuration supports multiple LLM providers with fallback mechanisms
    as required by the constitution.
    """

    provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="LLM provider to use"
    )
    api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="API key for the LLM provider"
    )
    model: str = Field(
        default="gpt-4",
        description="Model name to use"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for response generation"
    )
    max_tokens: int = Field(
        default=1000,
        gt=0,
        description="Maximum tokens in response"
    )

    # Azure OpenAI specific fields
    azure_endpoint: str | None = Field(
        default=None,
        description="Azure OpenAI endpoint URL"
    )
    azure_deployment: str | None = Field(
        default=None,
        description="Azure OpenAI deployment name"
    )
    api_version: str | None = Field(
        default="2024-02-15-preview",
        description="API version for Azure OpenAI"
    )

    # Fallback configuration
    fallback_provider: LLMProvider | None = Field(
        default=None,
        description="Fallback provider if primary fails"
    )
    fallback_model: str | None = Field(
        default=None,
        description="Fallback model name"
    )

    # Token usage tracking
    enable_token_tracking: bool = Field(
        default=True,
        description="Enable token usage tracking for cost monitoring"
    )

    model_config = ConfigDict(use_enum_values=True)
