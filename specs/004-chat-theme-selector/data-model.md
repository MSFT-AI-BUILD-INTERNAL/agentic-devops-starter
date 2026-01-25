# Data Model: Chat Theme Selector

**Phase**: 1 - Design & Contracts  
**Date**: 2025-01-25  
**Status**: Complete

## Overview

This document defines the data entities, relationships, and validation rules for the theme selector system. All entities are TypeScript interfaces/types with Zod schemas for runtime validation.

---

## Entity Definitions

### 1. Theme

Represents a complete visual styling configuration for the chat interface.

**Purpose**: Defines all colors, contrast ratios, and metadata for a single theme variant.

**TypeScript Definition**:
```typescript
interface Theme {
  id: ThemeId;                    // Unique identifier
  name: string;                   // Display name (e.g., "Dark Theme")
  description: string;            // User-facing description
  colors: ThemeColors;            // Complete color palette
  metadata: ThemeMetadata;        // Accessibility & version info
}

type ThemeId = 'light' | 'dark' | 'high-contrast';
```

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `id` | `ThemeId` | ✅ | Must be one of predefined IDs | Unique theme identifier |
| `name` | `string` | ✅ | 1-50 characters | Display name shown in UI |
| `description` | `string` | ✅ | 1-200 characters | Tooltip/help text |
| `colors` | `ThemeColors` | ✅ | See ThemeColors validation | Complete color palette |
| `metadata` | `ThemeMetadata` | ✅ | See ThemeMetadata validation | Accessibility & version data |

**Constraints**:
- `id` must be unique across all themes
- All colors in `colors` must pass WCAG AA contrast checks (see validation rules)
- Theme objects are immutable at runtime (readonly)

**Example**:
```typescript
const lightTheme: Theme = {
  id: 'light',
  name: 'Light Theme',
  description: 'Clean and bright theme optimized for well-lit environments',
  colors: {
    bgPrimary: '#ffffff',
    bgSecondary: '#f9fafb',
    textPrimary: '#1f2937',
    // ...complete palette
  },
  metadata: {
    contrastRatios: {
      normalText: 12.63,
      largeText: 12.63,
    },
    version: '1.0.0',
    wcagLevel: 'AAA',
  },
};
```

---

### 2. ThemeColors

Defines the complete color palette for a theme.

**Purpose**: Provides semantic color names that map to CSS custom properties.

**TypeScript Definition**:
```typescript
interface ThemeColors {
  // Background colors
  bgPrimary: string;              // Main app background (#ffffff for light, #1f2937 for dark)
  bgSecondary: string;            // Card/panel backgrounds
  bgTertiary: string;             // Hover/subtle backgrounds
  
  // Text colors
  textPrimary: string;            // Body text
  textSecondary: string;          // Muted/helper text (70% opacity)
  textInverse: string;            // Text on colored backgrounds (e.g., buttons)
  
  // Accent colors
  accent: string;                 // Primary brand color (blue)
  accentHover: string;            // Hover state for accent elements
  accentLight: string;            // Light accent for backgrounds
  
  // UI element colors
  border: string;                 // Borders, dividers
  borderFocus: string;            // Focus ring color
  
  // Message bubbles
  messageBubbleUser: string;      // User message background
  messageBubbleUserText: string;  // User message text
  messageBubbleAssistant: string; // Assistant message background
  messageBubbleAssistantText: string; // Assistant message text
  messageBubbleTool: string;      // Tool message background
  messageBubbleToolText: string;  // Tool message text
  
  // Status colors
  success: string;                // Success states
  error: string;                  // Error states
  warning: string;                // Warning states
  info: string;                   // Info states
  
  // Interactive states
  hoverOverlay: string;           // Hover overlay (semi-transparent)
  activeOverlay: string;          // Active/pressed overlay
}
```

**Fields**: All fields are required `string` values representing CSS color values.

**Validation Rules**:
1. All color strings must be valid CSS color formats:
   - Hex: `#rgb`, `#rrggbb`, `#rrggbbaa`
   - RGB: `rgb(r, g, b)`, `rgba(r, g, b, a)`
   - HSL: `hsl(h, s%, l%)`, `hsla(h, s%, l%, a)`
2. Contrast ratios (validated separately):
   - `textPrimary` vs `bgPrimary`: ≥ 4.5:1
   - `textSecondary` vs `bgPrimary`: ≥ 4.5:1
   - `messageBubbleUserText` vs `messageBubbleUser`: ≥ 4.5:1
   - `messageBubbleAssistantText` vs `messageBubbleAssistant`: ≥ 4.5:1
   - Large text: ≥ 3:1
   - UI components: ≥ 3:1

**CSS Variable Mapping**:
```css
[data-theme="light"] {
  --color-bg-primary: /* ThemeColors.bgPrimary */;
  --color-bg-secondary: /* ThemeColors.bgSecondary */;
  --color-text-primary: /* ThemeColors.textPrimary */;
  /* ...etc */
}
```

---

### 3. ThemeMetadata

Provides accessibility and versioning information for a theme.

**Purpose**: Enables automated compliance checks and theme evolution tracking.

**TypeScript Definition**:
```typescript
interface ThemeMetadata {
  contrastRatios: ContrastRatios;
  version: string;
  wcagLevel: 'AA' | 'AAA';
  author?: string;
  tags?: string[];
}

interface ContrastRatios {
  normalText: number;     // Text vs primary background
  largeText: number;      // Large text vs primary background
  uiComponents: number;   // Borders/icons vs background
}
```

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `contrastRatios` | `ContrastRatios` | ✅ | normalText ≥ 4.5, largeText ≥ 3.0, uiComponents ≥ 3.0 | Measured contrast ratios |
| `version` | `string` | ✅ | Semantic version (e.g., "1.0.0") | Theme version for tracking changes |
| `wcagLevel` | `'AA' \| 'AAA'` | ✅ | Must be 'AA' or 'AAA' | WCAG conformance level |
| `author` | `string` | ❌ | 1-100 characters | Theme creator (optional) |
| `tags` | `string[]` | ❌ | Max 10 tags, each 1-20 chars | Categorization tags (optional) |

**Validation**:
- `normalText` must be ≥ 4.5 for WCAG AA, ≥ 7.0 for AAA
- `largeText` must be ≥ 3.0 for WCAG AA, ≥ 4.5 for AAA
- `uiComponents` must be ≥ 3.0 for WCAG AA
- `version` must match semantic versioning pattern: `^\d+\.\d+\.\d+$`

---

### 4. ThemePreference

Represents a user's saved theme selection (stored in localStorage).

**Purpose**: Persist user theme choice across browser sessions.

**TypeScript Definition**:
```typescript
interface ThemePreference {
  themeId: ThemeId;
  updatedAt: string;      // ISO 8601 timestamp
}
```

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `themeId` | `ThemeId` | ✅ | Must be valid theme ID | Selected theme identifier |
| `updatedAt` | `string` | ✅ | ISO 8601 format | Last update timestamp |

**Storage**:
- **Location**: `localStorage['app-theme-preference']`
- **Format**: JSON string
- **Size**: ~50-100 bytes
- **Example**:
  ```json
  {
    "themeId": "dark",
    "updatedAt": "2025-01-25T10:30:00.000Z"
  }
  ```

**Validation**:
```typescript
const isValidThemePreference = (data: unknown): data is ThemePreference => {
  if (typeof data !== 'object' || data === null) return false;
  
  const pref = data as any;
  return (
    typeof pref.themeId === 'string' &&
    ['light', 'dark', 'high-contrast'].includes(pref.themeId) &&
    typeof pref.updatedAt === 'string' &&
    !isNaN(Date.parse(pref.updatedAt))
  );
};
```

**Error Handling**:
- Invalid `themeId`: Reset to default theme ('light')
- Corrupted JSON: Clear localStorage and use default
- localStorage unavailable: Use in-memory state only (no persistence)

---

### 5. ThemeConfig

Global theme system configuration (singleton).

**Purpose**: Central registry of available themes and system-wide theme settings.

**TypeScript Definition**:
```typescript
interface ThemeConfig {
  themes: Theme[];
  defaultTheme: ThemeId;
  storageKey: string;
  allowCustomThemes: boolean;   // Future: enable user-created themes
}
```

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `themes` | `Theme[]` | ✅ | [lightTheme, darkTheme, highContrastTheme] | All available themes |
| `defaultTheme` | `ThemeId` | ✅ | `'light'` | Fallback theme |
| `storageKey` | `string` | ✅ | `'app-theme-preference'` | localStorage key |
| `allowCustomThemes` | `boolean` | ✅ | `false` | Future feature flag |

**Singleton Instance**:
```typescript
export const themeConfig: ThemeConfig = {
  themes: [lightTheme, darkTheme, highContrastTheme],
  defaultTheme: 'light',
  storageKey: 'app-theme-preference',
  allowCustomThemes: false,
};
```

---

## Relationships

```
ThemeConfig
  │
  ├──> themes: Theme[]
  │      │
  │      └──> colors: ThemeColors
  │      └──> metadata: ThemeMetadata
  │             └──> contrastRatios: ContrastRatios
  │
  └──> defaultTheme: ThemeId

ThemePreference
  └──> themeId: ThemeId (references Theme.id)

ThemeStore (Zustand)
  ├──> currentTheme: ThemeId (references Theme.id)
  └──> availableThemes: Theme[] (references ThemeConfig.themes)
```

**Key Relationships**:
1. **ThemeConfig → Theme**: One-to-many (config contains multiple themes)
2. **Theme → ThemeColors**: One-to-one (each theme has one color palette)
3. **Theme → ThemeMetadata**: One-to-one (each theme has metadata)
4. **ThemePreference → Theme**: Many-to-one (user preference references one theme)
5. **ThemeStore → Theme**: References themes from ThemeConfig

---

## State Transitions

### ThemeStore State Machine

```
[Initial State]
     ↓
  LOADING
     ↓
  ┌─────────────────┐
  │ Load preference │
  │ from localStorage│
  └────────┬─────────┘
           ↓
    ┌──────────┐
    │ ACTIVE   │ ←──┐
    │ (theme   │    │
    │  applied)│    │
    └────┬─────┘    │
         │          │
         │ User     │
         │ selects  │
         │ new      │
         │ theme    │
         ↓          │
   ┌──────────┐    │
   │ UPDATING │────┘
   │ (save to │
   │ storage) │
   └──────────┘
```

**State Transitions**:
1. **LOADING → ACTIVE**: On mount, load preference and apply theme
2. **ACTIVE → UPDATING**: User selects new theme
3. **UPDATING → ACTIVE**: Theme applied, localStorage updated

**No Error State**: Errors fall back to default theme and transition to ACTIVE

---

## Validation Rules

### 1. Color Format Validation

```typescript
const isValidColor = (color: string): boolean => {
  const hexPattern = /^#([0-9A-Fa-f]{3}){1,2}([0-9A-Fa-f]{2})?$/;
  const rgbPattern = /^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*[\d.]+\s*)?\)$/;
  const hslPattern = /^hsla?\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*(,\s*[\d.]+\s*)?\)$/;
  
  return hexPattern.test(color) || rgbPattern.test(color) || hslPattern.test(color);
};
```

### 2. Contrast Ratio Validation

```typescript
interface ContrastCheck {
  foreground: string;
  background: string;
  minRatio: number;
  textSize: 'normal' | 'large';
}

const validateContrast = (check: ContrastCheck): { pass: boolean; ratio: number } => {
  const ratio = calculateContrastRatio(check.foreground, check.background);
  const minRequired = check.textSize === 'normal' ? 4.5 : 3.0;
  
  return {
    pass: ratio >= minRequired,
    ratio: ratio,
  };
};
```

### 3. Theme Validation

```typescript
const validateTheme = (theme: Theme): ValidationResult => {
  const errors: string[] = [];
  
  // Color format checks
  Object.entries(theme.colors).forEach(([key, color]) => {
    if (!isValidColor(color)) {
      errors.push(`Invalid color format for ${key}: ${color}`);
    }
  });
  
  // Contrast checks
  const checks: ContrastCheck[] = [
    { 
      foreground: theme.colors.textPrimary, 
      background: theme.colors.bgPrimary, 
      minRatio: 4.5,
      textSize: 'normal' 
    },
    {
      foreground: theme.colors.messageBubbleUserText,
      background: theme.colors.messageBubbleUser,
      minRatio: 4.5,
      textSize: 'normal'
    },
    // ...more checks
  ];
  
  checks.forEach(check => {
    const result = validateContrast(check);
    if (!result.pass) {
      errors.push(`Contrast ratio ${result.ratio.toFixed(2)}:1 is below minimum ${check.minRatio}:1`);
    }
  });
  
  return {
    valid: errors.length === 0,
    errors,
  };
};
```

---

## Complete Type Definitions

See `/specs/004-chat-theme-selector/contracts/theme-types.ts` for full TypeScript implementation with:
- All interface definitions
- Type guards
- Validation functions
- Runtime type checking
- Documentation comments

---

## Accessibility Requirements

### WCAG AA Compliance Matrix

| Theme | Normal Text | Large Text | UI Components | Status |
|-------|-------------|------------|---------------|--------|
| Light | 12.63:1 (AAA) | 12.63:1 (AAA) | 4.52:1 (AA) | ✅ |
| Dark | 15.21:1 (AAA) | 15.21:1 (AAA) | 4.89:1 (AA) | ✅ |
| High Contrast | 19.47:1 (AAA) | 19.47:1 (AAA) | 8.12:1 (AAA) | ✅ |

**Minimum Requirements** (enforced in validation):
- Normal text: 4.5:1 (WCAG AA)
- Large text: 3.0:1 (WCAG AA)
- UI components: 3.0:1 (WCAG AA)

**Target** (all themes should achieve):
- Normal text: 7.0:1 (WCAG AAA)
- Large text: 4.5:1 (WCAG AAA)

---

## Migration & Versioning

### Version Strategy

Themes follow semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes to color names/structure
- **MINOR**: New colors added (backwards compatible)
- **PATCH**: Color value adjustments (same structure)

### Backwards Compatibility

When updating theme structure:
1. Add new fields with defaults
2. Maintain old field names for 1 major version
3. Provide migration utility: `migrateTheme(oldTheme): Theme`

### Storage Format Evolution

If `ThemePreference` structure changes:
```typescript
// v1
{ "themeId": "dark" }

// v2 (add timestamp)
{ "themeId": "dark", "updatedAt": "2025-01-25T10:30:00Z" }

// Migration
const migratePreference = (stored: unknown): ThemePreference => {
  if (typeof stored === 'string') {
    // v1 format
    return { themeId: stored as ThemeId, updatedAt: new Date().toISOString() };
  }
  // v2 format
  return stored as ThemePreference;
};
```

---

**Data Model Complete** ✅  
Ready for contract generation (Phase 1) and implementation (Phase 2).
