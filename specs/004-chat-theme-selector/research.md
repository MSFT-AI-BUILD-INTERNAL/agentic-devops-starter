# Research: Chat Theme Selector

**Phase**: 0 - Outline & Research  
**Date**: 2025-01-25  
**Status**: Complete

## Overview

This document consolidates research findings for implementing a theme selector in the React + TypeScript chat interface. The research covers architectural approaches, accessibility requirements, performance optimizations, and integration patterns with the existing Zustand + Tailwind CSS stack.

---

## 1. Theme Architecture Strategy

### Decision: CSS Custom Properties (CSS Variables) + Tailwind CSS

**Rationale**:
- **Performance**: CSS variables enable instant theme switching without re-rendering React components. The browser handles repainting natively.
- **Maintainability**: Centralized theme definitions in CSS with semantic naming (e.g., `--color-bg-primary`, `--color-text-primary`)
- **Tailwind Integration**: Tailwind CSS 3.4+ supports CSS variables in `tailwind.config.js` via `colors` configuration, allowing seamless use of utility classes like `bg-primary` that reference theme variables
- **Zero JS Overhead**: No inline styles or style prop manipulation needed—themes are pure CSS with JS only managing the active theme class on root element

**Alternatives Considered**:
1. **CSS-in-JS (styled-components, emotion)**: Rejected due to runtime cost, additional bundle size, and unnecessary complexity for this use case. Tailwind CSS already provides the styling infrastructure.
2. **Tailwind Dark Mode Plugin**: Rejected as insufficient—only supports light/dark toggle, not extensible to multiple custom themes
3. **Inline Styles with JS**: Rejected due to poor performance (triggers re-renders), verbose code, and lack of pseudo-class support

**Implementation Pattern**:
```css
/* themes.css */
[data-theme="light"] {
  --color-bg-primary: #ffffff;
  --color-text-primary: #1f2937;
  --color-accent: #2563eb;
  /* ...full palette */
}

[data-theme="dark"] {
  --color-bg-primary: #1f2937;
  --color-text-primary: #f9fafb;
  --color-accent: #60a5fa;
  /* ...full palette */
}
```

```typescript
// Apply theme by setting data attribute
document.documentElement.setAttribute('data-theme', 'dark');
```

---

## 2. State Management Pattern

### Decision: Zustand Store with localStorage Middleware

**Rationale**:
- **Consistency**: Zustand is already used for chat state (`chatStore.ts`). Adding `themeStore.ts` maintains architectural consistency.
- **Simplicity**: Zustand's minimal API (no providers, no context) makes theme state globally accessible without prop drilling
- **Persistence**: Zustand's `persist` middleware provides out-of-the-box localStorage synchronization with automatic serialization/deserialization
- **TypeScript Safety**: Full type inference with TypeScript 5.3

**Alternatives Considered**:
1. **React Context API**: Rejected due to unnecessary re-renders, provider boilerplate, and lack of built-in persistence
2. **Redux**: Rejected as overkill for simple theme state (3-5 fields)
3. **Local Component State**: Rejected as theme needs to be global and persistent

**Store Structure**:
```typescript
interface ThemeStore {
  currentTheme: ThemeId;           // 'light' | 'dark' | 'high-contrast'
  availableThemes: Theme[];        // Theme definitions
  setTheme: (themeId: ThemeId) => void;
  initializeTheme: () => void;     // Load from localStorage on mount
}
```

**Persistence Strategy**:
- Store only `currentTheme` ID in localStorage (key: `app-theme-preference`)
- Theme definitions (colors, metadata) remain in code (not user-configurable)
- Graceful degradation: If localStorage fails, fall back to default theme without errors

---

## 3. Accessibility Compliance (WCAG AA)

### Decision: Automated Contrast Validation + Manual Verification

**Rationale**:
- **Legal Requirement**: WCAG AA is the industry standard and often legally required
- **Color Contrast Ratios**: 
  - Normal text (< 18pt): 4.5:1 minimum
  - Large text (≥ 18pt or 14pt bold): 3:1 minimum
  - UI components and graphical objects: 3:1 minimum
- **Validation Approach**: Use `tinycolor2` or similar library to compute contrast ratios programmatically during development

**Alternatives Considered**:
1. **Manual Testing Only**: Rejected as error-prone and not scalable
2. **Runtime Validation**: Rejected due to performance overhead (validation should happen at build/test time)

**Implementation**:
- Create utility function `validateThemeContrast(theme: Theme): ValidationResult`
- Run validation in unit tests for each theme
- Document contrast ratios in `data-model.md` for each theme

**Tools**:
- Development: WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/)
- Testing: axe-core or similar library in E2E tests

**Required Checks**:
- ✅ Body text vs. background
- ✅ Message bubble text vs. bubble background
- ✅ Button text vs. button background
- ✅ Input text vs. input background
- ✅ Link text vs. background
- ✅ Icon colors vs. background

---

## 4. Theme Definitions

### Decision: 3 Initial Themes (Light, Dark, High Contrast)

**Rationale**:
- **Light Theme**: Default, optimized for bright environments, matches current design
- **Dark Theme**: Reduces eye strain in low-light, conserves battery on OLED screens
- **High Contrast**: Accessibility-focused for users with visual impairments, exceeds WCAG AAA (7:1 for normal text)

**Alternatives Considered**:
1. **Only Light/Dark**: Rejected as insufficient for accessibility requirements (spec requires "at least three themes")
2. **Multiple Color Schemes (blue, green, purple)**: Deferred to post-MVP—focus on accessibility variants first

**Color Palette Structure** (per theme):
```typescript
interface ThemeColors {
  // Backgrounds
  bgPrimary: string;      // Main app background
  bgSecondary: string;    // Card/panel backgrounds
  bgTertiary: string;     // Hover/subtle backgrounds
  
  // Text
  textPrimary: string;    // Body text
  textSecondary: string;  // Muted/helper text
  textInverse: string;    // Text on colored backgrounds
  
  // Accents
  accent: string;         // Primary brand color
  accentHover: string;    // Hover state
  
  // UI Elements
  border: string;         // Borders, dividers
  messageBubbleUser: string;
  messageBubbleAssistant: string;
  
  // Status
  success: string;
  error: string;
  warning: string;
}
```

---

## 5. Performance Optimization

### Decision: Immediate Theme Switch + Prevent FOUC

**Rationale**:
- **User Expectation**: Theme switch should feel instant (<100ms)
- **FOUC Prevention**: Theme must load before first paint to avoid flash of default theme
- **Strategy**: 
  1. Read theme preference from localStorage in blocking script tag in `index.html` (before React loads)
  2. Set `data-theme` attribute on `<html>` element immediately
  3. React mounts with correct theme already applied

**Alternatives Considered**:
1. **Load Theme After React Mount**: Rejected due to visible FOUC
2. **Server-Side Rendering (SSR)**: Not applicable—frontend is SPA with Vite
3. **Theme Transition Animations**: Considered for post-MVP (can cause jank if not optimized)

**Implementation**:
```html
<!-- index.html -->
<script>
  // Runs before React loads
  const savedTheme = localStorage.getItem('app-theme-preference') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
</script>
```

**Performance Metrics**:
- Theme switch: <100ms (CSS variable updates are synchronous)
- localStorage read: <10ms (blocking acceptable due to size: ~10 bytes)
- No layout shift or reflow

---

## 6. Component Integration Pattern

### Decision: Theme Selector in Chat Header + Global Hook

**Rationale**:
- **Discoverability**: Header is always visible and follows common UI patterns (GitHub, VS Code, Slack)
- **Accessibility**: Keyboard navigable dropdown with ARIA labels
- **Global Access**: `useTheme()` hook allows any component to read/update theme

**Alternatives Considered**:
1. **Settings Modal**: Rejected as less discoverable and requires extra clicks
2. **Sidebar**: Rejected as chat interface has no sidebar
3. **Right-Click Context Menu**: Rejected as poor mobile support

**Component Structure**:
```typescript
// ThemeSelector.tsx
export function ThemeSelector() {
  const { currentTheme, availableThemes, setTheme } = useTheme();
  
  return (
    <Dropdown>
      {availableThemes.map(theme => (
        <DropdownItem 
          key={theme.id}
          selected={theme.id === currentTheme}
          onClick={() => setTheme(theme.id)}
        >
          {theme.name}
        </DropdownItem>
      ))}
    </Dropdown>
  );
}
```

**Integration Point**: Add `<ThemeSelector />` to `ChatInterface.tsx` header, next to "New Conversation" button

---

## 7. Error Handling & Edge Cases

### Decision: Graceful Degradation + Validation

**Rationale**: System must remain functional even when localStorage is unavailable or corrupted

**Scenarios & Resolutions**:

1. **localStorage Disabled/Unavailable**:
   - **Detection**: Wrap access in try-catch
   - **Fallback**: Use in-memory state only (theme persists for session)
   - **User Impact**: No persistence, but theme selection still works

2. **Corrupted Theme Preference**:
   - **Detection**: Validate theme ID against `availableThemes` array
   - **Fallback**: Reset to default theme ('light')
   - **Action**: Clear corrupted data from localStorage

3. **Rapid Theme Switching**:
   - **Risk**: Multiple rapid clicks could cause UI jank
   - **Mitigation**: Debounce is NOT needed—CSS variable updates are synchronous and fast
   - **Verification**: E2E test with rapid clicks (acceptance criteria)

4. **Theme Switch During User Input**:
   - **Risk**: Losing focus or input data
   - **Mitigation**: Theme changes only update CSS—React component state untouched
   - **Verification**: E2E test (user types message, switches theme, continues typing)

5. **Invalid Theme in localStorage**:
   ```typescript
   const loadTheme = (): ThemeId => {
     try {
       const saved = localStorage.getItem('app-theme-preference');
       if (saved && isValidThemeId(saved)) {
         return saved as ThemeId;
       }
     } catch (error) {
       logger.error('Failed to load theme preference', error);
     }
     return DEFAULT_THEME;
   };
   ```

---

## 8. Testing Strategy

### Decision: Multi-Layer Testing (Unit + Integration + E2E + Accessibility)

**Rationale**: Theme system touches UI, state, persistence, and accessibility—requires comprehensive coverage

**Test Coverage**:

1. **Unit Tests (Vitest)**:
   - `themeStore.ts`: State transitions, localStorage integration
   - `themeUtils.ts`: Contrast validation, theme validation
   - `useTheme.ts`: Hook behavior

2. **Integration Tests (Testing Library)**:
   - `ThemeSelector.tsx`: User interactions (click, keyboard nav)
   - Theme application to components

3. **E2E Tests (Playwright)**:
   - User story 1: Switch themes, verify all UI updates
   - User story 2: Persistence across sessions
   - User story 3: Theme selector UI behavior
   - Edge cases: localStorage disabled, rapid switching

4. **Accessibility Tests**:
   - Automated: axe-core checks in E2E tests
   - Manual: Screen reader testing (VoiceOver, NVDA)
   - Contrast validation: Programmatic checks in unit tests

**Acceptance Criteria Mapping**:
- SC-001 (Discoverability): E2E test measuring time to locate selector
- SC-002 (Speed): Performance test measuring theme switch time
- SC-003 (Persistence): E2E test with browser restart
- SC-004 (Accessibility): Automated contrast validation
- SC-005 (Functionality): E2E tests for all user stories
- SC-006 (FOUC Prevention): E2E test checking initial render
- SC-007 (Usability): Manual testing / user testing

---

## 9. Migration Strategy

### Decision: Non-Breaking Incremental Rollout

**Rationale**: Existing users should see zero disruption

**Phases**:
1. **Phase 1**: Add theme system (default: light theme—matches current UI)
2. **Phase 2**: Add ThemeSelector component (opt-in feature)
3. **Phase 3**: Test with internal users
4. **Phase 4**: Production release

**Backwards Compatibility**:
- Users without saved preference: Default to 'light' (current behavior)
- Existing CSS classes: Remain functional (Tailwind utilities still work)
- No breaking changes to components

---

## 10. Technology-Specific Best Practices

### React 18.2
- **Concurrent Features**: Not needed for theme (synchronous state updates)
- **useEffect for Init**: Use to load theme preference on mount
- **Memoization**: Not needed—theme changes are infrequent

### TypeScript 5.3
- **Strict Mode**: Enabled (`tsconfig.json`)
- **Type Safety**: All theme types fully defined (no `any`)
- **Discriminated Unions**: Use for theme IDs: `type ThemeId = 'light' | 'dark' | 'high-contrast'`

### Tailwind CSS 3.4
- **Config Extension**: 
  ```javascript
  // tailwind.config.js
  module.exports = {
    theme: {
      extend: {
        colors: {
          primary: 'var(--color-bg-primary)',
          secondary: 'var(--color-bg-secondary)',
          // ...map all CSS variables
        }
      }
    }
  }
  ```
- **JIT Mode**: Enabled by default in Tailwind 3.x—supports dynamic class generation

### Zustand 5.0
- **Persist Middleware**: 
  ```typescript
  import { persist } from 'zustand/middleware';
  
  export const useThemeStore = create<ThemeStore>()(
    persist(
      (set) => ({...}),
      { name: 'app-theme-preference' }
    )
  );
  ```
- **Immer Middleware**: Not needed for simple theme state

### Vite
- **Build Optimization**: CSS variables work seamlessly with Vite's CSS handling
- **Dev Mode**: Hot module replacement (HMR) works with theme changes

---

## 11. Open Questions & Risks

### Resolved
✅ **Q**: Should themes be user-customizable (color pickers)?  
**A**: No—MVP focuses on pre-defined themes. Custom themes deferred to future iteration.

✅ **Q**: Should theme preference sync across devices?  
**A**: No—localStorage is device-specific. Cross-device sync requires backend (out of scope).

✅ **Q**: Should theme affect message history?  
**A**: Yes—all rendered messages update immediately (CSS variables ensure retroactive styling).

### Remaining Risks
⚠️ **Risk**: Browser localStorage quota exceeded (rare but possible)  
**Mitigation**: Theme preference is ~10 bytes. Quota is typically 5-10MB. Very low risk.

⚠️ **Risk**: User has browser extension that modifies styles  
**Mitigation**: Cannot control. Document as known limitation.

---

## Summary & Next Steps

### Key Decisions
1. ✅ CSS Variables + Tailwind CSS for theme architecture
2. ✅ Zustand store with persist middleware for state management
3. ✅ 3 initial themes: Light, Dark, High Contrast (all WCAG AA compliant)
4. ✅ FOUC prevention via inline script in index.html
5. ✅ Theme selector in chat header
6. ✅ Comprehensive testing strategy (unit + E2E + accessibility)

### Phase 1 Deliverables (Next)
- `data-model.md`: Define Theme, ThemePreference, and ThemeConfig entities
- `contracts/theme-types.ts`: TypeScript interfaces and type definitions
- `quickstart.md`: Developer guide for using and extending theme system

### Estimated Effort
- Implementation: 3-5 days (8-10 files new/modified)
- Testing: 2-3 days (unit + E2E + accessibility)
- Total: ~1 week sprint

---

**Research Complete** ✅  
All NEEDS CLARIFICATION items resolved. Ready for Phase 1 (Design & Contracts).
