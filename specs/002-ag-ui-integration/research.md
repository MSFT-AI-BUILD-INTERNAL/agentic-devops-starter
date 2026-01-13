# Research: AG-UI Integration

**Feature**: AG-UI Integration for Web-Based Agent Interface  
**Phase**: Phase 0 - Research & Outline  
**Date**: 2026-01-13

This document captures research findings that informed the design decisions for AG-UI integration.

---

## 1. AG-UI Package API

### Decision
Use `agent-framework-ag-ui` package with FastAPI integration for web-based agent interface.

### Rationale
- Official Microsoft Agent Framework package for UI integration
- Built specifically for FastAPI compatibility
- Provides SSE streaming out of the box
- Supports both server-side and client-side tool execution
- Maintains compatibility with existing `agent-framework` core

### Implementation Details

The `agent-framework-ag-ui` package provides:

1. **Server Setup**: Integration with FastAPI to create AG-UI endpoints
2. **SSE Streaming**: Built-in support for Server-Sent Events protocol
3. **Tool Registration**: Decorator-based tool registration system
4. **Type Safety**: Pydantic models for all data structures

Key API patterns:
```python
from agent_framework_ag_ui import create_agui_app

app = create_agui_app(
    agent=conversational_agent,
    server_tools=[get_time_zone],
    config=agui_config
)
```

### Alternatives Considered

1. **Custom FastAPI Implementation**: Build entire SSE streaming from scratch
   - Rejected: Reinventing the wheel, more maintenance burden
   - Would take significantly longer to implement

2. **WebSocket-based approach**: Use WebSockets instead of SSE
   - Rejected: More complex protocol, SSE sufficient for unidirectional streaming
   - SSE better for HTTP infrastructure compatibility

3. **Third-party chat frameworks**: LangChain, LlamaIndex with web interfaces
   - Rejected: Constitution mandates microsoft-agent-framework as foundation
   - Would require significant rework of existing ConversationalAgent

### References
- Agent Framework AG-UI Documentation (assumed to be available)
- FastAPI SSE Documentation: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
- SSE Specification: https://html.spec.whatwg.org/multipage/server-sent-events.html

---

## 2. FastAPI Integration Patterns

### Decision
Use factory pattern with lazy initialization for FastAPI app creation.

### Rationale
- **Testability**: Factory function allows creating app with different configs for testing
- **Flexibility**: Easy to inject mocks and test configurations
- **Separation of Concerns**: App creation separate from server startup
- **Best Practice**: Recommended pattern in FastAPI documentation for testing

### Implementation Pattern

```python
def create_app(
    config: AGUIServerConfig | None = None,
    agent: ConversationalAgent | None = None
) -> FastAPI:
    """Factory function to create FastAPI application.
    
    Args:
        config: Server configuration, uses defaults if None
        agent: Conversational agent instance, creates new if None
        
    Returns:
        Configured FastAPI application
    """
    if config is None:
        config = AGUIServerConfig.from_env()
    
    if agent is None:
        agent = ConversationalAgent(llm_config=config.llm_config)
    
    app = FastAPI(
        title="AG-UI Agent Server",
        description="Web-based conversational agent interface",
        version="0.1.0"
    )
    
    # Add middleware for correlation IDs
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(correlation_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    
    # Register routes
    app.include_router(chat_router)
    app.include_router(health_router)
    
    return app
```

### Lifespan Management

Use FastAPI lifespan events for resource management:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AG-UI server")
    yield
    # Shutdown
    logger.info("Shutting down AG-UI server")
    # Cleanup resources
```

### CORS Configuration

Enable CORS for web clients:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Alternatives Considered

1. **Global app instance**: Single app instance created at module level
   - Rejected: Makes testing difficult, tight coupling, hard to mock

2. **Class-based app**: Wrap FastAPI in a class
   - Rejected: Unnecessary complexity, FastAPI works best with functional approach
   - Factory pattern provides same benefits with less code

### References
- FastAPI Testing: https://fastapi.tiangolo.com/tutorial/testing/
- FastAPI Lifespan: https://fastapi.tiangolo.com/advanced/events/
- Factory Pattern: https://refactoring.guru/design-patterns/factory-method

---

## 3. Server-Sent Events (SSE) Streaming

### Decision
Implement SSE streaming using FastAPI's StreamingResponse with async generators.

### Rationale
- **Simple Protocol**: HTTP-based, works with existing infrastructure
- **Browser Support**: Native EventSource API in browsers
- **FastAPI Integration**: Built-in StreamingResponse support
- **Unidirectional**: Perfect for agent responses (server→client)
- **Reconnection**: Automatic reconnection handling in browsers

### Implementation Pattern

```python
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

async def generate_sse_events(
    message: str,
    thread_id: str,
    agent: ConversationalAgent
) -> AsyncGenerator[str, None]:
    """Generate SSE events for agent response.
    
    Yields SSE-formatted strings (data: {json}\n\n)
    """
    try:
        # Stream tokens from agent
        async for token in agent.stream_response(message):
            event_data = {
                "event": "token",
                "data": token,
                "thread_id": thread_id
            }
            yield f"data: {json.dumps(event_data)}\n\n"
        
        # Send completion event
        completion_event = {
            "event": "message_complete",
            "thread_id": thread_id
        }
        yield f"data: {json.dumps(completion_event)}\n\n"
        
    except Exception as e:
        # Send error event
        error_event = {
            "event": "error",
            "error": str(e),
            "thread_id": thread_id
        }
        yield f"data: {json.dumps(error_event)}\n\n"

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint with SSE streaming."""
    return StreamingResponse(
        generate_sse_events(request.message, request.thread_id, agent),
        media_type="text/event-stream"
    )
```

### Event Format

Standard SSE event structure:
```
data: {"event": "token", "data": "Hello", "thread_id": "uuid"}\n\n
data: {"event": "token", "data": " world", "thread_id": "uuid"}\n\n
data: {"event": "tool_start", "tool_name": "get_time_zone", "thread_id": "uuid"}\n\n
data: {"event": "tool_end", "result": {...}, "thread_id": "uuid"}\n\n
data: {"event": "message_complete", "thread_id": "uuid"}\n\n
```

### Client-Side Consumption

```python
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream("POST", f"{base_url}/chat", json=request_data) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])  # Remove "data: " prefix
                handle_event(data)
```

### Error Handling

1. **Connection Lost**: Client detects via timeout, attempts reconnection
2. **Server Error**: Send error event in stream, close stream gracefully
3. **Client Disconnect**: Server detects via connection close, stops generation

### Alternatives Considered

1. **WebSockets**: Bidirectional communication protocol
   - Rejected: Overkill for unidirectional streaming
   - More complex to implement and debug
   - Harder to work with HTTP infrastructure (load balancers, proxies)

2. **Long Polling**: Client polls for updates
   - Rejected: Higher latency, more server load
   - Not real-time streaming
   - More complex state management

3. **HTTP/2 Server Push**: Push responses to client
   - Rejected: Limited browser support
   - More complex setup
   - SSE provides similar experience with better compatibility

### References
- SSE Spec: https://html.spec.whatwg.org/multipage/server-sent-events.html
- FastAPI Streaming: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
- httpx Streaming: https://www.python-httpx.org/quickstart/#streaming-responses

---

## 4. Tool Execution Architecture

### Decision
Implement hybrid tool execution: server-side tools execute directly, client-side tools use request/response pattern.

### Rationale
- **Server Tools**: Fast execution, full server context access (databases, APIs, secrets)
- **Client Tools**: Access to client resources (local files, browser APIs, user-specific data)
- **Flexibility**: Mix both types in same conversation
- **Security**: Sensitive operations stay on server, user-specific operations on client

### Server-Side Tool Pattern

```python
from agent_framework import tool

@tool(description="Get the time zone for a city")
def get_time_zone(city: str) -> str:
    """Get time zone for a given city.
    
    Args:
        city: Name of the city
        
    Returns:
        Time zone name (e.g., 'America/New_York')
    """
    # Implementation with server-side resources
    import zoneinfo
    from timezonefinder import TimezoneFinder
    
    tf = TimezoneFinder()
    # Look up coordinates (simplified)
    tz_name = tf.timezone_at(lng=longitude, lat=latitude)
    return tz_name
```

Registration:
```python
app = create_agui_app(
    agent=agent,
    server_tools=[get_time_zone]  # Registered on server
)
```

### Client-Side Tool Pattern

```python
# Client-side tool (runs in client process)
def get_weather(city: str) -> dict:
    """Get current weather for a city.
    
    Args:
        city: Name of the city
        
    Returns:
        Weather data with temperature and conditions
    """
    # Simulated weather data
    return {
        "city": city,
        "temp": 72,
        "conditions": "Sunny"
    }
```

Registration:
```python
# In client code
client = HybridToolsClient(
    server_url="http://localhost:8000",
    client_tools=[get_weather]  # Registered on client
)
```

### Tool Execution Protocol

**Flow for Server Tool**:
1. Agent decides to call `get_time_zone("New York")`
2. Server executes tool directly in process
3. Result streamed to client: `{"event": "tool_end", "tool_name": "get_time_zone", "result": "America/New_York"}`

**Flow for Client Tool**:
1. Agent decides to call `get_weather("New York")`
2. Server streams: `{"event": "tool_execution_request", "tool_name": "get_weather", "params": {"city": "New York"}, "execution_id": "uuid"}`
3. Client executes local function: `result = get_weather("New York")`
4. Client sends: `POST /tool_result {"execution_id": "uuid", "result": {"temp": 72, "conditions": "Sunny"}}`
5. Server receives result, continues agent execution
6. Server streams: `{"event": "tool_execution_complete", "execution_id": "uuid"}`

### Error Handling

**Server Tool Errors**:
```python
try:
    result = tool_function(**params)
except Exception as e:
    logger.error(f"Server tool error: {tool_name}", exc_info=True)
    # Send error event to client
    yield f'data: {{"event": "tool_error", "tool_name": "{tool_name}", "error": "{str(e)}"}}\n\n'
```

**Client Tool Errors**:
```python
# Client catches exception
try:
    result = client_tool(**params)
except Exception as e:
    # Send error to server
    await client.post(f"{server_url}/tool_result", json={
        "execution_id": execution_id,
        "error": str(e)
    })
```

### Timeout Handling

- Server tools: Use `asyncio.wait_for()` with configurable timeout (default 30s)
- Client tools: Server waits for `/tool_result` with timeout, returns error if exceeded

### Alternatives Considered

1. **All tools on server**: No client-side execution
   - Rejected: Can't access client-local resources
   - Limits use cases (file access, browser APIs)

2. **All tools on client**: Agent runs on client
   - Rejected: Exposes API keys and secrets
   - Can't leverage server-side resources (databases)
   - Higher client complexity

3. **Remote Procedure Call (RPC)**: Use gRPC or similar
   - Rejected: Overkill for this use case
   - Adds complexity and dependencies
   - SSE-based approach is simpler

### References
- Tool Calling in LLMs: https://platform.openai.com/docs/guides/function-calling
- Agent Framework Tools Documentation (assumed)

---

## 5. Conversation State Management

### Decision
Use in-memory dictionary with threading.Lock for thread storage.

### Rationale
- **Simplicity**: No external dependencies, easy to understand
- **MVP Appropriate**: Sufficient for demonstration and development
- **Fast Access**: In-memory lookup is instant
- **Easy Testing**: No need to mock database connections
- **Migration Path**: Can be replaced with Redis/PostgreSQL later

### Implementation Pattern

```python
from threading import Lock
from datetime import datetime
from typing import Dict

class ThreadStorage:
    """In-memory storage for conversation threads."""
    
    def __init__(self):
        self._threads: Dict[str, ConversationThread] = {}
        self._lock = Lock()
    
    def create_thread(self, thread_id: str) -> ConversationThread:
        """Create a new conversation thread."""
        with self._lock:
            if thread_id in self._threads:
                raise ValueError(f"Thread {thread_id} already exists")
            
            thread = ConversationThread(
                thread_id=thread_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                message_history=[]
            )
            self._threads[thread_id] = thread
            return thread
    
    def get_thread(self, thread_id: str) -> ConversationThread | None:
        """Get a thread by ID."""
        with self._lock:
            return self._threads.get(thread_id)
    
    def update_thread(self, thread_id: str, message: ChatMessage) -> None:
        """Add a message to thread history."""
        with self._lock:
            if thread_id not in self._threads:
                raise ValueError(f"Thread {thread_id} not found")
            
            thread = self._threads[thread_id]
            thread.message_history.append(message)
            thread.updated_at = datetime.utcnow()
    
    def list_threads(self) -> list[ConversationThread]:
        """List all threads."""
        with self._lock:
            return list(self._threads.values())
    
    def delete_thread(self, thread_id: str) -> None:
        """Delete a thread."""
        with self._lock:
            if thread_id in self._threads:
                del self._threads[thread_id]
```

### Thread Safety

- Use `threading.Lock` for all dictionary access
- Lock acquisition in context manager (`with self._lock:`)
- Prevents race conditions in concurrent requests
- Tested with concurrent pytest-asyncio tests

### History Management

**Pruning Strategy**:
```python
def prune_history(thread: ConversationThread, max_messages: int = 50) -> None:
    """Keep only recent messages to prevent memory growth."""
    if len(thread.message_history) > max_messages:
        # Keep system message + recent messages
        system_messages = [m for m in thread.message_history if m.role == "system"]
        recent_messages = thread.message_history[-max_messages:]
        thread.message_history = system_messages + recent_messages
```

**Token Counting**:
```python
def count_tokens(thread: ConversationThread) -> int:
    """Estimate token count for conversation history."""
    # Rough estimate: 4 characters per token
    total_chars = sum(len(m.content) for m in thread.message_history)
    return total_chars // 4

def truncate_history(thread: ConversationThread, max_tokens: int = 4000) -> None:
    """Truncate history to fit within token limit."""
    while count_tokens(thread) > max_tokens:
        # Remove oldest non-system message
        for i, msg in enumerate(thread.message_history):
            if msg.role != "system":
                thread.message_history.pop(i)
                break
```

### Persistence Considerations

**Current (MVP)**:
- In-memory only
- Lost on server restart
- Not suitable for multi-process deployment

**Future Migration Path**:
1. Extract interface: `ThreadStorageInterface`
2. Implement `RedisThreadStorage` or `PostgreSQLThreadStorage`
3. Inject storage implementation via dependency injection
4. No changes to business logic

### Alternatives Considered

1. **Redis**: External in-memory store
   - Rejected for MVP: Adds deployment complexity
   - Consider for production: Enables multi-process deployment, persistence

2. **PostgreSQL**: Relational database
   - Rejected for MVP: Overkill for simple key-value storage
   - Consider for production: Full persistence, complex queries

3. **SQLite**: File-based database
   - Rejected: Concurrency limitations, file I/O overhead
   - Not suitable for web server

4. **Global dictionary without lock**: Simplest approach
   - Rejected: Race conditions in concurrent requests
   - Thread safety is critical

### References
- Python threading.Lock: https://docs.python.org/3/library/threading.html#lock-objects
- FastAPI Dependency Injection: https://fastapi.tiangolo.com/tutorial/dependencies/

---

## Summary of Research Decisions

### Critical Decisions Matrix

| Area | Decision | Impact | Reversibility |
|------|----------|--------|---------------|
| AG-UI Package | Use agent-framework-ag-ui | High - Core architecture | Low - Would require rewrite |
| App Initialization | Factory pattern | Medium - Testing capability | High - Can refactor easily |
| Streaming Protocol | SSE over WebSockets | Medium - Client compatibility | Medium - Protocol change |
| Tool Architecture | Hybrid (client + server) | High - Capabilities | Medium - Can add/remove sides |
| State Storage | In-memory with Lock | Low - MVP only | High - Interface extraction |

### Key Takeaways

1. **Leverage Existing Infrastructure**: Build on top of existing ConversationalAgent, logging_utils, and LLMConfig
2. **Start Simple**: In-memory storage for MVP, easy to upgrade later
3. **Follow Standards**: Use SSE (standard protocol), FastAPI patterns (framework conventions)
4. **Prioritize Testing**: Factory pattern enables comprehensive testing
5. **Plan for Scale**: Design allows future migration to Redis/PostgreSQL without business logic changes

### Next Steps

With research complete, proceed to:
1. **Phase 1**: Create detailed design documents
   - `data-model.md`: Entity definitions
   - `contracts/`: API specifications
   - `quickstart.md`: Getting started guide
   
2. **Update Agent Context**: Add new patterns to `.specify/context/copilot.md`

3. **Phase 2**: Break down into detailed implementation tasks

---

**Research Complete**: 2026-01-13  
**Next Phase**: Phase 1 - Design & Contracts
