# Dev-UI Usage Guide

## Overview

This application uses **Dev-UI** from the Microsoft Agent Framework, which provides a complete development and debugging interface for AI agents.

Dev-UI includes:
- **Web UI**: Browser-based interface for interacting with agents
- **OpenAI-compatible API**: Standard API endpoints at `/v1`
- **Health Endpoint**: `/health` for monitoring
- **Built-in Agent Management**: Automatic agent registration and discovery

## Quick Start

### 1. Set Up Environment

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` and add your Azure configuration:

```env
# Azure OpenAI Configuration
AZURE_AI_PROJECT_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-08-07

# Optional: Custom port (default: 8080)
PORT=8080
```

### 2. Start the Dev-UI Server

```bash
cd app
uv run devui_server.py
```

Expected output:
```
2026-02-18 08:00:00 - INFO - Creating Agent: endpoint=https://...
2026-02-18 08:00:00 - INFO - Starting Dev-UI server on port 8080
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

### 3. Access the Web UI

Open your browser to:
- **Web UI**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs (developer mode only)
- **Health Check**: http://localhost:8080/health

## Features

### Interactive Web Interface

The Dev-UI provides a modern web interface with:
- **Chat Interface**: Converse with the AI assistant
- **Tool Execution**: See when tools are called and their results
- **Conversation History**: Browse and continue previous conversations
- **Real-time Streaming**: See responses as they're generated

### Available Tools

The assistant has access to two tools:

1. **get_weather**: Get current weather for a location
   ```python
   # Example: "What's the weather in Seattle?"
   # Returns: "Rainy, 55°F"
   ```

2. **get_time_zone**: Get time zone information for a location
   ```python
   # Example: "What time zone is Tokyo in?"
   # Returns: "Japan Standard Time (UTC+9)"
   ```

### OpenAI-Compatible API

Dev-UI exposes an OpenAI-compatible API at `/v1`:

```bash
# Create a chat completion
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "DevUIAssistant",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

Endpoints:
- `POST /v1/chat/completions` - Chat completions (streaming and non-streaming)
- `GET /v1/models` - List available models
- `GET /health` - Health check

## Production Deployment

Dev-UI supports two modes:

### Developer Mode (default)
- Full API access
- Detailed error messages
- API documentation available
- Permissive CORS for localhost

### User Mode
```python
serve(
    entities=[agent],
    host="0.0.0.0",
    port=8080,
    mode="user",  # Restricts some APIs, generic errors
    ui_enabled=True
)
```

For production deployments:
- Use `mode="user"` for restricted access
- Consider `auth_enabled=True` with a secure token
- Configure CORS appropriately for your domain
- Set `host="0.0.0.0"` for network access

## Architecture

```
┌─────────────────────────────────────────┐
│         Browser / API Client            │
└─────────────────────────────────────────┘
                  ↓
         http://localhost:8080
                  ↓
┌─────────────────────────────────────────┐
│           Dev-UI Server                 │
│  ┌───────────────────────────────────┐  │
│  │   Web UI (/)                      │  │
│  │   OpenAI API (/v1)                │  │
│  │   Health Check (/health)          │  │
│  └───────────────────────────────────┘  │
│                 ↓                       │
│  ┌───────────────────────────────────┐  │
│  │   Agent Framework                 │  │
│  │   - DevUIAssistant                │  │
│  │   - Tools: weather, timezone      │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      Azure OpenAI / Azure AI            │
│      - Model: gpt-4o-mini               │
│      - Authentication: Managed Identity │
└─────────────────────────────────────────┘
```

## Troubleshooting

### Server won't start
- Check that port 8080 is not already in use
- Verify Azure credentials are configured (DefaultAzureCredential)
- Check logs for specific error messages

### Can't connect from browser
- Ensure server is running and listening on the correct port
- Check firewall settings
- Verify CORS configuration if accessing from different origin

### Tools not executing
- Check server logs to see tool execution
- Verify tool definitions have proper docstrings and type hints
- Test tools directly: `uv run python -c "from devui_server import get_weather; print(get_weather('seattle'))"`

### Authentication errors
- Verify `AZURE_AI_PROJECT_ENDPOINT` is correct
- Check that Managed Identity or credentials have appropriate roles:
  - "Azure AI Developer" on AI Foundry project
  - "Cognitive Services User" on Azure OpenAI resource

## Differences from AG-UI

Dev-UI replaces the previous AG-UI implementation with these improvements:

| Feature | AG-UI (Old) | Dev-UI (New) |
|---------|-------------|--------------|
| **Frontend** | Custom React app | Built-in web UI |
| **Deployment** | Sidecar (nginx + backend) | Single backend process |
| **API** | Custom protocol | OpenAI-compatible |
| **Configuration** | Multiple files | Single `serve()` call |
| **Port** | 5100 (backend), 8080 (nginx) | 8080 (all-in-one) |
| **Complexity** | High (2 services) | Low (1 service) |

## Additional Resources

- [Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/)
- [Dev-UI PyPI Package](https://pypi.org/project/agent-framework-devui/)
- [Azure AI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/)
