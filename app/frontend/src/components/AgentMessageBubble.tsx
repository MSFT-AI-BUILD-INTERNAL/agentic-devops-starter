// Message bubble for agent team messages
import { memo } from 'react';
import { MarkdownContent } from './MarkdownContent';
import { ROLE_EMOJIS } from '../types/teams';
import type { AgentMessage } from '../types/teams';

interface AgentMessageBubbleProps {
  message: AgentMessage;
}

const BORDER_COLORS = [
  'border-l-blue-500',
  'border-l-purple-500',
  'border-l-green-500',
  'border-l-orange-500',
  'border-l-pink-500',
  'border-l-teal-500',
];

function getBorderColor(role: string): string {
  let hash = 0;
  for (let i = 0; i < role.length; i++) {
    hash = role.charCodeAt(i) + ((hash << 5) - hash);
  }
  return BORDER_COLORS[Math.abs(hash) % BORDER_COLORS.length];
}

export const AgentMessageBubble = memo(({ message }: AgentMessageBubbleProps) => {
  const emoji = ROLE_EMOJIS[message.role] ?? '🤖';
  const borderColor = getBorderColor(message.role);

  return (
    <div className="flex justify-start mb-4">
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 bg-message-assistant text-message-assistant-text shadow-sm mr-auto border-l-4 ${borderColor}`}
      >
        {/* Role badge */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold">
            {emoji} {message.role}
          </span>
          <span className="text-xs opacity-60">Round {message.round}</span>
        </div>

        {/* Content */}
        {message.content ? (
          <MarkdownContent content={message.content} />
        ) : (
          <div className="flex items-center space-x-2 py-1">
            <span className="text-sm opacity-60">Thinking…</span>
          </div>
        )}

        {/* Streaming indicator */}
        {!message.isComplete && message.content && (
          <div className="flex space-x-1 mt-1">
            <span className="w-1.5 h-1.5 bg-text-secondary rounded-full animate-pulse"></span>
            <span className="w-1.5 h-1.5 bg-text-secondary rounded-full animate-pulse delay-75"></span>
            <span className="w-1.5 h-1.5 bg-text-secondary rounded-full animate-pulse delay-150"></span>
          </div>
        )}
      </div>
    </div>
  );
});

AgentMessageBubble.displayName = 'AgentMessageBubble';
