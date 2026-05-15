// ChatInterface main container component
import { useCallback } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { ThemeSelector } from './ThemeSelector';
import { TeamsMessageList } from './TeamsMessageList';
import { useChat } from '../hooks/useChat';
import { useTeams } from '../hooks/useTeams';
import { logger } from '../utils/logger';
import type { FileAttachment } from '../types/file';

export function ChatInterface() {
  const { messages, sendMessage, newConversation, isInputDisabled, currentThreadId, isStreaming, streamingText } = useChat();
  const { selectedPattern, sendTeamsMessage, isRunning: isTeamsRunning } = useTeams();

  const isTeamsMode = selectedPattern !== null;

  /**
   * Handle sending a message
   */
  const handleSendMessage = useCallback(
    async (content: string, attachments?: FileAttachment[]) => {
      try {
        if (isTeamsMode) {
          await sendTeamsMessage(content, attachments);
        } else {
          await sendMessage(content, attachments);
        }
      } catch (error) {
        logger.error('Failed to send message from chat interface', error);
      }
    },
    [isTeamsMode, sendMessage, sendTeamsMessage]
  );

  /**
   * Handle starting a new conversation
   */
  const handleNewConversation = useCallback(() => {
    if (window.confirm('Are you sure you want to start a new conversation?')) {
      newConversation();
      logger.info('New conversation started');
    }
  }, [newConversation]);

  const placeholder = isTeamsMode
    ? `Enter a topic for the ${selectedPattern.name} team...`
    : 'Type your message...';

  return (
    <div className="flex flex-col h-full bg-primary rounded-lg shadow-lg overflow-hidden border border-border">
      {/* Header */}
      <div className="bg-accent text-white px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">AI Assistant</h2>
          <div className="text-sm opacity-90 mt-1">
            <span className="flex items-center">
              <span className="w-2 h-2 bg-success rounded-full mr-2 animate-pulse"></span>
              {isTeamsMode ? `${selectedPattern.name} Mode` : 'Ready'}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Message count (normal mode only) */}
          {!isTeamsMode && currentThreadId && (
            <div className="text-sm opacity-90">
              {messages.length} message{messages.length !== 1 ? 's' : ''}
            </div>
          )}

          {/* New conversation button (normal mode only) */}
          {!isTeamsMode && (
            <button
              onClick={handleNewConversation}
              disabled={!currentThreadId || messages.length === 0}
              className="px-4 py-2 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
              aria-label="New conversation"
            >
              <div className="flex items-center space-x-2">
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                <span>New</span>
              </div>
            </button>
          )}

          {/* Theme Selector */}
          <div className="ml-2">
            <ThemeSelector />
          </div>
        </div>
      </div>

      {/* Message area */}
      {isTeamsMode ? (
        <TeamsMessageList />
      ) : (
        <MessageList messages={messages} isStreaming={isStreaming} streamingText={streamingText} />
      )}

      {/* Input */}
      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={isTeamsMode ? isTeamsRunning : isInputDisabled}
        placeholder={placeholder}
      />
    </div>
  );
}
