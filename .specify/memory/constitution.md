# LLM-Based Chatbot Constitution

## Core Principles

### I. Python-First Backend
All backend services must be implemented in Python (≥3.12). The microsoft-agent-framework is the mandatory foundation for building conversational agents and handling LLM interactions.

### II. Agent-Centric Architecture
Use microsoft-agent-framework as the core orchestration layer. All conversational logic, state management, and tool integrations must leverage the framework's agent primitives.

### III. Type Safety
All code must include type hints. Use Pydantic for data validation and serialization. Run mypy checks to ensure type correctness.

### IV. Response Quality
LLM responses must be validated before delivery to users. Implement guardrails for harmful content, hallucinations, and off-topic responses. Log all LLM interactions for audit and improvement.

### V. Observability
Structured logging is mandatory. All agent actions, LLM calls, and errors must be traceable. Use correlation IDs to track conversation flows across services.

### VI. Project Structure
All application code must reside in the `app/` directory. All Infrastructure as Code (IaC) must reside in the `infra/` directory. No application logic in infra, no infrastructure code in app.

## Technical Stack Requirements

### Required Technologies
- **Backend**: Python ≥3.12
- **Agent Framework**: microsoft-agent-framework (mandatory)
- **Package Manager**: uv
- **Linting/Formatting**: Ruff
- **Type Checking**: mypy

### LLM Integration
- Support for multiple LLM providers (OpenAI, Azure OpenAI, etc.)
- Graceful fallback mechanisms when primary LLM is unavailable
- Token usage tracking and cost monitoring

## Development Workflow

### Speckit-Driven Development
Use Speckit to define and manage development workflows. All work must be broken down into Plans and Tasks:
- Define Plans for high-level features or epics
- Break down Plans into actionable Tasks
- Execute Tasks using `specify run`
- Track progress and maintain task history
- All Plans and Tasks must be version-controlled in the `.specify/` directory

### Test-First Development
- Write tests before implementation
- Minimum 80% code coverage for agent logic
- Integration tests for end-to-end conversation flows

### Code Quality Gates
- All code must pass Ruff linting
- Type checks must pass (mypy)
- No security vulnerabilities (dependency scanning)
- PR reviews required before merge

## Governance

This constitution defines the minimal principles for building LLM-based chatbots. All implementations must comply with these standards. Deviations require explicit justification and approval.

**Version**: 1.0.0 | **Ratified**: 2025-12-30 | **Last Amended**: 2025-12-30

