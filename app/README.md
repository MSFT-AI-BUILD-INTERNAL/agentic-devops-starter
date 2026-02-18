# Agent Framework Integration with Dev-UI

This application demonstrates the integration of the Microsoft Agent Framework with **Dev-UI** - a browser-based development and debugging interface for AI agents.

## Overview

This implementation showcases:

- **Python-First Backend**: All code uses Python ≥3.12
- **Agent-Centric Architecture**: Core orchestration using agent primitives
- **Dev-UI Integration**: Built-in web interface with OpenAI-compatible API
- **Type Safety**: Full type hints with type checking
- **Tool Integration**: Example tools for weather and time zones
- **Azure Integration**: Native Azure AI and Azure OpenAI support
- **Simplified Deployment**: Single backend process (no separate frontend)

## Project Structure

```
app/
├── src/
│   ├── __init__.py
│   ├── logging_utils.py          # Structured logging
│   ├── config/
│   │   └── llm_config.py         # LLM provider configuration
│   └── agents/
│       ├── base_agent.py         # Base agent class
│       ├── conversational_agent.py  # Agent implementation
│       └── tools.py              # Tool examples
├── tests/                        # Test directory
├── devui_server.py               # Dev-UI server (main entry point)
├── main.py                       # CLI demo
├── .env.example                  # Environment configuration example
├── pyproject.toml               # Project dependencies
├── Dockerfile                    # Container definition
└── DEVUI_USAGE.md               # Detailed Dev-UI guide
```

## Quick Start

### 1. Install Dependencies

```bash
cd app
uv sync
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Azure AI configuration
```

Required variables:
```env
AZURE_AI_PROJECT_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-08-07
```

### 3. Start Dev-UI Server

```bash
uv run devui_server.py
```

Server will start at `http://localhost:8080` with:
- **Web UI**: `http://localhost:8080/`
- **OpenAI API**: `http://localhost:8080/v1/`
- **Health Check**: `http://localhost:8080/health`
- **API Docs**: `http://localhost:8080/docs` (developer mode)

## Features

### 1. Dev-UI Interface

Dev-UI provides a complete web-based interface with:

- **Interactive Chat**: Browser-based conversation interface
- **Real-time Streaming**: See responses as they're generated
- **Conversation History**: Browse and continue previous conversations
- **Tool Visualization**: See when tools are executed and their results
- **OpenAI-Compatible API**: Standard API endpoints for integration

### 2. Tool Integration

Two example tools are included:

- **get_weather**: Get current weather for a location (mock data)
- **get_time_zone**: Get time zone information for a location

Example queries:
```
"What's the weather in Seattle?"
"What time zone is Tokyo in?"
"Tell me about the weather and time zone in London"
```

### 3. Azure Integration

Native support for Azure services:

- **Azure AI Foundry**: Primary AI orchestration
- **Azure OpenAI**: Model deployment and inference  
- **Managed Identity**: Passwordless authentication
- **Azure Monitor**: Logging and telemetry

## Architecture

```
┌─────────────────────────────────────────┐
│      Browser / API Client               │
│      http://localhost:8080              │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│       Dev-UI Server (FastAPI)           │
│  ┌───────────────────────────────────┐  │
│  │  Web UI (/)                       │  │
│  │  OpenAI API (/v1)                 │  │
│  │  Health (/health)                 │  │
│  └───────────────────────────────────┘  │
│                ↓                        │
│  ┌───────────────────────────────────┐  │
│  │  Agent Framework                  │  │
│  │  - DevUIAssistant                 │  │
│  │  - Tools: weather, timezone       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│     Azure AI / Azure OpenAI             │
│     - Authentication: Managed Identity  │
│     - Model: gpt-4o-mini                │
└─────────────────────────────────────────┘
```

## Production Deployment

### Azure App Service

The application is deployed as a single container to Azure App Service:

1. **Build**: GitHub Actions builds the Docker image
2. **Push**: Image is pushed to Azure Container Registry
3. **Deploy**: App Service pulls and runs the image

```
┌──────────────────────────────────────┐
│   Azure App Service (HTTPS)          │
│  ┌────────────────────────────────┐  │
│  │  Dev-UI Server (port 8080)     │  │
│  │  - Web UI                      │  │
│  │  - OpenAI API                  │  │
│  │  - Agent Framework             │  │
│  └────────────────────────────────┘  │
│  System-Assigned Managed Identity    │
└──────────────────────────────────────┘
```

### Authentication

- **Local Development**: Uses `DefaultAzureCredential` (Azure CLI, VS Code, etc.)
- **Production**: Uses System-Assigned Managed Identity on App Service

Required Azure RBAC roles:
- Azure AI Developer (on AI Foundry project)
- Cognitive Services User (on Azure OpenAI resource)

## Configuration

### Environment Variables

See `.env.example` for all available options:

```bash
# Required
AZURE_AI_PROJECT_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini

# Optional
AZURE_OPENAI_API_VERSION=2025-08-07  # Default
PORT=8080                             # Default
```

### Dev-UI Server Options

The `serve()` function accepts various options:

```python
serve(
    entities=[agent],           # List of agents to serve
    host="0.0.0.0",            # Host to bind to
    port=8080,                  # Port to listen on
    auto_open=False,            # Open browser automatically
    mode="developer",           # "developer" or "user"
    ui_enabled=True,            # Enable web UI
    auth_enabled=False,         # Require authentication
    cors_origins=None,          # CORS configuration
)
```

## Development

### Running Locally

```bash
cd app
uv run devui_server.py
```

### Testing with Docker

```bash
# Build
docker build -f app/Dockerfile -t devui-test .

# Run
docker run -p 8080:8080 \
  -e AZURE_AI_PROJECT_ENDPOINT=<endpoint> \
  -e AZURE_AI_MODEL_DEPLOYMENT_NAME=<model> \
  devui-test

# Access at http://localhost:8080
```

### Code Quality

```bash
cd app

# Lint
ruff check src/

# Type check
mypy src/

# Test
pytest tests/
```

## Migration from AG-UI

This application previously used AG-UI with a custom React frontend. Dev-UI simplifies the architecture:

| Aspect | AG-UI (Old) | Dev-UI (New) |
|--------|-------------|--------------|
| **Frontend** | Custom React | Built-in UI |
| **Deployment** | Sidecar (nginx + backend) | Single process |
| **Port** | 5100 (backend), 8080 (nginx) | 8080 (unified) |
| **API Protocol** | Custom AG-UI | OpenAI-compatible |
| **Configuration** | Multiple files | Single `serve()` |
| **Maintenance** | High | Low |

## Documentation

- **Dev-UI Guide**: See [DEVUI_USAGE.md](./DEVUI_USAGE.md) for detailed usage
- **Agent Framework**: [Microsoft Learn](https://learn.microsoft.com/en-us/agent-framework/)
- **Dev-UI Package**: [PyPI](https://pypi.org/project/agent-framework-devui/)

## Troubleshooting

### Server won't start
- Check port 8080 is not in use
- Verify Azure credentials are configured
- Check environment variables are set

### Authentication errors
- Ensure Azure credentials are available (`az login`)
- Verify Managed Identity has required roles
- Check endpoint URL is correct

### Tools not working
- Check tool docstrings are descriptive
- Verify function signatures are correct
- Look for tool execution in logs

## License

See LICENSE file in the repository root.

## Support

For issues or questions, please refer to the repository's issue tracker.
