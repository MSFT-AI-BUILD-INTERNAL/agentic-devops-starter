"""LLM configuration for agent framework."""

import os
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LLMProvider(StrEnum):
    """Supported LLM providers."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""
    provider: LLMProvider = Field(default=LLMProvider.OPENAI)
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model: str = Field(default="gpt-4")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, gt=0)

    # Azure OpenAI specific
    azure_endpoint: str | None = Field(default=None)
    azure_deployment: str | None = Field(default=None)
    api_version: str | None = Field(default="2024-02-15-preview")

    # Fallback
    fallback_provider: LLMProvider | None = Field(default=None)
    fallback_model: str | None = Field(default=None)

    model_config = ConfigDict(use_enum_values=True)
