# Data Model: YAML-Backed Agent Team Pattern Registry

## Entity: Predefined Pattern Registry

**Purpose**: Complete in-repository collection of Agent Team Patterns loaded at module/server load and exposed through the existing `PATTERNS` dictionary.

**Fields**:

- `patterns`: ordered list of Agent Team Pattern records.

**Validation rules**:

- Must be loaded from a repository-packaged YAML source.
- Must contain exactly the current five pattern identifiers for this refactor:
  - `debate-critic`
  - `generator-evaluator`
  - `leadership`
  - `planner-executor`
  - `research-report`
- Identifiers must be unique.
- Ordering must match the current registry order unless a future feature explicitly changes it.
- No partial registry may be exposed when loading or validation fails.

**Relationships**:

- Contains one or more Agent Team Pattern records.
- Produces the existing `dict[str, Pattern]` registry keyed by pattern identifier.

## Entity: Agent Team Pattern

**Purpose**: A predefined collaboration pattern available to the Agent Team experience.

**Fields**:

- `id`: stable pattern identifier string.
- `name`: display name.
- `description`: user-visible summary.
- `flow_type`: orchestration flow type string consumed by existing team logic.
- `max_rounds`: integer maximum round count; current value is `3` for all five patterns.
- `roles`: ordered list of Agent Role records.

**Validation rules**:

- `id`, `name`, `description`, `flow_type`, `max_rounds`, and `roles` are required.
- `id` must be unique within the registry.
- `roles` must contain at least one role.
- All current field values must be preserved exactly from `app/src/patterns.py`, including Korean prompt text and emoji.
- Additional pattern entries are out of scope and should fail validation unless a later feature approves expanding the registry.

**Relationships**:

- Belongs to the Predefined Pattern Registry.
- Contains one or more Agent Role records.
- Is exposed as the existing Pydantic `Pattern` model.

## Entity: Agent Role

**Purpose**: A role within an Agent Team Pattern, including display and prompt data used by orchestration.

**Fields**:

- `name`: role name.
- `emoji`: user-visible emoji.
- `system_prompt`: role prompt text.

**Validation rules**:

- `name`, `emoji`, and `system_prompt` are required.
- Values must be non-empty strings.
- Existing prompt text and emoji must be preserved exactly.
- Role order within each pattern must remain unchanged.

**Relationships**:

- Belongs to exactly one Agent Team Pattern record.
- Is exposed as the existing Pydantic `AgentRole` model.

## State and Load Behavior

```text
Process/module import
└── Read predefined YAML
    ├── Missing file or invalid YAML -> fail clearly, expose no partial replacement registry
    ├── Duplicate IDs or invalid records -> fail clearly, expose no partial replacement registry
    └── Valid registry -> construct dict[str, Pattern] as PATTERNS
```

There are no runtime state transitions for pattern editing, persistence, versioning, or remote refresh in this feature.
