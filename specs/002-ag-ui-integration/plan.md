# Implementation Plan: AG-UI Integration for Web-Based Agent Interface

**Branch**: `002-ag-ui-integration` | **Date**: 2026-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-ag-ui-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature integrates AG-UI (Agent Framework UI) from the `agent-framework-ag-ui` package to provide a web-based interface for the conversational agent. The implementation adds a FastAPI server with Server-Sent Events (SSE) streaming, supports both server-side and client-side tool execution in a hybrid architecture, and maintains conversation state across multiple exchanges. The solution leverages the existing ConversationalAgent and extends it with AG-UI capabilities while following the constitution requirements for Python ≥3.12, type safety, structured logging, and comprehensive testing.

## Technical Context

**Language/Version**: Python 3.12 (as mandated by constitution)  
**Primary Dependencies**: 
- `agent-framework` (microsoft-agent-framework) - Core agent orchestration
- `agent-framework-ag-ui` - AG-UI integration package for web interface
- `fastapi>=0.115.0` - Web framework for HTTP server
- `uvicorn[standard]>=0.32.0` - ASGI server for FastAPI
- `python-dotenv>=1.0.0` - Environment variable management
- `pydantic>=2.0.0` - Data validation and serialization
- `httpx>=0.27.0` - HTTP client for testing

**Storage**: In-memory conversation state (thread ID to history mapping); no persistent database required for MVP  
**Testing**: pytest with pytest-asyncio for async tests, httpx for HTTP client testing  
**Target Platform**: Linux server (containerized deployment), development on any OS with Python 3.12+  
**Project Type**: Single project with web server capabilities (existing `app/` structure extended)  
**Performance Goals**: 
- First token latency <2 seconds under normal LLM API conditions
- Support 10 concurrent conversation threads without degradation
- Server startup <30 seconds
- Tool execution within configured timeouts (default 30s)

**Constraints**: 
- SSE streaming response time bounded by LLM API latency
- Memory usage scales with concurrent conversations and history depth
- All operations must be async/await compatible for FastAPI

**Scale/Scope**: 
- ~10 new modules/files (server, clients, tools, tests)
- ~1500-2000 lines of new code
- 80%+ test coverage target
- Support for demonstration and development use cases initially

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Python-First Backend**: Using Python 3.12 as mandated  
✅ **Agent-Centric Architecture**: Leveraging microsoft-agent-framework (agent-framework package) and extending with AG-UI  
✅ **Type Safety**: All code includes type hints, Pydantic models for validation, mypy for type checking  
✅ **Response Quality**: Existing ConversationalAgent includes response validation and guardrails  
✅ **Observability**: Structured logging with correlation IDs already implemented in logging_utils.py  
✅ **Project Structure**: All application code in `app/` directory, no IaC in this feature  
✅ **Required Technologies**: Using uv (package manager), Ruff (linting), mypy (type checking)  
✅ **LLM Integration**: Existing LLMConfig supports OpenAI and Azure OpenAI  
✅ **Speckit-Driven Development**: This plan created via Speckit workflow  
✅ **Test-First Development**: Will write comprehensive tests with 80%+ coverage target  
✅ **Code Quality Gates**: Must pass Ruff linting and mypy type checking

**Assessment**: All constitution requirements are satisfied. No deviations or violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-ag-ui-integration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (research decisions)
├── data-model.md        # Phase 1 output (entities and state)
├── quickstart.md        # Phase 1 output (getting started guide)
└── contracts/           # Phase 1 output (API specifications)
    ├── openapi.yaml     # OpenAPI 3.0 specification for FastAPI endpoints
    └── tools.yaml       # Tool function signatures and descriptions
```

### Source Code (repository root)

```text
app/
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py          # Existing
│   │   ├── conversational_agent.py # Existing
│   │   └── tools.py                # Existing (will be updated)
│   ├── config/
│   │   ├── __init__.py
│   │   └── llm_config.py           # Existing
│   ├── agui/                       # NEW: AG-UI integration modules
│   │   ├── __init__.py
│   │   ├── server.py               # FastAPI server with AG-UI endpoint
│   │   ├── clients/
│   │   │   ├── __init__.py
│   │   │   ├── basic_client.py     # Basic AG-UI client with streaming
│   │   │   └── hybrid_client.py    # Hybrid tools client (client+server tools)
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── server_tools.py     # Server-side tool: get_time_zone
│   │       └── client_tools.py     # Client-side tool: get_weather
│   └── logging_utils.py            # Existing
├── tests/
│   ├── __init__.py
│   ├── test_conversational_agent.py # Existing
│   ├── agui/                       # NEW: AG-UI tests
│   │   ├── __init__.py
│   │   ├── test_server.py          # Server endpoint tests
│   │   ├── test_basic_client.py    # Basic client tests
│   │   ├── test_hybrid_client.py   # Hybrid client tests
│   │   ├── test_server_tools.py    # Server tool tests
│   │   ├── test_client_tools.py    # Client tool tests
│   │   └── test_integration.py     # End-to-end integration tests
│   └── conftest.py                 # Pytest fixtures
├── main.py                         # Existing CLI (may be updated for demo)
├── agui_server.py                  # NEW: Server entry point script
├── agui_client.py                  # NEW: Basic client demo script
├── agui_client_hybrid.py           # NEW: Hybrid client demo script
├── pyproject.toml                  # Updated with new dependencies
├── .env.example                    # NEW: Example environment configuration
└── README.md                       # Updated with AG-UI documentation
```

**Structure Decision**: Using "Single project" structure since this is a Python backend application with web server capabilities. All code remains in the `app/` directory following the constitution requirement. The new `src/agui/` module provides clear separation of AG-UI concerns while keeping the existing agent framework code intact. Demo scripts at the root level provide easy entry points for developers.

## Complexity Tracking

> **No violations to track** - All constitution requirements are satisfied without deviations.

---

## Phase 0: Research & Outline

### Research Questions

The following questions need to be answered through research to resolve NEEDS CLARIFICATION items:

1. **AG-UI Package API**: What is the exact API surface of `agent-framework-ag-ui`? 
   - How to initialize AG-UI server with FastAPI?
   - What are the required/optional configuration parameters?
   - How to register tools (server-side vs client-side)?
   - What is the SSE event format for streaming?

2. **FastAPI Integration Patterns**: Best practices for FastAPI with async agents
   - How to structure lazy app initialization for testing?
   - Proper lifespan management for agent instances?
   - Error handling patterns for SSE streams?
   - CORS configuration for web clients?

3. **Streaming Implementation**: Server-Sent Events with FastAPI
   - How to implement SSE endpoint in FastAPI?
   - Message format for streaming tokens vs tool execution events?
   - Client-side SSE consumption patterns?
   - Error handling and reconnection strategies?

4. **Tool Execution Architecture**: Hybrid tools (client + server)
   - How does AG-UI distinguish client vs server tools?
   - Communication protocol for client tool execution?
   - Error propagation from client to server?
   - Timeout and cancellation handling?

5. **Conversation State Management**: Thread-based state
   - Best practices for in-memory thread storage?
   - Thread safety for concurrent requests?
   - History pruning strategies for long conversations?
   - Context window management?

### Research Deliverables

All research findings will be documented in `research.md` with:
- **Decision**: Technology/approach chosen
- **Rationale**: Why this choice was made
- **Alternatives Considered**: Other options evaluated
- **Code Examples**: Minimal examples demonstrating the pattern
- **References**: Links to official documentation

---

## Phase 1: Design & Contracts

### Data Model (`data-model.md`)

Key entities to be documented:

1. **AGUIServerConfig**
   - Fields: host, port, llm_config, server_tools, log_level
   - Validation: Port range, valid host, required API keys
   - Relationships: Contains LLMConfig

2. **ConversationThread**
   - Fields: thread_id (UUID), created_at, updated_at, message_history
   - State transitions: Created → Active → (optionally) Archived
   - Relationships: Contains multiple ChatMessages

3. **ChatMessage**
   - Fields: role (user|assistant|system), content, timestamp, metadata
   - Validation: Non-empty content, valid role enum
   - Relationships: Belongs to ConversationThread

4. **ToolDefinition**
   - Fields: name, description, parameters (JSON Schema), execution_location (server|client)
   - Validation: Valid function name, complete parameter schema
   - Relationships: Used by ServerTool or ClientTool

5. **StreamingEvent**
   - Fields: event_type (token|tool_start|tool_end|error), data, timestamp
   - Variants: TokenEvent, ToolExecutionEvent, ErrorEvent
   - Serialization: SSE-compatible format

6. **ToolExecutionContext**
   - Fields: tool_name, thread_id, correlation_id, parameters, result, execution_time
   - Logging: Structured logs for audit trail

### API Contracts (`contracts/`)

#### `contracts/openapi.yaml`

FastAPI endpoints to be specified:

```yaml
/health:
  GET: Health check endpoint
  Response: {"status": "healthy", "version": "0.1.0"}

/chat:
  POST: Main chat endpoint with SSE streaming
  Request Body: {"message": str, "thread_id": str | None}
  Response: SSE stream of events (text/event-stream)
  Events: token, tool_start, tool_end, message_complete, error

/threads/{thread_id}:
  GET: Retrieve conversation history
  Response: {"thread_id": str, "messages": [...], "created_at": str}
  
/threads:
  GET: List all active threads
  Response: {"threads": [{"thread_id": str, "message_count": int, ...}]}

/docs:
  GET: OpenAPI documentation (auto-generated by FastAPI)
```

#### `contracts/tools.yaml`

Tool function signatures:

```yaml
get_time_zone:
  location: server
  description: "Get the current time zone for a given location"
  parameters:
    city: {type: string, required: true}
  returns: {type: string, description: "Time zone name (e.g., 'America/New_York')"}

get_weather:
  location: client
  description: "Get current weather for a location (simulated)"
  parameters:
    city: {type: string, required: true}
  returns: {type: object, properties: {temp: number, conditions: string}}
```

### Quickstart Guide (`quickstart.md`)

Structure:
1. **Prerequisites**: Python 3.12+, required API keys
2. **Installation**: `uv sync` command
3. **Configuration**: Environment variables setup
4. **Running the Server**: `python app/agui_server.py`
5. **Basic Client Example**: Simple message exchange
6. **Hybrid Client Example**: Using both client and server tools
7. **Testing**: Running the test suite
8. **Troubleshooting**: Common issues and solutions

### Agent Context Update

After generating design artifacts, run:
```bash
.specify/scripts/bash/update-agent-context.sh copilot
```

This will update `.specify/context/copilot.md` with:
- New AG-UI dependencies
- FastAPI patterns used
- SSE streaming conventions
- Tool registration patterns

---
## Phase 2: Task Breakdown (Overview)

**Note**: Detailed tasks will be generated by the `/speckit.tasks` command in Phase 2. This section provides a high-level overview of implementation phases.

### Implementation Phases

#### Phase 2.1: Core Server Implementation
**Priority**: P1 - Foundation for all other work  
**Estimated Effort**: 3-4 hours

Tasks:
1. Implement `src/agui/server.py` with FastAPI app and lazy initialization
2. Add `/health` endpoint with version info
3. Add `/chat` endpoint with SSE streaming (basic text streaming)
4. Implement in-memory thread storage (dict-based)
5. Add correlation ID middleware for request tracing
6. Create `agui_server.py` entry point script
7. Write unit tests for server endpoints

**Acceptance**: Server starts successfully, health check returns 200, basic chat messages stream via SSE

---

#### Phase 2.2: Server-Side Tools
**Priority**: P2 - Required for tool execution demo  
**Estimated Effort**: 2-3 hours

Tasks:
1. Implement `src/agui/tools/server_tools.py` with `get_time_zone` function
2. Add tool registration to server initialization
3. Update `/chat` endpoint to handle tool execution events
4. Add structured logging for tool invocations
5. Implement tool error handling and recovery
6. Write unit tests for server tools
7. Add integration test for tool execution flow

**Acceptance**: Server tool executes when requested, logs show tool invocation with correlation ID, tool results streamed to client

---

#### Phase 2.3: Basic Client Implementation
**Priority**: P1 - Needed to test server  
**Estimated Effort**: 2-3 hours

Tasks:
1. Implement `src/agui/clients/basic_client.py` with SSE consumption
2. Handle streaming events (tokens, tool execution, errors)
3. Implement message sending and response collection
4. Add connection error handling and retries
5. Create `agui_client.py` demo script
6. Write unit tests for client (using mocked server)
7. Write integration tests (client + real server)

**Acceptance**: Client connects to server, sends messages, displays streaming responses, handles disconnections gracefully

---

#### Phase 2.4: Client-Side Tools & Hybrid Architecture
**Priority**: P3 - Demonstrates full hybrid capabilities  
**Estimated Effort**: 3-4 hours

Tasks:
1. Implement `src/agui/tools/client_tools.py` with `get_weather` function
2. Implement `src/agui/clients/hybrid_client.py` extending basic client
3. Add client tool registration and execution logic
4. Implement tool execution request/response protocol
5. Add client-side logging for tool invocations
6. Create `agui_client_hybrid.py` demo script
7. Write unit tests for client tools and hybrid client
8. Add integration test with both client and server tools

**Acceptance**: Hybrid client executes server tools remotely and client tools locally, both types work in same conversation, logs show execution location

---

#### Phase 2.5: Conversation State & Thread Management
**Priority**: P2 - Required for multi-turn conversations  
**Estimated Effort**: 2 hours

Tasks:
1. Implement thread creation and retrieval endpoints
2. Add conversation history management (pruning, context limits)
3. Implement thread isolation (no cross-thread interference)
4. Add thread listing endpoint `/threads`
5. Add thread retrieval endpoint `/threads/{thread_id}`
6. Write tests for concurrent thread access
7. Add tests for history management

**Acceptance**: Multiple concurrent threads maintain separate state, history preserved across requests, thread API returns correct data

---

#### Phase 2.6: Configuration & Environment Management
**Priority**: P2 - Required for deployment flexibility  
**Estimated Effort**: 1-2 hours

Tasks:
1. Create `.env.example` with all required variables
2. Add environment variable validation on server startup
3. Support both OpenAI and Azure OpenAI via env config
4. Add configuration documentation to README
5. Add configuration error messages with clear guidance
6. Write tests for configuration loading and validation

**Acceptance**: Server reads config from environment, validates required fields, fails gracefully with clear messages for missing config

---

#### Phase 2.7: Error Handling & Edge Cases
**Priority**: P2 - Required for production readiness  
**Estimated Effort**: 2-3 hours

Tasks:
1. Add LLM API error handling (rate limits, timeouts, invalid responses)
2. Add SSE connection error handling (client disconnect during streaming)
3. Add tool execution timeout handling
4. Add malformed request validation and error responses
5. Add graceful shutdown handling
6. Write tests for all error scenarios
7. Add error recovery documentation

**Acceptance**: All edge cases handled gracefully, errors logged with context, clients receive user-friendly error messages

---

#### Phase 2.8: Documentation & Examples
**Priority**: P2 - Required for developer adoption  
**Estimated Effort**: 2-3 hours

Tasks:
1. Update `app/README.md` with AG-UI setup and usage
2. Create architecture diagram (ASCII art or Markdown)
3. Add code examples for common use cases
4. Document tool creation guide (server and client)
5. Add troubleshooting guide
6. Add API endpoint documentation (supplement OpenAPI)
7. Create deployment guide (Docker, environment setup)

**Acceptance**: Developers can follow docs and get working AG-UI server in <30 minutes, all examples run successfully

---

#### Phase 2.9: Testing & Quality Assurance
**Priority**: P1 - Required to pass constitution gates  
**Estimated Effort**: 2-3 hours

Tasks:
1. Ensure 80%+ test coverage across all modules
2. Run Ruff linting and fix all issues
3. Run mypy type checking and fix all issues
4. Add performance tests (concurrent threads, long conversations)
5. Add load test for streaming endpoint
6. Review and fix any security issues
7. Final integration test run

**Acceptance**: All tests pass, 80%+ coverage achieved, Ruff and mypy clean, no security vulnerabilities

---

### Dependency Graph

```text
Phase 2.1 (Core Server)
    ├──> Phase 2.2 (Server Tools)
    ├──> Phase 2.3 (Basic Client)
    │       └──> Phase 2.4 (Hybrid Architecture)
    ├──> Phase 2.5 (Thread Management)
    └──> Phase 2.6 (Configuration)

Phase 2.7 (Error Handling) [depends on all above]
Phase 2.8 (Documentation) [depends on all above]
Phase 2.9 (Testing & QA) [final phase, validates everything]
```

**Critical Path**: 2.1 → 2.3 → 2.2 → 2.4 → 2.9

---

## Design Decisions

### Key Technical Decisions

#### 1. Lazy Application Initialization

**Decision**: Use factory pattern for FastAPI app creation

**Rationale**: 
- Enables testing without starting actual server
- Allows different configurations for dev/test/prod
- Separates app creation from server startup

**Implementation**:
```python
def create_app(config: AGUIServerConfig | None = None) -> FastAPI:
    """Factory function to create FastAPI app"""
    # App initialization here
    return app
```

---

#### 2. In-Memory Thread Storage

**Decision**: Use `dict[str, ConversationThread]` with threading.Lock

**Rationale**:
- Simple for MVP and demonstration purposes
- No external dependencies (database) required
- Easy to test and reason about
- Can be replaced with persistent storage later (Redis, PostgreSQL)

**Limitations**:
- State lost on server restart
- Not suitable for multi-process deployment (use Redis for that)
- Memory usage grows with thread count

**Future Enhancement**: Add persistent storage adapter interface

---

#### 3. SSE for Streaming

**Decision**: Use Server-Sent Events (SSE) over WebSockets

**Rationale**:
- Simpler protocol (HTTP-based, one-way)
- Better for unidirectional streaming (server→client)
- Works with standard HTTP infrastructure (proxies, load balancers)
- Native browser support via EventSource API
- FastAPI has built-in SSE support

**Trade-offs**:
- No client→server streaming (not needed for this use case)
- Connection overhead for each request (acceptable for chat)

---

#### 4. Tool Execution Protocol

**Decision**: Server-side tools execute in FastAPI process, client-side tools use request/response pattern

**Rationale**:
- Server tools: Direct function call, fastest execution, full server context access
- Client tools: Agent requests execution via special SSE event, client calls function, sends result back

**Protocol**:
```
Server → Client: {"event": "tool_execution_request", "tool_name": "get_weather", "params": {...}, "execution_id": "uuid"}
Client → Server: POST /tool_result {"execution_id": "uuid", "result": {...}}
Server → Client: {"event": "tool_execution_complete", "execution_id": "uuid"}
```

---

#### 5. Error Handling Strategy

**Decision**: Graceful degradation with detailed logging, user-friendly error messages

**Layers**:
1. **Input Validation**: Pydantic models reject invalid requests at API boundary
2. **LLM Errors**: Retry with exponential backoff, fallback to error message if all retries fail
3. **Tool Errors**: Catch exceptions, log with context, return error to agent, let agent decide how to respond to user
4. **Streaming Errors**: Send error event in SSE stream, close stream gracefully
5. **Server Errors**: Return appropriate HTTP status codes, log with correlation IDs

**User Experience**: Always provide actionable feedback, never expose internal errors

---

#### 6. Logging Architecture

**Decision**: Extend existing `logging_utils.py` with AG-UI-specific logging

**Patterns**:
- Every request gets a correlation ID (from existing implementation)
- Log at entry/exit of major functions
- Log all LLM interactions (per constitution)
- Log tool executions with parameters and results
- Structured logging with JSON metadata for machine parsing

**Example**:
```python
logger.info(
    "Tool execution started",
    extra={
        "correlation_id": correlation_id,
        "tool_name": tool_name,
        "thread_id": thread_id,
        "execution_location": "server"
    }
)
```

---

#### 7. Type Safety & Validation

**Decision**: Pydantic models for all data structures, comprehensive type hints

**Models**:
- Request/Response: `ChatRequest`, `ChatResponse`, `ToolExecutionRequest`
- Configuration: `AGUIServerConfig` extends/wraps `LLMConfig`
- Domain: `ConversationThread`, `ChatMessage`, `ToolDefinition`
- Events: `StreamingEvent` base class with subtypes

**Benefits**:
- Automatic OpenAPI schema generation
- Runtime validation at API boundaries
- IDE autocomplete and error detection
- mypy type checking passes

---

#### 8. Testing Strategy

**Layers**:
1. **Unit Tests**: Test individual functions and classes in isolation
   - Mock external dependencies (LLM API, HTTP clients)
   - Fast execution (<1s per test)
   
2. **Integration Tests**: Test component interactions
   - Real FastAPI TestClient (no network)
   - Real SSE streaming
   - Server + client together
   
3. **End-to-End Tests**: Full workflow tests
   - Start real server process
   - Real client connection
   - Complete conversation flows
   - Tool execution (both types)

**Coverage Target**: 80%+ across all modules

**CI/CD**: All tests must pass before merge

---

## Risk Analysis & Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| AG-UI package API changes | High | Low | Pin exact version in pyproject.toml, monitor changelog |
| LLM API rate limiting | Medium | Medium | Implement exponential backoff, add rate limit detection |
| SSE connection instability | Medium | Medium | Add reconnection logic in client, heartbeat events |
| Memory growth from threads | Medium | High | Implement thread cleanup, max thread limit, history pruning |
| Tool execution timeout | Low | Medium | Configure timeouts per tool, log timeout events |
| Concurrent access issues | High | Low | Use threading.Lock for thread storage, comprehensive concurrency tests |

### Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Missing API keys | High | High | Clear startup validation, example .env file, error messages |
| Port conflicts | Low | Medium | Allow port configuration, document common ports to avoid |
| Long conversation history | Medium | Medium | Implement token counting, truncate old messages |
| Client disconnect mid-stream | Low | High | Server handles gracefully, client has reconnect logic |

---

## Success Metrics

### Functional Metrics

- ✅ Server starts in <30 seconds with valid configuration
- ✅ Health endpoint responds with 200 in <100ms
- ✅ Chat endpoint accepts messages and streams responses
- ✅ First token appears in <2 seconds (under normal LLM latency)
- ✅ Server tools execute and log with correlation IDs
- ✅ Client tools execute locally and communicate results
- ✅ Hybrid client handles both tool types in same conversation
- ✅ Multiple threads maintain separate state (10 concurrent threads tested)
- ✅ Conversation history preserved across messages (50+ messages tested)

### Quality Metrics

- ✅ 80%+ test coverage across all new modules
- ✅ Zero Ruff linting errors
- ✅ Zero mypy type checking errors
- ✅ All tests pass in CI/CD
- ✅ OpenAPI documentation generated and accessible
- ✅ All edge cases handled gracefully (see spec Section: Edge Cases)

### Developer Experience Metrics

- ✅ Developer can install and run server in <30 minutes following docs
- ✅ Example clients run successfully without modification
- ✅ Clear error messages guide configuration issues
- ✅ Documentation covers all common use cases
- ✅ Architecture diagram clarifies component relationships

---

## Future Enhancements (Out of Scope)

The following items are explicitly out of scope for this implementation but documented for future consideration:

1. **Persistent Storage**: Replace in-memory thread storage with Redis or PostgreSQL
2. **Authentication**: Add user authentication and authorization
3. **Multi-Process Support**: Add shared state for horizontal scaling
4. **WebSocket Support**: Alternative to SSE for bidirectional streaming
5. **Conversation Export**: Download conversation history as JSON/Markdown
6. **Tool Marketplace**: Registry of shareable tools
7. **Advanced Prompting**: Prompt templates and customization UI
8. **Analytics Dashboard**: Usage metrics, tool performance, error rates
9. **Rate Limiting**: Per-user rate limits and quotas
10. **Conversation Branching**: Fork conversations at specific points

These enhancements would be addressed in subsequent feature specifications following the Speckit workflow.

---

## Appendix: Key Files Overview

### Core Implementation Files

| File | Purpose | Lines (est.) | Dependencies |
|------|---------|--------------|--------------|
| `src/agui/server.py` | FastAPI server, endpoints, SSE | ~300 | FastAPI, agent-framework-ag-ui |
| `src/agui/clients/basic_client.py` | SSE client, message sending | ~150 | httpx, sseclient |
| `src/agui/clients/hybrid_client.py` | Extends basic with tool execution | ~200 | basic_client |
| `src/agui/tools/server_tools.py` | Server-side tool implementations | ~50 | None |
| `src/agui/tools/client_tools.py` | Client-side tool implementations | ~50 | None |

### Test Files

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `tests/agui/test_server.py` | Server endpoint tests | ~200 |
| `tests/agui/test_basic_client.py` | Basic client tests | ~150 |
| `tests/agui/test_hybrid_client.py` | Hybrid client tests | ~200 |
| `tests/agui/test_server_tools.py` | Server tool tests | ~100 |
| `tests/agui/test_client_tools.py` | Client tool tests | ~100 |
| `tests/agui/test_integration.py` | End-to-end tests | ~250 |

### Documentation Files

| File | Purpose |
|------|---------|
| `specs/002-ag-ui-integration/plan.md` | This file |
| `specs/002-ag-ui-integration/research.md` | Research findings (Phase 0) |
| `specs/002-ag-ui-integration/data-model.md` | Entity definitions (Phase 1) |
| `specs/002-ag-ui-integration/quickstart.md` | Getting started guide (Phase 1) |
| `specs/002-ag-ui-integration/contracts/openapi.yaml` | API specification (Phase 1) |
| `specs/002-ag-ui-integration/contracts/tools.yaml` | Tool signatures (Phase 1) |
| `app/README.md` | Updated main documentation |

---

## Conclusion

This implementation plan provides a comprehensive roadmap for integrating AG-UI into the agentic-devops-starter project. The design follows all constitution requirements, leverages existing infrastructure (ConversationalAgent, logging_utils, LLMConfig), and provides a clear path from research through implementation to deployment.

**Next Steps**:
1. Execute Phase 0: Research (create `research.md`)
2. Execute Phase 1: Design (create `data-model.md`, `quickstart.md`, `contracts/`)
3. Update agent context with new patterns
4. Execute Phase 2: Detailed task breakdown via `/speckit.tasks` command

**Command to proceed with Phase 0**:
```bash
# Research phase (automated by agent)
# Creates specs/002-ag-ui-integration/research.md
```

**Command to proceed with Phase 1**:
```bash
# Design phase (automated by agent)
# Creates data-model.md, quickstart.md, contracts/
```

**Command to proceed with Phase 2**:
```bash
specify tasks specs/002-ag-ui-integration/plan.md
# Creates specs/002-ag-ui-integration/tasks.md
```
