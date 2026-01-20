// Zustand chat store with initial state
import { create } from 'zustand';
import type { Message } from '../types/message';
import type { Thread, ThreadStatus } from '../types/session';
import type { Connection, ConnectionStatus, StreamingState, ToolCall } from '../types/agui';

interface ChatStore {
  // Core entities
  currentThread: Thread | null;
  messages: Message[];
  connection: Connection;
  streamingState: StreamingState;

  // UI state
  isInputDisabled: boolean;
  lastError: string | null;

  // Actions
  createThread: () => string;
  addMessage: (message: Message) => void;
  updateStreamingState: (update: Partial<StreamingState>) => void;
  setConnectionStatus: (status: ConnectionStatus, errorMessage?: string) => void;
  clearThread: () => void;
  retryLastMessage: () => void;
  setThreadStatus: (status: ThreadStatus) => void;
  addToolCall: (messageId: string, toolCall: ToolCall) => void;
  updateToolCall: (messageId: string, toolCallId: string, update: Partial<ToolCall>) => void;
}

const initialState = {
  currentThread: null,
  messages: [],
  connection: {
    status: 'disconnected' as ConnectionStatus,
    endpoint: import.meta.env.VITE_AGUI_ENDPOINT || '/api/',
    reconnectAttempts: 0,
  },
  streamingState: {
    isStreaming: false,
    buffer: '',
    tokenCount: 0,
  },
  isInputDisabled: false,
  lastError: null,
};

export const useChatStore = create<ChatStore>((set, get) => ({
  ...initialState,

  createThread: () => {
    const threadId = crypto.randomUUID();
    const now = new Date();

    set({
      currentThread: {
        id: threadId,
        createdAt: now,
        updatedAt: now,
        messages: [],
        status: 'active',
      },
      messages: [],
      lastError: null,
    });

    return threadId;
  },

  addMessage: (message: Message) => {
    set((state) => {
      const newMessages = [...state.messages, message];

      // Auto-prune if exceeds 50 messages
      const prunedMessages = newMessages.length > 50 ? newMessages.slice(-50) : newMessages;

      return {
        messages: prunedMessages,
        currentThread: state.currentThread
          ? {
              ...state.currentThread,
              messages: prunedMessages,
              updatedAt: new Date(),
              metadata: {
                ...state.currentThread.metadata,
                messageCount: prunedMessages.length,
              },
            }
          : null,
      };
    });
  },

  updateStreamingState: (update: Partial<StreamingState>) => {
    set((state) => ({
      streamingState: {
        ...state.streamingState,
        ...update,
      },
    }));
  },

  setConnectionStatus: (status: ConnectionStatus, errorMessage?: string) => {
    set((state) => ({
      connection: {
        ...state.connection,
        status,
        errorMessage: errorMessage || state.connection.errorMessage,
        reconnectAttempts:
          status === 'connected' ? 0 : status === 'reconnecting' ? state.connection.reconnectAttempts + 1 : state.connection.reconnectAttempts,
        lastPingAt: status === 'connected' ? new Date() : state.connection.lastPingAt,
      },
      isInputDisabled: status === 'disconnected' || status === 'error',
    }));
  },

  clearThread: () => {
    set({
      ...initialState,
      connection: get().connection, // Preserve connection state
    });
  },

  retryLastMessage: () => {
    const { messages } = get();
    const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user');

    if (lastUserMessage) {
      // Remove failed assistant response if any
      set((state) => ({
        messages: state.messages.filter(
          (m) => !(m.role === 'assistant' && m.timestamp > lastUserMessage.timestamp)
        ),
        lastError: null,
      }));
    }
  },

  setThreadStatus: (status: ThreadStatus) => {
    set((state) => ({
      currentThread: state.currentThread
        ? {
            ...state.currentThread,
            status,
          }
        : null,
    }));
  },

  addToolCall: (messageId: string, toolCall: ToolCall) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === messageId
          ? {
              ...msg,
              toolCalls: [...(msg.toolCalls || []), toolCall],
            }
          : msg
      ),
    }));
  },

  updateToolCall: (messageId: string, toolCallId: string, update: Partial<ToolCall>) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === messageId
          ? {
              ...msg,
              toolCalls: msg.toolCalls?.map((tc) =>
                tc.id === toolCallId ? { ...tc, ...update } : tc
              ),
            }
          : msg
      ),
    }));
  },
}));
