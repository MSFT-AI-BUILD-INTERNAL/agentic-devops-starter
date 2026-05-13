// Utility for processing Server-Sent Events (SSE) from fetch responses
import { logger } from '../utils/logger';
import type { StreamEvent } from '../services/aguiClient';

/**
 * Process SSE stream from a Response body
 * Returns a promise that resolves when the stream is complete
 */
export async function processSSEStream(
  response: Response,
  onEvent: (event: StreamEvent) => void
): Promise<string | undefined> {
  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let threadIdFromStream: string | undefined;

  try {
    let done = false;
    while (!done) {
      const result = await reader.read();
      done = result.done;
      const value = result.value;

      if (done) {
        logger.info('Stream reading completed');
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data.trim()) {
            try {
              const event = JSON.parse(data) as StreamEvent;
              if (event.threadId && !threadIdFromStream) {
                threadIdFromStream = event.threadId;
              }
              onEvent(event);
            } catch (e) {
              logger.error('Failed to parse SSE event', e);
            }
          }
        }
      }
    }
  } catch (error) {
    logger.error('Stream reading error', error);
    throw error;
  } finally {
    // Ensure reader is properly released
    try {
      reader.releaseLock();
    } catch (e) {
      // Reader may already be released, ignore error
    }
  }

  return threadIdFromStream;
}
