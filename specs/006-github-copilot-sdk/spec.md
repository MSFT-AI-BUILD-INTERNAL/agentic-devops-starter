# Feature Specification: GitHub Copilot SDK Migration

**Feature ID**: 006-github-copilot-sdk  
**Date**: 2026-05-13  
**Status**: Complete

## Overview

Replace the Microsoft Foundry (Azure AI Agents) LLM backend with the
**GitHub Copilot SDK** (`github-copilot-sdk`) to leverage server-side
context engineering features — specifically **Fleet** (parallel multi-session)
and **Infinite Session** (chained iterative prompting) — without building
custom client-level context management.

## Background

The original backend used:
- `AzureAIAgentClient` / `AzureAIClient` from `agent_framework_azure_ai`
- Azure AI Agents service with `ENDPOINT` + `DEPLOYMENT` configuration
- `temperature` / `top_p` parameter management for o-series model compatibility

This required client-level context engineering for multi-session orchestration.
The GitHub Copilot SDK provides these capabilities as first-class primitives,
reducing complexity and enabling features like Fleet and Infinite Session
out of the box.

**Reference implementation**: https://github.com/MSFT-AI-Build/copilot-sdk-toolkit

## Motivation

1. **Fleet**: Execute multiple independent Copilot sessions in parallel with
   `asyncio.gather()` + semaphore throttling. Enables batch processing,
   A/B prompt comparison, and fan-out/fan-in patterns.
2. **Infinite Session**: Chain multiple Copilot sessions where output of
   iteration N becomes the prompt for iteration N+1. Enables iterative
   refinement, multi-step reasoning, and progressive summarization.
3. **Simplified auth**: Single `GITHUB_TOKEN` (PAT with Copilot scope) replaces
   multiple Azure credentials (`ENDPOINT`, `DEPLOYMENT`, `AZURE_CLIENT_ID`, etc.).
4. **Server-side context**: The SDK handles session state, token management,
   and context windows internally.

## Architecture

### SDK Integration Pattern

```
CopilotClient (singleton, managed in app lifespan)
  ├── start() / stop() lifecycle
  ├── SubprocessConfig(github_token=...) for production
  └── use_logged_in_user=True (gh auth) for local dev

CopilotSession (per-request, created from client)
  ├── on(callback) — event-driven: delta, complete, error, idle
  ├── send(prompt) — initiates generation
  └── destroy() — cleanup
```

### Event Flow (AG-UI Streaming)

```
Client POST /api/ → Backend creates CopilotSession
  → session.send(prompt)
  → AssistantMessageDeltaData → SSE: TEXT_MESSAGE_CONTENT (delta)
  → SessionIdleData → SSE: TEXT_MESSAGE_END, RUN_FINISHED
```

**Important**: When `streaming=True`, the SDK emits both
`AssistantMessageDeltaData` (incremental tokens) and `AssistantMessageData`
(complete assembled message). Only delta events should be forwarded to avoid
duplicate content in the response.

### File Structure (Post-Migration)

```
app/
├── agui_server.py          # App factory, lifespan (CopilotClient init)
├── src/
│   ├── routes.py           # API routes (AG-UI streaming, fleet, infinite-session)
│   ├── models.py           # Pydantic models (FleetRequest, InfiniteSessionRequest, etc.)
│   ├── jobs.py             # Async job manager (fleet parallel, infinite-session chain)
│   ├── state.py            # CopilotClient singleton (get_client/set_client)
│   ├── config.py           # Settings via pydantic-settings
│   ├── observability.py    # OpenTelemetry setup
│   └── logging_utils.py    # Structured logging
├── tests/
│   ├── test_agui_server.py # Server creation, health, security headers
│   ├── test_fleet_infinite.py  # Fleet/Infinite Session endpoint tests
│   └── test_observability.py
└── pyproject.toml          # github-copilot-sdk dependency, uv prerelease=allow
```

## API Endpoints

| Method | Path                    | Description                        |
|--------|-------------------------|------------------------------------|
| POST   | `/`                     | AG-UI streaming chat (SSE)         |
| GET    | `/health`               | Health check                       |
| POST   | `/v1/fleet`             | Start parallel Fleet job (202)     |
| POST   | `/v1/infinite-session`  | Start chained session job (202)    |
| GET    | `/v1/jobs/{job_id}`     | Poll async job status/results      |

## Authentication

| Environment | Method                                              |
|-------------|-----------------------------------------------------|
| Local dev   | `gh auth login` (SDK uses logged-in user)           |
| Production  | `GITHUB_TOKEN` env var → `SubprocessConfig`         |
| CI/CD       | `COPILOT_GITHUB_TOKEN` secret → App Service setting |

## Key Technical Decisions

1. **Streaming duplicate fix**: `AssistantMessageData` (complete) is ignored
   when `streaming=True` because delta events already deliver all content.
   Forwarding both causes the response to appear twice in the UI.

2. **Thread-safe event bridging**: SDK callbacks fire from a background thread.
   Use `loop.call_soon_threadsafe(queue.put_nowait, ...)` to bridge into the
   asyncio event loop for SSE generation.

3. **Session lifecycle**: Each request creates and destroys its own session.
   Multi-turn context is achieved by injecting prior conversation into the
   system message (not by reusing SDK sessions).

4. **Fleet concurrency**: `asyncio.Semaphore(20)` limits parallel sessions
   to avoid overwhelming the SDK subprocess.

5. **Job pattern**: Fleet and Infinite Session are long-running, so they
   return `202 Accepted` with a `job_id` for polling via `/v1/jobs/{job_id}`.

6. **No NGINX `/api/` prefix in routes**: Backend routes are registered
   without `/api/` prefix. Production NGINX (`Dockerfile.appservice`) maps
   external `/api/*` → backend `/*` via trailing-slash `proxy_pass`.

## Dependencies

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.5.0",
    "python-dotenv>=1.1.0",
    "github-copilot-sdk>=0.3.0",
]

[tool.uv]
prerelease = "allow"  # github-copilot-sdk is prerelease
```

## Deployment

- **Dockerfile.appservice**: Multi-stage (Node frontend → Python backend → NGINX+supervisor)
- **deploy.yml**: Replaced Azure AI secrets with single `COPILOT_GITHUB_TOKEN`
- **App Service setting**: `GITHUB_TOKEN` injected as environment variable

## Testing

- 21 tests total (all passing)
- Tests mock `CopilotClient` via `monkeypatch.setattr`
- No real SDK calls in CI (no token required for tests)

## Out of Scope

- Tool/function calling via Copilot SDK (future enhancement)
- Persistent session reuse across requests (each request is stateless)
- Frontend changes to expose Fleet/Infinite Session UI (API-only for now)
