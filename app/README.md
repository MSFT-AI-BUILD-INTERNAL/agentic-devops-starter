# Agent Framework Integration with AG-UI

This is a comprehensive example demonstrating the integration of the `microsoft-agent-framework` for building conversational AI agents with **AG-UI (Agent User Interface)** for web-based interaction, following all requirements from `constitution.md`.

## Overview

This implementation showcases:

- **Python-First Backend**: All code uses Python ≥3.12
- **Agent-Centric Architecture**: Core orchestration using agent primitives
- **AG-UI Integration**: Web-based interface using FastAPI with streaming support
- **Type Safety**: Full type hints with Pydantic validation
- **Response Quality**: Guardrails and validation for LLM responses
- **Observability**: Structured logging with correlation IDs
- **Tool Integration**: Example tools with hybrid client/server execution
- **Streaming Responses**: Real-time agent responses via Server-Sent Events (SSE)

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
├── main.py                       # CLI demo (original example)
├── agui_server.py                # AG-UI FastAPI server
├── agui_client.py                # Basic AG-UI client
├── agui_client_hybrid.py         # Advanced client with hybrid tools
├── .env.example                  # Environment configuration example
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
- Time zone tool for location information
- Extensible tool framework
- **Hybrid tool execution**: Both client-side and server-side tools

### 6. AG-UI Web Interface

Web-based agent interface with:

- FastAPI server with AG-UI protocol support
- Server-Sent Events (SSE) for real-time streaming
- Thread management for conversation continuity
- Client-side and server-side tool execution
- Full OpenAPI documentation at `/docs`
- Health check endpoint

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
uv run main.py
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

## Using AG-UI Web Interface

AG-UI provides a web-based interface for your agent with streaming responses and tool execution.

### Quick Start

1. **Configure environment variables** (copy `.env.example` to `.env`):

```bash
cd app
cp .env.example .env
# Edit .env with your API keys
```

2. **Start the AG-UI server**:

```bash
cd app
uv run agui_server.py
```

The server will start at `http://127.0.0.1:5100` with:
- OpenAPI documentation at `http://127.0.0.1:5100/docs`
- AG-UI endpoint at `http://127.0.0.1:5100/`

3. **Use the basic client** (in another terminal):

```bash
cd app
uv run agui_client.py
```

4. **Or use the hybrid tools client**:

```bash
cd app
uv run agui_client_hybrid.py
```

### AG-UI Features

#### Server-Side Tools

The server includes the `get_time_zone` tool that executes on the server:

```python
# Try asking:
# "What time zone is Seattle in?"
# "What's the time zone for Tokyo?"
```

#### Client-Side Tools

The hybrid client includes the `get_weather` tool that executes on the client:

```python
# Try asking:
# "What's the weather like in Seattle?"
# "How's the weather in Tokyo?"
```

#### Hybrid Tool Execution

Both tools work together seamlessly:

```python
# Try asking:
# "What's the weather and time zone in London?"
# "Tell me about the weather in Paris and what time zone it's in"
```

The agent will automatically:
1. Decide which tools to use based on the query
2. Execute server-side tools (get_time_zone) on the server
3. Execute client-side tools (get_weather) on the client
4. Combine results into a coherent response

### Conversation Continuity

The AG-UI protocol maintains conversation history through thread management:

- Each conversation gets a unique thread ID
- Messages are tracked across requests
- Context is preserved for natural multi-turn conversations

### API Documentation

Visit `http://127.0.0.1:5100/docs` when the server is running to see:
- Complete API documentation
- Interactive API testing
- Request/response schemas
- Try out endpoints directly

## Configuration

### Environment Variables

Configure LLM providers using environment variables (see `.env.example`):

```bash
# Azure OpenAI (Preferred)
export AZURE_AI_PROJECT_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4o-mini"
export AZURE_OPENAI_API_KEY="your-key"  # Optional if using DefaultAzureCredential

# OpenAI (Fallback)
export OPENAI_API_KEY="your-key"

# AG-UI Client Configuration
export AGUI_SERVER_URL="http://127.0.0.1:5100/"
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
