// useChat hook for message management
import { useCallback } from 'react';
import { useChatStore } from '../stores/chatStore';
import { aguiClient } from '../services/aguiClient';
import { logger } from '../utils/logger';
import { generateUUID } from '../utils/uuid';
import type { Message } from '../types/message';

// Approximate token count: one token ≈ 4 characters (common heuristic)
const CHARS_PER_TOKEN_ESTIMATE = 4;

export function useChat() {
  const messages = useChatStore((state) => state.messages);
  const currentThread = useChatStore((state) => state.currentThread);
  const isInputDisabled = useChatStore((state) => state.isInputDisabled);
  const streamingState = useChatStore((state) => state.streamingState);
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
        id: generateUUID(),
        role: 'user',
        content: content.trim(),
        timestamp: new Date(),
        threadId,
      };

      // Add to store immediately
      addMessage(userMessage);

      // Prepare assistant message
      const assistantMessageId = generateUUID();
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
                  tokenCount: Math.round(assistantContent.length / CHARS_PER_TOKEN_ESTIMATE),
                });
              }
              break;

            case 'TEXT_MESSAGE_END':
              // TEXT_MESSAGE_END is the AG-UI protocol signal that the assistant text is
              // complete. Commit the message to the permanent list immediately so it is
              // never lost, even if RUN_FINISHED is not received (e.g. due to a network
              // interruption or a server exception after content is already delivered).
              if (assistantContent) {
                addMessage({
                  id: assistantMessageId,
                  role: 'assistant',
                  content: assistantContent,
                  timestamp: new Date(),
                  threadId,
                  metadata: {
                    streamingComplete: true,
                    tokenCount: Math.round(assistantContent.length / CHARS_PER_TOKEN_ESTIMATE),
                  },
                });
              }
              // Clear the streaming bubble as soon as the text is complete.
              updateStreamingState({ isStreaming: false, buffer: '', tokenCount: 0 });
              break;

            case 'RUN_FINISHED':
              // The message was already committed on TEXT_MESSAGE_END for text responses.
              // For runs that produce no text (e.g. tool-only), TEXT_MESSAGE_END never fires,
              // so RUN_FINISHED is the only place that clears isStreaming.
              updateStreamingState({ isStreaming: false, buffer: '', tokenCount: 0 });
              break;

            case 'ERROR':
              logger.error('Backend error', new Error(event.message || 'Unknown error'));
              updateStreamingState({ isStreaming: false, buffer: '', tokenCount: 0 });
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
    // Streaming state
    isStreaming: streamingState.isStreaming,
    streamingText: streamingState.buffer,
  };
}
