# Quickstart: Default Copilot Model Auto Routing

## Scope

Implementation updates the standard Copilot SDK kwargs in:

- `app/src/runtime/state.py` — shared `SessionPool` kwargs for resume and fallback creation.
- `app/src/teams/orchestrator.py` — `_create_agent_session`.
- `app/src/runtime/jobs.py` — `_call_session`.

Regression coverage belongs in the existing tests:

- `app/tests/test_session_pool_skills.py` — independent resume and fallback-create `model == "auto"` assertions, plus a Foundry assertion that the configured deployment model is retained.
- `app/tests/test_teams.py` — team `create_session` kwargs include `model == "auto"`.
- `app/tests/test_fleet_infinite.py` — job `create_session` kwargs include `model == "auto"`.

Do not pass `auto` to `FoundrySessionPool`, add a user setting, or alter unrelated session kwargs.

## Targeted validation

From `app/`, run the three focused test modules after implementation:

```bash
uv run pytest tests/test_session_pool_skills.py -v
uv run pytest tests/test_teams.py -v
uv run pytest tests/test_fleet_infinite.py -v
```

This planning task does not run tests, lint, or builds.
