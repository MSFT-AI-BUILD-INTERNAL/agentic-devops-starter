# Implementation Plan: Agent Framework Integration

**Branch**: `copilot/create-agent-framework-example-again` | **Date**: 2025-12-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-agent-framework/spec.md`

**Note**: This is a retroactive implementation plan documenting the completed agent framework integration feature.

## Summary

Create a comprehensive agent framework integration example demonstrating the use of microsoft-agent-framework for building conversational AI agents. The implementation provides a complete reference architecture with base agent primitives, conversational agent implementation, LLM configuration, structured logging, tool integration, and comprehensive testing—all following constitutional requirements for Python-first backend, type safety, and observability.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: agent-framework (microsoft-agent-framework), pydantic ≥2.0.0  
**Storage**: N/A (in-memory conversation state for this example)  
**Testing**: pytest ≥8.0.0 with 25 comprehensive tests  
**Target Platform**: Python 3.12+ runtime environment  
**Project Type**: Single project with `app/` directory structure  
**Performance Goals**: Efficient conversation processing with structured logging overhead  
**Constraints**: Type-safe implementation, mypy strict mode, ruff linting compliance  
**Scale/Scope**: Reference implementation for building production-ready conversational agents

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Python-First Backend ✓
- **Requirement**: Python ≥3.12
- **Implementation**: pyproject.toml specifies `requires-python = ">=3.12"`
- **Status**: PASS

### II. Agent-Centric Architecture ✓
- **Requirement**: microsoft-agent-framework as core orchestration layer
- **Implementation**: 
  - `agent-framework` listed in dependencies
  - BaseAgent abstract class implements agent primitives
  - ConversationalAgent provides concrete implementation
  - AgentState model for conversation tracking
- **Status**: PASS

### III. Type Safety ✓
- **Requirement**: Type hints on all code, Pydantic for validation, mypy checks
- **Implementation**:
  - All functions and methods include type hints
  - Pydantic models for AgentState, LLMConfig
  - mypy configured with `disallow_untyped_defs = true`
  - mypy checks pass with no errors
- **Status**: PASS

### IV. Response Quality ✓
- **Requirement**: Response validation, guardrails, LLM interaction logging
- **Implementation**:
  - `validate_response()` abstract method in BaseAgent
  - `_check_harmful_content()` method for content filtering
  - `log_llm_interaction()` utility for audit trail
  - Response validation hooks in message processing pipeline
- **Status**: PASS

### V. Observability ✓
- **Requirement**: Structured logging with correlation IDs
- **Implementation**:
  - `logging_utils.py` module with CorrelationIdFilter
  - Context-aware correlation ID tracking using ContextVar
  - Structured logging throughout all agent operations
  - `log_llm_interaction()` for LLM call traceability
- **Status**: PASS

### VI. Project Structure ✓
- **Requirement**: All application code in `app/` directory
- **Implementation**: Complete implementation in `app/src/` with proper module structure
- **Status**: PASS

**Constitution Check Result**: ✓ ALL GATES PASSED

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-framework/
├── spec.md              # Feature specification (complete)
└── plan.md              # This implementation plan (retroactive)
```

### Source Code (repository root)

```text
app/
├── src/
│   ├── __init__.py
│   ├── logging_utils.py          # Structured logging with correlation IDs
│   ├── config/
│   │   ├── __init__.py
│   │   └── llm_config.py         # LLM provider configuration (OpenAI, Azure)
│   └── agents/
│       ├── __init__.py
│       ├── base_agent.py         # BaseAgent abstract class with AgentState
│       ├── conversational_agent.py  # ConversationalAgent implementation
│       └── tools.py              # Tool integration framework (Calculator, Weather)
├── tests/
│   ├── __init__.py
│   ├── test_agent.py             # Agent behavior tests
│   ├── test_config.py            # Configuration validation tests
│   └── test_tools.py             # Tool execution tests
├── main.py                       # Example demonstrations
├── README.md                     # Comprehensive documentation
└── pyproject.toml               # Dependencies and tool configuration
```

**Structure Decision**: Single project structure in `app/` directory per constitution requirements. This aligns with the constitutional mandate that "All application code must reside in the `app/` directory." The modular organization separates concerns into config, agents, and logging utilities for maintainability.

## Technical Architecture

### Phase 0: Research & Technology Selection (COMPLETED)

**Decisions Made:**

1. **Agent Framework Integration**
   - Decision: Use abstract base class pattern with agent-framework primitives
   - Rationale: Provides flexibility for multiple agent types while ensuring consistent behavior
   - Implementation: `BaseAgent` with `AgentState` Pydantic model

2. **State Management**
   - Decision: Pydantic models for conversation state
   - Rationale: Type-safe serialization and validation per constitution
   - Implementation: `AgentState` with conversation_id, message_count, context, history

3. **Logging Approach**
   - Decision: ContextVar-based correlation ID tracking
   - Rationale: Thread-safe and async-compatible for future scalability
   - Implementation: `correlation_id_var` ContextVar with CorrelationIdFilter

4. **LLM Configuration**
   - Decision: Provider-agnostic configuration with fallback support
   - Rationale: Constitutional requirement for "multiple LLM providers with fallback"
   - Implementation: `LLMConfig` with LLMProvider enum (OpenAI, Azure OpenAI)

5. **Tool Integration**
   - Decision: Abstract Tool base class with parameter schemas
   - Rationale: Extensible framework for agent capabilities beyond text generation
   - Implementation: `Tool` ABC with `get_definition()` and `execute()` methods

### Phase 1: Design & Implementation (COMPLETED)

#### Data Model (`data-model.md` equivalent)

**Core Entities:**

1. **AgentState**
   - Fields: `conversation_id` (str), `message_count` (int), `context` (dict), `history` (list)
   - Validation: Pydantic model with Field descriptions
   - Relationships: Owned by BaseAgent instance

2. **LLMConfig**
   - Fields: `provider`, `api_key`, `model`, `temperature`, `max_tokens`
   - Azure-specific: `azure_endpoint`, `azure_deployment`, `azure_api_version`
   - Fallback: `fallback_provider`, `fallback_config`
   - Validation: Pydantic with constraints (temperature: 0.0-2.0, max_tokens > 0)

3. **Tool Definition**
   - Fields: `name`, `description`, `parameters` (JSON schema)
   - Execution: Abstract `execute()` method returning dict

**State Transitions:**
- Agent initialization → Empty AgentState created
- Message processing → message_count incremented, history appended
- Tool execution → Context updated with tool results

#### API Contracts (Implementation Interfaces)

**BaseAgent Interface:**
```python
class BaseAgent(ABC):
    def __init__(name: str, llm_config: LLMConfig, system_prompt: str | None)
    @abstractmethod
    def process_message(message: str) -> str
    @abstractmethod
    def validate_response(response: str) -> bool
    def get_state() -> AgentState
    def get_conversation_summary() -> dict[str, Any]
```

**ConversationalAgent Interface:**
```python
class ConversationalAgent(BaseAgent):
    def process_message(message: str) -> str
    def validate_response(response: str) -> bool
    def _check_harmful_content(text: str) -> bool
    def _call_llm(messages: list[dict[str, str]]) -> str
```

**Tool Interface:**
```python
class Tool(ABC):
    @abstractmethod
    def get_definition() -> dict[str, Any]
    @abstractmethod
    def execute(**kwargs) -> dict[str, Any]
```

#### Component Design

**1. Logging Infrastructure** (`src/logging_utils.py`)
- CorrelationIdFilter: Injects correlation_id into all log records
- get_correlation_id(): Retrieves or generates correlation ID
- set_correlation_id(): Sets correlation ID for context
- setup_logging(): Configures structured logging
- log_llm_interaction(): Logs LLM calls with correlation tracking

**2. Configuration Layer** (`src/config/llm_config.py`)
- LLMProvider enum: OPENAI, AZURE_OPENAI
- LLMConfig model: Provider configuration with validation
- Environment variable support: OPENAI_API_KEY, AZURE_OPENAI_*
- Fallback configuration: Secondary provider for reliability
- Token tracking: enable_token_tracking flag

**3. Agent Framework** (`src/agents/`)
- BaseAgent: Abstract foundation with state management
- ConversationalAgent: Concrete implementation with message pipeline
- Response validation: Content filtering and guardrails
- Tool integration: Tool registration and execution

**4. Tool System** (`src/agents/tools.py`)
- Tool ABC: Base class for all tools
- CalculatorTool: Arithmetic operations with parameter validation
- WeatherTool: Mock API integration example
- Extensible: Easy to add new tools

### Phase 2: Testing & Quality Assurance (COMPLETED)

**Test Coverage: 25 Tests Implemented**

1. **Configuration Tests** (`tests/test_config.py`)
   - LLMConfig validation
   - Provider enum validation
   - Environment variable integration
   - Fallback configuration
   - Parameter constraints

2. **Agent Tests** (`tests/test_agent.py`)
   - BaseAgent instantiation
   - State management
   - Message processing pipeline
   - Response validation
   - Conversation history tracking
   - Harmful content detection
   - Conversation summary generation

3. **Tool Tests** (`tests/test_tools.py`)
   - Tool definition schema
   - Calculator operations (add, subtract, multiply, divide)
   - Weather tool integration
   - Parameter validation
   - Error handling

**Quality Gates: ALL PASSING**
- ✓ Ruff linting: No violations
- ✓ Mypy type checking: No errors (strict mode)
- ✓ Pytest: 25 tests passing
- ✓ Code structure: Constitutional compliance verified

### Phase 3: Documentation & Examples (COMPLETED)

**Documentation Artifacts:**

1. **README.md** (`app/README.md`)
   - Overview and features
   - Installation instructions
   - Usage examples with code snippets
   - Configuration guide
   - Development workflow
   - Architecture principles mapping to constitution
   - Extension guide

2. **Example Code** (`app/main.py`)
   - Basic conversation demonstration
   - Tool integration example
   - State management showcase
   - Comprehensive inline documentation

3. **Inline Documentation**
   - Docstrings on all classes and methods
   - Type hints throughout
   - Parameter descriptions in Pydantic models

## Implementation Summary

### What Was Built

**Core Components:**
1. Agent framework with BaseAgent and ConversationalAgent
2. State management using Pydantic models
3. LLM configuration with multi-provider support
4. Structured logging with correlation IDs
5. Tool integration framework
6. Comprehensive test suite (25 tests)
7. Example code and documentation

**Constitutional Compliance:**
- ✓ Python ≥3.12
- ✓ microsoft-agent-framework integration
- ✓ Type safety with Pydantic and mypy
- ✓ Response validation and guardrails
- ✓ Structured logging with correlation IDs
- ✓ All code in `app/` directory

**Quality Metrics:**
- 25 tests implemented and passing
- 0 ruff linting violations
- 0 mypy type errors
- 100% constitutional compliance
- Comprehensive documentation

### Technical Highlights

1. **Modular Architecture**: Clean separation between config, agents, and utilities
2. **Type Safety**: Strict mypy configuration with no type violations
3. **Observability**: Context-aware correlation ID tracking throughout
4. **Extensibility**: Abstract base classes for agents and tools
5. **Validation**: Pydantic models with field constraints
6. **Testing**: Comprehensive unit tests covering all components

### Future Enhancement Opportunities

While the current implementation is complete and constitutional, potential future enhancements could include:

1. **Real LLM Integration**: Replace mock implementation with actual API calls
2. **Persistent Storage**: Add database backend for conversation history
3. **Advanced Tools**: Web search, API integration, file operations
4. **Streaming Responses**: Support for LLM streaming APIs
5. **Multi-Agent Orchestration**: Coordination between multiple agents
6. **Performance Monitoring**: Metrics collection and dashboards

## Conclusion

This implementation plan documents a complete, constitutional-compliant agent framework integration. All user stories from the specification have been implemented, tested, and documented. The codebase demonstrates best practices for building conversational AI agents with Python 3.12, microsoft-agent-framework, type safety, and structured logging.

The retroactive nature of this plan reflects the reality that implementation preceded formal planning, but all constitutional requirements were followed, and the resulting architecture aligns with Speckit's recommended workflow for future features.
