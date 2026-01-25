// MessageInput component with keyboard submission
import { useState, useCallback, KeyboardEvent, FormEvent, useRef } from 'react';
import { logger } from '../utils/logger';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageInput({
  onSendMessage,
  disabled = false,
  placeholder = 'Type your message...',
}: MessageInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /**
   * Auto-resize textarea based on content
   */
  const adjustTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, []);

  /**
   * Handle message submission
   */
  const handleSubmit = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();

      const message = inputValue.trim();

      if (!message || disabled || isSubmitting) {
        return;
      }

      logger.debug('Submitting message', { length: message.length });

      setIsSubmitting(true);

      try {
        await onSendMessage(message);
        setInputValue(''); // Clear input on success
        // Reset textarea height
        if (textareaRef.current) {
          textareaRef.current.style.height = 'auto';
        }
      } catch (error) {
        logger.error('Failed to send message', error);
        // Keep the input value so user can retry
      } finally {
        setIsSubmitting(false);
      }
    },
    [inputValue, disabled, isSubmitting, onSendMessage]
  );

  /**
   * Handle keyboard shortcuts
   */
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Submit on Enter (without Shift)
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  /**
   * Handle input change and auto-resize
   */
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    adjustTextareaHeight();
  }, [adjustTextareaHeight]);

  return (
    <form onSubmit={handleSubmit} className="border-t border-border bg-primary p-4">
      <div className="flex items-end space-x-2">
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isSubmitting}
            rows={1}
            className="w-full px-4 py-2 bg-secondary text-text-primary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-border-focus focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            style={{
              minHeight: '44px',
              maxHeight: '120px',
            }}
            aria-label="Message input"
            aria-describedby="keyboard-shortcuts-help"
          />
          <div id="keyboard-shortcuts-help" className="text-xs text-text-secondary mt-1">
            Press Enter to send, Shift+Enter for new line
          </div>
        </div>

        <button
          type="submit"
          disabled={disabled || isSubmitting || !inputValue.trim()}
          className="px-6 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-border-focus focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
          style={{ minHeight: '44px' }}
          aria-label="Send message"
        >
          {isSubmitting ? (
            <>
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>Sending...</span>
            </>
          ) : (
            <>
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
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
              <span>Send</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
}
