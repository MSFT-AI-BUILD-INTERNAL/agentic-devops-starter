# Feature Specification: Default Copilot Model Auto Routing

**Feature Branch**: `copilot/setup-ghcp-cli-default-model-to-auto`

**Created**: 2026-10-28

**Status**: Draft

**Input**: Issue #257: Make all GitHub Copilot SDK sessions explicitly use the virtual model id `auto` for automatic model routing, while leaving Azure AI Foundry BYOK deployment models unchanged.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic routing for regular sessions (Priority: P1)

As a user of a regular GitHub Copilot session, I want the session to use automatic model routing whether it is new, resumed, or created as a fallback, so I get consistent model selection across session lifecycles.

**Why this priority**: Regular sessions are the primary Copilot experience and all their creation paths must behave consistently.

**Independent Test**: Exercise new, resumed, and fallback-created regular sessions and verify each uses the SDK virtual model id `auto`.

**Acceptance Scenarios**:

1. **Given** a new regular GitHub Copilot SDK session, **When** it is created, **Then** it explicitly uses the virtual model id `auto`.
2. **Given** a regular session that is resumed or created through a fallback path, **When** it becomes active, **Then** it explicitly uses `auto`.

---

### User Story 2 - Automatic routing for agent and fleet sessions (Priority: P1)

As a user running a team-agent session or a fleet/infinite-session job, I want each GitHub Copilot SDK session to use automatic model routing, so these workflows follow the same model-selection behavior as regular sessions.

**Why this priority**: These sessions are separate entry points and must not be missed when automatic routing is applied.

**Independent Test**: Start a team-agent session and a fleet/infinite-session job, then verify every GitHub Copilot SDK session they create uses `auto`.

**Acceptance Scenarios**:

1. **Given** a team-agent workflow that creates a GitHub Copilot SDK session, **When** the session starts, **Then** it explicitly uses `auto`.
2. **Given** a fleet/infinite-session job that creates a GitHub Copilot SDK session, **When** the session starts, **Then** it explicitly uses `auto`.

---

### User Story 3 - Preserve Azure AI Foundry BYOK model selection (Priority: P1)

As a user of an Azure AI Foundry BYOK session, I want my configured deployment model to remain in effect, so automatic Copilot routing does not change my deployment choice.

**Why this priority**: BYOK model selection is an explicit user configuration and must remain unaffected by the Copilot default.

**Independent Test**: Start an Azure AI Foundry BYOK session with a configured deployment model and verify that same model remains selected.

**Acceptance Scenarios**:

1. **Given** an Azure AI Foundry BYOK session with a configured deployment model, **When** the session is created, **Then** it continues to use that configured model unchanged and is not overridden with `auto`.

## Edge Cases

- A resumed or fallback-created regular session must use `auto` just like a newly created regular session.
- When a workflow uses Azure AI Foundry BYOK rather than the GitHub Copilot SDK, its configured deployment model takes precedence and remains unchanged.
- Applying automatic routing must not require a user-configurable setting or alter other session behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every regular GitHub Copilot SDK session MUST explicitly use the SDK virtual model id `auto`.
- **FR-002**: The `auto` model requirement MUST apply to new, resumed, and fallback-created regular sessions.
- **FR-003**: Every GitHub Copilot SDK session created for a team-agent workflow MUST explicitly use `auto`.
- **FR-004**: Every GitHub Copilot SDK session created for a fleet/infinite-session job MUST explicitly use `auto`.
- **FR-005**: An Azure AI Foundry BYOK session MUST continue to use its configured deployment model unchanged; it MUST NOT be overridden with `auto`.
- **FR-006**: The automatic model-routing behavior MUST be the default and MUST NOT introduce a configurable setting.
- **FR-007**: Session behavior other than the specified model selection MUST remain unchanged.

### Key Entities

- **Session**: A regular, team-agent, fleet/infinite, or Azure AI Foundry BYOK interaction with a selected model.
- **Model selection**: The SDK virtual model id `auto` for GitHub Copilot SDK sessions, or the configured deployment model for Azure AI Foundry BYOK sessions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of regular GitHub Copilot SDK session paths—including new, resumed, and fallback-created sessions—use automatic model routing.
- **SC-002**: 100% of GitHub Copilot SDK sessions created by team-agent and fleet/infinite-session workflows use automatic model routing.
- **SC-003**: 100% of Azure AI Foundry BYOK sessions retain their configured deployment model.
- **SC-004**: Users receive the automatic-routing default without setting a preference, and existing session behavior outside model selection remains unchanged.

## Assumptions

- The SDK virtual model id `auto` is the intended identifier for automatic model routing.
- The listed regular, team-agent, and fleet/infinite-session paths cover the GitHub Copilot SDK session types in scope.
- Azure AI Foundry BYOK model selection is independently configured and remains authoritative for those sessions.
- No configurable setting is desired; this behavior is a default for the specified GitHub Copilot SDK sessions.
