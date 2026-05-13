// Message list for agent team mode
import { useEffect, useRef, useState, useCallback } from 'react';
import { AgentMessageBubble } from './AgentMessageBubble';
import { MarkdownContent } from './MarkdownContent';
import { useTeams } from '../hooks/useTeams';

export function TeamsMessageList() {
  const { teamsMessages, isRunning, error, summary } = useTeams();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior, block: 'end' });
  }, []);

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    setShouldAutoScroll(Math.abs(scrollHeight - clientHeight - scrollTop) < 10);
  }, []);

  useEffect(() => {
    if (shouldAutoScroll) {
      scrollToBottom('smooth');
    }
  }, [teamsMessages, shouldAutoScroll, scrollToBottom]);

  // Group messages by round for dividers
  let lastRound = 0;

  return (
    <div className="relative flex-1 overflow-hidden bg-secondary">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto px-4 py-6"
      >
        {teamsMessages.length === 0 && !isRunning ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-text-secondary">
              <p className="text-lg font-medium text-text-primary">Agent Team Ready</p>
              <p className="text-sm mt-2">
                Select a pattern and enter a topic to start
              </p>
            </div>
          </div>
        ) : (
          <>
            {teamsMessages.map((msg) => {
              const showDivider = msg.round > lastRound;
              lastRound = msg.round;
              return (
                <div key={msg.id}>
                  {showDivider && (
                    <div className="flex items-center my-4">
                      <div className="flex-1 border-t border-border"></div>
                      <span className="px-3 text-xs text-text-secondary font-medium">
                        Round {msg.round}
                      </span>
                      <div className="flex-1 border-t border-border"></div>
                    </div>
                  )}
                  <AgentMessageBubble message={msg} />
                </div>
              );
            })}

            {/* Running indicator */}
            {isRunning && teamsMessages.length > 0 && (
              <div className="flex items-center justify-center py-2">
                <div className="flex items-center space-x-2 text-text-secondary text-sm">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
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
                  <span>Team running…</span>
                </div>
              </div>
            )}

            {/* Error display */}
            {error && (
              <div className="mx-4 my-2 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm">
                Error: {error}
              </div>
            )}

            {/* Summary */}
            {summary && (
              <div className="mx-4 my-4 p-4 bg-message-assistant text-message-assistant-text rounded-lg border border-border">
                <div className="text-sm font-semibold mb-2 opacity-70">📋 Summary</div>
                <MarkdownContent content={summary} />
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>
    </div>
  );
}
