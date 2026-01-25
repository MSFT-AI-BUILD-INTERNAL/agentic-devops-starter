# Quickstart Guide: Chat Theme Selector

**Audience**: Frontend developers implementing or extending the theme system  
**Version**: 1.0.0  
**Date**: 2025-01-25

---

## Overview

This guide provides a practical introduction to using and extending the chat theme selector system. After reading this, you'll be able to:

1. ✅ Apply themes to components using CSS variables
2. ✅ Use the `useTheme()` hook for theme operations
3. ✅ Create new custom themes
4. ✅ Validate theme accessibility
5. ✅ Debug theme-related issues

---

## 🚀 Quick Start (5 minutes)

### 1. Using Themes in Components

All theme colors are available as CSS custom properties (CSS variables). Use them directly in Tailwind classes:

```tsx
// ✅ CORRECT: Use theme-aware Tailwind classes
function MyComponent() {
  return (
    <div className="bg-primary text-primary border border-border">
      <p className="text-secondary">This text respects the current theme</p>
      <button className="bg-accent text-inverse hover:bg-accent-hover">
        Click me
      </button>
    </div>
  );
}
```

```tsx
// ❌ WRONG: Hard-coded colors bypass theme system
function MyComponent() {
  return (
    <div className="bg-white text-gray-900 border border-gray-300">
      {/* This won't change when user switches themes */}
    </div>
  );
}
```

**Available Tailwind Classes** (defined in `tailwind.config.js`):
- Backgrounds: `bg-primary`, `bg-secondary`, `bg-tertiary`
- Text: `text-primary`, `text-secondary`, `text-inverse`
- Accents: `bg-accent`, `hover:bg-accent-hover`, `bg-accent-light`
- Borders: `border-border`, `focus:ring-border-focus`
- Message bubbles: `bg-message-user`, `text-message-user`, etc.
- Status: `bg-success`, `bg-error`, `bg-warning`, `bg-info`

### 2. Using the `useTheme()` Hook

Access theme state and operations from any component:

```tsx
import { useTheme } from '../hooks/useTheme';

function ThemeSelector() {
  const { currentTheme, availableThemes, setTheme, isThemeLoading } = useTheme();
  
  return (
    <select 
      value={currentTheme} 
      onChange={(e) => setTheme(e.target.value as ThemeId)}
      disabled={isThemeLoading}
    >
      {availableThemes.map(theme => (
        <option key={theme.id} value={theme.id}>
          {theme.name}
        </option>
      ))}
    </select>
  );
}
```

**Hook API**:
```typescript
interface UseThemeReturn {
  currentTheme: ThemeId;              // Currently active theme ID
  currentThemeObject: Theme;          // Full theme object with colors
  availableThemes: Theme[];           // All available themes
  setTheme: (themeId: ThemeId) => void; // Switch themes
  isThemeLoading: boolean;            // Loading state (initial mount)
}
```

### 3. Programmatic Theme Switching

```tsx
import { useTheme } from '../hooks/useTheme';

function DarkModeToggle() {
  const { currentTheme, setTheme } = useTheme();
  
  const toggleDarkMode = () => {
    setTheme(currentTheme === 'dark' ? 'light' : 'dark');
  };
  
  return (
    <button onClick={toggleDarkMode}>
      {currentTheme === 'dark' ? '☀️ Light' : '🌙 Dark'}
    </button>
  );
}
```

---

## 📦 Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     React Components                         │
│  (ChatInterface, MessageBubble, ThemeSelector, etc.)        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ useTheme()
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                   themeStore (Zustand)                       │
│  - currentTheme: ThemeId                                     │
│  - availableThemes: Theme[]                                  │
│  - setTheme(id): void                                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ persist middleware
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                  localStorage                                │
│  Key: 'app-theme-preference'                                 │
│  Value: { themeId: 'dark', updatedAt: '2025-01-25...' }    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ On page load
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              <html data-theme="dark">                        │
│  CSS variables applied via themes.css                        │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
app/frontend/src/
├── stores/
│   └── themeStore.ts        # Zustand store with persistence
├── hooks/
│   └── useTheme.ts          # React hook (wrapper around store)
├── components/
│   └── ThemeSelector.tsx    # UI component for theme selection
├── types/
│   └── theme.ts             # TypeScript types (imported from contracts)
├── utils/
│   └── themeUtils.ts        # Validation, contrast checking
└── styles/
    └── themes.css           # CSS custom properties per theme
```

---

## 🎨 Creating a New Theme

### Step 1: Define the Theme Object

Create your theme in `src/utils/themes.ts` (or wherever themes are defined):

```typescript
import type { Theme } from '../types/theme';

export const myCustomTheme: Theme = {
  id: 'my-custom',  // Add to ThemeId union type
  name: 'My Custom Theme',
  description: 'A unique theme with custom colors',
  
  colors: {
    // Backgrounds
    bgPrimary: '#f0f4f8',
    bgSecondary: '#e2e8f0',
    bgTertiary: '#cbd5e0',
    
    // Text
    textPrimary: '#2d3748',
    textSecondary: '#4a5568',
    textInverse: '#ffffff',
    
    // Accents
    accent: '#5a67d8',
    accentHover: '#4c51bf',
    accentLight: '#c3dafe',
    
    // UI elements
    border: '#cbd5e0',
    borderFocus: '#5a67d8',
    
    // Message bubbles
    messageBubbleUser: '#5a67d8',
    messageBubbleUserText: '#ffffff',
    messageBubbleAssistant: '#e2e8f0',
    messageBubbleAssistantText: '#2d3748',
    messageBubbleTool: '#fef5e7',
    messageBubbleToolText: '#744210',
    
    // Status
    success: '#38a169',
    error: '#e53e3e',
    warning: '#d69e2e',
    info: '#3182ce',
    
    // Interactive
    hoverOverlay: 'rgba(0, 0, 0, 0.05)',
    activeOverlay: 'rgba(0, 0, 0, 0.1)',
  },
  
  metadata: {
    contrastRatios: {
      normalText: 8.5,    // Measured: textPrimary vs bgPrimary
      largeText: 8.5,
      uiComponents: 4.2,
    },
    version: '1.0.0',
    wcagLevel: 'AAA',
    author: 'Your Name',
    tags: ['custom', 'blue'],
  },
};
```

### Step 2: Add to ThemeId Type

Update the `ThemeId` type in `types/theme.ts`:

```typescript
// Before
export type ThemeId = 'light' | 'dark' | 'high-contrast';

// After
export type ThemeId = 'light' | 'dark' | 'high-contrast' | 'my-custom';
```

### Step 3: Register in ThemeConfig

Add to the global theme configuration:

```typescript
// src/config/themeConfig.ts
export const themeConfig: ThemeConfig = {
  themes: [
    lightTheme,
    darkTheme,
    highContrastTheme,
    myCustomTheme,  // ← Add here
  ],
  defaultTheme: 'light',
  storageKey: 'app-theme-preference',
  allowCustomThemes: false,
};
```

### Step 4: Add CSS Variables

Update `src/styles/themes.css`:

```css
[data-theme="my-custom"] {
  --color-bg-primary: #f0f4f8;
  --color-bg-secondary: #e2e8f0;
  --color-bg-tertiary: #cbd5e0;
  
  --color-text-primary: #2d3748;
  --color-text-secondary: #4a5568;
  --color-text-inverse: #ffffff;
  
  --color-accent: #5a67d8;
  --color-accent-hover: #4c51bf;
  --color-accent-light: #c3dafe;
  
  --color-border: #cbd5e0;
  --color-border-focus: #5a67d8;
  
  /* Message bubbles */
  --color-message-user: #5a67d8;
  --color-message-user-text: #ffffff;
  --color-message-assistant: #e2e8f0;
  --color-message-assistant-text: #2d3748;
  --color-message-tool: #fef5e7;
  --color-message-tool-text: #744210;
  
  /* Status */
  --color-success: #38a169;
  --color-error: #e53e3e;
  --color-warning: #d69e2e;
  --color-info: #3182ce;
  
  /* Interactive */
  --color-hover-overlay: rgba(0, 0, 0, 0.05);
  --color-active-overlay: rgba(0, 0, 0, 0.1);
}
```

### Step 5: Validate Accessibility

Run the contrast validation utility:

```typescript
import { validateTheme } from '../utils/themeUtils';

const result = validateTheme(myCustomTheme);

if (!result.valid) {
  console.error('Theme validation failed:', result.errors);
} else {
  console.log('✅ Theme is WCAG AA compliant');
}
```

**Manual Verification**:
1. Use WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
2. Check key combinations:
   - `textPrimary` vs `bgPrimary` (should be ≥ 4.5:1)
   - `messageBubbleUserText` vs `messageBubbleUser` (should be ≥ 4.5:1)
   - `border` vs `bgPrimary` (should be ≥ 3:1)

---

## 🧪 Testing Your Theme

### Manual Testing Checklist

1. **Visual Inspection**:
   ```bash
   npm run dev
   ```
   - Open the app in browser
   - Switch to your custom theme using ThemeSelector
   - Verify all UI elements are readable and styled correctly
   - Check all pages/views (chat, settings, etc.)

2. **Contrast Testing**:
   - Use browser DevTools to inspect color values
   - Verify text is readable on all backgrounds
   - Check hover states, focus states, active states

3. **Cross-Browser Testing**:
   - Chrome, Firefox, Safari, Edge
   - Verify colors render consistently

### Automated Testing

**Unit Test (Vitest)**:
```typescript
import { describe, it, expect } from 'vitest';
import { myCustomTheme } from './themes';
import { validateTheme } from '../utils/themeUtils';

describe('myCustomTheme', () => {
  it('should pass WCAG AA validation', () => {
    const result = validateTheme(myCustomTheme);
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });
  
  it('should have all required color properties', () => {
    const requiredColors: (keyof ThemeColors)[] = [
      'bgPrimary', 'bgSecondary', 'textPrimary', 'accent', 'border',
      // ...list all required colors
    ];
    
    requiredColors.forEach(colorKey => {
      expect(myCustomTheme.colors[colorKey]).toBeDefined();
      expect(typeof myCustomTheme.colors[colorKey]).toBe('string');
    });
  });
  
  it('should have contrast ratios above minimums', () => {
    expect(myCustomTheme.metadata.contrastRatios.normalText).toBeGreaterThanOrEqual(4.5);
    expect(myCustomTheme.metadata.contrastRatios.largeText).toBeGreaterThanOrEqual(3.0);
  });
});
```

**E2E Test (Playwright)**:
```typescript
import { test, expect } from '@playwright/test';

test('custom theme applies correctly', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  // Select custom theme
  await page.click('[data-testid="theme-selector"]');
  await page.click('text=My Custom Theme');
  
  // Verify theme is applied
  const html = page.locator('html');
  await expect(html).toHaveAttribute('data-theme', 'my-custom');
  
  // Verify colors are applied
  const chatHeader = page.locator('[data-testid="chat-header"]');
  const bgColor = await chatHeader.evaluate((el) => 
    window.getComputedStyle(el).backgroundColor
  );
  
  expect(bgColor).toBe('rgb(90, 103, 216)'); // #5a67d8 in RGB
});
```

---

## 🔧 Common Tasks

### Adjusting Existing Theme Colors

```typescript
// Option 1: Modify theme definition directly
export const darkTheme: Theme = {
  // ...
  colors: {
    // ...
    accent: '#60a5fa',  // Change from old color
    // ...
  },
  // ...
};

// Option 2: Create a theme variant
export const darkThemeAlt: Theme = {
  ...darkTheme,
  id: 'dark-alt',
  name: 'Dark Theme (Alt)',
  colors: {
    ...darkTheme.colors,
    accent: '#34d399',  // Override specific colors
  },
};
```

### Reading Current Theme in Non-React Code

```typescript
// Use Zustand store directly
import { useThemeStore } from './stores/themeStore';

function myUtilityFunction() {
  const currentTheme = useThemeStore.getState().currentTheme;
  console.log('Current theme:', currentTheme);
}
```

### Resetting Theme to Default

```typescript
import { useTheme } from '../hooks/useTheme';

function ResetButton() {
  const { setTheme } = useTheme();
  
  const handleReset = () => {
    setTheme('light'); // Reset to default
    localStorage.removeItem('app-theme-preference'); // Clear saved preference
  };
  
  return <button onClick={handleReset}>Reset Theme</button>;
}
```

### Detecting System Theme Preference

```typescript
// Detect user's OS theme preference
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

// Use as fallback when no saved preference exists
const initialTheme = savedPreference || (prefersDark ? 'dark' : 'light');
```

---

## 🐛 Debugging

### Theme Not Applying

**Problem**: Theme selector changes but UI doesn't update

**Checklist**:
1. ✅ Check `<html>` element has `data-theme` attribute:
   ```javascript
   console.log(document.documentElement.getAttribute('data-theme'));
   ```

2. ✅ Verify CSS variables are defined in `themes.css`:
   ```javascript
   console.log(getComputedStyle(document.documentElement).getPropertyValue('--color-bg-primary'));
   ```

3. ✅ Ensure components use theme-aware classes (not hard-coded colors)

4. ✅ Check browser DevTools → Elements → Computed styles for CSS variable values

### FOUC (Flash of Unstyled Content)

**Problem**: Default theme flashes before user's saved theme loads

**Solution**: Ensure blocking script in `index.html` runs **before** React:
```html
<!DOCTYPE html>
<html>
<head>
  <!-- This MUST be in <head>, before any React code -->
  <script>
    (function() {
      try {
        const theme = localStorage.getItem('app-theme-preference');
        if (theme) {
          const parsed = JSON.parse(theme);
          document.documentElement.setAttribute('data-theme', parsed.themeId);
        }
      } catch (e) {
        // Ignore errors, fall back to default theme
      }
    })();
  </script>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

### localStorage Not Persisting

**Problem**: Theme resets on page reload

**Checklist**:
1. ✅ Check browser allows localStorage (not in incognito/private mode)
2. ✅ Verify Zustand persist middleware is configured:
   ```typescript
   import { persist } from 'zustand/middleware';
   
   export const useThemeStore = create<ThemeStore>()(
     persist(
       (set) => ({ /* store implementation */ }),
       { name: 'app-theme-preference' }
     )
   );
   ```
3. ✅ Check browser DevTools → Application → Local Storage

### Contrast Validation Fails

**Problem**: Theme fails WCAG checks

**Tools**:
- **WebAIM Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Chrome DevTools**: Inspect element → Accessibility pane shows contrast ratio
- **Automated validation**: Run `validateTheme()` utility

**Fix**:
- Adjust foreground or background color to increase contrast
- Use darker text on light backgrounds
- Use lighter text on dark backgrounds
- Test with actual users (especially those with visual impairments)

---

## 📚 Additional Resources

### Documentation
- [Full Data Model](./data-model.md) - Complete entity definitions
- [Type Definitions](./contracts/theme-types.ts) - TypeScript contracts
- [Research Document](./research.md) - Architecture decisions
- [Implementation Plan](./plan.md) - Project structure

### External Resources
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Tailwind CSS Variables](https://tailwindcss.com/docs/customizing-colors#using-css-variables)
- [Zustand Documentation](https://docs.pmnd.rs/zustand/getting-started/introduction)
- [React 18 Docs](https://react.dev/)

### Tools
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Coolors Palette Generator](https://coolors.co/)
- [Adobe Color Accessibility Tools](https://color.adobe.com/create/color-accessibility)

---

## ✅ Checklist: Adding a New Theme

Use this checklist when creating a new theme:

- [ ] Define `Theme` object with all required fields
- [ ] Add theme ID to `ThemeId` type union
- [ ] Register theme in `ThemeConfig`
- [ ] Add CSS variables to `themes.css`
- [ ] Validate contrast ratios (≥ 4.5:1 for normal text)
- [ ] Write unit tests for theme validation
- [ ] Write E2E test for theme application
- [ ] Test in multiple browsers
- [ ] Test keyboard navigation and focus states
- [ ] Test with screen reader (accessibility)
- [ ] Document theme purpose and use cases
- [ ] Update this quickstart guide with examples (if needed)

---

**Questions?** Check the research document (`research.md`) or data model (`data-model.md`) for deeper technical details.

Happy theming! 🎨
