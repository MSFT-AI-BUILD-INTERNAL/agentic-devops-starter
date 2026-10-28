# Implementation Plan: Default Copilot Model Auto Routing

**Branch**: `copilot/setup-ghcp-cli-default-model-to-auto` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-default-copilot-model-auto/spec.md`

## Summary

Set `model="auto"` in the kwargs used to create standard GitHub Copilot SDK sessions in exactly three code paths: the shared `SessionPool` kwargs (used by both `resume_session` and its fallback `create_session`), `teams.orchestrator._create_agent_session`, and `runtime.jobs._call_session`. Add focused tests for the two regular-session outcomes, team creation, and job creation. Keep `FoundrySessionPool`'s configured deployment model unchanged and cover it with a regression assertion.

## Technical Context

**Language/Version**: Python ≥3.12

**Primary Dependencies**: `github-copilot-sdk`; pytest and pytest-asyncio for tests. No dependency changes.

**Storage**: No storage or schema changes.

**Testing**: pytest + pytest-asyncio; invoke targeted tests from `app/` using `uv run pytest ...`. Tests are planned but are not to be run as part of this planning task.

**Target Platform**: Linux-hosted Python backend.

**Project Type**: Backend web service; application code is under `app/`.

**Performance Goals**: No performance behavior or target changes; model selection is an additional session-creation kwarg.

**Constraints**: Limit implementation to the three standard GitHub Copilot SDK creation paths listed above. Do not apply `auto` to Azure AI Foundry BYOK. Do not introduce a setting or change other session kwargs or behavior.

**Scale/Scope**: Three SDK session-creation paths and focused tests in the existing session-pool, team, and fleet/infinite-session test modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Python-first backend / project structure**: PASS. The change remains in the existing Python backend in `app/src/`; no infrastructure code is involved.
- **Agent-centric architecture**: PASS. The plan uses the existing Copilot SDK session-creation integration and adds only its requested model-selection argument; no orchestration framework or architecture is replaced.
- **Type safety**: PASS. No new dependencies or untyped interfaces are planned; tests and changes follow existing Python conventions.
- **Response quality / observability**: PASS. The change affects only model selection; response handling, logging, and tracing remain unchanged.
- **Test-first development**: PASS for implementation planning. Focused assertions are planned for each in-scope SDK path and for the Foundry boundary. No tests are run during this planning-only task.
- **Code quality gates**: PASS by scope. There are no dependency, lint, or type-check configuration changes. Validation commands are documented for implementation follow-up, not run here.

No constitution violations or exceptions are introduced.

## Project Structure

### Documentation (this feature)

```text
specs/012-default-copilot-model-auto/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
└── quickstart.md
```

No `contracts/` directory is needed: the feature changes no externally exposed API, and the SDK kwargs are internal session-creation configuration. `tasks.md` is not part of this planning deliverable.

### Source Code (repository root)

```text
app/
├── src/
│   ├── runtime/
│   │   ├── state.py          # SessionPool and FoundrySessionPool
│   │   └── jobs.py           # Fleet/infinite-session SDK session creation
│   └── teams/
│       └── orchestrator.py   # Team-agent SDK session creation
└── tests/
    ├── test_session_pool_skills.py
    ├── test_teams.py
    └── test_fleet_infinite.py
```

**Structure Decision**: Use the existing single Python backend layout. The implementation and regression tests fit the current runtime/team modules and their existing test modules; no new application module or public contract is necessary.

## Implementation and Test Design

1. Add `"model": "auto"` to the standard `SessionPool` kwargs in `app/src/runtime/state.py`. Since the same kwargs are passed to `resume_session` and then to fallback `create_session`, independently assert `auto` in each call's captured kwargs.
2. Add `"model": "auto"` to `app/src/teams/orchestrator.py`'s `_create_agent_session` kwargs. Test the captured `create_session` kwargs in `app/tests/test_teams.py`.
3. Add `"model": "auto"` to `app/src/runtime/jobs.py`'s `_call_session` kwargs. Test the captured `create_session` kwargs in `app/tests/test_fleet_infinite.py`.
4. Preserve a Foundry regression assertion in `app/tests/test_session_pool_skills.py`: a `FoundrySessionPool` session continues to pass its configured deployment model (currently `gpt-5.2-codex` in the test fixture), not the Copilot virtual model `auto`.

The tests should remain separate so each session-creation route and the Foundry exclusion is independently guarded. Keep all other kwargs and session behavior unchanged.

## Complexity Tracking

No constitution deviations; no complexity justification is required.
