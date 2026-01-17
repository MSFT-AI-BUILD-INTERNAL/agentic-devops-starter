// useChat hook for message management
import { useCallback } from 'react';
import { useChatStore } from '../stores/chatStore';
import { aguiClient } from '../services/aguiClient';
import { logger } from '../utils/logger';
import type { Message } from '../types/message';

export function useChat() {
  const messages = useChatStore((state) => state.messages);
  const currentThread = useChatStore((state) => state.currentThread);
  const isInputDisabled = useChatStore((state) => state.isInputDisabled);
  const addMessage = useChatStore((state) => state.addMessage);
  const createThread = useChatStore((state) => state.createThread);
  const clearThread = useChatStore((state) => state.clearThread);
  const retryLastMessage = useChatStore((state) => state.retryLastMessage);

  /**
   * Send a message to the backend
   */
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) {
        logger.warn('Attempted to send empty message');
        return;
      }

      // Create thread if none exists
      let threadId = currentThread?.id;
      if (!threadId) {
        threadId = createThread();
      }

      // Create user message
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: content.trim(),
        timestamp: new Date(),
        threadId,
      };

      // Add to store immediately
      addMessage(userMessage);

      try {
        // Send to backend (SSE stream will handle response)
        await aguiClient.sendMessage(content.trim(), threadId);
        logger.info('Message sent successfully', { messageId: userMessage.id });
      } catch (error) {
        logger.error('Failed to send message', error);
        throw error;
      }
    },
    [currentThread?.id, createThread, addMessage]
  );

  /**
   * Create a new conversation
   */
  const newConversation = useCallback(() => {
    logger.info('Starting new conversation');
    clearThread();
  }, [clearThread]);

  /**
   * Retry the last failed message
   */
  const retry = useCallback(() => {
    logger.info('Retrying last message');
    retryLastMessage();
  }, [retryLastMessage]);

  return {
    messages,
    currentThreadId: currentThread?.id || null,
    sendMessage,
    newConversation,
    retry,
    isInputDisabled,
  };
}
