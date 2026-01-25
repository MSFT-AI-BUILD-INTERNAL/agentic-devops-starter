# Tasks: Chat Theme Selector

**Input**: Design documents from `/specs/001-chat-theme-selector/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/theme-types.ts ✅

**Tests**: No explicit test requirements found in spec.md - tests are OPTIONAL for this feature.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This is a **web application** (frontend only feature):
- Frontend: `app/frontend/src/`
- Tests: `app/frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for theme system

- [X] T001 Copy TypeScript type definitions from specs/001-chat-theme-selector/contracts/theme-types.ts to app/frontend/src/types/theme.ts
- [X] T002 [P] Create CSS themes stylesheet at app/frontend/src/styles/themes.css with CSS custom properties for light, dark, and high-contrast themes
- [X] T003 [P] Update app/frontend/src/index.css to import themes.css
- [X] T004 Update app/frontend/tailwind.config.js to map CSS variables to Tailwind utility classes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core theme infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create theme definitions (light, dark, high-contrast) with full color palettes in app/frontend/src/config/themes.ts
- [X] T006 Create theme validation utility functions in app/frontend/src/utils/themeUtils.ts (color format validation, contrast checking)
- [X] T007 Create Zustand theme store with persist middleware in app/frontend/src/stores/themeStore.ts
- [X] T008 Create useTheme hook in app/frontend/src/hooks/useTheme.ts as wrapper around themeStore
- [X] T009 Add FOUC prevention script to app/frontend/index.html that loads theme from localStorage before React renders
- [X] T010 Update app/frontend/src/App.tsx to initialize theme system on mount

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Switch Between Themes (Priority: P1) 🎯 MVP

**Goal**: Users can switch between light, dark, and high-contrast themes with immediate visual feedback

**Independent Test**: Open chat interface, click theme selector, choose different theme, verify all UI elements update to new color scheme

### Implementation for User Story 1

- [X] T011 [US1] Create ThemeSelector component in app/frontend/src/components/ThemeSelector.tsx with dropdown UI for theme selection
- [X] T012 [US1] Add aria-labels and keyboard navigation support to ThemeSelector component
- [X] T013 [US1] Integrate ThemeSelector into ChatInterface header in app/frontend/src/components/ChatInterface.tsx
- [X] T014 [US1] Update existing components to use theme-aware Tailwind classes instead of hard-coded colors:
  - app/frontend/src/components/MessageBubble.tsx
  - app/frontend/src/components/MessageInput.tsx
  - app/frontend/src/components/MessageList.tsx
- [X] T015 [US1] Verify theme applies to all UI elements (backgrounds, text, borders, buttons, message bubbles)
- [X] T016 [US1] Test rapid theme switching to ensure no UI flickering or state errors

**Checkpoint**: At this point, User Story 1 should be fully functional - users can switch themes and see immediate updates

---

## Phase 4: User Story 2 - Theme Preference Persistence (Priority: P2)

**Goal**: Selected theme persists across browser sessions using localStorage

**Independent Test**: Select a theme, close browser/tab, reopen chat interface, verify previously selected theme is automatically applied

### Implementation for User Story 2

- [ ] T017 [US2] Implement localStorage persistence logic in themeStore using Zustand persist middleware
- [ ] T018 [US2] Add error handling for localStorage failures (disabled, quota exceeded, corrupted data) with fallback to default theme
- [ ] T019 [US2] Implement theme preference validation and recovery (invalid theme ID → reset to default)
- [ ] T020 [US2] Test FOUC prevention: verify theme loads before first paint with no flash of default theme
- [ ] T021 [US2] Test first-time user experience: verify default light theme applies when no preference exists
- [ ] T022 [US2] Test persistence: select dark theme, close tab, reopen, verify dark theme is automatically applied

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - theme switching works AND persists across sessions

---

## Phase 5: User Story 3 - Explore Theme Options (Priority: P3)

**Goal**: Users can view all available themes with clear labels and visual indicators

**Independent Test**: Open theme selector UI, view list of available themes, verify theme names/descriptions are displayed and currently active theme is indicated

### Implementation for User Story 3

- [ ] T023 [US3] Enhance ThemeSelector component to show all available themes with names and descriptions
- [ ] T024 [US3] Add visual indicator (checkmark, highlight, icon) for currently active theme in selector
- [ ] T025 [US3] Add hover/focus states to theme options for better interactivity feedback
- [ ] T026 [US3] Add tooltips or descriptions to each theme option explaining when to use each theme
- [ ] T027 [US3] Test keyboard navigation through theme list (Tab, Arrow keys, Enter to select)
- [ ] T028 [US3] Test on mobile devices: verify theme selector is accessible with touch interactions

**Checkpoint**: All user stories should now be independently functional - complete theme selection experience

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T029 [P] Verify all themes meet WCAG AA accessibility standards (4.5:1 contrast for normal text, 3:1 for large text)
- [ ] T030 [P] Add logging for theme operations using existing app/frontend/src/utils/logger.ts
- [ ] T031 [P] Test edge cases:
  - Theme switch while user is typing a message (should not lose input or focus)
  - Rapid theme switching (10+ clicks in 2 seconds)
  - localStorage disabled in browser
  - Corrupted theme data in localStorage
- [ ] T032 [P] Update developer documentation in specs/001-chat-theme-selector/quickstart.md if any API changes were made during implementation
- [ ] T033 Code review and refactoring for consistency with existing frontend patterns
- [ ] T034 Verify no breaking changes to existing chat functionality (message sending, receiving, scrolling)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 theme store but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1 ThemeSelector component but independently testable

### Within Each User Story

**User Story 1** (Switch Between Themes):
- ThemeSelector component before ChatInterface integration
- Component updates can happen in parallel (T014 has [P] potential for MessageBubble, MessageInput, MessageList)

**User Story 2** (Persistence):
- localStorage logic before error handling
- Testing tasks can happen after implementation

**User Story 3** (Explore Options):
- UI enhancements before testing
- All testing tasks can run in parallel after implementation

### Parallel Opportunities

**Within Setup (Phase 1)**:
- T002 (CSS themes) and T003 (import themes.css) can run in parallel after T001

**Within Foundational (Phase 2)**:
- T005 (theme definitions) and T006 (validation utils) can run in parallel
- After T005-T006 complete: T007 (store), T008 (hook), T009 (FOUC script) can run in parallel

**Within User Story 1 (Phase 3)**:
- After T011 created: T012 (accessibility), T013 (integration), T014 (component updates) can run in parallel

**Within Polish (Phase 6)**:
- T029 (accessibility), T030 (logging), T031 (edge cases), T032 (docs) can all run in parallel

---

## Parallel Example: User Story 1

```bash
# After ThemeSelector component exists (T011 complete):
# Launch these tasks in parallel:

Task T012: "Add aria-labels and keyboard navigation to ThemeSelector"
Task T013: "Integrate ThemeSelector into ChatInterface header"
Task T014: "Update MessageBubble, MessageInput, MessageList to use theme-aware classes"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004) → ~1-2 hours
2. Complete Phase 2: Foundational (T005-T010) → ~4-6 hours
3. Complete Phase 3: User Story 1 (T011-T016) → ~4-6 hours
4. **STOP and VALIDATE**: Test theme switching independently
5. Deploy/demo if ready → **MVP COMPLETE** ✅

**Total MVP Effort**: ~1-2 days

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! - Core theme switching)
3. Add User Story 2 → Test independently → Deploy/Demo (Theme persistence)
4. Add User Story 3 → Test independently → Deploy/Demo (Enhanced theme discovery)
5. Add Polish → Final validation → Deploy/Demo (Production-ready)

**Total Full Feature Effort**: ~5-8 days

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (~1-2 days)
2. Once Foundational is done:
   - Developer A: User Story 1 (T011-T016) - 1 day
   - Developer B: User Story 2 (T017-T022) - can start T017-T019 in parallel - 1 day
   - Developer C: User Story 3 (T023-T028) - can start T023-T024 in parallel - 1 day
3. Stories integrate naturally (US2 extends US1's store, US3 extends US1's component)
4. Team completes Polish together (~1 day)

**Total Parallel Effort**: ~3-4 days with 3 developers

---

## Accessibility Compliance

All themes MUST meet these standards:

- ✅ Normal text contrast: ≥ 4.5:1 (WCAG AA)
- ✅ Large text contrast: ≥ 3:1 (WCAG AA)
- ✅ UI components contrast: ≥ 3:1 (WCAG AA)
- ✅ Keyboard navigation support
- ✅ ARIA labels for screen readers
- ✅ Focus indicators visible in all themes

**Validation**: Run automated checks in T029, manual testing throughout implementation

---

## Success Criteria Mapping

| Success Criteria | Verified By |
|------------------|-------------|
| SC-001: Theme selector discoverable within 5 seconds | T013 (placement in header) |
| SC-002: Theme changes apply within 1 second | T015 (verify immediate updates) |
| SC-003: Preferences persist with 100% reliability | T017, T022 (localStorage persistence) |
| SC-004: WCAG AA compliance for all themes | T029 (accessibility validation) |
| SC-005: No loss of functionality during theme switch | T016, T031, T034 (edge case testing) |
| SC-006: No flash of default theme on load | T020 (FOUC prevention) |
| SC-007: 95% users can change theme on first attempt | T023-T028 (clear UI, tooltips) |

---

## Notes

- **[P] tasks**: Different files, no dependencies, can run in parallel
- **[Story] label**: Maps task to specific user story for traceability
- **File paths**: All paths are absolute from repository root
- **Commit strategy**: Commit after each task or logical group
- **Testing**: No automated tests explicitly requested - focus on manual validation at checkpoints
- **WCAG compliance**: Critical requirement - validate in T029 before considering feature complete
- **FOUC prevention**: Critical for user experience - T009 and T020 are high priority

---

## Risk Mitigation

### High Priority Risks

1. **localStorage unavailable** → Mitigated by T018 (error handling, graceful degradation)
2. **FOUC on initial load** → Mitigated by T009 (inline script in index.html)
3. **Breaking existing chat functionality** → Mitigated by T034 (regression testing)
4. **Accessibility compliance failure** → Mitigated by T029 (validation before completion)

### Medium Priority Risks

1. **Rapid theme switching causes jank** → Mitigated by T016 (performance testing)
2. **Theme selector not discoverable** → Mitigated by T013 (header placement), T023 (clear labels)
3. **Mobile usability issues** → Mitigated by T028 (mobile testing)

---

**Tasks Ready for Implementation** ✅  
**Total Tasks**: 34  
**MVP Tasks**: 16 (T001-T016)  
**Parallel Opportunities**: High (multiple tasks can run concurrently in each phase)  
**Estimated Total Effort**: 5-8 days (single developer), 3-4 days (team of 3)
