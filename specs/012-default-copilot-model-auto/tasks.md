# Tasks: Default Copilot Model Auto Routing

**Input**: Design documents from `specs/012-default-copilot-model-auto/`

**Scope**: Focused captured-kwargs tests, exactly three standard Copilot SDK creation paths, targeted validation, and a Foundry BYOK regression assertion. No setup or foundational work is required: the feature adds no dependencies, infrastructure, configuration, or data schema.

## Phase 1: User Story 1 - Automatic routing for regular sessions (Priority: P1)

**Goal**: Ensure standard `SessionPool` resume and fallback creation both explicitly pass the SDK virtual model id `auto`.

**Independent Test**: Independently capture `resume_session` kwargs and fallback `create_session` kwargs and verify each contains `model="auto"`.

### Tests

- [ ] T001 [US1] Add a focused assertion that standard `SessionPool` passes `model="auto"` to `resume_session` in `app/tests/test_session_pool_skills.py`
- [ ] T002 [US1] Add a focused assertion that standard `SessionPool` fallback `create_session` passes `model="auto"` in `app/tests/test_session_pool_skills.py`

### Implementation

- [ ] T003 [US1] Add `"model": "auto"` to the shared standard `SessionPool` session kwargs in `app/src/runtime/state.py`, preserving the existing resume and fallback behavior and all other kwargs

---

## Phase 2: User Story 2 - Automatic routing for agent and fleet sessions (Priority: P1)

**Goal**: Ensure team-agent and fleet/infinite-session SDK creation each explicitly pass `model="auto"`.

**Independent Test**: Capture each workflow's `create_session` kwargs and verify its model is `auto`.

### Tests

- [ ] T004 [P] [US2] Add a focused assertion that team-agent `create_session` receives `model="auto"` in `app/tests/test_teams.py`
- [ ] T005 [P] [US2] Add a focused assertion that fleet/infinite-job `create_session` receives `model="auto"` in `app/tests/test_fleet_infinite.py`

### Implementation

- [ ] T006 [P] [US2] Add `"model": "auto"` to `_create_agent_session` kwargs in `app/src/teams/orchestrator.py`, preserving all other session behavior
- [ ] T007 [P] [US2] Add `"model": "auto"` to `_call_session` kwargs in `app/src/runtime/jobs.py`, preserving all other session behavior

---

## Phase 3: User Story 3 - Preserve Azure AI Foundry BYOK model selection (Priority: P1)

**Goal**: Keep Foundry BYOK sessions on their configured deployment model, without applying the Copilot SDK virtual model id.

**Independent Test**: Verify a `FoundrySessionPool` session passes its configured deployment model unchanged and not `auto`.

- [ ] T008 [US3] Add or retain a regression assertion that `FoundrySessionPool` passes its configured deployment model unchanged and not `"auto"` in `app/tests/test_session_pool_skills.py`; do not change Foundry model-selection code

---

## Final Phase: Targeted Validation

**Purpose**: Validate only the focused session-pool, team, and fleet/infinite-session tests after implementation; do not broaden validation to lint, build, or the full test suite.

- [ ] T009 Run the three focused pytest modules from `app/`: `uv run pytest tests/test_session_pool_skills.py -v`, `uv run pytest tests/test_teams.py -v`, and `uv run pytest tests/test_fleet_infinite.py -v`

## Dependencies & Execution Order

### Phase Dependencies

- **User Story 1**: No setup or foundational prerequisites. Complete T001 and T002 before T003.
- **User Story 2**: Independent of User Story 1. Complete T004 and T005 before their corresponding implementation tasks T006 and T007.
- **User Story 3**: Independent behavior boundary; T008 only asserts the existing Foundry BYOK model selection and must not introduce a model change.
- **Targeted Validation**: T009 follows the focused tests and all three implementations.

### User Story Completion Order

All stories are P1 and can be implemented independently after their focused tests are in place. Suggested delivery is US1 first as the regular-session MVP, followed by US2 and the US3 Foundry regression guard; no story requires another story's code.

### Parallel Opportunities

- T004 and T005 can proceed in parallel because they edit different test modules.
- T006 and T007 can proceed in parallel because they edit different source files and their corresponding tests are independent.
- T001, T002, and T008 all touch `app/tests/test_session_pool_skills.py`; do not perform those edits in parallel.

### Parallel Examples by User Story

- **US1**: No parallel tasks; T001 and T002 edit the same test module, and T003 follows both assertions.
- **US2**: Run T004 and T005 together. After both focused assertions are in place, T006 and T007 can be implemented together.
- **US3**: No parallel tasks; T008 is the single Foundry BYOK regression assertion.

## Implementation Strategy

1. Add the regular-session resume and fallback assertions, then update the shared `SessionPool` kwargs.
2. Add the team and fleet/infinite focused assertions; implement those two independent creation paths in parallel.
3. Keep the Foundry BYOK configured-model regression assertion and make no Foundry model-selection changes.
4. Run only the three targeted pytest commands in T009 after implementation. This task-generation step does not run tests, lint, or builds.

## Task Format Check

All actionable tasks use the required unchecked-checkbox format, sequential task IDs, exact file paths, and story labels for user-story tasks. `[P]` appears only on tasks with independent file scopes.
