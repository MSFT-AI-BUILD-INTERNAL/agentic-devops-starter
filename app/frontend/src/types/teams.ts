// Agent Team types for multi-agent collaboration

export interface PatternInfo {
  id: string;
  name: string;
  description: string;
  roles: string[];
}

export interface TeamsRequest {
  pattern_id: string;
  prompt: string;
  max_rounds?: number;
}

export const ROLE_EMOJIS: Record<string, string> = {
  Proposer: '🗣️',
  Opponent: '⚔️',
  Critic: '🔍',
  Synthesizer: '🧩',
  Scribe: '📝',
  Generator: '🔨',
  Evaluator: '📊',
  Refiner: '✨',
  CEO: '👔',
  CTO: '💻',
  CISO: '🛡️',
  CFO: '💰',
  CPO: '📱',
  'Chief of Staff': '📋',
  Planner: '📐',
  Executor: '⚡',
  Validator: '✅',
  Researcher: '🔬',
  Reasoner: '🧠',
  Reporter: '📰',
};

export type TeamsEventType =
  | 'TEAMS_STARTED'
  | 'AGENT_STARTED'
  | 'AGENT_MESSAGE_DELTA'
  | 'AGENT_MESSAGE_END'
  | 'ROUND_COMPLETED'
  | 'TEAMS_FINISHED'
  | 'TEAMS_ERROR';

export interface TeamsEvent {
  type: TeamsEventType;
  agent_role?: string;
  round?: number;
  delta?: string;
  content?: string;
  pattern_id?: string;
  run_id?: string;
  converged?: boolean;
  summary?: string;
  message?: string;
}

export interface AgentMessage {
  id: string;
  role: string;
  content: string;
  round: number;
  timestamp: Date;
  isComplete: boolean;
}
