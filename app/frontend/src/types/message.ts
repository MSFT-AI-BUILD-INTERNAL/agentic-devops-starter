// Message entity types
export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

export interface MessageMetadata {
  streamingComplete?: boolean;
  errorRecoverable?: boolean;
  executionTimeMs?: number;
  tokenCount?: number;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  threadId: string;
  toolCalls?: import('./agui').ToolCall[];
  metadata?: MessageMetadata;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Validates a message object
 */
export function validateMessage(message: Message): ValidationResult {
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
