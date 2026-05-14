// Zustand store for agent team state
import { create } from 'zustand';
import type { PatternInfo, AgentMessage } from '../types/teams';

interface TeamsState {
  patterns: PatternInfo[];
  selectedPattern: PatternInfo | null;
  teamsMessages: AgentMessage[];
  isRunning: boolean;
  currentRound: number;
  error: string | null;
  summary: string | null;
  threadId: string | null;

  setPatterns: (patterns: PatternInfo[]) => void;
  selectPattern: (pattern: PatternInfo | null) => void;
  addAgentMessage: (msg: AgentMessage) => void;
  updateLastAgentMessage: (delta: string) => void;
  completeLastAgentMessage: (content: string) => void;
  setRound: (round: number) => void;
  setRunning: (running: boolean) => void;
  setError: (error: string | null) => void;
  setSummary: (summary: string | null) => void;
  clearTeams: () => void;
  newThread: () => void;
}

export const useTeamsStore = create<TeamsState>((set) => ({
  patterns: [],
  selectedPattern: null,
  teamsMessages: [],
  isRunning: false,
  currentRound: 0,
  error: null,
  summary: null,
  threadId: null,

  setPatterns: (patterns) => set({ patterns }),

  selectPattern: (pattern) => set({ selectedPattern: pattern }),

  addAgentMessage: (msg) =>
    set((state) => ({ teamsMessages: [...state.teamsMessages, msg] })),

  updateLastAgentMessage: (delta) =>
    set((state) => {
      const msgs = [...state.teamsMessages];
      const last = msgs[msgs.length - 1];
      if (last && !last.isComplete) {
        msgs[msgs.length - 1] = { ...last, content: last.content + delta };
      }
      return { teamsMessages: msgs };
    }),

  completeLastAgentMessage: (content) =>
    set((state) => {
      const msgs = [...state.teamsMessages];
      const last = msgs[msgs.length - 1];
      if (last) {
        msgs[msgs.length - 1] = { ...last, content, isComplete: true };
      }
      return { teamsMessages: msgs };
    }),

  setRound: (round) => set({ currentRound: round }),

  setRunning: (running) => set({ isRunning: running }),

  setError: (error) => set({ error }),

  setSummary: (summary) => set({ summary }),

  clearTeams: () =>
    set({ teamsMessages: [], currentRound: 0, error: null, summary: null }),

  newThread: () =>
    set({ teamsMessages: [], currentRound: 0, error: null, summary: null, threadId: null }),
}));
