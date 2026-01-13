# Data Model: AG-UI Integration

**Feature**: AG-UI Integration for Web-Based Agent Interface  
**Phase**: Phase 1 - Design & Contracts  
**Date**: 2026-01-13

This document defines the entities, their relationships, validation rules, and state transitions for the AG-UI integration feature.

---

## Entity Definitions

### 1. AGUIServerConfig

**Purpose**: Configuration for the AG-UI FastAPI server

**Fields**:
```python
class AGUIServerConfig(BaseModel):
    """Configuration for AG-UI server."""
    
    # Server settings
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to"
    )
    port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Port to bind the server to"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # LLM configuration
    llm_config: LLMConfig = Field(
        description="LLM provider configuration"
    )
    
    # Tool configuration
    server_tools: list[Callable] = Field(
        default_factory=list,
        description="Server-side tool functions"
    )
    
    # Threading settings
    max_threads: int = Field(
        default=100,
        gt=0,
        description="Maximum number of concurrent conversation threads"
    )
    max_messages_per_thread: int = Field(
        default=50,
        gt=0,
        description="Maximum messages to keep in thread history"
    )
    
    # Timeout settings
    tool_timeout_seconds: int = Field(
        default=30,
        gt=0,
        description="Timeout for tool execution in seconds"
    )
    
    @classmethod
    def from_env(cls) -> "AGUIServerConfig":
        """Create configuration from environment variables."""
        llm_config = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("LLM_MODEL", "gpt-4"),
            # ... other LLM settings
        )
        
        return cls(
            host=os.getenv("AGUI_HOST", "0.0.0.0"),
            port=int(os.getenv("AGUI_PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            llm_config=llm_config
        )
```

**Validation Rules**:
- Port must be in range 1024-65535 (non-privileged ports)
- Host must be valid IP address or hostname
- LLM API key must be non-empty
- Log level must be valid Python logging level
- Timeout values must be positive integers
- Max threads must be positive

**Relationships**:
- Contains one `LLMConfig` (composition)
- References list of server tool functions

---

### 2. ConversationThread

**Purpose**: Represents an ongoing conversation session

**Fields**:
```python
class ConversationThread(BaseModel):
    """A conversation thread with message history."""
    
    thread_id: str = Field(
        description="Unique identifier for the thread (UUID)"
    )
    created_at: datetime = Field(
        description="When the thread was created"
    )
    updated_at: datetime = Field(
        description="When the thread was last updated"
    )
    message_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Ordered list of messages in this thread"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (user_id, session_id, etc.)"
    )
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the thread history."""
        self.message_history.append(message)
        self.updated_at = datetime.utcnow()
    
    def get_message_count(self) -> int:
        """Get the number of messages in this thread."""
        return len(self.message_history)
    
    def get_token_estimate(self) -> int:
        """Estimate token count for the conversation."""
        # Rough estimate: 4 characters per token
        total_chars = sum(len(m.content) for m in self.message_history)
        return total_chars // 4
```

**Validation Rules**:
- `thread_id` must be valid UUID format
- `created_at` and `updated_at` must be valid datetime objects
- `updated_at` must be >= `created_at`
- `message_history` must maintain chronological order
- Maximum message count enforced by server configuration

**State Transitions**:
```
[Created] → [Active] → [Archived] (future)
    ↓          ↓
  Initial    Adding messages
```

**Relationships**:
- Contains many `ChatMessage` instances (composition)
- No parent entity (top-level aggregate)

---

### 3. ChatMessage

**Purpose**: A single message in a conversation

**Fields**:
```python
class MessageRole(str, Enum):
    """Valid message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A message in a conversation."""
    
    role: MessageRole = Field(
        description="Role of the message sender"
    )
    content: str = Field(
        min_length=1,
        description="Content of the message"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the message was created"
    )
    tool_calls: list[ToolCall] | None = Field(
        default=None,
        description="Tool calls made in this message (if any)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
```

**Validation Rules**:
- `role` must be one of: user, assistant, system, tool
- `content` must not be empty (min_length=1)
- `timestamp` must be valid datetime
- `tool_calls` only valid for assistant role
- Maximum content length: 100,000 characters (configurable)

**Relationships**:
- Belongs to one `ConversationThread`
- May contain multiple `ToolCall` instances

---

### 4. ToolDefinition

**Purpose**: Metadata for a tool function

**Fields**:
```python
class ExecutionLocation(str, Enum):
    """Where the tool executes."""
    SERVER = "server"
    CLIENT = "client"


class ToolParameter(BaseModel):
    """A parameter for a tool."""
    name: str
    type: str  # JSON Schema type: string, number, boolean, object, array
    description: str
    required: bool = True
    default: Any | None = None


class ToolDefinition(BaseModel):
    """Definition of a tool function."""
    
    name: str = Field(
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$",
        description="Tool function name (valid Python identifier)"
    )
    description: str = Field(
        min_length=10,
        description="Human-readable description of what the tool does"
    )
    parameters: list[ToolParameter] = Field(
        description="List of parameters the tool accepts"
    )
    return_type: str = Field(
        description="JSON Schema type of the return value"
    )
    execution_location: ExecutionLocation = Field(
        description="Where the tool executes (server or client)"
    )
    timeout_seconds: int = Field(
        default=30,
        gt=0,
        description="Timeout for tool execution"
    )
    
    @classmethod
    def from_function(
        cls,
        func: Callable,
        execution_location: ExecutionLocation
    ) -> "ToolDefinition":
        """Create tool definition from a function with type hints."""
        import inspect
        from typing import get_type_hints
        
        # Extract from function signature and docstring
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        parameters = []
        for param_name, param in sig.parameters.items():
            param_type = type_hints.get(param_name, "string")
            parameters.append(ToolParameter(
                name=param_name,
                type=cls._python_type_to_json_schema(param_type),
                description=f"Parameter {param_name}",
                required=param.default == inspect.Parameter.empty
            ))
        
        return cls(
            name=func.__name__,
            description=func.__doc__ or "No description provided",
            parameters=parameters,
            return_type=cls._python_type_to_json_schema(
                type_hints.get("return", str)
            ),
            execution_location=execution_location
        )
```

**Validation Rules**:
- `name` must be valid Python identifier (alphanumeric + underscore)
- `description` must be at least 10 characters (meaningful description)
- `parameters` must have valid JSON Schema types
- `timeout_seconds` must be positive
- `execution_location` must be 'server' or 'client'

**Relationships**:
- Used by server tools (ServerTool) or client tools (ClientTool)
- Referenced by `ToolCall` instances

---

### 5. ToolCall

**Purpose**: Record of a tool function invocation

**Fields**:
```python
class ToolCall(BaseModel):
    """A tool function call made by the agent."""
    
    tool_name: str = Field(
        description="Name of the tool that was called"
    )
    arguments: dict[str, Any] = Field(
        description="Arguments passed to the tool"
    )
    result: Any | None = Field(
        default=None,
        description="Result returned by the tool (None if not yet executed)"
    )
    error: str | None = Field(
        default=None,
        description="Error message if tool execution failed"
    )
    execution_time_ms: float | None = Field(
        default=None,
        ge=0,
        description="Time taken to execute the tool in milliseconds"
    )
```

**Validation Rules**:
- `tool_name` must match a registered tool
- `arguments` must validate against tool's parameter schema
- Either `result` or `error` should be set after execution, not both
- `execution_time_ms` must be non-negative if set

**Relationships**:
- Belongs to one `ChatMessage`
- References one `ToolDefinition` (by name)

---

### 6. StreamingEvent

**Purpose**: Event sent via SSE stream to client

**Base Class**:
```python
class EventType(str, Enum):
    """Types of streaming events."""
    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_EXECUTION_REQUEST = "tool_execution_request"
    TOOL_EXECUTION_COMPLETE = "tool_execution_complete"
    MESSAGE_COMPLETE = "message_complete"
    ERROR = "error"


class StreamingEvent(BaseModel):
    """Base class for streaming events."""
    
    event: EventType = Field(
        description="Type of event"
    )
    thread_id: str = Field(
        description="Thread ID this event belongs to"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred"
    )
    
    def to_sse_format(self) -> str:
        """Convert to SSE format string."""
        data = self.model_dump_json()
        return f"data: {data}\n\n"
```

**Event Subtypes**:

```python
class TokenEvent(StreamingEvent):
    """A token from the LLM response."""
    event: EventType = EventType.TOKEN
    token: str = Field(description="The token text")


class ToolStartEvent(StreamingEvent):
    """Tool execution starting."""
    event: EventType = EventType.TOOL_START
    tool_name: str
    arguments: dict[str, Any]


class ToolEndEvent(StreamingEvent):
    """Tool execution completed."""
    event: EventType = EventType.TOOL_END
    tool_name: str
    result: Any
    execution_time_ms: float


class ToolExecutionRequestEvent(StreamingEvent):
    """Request client to execute a tool."""
    event: EventType = EventType.TOOL_EXECUTION_REQUEST
    execution_id: str = Field(description="Unique ID for this execution")
    tool_name: str
    arguments: dict[str, Any]


class ToolExecutionCompleteEvent(StreamingEvent):
    """Client tool execution completed."""
    event: EventType = EventType.TOOL_EXECUTION_COMPLETE
    execution_id: str


class MessageCompleteEvent(StreamingEvent):
    """Message generation completed."""
    event: EventType = EventType.MESSAGE_COMPLETE
    message: ChatMessage


class ErrorEvent(StreamingEvent):
    """An error occurred."""
    event: EventType = EventType.ERROR
    error_type: str = Field(description="Type of error (validation, timeout, llm, etc.)")
    error_message: str = Field(description="Human-readable error message")
    recoverable: bool = Field(description="Whether the client should retry")
```

**Validation Rules**:
- All events must have valid `event` type
- All events must have valid `thread_id` (UUID format)
- Timestamps must be valid datetime objects
- Event-specific fields must be present and valid

**Serialization**:
- Events serialized to JSON for SSE transmission
- Format: `data: {json}\n\n`
- Multiple events can be sent in sequence

---

### 7. ChatRequest

**Purpose**: Request body for /chat endpoint

**Fields**:
```python
class ChatRequest(BaseModel):
    """Request to send a message to the agent."""
    
    message: str = Field(
        min_length=1,
        max_length=10000,
        description="User message to send to the agent"
    )
    thread_id: str | None = Field(
        default=None,
        description="Thread ID to continue conversation (None for new thread)"
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream the response (True) or wait for completion"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata for the request"
    )
```

**Validation Rules**:
- `message` must not be empty and not exceed 10,000 characters
- `thread_id` must be valid UUID format if provided
- `stream` must be boolean
- Server generates new UUID if `thread_id` is None

---

### 8. ToolExecutionResult

**Purpose**: Result from client tool execution sent back to server

**Fields**:
```python
class ToolExecutionResult(BaseModel):
    """Result from client tool execution."""
    
    execution_id: str = Field(
        description="ID from the tool execution request"
    )
    result: Any | None = Field(
        default=None,
        description="Result from the tool (None if error)"
    )
    error: str | None = Field(
        default=None,
        description="Error message if execution failed"
    )
    execution_time_ms: float = Field(
        ge=0,
        description="Time taken to execute on client"
    )
```

**Validation Rules**:
- `execution_id` must match a pending tool execution request
- Either `result` or `error` must be set, not both
- `execution_time_ms` must be non-negative

---

### 9. HealthResponse

**Purpose**: Response from /health endpoint

**Fields**:
```python
class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(
        default="healthy",
        description="Health status"
    )
    version: str = Field(
        description="Server version"
    )
    thread_count: int = Field(
        ge=0,
        description="Number of active conversation threads"
    )
    uptime_seconds: float = Field(
        ge=0,
        description="Server uptime in seconds"
    )
```

---

## Relationships Diagram

```
AGUIServerConfig
    ├─ contains → LLMConfig (1:1)
    └─ references → ToolDefinition (1:N) [server_tools]

ConversationThread (aggregate root)
    └─ contains → ChatMessage (1:N) [message_history]
                     └─ contains → ToolCall (1:N) [tool_calls]

ToolDefinition
    ├─ referenced by → ToolCall [by name]
    └─ references → ToolParameter (1:N) [parameters]

StreamingEvent (abstract)
    ├─ TokenEvent
    ├─ ToolStartEvent
    ├─ ToolEndEvent
    ├─ ToolExecutionRequestEvent
    ├─ ToolExecutionCompleteEvent
    ├─ MessageCompleteEvent
    └─ ErrorEvent

ChatRequest → creates → ConversationThread (if thread_id is None)
ToolExecutionResult → completes → ToolCall
```

---

## State Management

### Thread Lifecycle

```
[None] 
  │
  │ POST /chat (thread_id=None)
  ↓
[Created: thread_id=UUID, message_history=[], created_at=now]
  │
  │ POST /chat (thread_id=UUID, message="...")
  ↓
[Active: message_history=[user_msg], updated_at=now]
  │
  │ Agent processes, tools execute
  ↓
[Active: message_history=[user_msg, assistant_msg], updated_at=now]
  │
  │ GET /threads/{thread_id}
  ↓
[Active: returns thread data]
  │
  │ (Future: DELETE /threads/{thread_id})
  ↓
[Archived: removed from active storage]
```

### Message State

```
[User Creates Message] → [Added to Thread History]
                              ↓
                         [Agent Processes]
                              ↓
                    [Tool Execution (optional)]
                              ↓
                     [Response Generated]
                              ↓
                   [Assistant Message Added]
```

### Tool Execution State

**Server Tool**:
```
[Tool Call Requested by Agent]
    ↓
[ToolStartEvent emitted]
    ↓
[Tool Function Executed (server process)]
    ↓
[ToolEndEvent emitted with result]
    ↓
[Result available to Agent]
```

**Client Tool**:
```
[Tool Call Requested by Agent]
    ↓
[ToolExecutionRequestEvent emitted to client]
    ↓
[Client Receives Request]
    ↓
[Client Executes Tool (client process)]
    ↓
[Client POSTs ToolExecutionResult to server]
    ↓
[Server Receives Result]
    ↓
[ToolExecutionCompleteEvent emitted]
    ↓
[Result available to Agent]
```

---

## Validation Strategy

### Input Validation (API Boundary)

All request models use Pydantic validation:
- Type checking (str, int, bool, etc.)
- Range validation (min/max length, value ranges)
- Pattern matching (regex for UUIDs, identifiers)
- Required field enforcement
- Custom validators for complex rules

### Business Logic Validation

Additional validation in service layer:
- Thread ID must exist for non-creation requests
- Tool names must be registered
- Token limits enforced for conversation history
- Timeout limits enforced for tool execution

### Output Validation

Response models ensure:
- All required fields present
- Correct types
- Valid enum values
- Proper serialization format (JSON, SSE)

---

## Performance Considerations

### Memory Usage

- **Per Thread**: ~10KB base + ~1KB per message
- **100 threads, 50 messages each**: ~5.1MB total
- **History pruning**: Automatic when exceeding `max_messages_per_thread`

### Token Management

- Estimate: 4 characters per token
- Track per thread to stay within LLM context limits
- Truncate oldest messages when approaching limit

### Concurrency

- Thread-safe storage with `threading.Lock`
- Each request processes independently
- No blocking operations in critical sections
- Async/await for I/O-bound operations (LLM calls, HTTP)

---

## Summary

This data model provides:

✅ **Type Safety**: All entities use Pydantic for runtime validation  
✅ **Clear Relationships**: Explicit composition and reference relationships  
✅ **State Tracking**: Well-defined state transitions and lifecycle  
✅ **Validation**: Multi-layer validation (input, business logic, output)  
✅ **Performance**: Efficient memory usage with pruning strategies  
✅ **Extensibility**: Easy to add new event types, tool types, metadata

**Next Steps**: Create API contracts in `contracts/` directory

---

**Data Model Complete**: 2026-01-13  
**Next**: API Contracts (OpenAPI and Tools specifications)
