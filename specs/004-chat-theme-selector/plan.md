# Implementation Plan: Chat Theme Selector

**Branch**: `004-chat-theme-selector` | **Date**: 2025-01-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-chat-theme-selector/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a theme selector feature that allows users to switch between multiple visual themes (Light, Dark, and custom variants) in the React + TypeScript chat interface. The solution uses Zustand for state management, localStorage for persistence, Tailwind CSS for styling via CSS custom properties (CSS variables), and ensures WCAG AA accessibility compliance across all themes.

## Technical Context

**Language/Version**: TypeScript 5.3, React 18.2  
**Primary Dependencies**: 
  - Zustand 5.0.10 (state management)
  - Tailwind CSS 3.4.19 (styling framework)
  - Vite 7.3.1 (build tool)
  - React 18.2.0 (UI library)

**Storage**: Browser localStorage for theme preference persistence  
**Testing**: Vitest for unit tests, Playwright for E2E tests  
**Target Platform**: Modern web browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)  
**Project Type**: Web application (frontend only - this feature is entirely client-side)  
**Performance Goals**: 
  - Theme switch completes in <100ms (visual update)
  - Initial theme load with zero flash of unstyled content (FOUC)
  - localStorage read/write <10ms

**Constraints**: 
  - WCAG AA accessibility: 4.5:1 contrast ratio for normal text, 3:1 for large text
  - No external dependencies beyond existing stack
  - Zero-impact on existing chat functionality during theme transitions
  - Support for users with localStorage disabled (graceful degradation)

**Scale/Scope**: 
  - 3+ themes initially (Light, Dark, High Contrast)
  - Single page application with ~15 UI components affected
  - ~500-1000 LOC for theme system implementation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check (Before Phase 0)

This feature is **FRONTEND-ONLY** and does not interact with backend services. The project constitution primarily governs backend Python development with microsoft-agent-framework. This feature:

✅ **COMPLIANT**: Does not require Python backend changes  
✅ **COMPLIANT**: Uses existing frontend tech stack (React, TypeScript, Zustand)  
✅ **COMPLIANT**: Maintains type safety with TypeScript  
✅ **COMPLIANT**: All code resides in `app/frontend/` directory (correct structure)  
✅ **COMPLIANT**: No new infrastructure required (all client-side)  
✅ **COMPLIANT**: Follows test-first development (Vitest unit tests, Playwright E2E)

### Re-Check After Phase 1 Design

**Design Artifacts Reviewed**:
- ✅ `research.md`: Architecture decisions documented
- ✅ `data-model.md`: Entity definitions follow TypeScript type safety principles
- ✅ `contracts/theme-types.ts`: Full type definitions with no `any` types
- ✅ `quickstart.md`: Developer documentation for extending system

**Compliance Verification**:
- ✅ **Type Safety**: All theme entities have strict TypeScript interfaces with type guards
- ✅ **Project Structure**: All files remain in `app/frontend/` - no backend/infra changes
- ✅ **Testing Strategy**: Multi-layer testing approach (unit, integration, E2E, accessibility)
- ✅ **No External Dependencies**: Uses existing tech stack (React, TypeScript, Zustand, Tailwind)
- ✅ **Observability**: Logging integration with existing `utils/logger.ts`

### Final Verdict: **PASS** ✅

No constitution violations detected in design phase. The implementation plan maintains compliance with all project standards. Ready to proceed to Phase 2 (Task Generation).

## Project Structure

### Documentation (this feature)

```text
specs/004-chat-theme-selector/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - Theme system architecture research
├── data-model.md        # Phase 1 output - Theme and preference entities
├── quickstart.md        # Phase 1 output - Developer guide for theme system
├── contracts/           # Phase 1 output - Theme type definitions
│   └── theme-types.ts   # TypeScript interfaces for Theme, ThemeConfig, UserPreference
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/frontend/
├── src/
│   ├── stores/
│   │   ├── chatStore.ts          # Existing - chat state management
│   │   └── themeStore.ts         # NEW - theme state and persistence
│   ├── components/
│   │   ├── ChatInterface.tsx     # MODIFIED - add ThemeSelector component
│   │   ├── MessageList.tsx       # Existing - inherits theme via CSS vars
│   │   ├── MessageInput.tsx      # Existing - inherits theme via CSS vars
│   │   ├── MessageBubble.tsx     # Existing - inherits theme via CSS vars
│   │   └── ThemeSelector.tsx     # NEW - dropdown/modal for theme selection
│   ├── hooks/
│   │   ├── useChat.ts            # Existing - no changes
│   │   └── useTheme.ts           # NEW - hook for theme operations
│   ├── types/
│   │   ├── message.ts            # Existing
│   │   └── theme.ts              # NEW - Theme, ThemeConfig, ThemePreference types
│   ├── utils/
│   │   ├── logger.ts             # Existing
│   │   └── themeUtils.ts         # NEW - theme validation, contrast checking
│   ├── styles/
│   │   └── themes.css            # NEW - CSS custom properties per theme
│   ├── index.css                 # MODIFIED - import themes.css
│   └── App.tsx                   # MODIFIED - wrap with theme provider logic
│
└── tests/
    ├── unit/
    │   ├── themeStore.test.ts    # NEW - Zustand store tests
    │   ├── useTheme.test.ts      # NEW - hook tests
    │   └── themeUtils.test.ts    # NEW - utility function tests
    └── e2e/
        └── theme-selector.spec.ts # NEW - Playwright E2E tests
```

**Structure Decision**: Web application (frontend only). This feature is self-contained within the `app/frontend/` directory. No backend or infrastructure changes required. All theme management, persistence, and UI updates occur client-side using React, Zustand, and browser localStorage.

## Complexity Tracking

**No violations identified** - this section is not applicable. The feature fully complies with the project constitution.

---

## Phase Summary

### ✅ Phase 0: Outline & Research (COMPLETE)

**Deliverable**: `research.md`

**Key Decisions**:
1. CSS Variables + Tailwind CSS for theme architecture
2. Zustand store with persist middleware for state management
3. 3 initial themes: Light, Dark, High Contrast (all WCAG AA compliant)
4. FOUC prevention via inline script in index.html
5. Theme selector in chat header
6. Comprehensive testing strategy (unit + E2E + accessibility)

**All NEEDS CLARIFICATION items resolved** ✅

### ✅ Phase 1: Design & Contracts (COMPLETE)

**Deliverables**:
- ✅ `data-model.md`: Complete entity definitions (Theme, ThemeColors, ThemePreference, ThemeConfig, ThemeMetadata)
- ✅ `contracts/theme-types.ts`: TypeScript interfaces with type guards and validation
- ✅ `quickstart.md`: Developer guide for using and extending themes
- ✅ Agent context updated via `update-agent-context.sh copilot`

**Constitution Re-Check**: PASS ✅

### 🔜 Phase 2: Task Generation (NEXT STEP)

**Action Required**: Run `/speckit.tasks` command to generate `tasks.md`

**Expected Output**: 
- Dependency-ordered task breakdown for implementation
- Each task with clear acceptance criteria
- Task dependencies mapped
- Estimated effort per task

---

## Next Steps

1. **Review this plan**: Ensure all stakeholders agree with architectural decisions
2. **Run task generation**: Execute `/speckit.tasks` to create `tasks.md`
3. **Begin implementation**: Use `/speckit.implement` to execute tasks in order

---

## Artifacts Summary

| Artifact | Status | Location | Description |
|----------|--------|----------|-------------|
| `plan.md` | ✅ Complete | This file | Implementation plan and architecture |
| `research.md` | ✅ Complete | Same directory | Research findings and decisions |
| `data-model.md` | ✅ Complete | Same directory | Entity definitions and relationships |
| `quickstart.md` | ✅ Complete | Same directory | Developer guide |
| `contracts/theme-types.ts` | ✅ Complete | `./contracts/` | TypeScript type definitions |
| `tasks.md` | ⏳ Pending | Not yet created | Task breakdown (Phase 2) |

---

**Implementation Plan Complete** ✅  
**Branch**: `004-chat-theme-selector`  
**Ready for**: Task generation (`/speckit.tasks` command)

---

## Estimated Effort

Based on research and design:

- **Implementation**: 3-5 days (8-10 files new/modified)
- **Testing**: 2-3 days (unit + E2E + accessibility)
- **Total**: ~1 week sprint (5-8 days)

**Complexity**: Medium  
**Risk**: Low (frontend-only, no backend changes, well-established patterns)
