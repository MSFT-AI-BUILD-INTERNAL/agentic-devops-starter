# Feature Specification: Refactor Agent Team Pattern Registry to YAML

**Feature Branch**: `009-refactor-patterns-yaml`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "Create a Speckit feature specification for issue #166: refactor the Agent Team Pattern registry from hard-coded Python definitions in app/src/patterns.py to predefined YAML loaded when the server/module is loaded. Keep scope minimal: preserve current API behavior and the five existing patterns, add focused validation/tests, no over-engineering. Do not implement code changes; only create/update the appropriate specs/{NNN}-*/spec.md artifacts following repository conventions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Existing Pattern Access (Priority: P1)

An application user or client opens the Agent Team Pattern experience and expects the same available pattern choices, names, descriptions, roles, flow types, and round limits as before, even though the pattern registry is now sourced from predefined YAML rather than hard-coded definitions.

**Why this priority**: Preserving existing behavior is the core value of the refactor. If users or clients observe different pattern data or broken lookups, the refactor has failed.

**Independent Test**: Can be tested by requesting each existing pattern by its current identifier and comparing the returned pattern data to the current baseline for all five patterns.

**Acceptance Scenarios**:

1. **Given** the system has loaded the predefined pattern registry, **When** a client requests the list of Agent Team Patterns, **Then** the same five existing patterns are available with unchanged identifiers, display names, descriptions, role definitions, flow types, and maximum rounds.
2. **Given** the system has loaded the predefined pattern registry, **When** a client requests any existing pattern by identifier, **Then** the returned pattern is equivalent to the current behavior for that identifier.
3. **Given** a client requests an unknown pattern identifier, **When** the lookup is performed, **Then** the response behavior remains unchanged from the current system behavior.

---

### User Story 2 - Maintain Patterns as Predefined Data (Priority: P2)

A maintainer needs the five predefined Agent Team Patterns to live in a readable data file so future prompt and role text updates can be reviewed as data changes rather than edits to executable registry definitions.

**Why this priority**: This is the requested maintainability improvement and removes the pattern content from hard-coded definitions while keeping scope minimal.

**Independent Test**: Can be tested by reviewing that the predefined registry data contains all five current patterns and that the application loads from that data at server or module load time.

**Acceptance Scenarios**:

1. **Given** the repository contains predefined pattern data, **When** a maintainer reviews the registry, **Then** all five existing patterns are represented in one YAML source with their current fields and role content preserved.
2. **Given** the server or module is loaded, **When** pattern access is first needed, **Then** the predefined YAML-backed registry is already available without requiring a user-triggered import or manual initialization step.

---

### User Story 3 - Reject Invalid Predefined Registry Data (Priority: P3)

A maintainer accidentally introduces malformed or incomplete predefined pattern data. The system should fail clearly during load or validation rather than silently exposing partial or incorrect Agent Team Patterns.

**Why this priority**: Focused validation protects the refactor from regressions without expanding the feature into a general pattern-management system.

**Independent Test**: Can be tested with targeted invalid registry examples that omit required fields, duplicate identifiers, or define invalid role collections.

**Acceptance Scenarios**:

1. **Given** predefined pattern data is missing a required pattern field, **When** the registry is loaded or validated, **Then** validation fails with a clear diagnostic that identifies the invalid pattern.
2. **Given** predefined pattern data contains duplicate pattern identifiers, **When** the registry is loaded or validated, **Then** validation fails instead of choosing one definition silently.
3. **Given** predefined pattern data defines a pattern without any roles, **When** the registry is loaded or validated, **Then** validation fails before the registry is exposed to clients.

---

### Edge Cases

- What happens when the YAML source is missing at load time? The registry load fails clearly and no partial replacement registry is exposed.
- What happens when the YAML source has invalid syntax? The registry load fails clearly with a diagnostic suitable for maintainers.
- What happens when a pattern role is missing required role data such as name, emoji, or prompt text? Validation fails for that pattern.
- What happens when the YAML includes additional pattern entries beyond the current five? They are treated as out of scope for this refactor unless explicitly approved in a later feature.
- What happens when pattern text contains non-English characters or emoji? Existing text and emoji are preserved exactly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load the Agent Team Pattern registry from a predefined YAML source when the server or relevant module is loaded.
- **FR-002**: System MUST preserve the current public pattern-access behavior, including successful lookups and unknown-identifier behavior.
- **FR-003**: System MUST preserve exactly the five existing pattern identifiers: `debate-critic`, `generator-evaluator`, `leadership`, `planner-executor`, and `research-report`.
- **FR-004**: System MUST preserve each existing pattern's name, description, flow type, maximum rounds, role names, role emoji, and role prompt text.
- **FR-005**: System MUST expose the loaded patterns through the existing registry shape expected by current callers.
- **FR-006**: System MUST validate that every predefined pattern has a unique identifier.
- **FR-007**: System MUST validate that every predefined pattern includes all required pattern fields: identifier, name, description, flow type, maximum rounds, and roles.
- **FR-008**: System MUST validate that every predefined role includes all required role fields: name, emoji, and prompt text.
- **FR-009**: System MUST validate that every predefined pattern has at least one role.
- **FR-010**: System MUST fail clearly during load or validation when predefined pattern data is missing, malformed, duplicated, or incomplete.
- **FR-011**: System MUST include focused tests that prove the five existing patterns are preserved after loading from YAML.
- **FR-012**: System MUST include focused tests for registry validation failures covering missing required fields, duplicate identifiers, and empty role collections.
- **FR-013**: System MUST NOT add runtime pattern editing, user-uploaded pattern definitions, remote configuration, database-backed storage, or pattern versioning as part of this refactor.
- **FR-014**: System MUST NOT change user-facing Agent Team Pattern names, ordering, role composition, or prompt content as part of this refactor.

### Key Entities

- **Agent Team Pattern**: A predefined collaboration pattern available to the Agent Team experience; includes identifier, name, description, flow type, maximum rounds, and one or more roles.
- **Agent Role**: A role within an Agent Team Pattern; includes name, emoji, and prompt text used to guide the role's behavior.
- **Predefined Pattern Registry**: The complete set of YAML-backed Agent Team Patterns loaded for use by current pattern lookup behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All five current Agent Team Patterns are available after the refactor with 100% of their existing identifiers and user-visible fields preserved.
- **SC-002**: Existing clients can retrieve known and unknown patterns with no observable behavior change compared with the current system.
- **SC-003**: The predefined registry loads successfully during server or module load in a normal environment without requiring any manual operator action.
- **SC-004**: Focused automated tests cover all five preserved patterns and at least three invalid registry cases.
- **SC-005**: Maintainers can review the complete predefined registry as data in one place without reading executable pattern definitions.
- **SC-006**: No new pattern-management capability is introduced beyond the YAML-backed predefined registry.

## Assumptions

- The feature is limited to issue #166 and does not implement later planning, code changes, or evaluation in this specification step.
- The current behavior in `app/src/patterns.py` is the source of truth for the five existing patterns and their content.
- The predefined YAML source is stored in the repository and packaged with the application so it is available at server or module load time.
- Pattern ordering remains the same as the current registry unless existing callers are already order-independent.
- Validation is focused on preventing broken predefined data and is not intended to become a full schema-management or authoring system.
- No public API contract, endpoint shape, or client behavior changes are intended.
