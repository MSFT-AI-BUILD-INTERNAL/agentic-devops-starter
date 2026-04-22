# AGENTS.md — Agentic DevOps Starter

> Harness Engineering configuration for GitHub Copilot agents.
> Each harness defines scope, conventions, and tooling for a specific domain of this project.

---

## ⚠️ Important: Two types of agents in this project

This file configures the **GitHub Copilot Coding Agent** — the AI coding assistant that reads and writes source code in this repository.

Do **not** confuse this with the **AI Agents** that run inside the application under `app/src/` (LLM-based conversational agents built on Microsoft Foundry). Those are application code, not coding agent configuration:

| | GitHub Copilot Coding Agent | AI Agent (app/src/) |
|---|---|---|
| **What it is** | Coding assistant that writes/reviews source code | Conversational LLM agent powered by Microsoft Foundry |
| **Configured by** | This file (`AGENTS.md`) | Application code: `BaseAgent`, `agui_server.py`, etc. |
| **Harness rules apply to** | Copilot when working in this repo | Runtime agent behavior (not this file) |

The harness sections below are rules **for the Copilot Coding Agent** — what it must and must not do when writing, reviewing, or modifying code in this repository. They are **not** runtime documentation for the AI Agents in `app/src/`.

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

---

## code-review-criteria

### Scope

All code that Copilot writes or modifies across the entire repository.

### Purpose

This harness defines the mandatory code review criteria that Copilot **must** apply when generating or modifying any code. These criteria serve as the evaluation baseline for the Generation & Evaluation Pattern described in `code-generation-evaluation`.

### Review Criteria

Copilot **must** evaluate every code change against all five criteria below before finalizing output:

#### 1. Code Stability and Compatibility

- Generated code must not introduce breaking changes to existing public APIs, interfaces, or data contracts.
- New code must be compatible with the declared language versions and dependency versions in the project (Python ≥3.12, Node.js as specified in `package.json`, Terraform ≥1.5.0).
- Avoid language features or library APIs marked as unstable, experimental, or scheduled for removal.
- Side-effects that change persistent state (database writes, file mutations, network calls) must be explicit and intentional — never implicit or accidental.

#### 2. Prevention of Unnecessary Over-Engineering

- Implement only what the current requirement demands. Do not pre-emptively build abstractions, extension points, or configurability that is not yet needed.
- Prefer straightforward, readable code over clever or highly abstract code when both solve the problem equally well.
- A new class, interface, or layer of indirection must justify its existence — if a plain function or inline logic suffices, use it.
- Do not add optional parameters, feature flags, or plugin hooks unless explicitly required by the spec.

#### 3. Removal of Duplicate Code and Refactoring

- Before writing new logic, check whether equivalent logic already exists in the codebase. Reuse it rather than duplicating it.
- If the same pattern appears in two or more places as a result of this change, extract it into a shared function, utility, or base class.
- Remove any dead, unreachable, or commented-out code introduced by — or exposed by — the current change.
- Refactoring that is required to avoid duplication is in scope; refactoring unrelated code is out of scope.

#### 4. Prevention of Incorrect Logic via Fallback and Error Hiding

- Fallback paths (e.g., `except Exception`, default return values, silent `None` checks) must not silently swallow errors or produce misleading results.
- Every fallback must either re-raise, log with full context, or return a clearly typed error value — never an empty string, `None`, or a hardcoded default that masks the real failure.
- Do not convert a hard error into a soft warning merely to keep the application running; if a component is broken, propagate that signal upward.
- Avoid broad `try/except` blocks that catch unrelated exceptions and obscure the root cause.

#### 5. Root-Cause Orientation in All Fixes

- Every bug fix or defensive change must address the underlying root cause, not only the symptom.
- Do not add workarounds, patches, or compensating logic that suppresses a symptom while leaving the root cause in place.
- If the root cause cannot be fixed in the current scope, document it explicitly with a `# TODO(root-cause):` comment, a linked issue reference, and the reason it is deferred — never silently defer.
- Changes that introduce new complexity solely to work around a known defect in an upstream dependency must be accompanied by a comment and an issue tracking the proper fix.

### Enforcement

These criteria are enforced through the Generation & Evaluation Pattern defined in `code-generation-evaluation`. Copilot **must not** mark a code change as complete until it has passed a self-evaluation against all five criteria.

---

## code-generation-evaluation

### Scope

All code written or modified by Copilot across the entire repository.

### Purpose

This harness defines the **Generation & Evaluation Pattern** — a mandatory self-review loop that Copilot must execute for every non-trivial code change. The pattern ensures that generated code is critically assessed against the `code-review-criteria` before it is presented as final output.

### The Pattern

Every code generation task follows three sequential phases:

```
┌────────────────────────────────────────────────────────────────┐
│  Phase 1 — GENERATE                                            │
│  Write the initial implementation based on the requirement.    │
├────────────────────────────────────────────────────────────────┤
│  Phase 2 — EVALUATE                                            │
│  Critically review the generated code against all five         │
│  code-review-criteria. Produce a scored finding per criterion. │
├────────────────────────────────────────────────────────────────┤
│  Phase 3 — REVISE                                              │
│  Apply targeted fixes for every finding raised in Phase 2.     │
│  Repeat Phase 2 → Phase 3 until all criteria pass.             │
└────────────────────────────────────────────────────────────────┘
```

### Phase 1 — Generate

- Produce a complete, working initial implementation.
- Do not self-censor or over-iterate at this stage; the goal is a functionally correct first draft.
- Apply all harness rules (security, prompts, hooks, etc.) from the outset — do not defer them to the evaluation phase.

### Phase 2 — Evaluate

After generating the initial implementation, Copilot **must** perform an internal evaluation by scoring the code against each of the five `code-review-criteria`. For each criterion, assign one of:

| Score | Meaning |
|-------|---------|
| ✅ Pass | No issues found. |
| ⚠️ Warning | A minor issue that should be improved but does not break correctness. |
| ❌ Fail | A material issue that must be fixed before the output is final. |

A code change may only be marked complete when **all five criteria score ✅ Pass** or **⚠️ Warning with documented justification**. Any ❌ Fail must trigger Phase 3.

#### Evaluation checklist (apply in order)

1. **Stability & Compatibility** — Does this code break any existing contract or require a version not available in the project?
2. **Over-Engineering** — Is every abstraction, parameter, and layer of indirection justified by the current requirement?
3. **Duplicate Code** — Is there any logic that already exists in the codebase and should be reused instead of re-implemented?
4. **Fallback & Error Hiding** — Do all error paths propagate or log the failure explicitly? Are there any silent swallows?
5. **Root-Cause Orientation** — Does every fix address the root cause, or does it introduce a workaround that defers the underlying problem?

### Phase 3 — Revise

- For each ❌ Fail finding, apply the minimal targeted fix that resolves the issue.
- Do not refactor unrelated code during revision.
- After revisions, return to Phase 2 and re-evaluate only the criteria that had findings.
- Continue iterating until no ❌ Fail findings remain.

### When to Apply the Full Pattern

Apply all three phases for:
- Any new function, class, or module.
- Any change to business logic, error handling, or data flow.
- Any change that touches security-sensitive code paths.
- Any fix to a reported bug.

For purely mechanical changes (e.g., renaming a variable, updating a comment, reformatting), a lighter evaluation (checklist scan only) is sufficient.

### Output Format

When presenting code changes, Copilot should include a brief evaluation summary when findings were identified and resolved:

```
**Evaluation Summary**
- Stability & Compatibility: ✅ Pass
- Over-Engineering: ✅ Pass
- Duplicate Code: ⚠️ Warning — extracted shared validation into `_validate_input()` helper
- Fallback & Error Hiding: ✅ Pass
- Root-Cause Orientation: ✅ Pass
```

Omit the summary for trivial changes (no findings).
