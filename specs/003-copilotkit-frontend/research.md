# Research: Web-Based Chatbot Frontend Integration

**Feature Branch**: `003-copilotkit-frontend`  
**Date**: 2025-01-17  
**Status**: Complete

## Overview

This document consolidates research findings for implementing a modern web-based chat interface that integrates with the existing AG-UI backend. The research covers CopilotKit framework capabilities, AG-UI protocol specifications, and React/TypeScript best practices for building production-quality chat applications.

## Research Areas

### 1. CopilotKit Framework Integration

#### Decision: Use CopilotKit for Chat UI Components

**Rationale**: CopilotKit provides production-ready React components specifically designed for AI chat interfaces, eliminating the need to build complex chat UI from scratch. It has native support for streaming responses, tool execution visualization, and backend integration.

**Key Packages**:
- `@copilotkit/react-core` - Core provider and state management
- `@copilotkit/react-ui` - Pre-built chat components (CopilotChat, message bubbles)
- `@copilotkit/react-textarea` - Enhanced input with AI suggestions (optional)

**Integration Pattern**:
```typescript
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";

function App() {
  return (
    <CopilotKit 
      runtimeUrl="http://127.0.0.1:5100"
      agent="AGUIAssistant"
    >
      <ChatInterface />
    </CopilotKit>
  );
}
```

**Streaming Support**: CopilotKit natively handles Server-Sent Events (SSE) for real-time token streaming. The framework automatically manages:
- EventSource connection establishment and cleanup
- Progressive token display (60fps target)
- Reconnection logic on connection failures
- Message completion detection

**Tool Execution**: CopilotKit supports both server-side and client-side tool execution through its agent framework integration. Tools are registered and invoked transparently through the chat interface.

**Alternatives Considered**:
- **Build custom React components**: Rejected - would require 2-3 weeks additional development time for chat UI basics
- **react-chat-widget**: Rejected - lacks streaming support and tool integration
- **Langchain Chat UI**: Rejected - tightly coupled to Langchain, not backend-agnostic

---

### 2. AG-UI Protocol Specifications

#### Backend API Endpoints

The existing backend (`/app/agui_server.py`) exposes the following endpoints via `agent-framework-ag-ui`:

| Endpoint | Method | Purpose | Request Format | Response Format |
|----------|--------|---------|----------------|-----------------|
| `/` (root) | POST | Main chat endpoint | `{message, thread_id?, stream}` | SSE stream |
| `/health` | GET | Server health check | None | `{status, version, thread_count, uptime_seconds}` |
| `/threads` | GET | List all conversations | None | `[{thread_id, created_at, message_count}]` |
| `/threads/{id}` | GET | Retrieve conversation | None | `{thread_id, messages[], metadata}` |
| `/tool_result` | POST | Client tool results | `{execution_id, result, error?}` | `{success: true}` |
| `/docs` | GET | OpenAPI documentation | None | Swagger UI |

#### SSE Event Format

All streaming events follow this base structure:
```typescript
interface AGUIEvent {
  event: 'token' | 'tool_start' | 'tool_end' | 'tool_execution_request' | 
         'tool_execution_complete' | 'message_complete' | 'error';
  thread_id: string;
  timestamp: string; // ISO 8601
  // Event-specific fields below
}
```

**Event Types**:

1. **token**: Individual text chunk from LLM
   ```typescript
   { event: 'token', token: 'Hello', thread_id: '...', timestamp: '...' }
   ```

2. **tool_start**: Server-side tool execution begins
   ```typescript
   { 
     event: 'tool_start', 
     tool_name: 'get_time_zone', 
     arguments: { location: 'Seattle' },
     thread_id: '...', 
     timestamp: '...' 
   }
   ```

3. **tool_end**: Server-side tool execution completes
   ```typescript
   { 
     event: 'tool_end', 
     tool_name: 'get_time_zone', 
     result: 'Pacific Time (UTC-8)',
     execution_time_ms: 45.2,
     thread_id: '...', 
     timestamp: '...' 
   }
   ```

4. **tool_execution_request**: Request client to execute tool
   ```typescript
   { 
     event: 'tool_execution_request', 
     execution_id: 'uuid',
     tool_name: 'get_weather', 
     arguments: { location: 'Seattle' },
     thread_id: '...', 
     timestamp: '...' 
   }
   ```

5. **tool_execution_complete**: Client tool results received
   ```typescript
   { 
     event: 'tool_execution_complete', 
     execution_id: 'uuid',
     thread_id: '...', 
     timestamp: '...' 
   }
   ```

6. **message_complete**: Full response generation finished
   ```typescript
   { event: 'message_complete', thread_id: '...', timestamp: '...' }
   ```

7. **error**: Error occurred during processing
   ```typescript
   { 
     event: 'error', 
     error_type: 'timeout' | 'llm' | 'tool_error' | 'validation',
     error_message: 'Human-readable description',
     recoverable: true | false,
     thread_id: '...', 
     timestamp: '...' 
   }
   ```

#### Thread Management

**Thread Lifecycle**:
- Create new thread: POST `/` with `thread_id: null` → returns new UUID
- Continue conversation: POST `/` with existing `thread_id` → maintains context
- Retrieve history: GET `/threads/{thread_id}` → returns full message array
- List threads: GET `/threads` → returns all active thread metadata

**Thread Storage**: In-memory with thread-safe locking (MVP). Configuration:
- Max 100 concurrent threads
- Max 50 messages per thread (auto-pruning oldest)
- Thread IDs are UUIDs v4
- Lost on server restart (acceptable for MVP)

**Context Preservation**: Backend maintains full conversation history per thread. Each message includes:
```typescript
interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: Date;
  tool_calls?: ToolCall[];
}
```

#### Tool Execution Patterns

**Server-Side Tools** (synchronous):
```python
# Backend registration
@ai_function(description="Get the time zone for a location.")
def get_time_zone(location: str) -> str:
    return timezone_data.get(location.lower())

agent = ChatAgent(tools=[get_time_zone])
```
Flow: Agent decides → Server executes → `tool_start` event → `tool_end` event → Result incorporated

**Client-Side Tools** (async request/response):
1. Agent emits `tool_execution_request` with execution_id
2. Frontend receives SSE event
3. Frontend executes tool locally
4. Frontend POSTs results to `/tool_result` with execution_id
5. Backend continues agent processing with result

**Hybrid Mode**: Both server and client tools work seamlessly in same conversation. Agent framework automatically routes to appropriate executor.

#### Error Handling

**Error Categories**:
- `validation`: Malformed request (422 HTTP response before streaming)
- `timeout`: Tool execution exceeded 30s limit
- `llm`: LLM API unavailable or returned error
- `tool_error`: Tool raised exception
- `connection`: Network interruption

**Error Response**:
- Recoverable errors: `recoverable: true` → Client can retry
- Non-recoverable errors: `recoverable: false` → Show error, reset state

**Logging**: All operations logged with correlation IDs (`X-Correlation-ID` header) for tracing:
```
2025-01-17 10:00:00 - INFO - [abc-123-def] - Chat request received
2025-01-17 10:00:01 - INFO - [abc-123-def] - Tool execution: get_time_zone
2025-01-17 10:00:02 - INFO - [abc-123-def] - Message complete
```

---

### 3. React/TypeScript Best Practices

#### State Management Strategy

**Decision: Zustand + Custom Hooks**

**Rationale**: 
- Zustand provides lightweight global state without Redux boilerplate
- Better performance for frequent updates (streaming tokens) than Context API
- TypeScript-first design with excellent type inference
- Minimal re-renders through selector pattern
- Easy to test with mock stores

**Store Architecture**:
```typescript
// stores/chatStore.ts
import { create } from 'zustand';

interface ChatStore {
  // State
  messages: Message[];
  currentThreadId: string | null;
  connectionStatus: 'connected' | 'disconnected' | 'reconnecting';
  isStreaming: boolean;
  streamingMessage: string;
  
  // Actions
  addMessage: (message: Message) => void;
  updateStreamingMessage: (token: string) => void;
  finalizeStreamingMessage: () => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  clearConversation: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  currentThreadId: null,
  connectionStatus: 'disconnected',
  isStreaming: false,
  streamingMessage: '',
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  updateStreamingMessage: (token) => set((state) => ({
    streamingMessage: state.streamingMessage + token
  })),
  
  finalizeStreamingMessage: () => set((state) => ({
    messages: [...state.messages, {
      role: 'assistant',
      content: state.streamingMessage,
      timestamp: new Date()
    }],
    streamingMessage: '',
    isStreaming: false
  })),
  
  // ... other actions
}));
```

**Custom Hooks Pattern**:
```typescript
// hooks/useChat.ts
export function useChat() {
  const { messages, addMessage, currentThreadId } = useChatStore();
  const { sendMessage } = useAGUIClient();
  
  const handleSendMessage = useCallback(async (content: string) => {
    const userMessage = { role: 'user', content, timestamp: new Date() };
    addMessage(userMessage);
    await sendMessage(content, currentThreadId);
  }, [addMessage, sendMessage, currentThreadId]);
  
  return { messages, sendMessage: handleSendMessage };
}
```

**Alternatives Considered**:
- **Redux Toolkit**: Rejected - overkill for chat application, more boilerplate
- **Context API alone**: Rejected - performance issues with frequent streaming updates
- **Jotai/Recoil**: Rejected - less mature ecosystem, harder to debug

#### SSE Connection Management

**Pattern: Custom Hook with Cleanup**:
```typescript
// hooks/useSSEConnection.ts
export function useSSEConnection(url: string, threadId: string | null) {
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const sourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttempts = useRef(0);
  
  const connect = useCallback(() => {
    // Build URL with thread_id if available
    const eventSourceUrl = threadId 
      ? `${url}?thread_id=${threadId}` 
      : url;
      
    sourceRef.current = new EventSource(eventSourceUrl);
    
    sourceRef.current.onopen = () => {
      setStatus('connected');
      reconnectAttempts.current = 0;
    };
    
    sourceRef.current.onerror = () => {
      setStatus('disconnected');
      sourceRef.current?.close();
      scheduleReconnect();
    };
    
    sourceRef.current.onmessage = (event) => {
      handleSSEMessage(JSON.parse(event.data));
    };
  }, [url, threadId]);
  
  const scheduleReconnect = () => {
    if (reconnectAttempts.current >= 5) {
      setStatus('error');
      return;
    }
    
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
    reconnectAttempts.current++;
    setStatus('reconnecting');
    
    reconnectTimeoutRef.current = window.setTimeout(connect, delay);
  };
  
  useEffect(() => {
    connect();
    
    return () => {
      sourceRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);
  
  return { status, reconnect: connect };
}
```

**Reconnection Strategy**:
- Exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s (max)
- Max 5 automatic retry attempts
- Manual reconnect button after exhausted attempts
- Preserve message queue during reconnection
- Use `navigator.onLine` event for network detection

#### Streaming Text Optimization

**Problem**: Frequent token updates cause excessive re-renders, degrading performance.

**Solution: Debounced State Updates**:
```typescript
// hooks/useStreamingText.ts
export function useStreamingText() {
  const [localBuffer, setLocalBuffer] = useState('');
  const debouncedUpdate = useDebouncedCallback(
    (text: string) => useChatStore.getState().updateStreamingMessage(text),
    50 // Batch updates every 50ms
  );
  
  const appendToken = useCallback((token: string) => {
    setLocalBuffer(prev => {
      const newText = prev + token;
      debouncedUpdate(newText);
      return newText;
    });
  }, [debouncedUpdate]);
  
  const finalize = useCallback(() => {
    debouncedUpdate.flush(); // Ensure final state is synced
    useChatStore.getState().finalizeStreamingMessage();
    setLocalBuffer('');
  }, [debouncedUpdate]);
  
  return { appendToken, finalize, streamingText: localBuffer };
}
```

**React 18 Optimizations**:
- Use `useTransition()` for pending UI states during streaming
- Memoize message components with `React.memo()`
- Use `useDeferredValue()` for non-critical updates (timestamps, metadata)
- Avoid inline functions in render (use `useCallback`)

#### Auto-Scrolling Implementation

**Pattern: Smart Auto-Scroll with User Override**:
```typescript
// hooks/useAutoScroll.ts
export function useAutoScroll(messages: Message[]) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);
  
  // Detect if user scrolled up
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10;
    
    shouldAutoScroll.current = isAtBottom;
  }, []);
  
  // Scroll to bottom on new messages (only if not manually scrolled up)
  useLayoutEffect(() => {
    if (shouldAutoScroll.current && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [messages.length]);
  
  // Force scroll to bottom (for new user messages)
  const scrollToBottom = useCallback(() => {
    shouldAutoScroll.current = true;
    messagesEndRef.current?.scrollIntoView({ 
      behavior: 'smooth',
      block: 'end' 
    });
  }, []);
  
  return { messagesEndRef, containerRef, handleScroll, scrollToBottom };
}
```

**Key Details**:
- Use `useLayoutEffect` instead of `useEffect` for synchronous scroll
- Detect user scroll with tolerance (10px from bottom)
- Resume auto-scroll when user scrolls back to bottom
- Force scroll on new user messages

#### Testing Strategies

**Unit Tests** (Vitest + React Testing Library):
```typescript
// tests/unit/useChat.test.ts
import { renderHook, act } from '@testing-library/react';
import { useChat } from '@/hooks/useChat';

describe('useChat', () => {
  it('should add message to store when sendMessage is called', async () => {
    const { result } = renderHook(() => useChat());
    
    await act(async () => {
      await result.current.sendMessage('Hello');
    });
    
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe('Hello');
  });
});
```

**Integration Tests** (Mock Service Worker for SSE):
```typescript
// tests/integration/streaming.test.ts
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('http://127.0.0.1:5100/stream', (req, res, ctx) => {
    // Simulate SSE stream
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"event":"token","token":"Hello"}\n\n'));
        controller.enqueue(encoder.encode('data: {"event":"message_complete"}\n\n'));
        controller.close();
      }
    });
    
    return res(
      ctx.status(200),
      ctx.set('Content-Type', 'text/event-stream'),
      ctx.body(stream)
    );
  })
);
```

**E2E Tests** (Playwright):
```typescript
// tests/e2e/chat.spec.ts
import { test, expect } from '@playwright/test';

test('should display streamed response', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  await page.fill('[data-testid="message-input"]', 'Hello');
  await page.click('[data-testid="send-button"]');
  
  // Wait for streaming to start
  await expect(page.locator('[data-testid="streaming-indicator"]')).toBeVisible();
  
  // Wait for message completion
  await expect(page.locator('[data-testid="assistant-message"]')).toContainText('Hello');
});
```

#### Security Considerations

**XSS Prevention**:
```typescript
import DOMPurify from 'dompurify';

function sanitizeMessage(content: string): string {
  return DOMPurify.sanitize(content, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'code', 'pre', 'br'],
    ALLOWED_ATTR: []
  });
}
```

**Rate Limiting** (Client-side):
```typescript
const rateLimiter = {
  messages: [] as number[],
  windowMs: 60000, // 1 minute
  maxRequests: 10,
  
  canSend(): boolean {
    const now = Date.now();
    this.messages = this.messages.filter(t => now - t < this.windowMs);
    return this.messages.length < this.maxRequests;
  },
  
  recordMessage(): void {
    this.messages.push(Date.now());
  }
};
```

**CORS Configuration** (Backend already configured):
```python
# Backend handles CORS - frontend just needs to send credentials
fetch(url, {
  credentials: 'include',  // Include cookies if using auth
  headers: {
    'Content-Type': 'application/json'
  }
});
```

**Content Security Policy**:
```html
<!-- Add to index.html -->
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               connect-src 'self' http://127.0.0.1:5100; 
               script-src 'self' 'unsafe-inline'; 
               style-src 'self' 'unsafe-inline';">
```

---

## Technology Stack Summary

### Core Dependencies

| Package | Version | Purpose | Justification |
|---------|---------|---------|---------------|
| **react** | ^18.2.0 | UI framework | Industry standard, excellent TypeScript support |
| **@copilotkit/react-core** | ^latest | Chat state management | Pre-built chat logic, streaming support |
| **@copilotkit/react-ui** | ^latest | Chat UI components | Production-ready chat interface |
| **typescript** | ^5.3.0 | Type safety | Constitution requirement equivalent for frontend |
| **vite** | ^5.0.0 | Build tool | Fast HMR, optimized builds |
| **zustand** | ^4.4.0 | State management | Lightweight, performant for streaming |
| **tailwindcss** | ^3.4.0 | Styling | Rapid UI development, design consistency |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **vitest** | ^1.0.0 | Unit testing |
| **@testing-library/react** | ^14.0.0 | Component testing |
| **playwright** | ^1.40.0 | E2E testing |
| **eslint** | ^8.55.0 | Linting |
| **prettier** | ^3.1.0 | Code formatting |
| **@types/react** | ^18.2.0 | TypeScript definitions |

### Build Configuration

**Vite** (`vite.config.ts`):
- Dev server port: 5173
- Proxy `/api` to `http://127.0.0.1:5100` for CORS avoidance
- Fast Refresh enabled for React
- Code splitting for optimal bundle size

**TypeScript** (`tsconfig.json`):
- Target: ES2020
- Strict mode enabled
- Path aliases: `@/` → `src/`
- JSX: react-jsx

**TailwindCSS** (`tailwind.config.js`):
- Custom color scheme for chat UI
- Dark mode support (optional enhancement)
- Custom animations for streaming indicators

---

## Design Decisions Summary

### 1. CopilotKit vs. Custom Implementation
**Decision**: Use CopilotKit  
**Why**: Saves 2-3 weeks of development, provides production-tested components, native streaming support

### 2. Zustand vs. Redux vs. Context API
**Decision**: Zustand  
**Why**: Optimal performance for streaming updates, minimal boilerplate, excellent TypeScript support

### 3. Vite vs. Create React App vs. Next.js
**Decision**: Vite  
**Why**: Fastest dev server, simple SPA requirements (no SSR needed), modern tooling

### 4. SSE vs. WebSocket
**Decision**: SSE (Server-Sent Events)  
**Why**: Backend already uses SSE, simpler protocol, auto-reconnection built-in, HTTP-friendly

### 5. Component Library vs. TailwindCSS
**Decision**: TailwindCSS  
**Why**: Full design control, smaller bundle size, CopilotKit components are headless/customizable

### 6. Local State vs. Global State for Streaming
**Decision**: Hybrid (local buffer + debounced global updates)  
**Why**: Prevents re-render thrashing, maintains single source of truth, optimal performance

### 7. Manual Scroll Management vs. Library
**Decision**: Manual implementation  
**Why**: Simple requirement, full control, no additional dependencies, < 50 lines of code

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │           React Application (Port 5173)             │  │
│  │                                                       │  │
│  │  ┌──────────────┐    ┌─────────────────────────┐   │  │
│  │  │ CopilotKit   │───▶│   Custom Hooks          │   │  │
│  │  │   Provider   │    │  - useChat()            │   │  │
│  │  └──────────────┘    │  - useStreaming()       │   │  │
│  │         │             │  - useConnection()      │   │  │
│  │         ▼             └─────────────────────────┘   │  │
│  │  ┌──────────────┐              │                     │  │
│  │  │   Zustand    │◀─────────────┘                     │  │
│  │  │    Store     │                                     │  │
│  │  └──────────────┘                                     │  │
│  │         │                                              │  │
│  │         ▼                                              │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │           React Components                    │   │  │
│  │  │  - ChatInterface                              │   │  │
│  │  │  - MessageList                                │   │  │
│  │  │  - MessageInput                               │   │  │
│  │  │  - ToolIndicator                              │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          │ HTTP + SSE                       │
│                          ▼                                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                          ▼                                   │
│              FastAPI Server (Port 5100)                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         agent-framework-ag-ui Endpoints              │  │
│  │                                                       │  │
│  │  POST   /          - Main chat (SSE streaming)       │  │
│  │  GET    /health    - Health check                    │  │
│  │  GET    /threads   - List conversations              │  │
│  │  POST   /tool_result - Client tool results           │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ChatAgent                               │  │
│  │    (microsoft-agent-framework)                       │  │
│  │                                                       │  │
│  │  - Conversation state management                     │  │
│  │  - LLM orchestration                                 │  │
│  │  - Tool execution (server-side)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Azure OpenAI / OpenAI API                    │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Communication Flow**:
1. User types message → React component
2. Component calls `useChat().sendMessage()`
3. Hook sends POST request to `/` endpoint
4. Backend creates SSE stream
5. Frontend receives token events progressively
6. Zustand store batches updates (50ms debounce)
7. React components re-render with new tokens
8. On `message_complete` event, finalize message
9. Tool execution follows same pattern with request/response cycle

---

## Implementation Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **CopilotKit compatibility issues with AG-UI** | High | Low | Test integration early in Phase 1, fallback to custom components if needed |
| **SSE connection instability** | Medium | Medium | Implement robust reconnection logic with exponential backoff |
| **Performance degradation with long conversations** | Medium | Medium | Auto-prune messages >50, implement virtual scrolling if needed |
| **Browser compatibility issues** | Low | Low | Target modern browsers only (constitution allows), test with Playwright |
| **Backend changes during development** | High | Low | Backend is frozen per spec, communicate with backend team |
| **Type mismatches between frontend/backend** | Medium | Medium | Generate TypeScript types from OpenAPI spec at `/docs` |

---

## Next Steps (Phase 1)

Based on this research, Phase 1 will focus on:

1. **Data Model Definition** (`data-model.md`):
   - Message entity structure
   - Session/Thread entity structure
   - AG-UI event type definitions
   - Tool execution state models

2. **API Contracts** (`contracts/agui-protocol.yaml`):
   - OpenAPI specification for all endpoints
   - SSE event schema definitions
   - Request/response type definitions

3. **Quickstart Guide** (`quickstart.md`):
   - Step-by-step setup instructions
   - Environment configuration
   - Running backend + frontend concurrently
   - Testing the integration

4. **Agent Context Update**:
   - Update Copilot context with new technologies
   - Document frontend architecture for AI assistance

All unknowns from Technical Context have been resolved. Ready to proceed to Phase 1.
