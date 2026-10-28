# Data Model: Default Copilot Model Auto Routing

This feature changes session-creation configuration only. It adds no persisted data, schema, or public Pydantic model.

## Session

Represents an active or resumed interaction created through one of the existing session-management paths.

| Attribute | Description | Feature rule |
|---|---|---|
| Session path | Existing creation boundary: standard `SessionPool`, team agent, fleet/infinite job, or Foundry BYOK | The first three are in scope for `auto`; Foundry is an explicit exception. |
| Provider | Existing SDK/provider selection for the session | Unchanged. Foundry continues to use its existing BYOK provider. |
| Model selection | Model identifier passed in SDK session kwargs | `auto` for standard Copilot session paths; configured deployment model for Foundry BYOK. |
| Lifecycle operation | Create or resume an SDK session | Both the SessionPool resume attempt and its fallback creation receive the same standard model selection. |

### Relationships and invariants

- A standard `SessionPool` model selection is shared by its resume attempt and fallback `create_session`.
- A team-agent session and a fleet/infinite job session each use their own existing session-creation kwargs and explicitly select `auto`.
- A Foundry BYOK session uses the configured Azure AI Foundry deployment model; it must not be assigned `auto`.
- No transition, persistence, or user-facing configuration is added.
