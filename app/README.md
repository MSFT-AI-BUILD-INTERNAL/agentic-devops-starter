# Agentic DevOps Starter — Application

Conversational AI application powered by the **GitHub Copilot SDK**. The backend streams responses via the AG-UI SSE protocol, and a React frontend renders them in real time.

## Architecture

```
app/
├── agui_server.py           # FastAPI app factory (entry point)
├── agui_client.py           # CLI chat client (smoke-test tool)
├── src/
│   ├── api/                 # FastAPI routes, API models, SSE helpers
│   ├── core/                # Settings, logging, observability
│   ├── runtime/             # Copilot client/session state, jobs, skills
│   ├── storage/             # Blob storage and upload validation
│   ├── teams/               # Multi-agent orchestration and pattern data
│   └── *.py                 # Compatibility imports for legacy module paths
├── frontend/                # React + TypeScript + Vite
├── tests/                   # pytest test suite
├── pyproject.toml           # Python deps (uv-managed)
├── Dockerfile.appservice    # Production multi-stage build
└── .env.example             # Environment variable reference
```

## Prerequisites

- **Python ≥ 3.12**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **Node.js ≥ 20** — for the frontend
- **GitHub CLI** (`gh`) — authenticated with `gh auth login`
  - Required for the Copilot SDK (it uses your GitHub Copilot entitlement)
  - Your GitHub account must have an active Copilot subscription

## Quick Start (Local Development)

### 1. Install backend dependencies

```bash
cd app
uv sync --frozen --all-extras
```

### 2. Configure environment

```bash
cp .env.example .env
# No edits needed for local dev — SDK uses `gh auth` automatically
```

### 3. Start the backend

```bash
cd app
uv run agui_server.py
```

The server starts at **http://127.0.0.1:5100**:
- `POST /` — AG-UI streaming endpoint (used by frontend)
- `GET /health` — health check
- `POST /v1/fleet` — parallel multi-prompt execution
- `POST /v1/infinite-session` — chained reasoning loop
- `GET /v1/jobs/{job_id}` — async job status
- `GET /docs` — interactive OpenAPI docs

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

| Method | Path | Description |
|--------|------|-------------|
| `POST /` | AG-UI SSE stream | Chat with streaming (frontend uses this) |
| `GET /health` | Health check | Returns `{"status": "healthy"}` |
| `POST /v1/fleet` | Fleet execution | Run up to 20 prompts in parallel |
| `POST /v1/infinite-session` | Chained reasoning | Output N → Input N+1, up to 10 iterations |
| `GET /v1/jobs/{job_id}` | Job status | Poll async job results |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Production only | — | GitHub PAT with `copilot` scope (local dev uses `gh auth`) |
| `COPILOT_API_HOST` | No | `0.0.0.0` | Server bind address |
| `COPILOT_API_PORT` | No | `5100` | Server port |
| `COPILOT_API_LOG_LEVEL` | No | `INFO` | Log level |
| `COPILOT_API_SESSION_TIMEOUT` | No | `120.0` | Copilot session timeout (seconds) |
| `CORS_ORIGINS` | No | `localhost:5173` | Comma-separated CORS origins |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | No | — | Enables Azure Monitor tracing |
| `OTEL_SERVICE_NAME` | No | `agentic-devops-starter` | OpenTelemetry service name |
| `COPILOT_API_CLI_OTEL_ENDPOINT` | No | — | Enables OTLP export from the GitHub Copilot CLI subprocess, for example `http://localhost:4318` |
| `COPILOT_API_CLI_OTEL_EXPORTER_TYPE` | No | `otlp-http` | Copilot CLI telemetry exporter: `otlp-http` or `file` |
| `COPILOT_API_CLI_OTEL_FILE_PATH` | No | — | JSON-lines telemetry file path when using the `file` exporter |
| `COPILOT_API_CLI_OTEL_SOURCE_NAME` | No | `agentic-devops-starter` | Instrumentation source name reported by the Copilot CLI |
| `COPILOT_API_CLI_OTEL_CAPTURE_CONTENT` | No | `false` | Whether Copilot CLI telemetry captures prompt/response content |

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

The app deploys to **Azure App Service** as a single container:

1. **Frontend** — built to static files, served by NGINX on `:8080`
2. **Backend** — FastAPI on `:5100`, proxied via NGINX at `/api/*`
3. **Supervisor** — manages both processes

See [`Dockerfile.appservice`](./Dockerfile.appservice) and the [deploy workflow](../.github/workflows/deploy.yml).

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `ACR_NAME` | Azure Container Registry name |
| `APP_SERVICE_NAME` | App Service resource name |
| `RESOURCE_GROUP` | Azure resource group |
| `AZURE_CLIENT_ID` | OIDC service principal |
| `AZURE_TENANT_ID` | Azure AD tenant |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `COPILOT_GITHUB_TOKEN` | GitHub PAT with `copilot` scope |

## How It Works

```
Browser → React (useChat hook)
  → POST /api/ (Vite proxy in dev, NGINX in prod)
    → FastAPI POST / (agui_server.py)
      → CopilotClient.create_session()
        → Copilot SDK CLI subprocess
          → GitHub Copilot LLM
      ← SessionEvent stream (deltas)
    ← SSE: RUN_STARTED → TEXT_MESSAGE_CONTENT* → TEXT_MESSAGE_END → RUN_FINISHED
  ← Real-time token rendering in chat UI
```

**Authentication flow:**
- **Local dev**: SDK spawns bundled CLI → uses `gh auth` token automatically
- **Production**: `GITHUB_TOKEN` env var → `CopilotClient(github_token=...)` → CLI authenticates via PAT

## License

See LICENSE file in the repository root.
