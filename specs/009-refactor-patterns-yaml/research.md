# Research: Refactor Agent Team Pattern Registry to YAML

## Decision: Load predefined YAML once at module/server load

**Rationale**: The current callers import `PATTERNS` and `get_pattern()` from `app/src/patterns.py`, and routes iterate `PATTERNS.values()` for `/v1/patterns`. Loading the YAML during module import preserves the existing registry shape and avoids per-request parsing while satisfying the requirement that the registry is available when the server/module is loaded.

**Alternatives considered**:

- Lazy load on first request: rejected because the spec requires availability at module/server load and because delayed errors would surface during user traffic.
- Load on every request: rejected as unnecessary overhead and more complex failure behavior.
- Runtime reload/watch support: rejected as out of scope because the feature explicitly excludes runtime pattern management.

## Decision: Preserve Pydantic `AgentRole` and `Pattern` as validation boundary

**Rationale**: The existing registry already exposes Pydantic models with typed fields. Keeping those models minimizes public API risk, satisfies the constitution's type-safety requirement, and allows the YAML loader to validate required fields, role collections, and field types before exposing `PATTERNS`.

**Alternatives considered**:

- Replace models with plain dictionaries: rejected because it weakens type safety and changes the registry shape expected by current Python callers.
- Introduce a separate schema framework: rejected as over-engineering for five predefined records.
- Add a general pattern authoring schema/version system: rejected as out of scope.

## Decision: Use one repository-packaged YAML source for the five patterns

**Rationale**: One predefined YAML file makes the complete registry reviewable as data and supports exact preservation checks for the current five patterns. The file should be packaged with the Python app so normal server/module imports can load it without manual setup.

**Alternatives considered**:

- Multiple YAML files, one per pattern: rejected because it adds discovery/ordering complexity for only five predefined patterns.
- Database or remote configuration: rejected by the spec as out of scope.
- Environment-variable-configured path: rejected because it adds operational configuration not needed for a predefined registry.

## Decision: Add PyYAML only if a YAML parser is not already available

**Rationale**: Python has no standard-library YAML parser. PyYAML is a small, common dependency suitable for loading trusted repository-packaged YAML with `safe_load`; GitHub Advisory check found no known vulnerabilities for PyYAML 6.0.2. The implementation should keep parsing simple and avoid advanced YAML features.

**Alternatives considered**:

- Encode the data as JSON or TOML: rejected because the requested feature specifically calls for YAML.
- Implement a custom YAML parser: rejected as unsafe and unnecessary.
- Use ruamel.yaml or strictyaml: rejected as heavier than needed for a small predefined data file.

## Decision: Fail clearly for missing, malformed, duplicated, or incomplete data

**Rationale**: A broken predefined registry is a deploy-time/application-load problem. The loader should fail before exposing a partial replacement registry and should identify the invalid pattern or duplicate identifier where possible.

**Alternatives considered**:

- Skip invalid entries and expose valid entries: rejected because it would violate the exact five-pattern requirement and could hide maintainer mistakes.
- Fall back to embedded Python defaults: rejected because it would preserve hard-coded data and mask YAML regressions.
- Return empty registry on failure: rejected because callers would see misleading runtime behavior.

## Decision: Focus tests on preservation and validation, not broad end-to-end flows

**Rationale**: Existing tests already cover pattern count, lookup, unknown IDs, and API responses. This feature should add or tighten focused tests that compare all five patterns' IDs/order/user-visible fields against the current baseline and exercise validation failures for missing fields, duplicate IDs, and empty roles.

**Alternatives considered**:

- Snapshot every API response from full server flows only: rejected because it is slower and less targeted than loader/model tests.
- Test remote or runtime editing scenarios: rejected as out of scope.
- Large golden-file framework: rejected as unnecessary for five records.
