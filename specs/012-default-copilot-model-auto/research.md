# Research: Default Copilot Model Auto Routing

## Scope and resolved context

The feature specification identifies the SDK virtual model id `auto` as the desired automatic-routing identifier. The requested scope is the standard GitHub Copilot SDK session paths in `SessionPool`, team orchestration, and fleet/infinite jobs. Azure AI Foundry BYOK has a separate session pool and a configured deployment model that must remain authoritative. No unresolved technical-context questions remain.

## Decisions

### Use the SDK model kwarg at each in-scope session-creation boundary

- **Decision**: Pass `model="auto"` in standard Copilot session kwargs in `SessionPool`, `_create_agent_session`, and `_call_session`.
- **Rationale**: These are the specified SDK creation entry points. The shared `SessionPool` kwargs reach both the resume attempt and fallback creation, while team and job paths construct their own kwargs. Applying the model at these boundaries directly covers every listed path without adding user configuration.
- **Alternatives considered**: A configurable model setting would contradict the requirement that this be a fixed default. A broader client-wide default or blanket change to every session path risks overriding Foundry's separately configured deployment model.

### Keep the Foundry BYOK path separate

- **Decision**: Do not add `auto` to `FoundrySessionPool`; retain its configured deployment-model kwarg and test that it remains unchanged.
- **Rationale**: The Foundry session pool uses a distinct provider and obtains its model from `settings.azure_ai_model_deployment_name`. The feature explicitly excludes BYOK sessions from Copilot automatic routing.
- **Alternatives considered**: Sharing or normalizing the model setting across Copilot and Foundry sessions was rejected because it would change the user's configured deployment selection.

### Verify each path with independent captured-kwargs assertions

- **Decision**: Plan independent assertions for SessionPool resume kwargs, fallback create kwargs, team create kwargs, job create kwargs, and the Foundry configured model.
- **Rationale**: Captured SDK kwargs verify the actual input at each distinct integration boundary, including the resumed session where there is no `create_session` call. Independent tests make omissions in one route visible without relying on broad integration behavior.
- **Alternatives considered**: A single shared assertion or a test of only newly created regular sessions would not protect all entry points named by the specification.

### No external contract artifact

- **Decision**: Do not create a `contracts/` artifact.
- **Rationale**: No public HTTP API or externally consumed interface changes. The model value is internal configuration passed to the existing GitHub Copilot SDK.
- **Alternatives considered**: A new public API or configuration contract would be unnecessary and would expand scope.
