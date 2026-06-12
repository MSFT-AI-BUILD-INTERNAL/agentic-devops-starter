# Implementation Plan: Refactor Agent Team Pattern Registry to YAML

**Branch**: `copilot/refactor-agent-team-pattern-to-yaml` | **Date**: 2026-06-12 | **Spec**: `specs/009-refactor-patterns-yaml/spec.md`

**Input**: Feature specification from `specs/009-refactor-patterns-yaml/spec.md`

## Summary

Refactor the Agent Team Pattern registry so the current five predefined patterns are represented as repository YAML data and loaded during `src.patterns` module/server load instead of being constructed inline in Python. Preserve the existing public API behavior, `PATTERNS` registry shape, `get_pattern()` behavior, pattern ordering, and all current pattern/user-visible fields while adding focused validation and tests for preserved data and invalid predefined registries.

## Technical Context

**Language/Version**: Python 3.12+ backend; TypeScript frontend is a consumer only and requires no behavior change.

**Primary Dependencies**: Existing Pydantic v2 models; add PyYAML `>=6.0.3` only if no YAML loader is already present in the app environment. GitHub Advisory check found no known vulnerabilities for PyYAML 6.0.3.

**Storage**: Repository-packaged YAML file under `app/src/` or `app/src/data/`; no database, remote configuration, runtime edits, or user uploads.

**Testing**: pytest with existing `app/tests/` layout; focused unit/API tests for preserved patterns and validation failures.

**Target Platform**: Linux-hosted Python web service loaded by the existing FastAPI application/module import path.

**Project Type**: Web-service backend with frontend/API consumers; this feature changes backend registry internals only.

**Performance Goals**: Load five predefined patterns once at module/server load with negligible startup impact; no per-request YAML parsing.

**Constraints**: Preserve existing public behavior exactly: same five IDs, same ordering, same `/v1/patterns` response shape, same `get_pattern()` known/unknown behavior, same role composition/prompt text, and no new pattern-management capability.

**Scale/Scope**: Exactly five existing Agent Team Patterns and their current role definitions; validation is limited to predefined registry integrity.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python-First Backend | PASS | Implementation remains in Python 3.12+ under `app/`; YAML is data only. |
| II. Agent-Centric Architecture | PASS | Existing agent orchestration remains unchanged; this refactor only changes predefined pattern loading. |
| III. Type Safety | PASS | Keep Pydantic models as the runtime validation boundary and preserve typed `PATTERNS: dict[str, Pattern]` / `get_pattern()` signatures. |
| IV. Response Quality | PASS | No LLM response-generation change; existing prompts must be preserved exactly. |
| V. Observability | PASS | Clear load/validation errors are required; no new long-running workflow needs additional tracing. |
| VI. Project Structure | PASS | Application data and loader code remain under `app/`; no infra changes. |
| Speckit-Driven Development | PASS | Plan/design artifacts are version-controlled under `specs/009-refactor-patterns-yaml/`. |
| Test-First Development | PASS | Implementation tasks must add focused tests before changing loader behavior. |
| Code Quality Gates | PASS | Future code changes must pass Ruff, mypy, pytest, and dependency scanning. |

No constitution violations or justified complexity exceptions.

## Project Structure

### Documentation (this feature)

```text
specs/009-refactor-patterns-yaml/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── pattern-registry-api.md
└── tasks.md                 # Created later by /speckit.tasks, not by this plan
```

### Source Code (repository root)

```text
app/
├── src/
│   ├── patterns.py          # Keep public models, PATTERNS, and get_pattern(); load from YAML at import
│   ├── routes.py            # Existing /v1/patterns and /v1/teams/stream behavior remains unchanged
│   └── data/                # Planned location for packaged predefined YAML, if selected during implementation
└── tests/
    ├── test_teams.py        # Existing pattern/API behavior coverage
    └── test_patterns.py     # Planned focused loader/validation tests, if split from test_teams.py
```

**Structure Decision**: Use the existing single Python backend structure under `app/`. Keep executable registry access in `app/src/patterns.py`, place predefined YAML data under `app/src/data/` (or an equally packaged `app/src/` subpath), and keep tests in `app/tests/`.

## Phase 0: Research

Completed in `specs/009-refactor-patterns-yaml/research.md`.

## Phase 1: Design & Contracts

Completed artifacts:

- `specs/009-refactor-patterns-yaml/data-model.md`
- `specs/009-refactor-patterns-yaml/contracts/pattern-registry-api.md`
- `specs/009-refactor-patterns-yaml/quickstart.md`

Agent context marker update:

- `SPECKIT` marker reference created in `.github/copilot-instructions.md` for this plan path.

## Post-Design Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python-First Backend | PASS | Design keeps loader/model code in Python under `app/`. |
| II. Agent-Centric Architecture | PASS | No orchestration behavior or agent primitive changes. |
| III. Type Safety | PASS | Data model requires Pydantic validation and typed registry helpers. |
| IV. Response Quality | PASS | Data contract requires exact prompt preservation. |
| V. Observability | PASS | Validation failures must fail clearly at load time. |
| VI. Project Structure | PASS | Planned files remain in `app/`; no infra changes. |
| Speckit-Driven Development | PASS | Design artifacts are complete for Phase 2 task generation. |
| Test-First Development | PASS | Quickstart requires tests first and identifies focused coverage. |
| Code Quality Gates | PASS | Quickstart includes pytest, Ruff, and mypy validation commands. |

No gate failures and no unresolved clarifications remain.

## Complexity Tracking

No constitution violations require complexity tracking.
