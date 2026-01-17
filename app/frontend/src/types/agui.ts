// AG-UI Protocol event types and definitions

// Connection status
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

// Tool Call types
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

// Streaming state
export interface StreamingState {
  isStreaming: boolean;
  currentMessageId?: string;
  buffer: string;
  startedAt?: Date;
  tokenCount: number;
}

// AG-UI Event types
export type AGUIEventType =
  | 'token'
  | 'tool_start'
  | 'tool_end'
  | 'tool_execution_request'
  | 'tool_execution_complete'
  | 'message_complete'
  | 'error';

export interface AGUIEvent {
  event: AGUIEventType;
  threadId: string;
  timestamp: string;
  data?: unknown;
}

// Specific event types
export interface TokenEvent extends AGUIEvent {
  event: 'token';
  data: {
    token: string;
  };
}

export interface ToolStartEvent extends AGUIEvent {
  event: 'tool_start';
  data: {
    toolName: string;
    arguments: Record<string, unknown>;
  };
}

export interface ToolEndEvent extends AGUIEvent {
  event: 'tool_end';
  data: {
    toolName: string;
    result: unknown;
    executionTimeMs: number;
  };
}

export interface ToolExecutionRequestEvent extends AGUIEvent {
  event: 'tool_execution_request';
  data: {
    executionId: string;
    toolName: string;
    arguments: Record<string, unknown>;
  };
}

export interface ToolExecutionCompleteEvent extends AGUIEvent {
  event: 'tool_execution_complete';
  data: {
    executionId: string;
  };
}

export interface MessageCompleteEvent extends AGUIEvent {
  event: 'message_complete';
  data?: undefined;
}

export interface ErrorEvent extends AGUIEvent {
  event: 'error';
  data: {
    errorType: 'validation' | 'timeout' | 'llm' | 'tool_error' | 'connection';
    errorMessage: string;
    recoverable: boolean;
  };
}

export type AGUIEventUnion =
  | TokenEvent
  | ToolStartEvent
  | ToolEndEvent
  | ToolExecutionRequestEvent
  | ToolExecutionCompleteEvent
  | MessageCompleteEvent
  | ErrorEvent;

// Type guards
export function isTokenEvent(event: AGUIEvent): event is TokenEvent {
  return event.event === 'token';
}

export function isToolStartEvent(event: AGUIEvent): event is ToolStartEvent {
  return event.event === 'tool_start';
}

export function isToolEndEvent(event: AGUIEvent): event is ToolEndEvent {
  return event.event === 'tool_end';
}

export function isToolExecutionRequestEvent(
  event: AGUIEvent
): event is ToolExecutionRequestEvent {
  return event.event === 'tool_execution_request';
}

export function isToolExecutionCompleteEvent(
  event: AGUIEvent
): event is ToolExecutionCompleteEvent {
  return event.event === 'tool_execution_complete';
}

export function isMessageCompleteEvent(event: AGUIEvent): event is MessageCompleteEvent {
  return event.event === 'message_complete';
}

export function isErrorEvent(event: AGUIEvent): event is ErrorEvent {
  return event.event === 'error';
}
