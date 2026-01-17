# Tasks: Web-Based Chatbot Frontend Integration

**Feature Branch**: `003-copilotkit-frontend`  
**Input**: Design documents from `/specs/003-copilotkit-frontend/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Not explicitly requested in the feature specification, so tests are OPTIONAL and not included in this task breakdown.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize frontend project structure and install dependencies

- [X] T001 Create frontend directory structure per plan.md at /home/runner/work/agentic-devops-starter/agentic-devops-starter/frontend
- [X] T002 Initialize Vite + React + TypeScript project with package.json in frontend/
- [X] T003 [P] Install CopilotKit dependencies (@copilotkit/react-core, @copilotkit/react-ui) in frontend/package.json
- [X] T004 [P] Install Zustand state management in frontend/package.json
- [X] T005 [P] Install TailwindCSS and configure in frontend/tailwind.config.js and frontend/postcss.config.js
- [X] T006 [P] Configure TypeScript with strict mode in frontend/tsconfig.json
- [X] T007 [P] Configure Vite with proxy to backend in frontend/vite.config.ts
- [X] T008 [P] Setup ESLint configuration in frontend/.eslintrc.json
- [X] T009 [P] Setup Prettier configuration in frontend/.prettierrc
- [X] T010 Create frontend README.md with setup instructions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core type definitions, utilities, and infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T011 [P] Create TypeScript type definitions for Message in frontend/src/types/message.ts
- [X] T012 [P] Create TypeScript type definitions for Thread/Session in frontend/src/types/session.ts
- [X] T013 [P] Create TypeScript type definitions for AG-UI protocol events in frontend/src/types/agui.ts
- [X] T014 [P] Create logger utility with correlation ID support in frontend/src/utils/logger.ts
- [X] T015 Create Zustand chat store with initial state in frontend/src/stores/chatStore.ts
- [X] T016 [P] Create AG-UI client service for HTTP requests in frontend/src/services/aguiClient.ts
- [X] T017 [P] Create SSE stream handler service in frontend/src/services/streamHandler.ts
- [X] T018 [P] Create session manager service for thread management in frontend/src/services/sessionManager.ts
- [X] T019 Create base App component structure in frontend/src/App.tsx
- [X] T020 Create main entry point with CopilotKit provider in frontend/src/main.tsx
- [X] T021 [P] Add global styles with TailwindCSS imports in frontend/src/index.css
- [X] T022 [P] Create ErrorBoundary component in frontend/src/components/ErrorBoundary.tsx

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Chat Interaction (Priority: P1) 🎯 MVP

**Goal**: Enable users to send messages and receive real-time streaming responses from the backend agent

**Independent Test**: Load the web interface at http://localhost:5173, type "Hello, what can you help me with?", submit, and verify a streamed response appears

### Implementation for User Story 1

- [X] T023 [P] [US1] Create useChat hook for message management in frontend/src/hooks/useChat.ts
- [X] T024 [P] [US1] Create useStreaming hook for real-time token handling in frontend/src/hooks/useStreaming.ts
- [X] T025 [P] [US1] Create useConnection hook for backend status tracking in frontend/src/hooks/useConnection.ts
- [X] T026 [US1] Create MessageBubble component for individual message display in frontend/src/components/MessageBubble.tsx
- [X] T027 [US1] Create MessageList component with auto-scroll in frontend/src/components/MessageList.tsx
- [X] T028 [US1] Create MessageInput component with keyboard submission in frontend/src/components/MessageInput.tsx
- [X] T029 [US1] Create ChatInterface main container component in frontend/src/components/ChatInterface.tsx
- [X] T030 [US1] Integrate ChatInterface into App component in frontend/src/App.tsx
- [X] T031 [US1] Implement SSE connection establishment in streamHandler service
- [X] T032 [US1] Implement token event handler with debounced updates in useStreaming hook
- [X] T033 [US1] Implement message_complete event handler in useStreaming hook
- [X] T034 [US1] Add conversation context preservation in chatStore (thread_id management)
- [X] T035 [US1] Add new conversation/clear functionality in chatStore and ChatInterface
- [X] T036 [US1] Style message bubbles with user/agent visual distinction using TailwindCSS
- [X] T037 [US1] Implement smooth scrolling behavior in MessageList component

**Checkpoint**: At this point, User Story 1 should be fully functional - users can chat with streaming responses and maintain context

---

## Phase 4: User Story 2 - Backend Tool Integration (Priority: P2)

**Goal**: Enable users to leverage backend tools (calculator, weather, timezone) through natural language in the chat interface

**Independent Test**: Ask "What time zone is Tokyo in?" and verify the backend's get_time_zone tool executes and returns timezone information

### Implementation for User Story 2

- [ ] T038 [P] [US2] Create ToolCall type definition in frontend/src/types/agui.ts
- [ ] T039 [P] [US2] Create ToolIndicator component for tool execution status in frontend/src/components/ToolIndicator.tsx
- [ ] T040 [US2] Implement tool_start event handler in streamHandler service
- [ ] T041 [US2] Implement tool_end event handler in streamHandler service
- [ ] T042 [US2] Add tool execution state tracking to chatStore
- [ ] T043 [US2] Integrate ToolIndicator into MessageBubble component for tool usage display
- [ ] T044 [US2] Add tool execution visualization in MessageList (show "Agent is using X tool...")
- [ ] T045 [US2] Handle tool_execution_request events for client-side tools in streamHandler
- [ ] T046 [US2] Implement tool result submission to /tool_result endpoint in aguiClient service
- [ ] T047 [US2] Add tool metadata to message history in chatStore
- [ ] T048 [US2] Style tool indicators with distinct visual appearance using TailwindCSS

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - tool execution is visible and functional

---

## Phase 5: User Story 3 - Conversation History Display (Priority: P3)

**Goal**: Enable users to review full conversation history with clear user/agent distinction and tool usage indicators

**Independent Test**: Have a multi-turn conversation with 10+ messages, scroll up, and verify all messages are visible with proper attribution

### Implementation for User Story 3

- [ ] T049 [P] [US3] Add message metadata to Message type in frontend/src/types/message.ts
- [ ] T050 [P] [US3] Create timestamp formatting utility in frontend/src/utils/formatters.ts
- [ ] T051 [US3] Enhance MessageBubble with timestamp display
- [ ] T052 [US3] Enhance MessageBubble with tool usage history indicators
- [ ] T053 [US3] Add message count tracking to Thread metadata in chatStore
- [ ] T054 [US3] Implement message history persistence in chatStore (50 message limit)
- [ ] T055 [US3] Add thread metadata display in ChatInterface (message count, thread age)
- [ ] T056 [US3] Enhance MessageList with virtual scrolling for long conversations
- [ ] T057 [US3] Add "scroll to bottom" button when user scrolls up in MessageList
- [ ] T058 [US3] Style conversation history with clear visual hierarchy using TailwindCSS

**Checkpoint**: All user stories (1, 2, 3) should now be independently functional with rich history display

---

## Phase 6: User Story 4 - Connection Status and Error Handling (Priority: P4)

**Goal**: Provide clear feedback when backend is unavailable or when errors occur during interaction

**Independent Test**: Stop the backend server, attempt to send a message, and verify a clear connection error is displayed

### Implementation for User Story 4

- [ ] T059 [P] [US4] Create ConnectionStatus component in frontend/src/components/ConnectionStatus.tsx
- [ ] T060 [P] [US4] Create error event type definitions in frontend/src/types/agui.ts
- [ ] T061 [US4] Implement connection status monitoring in useConnection hook
- [ ] T062 [US4] Implement exponential backoff reconnection logic in streamHandler service
- [ ] T063 [US4] Add error event handler in streamHandler service
- [ ] T064 [US4] Add connection error state to chatStore
- [ ] T065 [US4] Integrate ConnectionStatus indicator into ChatInterface header
- [ ] T066 [US4] Add network detection using navigator.onLine in useConnection hook
- [ ] T067 [US4] Implement manual reconnect button in ConnectionStatus component
- [ ] T068 [US4] Add user-friendly error messages with recovery guidance
- [ ] T069 [US4] Disable message input when disconnected or in error state
- [ ] T070 [US4] Add retry functionality for failed messages in MessageBubble
- [ ] T071 [US4] Handle mid-stream connection failures with partial message preservation
- [ ] T072 [US4] Style connection status with color-coded indicators (green/yellow/red) using TailwindCSS

**Checkpoint**: All user stories should now have robust error handling and clear connection feedback

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, refinements, and final validation

- [X] T073 [P] Update root README.md with frontend setup instructions and architecture overview
- [X] T074 [P] Create frontend-specific documentation in frontend/README.md
- [X] T075 [P] Add inline documentation comments to all hooks and services
- [ ] T076 [P] Add accessibility attributes (ARIA labels) to all interactive components
- [ ] T077 Validate quickstart.md instructions by following them step-by-step
- [ ] T078 Test all acceptance scenarios from spec.md User Stories 1-4
- [ ] T079 Performance optimization: verify streaming at 60fps with Chrome DevTools
- [ ] T080 Performance optimization: verify 100+ messages load without lag
- [ ] T081 [P] Security review: ensure XSS prevention with DOMPurify for message content
- [ ] T082 [P] Security review: verify CORS configuration and Content Security Policy
- [ ] T083 Run ESLint and fix all warnings: npm run lint in frontend/
- [ ] T084 Run TypeScript compiler and fix all type errors: npm run type-check in frontend/
- [ ] T085 Code cleanup: remove console.log statements except in logger utility
- [ ] T086 Final validation: test all edge cases from spec.md (long messages, rapid submissions, etc.)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion - can run parallel to US1
- **User Story 3 (Phase 5)**: Depends on User Story 1 (Phase 3) completion (enhances message display)
- **User Story 4 (Phase 6)**: Depends on Foundational (Phase 2) completion - can run parallel to US1/US2
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKS all stories)
    ↓
    ├─→ Phase 3: User Story 1 (P1) 🎯 MVP
    │       ↓
    │   Phase 5: User Story 3 (P3) [enhances US1]
    │
    ├─→ Phase 4: User Story 2 (P2) [parallel to US1]
    │
    └─→ Phase 6: User Story 4 (P4) [parallel to US1/US2]
        ↓
    Phase 7: Polish
```

### Within Each User Story

- Foundation tasks (types, services) before hook implementations
- Hooks before components
- Atomic components before composite components
- Core functionality before styling/polish
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: All tasks marked [P] can run in parallel (T003-T009)

**Phase 2 (Foundational)**: All tasks marked [P] can run in parallel (T011-T014, T016-T018, T021-T022)

**Once Foundational phase completes**:
- User Story 1 (Phase 3) - Core MVP path
- User Story 2 (Phase 4) - Can start in parallel if team has capacity
- User Story 4 (Phase 6) - Can start in parallel if team has capacity
- User Story 3 (Phase 5) - Must wait for US1 core components

**Phase 7 (Polish)**: All tasks marked [P] can run in parallel (T073-T076, T081-T082)

---

## Parallel Example: User Story 1 Core Components

```bash
# Launch foundational type definitions together:
Task T011: "Create TypeScript type definitions for Message in frontend/src/types/message.ts"
Task T012: "Create TypeScript type definitions for Thread/Session in frontend/src/types/session.ts"
Task T013: "Create TypeScript type definitions for AG-UI protocol events in frontend/src/types/agui.ts"

# Launch hooks together (after foundation):
Task T023: "Create useChat hook for message management in frontend/src/hooks/useChat.ts"
Task T024: "Create useStreaming hook for real-time token handling in frontend/src/hooks/useStreaming.ts"
Task T025: "Create useConnection hook for backend status tracking in frontend/src/hooks/useConnection.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only - Basic Chat)

1. Complete Phase 1: Setup → Frontend project scaffolded
2. Complete Phase 2: Foundational → Types, store, services ready
3. Complete Phase 3: User Story 1 → **WORKING CHAT INTERFACE**
4. **STOP and VALIDATE**: 
   - Open http://localhost:5173
   - Send "Hello, what can you help me with?"
   - Verify streaming response appears
   - Test context preservation with follow-up message
   - Test new conversation functionality
5. **MVP is ready for demo/deployment**

**Estimated Effort**: ~40-50 tasks (T001-T037) for a fully functional basic chat interface

### Incremental Delivery Plan

**Release 1 - MVP (User Story 1)**: Basic chat with streaming
- Phases 1, 2, 3
- Users can chat, see responses stream, maintain context
- **Demo-able after task T037**

**Release 2 - Tool Integration (User Story 2)**: Add backend tool support
- Phase 4
- Users can use calculator, weather, timezone tools
- **Demo-able after task T048**

**Release 3 - History Enhancement (User Story 3)**: Rich conversation history
- Phase 5
- Users can review full history with metadata
- **Demo-able after task T058**

**Release 4 - Production Ready (User Story 4 + Polish)**: Error handling + refinements
- Phases 6, 7
- Connection monitoring, error recovery, documentation
- **Production-ready after task T086**

### Parallel Team Strategy

With 3 developers after foundational phase completes:

1. **Team completes Setup + Foundational together** (T001-T022)
2. **Once Foundational is done**:
   - **Developer A**: User Story 1 (T023-T037) → Core chat interface
   - **Developer B**: User Story 2 (T038-T048) → Tool integration (parallel)
   - **Developer C**: User Story 4 (T059-T074) → Error handling (parallel)
3. **After US1 completes**:
   - **Developer A**: User Story 3 (T049-T058) → History enhancements
4. **All together**: Polish phase (T073-T086)

Stories complete and integrate independently without blocking each other.

---

## Validation Checklist

After completing all tasks, verify these success criteria from spec.md:

- [ ] **SC-001**: Simple queries complete within 5 seconds
- [ ] **SC-002**: Streaming shows visible token-by-token updates
- [ ] **SC-003**: Tool calls (timezone lookup) complete within 10 seconds
- [ ] **SC-004**: Context maintained across 10+ message exchanges
- [ ] **SC-005**: 95% of messages result in successful responses
- [ ] **SC-006**: User/agent messages distinguishable within 1 second
- [ ] **SC-007**: Connection status changes display within 2 seconds
- [ ] **SC-008**: Complete system setup takes less than 5 minutes
- [ ] **SC-009**: 100 messages in single thread without degradation
- [ ] **SC-010**: Error messages display within 3 seconds with guidance

---

## Summary

**Total Tasks**: 86 tasks across 7 phases  
**MVP Scope**: Tasks T001-T037 (37 tasks) → User Story 1 only  
**Full Feature**: All 86 tasks → All user stories + polish

**Technology Stack**:
- React 18.2+ with TypeScript 5.3+
- CopilotKit for chat UI components
- Zustand for state management
- Vite for build tooling
- TailwindCSS for styling
- SSE for real-time streaming

**Key Files Created** (73 files total):
- 13 TypeScript type definitions
- 3 services (aguiClient, streamHandler, sessionManager)
- 1 store (chatStore)
- 3 custom hooks (useChat, useStreaming, useConnection)
- 7 React components (ChatInterface, MessageList, MessageInput, MessageBubble, ToolIndicator, ConnectionStatus, ErrorBoundary)
- 9 configuration files (package.json, vite.config.ts, tsconfig.json, etc.)
- 2 documentation files (frontend/README.md, root README updates)
- Plus utilities, styles, and entry points

**Parallel Opportunities Identified**:
- 7 tasks in Setup phase can run in parallel
- 8 tasks in Foundational phase can run in parallel
- 3 user stories (US1, US2, US4) can be developed in parallel after foundation
- 6 tasks in Polish phase can run in parallel

**Independent Test Criteria Met**:
- Each user story has clear independent test criteria
- User Story 1 can be fully tested without US2/3/4
- User Story 2 can be validated independently with tool-based queries
- User Story 3 enhances US1 but doesn't break it
- User Story 4 error handling works across all stories

This task breakdown enables immediate execution with clear dependencies, parallel opportunities, and incremental delivery milestones. Each checkpoint provides a functional, demo-able increment of value.
