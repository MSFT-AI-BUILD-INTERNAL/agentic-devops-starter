// Left sidebar for selecting agent team patterns
import { useTeams } from '../hooks/useTeams';
import { ROLE_EMOJIS } from '../types/teams';

const PATTERN_META: Record<string, { emoji: string; hint: string }> = {
  'debate-critic': { emoji: '⚔️', hint: 'A vs B decisions, architecture choices' },
  'generator-evaluator': { emoji: '🔨', hint: 'Code review, document writing & review' },
  'leadership': { emoji: '👔', hint: 'Strategic decisions, multi-domain analysis' },
  'planner-executor': { emoji: '📐', hint: 'Complex task planning and execution' },
  'research-report': { emoji: '🔬', hint: 'Research, market analysis, trend reports' },
};

export function TeamsSidebar() {
  const { patterns, selectedPattern, selectPattern } = useTeams();

  const isNormalChat = selectedPattern === null;

  return (
    <div className="w-80 flex-shrink-0 bg-secondary border-r border-border flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border">
        <h2 className="text-lg font-bold text-text-primary">🤖 Agent Teams</h2>
        <p className="text-xs text-text-secondary mt-1">Select a collaboration pattern</p>
      </div>

      {/* Scrollable card list */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        {/* Normal Chat card */}
        <button
          type="button"
          onClick={() => selectPattern(null)}
          className={`w-full text-left rounded-lg p-3 transition-colors border ${
            isNormalChat
              ? 'border-l-4 border-accent bg-accent/10'
              : 'border-border hover:bg-primary'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="text-lg">💬</span>
            <span className="font-semibold text-sm text-text-primary">Normal Chat</span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Direct 1:1 conversation with AI assistant
          </p>
        </button>

        {/* Pattern cards */}
        {patterns.map((pattern) => {
          const meta = PATTERN_META[pattern.id];
          const isSelected = selectedPattern?.id === pattern.id;

          return (
            <button
              type="button"
              key={pattern.id}
              onClick={() => selectPattern(pattern)}
              className={`w-full text-left rounded-lg p-3 transition-colors border ${
                isSelected
                  ? 'border-l-4 border-accent bg-accent/10'
                  : 'border-border hover:bg-primary'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">{meta?.emoji ?? '🤖'}</span>
                <span className="font-semibold text-sm text-text-primary">{pattern.name}</span>
              </div>
              <p className="text-xs text-text-secondary mt-1">{pattern.description}</p>
              {meta?.hint && (
                <p className="text-xs text-text-secondary mt-1 italic">📌 {meta.hint}</p>
              )}
              {/* Role badges */}
              {pattern.roles.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {pattern.roles.map((role) => (
                    <span
                      key={role}
                      className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-accent/20 text-text-primary text-[10px] font-medium"
                    >
                      {ROLE_EMOJIS[role] ?? '👤'} {role}
                    </span>
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
