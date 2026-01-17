// useStreaming hook for real-time token handling
import { useEffect, useCallback, useRef } from 'react';
import { useChatStore } from '../stores/chatStore';
import { streamHandler } from '../services/streamHandler';
import { logger } from '../utils/logger';
import {
  isTokenEvent,
  isMessageCompleteEvent,
  isErrorEvent,
  type AGUIEventUnion,
} from '../types/agui';
import type { Message } from '../types/message';

export function useStreaming() {
  const streamingState = useChatStore((state) => state.streamingState);
  const updateStreamingState = useChatStore((state) => state.updateStreamingState);
  const addMessage = useChatStore((state) => state.addMessage);

  // Debounce timer ref
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const localBuffer = useRef<string>('');

  /**
   * Handle token event with debounced updates
   */
  const handleTokenEvent = useCallback(
    (event: AGUIEventUnion) => {
      if (!isTokenEvent(event)) return;

      const token = event.data.token;

      // Initialize streaming if not already started
      if (!streamingState.isStreaming) {
        const messageId = crypto.randomUUID();
        updateStreamingState({
          isStreaming: true,
          currentMessageId: messageId,
          startedAt: new Date(),
          buffer: token,
          tokenCount: 1,
        });
        localBuffer.current = token;
      } else {
        // Append to local buffer and increment token count
        localBuffer.current += token;
        const newTokenCount = streamingState.tokenCount + 1;

        // Debounced update (50ms)
        if (debounceTimer.current) {
          clearTimeout(debounceTimer.current);
        }

        debounceTimer.current = setTimeout(() => {
          updateStreamingState({
            buffer: localBuffer.current,
            tokenCount: newTokenCount,
          });
        }, 50);
      }
    },
    [streamingState.isStreaming, streamingState.tokenCount, updateStreamingState]
  );

  /**
   * Handle message_complete event
   */
  const handleMessageCompleteEvent = useCallback(
    (event: AGUIEventUnion) => {
      if (!isMessageCompleteEvent(event)) return;

      if (!streamingState.isStreaming || !streamingState.currentMessageId) {
        logger.warn('Received message_complete without active streaming');
        return;
      }

      // Flush any pending debounced updates
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
        debounceTimer.current = null;
      }

      // Create final message from buffer
      const message: Message = {
        id: streamingState.currentMessageId,
        role: 'assistant',
        content: localBuffer.current || streamingState.buffer,
        timestamp: new Date(event.timestamp),
        threadId: event.threadId,
        metadata: {
          streamingComplete: true,
          tokenCount: streamingState.tokenCount,
          executionTimeMs: streamingState.startedAt
            ? Date.now() - streamingState.startedAt.getTime()
            : undefined,
        },
      };

      // Add to message history
      addMessage(message);

      // Reset streaming state
      updateStreamingState({
        isStreaming: false,
        currentMessageId: undefined,
        buffer: '',
        startedAt: undefined,
        tokenCount: 0,
      });
      localBuffer.current = '';

      logger.info('Message streaming complete', { messageId: message.id });
    },
    [streamingState, addMessage, updateStreamingState]
  );

  /**
   * Handle error event
   */
  const handleErrorEvent = useCallback(
    (event: AGUIEventUnion) => {
      if (!isErrorEvent(event)) return;

      const { errorMessage, recoverable } = event.data;
      logger.error('Received error event', new Error(errorMessage), {
        recoverable,
        errorType: event.data.errorType,
      });

      // Clear streaming state if unrecoverable
      if (!recoverable && streamingState.isStreaming) {
        updateStreamingState({
          isStreaming: false,
          buffer: '',
          currentMessageId: undefined,
          tokenCount: 0,
        });
        localBuffer.current = '';
      }
    },
    [streamingState.isStreaming, updateStreamingState]
  );

  /**
   * Set up event listeners
   */
  useEffect(() => {
    // Register handlers
    streamHandler.on('token', handleTokenEvent);
    streamHandler.on('message_complete', handleMessageCompleteEvent);
    streamHandler.on('error', handleErrorEvent);

    return () => {
      // Cleanup handlers
      streamHandler.off('token', handleTokenEvent);
      streamHandler.off('message_complete', handleMessageCompleteEvent);
      streamHandler.off('error', handleErrorEvent);

      // Clear debounce timer
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [handleTokenEvent, handleMessageCompleteEvent, handleErrorEvent]);

  return {
    isStreaming: streamingState.isStreaming,
    streamingText: streamingState.buffer,
    tokenCount: streamingState.tokenCount,
  };
}
