// AG-UI client service for HTTP requests
import { logger } from '../utils/logger';
import { getApiBaseUrl } from '../config/api';
import { processSSEStream } from '../utils/sseProcessor';
import { generateUUID } from '../utils/uuid';
import type { ModelProvider } from '../types/modelProvider';

// Simple event interface for streaming events
export interface StreamEvent {
  type: string;
  delta?: string;
  message?: string;
  threadId?: string;
  [key: string]: unknown;
}

export interface AGUIMessage {
  id?: string;
  role: string;
  content: string;
}

export interface ChatRequest {
  messages: AGUIMessage[];
  thread_id?: string | null;
  stream: boolean;
}

export interface ChatResponse {
  thread_id: string;
  message?: string;
}

class AGUIClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || getApiBaseUrl();
    logger.info('AGUIClient initialized', { baseUrl: this.baseUrl });
  }

  private buildUrl(path: string): string {
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    if (this.baseUrl.startsWith('http://') || this.baseUrl.startsWith('https://')) {
      return new URL(cleanPath, this.baseUrl).toString();
    }
    return `${this.baseUrl.replace(/\/$/, '')}${cleanPath}`;
  }

  /**
   * Send a chat message to the backend.
   *
   * The full conversation history is forwarded to the AG-UI server so that
   * the Microsoft Agent Framework `AgentThread` built by the default
   * orchestrator (see `agent_framework_ag_ui._orchestrators`) has access to
   * every prior turn — this is what enables multi-turn conversation.
   */
  async sendMessage(
    messages: AGUIMessage[],
    threadId?: string | null,
    onEvent?: (event: StreamEvent) => void,
    attachments?: Array<{
      blobName: string;
      originalFilename: string;
      contentType: string;
      sizeBytes: number;
    }>,
    modelProvider: ModelProvider = 'github-copilot'
  ): Promise<ChatResponse> {
    const correlationId = logger.generateCorrelationId();
    logger.setCorrelationId(correlationId);

    logger.info('Sending chat message', {
      messageCount: messages.length,
      threadId: threadId || 'new',
      modelProvider,
    });

    const request: ChatRequest & { attachments?: Array<Record<string, unknown>> } = {
      messages,
      thread_id: threadId,
      stream: true,
    };

    if (attachments && attachments.length > 0) {
      request.attachments = attachments.map((a) => ({
        blob_name: a.blobName,
        original_filename: a.originalFilename,
        content_type: a.contentType,
        size_bytes: a.sizeBytes,
      }));
    }

    try {
      const endpoint = modelProvider === 'foundry' ? '/v1/byok/foundry' : '/';
      const response = await fetch(this.buildUrl(endpoint), {
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
        // Track RUN_FINISHED so we can detect a protocol violation when the
        // stream closes without signalling normal completion.
        let runFinished = false;
        const wrappedOnEvent = (event: StreamEvent) => {
          if (event.type === 'RUN_FINISHED') {
            runFinished = true;
          }
          onEvent(event);
        };

        try {
          await processSSEStream(response, wrappedOnEvent);
          // AG-UI protocol requires RUN_FINISHED to signal normal completion.
          // If the stream closed without it, treat this as an error so the
          // ERROR handler in the caller can reset streaming state properly.
          if (!runFinished) {
            onEvent({ type: 'ERROR', message: 'Stream ended without RUN_FINISHED event' });
          }
        } catch (error) {
          logger.error('Stream processing failed', error);
          onEvent({
            type: 'ERROR',
            message: error instanceof Error ? error.message : 'Stream processing failed',
          });
        }

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

  async abortThread(threadId: string): Promise<void> {
    logger.info('Aborting chat generation', { threadId });

    const response = await fetch(`${this.baseUrl}/v1/threads/${encodeURIComponent(threadId)}/abort`, {
      method: 'POST',
    });

    if (!response.ok) {
      const errorText = await response.text();
      logger.error('Abort request failed', new Error(errorText), {
        status: response.status,
        threadId,
      });
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
  }
}

// Export singleton instance
export const aguiClient = new AGUIClient();
