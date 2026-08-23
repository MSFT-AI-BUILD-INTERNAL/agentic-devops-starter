# Agentic DevOps Starter — Application

Conversational AI application powered by the **GitHub Copilot SDK**. The backend streams responses via the AG-UI SSE protocol, and a React frontend renders them in real time.

## Architecture

```
app/
├── agui_server.py           # FastAPI app factory (entry point, lifespan, middleware)
├── agui_client.py           # CLI chat client (smoke-test tool)
├── src/
│   ├── api/
│   │   ├── routes.py        # All HTTP route handlers (17 endpoints)
│   │   ├── auth.py          # GitHub App OAuth flow, Fernet cookie, AES-CMAC namespacing
│   │   ├── models.py        # Pydantic request/response models
│   │   ├── sse_utils.py     # SSE wire-format helpers
│   │   └── error_handler.py
│   ├── core/
│   │   ├── config.py        # Pydantic Settings (env vars, aliases)
│   │   ├── logging_utils.py # CorrelationFilter, logger setup
│   │   └── observability.py # Azure Monitor OpenTelemetry init
│   ├── runtime/
│   │   ├── state.py         # SessionPool, FoundrySessionPool, CopilotClient singleton
│   │   ├── jobs.py          # In-memory async job manager (Fleet, Infinite Session)
│   │   ├── skills.py        # SKILL.md discovery and path resolution
│   │   ├── tools.py         # Built-in tool implementations
│   │   ├── mcp_client.py    # Remote MCP server client (activated by MCP_SERVER_URL)
│   │   └── isolation.py     # X-Isolation-Session-ID scoping
│   ├── storage/
│   │   ├── blob_storage.py  # Azure Blob upload/download
│   │   └── file_validation.py # MIME/extension/size validation, blob name sanitisation
│   └── teams/
│       ├── orchestrator.py  # Multi-agent team execution, SSE streaming
│       ├── patterns.py      # Pattern/AgentRole models, YAML loader
│       └── data/patterns.yaml # 5 built-in team patterns
├── skills/                  # Built-in SKILL.md definitions (code-reviewer, etc.)
├── frontend/                # React + TypeScript + Vite
├── tests/                   # pytest test suite
├── pyproject.toml           # Python deps (uv-managed)
├── Dockerfile.appservice    # Production multi-stage build (4 stages)
└── .env.example             # Environment variable reference
```

## Prerequisites

- **Python ≥ 3.12**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **Node.js ≥ 20** — for the frontend
- A GitHub account with an active Copilot subscription

## Quick Start (Local Development)

### 1. Install backend dependencies

```bash
cd app
uv sync --frozen --all-extras
```

### 2. Configure environment

```bash
cp .env.example .env
```

Set `COPILOT_APP_CLIENT_ID` and `COPILOT_APP_CLIENT_SECRET` from your GitHub App settings.
Configure the GitHub App **Callback URL** to `http://localhost:8080/auth/callback` for local
development (production value: `https://app-agentic-devops.azurewebsites.net/auth/callback`).

> `COPILOT_APP_CLIENT_SECRET` has a dual role: it is sent to GitHub during the OAuth token
> exchange **and** used as the PBKDF2 passphrase (600k iterations, SHA-256) that derives the
> Fernet cookie-encryption key and the AES-CMAC session-namespace key. Without it set,
> `GET /auth/login` returns HTTP 503 and `POST /` returns HTTP 401.

### 3. Start the backend

```bash
cd app
uv run agui_server.py
```

The server starts at **http://127.0.0.1:5100**. See [API Endpoints](#api-endpoints) for the full route list.

### 4. Start the frontend (separate terminal)

```bash
cd app/frontend
npm ci
npm run dev
```

Opens at **http://localhost:8080**. The Vite dev server proxies `/api/*` → backend `:5100`.

### 5. Test with the CLI client (optional)

```bash
cd app
uv run agui_client.py
```

## API Endpoints

Auth is enforced by direct checks inside route handlers. `POST /` requires the session cookie; `/v1/models` and `/v1/messages` require `THIRDPARTY_API_KEY`; all other routes are unauthenticated at the route level.

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/` | ✓ | AG-UI SSE stream — GitHub Copilot |
| `POST` | `/v1/byok/foundry` | — | AG-UI SSE stream — Azure AI Foundry BYOK (bypasses OAuth) |
| `GET` | `/v1/models` | API key | List Copilot models via the Anthropic-compatible adapter |
| `POST` | `/v1/messages` | API key | Anthropic-compatible Messages API adapter backed by Copilot SDK |
| `GET` | `/auth/login` | — | Redirect to GitHub App OAuth consent page |
| `GET` | `/auth/callback` | — | OAuth callback; exchanges code, sets encrypted session cookie |
| `GET` | `/auth/session` | — | Returns `{"authenticated": true}` or HTTP 401 (frontend probe) |
| `POST` | `/auth/logout` | — | Deletes `github_oauth_session` cookie (HTTP 204) |
| `GET` | `/health` | — | Returns `{"status": "healthy"}` |
| `POST` | `/v1/files/upload` | — | Upload a validated file to Azure Blob Storage |
| `DELETE` | `/v1/threads/{thread_id}` | — | Disconnect and clean up a Copilot session |
| `POST` | `/v1/threads/{thread_id}/abort` | — | Abort an active chat or team generation |
| `POST` | `/v1/fleet` | — | Start up to 20 prompts in parallel; returns `job_id` (HTTP 202) |
| `POST` | `/v1/infinite-session` | — | Start chained reasoning (1–10 iterations); returns `job_id` (HTTP 202) |
| `GET` | `/v1/patterns` | — | List available multi-agent team patterns |
| `POST` | `/v1/teams/stream` | — | Stream multi-agent team execution |
| `GET` | `/v1/jobs/{job_id}` | — | Poll async job status |
| `GET` | `/v1/mcp/tools` | — | List tools from the remote MCP server (empty if `MCP_SERVER_URL` unset) |
| `GET` | `/docs` | — | Interactive OpenAPI UI |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `COPILOT_APP_CLIENT_ID` | OAuth | — | GitHub App client ID. Also accepted as `GITHUB_CLIENT_ID` |
| `COPILOT_APP_CLIENT_SECRET` | OAuth | — | GitHub App client secret. **Dual use**: OAuth token exchange AND PBKDF2 passphrase (600k iterations, SHA-256) for both the Fernet session-cookie cipher and the AES-CMAC user-namespace key. Also accepted as `GITHUB_CLIENT_SECRET` |
| `COPILOT_APP_REDIRECT_URI` | OAuth | — | GitHub App callback URL. Local: `http://localhost:8080/auth/callback`. Production: `https://<app>.azurewebsites.net/auth/callback`. Also accepted as `GITHUB_OAUTH_REDIRECT_URI` |
| `COPILOT_API_HOST` | No | `0.0.0.0` | Server bind address |
| `COPILOT_API_PORT` | No | `5100` | Server port |
| `COPILOT_API_LOG_LEVEL` | No | `INFO` | Log level |
| `COPILOT_API_SESSION_TIMEOUT` | No | `120.0` | Copilot session idle timeout (seconds) |
| `COPILOT_API_ISOLATION_SESSION_HEADER` | No | `X-Isolation-Session-ID` | Header for session/file isolation. When OAuth is active, combined with the per-user AES-CMAC namespace to form the final session pool key |
| `COPILOT_API_SESSION_CONFIG_ROOT_DIR` | No | `.copilot-session-config` | Base directory for per-isolation Copilot session config |
| `COPILOT_API_TOOL_TIMEOUT` | No | `10.0` | Default timeout (seconds) for each tool invocation |
| `THIRDPARTY_API_KEY` | Third-party API | — | Shared API key required from `GET /v1/models` / `POST /v1/messages` callers via `Authorization` bearer token or `x-api-key` |
| `THIRDPARTY_GITHUB_PAT` | Third-party API | — | PAT used to authenticate the Copilot SDK session for `POST /v1/messages` (Anthropic-compatible endpoint for third-party clients like Claude Code). This stands in for the GitHub Apps OAuth token the browser flow would normally supply |
| `COPILOT_API_EXCLUDED_TOOLS` | No | filesystem/shell/database tools | Comma-separated SDK built-in tools to disable. Unset applies a secure-by-default denylist (`bash`, `write_bash`, `read_bash`, `stop_bash`, `list_bash`, `view`, `create`, `edit`, `grep`, `glob`, `sql`). Ignored when `COPILOT_API_ALLOWED_TOOLS` is set |
| `COPILOT_API_ALLOWED_TOOLS` | No | — | Comma-separated tool allowlist. When set, only listed tools are enabled and the denylist is ignored |
| `MCP_SERVER_URL` | No | — | Remote MCP server URL (e.g. `https://<name>.azurecontainerapps.io`). Enables `/v1/mcp/tools` and registers MCP tools in Copilot sessions. Omit to run with built-in tools only |
| `COPILOT_API_SKILL_DIRECTORIES` | No | — | Extra directories (colon- or comma-separated) scanned for `SKILL.md` agent-skill files |
| `COPILOT_API_DISABLED_SKILLS` | No | — | Comma-separated skill names to disable |
| `COPILOT_API_APP_CONFIG_ENDPOINT` | No | — | Azure App Configuration endpoint (e.g. `https://<store>.azconfig.io`). Loaded at startup; env vars take precedence |
| `COPILOT_API_APP_CONFIG_LABEL` | No | — | Label filter for Azure App Configuration key-values |
| `COPILOT_API_AZURE_STORAGE_BLOB_ENDPOINT` | File upload | — | Blob endpoint, e.g. `https://<account>.blob.core.windows.net` |
| `COPILOT_API_AZURE_STORAGE_CONTAINER_NAME` | No | `uploads` | Upload container name |
| `AZURE_AI_PROJECT_ENDPOINT` | BYOK | — | Azure AI Foundry endpoint for `POST /v1/byok/foundry` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | BYOK | — | Foundry model deployment name |
| `FOUNDRY_AUTH_MODE` | BYOK | `auto` | `auto`, `api_key`, or `azure_identity` |
| `FOUNDRY_API_KEY` | BYOK (api_key) | — | Foundry API key when `FOUNDRY_AUTH_MODE=api_key` |
| `FOUNDRY_WIRE_API` | BYOK | — | Wire protocol: `responses` or `completions` |
| `CORS_ORIGINS` | No | `localhost:5173` | Comma-separated CORS origins. `allow_credentials=True` is required for cookie auth |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | No | — | Enables Azure Monitor tracing |
| `OTEL_SERVICE_NAME` | No | `agentic-devops-starter` | OpenTelemetry service name |
| `COPILOT_API_CLI_OTEL_ENDPOINT` | No | — | OTLP/HTTP endpoint for GitHub Copilot CLI subprocess telemetry, e.g. `http://localhost:4318` |
| `COPILOT_API_CLI_OTEL_EXPORTER_TYPE` | No | `otlp-http` | CLI telemetry exporter: `otlp-http` or `file` |
| `COPILOT_API_CLI_OTEL_FILE_PATH` | No | — | JSON-lines telemetry file path when using the `file` exporter |
| `COPILOT_API_CLI_OTEL_SOURCE_NAME` | No | `agentic-devops-starter` | Instrumentation source name for the Copilot CLI |
| `COPILOT_API_CLI_OTEL_CAPTURE_CONTENT` | No | `false` | Whether CLI telemetry captures prompt/response content |
| `VITE_AGUI_ENDPOINT` | No | `/api` | Frontend API base URL (build-time, frontend only) |

Session-scoped routes and file upload accept `X-Isolation-Session-ID`. When OAuth is active,
the header value is combined with the per-user AES-CMAC namespace to produce the final session
pool key; send a stable per-browser value on every request.

### GitHub Copilot CLI telemetry

The backend uses `github-copilot-sdk`, which spawns the bundled GitHub Copilot CLI. To feed the Azure Application Insights GitHub Copilot Grafana dashboard, point that CLI subprocess at an OpenTelemetry Collector:

```text
FastAPI app → github-copilot-sdk → GitHub Copilot CLI subprocess
  → OTLP endpoint → OpenTelemetry Collector → Application Insights → Grafana
```

Set `COPILOT_API_CLI_OTEL_ENDPOINT` to the collector's OTLP/HTTP endpoint. Content capture is disabled by default; enable `COPILOT_API_CLI_OTEL_CAPTURE_CONTENT=true` only after reviewing prompt and response retention policies.

In the App Service container, supervisor also starts `otelcol-contrib` with `otel-collector-config.yaml`. When `APPLICATIONINSIGHTS_CONNECTION_STRING` is set and `COPILOT_API_CLI_OTEL_ENDPOINT` is not explicitly set, `start-backend.sh` defaults the Copilot CLI endpoint to `http://127.0.0.1:4318`.

For local testing, run the OpenTelemetry Collector with the included config:

```bash
cd app
docker run --rm -p 4318:4318 \
  -e APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=..." \
  -v "$PWD/otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml" \
  otel/opentelemetry-collector-contrib:latest
```

## Development Commands

All commands run from `app/`:

```bash
# Install dependencies
uv sync --frozen --all-extras

# Run the server
uv run agui_server.py

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy .

# Run tests
uv run pytest tests/ -v
```

Frontend commands (from `app/frontend/`):

```bash
npm ci                  # Install deps
npm run dev             # Dev server (:8080, proxies /api → :5100)
npm run build           # Production build
npm run lint            # ESLint
npm run type-check      # TypeScript check
npm run test            # Vitest unit tests
npm run test:e2e        # Playwright E2E tests
```

## Production Deployment

The app deploys to **Azure App Service** as a single container built from `Dockerfile.appservice` (4 stages):

| Stage | Base | Output |
|-------|------|--------|
| `frontend-build` | `node:20-alpine` | Vite production build at `/dist` |
| `otel-collector` | `otel/opentelemetry-collector-contrib` | `otelcol-contrib` binary |
| `backend-base` | `python:3.12-slim` | uv, nginx, supervisor, Python deps |
| `final` | `backend-base` | Combined image: frontend dist + OTel Collector binary + backend |

At runtime **supervisor** manages three processes:

| Process | Port | Role |
|---------|------|------|
| nginx | 8080 | Serves frontend SPA; proxies `/api/*` → FastAPI, `/health` → FastAPI |
| uvicorn (FastAPI) | 5100 | API backend |
| otelcol-contrib | 4318 | Forwards GitHub Copilot CLI OTLP telemetry to Application Insights |

### nginx routing

| External path | Destination |
|---------------|-------------|
| `/api/` | `http://127.0.0.1:5100/` (prefix stripped, 300s timeout) |
| `/auth/*` | `http://127.0.0.1:5100/auth/` (passthrough) |
| `/health` | `http://127.0.0.1:5100/health` |
| `/` and SPA routes | `try_files` → `/index.html` |
| Other methods | HTTP 405 |

### Required GitHub Actions Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | OIDC service principal client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `ACR_NAME` | Azure Container Registry name |
| `APP_SERVICE_NAME` | App Service resource name |
| `RESOURCE_GROUP` | Azure resource group |
| `COPILOT_APP_CLIENT_ID` | GitHub App client ID (injected as `GITHUB_CLIENT_ID`) |
| `COPILOT_APP_CLIENT_SECRET` | GitHub App client secret; also PBKDF2 passphrase for cookie encryption (injected as `GITHUB_CLIENT_SECRET`) |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Foundry endpoint for BYOK |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Foundry model deployment name |
| `FOUNDRY_AUTH_MODE` | Foundry auth mode: `auto`, `api_key`, or `azure_identity` |
| `FOUNDRY_API_KEY` | Foundry API key (only for `api_key` mode) |
| `FOUNDRY_WIRE_API` | Foundry wire protocol: `responses` or `completions` |
| `APP_CONFIG_ENDPOINT` | Azure App Configuration endpoint |
| `APP_CONFIG_LABEL` | Azure App Configuration label filter |
| `MCP_SERVER_URL` | Remote MCP server URL |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Enables Azure Monitor telemetry and OTel Collector |
| `PLAYWRIGHT_GITHUB_TOKEN` | GitHub PAT for E2E test Fernet cookie generation |
| `PLAYWRIGHT_GITHUB_CLIENT_SECRET` | Same as `COPILOT_APP_CLIENT_SECRET`; used by E2E setup to replicate the cookie cipher |

See [`Dockerfile.appservice`](./Dockerfile.appservice) and the [deploy workflow](../.github/workflows/deploy.yml).

## How It Works

### Authentication (GitHub App OAuth)

```
App.tsx mounts
  → GET /api/auth/session (with cookie)
      → 401 (no session)
  → window.location.assign(/api/auth/login)
      → GitHub consent page
      → GET /api/auth/callback?code=...&state=...
          → exchange_code() → GitHub user token (ghu_...)
          → Fernet-encrypt(token) → set github_oauth_session cookie
              (httponly; secure; samesite=lax; max_age=28800)
  → GET /api/auth/session → 200 {"authenticated": true}
```

### Chat Streaming (GitHub Copilot)

```
Browser → POST /api/ (with session cookie)
  → get_user_token() → decrypt cookie → ghu_...
  → get_user_isolation_namespace() → AES-CMAC(token + X-Isolation-Session-ID)
  → SessionPool.get_or_create(namespace, github_token=ghu_...)
      → CopilotClient.create_session(skill_directories, tools)
  ← SSE: RUN_STARTED → TEXT_MESSAGE_CONTENT* → RUN_FINISHED
```

### Chat Streaming (Azure AI Foundry BYOK)

```
Browser → POST /api/v1/byok/foundry (no auth required)
  → FoundrySessionPool.get_or_create(thread_id, github_token=None)
      → Foundry provider (AZURE_AI_PROJECT_ENDPOINT, FOUNDRY_WIRE_API)
  ← SSE: same wire format as Copilot path
```

### Agent Teams

```
Browser → POST /api/v1/teams/stream
  → load pattern from patterns.yaml (5 built-in patterns)
  → run_teams(): spawn one CopilotSession per agent role
      → each agent streams output SSE events
      → output chaining between roles (pattern-dependent)
  ← SSE: per-agent RUN_STARTED / TEXT_MESSAGE_CONTENT* / RUN_FINISHED
```

### File Upload

```
Browser → POST /api/v1/files/upload (multipart)
  → validate_file_type() + validate_file_size() (10 MB limit)
  → BlobStorageService.upload() → Azure Blob Storage (private endpoint)
  ← {blob_url, container, blob_name}
  → blob_url included in next chat message as attachment
```

## License

See LICENSE file in the repository root.
