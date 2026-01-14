"""Tests for main module functions."""

import os
from unittest.mock import patch

import pytest

from src.config import LLMProvider


def test_create_agent_config_openai() -> None:
    """Test create_agent_config with OpenAI provider."""
    from main import create_agent_config
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        config = create_agent_config(provider="openai")
    
    assert config.provider == LLMProvider.OPENAI
    assert config.model == "gpt-4"
    assert config.temperature == 0.7
    assert config.max_tokens == 1000


def test_create_agent_config_azure() -> None:
    """Test create_agent_config with Azure OpenAI provider."""
    from main import create_agent_config
    
    with patch.dict(os.environ, {
        "AZURE_OPENAI_API_KEY": "azure-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_DEPLOYMENT": "test-deployment"
    }):
        config = create_agent_config(provider="azure_openai")
    
    assert config.provider == LLMProvider.AZURE_OPENAI
    assert config.azure_endpoint == "https://test.openai.azure.com"
    assert config.azure_deployment == "test-deployment"
    assert config.fallback_provider == LLMProvider.OPENAI
    assert config.fallback_model == "gpt-3.5-turbo"


def test_create_agent_config_default_provider() -> None:
    """Test create_agent_config uses OpenAI as default."""
    from main import create_agent_config
    
    config = create_agent_config()
    
    assert config.provider == LLMProvider.OPENAI


def test_demonstrate_basic_conversation(capsys: pytest.CaptureFixture[str]) -> None:
    """Test demonstrate_basic_conversation runs without errors."""
    from main import demonstrate_basic_conversation
    
    # Should not raise any exception
    demonstrate_basic_conversation()
    
    captured = capsys.readouterr()
    # Check for expected output
    assert "Agent Framework Integration" in captured.out
    assert "Basic Conversation Demo" in captured.out
    assert "User:" in captured.out
    assert "Agent:" in captured.out


def test_demonstrate_tool_integration(capsys: pytest.CaptureFixture[str]) -> None:
    """Test demonstrate_tool_integration runs without errors."""
    from main import demonstrate_tool_integration
    
    demonstrate_tool_integration()
    
    captured = capsys.readouterr()
    # Check for expected output
    assert "Tool Integration Demo" in captured.out
    assert "Calculator Tool" in captured.out
    assert "Weather Tool" in captured.out


def test_demonstrate_state_management(capsys: pytest.CaptureFixture[str]) -> None:
    """Test demonstrate_state_management runs without errors."""
    from main import demonstrate_state_management
    
    demonstrate_state_management()
    
    captured = capsys.readouterr()
    # Check for expected output
    assert "State Management Demo" in captured.out
    assert "Current State:" in captured.out
    assert "Resetting conversation" in captured.out


def test_main_function(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function runs all demonstrations."""
    from main import main
    
    main()
    
    captured = capsys.readouterr()
    # Check that all demonstrations ran
    assert "Basic Conversation Demo" in captured.out
    assert "Tool Integration Demo" in captured.out
    assert "State Management Demo" in captured.out
    assert "Demo Complete!" in captured.out


def test_main_shows_requirements_checklist(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function displays constitution requirements."""
    from main import main
    
    main()
    
    captured = capsys.readouterr()
    # Check for constitution requirements
    assert "Python ≥3.12" in captured.out
    assert "Pydantic models" in captured.out
    assert "Structured logging" in captured.out
    assert "correlation IDs" in captured.out


def test_agent_configuration_temperature() -> None:
    """Test agent configuration has correct temperature."""
    from main import create_agent_config
    
    config = create_agent_config()
    
    assert config.temperature == 0.7
    assert 0.0 <= config.temperature <= 2.0


def test_agent_configuration_max_tokens() -> None:
    """Test agent configuration has correct max_tokens."""
    from main import create_agent_config
    
    config = create_agent_config()
    
    assert config.max_tokens == 1000
    assert config.max_tokens > 0


def test_basic_conversation_messages() -> None:
    """Test basic conversation processes expected messages."""
    from main import demonstrate_basic_conversation
    from unittest.mock import MagicMock, patch
    
    # Mock the agent to verify messages
    with patch("main.ConversationalAgent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.process_message.return_value = "Test response"
        mock_agent.get_conversation_summary.return_value = {
            "conversation_id": "test-123",
            "message_count": 8,
            "history_length": 8
        }
        
        demonstrate_basic_conversation()
        
        # Verify agent was created
        assert mock_agent_class.called
        
        # Verify messages were processed
        assert mock_agent.process_message.called
        assert mock_agent.get_conversation_summary.called


def test_tool_integration_uses_calculator() -> None:
    """Test tool integration demonstration uses calculator."""
    from main import demonstrate_tool_integration
    from unittest.mock import MagicMock, patch
    
    with patch("main.CalculatorTool") as mock_calc:
        mock_tool = MagicMock()
        mock_calc.return_value = mock_tool
        mock_tool.execute.return_value = {
            "operation": "multiply",
            "operands": [15, 7],
            "result": 105
        }
        
        demonstrate_tool_integration()
        
        # Verify calculator was instantiated and used
        assert mock_calc.called
        assert mock_tool.execute.called


def test_tool_integration_uses_weather() -> None:
    """Test tool integration demonstration uses weather tool."""
    from main import demonstrate_tool_integration
    from unittest.mock import MagicMock, patch
    
    with patch("main.WeatherTool") as mock_weather:
        mock_tool = MagicMock()
        mock_weather.return_value = mock_tool
        mock_tool.execute.return_value = {
            "location": "Seattle",
            "temperature": 72,
            "conditions": "Partly cloudy",
            "note": "Mock data"
        }
        
        demonstrate_tool_integration()
        
        # Verify weather tool was instantiated and used
        assert mock_weather.called
        assert mock_tool.execute.called


def test_state_management_resets_conversation() -> None:
    """Test state management demonstration resets conversation."""
    from main import demonstrate_state_management
    from unittest.mock import MagicMock, patch
    
    with patch("main.ConversationalAgent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.process_message.return_value = "Test response"
        mock_agent.get_conversation_summary.return_value = {
            "conversation_id": "test-123",
            "message_count": 0
        }
        
        demonstrate_state_management()
        
        # Verify reset was called
        assert mock_agent.reset_conversation.called


def test_main_handles_errors_gracefully() -> None:
    """Test main function handles errors gracefully."""
    from main import main
    from unittest.mock import patch
    
    with patch("main.demonstrate_basic_conversation") as mock_demo:
        mock_demo.side_effect = Exception("Test error")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Test error"):
            main()
