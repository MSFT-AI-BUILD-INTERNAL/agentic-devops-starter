# AG-UI Server API Reference

HTTP/SSE API for the Agentic DevOps Starter backend. All chat endpoints stream responses using the [AG-UI SSE protocol](#sse-event-types). The underlying AI provider (GitHub Copilot SDK or Azure AI Foundry) is encapsulated behind the `AISessionPool` interface and is transparent to callers.

---

## Base URL

```
http://localhost:8000
```

---

## Authentication

| Endpoint | Auth required |
|---|---|
| `POST /` | GitHub OAuth session cookie (`_session`) |
| `POST /v1/byok/foundry` | None — server-side Azure credentials only |
| All other endpoints | None |

### Obtaining a GitHub session cookie

```bash
# 1. Initiate OAuth — opens GitHub login in browser
curl -c cookies.txt -L http://localhost:8000/auth/login

# 2. Complete login in the browser; the callback sets the session cookie
# 3. Verify the session
curl -b cookies.txt http://localhost:8000/auth/session
# → {"authenticated": true}
```

---

## Chat Endpoints

Both endpoints share the same request body and SSE response format. The only difference is the AI provider used on the server.

### POST /
GitHub Copilot SDK backend. Requires an authenticated GitHub session.

### POST /v1/byok/foundry
Azure AI Foundry BYOK backend. No client-side auth required; the server uses its configured Azure credentials.

#### Request body

```json
{
  "messages": [
    { "role": "user", "content": "Hello, what can you do?" }
  ],
  "thread_id": "test-thread-001",
  "run_id": "run-001",
  "attachments": []
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `messages` | `array` | Yes | Conversation history. Only the latest user message is forwarded to the SDK; prior turns are managed server-side per `thread_id`. |
| `thread_id` | `string` | No | Identifies the conversation session. Omit to generate one automatically. Reuse the same value across turns to maintain history. |
| `run_id` | `string` | No | Identifies this specific generation run. Echoed back in `RUN_STARTED` / `RUN_FINISHED` events. |
| `attachments` | `array` | No | List of previously uploaded blob references to include as file context. |

#### Response

`Content-Type: text/event-stream` — newline-delimited SSE. See [SSE Event Types](#sse-event-types).

---

## SSE Event Types

Each line in the stream is prefixed with `data: ` and contains a JSON object.

```
data: {"type": "RUN_STARTED", "thread_id": "...", "run_id": "..."}

data: {"type": "TEXT_MESSAGE_START", "message_id": "abc123"}

data: {"type": "TEXT_MESSAGE_CONTENT", "delta": "Hello! I can "}

data: {"type": "TEXT_MESSAGE_CONTENT", "delta": "help you with..."}

data: {"type": "TEXT_MESSAGE_END", "message_id": "abc123"}

data: {"type": "RUN_FINISHED", "thread_id": "...", "run_id": "..."}
```

| Event type | Description |
|---|---|
| `RUN_STARTED` | Generation started. Contains `thread_id` and `run_id`. |
| `TEXT_MESSAGE_START` | Assistant message begins. Contains `message_id`. |
| `TEXT_MESSAGE_CONTENT` | Incremental text chunk. Contains `delta`. |
| `TEXT_MESSAGE_END` | Assistant message complete. Contains `message_id`. |
| `RUN_FINISHED` | Generation complete. Always emitted, even on error. |
| `RUN_ERROR` | An error occurred. Contains `message`. |

---

## curl Examples

### Single-turn (Foundry, no auth)

```bash
curl -N -X POST http://localhost:8000/v1/byok/foundry \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello, what can you do?"}],
    "thread_id": "test-thread-001",
    "run_id": "run-001"
  }'
```

### Multi-turn conversation

Reuse the same `thread_id` across requests. The server maintains session history internally.

```bash
# Turn 1
curl -N -X POST http://localhost:8000/v1/byok/foundry \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "My name is Alice."}],
    "thread_id": "test-thread-001",
    "run_id": "run-001"
  }'

# Turn 2 — server already knows the name from turn 1
curl -N -X POST http://localhost:8000/v1/byok/foundry \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is my name?"}],
    "thread_id": "test-thread-001",
    "run_id": "run-002"
  }'
```

### Copilot endpoint (GitHub OAuth session)

```bash
curl -N -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "thread_id": "test-thread-001",
    "run_id": "run-001"
  }'
```

---

## Thread Management

### DELETE /v1/threads/{thread_id}
Disconnect and clean up a conversation session. The session state is preserved on disk and can be resumed on the next request.

```bash
curl -X DELETE http://localhost:8000/v1/threads/test-thread-001
# → {"status": "deleted", "thread_id": "test-thread-001"}
```

### POST /v1/threads/{thread_id}/abort
Abort an in-progress generation without disconnecting the session.

```bash
curl -X POST http://localhost:8000/v1/threads/test-thread-001/abort
# → {"status": "aborted", "thread_id": "test-thread-001"}
# → {"status": "not_found", ...}  if no active generation
```

---

## Other Endpoints

### GET /health
Liveness check.
```bash
curl http://localhost:8000/health
# → {"status": "healthy"}
```

### POST /v1/fleet
Run multiple prompts in parallel (max 20 concurrent). Returns a `job_id` immediately; poll `/v1/jobs/{job_id}` for results.

```bash
curl -X POST http://localhost:8000/v1/fleet \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"prompt": "Summarize DevOps best practices"},
      {"prompt": "List common CI/CD tools"}
    ]
  }'
# → {"job_id": "abc123"}
```

### POST /v1/infinite-session
Run a chain of sessions where each output becomes the next input.

```bash
curl -X POST http://localhost:8000/v1/infinite-session \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Describe a DevOps pipeline",
    "iterations": 3
  }'
# → {"job_id": "abc123"}
```

### GET /v1/jobs/{job_id}
Poll async job status.

```bash
curl http://localhost:8000/v1/jobs/abc123
# → {"job_id": "abc123", "status": "completed", "results": [...]}
```

`status` values: `pending` → `running` → `completed` / `failed`

### GET /v1/patterns
List available multi-agent team patterns.

```bash
curl http://localhost:8000/v1/patterns
```

### POST /v1/teams/stream
Execute a multi-agent pattern with SSE streaming. Uses the same SSE event format as the chat endpoints.

```bash
curl -N -X POST http://localhost:8000/v1/teams/stream \
  -H "Content-Type: application/json" \
  -d '{
    "pattern_id": "<pattern-id>",
    "prompt": "Review this pull request",
    "thread_id": "teams-thread-001"
  }'
```

### POST /v1/files/upload
Upload a file to Azure Blob Storage for use as a chat attachment.

```bash
curl -X POST http://localhost:8000/v1/files/upload \
  -F "file=@/path/to/document.pdf"
# → {"blob_name": "...", "original_filename": "document.pdf", ...}
```

### GET /v1/mcp/tools
List tools available on the configured remote MCP server. Returns `[]` when no MCP server is configured.

```bash
curl http://localhost:8000/v1/mcp/tools
```

---

## Architecture Note

Chat endpoints route through an `AISessionPool` interface ([`src/runtime/state.py`](../app/src/runtime/state.py)). The two concrete implementations are:

| Pool | Endpoint | Provider |
|---|---|---|
| `SessionPool` | `POST /` | GitHub Copilot SDK |
| `FoundrySessionPool` | `POST /v1/byok/foundry` | Azure AI Foundry BYOK |

Adding a new AI provider requires only implementing the four-method `AISessionPool` Protocol — no changes to routes or lifecycle management needed.
