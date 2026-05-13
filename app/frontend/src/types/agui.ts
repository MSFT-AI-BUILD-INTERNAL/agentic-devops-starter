// AG-UI Protocol types used by the application

export type ConnectionStatus =
  | 'connected'
  | 'disconnected'
  | 'connecting'
  | 'reconnecting'
  | 'error';

export interface Connection {
  status: ConnectionStatus;
  endpoint: string;
  lastPingAt?: Date;
  reconnectAttempts: number;
  errorMessage?: string;
}

export type ToolCallStatus = 'pending' | 'executing' | 'completed' | 'failed';

export interface ToolCall {
  id: string;
  toolName: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  status: ToolCallStatus;
  executionTimeMs?: number;
  error?: string;
}

export interface StreamingState {
  isStreaming: boolean;
  currentMessageId?: string;
  buffer: string;
  startedAt?: Date;
  tokenCount: number;
}
