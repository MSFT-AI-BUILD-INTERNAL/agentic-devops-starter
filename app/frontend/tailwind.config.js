/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Theme-aware colors (CSS variables)
        primary: 'var(--color-bg-primary)',
        secondary: 'var(--color-bg-secondary)',
        tertiary: 'var(--color-bg-tertiary)',
        
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-inverse': 'var(--color-text-inverse)',
        
        accent: 'var(--color-accent)',
        'accent-hover': 'var(--color-accent-hover)',
        'accent-light': 'var(--color-accent-light)',
        
        border: 'var(--color-border)',
        'border-focus': 'var(--color-border-focus)',
        
        'message-user': 'var(--color-message-user)',
        'message-user-text': 'var(--color-message-user-text)',
        'message-assistant': 'var(--color-message-assistant)',
        'message-assistant-text': 'var(--color-message-assistant-text)',
        'message-tool': 'var(--color-message-tool)',
        'message-tool-text': 'var(--color-message-tool-text)',
        
        success: 'var(--color-success)',
        error: 'var(--color-error)',
        warning: 'var(--color-warning)',
        info: 'var(--color-info)',
        
        'hover-overlay': 'var(--color-hover-overlay)',
        'active-overlay': 'var(--color-active-overlay)',
        
        // Legacy chat colors (deprecated - use theme-aware colors above)
        'chat-user': '#007AFF',
        'chat-assistant': '#5856D6',
        'chat-tool': '#FF9500',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
