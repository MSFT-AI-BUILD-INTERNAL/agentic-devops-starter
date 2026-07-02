# AGENTS.md — Agentic DevOps Starter

> Harness configuration for the **GitHub Copilot Coding Agent** working in this repo.
> Not to be confused with the runtime AI agents under `app/src/` — those are application code, not coding-agent configuration.

**Precedence:** `llm-coding-guidance` wins on any conflict with the harnesses below it.

---

## llm-coding-guidance (priority)

General behavioral rules to reduce common LLM coding mistakes. Bias toward caution over speed; use judgment for trivial tasks.

### 1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop and ask.

### 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Senior-engineer test: would they call this overcomplicated? If yes, simplify.

### 3. Surgical Changes
Touch only what you must. Clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, **mention it — don't delete it**.
- Remove imports/variables/functions that *your* changes orphaned. Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

> Overrides any broader "dead code elimination" rule elsewhere in this file.

### 4. Goal-Driven Execution
Define success criteria. Loop until verified.
- "Add validation" → "Write tests for invalid inputs, then make them pass."
- "Fix the bug" → "Write a test that reproduces it, then make it pass."
- "Refactor X" → "Ensure tests pass before and after."

For multi-step tasks, state a brief plan: `Step → verify: check`.

**Working signals:** fewer unnecessary diffs, fewer rewrites, clarifying questions *before* implementation.

---

## python-backend

**Scope:** `app/src/`, `app/agui_server.py`, `app/agui_client*.py`, `app/main.py`, `app/pyproject.toml`.

**Stack:** Python ≥3.12, FastAPI, Uvicorn, Pydantic ≥2, `agent-framework-*`, `azure-identity`. Package manager: `uv`.

**Conventions:**
- Modern Python typing (`str | None`, `list[str]`); all functions typed (`disallow_untyped_defs`).
- Ruff: line length 100, rules `E,W,F,I,B,C4,UP`.
- Use Pydantic `BaseModel` for data/state; `setup_logging()` from `src/logging_utils` with correlation IDs.
- Env via `python-dotenv`; no hardcoded secrets. AG-UI protocol with SSE streaming.

**Commands** (from `app/`):
```bash
uv sync --frozen --all-extras
uv run ruff check .
uv run pytest tests/ -v
uv run mypy .
uv run agui_server.py    # dev server :5100
```

---

## react-frontend

**Scope:** `app/frontend/`.

**Stack:** TypeScript 5.3+, React 18.2, Vite 7.3, CopilotKit, Zustand 5, Tailwind 3.4, DOMPurify. Tests: Vitest + Playwright.

**Conventions:**
- Strict TS (`strict`, `noUnusedLocals`, `noUnusedParameters`); path alias `@/*` → `./src/*`.
- Layout: `src/components/`, `src/hooks/`, `src/stores/`, `src/types/`.
- Use Zustand stores (`chatStore`, `themeStore`) — avoid prop drilling.
- ESLint zero-warnings (`--max-warnings 0`). Dev server :8080, proxy `/api` → `:5100`.

**Commands** (from `app/frontend/`):
```bash
npm ci
npm run dev | build | lint | type-check | test | test:e2e
```

---

## terraform-infra

**Scope:** `infra/`. **Stack:** Terraform ≥1.5, `azurerm ~3.0`, Azure (East US default).

**Modules** (orchestrated by `infra/main.tf`): `log-analytics/`, `acr/` (Standard), `app-service-plan/` (P1v3), `app-service/` (Linux Web App, system-assigned MI). Chain: RG → LA/ACR/Plan → App Service.

**Conventions:**
- Each module: `main.tf`, `variables.tf`, `outputs.tf`. Variables typed and described.
- Tag everything with `var.tags` (Environment, Project, ManagedBy).
- ACR & App Service names must be globally unique; ACR alphanumeric only.
- Never commit `*.tfstate*` or `.terraform/` (already gitignored).
- **All infra changes must be in Terraform.** Manual portal/CLI changes go in `docs/infra-manual-changes.md` with date, author, reason, repro steps.
- Verify `terraform plan` shows no unexpected drift before merging.

**Commands** (from `infra/`): `terraform init | fmt -check | validate | plan | apply`.

---

## cicd-workflows

**Scope:** `.github/workflows/`, `app/Dockerfile*`.

**CI** (`ci.yml`): push to `main`/`develop`, PRs, manual. Runs `uv sync --frozen --all-extras`, `ruff check`, `pytest tests/ -v` from `./app`.

**Deploy** (`deploy.yml`): push to `main`, manual. OIDC auth (Azure Login v2). Build via `app/Dockerfile.appservice`, push to ACR with `{sha}` + `latest` tags (GHA layer cache). Deploy updates App Service container image and injects secrets as app settings. Required secrets: `ACR_NAME`, `APP_SERVICE_NAME`, `RESOURCE_GROUP`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

**Production Dockerfile** (`Dockerfile.appservice`): multi-stage. (1) `node:20-alpine` builds frontend → `dist/`. (2) `python:3.12-slim` installs nginx/supervisor + `uv sync --frozen --no-dev`. (3) NGINX :8080 reverse-proxies `/api/` → FastAPI :5100; supervisor manages both. Health: `/health`. Security headers in NGINX: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`.

**Conventions:** OIDC only (no SP secrets); tag images with both sha and `latest`; use `type=gha` cache.

---

## testing

**Backend** (`app/tests/`): pytest + `pytest-asyncio`, `httpx` for HTTP. Tests typed and docstringed. Run: `cd app && uv run pytest tests/ -v`.

**Frontend** (`app/frontend/`): Vitest unit (`npm run test`), Playwright E2E (`npm run test:e2e`).

---

## project-governance

**Scope:** all application code (everything except `infra/`).

**Spec-Driven Development (mandatory)** for features, refactors, bug fixes, enhancements. Infra-only changes are exempt. Workflow: `specs/{NNN}-{slug}/` with `spec.md` → `plan.md` → `tasks.md` → implement & commit incrementally, verifying against the spec.

**Code minimization:**
- Reuse existing logic before writing new — extract shared patterns when they appear in 2+ places.
- Keep dependencies lean; prefer composition over inheritance; one responsibility per module/class/function.
- Keep public APIs small; smallest correct implementation that satisfies the spec.

> Dead-code rules in this section are subordinate to `llm-coding-guidance § 3` (Surgical Changes). Do not delete pre-existing dead code as part of an unrelated change.

---
