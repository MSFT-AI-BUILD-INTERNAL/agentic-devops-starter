// AG-UI client service for HTTP requests
import { logger } from '../utils/logger';
import { getApiBaseUrl } from '../config/api';
import { processSSEStream } from '../utils/sseProcessor';
import { generateUUID } from '../utils/uuid';

// Simple event interface for streaming events
export interface StreamEvent {
  type: string;
  delta?: string;
  message?: string;
  threadId?: string;
  [key: string]: unknown;
}

export interface ChatRequest {
  messages: Array<{ role: string; content: string }>;
  thread_id?: string | null;
  stream: boolean;
}

export interface ChatResponse {
  thread_id: string;
  message?: string;
}

export interface ToolResultRequest {
  execution_id: string;
  result?: unknown;
  error?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  thread_count: number;
  uptime_seconds: number;
}

export interface ThreadMetadata {
  thread_id: string;
  created_at: string;
  message_count: number;
}

class AGUIClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || getApiBaseUrl();
    logger.info('AGUIClient initialized', { baseUrl: this.baseUrl });
  }

  /**
   * Send a chat message to the backend
   */
  async sendMessage(
    message: string,
    threadId?: string | null,
    onEvent?: (event: StreamEvent) => void
  ): Promise<ChatResponse> {
    const correlationId = logger.generateCorrelationId();
    logger.setCorrelationId(correlationId);

    logger.info('Sending chat message', {
      messageLength: message.length,
      threadId: threadId || 'new',
    });

    const request: ChatRequest = {
      messages: [{ role: 'user', content: message }],
      thread_id: threadId,
      stream: true,
    };

    try {
      const response = await fetch(`${this.baseUrl}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Correlation-ID': correlationId,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.error('Chat request failed', new Error(errorText), {
          status: response.status,
        });
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      // Handle SSE stream from response body
      if (response.body && onEvent) {
        // Process stream in background with proper cleanup
        const processStream = async () => {
          try {
            // Note: threadIdFromStream is returned but not used here since we return immediately
            // The threadId is passed to the event handler if present in the stream
            const threadIdFromStream = await processSSEStream(response, onEvent);
            return threadIdFromStream;
          } catch (error) {
            logger.error('Stream processing failed', error);
            throw error;
          }
        };

        // Start stream processing without blocking
        processStream().catch((err) => {
          logger.error('Stream processing failed', err);
        });

        // Return immediately with thread_id (stream processing continues in background)
        // If no threadId provided, generate a new one - stream may provide one later via events
        return { thread_id: threadId || generateUUID() };
      }

      // Fallback for non-streaming
      const data = await response.json();
      logger.info('Chat message sent successfully', { threadId: data.thread_id });

      return data;
    } catch (error) {
      logger.error('Failed to send message', error);
      throw error;
    } finally {
      logger.clearCorrelationId();
    }
  }

  /**
   * Submit client-side tool execution result
   */
  async submitToolResult(executionId: string, result?: unknown, error?: string): Promise<void> {
    const correlationId = logger.generateCorrelationId();
    logger.setCorrelationId(correlationId);

    logger.info('Submitting tool result', { executionId, hasError: !!error });

    const request: ToolResultRequest = {
      execution_id: executionId,
      result,
      error,
    };

    try {
      const response = await fetch(`${this.baseUrl}/tool_result`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Correlation-ID': correlationId,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.error('Tool result submission failed', new Error(errorText), {
          status: response.status,
        });
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      logger.info('Tool result submitted successfully');
    } catch (error) {
      logger.error('Failed to submit tool result', error);
      throw error;
    } finally {
      logger.clearCorrelationId();
    }
  }

  /**
   * Check backend health
   */
  async checkHealth(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      logger.error('Health check failed', error);
      throw error;
    }
  }

  /**
   * List all threads
   */
  async listThreads(): Promise<ThreadMetadata[]> {
    try {
      const response = await fetch(`${this.baseUrl}/threads`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      logger.error('Failed to list threads', error);
      throw error;
    }
  }

  /**
   * Get thread by ID
   */
  async getThread(threadId: string): Promise<unknown> {
    try {
      const response = await fetch(`${this.baseUrl}/threads/${threadId}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      logger.error('Failed to get thread', error, { threadId });
      throw error;
    }
  }
}

// Export singleton instance
export const aguiClient = new AGUIClient();
