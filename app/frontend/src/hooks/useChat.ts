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
  const updateStreamingState = useChatStore((state) => state.updateStreamingState);

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

      // Prepare assistant message
      const assistantMessageId = crypto.randomUUID();
      let assistantContent = '';

      try {
        // Send to backend with SSE event handler
        await aguiClient.sendMessage(content.trim(), threadId, (event) => {
          logger.info('Received SSE event', { type: event.type });

          switch (event.type) {
            case 'RUN_STARTED':
              updateStreamingState({ isStreaming: true, buffer: '', tokenCount: 0 });
              break;

            case 'TEXT_MESSAGE_START':
              // Assistant message started
              assistantContent = '';
              break;

            case 'TEXT_MESSAGE_CONTENT':
              if (event.delta) {
                assistantContent += event.delta;
                updateStreamingState({
                  buffer: assistantContent,
                  tokenCount: assistantContent.length,
                });
              }
              break;

            case 'TEXT_MESSAGE_END':
            case 'RUN_FINISHED':
              // Add complete assistant message
              if (assistantContent && event.type === 'RUN_FINISHED') {
                const assistantMessage: Message = {
                  id: assistantMessageId,
                  role: 'assistant',
                  content: assistantContent,
                  timestamp: new Date(),
                  threadId,
                };
                addMessage(assistantMessage);
              }
              if (event.type === 'RUN_FINISHED') {
                updateStreamingState({ isStreaming: false, buffer: '', tokenCount: 0 });
              }
              break;

            case 'ERROR':
              logger.error('Backend error', new Error(event.message || 'Unknown error'));
              updateStreamingState({ isStreaming: false });
              break;
          }
        });

        logger.info('Message sent successfully', { messageId: userMessage.id });
      } catch (error) {
        logger.error('Failed to send message', error);
        throw error;
      }
    },
    [currentThread?.id, createThread, addMessage, updateStreamingState]
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
