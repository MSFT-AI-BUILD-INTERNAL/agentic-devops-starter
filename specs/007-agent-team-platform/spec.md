# Feature Specification: Agent Team Platform

**Feature ID**: 007-agent-team-platform  
**Date**: 2026-05-13  
**Status**: Implementation

## Overview

Transform the single-agent AI Chatbot into an **Agent Team Platform** where
users select a multi-agent collaboration pattern from a dropdown, and a team
of specialized agents executes the pattern collaboratively via the GitHub
Copilot SDK. Results are streamed back in real-time via SSE.

**Reference**: https://github.com/MSFT-AI-BUILD-INTERNAL/agentic-squad
(conceptual patterns only — no CLI/Squad tooling reuse)

## Patterns

### 1. Debate & Critic
**Purpose**: Best-option selection via adversarial argument.  
**Roles**: Proposer → Opponent → Critic → Synthesizer → Scribe  
**Flow**: Sequential rounds (max 3). Each round: Proposer argues → Opponent
counters → Critic evaluates → Synthesizer judges convergence. Scribe
documents final conclusion.

### 2. Generator & Evaluator
**Purpose**: Quality-threshold artifact production.  
**Roles**: Generator → Evaluator → Refiner → Scribe  
**Flow**: Feedback loop (max 3 cycles). Generator drafts → Evaluator scores
Pass/Fail → Fail: Refiner improves → re-evaluate. Scribe documents result.

### 3. Leadership Discussion
**Purpose**: Multi-domain strategic decision-making.  
**Roles**: CEO, CTO, CISO, CFO, CPO, Chief of Staff  
**Flow**: CEO sets agenda → 4 C-level briefings **in parallel** (Fleet) →
CEO cross-review → CEO decision → Chief of Staff documents.

### 4. Planner & Executor
**Purpose**: Systematic complex task execution.  
**Roles**: Planner → Executor → Validator → Scribe  
**Flow**: Planner creates task list → per-task: Executor implements →
Validator checks (Pass/Revise, max 3 revisions) → Scribe documents.

### 5. Research & Report
**Purpose**: Trusted knowledge synthesis.  
**Roles**: Researcher → Reasoner → Reporter  
**Flow**: Researcher investigates → Reasoner fact-checks (Pass/Revise loop,
max 3 rounds) → Reporter produces structured report.

## API Contract

### `GET /v1/patterns`
Returns available pattern definitions.
```json
[
  {
    "id": "debate-critic",
    "name": "Debate & Critic",
    "description": "...",
    "roles": ["Proposer", "Opponent", "Critic", "Synthesizer", "Scribe"]
  }
]
```

### `POST /v1/squad/stream`
Executes a pattern with SSE streaming.

**Request:**
```json
{
  "pattern_id": "debate-critic",
  "prompt": "REST API vs GraphQL — which should we use?",
  "max_rounds": 3
}
```

**SSE Events:**
| Event Type | Payload | Description |
|---|---|---|
| `SQUAD_STARTED` | `{pattern_id, run_id}` | Pattern execution begins |
| `AGENT_STARTED` | `{agent_role, round}` | An agent begins its turn |
| `AGENT_MESSAGE_DELTA` | `{agent_role, delta}` | Streaming token from agent |
| `AGENT_MESSAGE_END` | `{agent_role, content}` | Agent finished speaking |
| `ROUND_COMPLETED` | `{round, converged}` | Round finished |
| `SQUAD_FINISHED` | `{run_id, summary}` | Pattern execution complete |
| `SQUAD_ERROR` | `{message}` | Error occurred |

## Architecture

### Backend
```
src/
├── patterns.py      # Pattern definitions (roles, system prompts, flow type)
├── orchestrator.py   # Multi-agent orchestration engine (yields SSE events)
├── routes.py         # + GET /v1/patterns, POST /v1/squad/stream
└── models.py         # + SquadRequest, PatternInfo, AgentEvent models
```

### Frontend
```
src/
├── components/
│   ├── PatternSelector.tsx   # Dropdown for pattern selection
│   └── AgentMessage.tsx      # Agent message bubble with role badge
├── hooks/
│   └── useSquad.ts           # SSE hook for squad streaming
├── stores/
│   └── chatStore.ts          # + pattern state, agent messages
└── types/
    └── squad.ts              # Pattern/agent type definitions
```

### Orchestration Engine
Each agent role = one Copilot SDK session with a role-specific system prompt.
The orchestrator manages flow between agents, passing prior agent outputs as
context to the next agent.

- **Sequential patterns** (Debate, GenEval, Planner, Research): agents run
  one at a time, each seeing prior outputs.
- **Parallel phase** (Leadership Phase 2): 4 C-level briefings run via
  `asyncio.gather()` with semaphore, all results collected before Phase 3.
- **Convergence**: Synthesizer/Evaluator/Validator output is parsed for
  CONVERGED/PASS signals. If not found after max rounds, terminates gracefully.

## Key Design Decisions

1. **No Squad CLI**: Use only the Copilot SDK directly; no external tooling.
2. **SSE streaming for squad**: Unlike the current async `/v1/fleet` endpoint,
   the squad endpoint streams agent-by-agent output in real-time.
3. **Existing `/v1/fleet` preserved**: The raw parallel-call fleet API remains
   available for programmatic use. Squad is a higher-level orchestrated API.
4. **Pattern selection via dropdown**: Not a separate page — integrated into
   the existing chat UI with a mode toggle.
5. **Agent role labels**: Each message bubble shows which agent role produced
   it (e.g., "🗣️ Proposer", "⚔️ Opponent", "📝 Scribe").
