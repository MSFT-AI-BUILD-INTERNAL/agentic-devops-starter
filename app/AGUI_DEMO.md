# AG-UI Demo Usage

## Quick Start

### 1. Set Up Environment

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# For Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_KEY=your-api-key

# OR for OpenAI
OPENAI_API_KEY=your-api-key
```

### 2. Start the AG-UI Server

```bash
python agui_server.py
```

Expected output:
```
2026-01-10 07:30:00 - agentic_devops - INFO - [no-correlation-id] - Creating ChatAgent for AG-UI server
2026-01-10 07:30:00 - agentic_devops - INFO - [no-correlation-id] - Using Azure OpenAI client
2026-01-10 07:30:00 - agentic_devops - INFO - [no-correlation-id] - ChatAgent created successfully
2026-01-10 07:30:00 - agentic_devops - INFO - [no-correlation-id] - FastAPI app created with AG-UI endpoint
2026-01-10 07:30:00 - agentic_devops - INFO - [no-correlation-id] - Starting AG-UI server on http://127.0.0.1:5100
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:5100 (Press CTRL+C to quit)
```

### 3. Test with Basic Client

In a new terminal:

```bash
python agui_client.py
```

Example conversation:
```
Connecting to AG-UI server at: http://127.0.0.1:5100/

Type ':q' or 'quit' to exit

User: Hello!

[Thread: abc123-def456-789]
Assistant: Hello! I'm your AI assistant. How can I help you today?

User: What time zone is Seattle in?
Assistant: [SERVER] get_time_zone called with location: Seattle
Seattle is in Pacific Time (UTC-8).

User: :q
Goodbye!
```

### 4. Test Hybrid Tools Client

In a new terminal:

```bash
python agui_client_hybrid.py
```

Example conversation showing hybrid tools:
```
======================================================================
ChatAgent + AGUIChatClient: Hybrid Tool Execution Demo
======================================================================

Server: http://127.0.0.1:5100/

This demo shows:
  1. AgentThread maintains conversation state
  2. Client-side tools (get_weather) execute locally
  3. Server-side tools (get_time_zone) execute on server
  4. HYBRID: Both client and server tools work together

Type ':q' or 'quit' to exit
======================================================================

User: What's the weather like in Seattle?
[CLIENT] get_weather called with location: Seattle
[CLIENT] get_weather returning: Rainy, 55°F
Assistant: The weather in Seattle is currently rainy with a temperature of 55°F.

User: What time zone is that?
[SERVER] get_time_zone called with location: Seattle
[SERVER] get_time_zone returning: Pacific Time (UTC-8)
Assistant: Seattle is in Pacific Time (UTC-8).

User: How about Tokyo?
[CLIENT] get_weather called with location: Tokyo
[CLIENT] get_weather returning: Clear, 70°F
[SERVER] get_time_zone called with location: Tokyo
[SERVER] get_time_zone returning: Japan Standard Time (UTC+9)
Assistant: In Tokyo, the weather is currently clear with a temperature of 70°F, and it's in Japan Standard Time (UTC+9).
```

Notice how:
- `get_weather` (client tool) executes locally and you see `[CLIENT]` logs
- `get_time_zone` (server tool) executes on server and you see `[SERVER]` logs in the server terminal
- Both tools work together seamlessly in the same conversation!

### 5. View API Documentation

Open your browser to:
- **OpenAPI Docs**: http://127.0.0.1:5100/docs
- **ReDoc**: http://127.0.0.1:5100/redoc

You can test the API endpoints directly from the Swagger UI.

## Features Demonstrated

### Streaming Responses
Both clients use Server-Sent Events (SSE) to stream responses in real-time, character by character.

### Thread Management
The AG-UI protocol automatically manages conversation threads, maintaining context across multiple exchanges.

### Hybrid Tool Execution
The advanced client demonstrates the power of AG-UI's hybrid execution model:
- **Client-side tools** execute locally (get_weather)
- **Server-side tools** execute on the server (get_time_zone)  
- The LLM can use both seamlessly in the same conversation

### Type Safety
All code includes full type hints and passes mypy strict checking.

### Structured Logging
Both server and client include structured logging with correlation IDs for tracing.

## Architecture

```
┌─────────────────┐         HTTP/SSE          ┌──────────────────┐
│                 │◄──────────────────────────►│                  │
│  AG-UI Client   │    POST /chat              │  AG-UI Server    │
│  (Python CLI)   │    (streaming)             │  (FastAPI)       │
│                 │                            │                  │
│  Client Tools:  │                            │  Server Tools:   │
│  - get_weather  │                            │  - get_time_zone │
└─────────────────┘                            └──────────────────┘
                                                        │
                                                        ▼
                                                ┌──────────────────┐
                                                │                  │
                                                │  ChatAgent       │
                                                │  (Agent          │
                                                │   Framework)     │
                                                │                  │
                                                └──────────────────┘
                                                        │
                                                        ▼
                                                ┌──────────────────┐
                                                │  Azure OpenAI    │
                                                │  or OpenAI API   │
                                                └──────────────────┘
```

## Troubleshooting

### Server won't start
- Check that port 5100 is not already in use
- Verify API keys are set in .env file
- Check logs for specific error messages

### Client can't connect
- Ensure server is running first
- Verify server URL (default: http://127.0.0.1:5100/)
- Check firewall settings

### Tools not executing
- Check that tools are registered with the agent
- View server logs to see tool execution
- Verify tool definitions have proper type hints

### No streaming output
- Ensure you're using `get_streaming_response()` not `get_response()`
- Check that the server supports SSE
- Verify Accept header is set to "text/event-stream"
