// useTeams hook for agent team collaboration
import { useEffect, useCallback } from 'react';
import { useTeamsStore } from '../stores/teamsStore';
import { getApiBaseUrl } from '../config/api';
import { logger } from '../utils/logger';
import { generateUUID } from '../utils/uuid';
import type { TeamsEvent, TeamsRequest } from '../types/teams';

export function useTeams() {
  const patterns = useTeamsStore((s) => s.patterns);
  const selectedPattern = useTeamsStore((s) => s.selectedPattern);
  const teamsMessages = useTeamsStore((s) => s.teamsMessages);
  const isRunning = useTeamsStore((s) => s.isRunning);
  const currentRound = useTeamsStore((s) => s.currentRound);
  const error = useTeamsStore((s) => s.error);
  const summary = useTeamsStore((s) => s.summary);

  const setPatterns = useTeamsStore((s) => s.setPatterns);
  const selectPattern = useTeamsStore((s) => s.selectPattern);
  const addAgentMessage = useTeamsStore((s) => s.addAgentMessage);
  const updateLastAgentMessage = useTeamsStore((s) => s.updateLastAgentMessage);
  const completeLastAgentMessage = useTeamsStore((s) => s.completeLastAgentMessage);
  const setRound = useTeamsStore((s) => s.setRound);
  const setRunning = useTeamsStore((s) => s.setRunning);
  const setError = useTeamsStore((s) => s.setError);
  const setSummary = useTeamsStore((s) => s.setSummary);
  const clearTeams = useTeamsStore((s) => s.clearTeams);

  // Fetch patterns on mount
  useEffect(() => {
    const baseUrl = getApiBaseUrl();
    fetch(`${baseUrl}/v1/patterns`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: unknown) => {
        if (Array.isArray(data)) {
          setPatterns(data);
        }
      })
      .catch((err) => {
        logger.error('Failed to fetch patterns', err);
      });
  }, [setPatterns]);

  const handleTeamsEvent = useCallback(
    (event: TeamsEvent) => {
      logger.info('Teams SSE event', { type: event.type });

      switch (event.type) {
        case 'TEAMS_STARTED':
          clearTeams();
          setRunning(true);
          break;

        case 'AGENT_STARTED':
          addAgentMessage({
            id: generateUUID(),
            role: event.agent_role ?? 'Unknown',
            content: '',
            round: event.round ?? 1,
            timestamp: new Date(),
            isComplete: false,
          });
          break;

        case 'AGENT_MESSAGE_DELTA':
          if (event.delta) {
            updateLastAgentMessage(event.delta);
          }
          break;

        case 'AGENT_MESSAGE_END':
          completeLastAgentMessage(event.content ?? '');
          break;

        case 'ROUND_COMPLETED':
          if (event.round !== undefined) {
            setRound(event.round);
          }
          break;

        case 'TEAMS_FINISHED':
          setRunning(false);
          if (event.summary) {
            setSummary(event.summary);
          }
          break;

        case 'TEAMS_ERROR':
          setRunning(false);
          setError(event.message ?? 'Unknown teams error');
          break;
      }
    },
    [
      clearTeams,
      setRunning,
      addAgentMessage,
      updateLastAgentMessage,
      completeLastAgentMessage,
      setRound,
      setError,
      setSummary,
    ]
  );

  const sendTeamsMessage = useCallback(
    async (prompt: string) => {
      if (!selectedPattern || !prompt.trim()) return;

      const baseUrl = getApiBaseUrl();

      // Create thread_id on first message, reuse on follow-ups
      let threadId = useTeamsStore.getState().threadId;
      if (!threadId) {
        threadId = generateUUID();
        useTeamsStore.setState({ threadId });
      }

      const request: TeamsRequest = {
        pattern_id: selectedPattern.id,
        prompt: prompt.trim(),
        max_rounds: 3,
        thread_id: threadId,
      };

      clearTeams();
      setRunning(true);
      setError(null);

      try {
        const response = await fetch(`${baseUrl}/v1/teams/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        if (!response.body) {
          throw new Error('Response body is null');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        try {
          let done = false;
          while (!done) {
            const result = await reader.read();
            done = result.done;
            if (done) break;
            const value = result.value;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6).trim();
                if (data) {
                  try {
                    const event = JSON.parse(data) as TeamsEvent;
                    handleTeamsEvent(event);
                  } catch (e) {
                    logger.error('Failed to parse teams SSE event', e);
                  }
                }
              }
            }
          }
        } finally {
          try {
            reader.releaseLock();
          } catch {
            // Reader may already be released
          }
        }

        // If stream ended without TEAMS_FINISHED, mark as not running
        if (useTeamsStore.getState().isRunning) {
          setRunning(false);
        }
      } catch (err) {
        logger.error('Teams stream failed', err);
        setRunning(false);
        setError(err instanceof Error ? err.message : 'Teams stream failed');
      }
    },
    [selectedPattern, handleTeamsEvent, clearTeams, setRunning, setError]
  );

  const newThread = useTeamsStore((s) => s.newThread);

  return {
    patterns,
    selectedPattern,
    selectPattern,
    teamsMessages,
    sendTeamsMessage,
    isRunning,
    currentRound,
    error,
    summary,
    newThread,
  };
}
