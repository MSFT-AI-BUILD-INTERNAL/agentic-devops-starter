# Quickstart: YAML-Backed Pattern Registry Refactor

## Scope

Plan and implement only the minimal refactor from hard-coded Python pattern definitions to predefined YAML loaded at module/server load. Preserve existing public behavior and the current five patterns exactly.

## Implementation checklist for Phase 2 tasks

1. Add focused tests first.
   - Assert `PATTERNS` has exactly the five current IDs in the current order.
   - Assert every current pattern preserves `name`, `description`, `flow_type`, `max_rounds`, role names, role emoji, and role prompt text.
   - Assert `get_pattern("nonexistent") is None`.
   - Assert `/v1/patterns` response shape and unknown `/v1/teams/stream` behavior remain unchanged.
   - Add loader/validation tests for missing required fields, duplicate IDs, and empty role collections.
2. Add one repository-packaged YAML file containing the current five patterns.
3. Add minimal loader/validation code in `app/src/patterns.py` or a small helper under `app/src/`.
4. Construct `PATTERNS: dict[str, Pattern]` once during module import from the YAML data.
5. Keep `AgentRole`, `Pattern`, and `get_pattern()` public behavior unchanged.
6. Avoid runtime reloads, user uploads, remote config, database storage, pattern versioning, or broad framework changes.

## Suggested validation commands

From repository root:

```bash
cd app
uv run pytest tests/test_teams.py
uv run pytest tests/test_patterns.py
uv run ruff check .
uv run mypy .
```

If tests remain consolidated in `test_teams.py`, skip the `test_patterns.py` command.

## Expected result

- All five current patterns are loaded from YAML during module/server load.
- Existing clients observe no public API behavior change.
- Invalid predefined YAML data fails clearly before a partial registry is exposed.
- Focused tests cover preservation and validation failure cases.
