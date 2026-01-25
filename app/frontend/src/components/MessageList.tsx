// MessageList component with auto-scroll
import { useEffect, useRef, useCallback, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import type { Message } from '../types/message';

interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  streamingText?: string;
}

export function MessageList({ messages, isStreaming, streamingText }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);

  /**
   * Scroll to bottom
   */
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior, block: 'end' });
  }, []);

  /**
   * Handle scroll event to detect if user scrolled up
   */
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10;

    setShouldAutoScroll(isAtBottom);
    setShowScrollButton(!isAtBottom);
  }, []);

  /**
   * Auto-scroll on new messages if user hasn't scrolled up
   */
  useEffect(() => {
    if (shouldAutoScroll) {
      scrollToBottom('smooth');
    }
  }, [messages.length, streamingText, shouldAutoScroll, scrollToBottom]);

  /**
   * Force scroll to bottom when user sends a new message
   */
  useEffect(() => {
    if (messages.length > 0 && messages[messages.length - 1].role === 'user') {
      setShouldAutoScroll(true);
      scrollToBottom('smooth');
    }
  }, [messages, scrollToBottom]);

  return (
    <div className="relative flex-1 overflow-hidden bg-secondary">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto px-4 py-6"
      >
        {messages.length === 0 && !isStreaming ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-text-secondary">
              <svg
                className="mx-auto h-12 w-12 mb-4 opacity-50"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
              <p className="text-lg font-medium text-text-primary">Start a conversation</p>
              <p className="text-sm mt-2">Send a message to begin chatting with the AI assistant</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            {/* Streaming message preview */}
            {isStreaming && streamingText && (
              <div className="flex justify-start mb-4">
                <div className="max-w-[70%] rounded-lg px-4 py-2 bg-message-assistant text-message-assistant-text shadow-sm mr-auto">
                  <div className="text-xs font-semibold mb-1 opacity-70">Assistant</div>
                  <div className="whitespace-pre-wrap break-words">{streamingText}</div>
                  <div className="typing-indicator mt-2 flex space-x-1">
                    <span className="w-2 h-2 bg-text-secondary rounded-full"></span>
                    <span className="w-2 h-2 bg-text-secondary rounded-full"></span>
                    <span className="w-2 h-2 bg-text-secondary rounded-full"></span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <button
          onClick={() => {
            setShouldAutoScroll(true);
            scrollToBottom('smooth');
          }}
          className="absolute bottom-4 right-4 bg-accent text-white p-3 rounded-full shadow-lg hover:bg-accent-hover transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus"
          aria-label="Scroll to bottom"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 14l-7 7m0 0l-7-7m7 7V3"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
