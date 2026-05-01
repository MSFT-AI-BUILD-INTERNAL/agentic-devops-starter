# Feature Specification: Multi-Turn Conversation

**Feature ID**: 005-multi-turn-conversation
**Date**: 2026-05-01
**Status**: Implementation

## Overview

Enable multi-turn conversation in the chatbot by sending the full prior
conversation history with every chat request, so that the Microsoft
Agent Framework agent (`AgentThread` in the AG-UI default orchestrator)
sees all previous turns when generating each response.

## Background

The backend (`app/agui_server.py`) is already built on the
**Microsoft Agent Framework** (`agent_framework_ag_ui.AgentFrameworkAgent`
wrapping `agent_framework.ChatAgent`). The framework's
`DefaultOrchestrator` rebuilds an `AgentThread` per request from the
`messages` array supplied in the AG-UI run input
(`agent_framework_ag_ui/_orchestrators.py:316,324`). Multi-turn is
therefore enabled simply by sending the full message history from the
client; no server changes are required.

The current frontend (`app/frontend/src/services/aguiClient.ts:71`)
sends only the latest user message:

```ts
messages: [{ role: 'user', content: message }]
```

so the agent has no recollection of earlier turns and the chatbot
behaves as single-turn only.

## User Story

**As a** chatbot user
**I want** the assistant to remember earlier turns within the same thread
**So that** follow-up questions ("what about Tokyo?", "and there?")
resolve against prior context.

### Acceptance Criteria

1. After sending two messages in the same thread, the second request
   to the AG-UI server contains both the prior user turn and the prior
   assistant turn (in order) along with the new user turn.
2. The Microsoft Agent Framework `AgentThread` constructed by the
   default orchestrator therefore receives the full turn history.
3. Server behaviour and public APIs are unchanged; no infra changes.
4. Existing tests pass; new test confirms `aguiClient.sendMessage`
   forwards the messages array verbatim.

## Non-Goals

- Server-side persistence of threads across server restarts.
- Token-budget management / summarisation of long histories.
  (Existing 50-message store cap in `chatStore.addMessage` is
  sufficient for the harness "no over-engineering" rule.)
- Any change to the Azure AI client or model configuration.

## Design

### Frontend
- `aguiClient.sendMessage(messages, threadId, onEvent)` accepts a
  pre-built AG-UI messages array (`{id, role, content}[]`) and forwards
  it as-is in the request body.
- `useChat.sendMessage(content)` builds the array from the existing
  Zustand store messages plus the new user message and calls
  `aguiClient.sendMessage`.

### Backend
- No changes. `agent_framework_ag_ui` already creates the `AgentThread`
  from the full incoming messages list.

## Compatibility

- AG-UI protocol: messages array shape (`id`, `role`, `content`) is the
  standard run-input format consumed by
  `agui_messages_to_agent_framework`
  (`agent_framework_ag_ui/_message_adapters.py:32`).
- Microsoft Agent Framework: `AgentThread` is the framework's first-
  class multi-turn primitive; we use it indirectly via the AG-UI
  orchestrator, satisfying the "use Microsoft Agent Framework as much
  as possible" rule from the issue.
- Backwards-compatible with prior single-message requests; the server
  accepts any non-empty messages array.
