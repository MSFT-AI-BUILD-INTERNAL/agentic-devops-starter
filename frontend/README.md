# Frontend README

This is the web-based chatbot frontend for the AG-UI backend.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at http://localhost:5173

## Prerequisites

- Node.js 20.0.0 or higher
- npm 10.0.0 or higher
- Backend server running at http://127.0.0.1:5100

## Development

```bash
# Development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run type checking
npm run type-check

# Run linting
npm run lint

# Run tests
npm run test

# Run E2E tests
npm run test:e2e
```

## Environment Variables

Create a `.env.local` file for custom configuration:

```bash
# Backend API endpoint (default: http://127.0.0.1:5100)
VITE_AGUI_ENDPOINT=http://127.0.0.1:5100

# Enable debug logging
VITE_DEBUG_MODE=true
```

## Project Structure

```
frontend/
├── src/
│   ├── components/      # React components
│   ├── services/        # Business logic
│   ├── hooks/           # Custom React hooks
│   ├── types/           # TypeScript definitions
│   ├── utils/           # Helper functions
│   ├── stores/          # Zustand state management
│   ├── App.tsx          # Root component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── public/              # Static assets
└── tests/               # Test files
```

## Technology Stack

- **React 18.2+** - UI framework
- **TypeScript 5.3+** - Type safety
- **CopilotKit** - Chat UI components
- **Zustand** - State management
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Vitest** - Unit testing
- **Playwright** - E2E testing

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run type-check` - Run TypeScript compiler
- `npm run lint` - Run ESLint
- `npm run test` - Run unit tests
- `npm run test:e2e` - Run E2E tests

## Backend Integration

The frontend connects to the AG-UI backend via:
- HTTP POST requests to `/` for sending messages
- Server-Sent Events (SSE) for streaming responses
- HTTP GET requests to `/threads` for conversation history

See `../specs/003-copilotkit-frontend/contracts/agui-protocol.yaml` for full API specification.

## Troubleshooting

### Port 5173 already in use
```bash
npm run dev -- --port 5174
```

### Backend connection refused
Ensure the backend server is running:
```bash
cd ../app
python agui_server.py
```

### Dependencies not installed
```bash
rm -rf node_modules package-lock.json
npm install
```

## Documentation

- [Feature Specification](../specs/003-copilotkit-frontend/spec.md)
- [Implementation Plan](../specs/003-copilotkit-frontend/plan.md)
- [Data Model](../specs/003-copilotkit-frontend/data-model.md)
- [API Contracts](../specs/003-copilotkit-frontend/contracts/agui-protocol.yaml)
- [Quickstart Guide](../specs/003-copilotkit-frontend/quickstart.md)
