# AGENTS.md — Agentic DevOps Starter

> Harness Engineering configuration for GitHub Copilot agents.
> Each harness defines scope, conventions, and tooling for a specific domain of this project.

---

## agent-security

### Scope

All agent input processing, output generation, and file system interactions across `app/src/`.

### Security Policy

Agents **must never**:
- Execute or suggest shell/system commands: `sudo`, `rm -rf`, `kill -9`, `chmod`, `chown`, `shutdown`, `reboot`, `mkfs`, `dd if=`, `eval()`, `exec()`, `os.system()`, `subprocess.run/call/Popen`
- Access or reference restricted paths: `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/proc/`, `/sys/`, `/dev/`, `/boot/`, `.ssh/`, `.aws/credentials`, `.azure/`, `.env`, `.secret`
- Expose sensitive data in responses: passwords, API keys, bearer tokens, credentials, private keys, credit card numbers
- Attempt privilege escalation: bypass auth, request admin/root access, `grant all privileges`
- Use backtick command execution or pipe-to-shell patterns

### Enforcement

All agents inherit `SecurityValidator` from `src/security/validator.py`.

- `validate_input_security(text)` is called before processing every user message.
- `validate_output_security(text)` is called on every generated response.
- Violations are logged at `WARNING` level with category and severity.
- `HarnessHook` (see `agent-hooks` below) provides the post-execution check.

### Commands

```bash
cd app
uv run pytest tests/test_security.py -v   # Run security tests
```

---

## agent-prompts

### Scope

All agent system prompt definitions. `app/src/prompts/`.

### Convention

**Prompts must never be hardcoded in application code.**
All system prompts are centrally defined in `app/src/prompts/system_prompts.yaml`
and loaded at runtime via `PromptManager`.

#### Key schema

```
<agent_name>.<prompt_type>
```

Examples:
- `agui_assistant.system` — system prompt for the production AG-UI assistant
- `conversational.system` — system prompt for the demo ConversationalAgent
- `devops.system` — system prompt for a DevOps-focused agent
- `default.system` — fallback used when no specific key is found

#### How to add a prompt

1. Open `app/src/prompts/system_prompts.yaml`.
2. Add a new key under the `prompts:` mapping using YAML block scalar syntax (`|`):
   ```yaml
   prompts:
     my_agent.system: |
       You are a specialized AI assistant for <task>.
       ...
   ```
3. Load it in your agent via `PromptManager().get("my_agent.system")`.

#### How agents load prompts

`BaseAgent.__init__` automatically resolves the system prompt:

1. If an explicit `system_prompt=` argument is provided, it is used.
2. Otherwise, `PromptManager.get(f"{name.lower()}.system")` is tried.
3. Falls back to `default.system` if no matching key exists.

### Commands

```bash
cd app
uv run pytest tests/test_prompts.py -v   # Run prompt manager tests
```

---

## agent-skills

### Scope

`app/src/agents/tools.py` — skill definitions and `SkillRegistry`.

### Convention

Agent capabilities are expressed as **AgentSkills**, not ad-hoc tool functions.  Every skill:

1. Inherits from `AgentSkill` (replaces the legacy `Tool` base class).
2. Implements `get_definition() -> SkillDefinition` with:
   - `name` — unique identifier
   - `description` — human-readable purpose
   - `parameters` — JSON-schema-style parameter spec
   - `examples` — ≥1 example invocations to help agents decide when to use this skill
3. Implements `execute(**kwargs)` with typed arguments.
4. Is registered in `SkillRegistry` (default registry built by `build_default_registry()`).

#### Skill-aware response generation

Agents must check `self.describe_skills()` (which calls `SkillRegistry.describe()`) when
generating responses so they actively route applicable requests through skills:

```python
# Route arithmetic queries to the calculator skill
if "calculate" in message.lower():
    return f"I can help. {self.describe_skills()}\nPlease provide operands."
```

#### Adding a new skill

1. Create a class inheriting `AgentSkill` in `app/src/agents/tools.py` (or a sibling module).
2. Add it to `build_default_registry()`.
3. Document at least one example in `SkillDefinition.examples`.

### Built-in skills

| Skill | Class | Description |
|-------|-------|-------------|
| `calculator` | `CalculatorSkill` | Basic arithmetic (add, subtract, multiply, divide) |
| `get_weather` | `WeatherSkill` | Weather lookup for a city/location |

### Commands

```bash
cd app
uv run pytest tests/test_hooks.py -v -k "skill"  # Run skill registry tests
```

---

## agent-hooks

### Scope

`app/src/hooks/harness_hook.py` — post-execution harness compliance validation.

### Convention

After every agent message processing cycle, `HarnessHook.run(user_input, agent_output)` **must be called**.

#### What it checks

- Applies all security rules from `SecurityValidator` to both the input and the output.
- Produces a `HarnessViolationReport` with:
  - `input_violations` — violations found in user input
  - `output_violations` — violations found in agent output
  - `has_violations` — True when any violation exists
  - `critical_violations` — violations with `severity='critical'`

#### Enforcement modes

| Mode | Setting | Behavior |
|------|---------|---------|
| Observe (default) | `fail_on_violation=False` | Violations are logged; execution continues |
| Enforce | `fail_on_violation=True` | `HarnessViolationError` raised on critical violations |

#### Integration in BaseAgent

`BaseAgent.run_harness_hook(user_input, agent_output)` provides the hook call point.
Concrete agents **must** call it at the end of `process_message()`:

```python
def process_message(self, message: str) -> str:
    ...
    response = self._generate_response(message)
    self.run_harness_hook(user_input=message, agent_output=response)
    return response
```

### Commands

```bash
cd app
uv run pytest tests/test_hooks.py -v   # Run hook tests
```

---

## python-backend

### Scope

Files under `app/src/`, `app/agui_server.py`, `app/agui_client.py`, `app/agui_client_hybrid.py`, `app/main.py`, and `app/pyproject.toml`.

### Tech Stack

- **Language**: Python ≥3.12
- **Framework**: FastAPI ≥0.115.0, Uvicorn ≥0.32.0
- **AI Framework**: Microsoft Agent Framework (`agent-framework-core`, `agent-framework-ag-ui`, `agent-framework-azure-ai`)
- **Validation**: Pydantic ≥2.0.0
- **Auth**: `azure-identity` (DefaultAzureCredential)
- **Package Manager**: uv (with `uv.lock`)

### Conventions

- Use Python 3.12+ syntax: `str | None` union types, `list[str]` generics.
- All functions must have type hints (`disallow_untyped_defs` enforced by mypy).
- Line length limit: 100 characters (Ruff).
- Ruff lint rules: `E`, `W`, `F`, `I`, `B`, `C4`, `UP`.
- Use Pydantic `BaseModel` for data classes and state management.
- Use `setup_logging()` from `src/logging_utils` with correlation IDs for observability.
- Agent classes inherit from `BaseAgent` (abstract) in `src/agents/base_agent.py`.
- Environment variables loaded via `python-dotenv`; never hardcode secrets.
- FastAPI server uses AG-UI protocol with SSE streaming.
- **System prompts** must be loaded via `PromptManager` — never hardcoded in code.
- **Security validation** must run on every agent input and output via `SecurityValidator`.
- **Harness hook** must run at the end of every `process_message()` cycle.

### Commands

```bash
cd app
uv sync --frozen --all-extras   # Install dependencies (including dev)
uv run ruff check .             # Lint
uv run pytest tests/ -v         # Run tests
uv run mypy .                   # Type check
uv run agui_server.py           # Start dev server (port 5100)
```

---

## react-frontend

### Scope

Files under `app/frontend/`.

### Tech Stack

- **Language**: TypeScript 5.3+
- **Framework**: React 18.2, Vite 7.3
- **AI UI**: CopilotKit (`@copilotkit/react-core` ^1.51.2, `@copilotkit/react-ui` ^0.2.0)
- **State Management**: Zustand 5.0
- **Styling**: Tailwind CSS 3.4, PostCSS, Autoprefixer
- **Sanitization**: DOMPurify 3.3
- **Testing**: Vitest (unit), Playwright (E2E)

### Conventions

- Strict TypeScript: `strict: true`, `noUnusedLocals`, `noUnusedParameters`.
- Path alias: `@/*` maps to `./src/*`.
- Target: ES2020, Module: ESNext, JSX: `react-jsx`.
- Components in `src/components/`, hooks in `src/hooks/`, stores in `src/stores/`, types in `src/types/`.
- Use Zustand stores (`chatStore`, `themeStore`) for global state — avoid prop drilling.
- ESLint with zero warnings policy (`--max-warnings 0`).
- Dev server runs on port 8080 with proxy: `/api` → `http://127.0.0.1:5100`.

### Commands

```bash
cd app/frontend
npm ci                  # Install dependencies
npm run dev             # Start Vite dev server (port 8080)
npm run build           # TypeScript check + Vite build
npm run lint            # ESLint (zero warnings)
npm run type-check      # TypeScript only
npm run test            # Vitest unit tests
npm run test:e2e        # Playwright E2E tests
```

---

## terraform-infra

### Scope

Files under `infra/`.

### Tech Stack

- **IaC**: Terraform ≥1.5.0
- **Provider**: azurerm ~3.0
- **Target**: Azure (East US default)

### Architecture

Four active modules orchestrated by `infra/main.tf`:

| Module | Resource | Purpose |
|--------|----------|---------|
| `log-analytics/` | Log Analytics Workspace | Monitoring & log retention (30 days) |
| `acr/` | Azure Container Registry (Standard) | Private container image registry |
| `app-service-plan/` | App Service Plan (P1v3) | Compute tier for hosting |
| `app-service/` | Linux Web App | Container-based app hosting with managed identity |

Dependency chain: Resource Group → Log Analytics, ACR, App Service Plan → App Service.

### Conventions

- Each module has `main.tf`, `variables.tf`, `outputs.tf`.
- Use `variable` blocks with `description`, `type`, and `default`.
- Tag all resources with `var.tags` (Environment, Project, ManagedBy).
- Use System-Assigned Managed Identity for App Service (no stored credentials).
- Never commit `*.tfstate`, `*.tfstate.backup`, or `.terraform/` (already in `.gitignore`).
- ACR name must be globally unique and alphanumeric only.
- App Service name must be globally unique.

### Infrastructure-as-Code Consistency

- **All infrastructure changes must be codified in Terraform.** Manual Azure portal or CLI changes that are not reflected in `infra/` are not permitted.
- If a change cannot be expressed in Terraform (e.g., one-time manual setup, Azure portal-only configuration, external service registration), it **must** be documented in `docs/infra-manual-changes.md` with the date, author, reason, and exact steps to reproduce.
- Before merging any infra PR, verify `terraform plan` shows no unexpected drift between the code and the actual environment.

### Commands

```bash
cd infra
terraform init          # Initialize providers
terraform fmt -check    # Check formatting
terraform validate      # Validate configuration
terraform plan          # Preview changes
terraform apply         # Apply changes
```

---

## cicd-workflows

### Scope

Files under `.github/workflows/`, `app/Dockerfile`, `app/Dockerfile.appservice`.

### Workflows

#### CI (`ci.yml`)
- **Triggers**: Push to `main`/`develop`, PRs, manual dispatch.
- **Steps**: Checkout → Python 3.12 → uv → `uv sync --frozen --all-extras` → `ruff check .` → `pytest tests/ -v`.
- **Working directory**: `./app`

#### Deploy (`deploy.yml`)
- **Triggers**: Push to `main`, manual dispatch.
- **Authentication**: OIDC federated credentials (Azure Login v2).
- **Build job**: Docker multi-stage build via `app/Dockerfile.appservice`, push to ACR with tags `{sha}` + `latest`, GHA cache enabled.
- **Deploy job**: Update App Service container image, inject secrets as app settings.
- **Required secrets**: `ACR_NAME`, `APP_SERVICE_NAME`, `RESOURCE_GROUP`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

### Production Dockerfile (`Dockerfile.appservice`)

Multi-stage build combining frontend + backend into a single container:

1. **Stage 1** (`node:20-alpine`): `npm ci` → `npm run build` → static assets in `dist/`.
2. **Stage 2** (`python:3.12-slim`): System deps (nginx, supervisor) → `uv sync --frozen --no-dev` → backend code.
3. **Stage 3** (final): Copy frontend `dist/` to NGINX html → NGINX (port 8080) reverse-proxies `/api/` to FastAPI (port 5100) → supervisor manages both processes.

### Conventions

- Use OIDC for Azure authentication — never store service principal secrets.
- Tag images with both `github.sha` and `latest`.
- Use GitHub Actions cache (`type=gha`) for Docker layer caching.
- Security headers configured in NGINX: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`.
- Health check endpoint: `/health`.

---

## testing

### Scope

Files under `app/tests/` (backend) and `app/frontend/` test files (frontend).

### Backend Tests (pytest)

| Test File | Coverage |
|-----------|----------|
| `test_agent.py` | Agent initialization, message processing, state tracking |
| `test_agui_server.py` | FastAPI endpoints, thread management, SSE streaming |
| `test_agui_clients.py` | AG-UI client message sending |
| `test_config.py` | LLM configuration loading, provider fallback |
| `test_tools.py` | Tool execution (calculator, weather, timezone) |
| `test_security.py` | SecurityValidator — blocked commands, restricted paths, sensitive data, privilege escalation |
| `test_prompts.py` | PromptManager — YAML loading, key resolution, fallback |
| `test_hooks.py` | SkillRegistry, HarnessHook — violation detection, report properties |

### Conventions

- Use `pytest` with `pytest-asyncio` for async tests.
- Use `httpx` for HTTP testing (FastAPI TestClient pattern).
- Test functions must have type hints and docstrings.
- Create `LLMConfig(api_key="test-key")` for test agent instantiation.
- Assert on agent state attributes (`message_count`, `history`).
- CI runs: `uv run pytest tests/ -v` from `app/` directory.

### Frontend Tests

- **Unit**: Vitest (`npm run test`).
- **E2E**: Playwright (`npm run test:e2e`).

### Commands

```bash
# Backend
cd app && uv run pytest tests/ -v

# Frontend
cd app/frontend && npm run test
cd app/frontend && npm run test:e2e
```

---

## documentation

### Scope

`README.md`, `DEPLOYMENT.md`, `docs/`, `specs/`, `app/README.md`, `app/AGUI_DEMO.md`, `app/IMPLEMENTATION_SUMMARY.md`, `infra/README.md`, `app/frontend/README.md`.

### Structure

| Path | Purpose |
|------|---------|
| `README.md` | Project overview, quick start, architecture |
| `DEPLOYMENT.md` | GitHub Actions workflow documentation |
| `docs/` | Architecture diagrams (`diagram_v1.png`, `diagram_v2.png`), historical docs |
| `specs/` | Feature specifications (spec → plan → tasks per feature) |
| `app/README.md` | Backend setup, API docs, agent integration |
| `app/AGUI_DEMO.md` | AG-UI demo walkthrough |
| `infra/README.md` | Terraform setup guide |
| `app/frontend/README.md` | Frontend setup, component docs |

### Specs Directory Convention

Each feature gets a numbered folder under `specs/`:

```
specs/
├── 001-agent-framework/   # spec.md, plan.md, tasks.md
├── 002-ag-ui-integration/  # spec.md, plan.md, tasks.md, data-model.md, ...
├── 003-copilotkit-frontend/ # spec.md, plan.md, tasks.md, quickstart.md, ...
└── 004-chat-theme-selector/ # spec.md, plan.md, tasks.md
```

### Conventions

- Write documentation in Markdown.
- Keep READMEs up to date when changing related code.
- Feature specs follow the Speckit workflow: specify → plan → tasks → implement.
- Architecture diagrams go in `docs/`.
- Use sequential numbering (`001-`, `002-`, ...) for feature spec folders.

---

## project-governance

### Scope

All application code changes (everything except `infra/`). This harness defines cross-cutting rules that override or supplement domain-specific harnesses.

### Spec-Driven Development (Mandatory)

All application code work — new features, refactors, bug fixes, and enhancements — **must** follow the Spec-driven Development workflow. Infrastructure-only changes (`infra/`) are exempt.

#### Workflow

1. **Specify**: Create `specs/{NNN}-{feature-name}/spec.md` describing the feature or change.
2. **Plan**: Generate `plan.md` with implementation design and architecture decisions.
3. **Tasks**: Break down into `tasks.md` with actionable, dependency-ordered items.
4. **Implement**: Execute tasks, commit incrementally, and verify against the spec.

#### Numbering

- Spec folders use sequential three-digit numbering: `001-`, `002-`, `003-`, ...
- Check the highest existing number in `specs/` and increment by 1.
- Current highest: `004-chat-theme-selector` → next is `005-`.

### Dead Code Elimination

- **Remove unused code**: Delete functions, classes, imports, variables, and files that are no longer referenced or reachable.
- **Remove deprecated building blocks**: If a module, API, dependency, or pattern is deprecated, replace it with the recommended alternative or remove it entirely. Do not leave deprecated code in place.
- **Remove commented-out code**: Commented-out code blocks are not documentation — delete them. Use git history to recover old code if needed.
- Before removing, verify there are no remaining callers or references (use grep/search across the entire codebase).

### Code Minimization

- **No duplicate code**: Extract shared logic into reusable functions, utilities, or base classes. If the same pattern appears in two or more places, refactor it.
- **Keep dependencies lean**: Do not add new dependencies when existing ones or the standard library can accomplish the same task.
- **Prefer composition over inheritance** when reducing complexity.
- **Single Responsibility**: Each module, class, and function should have one clear purpose. Split anything doing too much.
- **Minimize surface area**: Avoid exporting or exposing internals that consumers don't need. Keep public APIs small.
- Always aim for the smallest correct implementation that satisfies the spec.

### Scope

Files under `app/src/`, `app/agui_server.py`, `app/agui_client.py`, `app/agui_client_hybrid.py`, `app/main.py`, and `app/pyproject.toml`.

### Tech Stack

- **Language**: Python ≥3.12
- **Framework**: FastAPI ≥0.115.0, Uvicorn ≥0.32.0
- **AI Framework**: Microsoft Agent Framework (`agent-framework-core`, `agent-framework-ag-ui`, `agent-framework-azure-ai`)
- **Validation**: Pydantic ≥2.0.0
- **Auth**: `azure-identity` (DefaultAzureCredential)
- **Package Manager**: uv (with `uv.lock`)

### Conventions

- Use Python 3.12+ syntax: `str | None` union types, `list[str]` generics.
- All functions must have type hints (`disallow_untyped_defs` enforced by mypy).
- Line length limit: 100 characters (Ruff).
- Ruff lint rules: `E`, `W`, `F`, `I`, `B`, `C4`, `UP`.
- Use Pydantic `BaseModel` for data classes and state management.
- Use `setup_logging()` from `src/logging_utils` with correlation IDs for observability.
- Agent classes inherit from `BaseAgent` (abstract) in `src/agents/base_agent.py`.
- Environment variables loaded via `python-dotenv`; never hardcode secrets.
- FastAPI server uses AG-UI protocol with SSE streaming.

### Commands

```bash
cd app
uv sync --frozen --all-extras   # Install dependencies (including dev)
uv run ruff check .             # Lint
uv run pytest tests/ -v         # Run tests
uv run mypy .                   # Type check
uv run agui_server.py           # Start dev server (port 5100)
```

---

## react-frontend

### Scope

Files under `app/frontend/`.

### Tech Stack

- **Language**: TypeScript 5.3+
- **Framework**: React 18.2, Vite 7.3
- **AI UI**: CopilotKit (`@copilotkit/react-core` ^1.51.2, `@copilotkit/react-ui` ^0.2.0)
- **State Management**: Zustand 5.0
- **Styling**: Tailwind CSS 3.4, PostCSS, Autoprefixer
- **Sanitization**: DOMPurify 3.3
- **Testing**: Vitest (unit), Playwright (E2E)

### Conventions

- Strict TypeScript: `strict: true`, `noUnusedLocals`, `noUnusedParameters`.
- Path alias: `@/*` maps to `./src/*`.
- Target: ES2020, Module: ESNext, JSX: `react-jsx`.
- Components in `src/components/`, hooks in `src/hooks/`, stores in `src/stores/`, types in `src/types/`.
- Use Zustand stores (`chatStore`, `themeStore`) for global state — avoid prop drilling.
- ESLint with zero warnings policy (`--max-warnings 0`).
- Dev server runs on port 8080 with proxy: `/api` → `http://127.0.0.1:5100`.

### Commands

```bash
cd app/frontend
npm ci                  # Install dependencies
npm run dev             # Start Vite dev server (port 8080)
npm run build           # TypeScript check + Vite build
npm run lint            # ESLint (zero warnings)
npm run type-check      # TypeScript only
npm run test            # Vitest unit tests
npm run test:e2e        # Playwright E2E tests
```

---

## terraform-infra

### Scope

Files under `infra/`.

### Tech Stack

- **IaC**: Terraform ≥1.5.0
- **Provider**: azurerm ~3.0
- **Target**: Azure (East US default)

### Architecture

Four active modules orchestrated by `infra/main.tf`:

| Module | Resource | Purpose |
|--------|----------|---------|
| `log-analytics/` | Log Analytics Workspace | Monitoring & log retention (30 days) |
| `acr/` | Azure Container Registry (Standard) | Private container image registry |
| `app-service-plan/` | App Service Plan (P1v3) | Compute tier for hosting |
| `app-service/` | Linux Web App | Container-based app hosting with managed identity |

Dependency chain: Resource Group → Log Analytics, ACR, App Service Plan → App Service.

### Conventions

- Each module has `main.tf`, `variables.tf`, `outputs.tf`.
- Use `variable` blocks with `description`, `type`, and `default`.
- Tag all resources with `var.tags` (Environment, Project, ManagedBy).
- Use System-Assigned Managed Identity for App Service (no stored credentials).
- Never commit `*.tfstate`, `*.tfstate.backup`, or `.terraform/` (already in `.gitignore`).
- ACR name must be globally unique and alphanumeric only.
- App Service name must be globally unique.

### Infrastructure-as-Code Consistency

- **All infrastructure changes must be codified in Terraform.** Manual Azure portal or CLI changes that are not reflected in `infra/` are not permitted.
- If a change cannot be expressed in Terraform (e.g., one-time manual setup, Azure portal-only configuration, external service registration), it **must** be documented in `docs/infra-manual-changes.md` with the date, author, reason, and exact steps to reproduce.
- Before merging any infra PR, verify `terraform plan` shows no unexpected drift between the code and the actual environment.

### Commands

```bash
cd infra
terraform init          # Initialize providers
terraform fmt -check    # Check formatting
terraform validate      # Validate configuration
terraform plan          # Preview changes
terraform apply         # Apply changes
```

---

## cicd-workflows

### Scope

Files under `.github/workflows/`, `app/Dockerfile`, `app/Dockerfile.appservice`.

### Workflows

#### CI (`ci.yml`)
- **Triggers**: Push to `main`/`develop`, PRs, manual dispatch.
- **Steps**: Checkout → Python 3.12 → uv → `uv sync --frozen --all-extras` → `ruff check .` → `pytest tests/ -v`.
- **Working directory**: `./app`

#### Deploy (`deploy.yml`)
- **Triggers**: Push to `main`, manual dispatch.
- **Authentication**: OIDC federated credentials (Azure Login v2).
- **Build job**: Docker multi-stage build via `app/Dockerfile.appservice`, push to ACR with tags `{sha}` + `latest`, GHA cache enabled.
- **Deploy job**: Update App Service container image, inject secrets as app settings.
- **Required secrets**: `ACR_NAME`, `APP_SERVICE_NAME`, `RESOURCE_GROUP`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

### Production Dockerfile (`Dockerfile.appservice`)

Multi-stage build combining frontend + backend into a single container:

1. **Stage 1** (`node:20-alpine`): `npm ci` → `npm run build` → static assets in `dist/`.
2. **Stage 2** (`python:3.12-slim`): System deps (nginx, supervisor) → `uv sync --frozen --no-dev` → backend code.
3. **Stage 3** (final): Copy frontend `dist/` to NGINX html → NGINX (port 8080) reverse-proxies `/api/` to FastAPI (port 5100) → supervisor manages both processes.

### Conventions

- Use OIDC for Azure authentication — never store service principal secrets.
- Tag images with both `github.sha` and `latest`.
- Use GitHub Actions cache (`type=gha`) for Docker layer caching.
- Security headers configured in NGINX: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`.
- Health check endpoint: `/health`.

---

## testing

### Scope

Files under `app/tests/` (backend) and `app/frontend/` test files (frontend).

### Backend Tests (pytest)

| Test File | Coverage |
|-----------|----------|
| `test_agent.py` | Agent initialization, message processing, state tracking |
| `test_agui_server.py` | FastAPI endpoints, thread management, SSE streaming |
| `test_agui_clients.py` | AG-UI client message sending |
| `test_config.py` | LLM configuration loading, provider fallback |
| `test_tools.py` | Tool execution (calculator, weather, timezone) |

### Conventions

- Use `pytest` with `pytest-asyncio` for async tests.
- Use `httpx` for HTTP testing (FastAPI TestClient pattern).
- Test functions must have type hints and docstrings.
- Create `LLMConfig(api_key="test-key")` for test agent instantiation.
- Assert on agent state attributes (`message_count`, `history`).
- CI runs: `uv run pytest tests/ -v` from `app/` directory.

### Frontend Tests

- **Unit**: Vitest (`npm run test`).
- **E2E**: Playwright (`npm run test:e2e`).

### Commands

```bash
# Backend
cd app && uv run pytest tests/ -v

# Frontend
cd app/frontend && npm run test
cd app/frontend && npm run test:e2e
```

---

## documentation

### Scope

`README.md`, `DEPLOYMENT.md`, `docs/`, `specs/`, `app/README.md`, `app/AGUI_DEMO.md`, `app/IMPLEMENTATION_SUMMARY.md`, `infra/README.md`, `app/frontend/README.md`.

### Structure

| Path | Purpose |
|------|---------|
| `README.md` | Project overview, quick start, architecture |
| `DEPLOYMENT.md` | GitHub Actions workflow documentation |
| `docs/` | Architecture diagrams (`diagram_v1.png`, `diagram_v2.png`), historical docs |
| `specs/` | Feature specifications (spec → plan → tasks per feature) |
| `app/README.md` | Backend setup, API docs, agent integration |
| `app/AGUI_DEMO.md` | AG-UI demo walkthrough |
| `infra/README.md` | Terraform setup guide |
| `app/frontend/README.md` | Frontend setup, component docs |

### Specs Directory Convention

Each feature gets a numbered folder under `specs/`:

```
specs/
├── 001-agent-framework/   # spec.md, plan.md, tasks.md
├── 002-ag-ui-integration/  # spec.md, plan.md, tasks.md, data-model.md, ...
├── 003-copilotkit-frontend/ # spec.md, plan.md, tasks.md, quickstart.md, ...
└── 004-chat-theme-selector/ # spec.md, plan.md, tasks.md
```

### Conventions

- Write documentation in Markdown.
- Keep READMEs up to date when changing related code.
- Feature specs follow the Speckit workflow: specify → plan → tasks → implement.
- Architecture diagrams go in `docs/`.
- Use sequential numbering (`001-`, `002-`, ...) for feature spec folders.

---

## project-governance

### Scope

All application code changes (everything except `infra/`). This harness defines cross-cutting rules that override or supplement domain-specific harnesses.

### Spec-Driven Development (Mandatory)

All application code work — new features, refactors, bug fixes, and enhancements — **must** follow the Spec-driven Development workflow. Infrastructure-only changes (`infra/`) are exempt.

#### Workflow

1. **Specify**: Create `specs/{NNN}-{feature-name}/spec.md` describing the feature or change.
2. **Plan**: Generate `plan.md` with implementation design and architecture decisions.
3. **Tasks**: Break down into `tasks.md` with actionable, dependency-ordered items.
4. **Implement**: Execute tasks, commit incrementally, and verify against the spec.

#### Numbering

- Spec folders use sequential three-digit numbering: `001-`, `002-`, `003-`, ...
- Check the highest existing number in `specs/` and increment by 1.
- Current highest: `004-chat-theme-selector` → next is `005-`.

### Dead Code Elimination

- **Remove unused code**: Delete functions, classes, imports, variables, and files that are no longer referenced or reachable.
- **Remove deprecated building blocks**: If a module, API, dependency, or pattern is deprecated, replace it with the recommended alternative or remove it entirely. Do not leave deprecated code in place.
- **Remove commented-out code**: Commented-out code blocks are not documentation — delete them. Use git history to recover old code if needed.
- Before removing, verify there are no remaining callers or references (use grep/search across the entire codebase).

### Code Minimization

- **No duplicate code**: Extract shared logic into reusable functions, utilities, or base classes. If the same pattern appears in two or more places, refactor it.
- **Keep dependencies lean**: Do not add new dependencies when existing ones or the standard library can accomplish the same task.
- **Prefer composition over inheritance** when reducing complexity.
- **Single Responsibility**: Each module, class, and function should have one clear purpose. Split anything doing too much.
- **Minimize surface area**: Avoid exporting or exposing internals that consumers don't need. Keep public APIs small.
- Always aim for the smallest correct implementation that satisfies the spec.
