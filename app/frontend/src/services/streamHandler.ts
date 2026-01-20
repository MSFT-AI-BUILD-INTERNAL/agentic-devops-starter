// SSE stream handler service
import { logger } from '../utils/logger';
import type { AGUIEvent, AGUIEventUnion } from '../types/agui';

export type EventHandler = (event: AGUIEventUnion) => void;

class StreamHandler {
  private eventSource: EventSource | null = null;
  private handlers: Map<string, EventHandler[]> = new Map();
  private baseUrl: string;

  constructor(baseUrl?: string) {
    // Use provided baseUrl, fallback to env var, or default to /api/ for production
    // IMPORTANT: Trailing slash is required to match nginx 'location /api/' block
    this.baseUrl = baseUrl || import.meta.env.VITE_AGUI_ENDPOINT || '/api/';
    logger.info('StreamHandler initialized', { baseUrl: this.baseUrl });
  }

  /**
   * Register event handler for specific event type
   */
  on(eventType: string, handler: EventHandler): void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType)!.push(handler);
  }

  /**
   * Remove event handler
   */
  off(eventType: string, handler: EventHandler): void {
    const handlers = this.handlers.get(eventType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * Emit event to registered handlers
   */
  private emit(event: AGUIEventUnion): void {
    const handlers = this.handlers.get(event.event) || [];
    const allHandlers = this.handlers.get('*') || [];

    [...handlers, ...allHandlers].forEach((handler) => {
      try {
        handler(event);
      } catch (error) {
        logger.error('Event handler error', error, { eventType: event.event });
      }
    });
  }

  /**
   * Connect to SSE stream
   */
  connect(threadId: string | null, onOpen?: () => void, onError?: (error: Event) => void): void {
    logger.info('Connecting to SSE stream', { threadId: threadId || 'new' });

    // Close existing connection
    this.disconnect();

    // Build URL - handle both absolute and relative URLs
    let urlString: string;
    if (this.baseUrl.startsWith('http://') || this.baseUrl.startsWith('https://')) {
      // Absolute URL
      const url = new URL(this.baseUrl);
      if (threadId) {
        url.searchParams.set('thread_id', threadId);
      }
      urlString = url.toString();
    } else {
      // Relative URL - ensure trailing slash for nginx 'location /api/' matching
      const baseWithSlash = this.baseUrl.endsWith('/') ? this.baseUrl : `${this.baseUrl}/`;
      urlString = threadId ? `${baseWithSlash}?thread_id=${threadId}` : baseWithSlash;
    }

    try {
      this.eventSource = new EventSource(urlString);

      this.eventSource.onopen = () => {
        logger.info('SSE connection established');
        onOpen?.();
      };

      this.eventSource.onerror = (error) => {
        logger.error('SSE connection error', error);
        onError?.(error);
      };

      // Listen for all AG-UI event types
      const eventTypes = [
        'token',
        'tool_start',
        'tool_end',
        'tool_execution_request',
        'tool_execution_complete',
        'message_complete',
        'error',
      ];

      eventTypes.forEach((eventType) => {
        this.eventSource!.addEventListener(eventType, (event: MessageEvent) => {
          try {
            const data = JSON.parse(event.data);
            // Handle both formats: { data: {...} } and direct {...}
            // Some SSE libraries wrap the event data in a 'data' property
            const eventData = typeof data === 'object' && 'data' in data && data.data !== undefined 
              ? data.data 
              : data;
            
            const aguiEvent: AGUIEvent = {
              event: eventType as AGUIEvent['event'],
              threadId: data.thread_id || threadId || 'unknown',
              timestamp: data.timestamp || new Date().toISOString(),
              data: eventData,
            };

            logger.debug('Received SSE event', { eventType, data: aguiEvent });
            this.emit(aguiEvent as AGUIEventUnion);
          } catch (error) {
            logger.error('Failed to parse SSE event', error, { eventType, raw: event.data });
          }
        });
      });

      // Default message handler for events without explicit type
      this.eventSource.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          logger.debug('Received untyped SSE message', { data });

          // Try to infer event type from data
          if (data.event) {
            const aguiEvent: AGUIEvent = {
              event: data.event,
              threadId: data.thread_id || threadId || 'unknown',
              timestamp: data.timestamp || new Date().toISOString(),
              data: data,
            };
            this.emit(aguiEvent as AGUIEventUnion);
          }
        } catch (error) {
          logger.error('Failed to parse SSE message', error);
        }
      };
    } catch (error) {
      logger.error('Failed to create SSE connection', error);
      throw error;
    }
  }

  /**
   * Disconnect from SSE stream
   */
  disconnect(): void {
    if (this.eventSource) {
      logger.info('Disconnecting from SSE stream');
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }

  /**
   * Get connection ready state
   */
  getReadyState(): number {
    return this.eventSource?.readyState ?? EventSource.CLOSED;
  }
}

// Export singleton instance
export const streamHandler = new StreamHandler();
