// Session manager service for thread management
import { logger } from '../utils/logger';
import { aguiClient } from './aguiClient';
import { useChatStore } from '../stores/chatStore';

class SessionManager {
  /**
   * Create a new conversation thread
   */
  createSession(): string {
    logger.info('Creating new session');
    const threadId = useChatStore.getState().createThread();
    logger.info('Session created', { threadId });
    return threadId;
  }

  /**
   * Load existing thread from backend
   */
  async loadSession(threadId: string): Promise<void> {
    logger.info('Loading session', { threadId });

    try {
      const thread = await aguiClient.getThread(threadId);
      logger.info('Session loaded', { threadId, thread });

      // TODO: Parse and populate store with thread data
      // This will be implemented when we integrate with the chat components
    } catch (error) {
      logger.error('Failed to load session', error, { threadId });
      throw error;
    }
  }

  /**
   * Clear current session
   */
  clearSession(): void {
    logger.info('Clearing current session');
    useChatStore.getState().clearThread();
    logger.info('Session cleared');
  }

  /**
   * Get current thread ID
   */
  getCurrentThreadId(): string | null {
    return useChatStore.getState().currentThread?.id || null;
  }

  /**
   * List all available threads
   */
  async listSessions(): Promise<unknown[]> {
    logger.info('Listing all sessions');

    try {
      const threads = await aguiClient.listThreads();
      logger.info('Sessions listed', { count: threads.length });
      return threads;
    } catch (error) {
      logger.error('Failed to list sessions', error);
      throw error;
    }
  }

  /**
   * Check if session is active
   */
  isSessionActive(): boolean {
    const thread = useChatStore.getState().currentThread;
    return thread !== null && thread.status === 'active';
  }

  /**
   * Get session message count
   */
  getMessageCount(): number {
    return useChatStore.getState().messages.length;
  }
}

// Export singleton instance
export const sessionManager = new SessionManager();
