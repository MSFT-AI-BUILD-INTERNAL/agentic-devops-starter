# Contract: Pattern Registry Public Behavior

This refactor changes the internal source of predefined pattern data only. Existing public Python and HTTP behavior must remain unchanged.

## Python module contract

Module: `app/src/patterns.py`

### `AgentRole`

- Remains a Pydantic model.
- Required fields:
  - `name: str`
  - `emoji: str`
  - `system_prompt: str`

### `Pattern`

- Remains a Pydantic model.
- Required/public fields:
  - `id: str`
  - `name: str`
  - `description: str`
  - `roles: list[AgentRole]`
  - `flow_type: str`
  - `max_rounds: int`

### `PATTERNS`

- Remains available at module import.
- Type/shape remains `dict[str, Pattern]`.
- Contains exactly five keys in the current order:
  1. `debate-critic`
  2. `generator-evaluator`
  3. `leadership`
  4. `planner-executor`
  5. `research-report`

### `get_pattern(pattern_id: str) -> Pattern | None`

- Known ID: returns the corresponding `Pattern`.
- Unknown ID: returns `None`.
- No caller-visible initialization step is required.

## HTTP API contract

### `GET /v1/patterns`

**Behavior**: Returns the available Agent Team Patterns using the existing response shape.

**Response**: `200 OK`

```json
[
  {
    "id": "debate-critic",
    "name": "Debate & Critic",
    "description": "Best-option selection via adversarial argument.",
    "roles": ["Proposer", "Opponent", "Critic", "Synthesizer", "Scribe"]
  }
]
```

The full response must include the same five pattern IDs, names, descriptions, and role-name lists currently exposed by the route.

### `POST /v1/teams/stream`

**Known `pattern_id`**: Existing streaming behavior is unchanged.

**Unknown `pattern_id`**: Existing error behavior is unchanged:

```json
{
  "detail": "Pattern not found"
}
```

Status remains `404`.

## Non-contracts / explicitly out of scope

- No public API for creating, editing, deleting, uploading, reloading, or versioning patterns.
- No remote configuration contract.
- No database schema contract.
- No frontend type or UI contract change.
