"""Tests for LLM configuration."""

import pytest
from pydantic import ValidationError

from src.config import LLMConfig, LLMProvider


def test_llm_config_default_values() -> None:
    """Test LLM config with default values."""
    config = LLMConfig(api_key="test-key")

    assert config.provider == LLMProvider.OPENAI
    assert config.model == "gpt-4"
    assert config.temperature == 0.7
    assert config.max_tokens == 1000
    assert config.enable_token_tracking is True


def test_llm_config_openai() -> None:
    """Test OpenAI configuration."""
    config = LLMConfig(
        provider=LLMProvider.OPENAI,
        api_key="test-key",
        model="gpt-3.5-turbo",
        temperature=0.5,
        max_tokens=500,
    )

    assert config.provider == LLMProvider.OPENAI
    assert config.api_key == "test-key"
    assert config.model == "gpt-3.5-turbo"
    assert config.temperature == 0.5
    assert config.max_tokens == 500


def test_llm_config_azure() -> None:
    """Test Azure OpenAI configuration."""
    config = LLMConfig(
        provider=LLMProvider.AZURE_OPENAI,
        api_key="azure-key",
        azure_endpoint="https://test.openai.azure.com",
        azure_deployment="test-deployment",
        model="gpt-4",
    )

    assert config.provider == LLMProvider.AZURE_OPENAI
    assert config.azure_endpoint == "https://test.openai.azure.com"
    assert config.azure_deployment == "test-deployment"


def test_llm_config_with_fallback() -> None:
    """Test configuration with fallback provider."""
    config = LLMConfig(
        provider=LLMProvider.AZURE_OPENAI,
        api_key="test-key",
        fallback_provider=LLMProvider.OPENAI,
        fallback_model="gpt-3.5-turbo",
    )

    assert config.fallback_provider == LLMProvider.OPENAI
    assert config.fallback_model == "gpt-3.5-turbo"


def test_llm_config_temperature_validation() -> None:
    """Test temperature validation bounds."""
    # Valid temperatures
    LLMConfig(api_key="test", temperature=0.0)
    LLMConfig(api_key="test", temperature=1.0)
    LLMConfig(api_key="test", temperature=2.0)

    # Invalid temperatures should raise validation error
    with pytest.raises(ValidationError):
        LLMConfig(api_key="test", temperature=-0.1)

    with pytest.raises(ValidationError):
        LLMConfig(api_key="test", temperature=2.1)


def test_llm_config_max_tokens_validation() -> None:
    """Test max_tokens validation."""
    # Valid max_tokens
    LLMConfig(api_key="test", max_tokens=1)
    LLMConfig(api_key="test", max_tokens=1000)

    # Invalid max_tokens (must be positive)
    with pytest.raises(ValidationError):
        LLMConfig(api_key="test", max_tokens=0)

    with pytest.raises(ValidationError):
        LLMConfig(api_key="test", max_tokens=-1)
