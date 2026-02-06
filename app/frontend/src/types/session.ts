// Thread/Session entity types
import type { Message } from './message';
import type { ValidationResult } from './common';

export type ThreadStatus = 'active' | 'idle' | 'error';

export interface ThreadMetadata {
  title?: string;
  messageCount?: number;
  lastError?: string;
  tags?: string[];
}

export interface Thread {
  id: string;
  createdAt: Date;
  updatedAt: Date;
  messages: Message[];
  status: ThreadStatus;
  metadata?: ThreadMetadata;
}

/**
 * Validates a thread object
 */
export function validateThread(thread: Thread): ValidationResult {
  const errors: string[] = [];

  if (thread.updatedAt < thread.createdAt) {
    errors.push('Thread updatedAt cannot be before createdAt');
  }

  if (thread.messages.length > 50) {
    errors.push('Thread exceeds maximum message count (50)');
  }

  // Ensure messages are ordered by timestamp
  const isOrdered = thread.messages.every(
    (msg, i) => i === 0 || msg.timestamp >= thread.messages[i - 1].timestamp
  );

  if (!isOrdered) {
    errors.push('Thread messages must be ordered by timestamp');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
