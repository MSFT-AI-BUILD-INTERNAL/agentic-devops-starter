# Tasks: AG-UI Integration for Web-Based Agent Interface

**Feature Branch**: `002-ag-ui-integration`  
**Input**: Design documents from `/specs/002-ag-ui-integration/`  
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md

## Overview

This document provides detailed, actionable implementation tasks for the AG-UI integration feature. Tasks are organized by user story to enable independent implementation and testing of each story.

**Total User Stories**: 5 (P1: 1, P2: 3, P3: 1)  
**Tests**: NOT included (not requested in specification)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for AG-UI integration

- [ ] T001 Update app/pyproject.toml with new dependencies: agent-framework-ag-ui, fastapi>=0.115.0, uvicorn[standard]>=0.32.0
- [ ] T002 [P] Create app/src/agui/__init__.py module directory structure
- [ ] T003 [P] Create app/src/agui/clients/__init__.py directory
- [ ] T004 [P] Create app/src/agui/tools/__init__.py directory
- [ ] T005 [P] Create app/tests/agui/__init__.py test directory
- [ ] T006 Create app/.env.example with all required environment variables (AGUI_HOST, AGUI_PORT, etc.)
- [ ] T007 Install dependencies with uv sync command

**Checkpoint**: Project structure ready for AG-UI modules

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Create app/src/agui/models.py with Pydantic models: AGUIServerConfig, ConversationThread, ChatMessage, StreamingEvent, ChatRequest
- [ ] T009 [P] Create app/src/agui/thread_storage.py with ThreadStorage class for in-memory conversation state management
- [ ] T010 [P] Define MessageRole, EventType, ExecutionLocation enums in app/src/agui/models.py
- [ ] T011 Implement StreamingEvent base class with subclasses (TokenEvent, ToolStartEvent, ToolEndEvent, MessageCompleteEvent, ErrorEvent) in app/src/agui/models.py
- [ ] T012 Add to_sse_format() method to StreamingEvent for SSE serialization in app/src/agui/models.py
- [ ] T013 Implement AGUIServerConfig.from_env() class method for environment variable loading in app/src/agui/models.py
- [ ] T014 Add correlation ID middleware infrastructure in app/src/agui/middleware.py
- [ ] T015 Create app/tests/agui/conftest.py with pytest fixtures for test configuration

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Web-Based Agent Interaction (Priority: P1) 🎯 MVP

**Goal**: Enable web-based interaction with conversational agent through FastAPI server with SSE streaming

**Independent Test**: Start FastAPI server, send HTTP POST to /chat endpoint, verify streaming response arrives via SSE

### Implementation for User Story 1

- [ ] T016 [P] [US1] Implement create_app() factory function in app/src/agui/server.py with FastAPI initialization
- [ ] T017 [P] [US1] Add /health endpoint handler in app/src/agui/server.py returning HealthResponse
- [ ] T018 [US1] Implement /chat POST endpoint in app/src/agui/server.py accepting ChatRequest
- [ ] T019 [US1] Implement generate_sse_events() async generator in app/src/agui/server.py for SSE streaming
- [ ] T020 [US1] Add StreamingResponse wrapper for SSE events with media_type="text/event-stream" in app/src/agui/server.py
- [ ] T021 [US1] Integrate ConversationalAgent with /chat endpoint for message processing in app/src/agui/server.py
- [ ] T022 [US1] Implement thread creation and retrieval logic in /chat endpoint using ThreadStorage in app/src/agui/server.py
- [ ] T023 [US1] Add correlation ID middleware to FastAPI app in app/src/agui/server.py
- [ ] T024 [US1] Add CORS middleware configuration in app/src/agui/server.py
- [ ] T025 [US1] Implement lifespan context manager for startup/shutdown in app/src/agui/server.py
- [ ] T026 [US1] Create app/agui_server.py entry point script that loads config and starts uvicorn
- [ ] T027 [US1] Add structured logging with correlation IDs for all /chat requests in app/src/agui/server.py
- [ ] T028 [US1] Implement error handling for invalid requests (400 responses) in app/src/agui/server.py
- [ ] T029 [US1] Implement error handling for LLM API failures with error events in SSE stream in app/src/agui/server.py
- [ ] T030 [US1] Add /docs endpoint auto-documentation (FastAPI built-in) verification in app/src/agui/server.py

**Checkpoint**: User Story 1 complete - web-based chat interface functional with streaming responses

---

## Phase 4: User Story 4 - Real-Time Streaming Responses (Priority: P2)

**Goal**: Stream agent responses in real-time token-by-token with tool execution updates

**Independent Test**: Send query generating long response, observe progressive text appearance and tool execution events in SSE stream

**Note**: This story builds on US1's streaming foundation, enhancing with token-level granularity

### Implementation for User Story 4

- [ ] T031 [P] [US4] Implement token-level streaming in generate_sse_events() with TokenEvent emission in app/src/agui/server.py
- [ ] T032 [P] [US4] Add tool execution event streaming (ToolStartEvent, ToolEndEvent) in app/src/agui/server.py
- [ ] T033 [US4] Integrate agent.stream_response() async iteration for token streaming in app/src/agui/server.py
- [ ] T034 [US4] Implement MessageCompleteEvent emission at end of stream in app/src/agui/server.py
- [ ] T035 [US4] Add connection interruption detection and graceful stream closure in app/src/agui/server.py
- [ ] T036 [US4] Implement concurrent stream isolation with thread-safe event generation in app/src/agui/server.py
- [ ] T037 [US4] Add SSE heartbeat mechanism to keep connections alive during processing in app/src/agui/server.py
- [ ] T038 [US4] Implement client disconnection detection during streaming in app/src/agui/server.py

**Checkpoint**: Real-time streaming operational with token-level granularity and tool events

---

## Phase 5: User Story 5 - Conversation State Management (Priority: P2)

**Goal**: Maintain conversation history and context across multiple message exchanges

**Independent Test**: Have multi-turn conversation where later messages reference earlier context, verify agent responds appropriately

### Implementation for User Story 5

- [ ] T039 [P] [US5] Implement create_thread() method in app/src/agui/thread_storage.py
- [ ] T040 [P] [US5] Implement get_thread() method in app/src/agui/thread_storage.py
- [ ] T041 [P] [US5] Implement update_thread() method to add messages in app/src/agui/thread_storage.py
- [ ] T042 [P] [US5] Implement list_threads() method in app/src/agui/thread_storage.py
- [ ] T043 [US5] Add threading.Lock for thread-safe concurrent access in app/src/agui/thread_storage.py
- [ ] T044 [US5] Add /threads GET endpoint in app/src/agui/server.py returning list of ThreadSummary
- [ ] T045 [US5] Add /threads/{thread_id} GET endpoint in app/src/agui/server.py returning ConversationThread
- [ ] T046 [US5] Implement conversation history retrieval in /chat endpoint in app/src/agui/server.py
- [ ] T047 [US5] Implement history pruning logic (max_messages_per_thread) in app/src/agui/thread_storage.py
- [ ] T048 [US5] Implement token counting estimation method in app/src/agui/models.py ConversationThread
- [ ] T049 [US5] Implement history truncation based on token limits in app/src/agui/thread_storage.py
- [ ] T050 [US5] Add thread isolation validation to prevent cross-thread interference in app/src/agui/thread_storage.py
- [ ] T051 [US5] Add 404 error handling for non-existent thread_id in /chat endpoint in app/src/agui/server.py

**Checkpoint**: Conversation state management complete - multi-turn conversations maintain context

---

## Phase 6: User Story 2 - Server-Side Tool Execution (Priority: P2)

**Goal**: Enable server-side tools that agent can invoke to extend capabilities

**Independent Test**: Define server-side tool, register with agent, ask question triggering tool execution, verify execution logs and results

### Implementation for User Story 2

- [ ] T052 [P] [US2] Create app/src/agui/tools/server_tools.py module
- [ ] T053 [P] [US2] Implement get_time_zone(city: str) -> str function in app/src/agui/tools/server_tools.py
- [ ] T054 [US2] Add @tool decorator to get_time_zone with description in app/src/agui/tools/server_tools.py
- [ ] T055 [US2] Implement ToolDefinition.from_function() class method in app/src/agui/models.py
- [ ] T056 [US2] Add server_tools parameter to create_app() in app/src/agui/server.py
- [ ] T057 [US2] Implement tool registration with ConversationalAgent in app/src/agui/server.py
- [ ] T058 [US2] Update generate_sse_events() to emit ToolStartEvent when tool execution begins in app/src/agui/server.py
- [ ] T059 [US2] Update generate_sse_events() to emit ToolEndEvent with result when tool completes in app/src/agui/server.py
- [ ] T060 [US2] Add structured logging for tool invocations with correlation IDs in app/src/agui/server.py
- [ ] T061 [US2] Implement tool execution timeout handling (default 30s) in app/src/agui/server.py
- [ ] T062 [US2] Implement tool error handling with ErrorEvent emission in app/src/agui/server.py
- [ ] T063 [US2] Add ToolCall tracking in ChatMessage metadata in app/src/agui/models.py
- [ ] T064 [US2] Update agui_server.py to register get_time_zone tool in app/agui_server.py
- [ ] T065 [US2] Add tool execution timing measurement (execution_time_ms) in app/src/agui/server.py

**Checkpoint**: Server-side tool execution operational - get_time_zone tool works end-to-end

---

## Phase 7: User Story 3 - Client-Side Tool Execution (Priority: P3)

**Goal**: Enable client-side tools that execute in client process for hybrid architecture

**Independent Test**: Create client with client-side tools, initiate conversation, verify client tools execute locally while server tools execute remotely

### Implementation for User Story 3

- [ ] T066 [P] [US3] Create app/src/agui/tools/client_tools.py module
- [ ] T067 [P] [US3] Implement get_weather(city: str) -> dict function in app/src/agui/tools/client_tools.py
- [ ] T068 [P] [US3] Create app/src/agui/clients/basic_client.py with AGUIChatClient class
- [ ] T069 [US3] Implement SSE stream parsing in AGUIChatClient._parse_sse_stream() in app/src/agui/clients/basic_client.py
- [ ] T070 [US3] Implement send_message() method with HTTP POST to /chat in app/src/agui/clients/basic_client.py
- [ ] T071 [US3] Implement stream_chat() async generator for SSE consumption in app/src/agui/clients/basic_client.py
- [ ] T072 [US3] Add connection error handling and retry logic in app/src/agui/clients/basic_client.py
- [ ] T073 [US3] Create app/src/agui/clients/hybrid_client.py extending AGUIChatClient
- [ ] T074 [US3] Add client_tools registration in HybridToolsClient.__init__() in app/src/agui/clients/hybrid_client.py
- [ ] T075 [US3] Implement ToolExecutionRequestEvent handling in app/src/agui/clients/hybrid_client.py
- [ ] T076 [US3] Implement local tool execution when ToolExecutionRequestEvent received in app/src/agui/clients/hybrid_client.py
- [ ] T077 [US3] Implement /tool_result POST to send execution results back to server in app/src/agui/clients/hybrid_client.py
- [ ] T078 [US3] Add /tool_result endpoint handler in app/src/agui/server.py accepting ToolExecutionResult
- [ ] T079 [US3] Implement pending tool execution tracking in server (execution_id mapping) in app/src/agui/server.py
- [ ] T080 [US3] Emit ToolExecutionCompleteEvent when client result received in app/src/agui/server.py
- [ ] T081 [US3] Add client-side logging for tool invocations in app/src/agui/clients/hybrid_client.py
- [ ] T082 [US3] Implement client tool timeout detection (wait for /tool_result) in app/src/agui/server.py
- [ ] T083 [US3] Create app/agui_client.py demo script for basic client (no client tools)
- [ ] T084 [US3] Create app/agui_client_hybrid.py demo script for hybrid client (with get_weather tool)
- [ ] T085 [US3] Add client tool error propagation to server via ToolExecutionResult.error in app/src/agui/clients/hybrid_client.py

**Checkpoint**: Hybrid architecture complete - both server and client tools work in same conversation

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and finalization

- [ ] T086 [P] Update app/README.md with AG-UI setup instructions, architecture diagram, usage examples
- [ ] T087 [P] Validate app/.env.example has all required variables with descriptions
- [ ] T088 [P] Add configuration validation with clear error messages on server startup in app/agui_server.py
- [ ] T089 [P] Add input validation error messages (empty message, invalid thread_id) in app/src/agui/server.py
- [ ] T090 Run Ruff linting on all new code: ruff check app/src/agui app/tests/agui app/agui*.py
- [ ] T091 Run mypy type checking on all new code: mypy app/src/agui app/tests/agui app/agui*.py
- [ ] T092 Fix all Ruff and mypy errors identified in T090 and T091
- [ ] T093 [P] Add graceful shutdown handling in app/src/agui/server.py lifespan
- [ ] T094 [P] Add max_threads limit enforcement in app/src/agui/thread_storage.py
- [ ] T095 Add LLM API rate limit detection and exponential backoff in app/src/agui/server.py
- [ ] T096 Validate quickstart.md instructions by following step-by-step
- [ ] T097 Create architecture diagram (ASCII art) in app/README.md
- [ ] T098 Add troubleshooting section to app/README.md with common issues
- [ ] T099 Add tool creation guide to app/README.md (server and client tools)
- [ ] T100 Final validation: Start server, run basic client, run hybrid client, verify all scenarios work

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS all user stories
    ↓
    ├─→ Phase 3 (US1 - Web Interface) [P1] 🎯 MVP
    │       ↓
    │   Phase 4 (US4 - Streaming) [P2] (enhances US1)
    │
    ├─→ Phase 5 (US5 - State Management) [P2] (can start after Foundational)
    │
    ├─→ Phase 6 (US2 - Server Tools) [P2] (can start after Foundational)
    │
    └─→ Phase 7 (US3 - Client Tools) [P3] (depends on US1 for client communication)
            ↓
Phase 8 (Polish) ← Depends on all desired user stories
```

### Critical Path for MVP (User Story 1 Only)

```
T001-T007 (Setup) → T008-T015 (Foundational) → T016-T030 (US1) → T090-T092 (QA) → T100 (Validation)
```

### User Story Independence

- **US1 (Web Interface)**: No dependencies on other stories - can be MVP
- **US4 (Streaming)**: Builds on US1's foundation
- **US5 (State Management)**: Independent of US1, can proceed in parallel
- **US2 (Server Tools)**: Independent of US1, can proceed in parallel
- **US3 (Client Tools)**: Depends on US1 for client-server communication

### Parallel Opportunities

**Setup Phase** (all can run together):
- T002, T003, T004, T005 (directory creation)
- T001, T006 (file updates)

**Foundational Phase** (can run together):
- T009, T010, T014, T015 (independent modules)

**User Story 1** (can run together):
- T016, T017 (independent endpoint handlers)

**User Story 4** (can run together):
- T031, T032 (independent streaming features)

**User Story 5** (can run together):
- T039, T040, T041, T042 (independent methods)

**User Story 2** (can run together):
- T052, T053 (tool implementation)

**User Story 3** (can run together):
- T066, T067, T068 (independent client/tool modules)

**Polish Phase** (can run together):
- T086, T087, T088, T089 (documentation and validation)
- T090, T091 (linting and type checking)
- T093, T094 (independent improvements)

---

## Implementation Strategy

### MVP First (Recommended)

**Goal**: Deliver functional web-based agent interface as quickly as possible

1. **Phase 1**: Setup (T001-T007) - ~30 minutes
2. **Phase 2**: Foundational (T008-T015) - ~2 hours
3. **Phase 3**: User Story 1 (T016-T030) - ~4 hours
4. **Partial Phase 8**: QA (T090-T092, T100) - ~1 hour

**Total MVP Time**: ~7-8 hours

**Deliverable**: Working web-based agent interface with streaming responses

### Incremental Delivery

After MVP, add features incrementally:

1. **MVP** (US1) → Test → Deploy ✅
2. **+US4** (Streaming enhancement) → Test → Deploy 
3. **+US5** (State management) → Test → Deploy
4. **+US2** (Server tools) → Test → Deploy
5. **+US3** (Client tools) → Test → Deploy
6. **Polish** → Final validation → Production deployment

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With 3 developers after Foundational phase:

- **Developer A**: US1 (T016-T030) + US4 (T031-T038)
- **Developer B**: US5 (T039-T051) + US2 (T052-T065)
- **Developer C**: US3 (T066-T085) + Polish (T086-T100)

Stories complete independently and integrate cleanly.

---

## Task Summary

**Total Tasks**: 100
**Phases**: 8
**User Stories**: 5

### Tasks by Phase

- **Phase 1 (Setup)**: 7 tasks
- **Phase 2 (Foundational)**: 8 tasks
- **Phase 3 (US1)**: 15 tasks
- **Phase 4 (US4)**: 8 tasks
- **Phase 5 (US5)**: 13 tasks
- **Phase 6 (US2)**: 14 tasks
- **Phase 7 (US3)**: 20 tasks
- **Phase 8 (Polish)**: 15 tasks

### Tasks by Priority

- **P1 (MVP - US1)**: 15 implementation tasks
- **P2 (US2, US4, US5)**: 35 implementation tasks
- **P3 (US3)**: 20 implementation tasks
- **Foundational**: 8 tasks (required for all)
- **Setup**: 7 tasks (required for all)
- **Polish**: 15 tasks (cross-cutting)

### Parallelizable Tasks

**Total [P] tasks**: 47 tasks can run in parallel with others in same phase

---

## Validation Checklist

Before considering implementation complete:

- [ ] All Ruff linting errors resolved
- [ ] All mypy type checking errors resolved
- [ ] Server starts successfully with valid configuration
- [ ] Server fails gracefully with clear error messages for invalid configuration
- [ ] /health endpoint returns 200 with correct data
- [ ] /chat endpoint accepts messages and streams responses
- [ ] First token appears within 2 seconds (normal LLM latency)
- [ ] Multi-turn conversations maintain context correctly
- [ ] Server tools (get_time_zone) execute and log with correlation IDs
- [ ] Client tools (get_weather) execute locally in hybrid client
- [ ] Hybrid client handles both tool types in same conversation
- [ ] 10 concurrent threads maintain separate state without interference
- [ ] Conversation history preserved across 50+ messages
- [ ] All demo scripts (agui_server.py, agui_client.py, agui_client_hybrid.py) run successfully
- [ ] OpenAPI documentation accessible at /docs
- [ ] README.md contains complete setup and usage instructions
- [ ] Quickstart.md validation completed successfully
- [ ] All edge cases handled gracefully (LLM errors, timeouts, disconnections)

---

## Notes

- **[P] marker**: Tasks marked with [P] can run in parallel with other [P] tasks in the same phase (different files, no dependencies)
- **[Story] label**: Maps task to specific user story (US1-US5) for traceability
- **File paths**: All tasks include specific file paths for implementation
- **Tests**: Not included per specification requirements (TDD not requested)
- **Independent stories**: Each user story is independently completable and testable
- **MVP scope**: User Story 1 (US1) provides minimal viable product - web-based agent interface
- **Incremental value**: Each subsequent story adds value without breaking previous stories

---

**Tasks Document Complete**: 2026-01-13  
**Ready for Implementation**: Yes  
**Estimated Total Effort**: 25-30 hours (including testing and documentation)  
**MVP Effort**: 7-8 hours (User Story 1 only)
