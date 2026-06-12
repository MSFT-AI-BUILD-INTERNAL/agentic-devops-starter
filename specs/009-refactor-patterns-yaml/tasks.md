# Tasks: Refactor Agent Team Pattern Registry to YAML

**Input**: Design documents from `/specs/009-refactor-patterns-yaml/`

**Tests**: Focused pytest coverage is required for preserving existing patterns and validating broken registry data.

## Phase 1: Setup

- [ ] T001 Add a direct PyYAML dependency for backend YAML loading.
- [ ] T002 Create a packaged backend data directory for predefined pattern YAML.

## Phase 2: Tests First

- [ ] T003 Add focused pattern preservation tests for IDs, order, fields, roles, emoji, and prompts.
- [ ] T004 Add focused loader validation tests for missing fields, duplicate IDs, empty roles, and invalid role data.

## Phase 3: Implementation

- [ ] T005 Move the five existing pattern definitions into a single predefined YAML data file.
- [ ] T006 Refactor `app/src/patterns.py` to load and validate the YAML at module load.
- [ ] T007 Preserve `AgentRole`, `Pattern`, `PATTERNS`, and `get_pattern()` public behavior.
- [ ] T008 Keep `/v1/patterns` and `/v1/teams/stream` endpoint behavior unchanged.

## Phase 4: Validation

- [ ] T009 Run focused pytest coverage for pattern and team behavior.
- [ ] T010 Run backend Ruff and mypy checks and document unrelated baseline failures if any remain.
- [ ] T011 Verify no runtime editing, uploads, remote config, database storage, versioning, or reload behavior was added.
