# Quickstart Guide: AG-UI Integration

**Feature**: AG-UI Integration for Web-Based Agent Interface  
**Version**: 0.1.0  
**Last Updated**: 2026-01-13

This guide will help you get the AG-UI web interface up and running in under 30 minutes.

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.12 or higher** installed
- **uv** package manager installed ([installation guide](https://github.com/astral-sh/uv))
- **OpenAI API key** or **Azure OpenAI credentials**
- **Terminal/Command prompt** access
- **Web browser** (for testing with browser clients)

---

## Installation

### 1. Clone and Navigate to Project

```bash
git clone <repository-url>
cd agentic-devops-starter/app
```

### 2. Install Dependencies

Using `uv` (recommended):

```bash
uv sync
```

Or using pip:

```bash
pip install -e .
```

For development dependencies (testing, linting):

```bash
uv sync --extra dev
```

---

## Configuration

### 1. Create Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with your settings:

```bash
# LLM Provider (openai or azure_openai)
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-4

# Azure OpenAI Configuration (if using Azure)
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_API_KEY=your-azure-key
# AZURE_OPENAI_DEPLOYMENT=your-deployment-name
# AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Server Configuration
AGUI_HOST=0.0.0.0
AGUI_PORT=8000
LOG_LEVEL=INFO

# Optional: Advanced Settings
MAX_THREADS=100
MAX_MESSAGES_PER_THREAD=50
TOOL_TIMEOUT_SECONDS=30
```

### Required Variables

At minimum, you must set:
- `OPENAI_API_KEY` (for OpenAI) OR
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` (for Azure)

---

## Running the Server

### Start the AG-UI Server

```bash
python agui_server.py
```

Expected output:

```
2026-01-13 22:00:00 - agentic_devops - INFO - [<correlation-id>] - Starting AG-UI server
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

The server is now running and ready to accept requests!

### Verify Server Health

In a new terminal:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "thread_count": 0,
  "uptime_seconds": 5.2
}
```

---

## Quick Test: Basic Client

### Option 1: Using the Python Client

In a new terminal (keep server running):

```bash
python agui_client.py
```

This starts an interactive chat session:

```
Connected to AG-UI server at http://localhost:8000
Thread ID: 550e8400-e29b-41d4-a716-446655440000

You: Hello! What can you do?
Agent: Hello! I'm here to help you. I'm a conversational AI assistant built with...
```

Type your messages and press Enter. Type `quit` or `exit` to end the session.

### Option 2: Using curl

Send a message:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "thread_id": null,
    "stream": true
  }'
```

You'll see streaming events:

```
data: {"event":"token","thread_id":"...","timestamp":"...","token":"Hello"}

data: {"event":"token","thread_id":"...","timestamp":"...","token":"!"}

data: {"event":"message_complete","thread_id":"...","timestamp":"..."}
```

---

## Using Server-Side Tools

### Test the `get_time_zone` Tool

Start the basic client and ask about time zones:

```
You: What's the time zone in New York?
Agent: [Processing with get_time_zone tool...]
Agent: The time zone for New York is America/New_York, which is Eastern Time.
```

In the server logs, you'll see:

```
2026-01-13 22:05:00 - agentic_devops - INFO - [correlation-id] - Tool execution started
2026-01-13 22:05:00 - agentic_devops - INFO - [correlation-id] - Tool: get_time_zone, Args: {'city': 'New York'}
2026-01-13 22:05:00 - agentic_devops - INFO - [correlation-id] - Tool execution completed in 45.2ms
```

---

## Using Client-Side Tools (Hybrid Client)

### Start the Hybrid Client

```bash
python agui_client_hybrid.py
```

This client can execute both server tools and client tools.

### Test Client Tool: `get_weather`

```
You: What's the weather like in Seattle?
Agent: [Processing with get_weather tool on client...]
Agent: In Seattle, it's currently 68°F and Sunny with 55% humidity.
```

Notice in the client output:

```
[CLIENT] Executing tool: get_weather with args: {'city': 'Seattle'}
[CLIENT] Tool result: {'city': 'Seattle', 'temperature': 68, 'conditions': 'Sunny', 'humidity': 55}
```

### Test Both Tool Types

```
You: What's the weather in Tokyo and what's its time zone?
Agent: [Uses get_weather on client and get_time_zone on server...]
```

---

## Exploring the API

### View OpenAPI Documentation

Open your browser and navigate to:

```
http://localhost:8000/docs
```

You'll see interactive API documentation with all endpoints:
- Try out the `/chat` endpoint
- View request/response schemas
- Test other endpoints like `/threads`, `/health`

### Get OpenAPI Specification

```bash
curl http://localhost:8000/openapi.json > openapi.json
```

---

## Common Use Cases

### 1. Continue a Conversation

Save the thread ID from the first message, then use it in subsequent requests:

```python
# First message (creates thread)
response1 = requests.post("http://localhost:8000/chat", json={
    "message": "Hello!",
    "thread_id": None
})
thread_id = extract_thread_id(response1)

# Continue conversation
response2 = requests.post("http://localhost:8000/chat", json={
    "message": "Tell me more",
    "thread_id": thread_id
})
```

### 2. List All Conversations

```bash
curl http://localhost:8000/threads
```

Response:

```json
{
  "threads": [
    {
      "thread_id": "550e8400-e29b-41d4-a716-446655440000",
      "message_count": 10,
      "created_at": "2026-01-13T20:00:00Z",
      "updated_at": "2026-01-13T21:30:00Z"
    }
  ]
}
```

### 3. Retrieve Conversation History

```bash
curl http://localhost:8000/threads/550e8400-e29b-41d4-a716-446655440000
```

### 4. Monitor Server Logs

Server logs show all operations with correlation IDs:

```
2026-01-13 22:00:00 - agentic_devops - INFO - [abc-123] - Request received
2026-01-13 22:00:01 - agentic_devops - INFO - [abc-123] - LLM call started
2026-01-13 22:00:02 - agentic_devops - INFO - [abc-123] - Tool execution: get_time_zone
2026-01-13 22:00:03 - agentic_devops - INFO - [abc-123] - Response complete
```

Use correlation IDs to trace requests end-to-end.

---

## Development Workflow

### 1. Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/agui/test_server.py

# Run with coverage
pytest --cov=src/agui --cov-report=html
```

### 2. Run Linting

```bash
# Run Ruff linter
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

### 3. Run Type Checking

```bash
# Run mypy
mypy src/ tests/
```

### 4. Hot Reload During Development

Use `uvicorn` directly with reload:

```bash
uvicorn agui_server:app --reload --host 0.0.0.0 --port 8000
```

The server will automatically restart when you modify code.

---

## Creating Custom Tools

### Server-Side Tool

Create a new function in `src/agui/tools/server_tools.py`:

```python
from agent_framework import tool

@tool(description="Convert currency amounts")
def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert an amount from one currency to another.
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., 'USD')
        to_currency: Target currency code (e.g., 'EUR')
        
    Returns:
        Converted amount
    """
    # Implementation here
    # Use exchange rate API
    pass
```

Register it in `agui_server.py`:

```python
from src.agui.tools.server_tools import get_time_zone, convert_currency

app = create_app(
    config=config,
    server_tools=[get_time_zone, convert_currency]
)
```

### Client-Side Tool

Create a new function in `src/agui/tools/client_tools.py`:

```python
def get_local_time() -> str:
    """Get the current local time on the client.
    
    Returns:
        Current time as string
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

Register it in your client:

```python
from src.agui.tools.client_tools import get_weather, get_local_time

client = HybridToolsClient(
    server_url="http://localhost:8000",
    client_tools=[get_weather, get_local_time]
)
```

---

## Troubleshooting

### Issue: Server won't start - "Address already in use"

**Solution**: Another process is using port 8000. Change the port:

```bash
export AGUI_PORT=8001
python agui_server.py
```

Or kill the process using port 8000:

```bash
lsof -ti:8000 | xargs kill -9
```

### Issue: "Invalid API key" error

**Solution**: Check your `.env` file:

1. Verify `OPENAI_API_KEY` is set correctly
2. Ensure no extra spaces or quotes around the key
3. Check if the key is valid on OpenAI platform

### Issue: Client can't connect to server

**Solution**: Verify server is running and accessible:

```bash
curl http://localhost:8000/health
```

If this fails:
1. Check server logs for errors
2. Verify firewall settings
3. Ensure correct host/port in client configuration

### Issue: Streaming responses not appearing

**Solution**: 
1. Check that `stream: true` in request
2. Verify client is properly parsing SSE format
3. Check for buffering issues in HTTP client

### Issue: Tool execution timeout

**Solution**: Increase timeout in configuration:

```bash
export TOOL_TIMEOUT_SECONDS=60
```

Or modify `AGUIServerConfig` in code.

### Issue: Memory usage growing over time

**Solution**: Check thread cleanup settings:

```bash
export MAX_THREADS=50
export MAX_MESSAGES_PER_THREAD=30
```

Threads are automatically pruned when limits are reached.

---

## Next Steps

Now that you have AG-UI running:

1. **Explore the API**: Use the interactive docs at `/docs`
2. **Create Custom Tools**: Add your own server/client tools
3. **Build a Web Frontend**: Use the API to build a React/Vue web interface
4. **Add Authentication**: Implement user authentication (see future enhancements)
5. **Deploy to Production**: Containerize with Docker, deploy to cloud

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Application                      │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Basic Client    │         │  Hybrid Client   │         │
│  │  (No tools)      │         │  (Client tools)  │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                            │                    │
│           │  HTTP/SSE                  │  HTTP/SSE          │
└───────────┼────────────────────────────┼────────────────────┘
            │                            │
            │                            │  Tool execution
            │                            │  request/response
            │                            │
┌───────────┴────────────────────────────┴────────────────────┐
│                      FastAPI Server                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │              /chat Endpoint (SSE)                   │    │
│  │  - Receives messages                                │    │
│  │  - Streams responses                                │    │
│  │  - Orchestrates tool execution                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  ConversationalA │         │  Thread Storage  │         │
│  │  gent            │◄────────┤  (In-memory)     │         │
│  │  (LLM calls)     │         │                  │         │
│  └────────┬─────────┘         └──────────────────┘         │
│           │                                                  │
│           │  Calls                                           │
│           │                                                  │
│  ┌────────▼─────────┐                                       │
│  │  Server Tools    │                                       │
│  │  - get_time_zone │                                       │
│  └──────────────────┘                                       │
└──────────────────────────────────────────────────────────────┘
```

---

## Additional Resources

- **Full Documentation**: See `app/README.md`
- **API Reference**: `specs/002-ag-ui-integration/contracts/openapi.yaml`
- **Data Model**: `specs/002-ag-ui-integration/data-model.md`
- **Implementation Plan**: `specs/002-ag-ui-integration/plan.md`
- **Research Notes**: `specs/002-ag-ui-integration/research.md`

---

## Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review server logs for error messages
3. Ensure all prerequisites are installed
4. Verify environment variables are set correctly
5. Check that API keys are valid

For bugs or feature requests, please open an issue in the repository.

---

**Quickstart Guide Complete**  
**Last Updated**: 2026-01-13  
**Next**: Start experimenting with custom tools and building your own client!
