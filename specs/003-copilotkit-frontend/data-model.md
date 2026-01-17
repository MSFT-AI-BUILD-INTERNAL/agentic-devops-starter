# Data Model: Web-Based Chatbot Frontend

**Feature Branch**: `003-copilotkit-frontend`  
**Date**: 2025-01-17  
**Status**: Complete

## Overview

This document defines the core data entities, their relationships, validation rules, and state transitions for the web-based chatbot frontend. These models align with the AG-UI protocol specifications and support the functional requirements defined in the feature spec.

---

## Entity Definitions

### 1. Message

Represents a single message in a conversation thread.

#### Fields

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `id` | `string` | Yes | UUID v4 | Unique message identifier |
| `role` | `MessageRole` | Yes | Enum: 'user', 'assistant', 'system', 'tool' | Message sender type |
| `content` | `string` | Yes | 1-50000 chars | Message text content |
| `timestamp` | `Date` | Yes | ISO 8601 datetime | Message creation time |
| `threadId` | `string` | Yes | UUID v4, foreign key to Thread | Parent conversation thread |
| `toolCalls` | `ToolCall[]` | No | Array of ToolCall objects | Tools invoked in this message |
| `metadata` | `MessageMetadata` | No | Object | Additional message information |

#### TypeScript Definition

```typescript
type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  threadId: string;
  toolCalls?: ToolCall[];
  metadata?: MessageMetadata;
}

interface MessageMetadata {
  streamingComplete?: boolean;
  errorRecoverable?: boolean;
  executionTimeMs?: number;
  tokenCount?: number;
}
```

#### Validation Rules

- `content` must not be empty after trimming
- `timestamp` must not be in the future
- User messages must not have `toolCalls`
- Tool messages must have exactly one corresponding `ToolCall` with `result` populated

#### State Transitions

```
[Draft] → [Sending] → [Sent] → [Complete]
                          ↓
                      [Error]
                          ↓
                  [Retrying] → [Sent]
```

**Draft**: User is typing (local state only)  
**Sending**: POST request in flight  
**Sent**: Backend acknowledged, SSE stream started  
**Complete**: Full message received, stored in thread history  
**Error**: Network failure or backend error  
**Retrying**: User triggered retry after error

---

### 2. Thread (Session)

Represents a conversation session with message history.

#### Fields

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `id` | `string` | Yes | UUID v4 | Unique thread identifier |
| `createdAt` | `Date` | Yes | ISO 8601 datetime | Thread creation time |
| `updatedAt` | `Date` | Yes | ISO 8601 datetime | Last message timestamp |
| `messages` | `Message[]` | Yes | Array of Message objects | Ordered conversation history |
| `status` | `ThreadStatus` | Yes | Enum: 'active', 'idle', 'error' | Current thread state |
| `metadata` | `ThreadMetadata` | No | Object | Additional thread information |

#### TypeScript Definition

```typescript
type ThreadStatus = 'active' | 'idle' | 'error';

interface Thread {
  id: string;
  createdAt: Date;
  updatedAt: Date;
  messages: Message[];
  status: ThreadStatus;
  metadata?: ThreadMetadata;
}

interface ThreadMetadata {
  title?: string; // Optional: first message preview
  messageCount?: number;
  lastError?: string;
  tags?: string[];
}
```

#### Validation Rules

- `messages` must be ordered by `timestamp` ascending
- `updatedAt` must be >= `createdAt`
- `status` must be 'error' if last message has error
- Maximum 50 messages per thread (auto-prune oldest if exceeded)

#### State Transitions

```
[New] → [Active] ↔ [Idle]
            ↓
        [Error] → [Recovered] → [Active]
```

**New**: Thread just created, no messages yet  
**Active**: Currently sending/receiving messages  
**Idle**: No activity, ready for new message  
**Error**: Last operation failed, awaiting retry  
**Recovered**: Error resolved, resuming normal operation

---

### 3. Connection

Represents the SSE connection state between frontend and backend.

#### Fields

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `status` | `ConnectionStatus` | Yes | Enum: 'connected', 'disconnected', 'connecting', 'reconnecting', 'error' | Current connection state |
| `endpoint` | `string` | Yes | Valid URL | Backend AG-UI endpoint |
| `lastPingAt` | `Date` | No | ISO 8601 datetime | Last successful heartbeat |
| `reconnectAttempts` | `number` | Yes | 0-5 | Number of reconnection attempts |
| `errorMessage` | `string` | No | Max 500 chars | Last connection error |

#### TypeScript Definition

```typescript
type ConnectionStatus = 
  | 'connected' 
  | 'disconnected' 
  | 'connecting' 
  | 'reconnecting' 
  | 'error';

interface Connection {
  status: ConnectionStatus;
  endpoint: string;
  lastPingAt?: Date;
  reconnectAttempts: number;
  errorMessage?: string;
}
```

#### Validation Rules

- `endpoint` must be valid HTTP/HTTPS URL
- `reconnectAttempts` must not exceed 5 (then move to 'error' state)
- `lastPingAt` must be within last 60 seconds for 'connected' status

#### State Transitions

```
[Disconnected] → [Connecting] → [Connected]
                      ↓              ↓
                  [Error] ← [Network Drop]
                      ↓
                [Reconnecting] → (retry with exponential backoff)
                      ↓
                [Connected] (if successful)
                      ↓
                [Error] (if max attempts exceeded)
```

**Disconnected**: Initial state, no connection established  
**Connecting**: EventSource connection being established  
**Connected**: SSE stream active, receiving events  
**Reconnecting**: Connection lost, attempting to restore  
**Error**: Max reconnection attempts exhausted, manual intervention needed

---

### 4. StreamingState

Represents the current state of streaming message reception.

#### Fields

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `isStreaming` | `boolean` | Yes | - | Whether currently receiving tokens |
| `currentMessageId` | `string` | No | UUID v4 | ID of message being streamed |
| `buffer` | `string` | Yes | Max 50000 chars | Accumulated tokens (not yet in message history) |
| `startedAt` | `Date` | No | ISO 8601 datetime | Stream start time |
| `tokenCount` | `number` | Yes | >= 0 | Number of tokens received |

#### TypeScript Definition

```typescript
interface StreamingState {
  isStreaming: boolean;
  currentMessageId?: string;
  buffer: string;
  startedAt?: Date;
  tokenCount: number;
}
```

#### Validation Rules

- `buffer` must be cleared when `isStreaming` transitions to false
- `currentMessageId` must exist when `isStreaming` is true
- `startedAt` must be set when streaming begins

#### State Transitions

```
[Idle] → [Streaming] → [Complete] → [Idle]
            ↓
        [Error] → [Idle]
```

**Idle**: No active streaming, buffer empty  
**Streaming**: Receiving tokens, accumulating in buffer  
**Complete**: `message_complete` event received, buffer moved to message history  
**Error**: Streaming interrupted, buffer discarded or marked as partial

---

### 5. ToolCall

Represents a backend tool invocation within a message.

#### Fields

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `id` | `string` | Yes | UUID v4 | Unique tool call identifier |
| `toolName` | `string` | Yes | Non-empty | Tool function name |
| `arguments` | `Record<string, unknown>` | Yes | Valid JSON object | Tool input parameters |
| `result` | `unknown` | No | Any valid JSON | Tool execution result |
| `status` | `ToolCallStatus` | Yes | Enum: 'pending', 'executing', 'completed', 'failed' | Execution state |
| `executionTimeMs` | `number` | No | >= 0 | Time taken to execute |
| `error` | `string` | No | Max 1000 chars | Error message if failed |

#### TypeScript Definition

```typescript
type ToolCallStatus = 'pending' | 'executing' | 'completed' | 'failed';

interface ToolCall {
  id: string;
  toolName: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  status: ToolCallStatus;
  executionTimeMs?: number;
  error?: string;
}
```

#### Validation Rules

- `result` must be present if `status` is 'completed'
- `error` must be present if `status` is 'failed'
- `executionTimeMs` must be present if `status` is 'completed' or 'failed'
- `toolName` must match one of the registered backend tools or client tools

#### State Transitions

```
[Pending] → [Executing] → [Completed]
                ↓
            [Failed]
```

**Pending**: Tool identified as needed, not yet invoked  
**Executing**: Tool function currently running (server or client)  
**Completed**: Tool returned result successfully  
**Failed**: Tool raised exception or timed out

---

### 6. AGUIEvent

Represents an event received via Server-Sent Events from the backend.

#### Fields

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `event` | `AGUIEventType` | Yes | Enum (see below) | Event type identifier |
| `threadId` | `string` | Yes | UUID v4 | Thread this event belongs to |
| `timestamp` | `string` | Yes | ISO 8601 datetime | Event creation time |
| `data` | `unknown` | No | Varies by event type | Event-specific payload |

#### TypeScript Definition

```typescript
type AGUIEventType = 
  | 'token'
  | 'tool_start'
  | 'tool_end'
  | 'tool_execution_request'
  | 'tool_execution_complete'
  | 'message_complete'
  | 'error';

interface AGUIEvent {
  event: AGUIEventType;
  threadId: string;
  timestamp: string;
  data?: unknown;
}

// Specific event type definitions
interface TokenEvent extends AGUIEvent {
  event: 'token';
  data: {
    token: string;
  };
}

interface ToolStartEvent extends AGUIEvent {
  event: 'tool_start';
  data: {
    toolName: string;
    arguments: Record<string, unknown>;
  };
}

interface ToolEndEvent extends AGUIEvent {
  event: 'tool_end';
  data: {
    toolName: string;
    result: unknown;
    executionTimeMs: number;
  };
}

interface ToolExecutionRequestEvent extends AGUIEvent {
  event: 'tool_execution_request';
  data: {
    executionId: string;
    toolName: string;
    arguments: Record<string, unknown>;
  };
}

interface ToolExecutionCompleteEvent extends AGUIEvent {
  event: 'tool_execution_complete';
  data: {
    executionId: string;
  };
}

interface MessageCompleteEvent extends AGUIEvent {
  event: 'message_complete';
  data?: undefined;
}

interface ErrorEvent extends AGUIEvent {
  event: 'error';
  data: {
    errorType: 'validation' | 'timeout' | 'llm' | 'tool_error' | 'connection';
    errorMessage: string;
    recoverable: boolean;
  };
}

type AGUIEventUnion = 
  | TokenEvent 
  | ToolStartEvent 
  | ToolEndEvent 
  | ToolExecutionRequestEvent
  | ToolExecutionCompleteEvent
  | MessageCompleteEvent 
  | ErrorEvent;
```

#### Validation Rules

- `event` must be one of the defined types
- `data` structure must match the event type
- `timestamp` must be parseable as ISO 8601 datetime
- `threadId` must correspond to an existing thread

---

## Entity Relationships

```
Thread (1) ──┬── (N) Message
             │
             └─── has current StreamingState (1)

Message (1) ──── (N) ToolCall

Connection (1) ──── observes ──── (N) AGUIEvent

StreamingState (1) ──── accumulates ──── (N) TokenEvent
```

**Description**:
- A Thread contains multiple Messages (1:N relationship)
- Each Thread has at most one active StreamingState
- A Message can have multiple ToolCalls (1:N relationship)
- The Connection receives AGUIEvents from backend
- StreamingState accumulates TokenEvents into a buffer

---

## State Management Schema

### Zustand Store Structure

```typescript
interface ChatStore {
  // Core entities
  currentThread: Thread | null;
  messages: Message[];
  connection: Connection;
  streamingState: StreamingState;
  
  // UI state
  isInputDisabled: boolean;
  lastError: string | null;
  
  // Actions
  createThread: () => string; // Returns new thread ID
  addMessage: (message: Message) => void;
  updateStreamingState: (update: Partial<StreamingState>) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  handleAGUIEvent: (event: AGUIEventUnion) => void;
  clearThread: () => void;
  retryLastMessage: () => void;
}
```

### Initial State

```typescript
const initialState: ChatStore = {
  currentThread: null,
  messages: [],
  connection: {
    status: 'disconnected',
    endpoint: 'http://127.0.0.1:5100',
    reconnectAttempts: 0,
  },
  streamingState: {
    isStreaming: false,
    buffer: '',
    tokenCount: 0,
  },
  isInputDisabled: false,
  lastError: null,
};
```

---

## Validation Rules Summary

### Message Validation

```typescript
function validateMessage(message: Message): ValidationResult {
  const errors: string[] = [];
  
  if (!message.content.trim()) {
    errors.push('Message content cannot be empty');
  }
  
  if (message.content.length > 50000) {
    errors.push('Message content exceeds maximum length (50000)');
  }
  
  if (message.timestamp > new Date()) {
    errors.push('Message timestamp cannot be in the future');
  }
  
  if (message.role === 'user' && message.toolCalls?.length) {
    errors.push('User messages cannot have tool calls');
  }
  
  if (message.role === 'tool' && (!message.toolCalls || message.toolCalls.length !== 1)) {
    errors.push('Tool messages must have exactly one tool call');
  }
  
  return {
    valid: errors.length === 0,
    errors,
  };
}
```

### Thread Validation

```typescript
function validateThread(thread: Thread): ValidationResult {
  const errors: string[] = [];
  
  if (thread.updatedAt < thread.createdAt) {
    errors.push('Thread updatedAt cannot be before createdAt');
  }
  
  if (thread.messages.length > 50) {
    errors.push('Thread exceeds maximum message count (50)');
  }
  
  // Ensure messages are ordered by timestamp
  const isOrdered = thread.messages.every((msg, i) => 
    i === 0 || msg.timestamp >= thread.messages[i - 1].timestamp
  );
  
  if (!isOrdered) {
    errors.push('Thread messages must be ordered by timestamp');
  }
  
  return {
    valid: errors.length === 0,
    errors,
  };
}
```

---

## Event Handlers

### Token Event Handler

```typescript
function handleTokenEvent(event: TokenEvent, store: ChatStore): void {
  if (!store.streamingState.isStreaming) {
    // Initialize streaming state
    store.updateStreamingState({
      isStreaming: true,
      currentMessageId: generateUUID(),
      startedAt: new Date(),
      buffer: event.data.token,
      tokenCount: 1,
    });
  } else {
    // Append token to buffer
    store.updateStreamingState({
      buffer: store.streamingState.buffer + event.data.token,
      tokenCount: store.streamingState.tokenCount + 1,
    });
  }
}
```

### Message Complete Event Handler

```typescript
function handleMessageCompleteEvent(event: MessageCompleteEvent, store: ChatStore): void {
  if (!store.streamingState.isStreaming) {
    console.warn('Received message_complete without active streaming');
    return;
  }
  
  // Create final message from buffer
  const message: Message = {
    id: store.streamingState.currentMessageId!,
    role: 'assistant',
    content: store.streamingState.buffer,
    timestamp: new Date(event.timestamp),
    threadId: event.threadId,
    metadata: {
      streamingComplete: true,
      tokenCount: store.streamingState.tokenCount,
      executionTimeMs: Date.now() - store.streamingState.startedAt!.getTime(),
    },
  };
  
  // Add to message history
  store.addMessage(message);
  
  // Reset streaming state
  store.updateStreamingState({
    isStreaming: false,
    currentMessageId: undefined,
    buffer: '',
    startedAt: undefined,
    tokenCount: 0,
  });
}
```

### Error Event Handler

```typescript
function handleErrorEvent(event: ErrorEvent, store: ChatStore): void {
  const { errorMessage, recoverable } = event.data;
  
  // Update connection status if connection error
  if (event.data.errorType === 'connection') {
    store.setConnectionStatus('error');
  }
  
  // Store error for display
  store.lastError = errorMessage;
  
  // Clear streaming state if unrecoverable
  if (!recoverable && store.streamingState.isStreaming) {
    store.updateStreamingState({
      isStreaming: false,
      buffer: '',
      currentMessageId: undefined,
    });
  }
  
  // Disable input if unrecoverable
  store.isInputDisabled = !recoverable;
}
```

---

## Persistence Strategy

### Browser LocalStorage (Optional Enhancement)

```typescript
interface PersistedState {
  threads: Thread[];
  lastActiveThreadId: string | null;
}

function saveToLocalStorage(store: ChatStore): void {
  const persistedState: PersistedState = {
    threads: [store.currentThread].filter(Boolean) as Thread[],
    lastActiveThreadId: store.currentThread?.id || null,
  };
  
  localStorage.setItem('chat-state', JSON.stringify(persistedState));
}

function loadFromLocalStorage(): PersistedState | null {
  const stored = localStorage.getItem('chat-state');
  if (!stored) return null;
  
  try {
    return JSON.parse(stored);
  } catch (error) {
    console.error('Failed to parse stored state:', error);
    return null;
  }
}
```

**Note**: LocalStorage is optional for MVP. Backend maintains authoritative state. Frontend persistence is for convenience only (e.g., recovering from accidental page refresh).

---

## Type Guards

```typescript
function isTokenEvent(event: AGUIEvent): event is TokenEvent {
  return event.event === 'token';
}

function isToolStartEvent(event: AGUIEvent): event is ToolStartEvent {
  return event.event === 'tool_start';
}

function isErrorEvent(event: AGUIEvent): event is ErrorEvent {
  return event.event === 'error';
}

// Use in event handler
function handleAGUIEvent(event: AGUIEvent): void {
  if (isTokenEvent(event)) {
    // TypeScript knows event.data.token exists
    appendToken(event.data.token);
  } else if (isErrorEvent(event)) {
    // TypeScript knows event.data.errorMessage exists
    displayError(event.data.errorMessage);
  }
}
```

---

## Summary

This data model provides:

1. **Type-safe entities** aligned with AG-UI protocol
2. **Clear validation rules** for data integrity
3. **State machine definitions** for lifecycle management
4. **Event handling patterns** for SSE processing
5. **Persistence strategy** for optional local caching
6. **Type guards** for runtime type safety

All entities are designed to support the functional requirements (FR-001 through FR-015) and integrate seamlessly with CopilotKit and the backend AG-UI protocol.
