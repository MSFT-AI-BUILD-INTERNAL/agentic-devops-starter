# Agent Framework Integration Example

This is a comprehensive example demonstrating the integration of the `microsoft-agent-framework` for building conversational AI agents, following all requirements from `constitution.md`.

## Overview

This implementation showcases:

- **Python-First Backend**: All code uses Python ≥3.12
- **Agent-Centric Architecture**: Core orchestration using agent primitives
- **Type Safety**: Full type hints with Pydantic validation
- **Response Quality**: Guardrails and validation for LLM responses
- **Observability**: Structured logging with correlation IDs
- **Tool Integration**: Example tools demonstrating agent capabilities

## Project Structure

```
app/
├── src/
│   ├── __init__.py
│   ├── logging_utils.py          # Structured logging with correlation IDs
│   ├── config/
│   │   ├── __init__.py
│   │   └── llm_config.py         # LLM provider configuration
│   └── agents/
│       ├── __init__.py
│       ├── base_agent.py         # Base agent class
│       ├── conversational_agent.py  # Conversational agent implementation
│       └── tools.py              # Tool/function integration examples
├── tests/                        # Test directory
├── main.py                       # Example usage and demonstrations
└── pyproject.toml               # Project dependencies and configuration
```

## Features

### 1. Agent Framework Integration

The implementation provides:

- **BaseAgent**: Abstract base class for all agents with:
  - State management using Pydantic models
  - Conversation history tracking
  - LLM interaction logging
  - Response validation hooks

- **ConversationalAgent**: Concrete implementation demonstrating:
  - Message processing pipeline
  - Conversation state management
  - Response validation and guardrails
  - Structured logging throughout

### 2. Configuration Management

LLM configuration supports:

- Multiple providers (OpenAI, Azure OpenAI)
- Fallback mechanisms for reliability
- Token usage tracking for cost monitoring
- Environment-based configuration

### 3. Observability

Comprehensive logging with:

- Structured log format
- Correlation ID tracking across all operations
- Contextual information for debugging
- LLM interaction audit trail

### 4. Type Safety

All code includes:

- Type hints on all functions and methods
- Pydantic models for data validation
- Mypy compatibility for type checking

### 5. Tool Integration

Example tools demonstrating:

- Tool definition with parameter schemas
- Calculator tool for arithmetic operations
- Weather tool (mock) for API integration
- Extensible tool framework

## Installation

### Prerequisites

- Python ≥3.12
- `uv` package manager (or pip)

### Setup

1. Install dependencies:

```bash
cd app
uv pip install -e .
```

Or with pip:

```bash
cd app
pip install -e .
```

2. Install development dependencies:

```bash
uv pip install -e ".[dev]"
```

## Usage

### Running the Example

```bash
cd app
python main.py
```

This will run three demonstrations:

1. **Basic Conversation**: Shows agent message processing
2. **Tool Integration**: Demonstrates calculator and weather tools
3. **State Management**: Shows conversation state tracking

### Using the Agent in Your Code

```python
from src.agents import ConversationalAgent
from src.config import LLMConfig, LLMProvider

# Create configuration
config = LLMConfig(
    provider=LLMProvider.OPENAI,
    api_key="your-api-key",
    model="gpt-4",
    temperature=0.7,
)

# Initialize agent
agent = ConversationalAgent(
    name="MyAgent",
    llm_config=config,
)

# Process messages
response = agent.process_message("Hello!")
print(response)

# Get conversation summary
summary = agent.get_conversation_summary()
print(f"Messages: {summary['message_count']}")
```

### Using Tools

```python
from src.agents.tools import CalculatorTool

# Create tool
calculator = CalculatorTool()

# Execute tool
result = calculator.execute(
    operation="multiply",
    a=15,
    b=7
)
print(f"Result: {result['result']}")
```

## Configuration

### Environment Variables

Configure LLM providers using environment variables:

```bash
# OpenAI
export OPENAI_API_KEY="your-key"

# Azure OpenAI
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="your-deployment"
```

### Configuration Options

All configuration is done through Pydantic models in `src/config/llm_config.py`:

- `provider`: LLM provider (OpenAI or Azure OpenAI)
- `api_key`: API key for authentication
- `model`: Model name to use
- `temperature`: Response temperature (0.0-2.0)
- `max_tokens`: Maximum tokens in response
- `fallback_provider`: Fallback provider if primary fails
- `enable_token_tracking`: Enable token usage tracking

## Development

### Code Quality

Run linting with Ruff:

```bash
cd app
ruff check src/
```

Run type checking with mypy:

```bash
cd app
mypy src/
```

### Testing

Run tests with pytest:

```bash
cd app
pytest tests/
```

## Architecture Principles

This implementation follows all principles from `constitution.md`:

### I. Python-First Backend
✓ Python ≥3.12 with modern features

### II. Agent-Centric Architecture
✓ Agent framework as core orchestration layer
✓ State management through agent primitives
✓ Tool integration for extended capabilities

### III. Type Safety
✓ Complete type hints throughout
✓ Pydantic for validation and serialization
✓ Mypy-compatible code

### IV. Response Quality
✓ Response validation before delivery
✓ Guardrails for harmful content
✓ LLM interaction logging

### V. Observability
✓ Structured logging everywhere
✓ Correlation IDs for request tracking
✓ Traceable agent actions and LLM calls

### VI. Project Structure
✓ All application code in `app/` directory
✓ Clear separation of concerns
✓ Modular and extensible design

## Extending the Example

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement `process_message` and `validate_response` methods
3. Add agent-specific logic and tools

### Adding New Tools

1. Create a new tool class inheriting from `Tool`
2. Implement `get_definition` and `execute` methods
3. Register tool with your agent

### Customizing Configuration

Extend `LLMConfig` in `src/config/llm_config.py` to add:
- New provider types
- Custom parameters
- Additional validation rules

## License

See LICENSE file in the repository root.

## Contributing

Follow the development workflow defined in `constitution.md`:

1. Use Speckit for planning and task management
2. Write tests before implementation
3. Ensure code passes all quality gates (Ruff, mypy)
4. Require PR reviews before merge

## Support

For issues or questions, please refer to the repository's issue tracker.
