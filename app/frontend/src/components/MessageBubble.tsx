// MessageBubble component for individual message display
import { memo } from 'react';
import type { Message } from '../types/message';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble = memo(({ message }: MessageBubbleProps) => {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isTool = message.role === 'tool';

  const bubbleClass = isUser
    ? 'bg-message-user text-message-user-text ml-auto'
    : isAssistant
    ? 'bg-message-assistant text-message-assistant-text mr-auto'
    : 'bg-message-tool text-message-tool-text mx-auto border border-border';

  const alignmentClass = isUser ? 'justify-end' : 'justify-start';

  return (
    <div className={`flex ${alignmentClass} mb-4`}>
      <div className={`max-w-[70%] rounded-lg px-4 py-2 shadow-sm ${bubbleClass}`}>
        {/* Role indicator for non-user messages */}
        {!isUser && (
          <div className="text-xs font-semibold mb-1 opacity-70">
            {isAssistant ? 'Assistant' : isTool ? 'Tool' : message.role}
          </div>
        )}

        {/* Message content */}
        <div className="whitespace-pre-wrap break-words">{message.content}</div>

        {/* Metadata footer */}
        <div className="text-xs mt-2 opacity-60">
          {message.timestamp.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
          })}
          {message.metadata?.tokenCount && (
            <span className="ml-2">• {message.metadata.tokenCount} tokens</span>
          )}
          {message.metadata?.executionTimeMs && (
            <span className="ml-2">• {(message.metadata.executionTimeMs / 1000).toFixed(1)}s</span>
          )}
        </div>

        {/* Tool calls indicator */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-2 pt-2 border-t border-current opacity-50">
            <div className="text-xs">
              Used {message.toolCalls.length} tool{message.toolCalls.length > 1 ? 's' : ''}:{' '}
              {message.toolCalls.map((tc) => tc.toolName).join(', ')}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

MessageBubble.displayName = 'MessageBubble';
