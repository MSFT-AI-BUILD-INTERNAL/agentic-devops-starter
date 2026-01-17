// ChatInterface main container component
import { useCallback } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { useChat } from '../hooks/useChat';
import { useStreaming } from '../hooks/useStreaming';
import { useConnection } from '../hooks/useConnection';
import { logger } from '../utils/logger';

export function ChatInterface() {
  const { messages, sendMessage, newConversation, isInputDisabled, currentThreadId } = useChat();
  const { isStreaming, streamingText } = useStreaming();
  const { status: connectionStatus, errorMessage: connectionError } = useConnection();

  /**
   * Handle sending a message
   */
  const handleSendMessage = useCallback(
    async (content: string) => {
      try {
        await sendMessage(content);
      } catch (error) {
        logger.error('Failed to send message from chat interface', error);
        // Error is already logged in useChat hook
      }
    },
    [sendMessage]
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

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">AI Assistant</h2>
          <div className="text-sm opacity-90 mt-1">
            {connectionStatus === 'connected' && (
              <span className="flex items-center">
                <span className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></span>
                Connected
              </span>
            )}
            {connectionStatus === 'connecting' && (
              <span className="flex items-center">
                <span className="w-2 h-2 bg-yellow-400 rounded-full mr-2 animate-pulse"></span>
                Connecting...
              </span>
            )}
            {connectionStatus === 'reconnecting' && (
              <span className="flex items-center">
                <span className="w-2 h-2 bg-yellow-400 rounded-full mr-2 animate-pulse"></span>
                Reconnecting...
              </span>
            )}
            {connectionStatus === 'disconnected' && (
              <span className="flex items-center">
                <span className="w-2 h-2 bg-red-400 rounded-full mr-2"></span>
                Disconnected
              </span>
            )}
            {connectionStatus === 'error' && (
              <span className="flex items-center">
                <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                {connectionError || 'Connection error'}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Message count */}
          {currentThreadId && (
            <div className="text-sm opacity-90">
              {messages.length} message{messages.length !== 1 ? 's' : ''}
            </div>
          )}

          {/* New conversation button */}
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
        </div>
      </div>

      {/* Connection error banner */}
      {connectionStatus === 'error' && connectionError && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3">
          <div className="flex items-center">
            <svg
              className="h-5 w-5 text-red-500 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="flex-1">
              <p className="text-sm text-red-800">{connectionError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Message list */}
      <MessageList messages={messages} isStreaming={isStreaming} streamingText={streamingText} />

      {/* Input */}
      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={isInputDisabled || connectionStatus !== 'connected'}
        placeholder={
          connectionStatus !== 'connected'
            ? 'Connect to start chatting...'
            : 'Type your message...'
        }
      />
    </div>
  );
}
