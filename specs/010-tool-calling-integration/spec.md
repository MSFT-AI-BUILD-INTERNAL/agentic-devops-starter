# Feature Specification: Tool Calling Pattern for Copilot SDK Web Service

**Feature Branch**: `feature/jinsung/tools`

**Created**: 2026-07-01

**Status**: Draft

**Input**: User description: "Design a Tool Calling pattern for the existing web service built on the GitHub Copilot SDK (Python, FastAPI backend under app/src/). Let the assistant/agents invoke multiple code-based tools through the SDK's tool-calling mechanism. Tools are integrated as code (registered in the codebase, including external-API integrations). Start simple: a small number of example tools and a clean registration pattern, not a plugin marketplace. Tool execution MUST be isolated/wrapped so a tool failure never crashes the session or server; errors are contained and surfaced as structured tool results; execution is bounded by a timeout; each invocation is observable (logging/telemetry with correlation IDs); secrets are not leaked; and one tool cannot interfere with another or with core session handling."

## User Scenarios & Testing *(mandatory)*

<!--
  Tool Calling is DISTINCT from Agent Skills (SKILL.md instruction files). Tools are
  executable application code the model can invoke; skills are on-disk instruction files.
  The stories below keep this distinction explicit.
-->

### User Story 1 - Call a Code-Based Tool During a Session (Priority: P1)

A maintainer registers a piece of application code as a callable tool. During an assistant or agent session, the model decides it needs that capability, calls the tool with arguments, and receives the tool's result back into the conversation so it can continue reasoning or respond to the user.

**Why this priority**: Registering and invoking a code-based tool is the core capability the feature exists to deliver. Without it, there is no Tool Calling pattern at all.

**Independent Test**: Register a single deterministic tool, start a session that is prompted to use it, and confirm the tool executes, returns a result to the model, and the model incorporates the result — with no other tools present.

**Acceptance Scenarios**:

1. **Given** a code-based tool is registered with a name, description, and input schema, **When** a session is created, **Then** the tool is made available to the model for that session alongside the existing built-in tools.
2. **Given** the model chooses to call a registered tool with valid arguments, **When** the tool runs, **Then** its output is returned to the session as a structured tool result that the model can consume.
3. **Given** a session that has not been granted the tool, **When** the model attempts to use it, **Then** the tool is not invoked and the session behavior follows the existing permission/allowlist model.

---

### User Story 2 - Guaranteed Isolation and Failure Containment (Priority: P1)

Every tool invocation runs inside an enforced wrapper boundary. Regardless of how a tool behaves — throwing an exception, hanging, leaking a stack trace, or misbehaving — the wrapper contains the effect: the session and server keep running, the model receives a structured failure result, the invocation is bounded by a timeout, and the invocation is logged with a correlation identifier. This boundary is the non-negotiable safety contract between untrusted/failure-prone tool logic and the rest of the application.

**Why this priority**: This is the critical requirement of the feature. A single tool must never be able to crash a session or the server, leak secrets, block indefinitely, or interfere with other tools or core session handling. The value of code-based tools is only acceptable if their blast radius is bounded.

**Independent Test**: Register deliberately misbehaving tools (one that raises, one that never returns, one that receives malformed arguments) and confirm each is contained: the session survives, a structured failure result is delivered within the configured timeout, and a correlated log entry is produced — without any unhandled exception propagating to the session or server.

**Acceptance Scenarios**:

1. **Given** a tool that raises an unexpected exception, **When** it is invoked, **Then** the wrapper contains the exception and returns a structured failure result to the session instead of propagating an unhandled error.
2. **Given** a tool that exceeds its allotted execution time, **When** the timeout is reached, **Then** the invocation is stopped and a structured timeout result is returned to the session.
3. **Given** any tool invocation, **When** it starts and finishes (success or failure), **Then** a log/telemetry record is emitted that includes a correlation identifier tying it to the session and tool call.
4. **Given** a tool that fails, **When** the failure is surfaced, **Then** the failure result does not expose secrets, credentials, or raw internal details beyond what is safe for the model and logs.
5. **Given** one tool fails or hangs, **When** other tools or sessions run concurrently, **Then** they are unaffected and continue to operate normally.

---

### User Story 3 - Example Tools Demonstrate the Pattern (Priority: P2)

A maintainer needs a clear, minimal reference for how to add a tool. The system ships one or two simple example tools — a trivial deterministic tool and an example external-API-integration tool — that demonstrate the registration and isolation pattern end to end without over-engineering.

**Why this priority**: Examples make the pattern adoptable and self-documenting, but they are supporting material rather than the core capability, so they follow the foundational P1 stories.

**Independent Test**: Inspect and exercise the shipped example tools; confirm the deterministic tool returns a predictable result and the external-API example demonstrates the integration and isolation pattern (including behavior when the dependency is unavailable).

**Acceptance Scenarios**:

1. **Given** the shipped deterministic example tool, **When** it is invoked with valid arguments, **Then** it returns a predictable, correct result through the standard tool result shape.
2. **Given** the shipped external-API example tool, **When** it is invoked, **Then** it demonstrates calling an external dependency as code and returns its result — or a structured failure when the dependency is unavailable.
3. **Given** a maintainer following the example, **When** they add a new tool, **Then** the registration and isolation pattern can be reproduced without modifying core session handling.

---

### User Story 4 - Interop with Allowlist and Coexistence with Skills (Priority: P3)

The new code-based tools coexist cleanly with the existing built-in tool allowlist/permission model and with the separate on-disk Agent Skills mechanism, without conflating the two concepts.

**Why this priority**: Correct interoperability protects existing behavior and prevents confusion, but the feature can be demonstrated as an MVP before this is fully generalized, so it is the lowest priority.

**Independent Test**: Configure a session with the existing allowlist plus registered custom tools and loaded skills; confirm allowlist rules govern availability, skills remain instruction files, and tools remain executable code, with each behaving according to its own mechanism.

**Acceptance Scenarios**:

1. **Given** the existing built-in tool allowlist, **When** custom code-based tools are registered, **Then** tool availability continues to respect the established permission/allowlist model.
2. **Given** Agent Skills are loaded for a session, **When** custom tools are also registered, **Then** both are available through their respective mechanisms and neither is treated as the other.
3. **Given** a request to use a tool that is not permitted, **When** it is evaluated, **Then** availability is governed by the permission model rather than by whether the tool code exists.

---

### Edge Cases

- **Tool raises an unexpected exception**: The wrapper contains it and returns a structured failure result; the session and server continue running.
- **Tool exceeds its timeout**: The invocation is bounded and stopped; a structured timeout result is returned.
- **Invalid/malformed arguments**: The invocation is rejected or fails with a structured, descriptive result rather than crashing; the model can retry with corrected input.
- **External dependency (API) unavailable**: The tool surfaces a structured failure (e.g., dependency unavailable) rather than hanging or leaking transport errors.
- **Secret/credential handling**: Secrets used by a tool are sourced from configuration/environment and never appear in tool results, logs, or telemetry.
- **Concurrent invocations across sessions**: Multiple sessions invoking tools at the same time do not interfere with one another or with core session handling.
- **Unknown or unregistered tool name**: A call to a tool that is not registered or not permitted does not crash the session and is handled by the permission/availability model.
- **Duplicate tool names**: Registering two tools with the same name is prevented or clearly disambiguated so callers cannot be silently misrouted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow application code to be registered as a callable tool with, at minimum, a name, a human-readable description, an input schema, and an execution handler.
- **FR-002**: System MUST make registered tools available to assistant and agent sessions so the model can invoke them during a session, both for newly created and resumed sessions.
- **FR-003**: System MUST return each tool's output to the session as a structured tool result the model can consume.
- **FR-004**: System MUST execute every tool inside an enforced isolation/wrapper boundary that separates tool logic from core session and server handling.
- **FR-005**: System MUST contain any tool failure (including unexpected exceptions) within the wrapper and surface it as a structured failure result rather than allowing it to crash the session or server.
- **FR-006**: System MUST bound each tool invocation with a timeout governed by a single global default, with an optional per-tool override, and return a structured timeout result when the limit is exceeded.
- **FR-007**: System MUST reject or safely handle invalid/malformed tool arguments, returning a structured result instead of an unhandled error.
- **FR-008**: System MUST emit a log/telemetry record for each tool invocation (start and completion, including failures) that carries a correlation identifier linking it to the originating session and tool call.
- **FR-009**: System MUST NOT expose secrets, credentials, or unsafe internal details in tool results, logs, or telemetry.
- **FR-010**: System MUST ensure that a failing, slow, or hanging tool does not affect other tool invocations, other sessions, or core session handling.
- **FR-011**: System MUST integrate custom tool availability with the existing built-in tool allowlist/permission model.
- **FR-012**: System MUST keep code-based tools distinct from on-disk Agent Skills so the two mechanisms coexist without being conflated.
- **FR-013**: System MUST ship at least one trivial deterministic example tool and one example external-API-integration tool that demonstrate the registration and isolation pattern.
- **FR-014**: System MUST allow adding a new tool by following the established pattern without modifying core session-creation or session-handling logic.
- **FR-015**: System MUST prevent silent misrouting from duplicate tool names, either by rejecting duplicates or clearly disambiguating them.
- **FR-016**: System MUST include focused tests covering successful invocation, exception containment, timeout bounding, and invalid-argument handling.
- **FR-017**: System MUST NOT support dynamic runtime upload or execution of arbitrary user-provided tool code.
- **FR-018**: System MUST NOT introduce a plugin marketplace, per-tenant sandboxing infrastructure beyond the in-process wrapper, or persistent tool registries as part of this initial version.
- **FR-019**: System SHOULD avoid frontend changes; any user-facing change MUST be limited to what is strictly necessary (ideally none) for this backend-focused feature.

### Key Entities *(include if feature involves data)*

- **Tool**: A unit of application code the model can call during a session. Conceptually has a unique name, a human-readable description, an input schema describing its arguments, and an execution handler. Distinct from an Agent Skill.
- **Tool Invocation**: A single request from the model to run a tool, associated with a session identifier, a tool-call identifier, the tool name, and the supplied arguments.
- **Tool Result**: The structured outcome of an invocation returned to the session, including a result usable by the model, an outcome classification (e.g., success, failure, rejected, timeout), optional error information, and optional telemetry — all free of secrets.
- **Isolation Wrapper**: The enforced boundary that runs every tool invocation, providing failure containment, timeout bounding, structured result production, correlated observability, and secret protection.
- **Tool Registry / Registration Surface**: The mechanism by which code-based tools are registered and supplied to sessions, interoperating with the existing built-in tool allowlist/permission model.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A registered code-based tool can be invoked by the model during a session and its result is incorporated into the session, demonstrated end to end for at least one tool.
- **SC-002**: A tool that raises an exception never terminates the session or server; the session receives a structured failure result in 100% of tested failure cases.
- **SC-003**: A tool that exceeds its timeout is stopped and returns a structured timeout result within the configured time bound in 100% of tested timeout cases.
- **SC-004**: Every tool invocation produces a correlated log/telemetry record identifying the session and tool call, for 100% of invocations in tests.
- **SC-005**: No tool result, log, or telemetry record produced in tests contains secrets or credentials.
- **SC-006**: Concurrent tool invocations across multiple sessions complete independently, with a failing tool in one session not affecting others in tests.
- **SC-007**: At least two example tools (one deterministic, one external-API integration) are shipped and exercised, including the external dependency's unavailable case.
- **SC-008**: Custom tool availability observably respects the existing allowlist/permission model, and Agent Skills remain functional and distinct in tests.
- **SC-009**: A maintainer can add a new tool by following the example pattern without editing core session-creation or session-handling logic.

## Assumptions

- The underlying Copilot SDK natively supports custom code tools (tool definition, invocation payload, and structured tool result), so this feature standardizes a registration-and-isolation pattern rather than building a tool protocol from scratch.
- Sessions are created and resumed through the existing shared client used by the runtime and orchestrator; custom tools are supplied to sessions through the SDK's session-creation mechanism.
- The isolation wrapper is an in-process boundary; stronger process- or container-level sandboxing is explicitly out of scope for this initial version.
- Tool secrets are provided via existing configuration/environment mechanisms and are never hardcoded.
- Tool execution timeout uses a single global default with an optional per-tool override; a per-tool value, when set, takes precedence over the global default.
- The existing built-in tool allowlist continues to be the authority for which tools a session may use; custom tools interoperate with, and do not bypass, it.
- Agent Skills (on-disk instruction files) remain a separate mechanism and are not replaced or modified by this feature.
- Scope is an initial minimal foundation (simplicity first, surgical changes); a small number of example tools is sufficient to demonstrate the pattern.
- No frontend changes are expected; the feature is backend-focused.
