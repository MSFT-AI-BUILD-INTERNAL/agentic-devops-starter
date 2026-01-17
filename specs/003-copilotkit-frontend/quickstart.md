# Quickstart Guide: Web-Based Chatbot Frontend

**Feature Branch**: `003-copilotkit-frontend`  
**Date**: 2025-01-17  
**Status**: Ready for Implementation

## Overview

This guide provides step-by-step instructions for setting up and running the web-based chatbot frontend alongside the existing AG-UI backend. Follow these instructions to get the complete system operational on your local development machine.

---

## Prerequisites

### Required Software

| Tool | Minimum Version | Purpose | Installation |
|------|----------------|---------|--------------|
| **Node.js** | 20.0.0 | JavaScript runtime | [nodejs.org](https://nodejs.org/) |
| **npm** | 10.0.0 | Package manager | Included with Node.js |
| **Python** | 3.12+ | Backend runtime | [python.org](https://www.python.org/) |
| **uv** | Latest | Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### System Requirements

- **OS**: macOS, Linux, or Windows with WSL2
- **RAM**: Minimum 4GB available
- **Disk**: 500MB free space
- **Network**: Internet connection for API calls

### Accounts & API Keys

- **Azure OpenAI** or **OpenAI API key** (backend requirement)
  - Get Azure OpenAI: [Azure Portal](https://portal.azure.com/)
  - Get OpenAI API: [platform.openai.com](https://platform.openai.com/)

---

## Quick Start (5 Minutes)

### Step 1: Clone and Navigate

```bash
# Clone the repository (if not already done)
git clone https://github.com/your-org/agentic-devops-starter.git
cd agentic-devops-starter

# Checkout the feature branch
git checkout 003-copilotkit-frontend
```

### Step 2: Backend Setup

```bash
# Navigate to backend directory
cd app

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: Either Azure OpenAI OR OpenAI credentials
nano .env  # or use your preferred editor
```

**Environment Variables** (`.env`):
```bash
# Option 1: Azure OpenAI (Recommended)
AZURE_AI_PROJECT_ENDPOINT="https://your-resource.openai.azure.com/"
AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4o-mini"
AZURE_OPENAI_API_VERSION="2025-08-07"
# AZURE_OPENAI_API_KEY is optional if using DefaultAzureCredential

# Option 2: OpenAI (Fallback)
OPENAI_API_KEY="sk-..."

# Server Configuration (defaults shown)
# AGUI_SERVER_HOST="127.0.0.1"
# AGUI_SERVER_PORT=5100
```

```bash
# Install backend dependencies
uv pip install -e .

# Start backend server
python agui_server.py
```

**Expected Output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:5100 (Press CTRL+C to quit)
```

**Verify Backend**:
```bash
# In a new terminal, test health endpoint
curl http://127.0.0.1:5100/health

# Expected response:
# {"status":"healthy","version":"1.0.0","thread_count":0,"uptime_seconds":5.2}
```

### Step 3: Frontend Setup

```bash
# Open a new terminal, navigate to frontend directory
cd ../frontend  # or from repo root: cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Expected Output**:
```
  VITE v5.0.0  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

### Step 4: Access the Application

1. Open your browser to: **http://localhost:5173**
2. You should see the chat interface
3. Type a message like "Hello, what can you help me with?"
4. Watch the response stream in real-time!

---

## Detailed Setup Instructions

### Backend Configuration

#### Environment Variables Explained

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AZURE_AI_PROJECT_ENDPOINT` | One of Azure/OpenAI | Azure OpenAI endpoint URL | `https://my-resource.openai.azure.com/` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | If using Azure | Model deployment name | `gpt-4o-mini` |
| `AZURE_OPENAI_API_VERSION` | If using Azure | API version | `2025-08-07` |
| `AZURE_OPENAI_API_KEY` | Optional | Azure API key (if not using DefaultAzureCredential) | `abc123...` |
| `OPENAI_API_KEY` | One of Azure/OpenAI | OpenAI API key | `sk-proj-...` |
| `AGUI_SERVER_HOST` | No | Server bind address | `127.0.0.1` (default) |
| `AGUI_SERVER_PORT` | No | Server port | `5100` (default) |

#### Backend Server Tools

The backend provides these tools for testing:

- **get_time_zone(location)**: Returns time zone information
  - Example: "What time zone is Tokyo in?"
  - Server-side execution

#### Backend Logs

Logs are output to console with structured format:
```
2025-01-17 10:00:00 - INFO - [correlation-id] - Chat request received
2025-01-17 10:00:01 - INFO - [correlation-id] - Tool execution: get_time_zone
2025-01-17 10:00:02 - INFO - [correlation-id] - Message complete
```

### Frontend Configuration

#### Development Server Options

```bash
# Default development server
npm run dev

# Expose to network (access from other devices)
npm run dev -- --host

# Use specific port
npm run dev -- --port 3000

# Open browser automatically
npm run dev -- --open
```

#### Environment Variables (Optional)

Create `frontend/.env.local` for custom configuration:

```bash
# Backend API endpoint (default shown)
VITE_AGUI_ENDPOINT=http://127.0.0.1:5100

# Enable debug logging
VITE_DEBUG_MODE=true

# Custom branding
VITE_APP_TITLE="My AI Assistant"
```

#### Frontend Build

```bash
# Production build
npm run build

# Preview production build
npm run preview

# Type checking
npm run type-check

# Linting
npm run lint

# Run tests
npm run test
```

---

## Testing the Integration

### Basic Functionality Tests

#### Test 1: Simple Chat

1. **Action**: Type "Hello!" and send
2. **Expected**: Agent responds with greeting in < 5 seconds
3. **Success**: Message appears with streaming tokens

#### Test 2: Tool Execution

1. **Action**: Type "What time zone is Seattle in?"
2. **Expected**: 
   - Tool indicator shows "Using get_time_zone tool..."
   - Response: "Pacific Time (UTC-8)"
3. **Success**: Tool executes and result is incorporated

#### Test 3: Context Preservation

1. **Action**: Ask "What's 15 times 7?"
2. **Expected**: Response: "105"
3. **Action**: Ask "What about that times 2?"
4. **Expected**: Response: "210" (maintains context)
5. **Success**: Follow-up question understood

#### Test 4: Connection Status

1. **Action**: Stop backend server (Ctrl+C in backend terminal)
2. **Expected**: Frontend shows "Disconnected" status
3. **Action**: Restart backend server
4. **Expected**: Frontend auto-reconnects, shows "Connected"
5. **Success**: Connection status updates correctly

#### Test 5: Error Handling

1. **Action**: Type a very long message (> 10,000 characters)
2. **Expected**: Validation error displayed
3. **Success**: Error message is user-friendly

### Performance Benchmarks

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Initial page load** | < 2s | Browser DevTools Network tab |
| **Message send latency** | < 200ms | Console log timestamps |
| **Streaming smoothness** | 60fps | No visible jank during streaming |
| **100 messages** | No lag | Scroll through long conversation |

---

## Troubleshooting

### Backend Issues

#### "ValueError: Either AZURE_AI_PROJECT_ENDPOINT... or OPENAI_API_KEY must be set"

**Cause**: Missing API credentials in `.env`  
**Solution**: 
```bash
cd app
cp .env.example .env
# Edit .env and add your API keys
```

#### "Port 5100 already in use"

**Cause**: Another process is using port 5100  
**Solution**:
```bash
# Find process using port 5100
lsof -i :5100

# Kill the process
kill -9 <PID>

# Or change port in .env
echo "AGUI_SERVER_PORT=5101" >> .env
```

#### "ModuleNotFoundError: No module named 'agent_framework'"

**Cause**: Backend dependencies not installed  
**Solution**:
```bash
cd app
uv pip install -e .
```

### Frontend Issues

#### "ERR_CONNECTION_REFUSED" when sending messages

**Cause**: Backend server not running  
**Solution**:
```bash
# Check if backend is running
curl http://127.0.0.1:5100/health

# If not, start it
cd app && python agui_server.py
```

#### "Module not found" errors

**Cause**: Frontend dependencies not installed  
**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### Frontend won't start: "Port 5173 already in use"

**Cause**: Another Vite dev server is running  
**Solution**:
```bash
# Kill existing Vite process
pkill -f vite

# Or use different port
npm run dev -- --port 5174
```

#### Streaming responses are slow or choppy

**Cause**: Network latency or browser throttling  
**Solution**:
1. Check backend logs for slow LLM responses
2. Disable browser extensions
3. Check CPU usage (< 50% recommended)

### Common Error Messages

| Error | Meaning | Fix |
|-------|---------|-----|
| `CORS error` | Backend not allowing frontend origin | Backend should auto-configure CORS |
| `Failed to fetch` | Network connection issue | Check backend is running, firewall settings |
| `422 Validation Error` | Invalid request format | Check message length, thread_id format |
| `Thread not found` | Invalid or expired thread_id | Create new conversation |
| `Tool execution timeout` | Tool took > 30s | Expected for long-running tools |

---

## Development Workflow

### Running Both Services Concurrently

#### Option 1: Manual (2 terminals)

**Terminal 1 - Backend**:
```bash
cd app
python agui_server.py
```

**Terminal 2 - Frontend**:
```bash
cd frontend
npm run dev
```

#### Option 2: Using tmux

```bash
# Start tmux session
tmux new -s chatbot

# Split window
Ctrl+b "

# Terminal 1 (top): Start backend
cd app && python agui_server.py

# Switch to Terminal 2 (bottom)
Ctrl+b ↓

# Terminal 2: Start frontend
cd frontend && npm run dev

# Detach from session: Ctrl+b d
# Re-attach: tmux attach -t chatbot
```

#### Option 3: Using npm-run-all (Future Enhancement)

```bash
# Add to frontend/package.json:
# "scripts": {
#   "dev:full": "npm-run-all --parallel dev:backend dev:frontend",
#   "dev:backend": "cd ../app && python agui_server.py",
#   "dev:frontend": "vite"
# }

cd frontend
npm run dev:full
```

### Hot Reload Behavior

**Frontend Hot Reload**: Changes to `.tsx`, `.ts`, `.css` files trigger instant reload  
**Backend Hot Reload**: Not enabled by default. Restart server after Python changes.

**Enable Backend Auto-Reload**:
```bash
# Install watchdog
uv pip install watchdog

# Run with auto-reload
python -m uvicorn agui_server:get_app --reload --host 127.0.0.1 --port 5100 --factory
```

### Debugging Tips

#### Frontend Debugging

```typescript
// Enable debug logging in frontend
// Add to src/main.tsx
if (import.meta.env.DEV) {
  window.DEBUG = true;
  console.log('Debug mode enabled');
}

// Add to hooks/useChat.ts
if (window.DEBUG) {
  console.log('[useChat] Sending message:', content);
}
```

#### Backend Debugging

```python
# Increase log verbosity
# In app/src/logging_utils.py, change level to DEBUG

import logging
logger = logging.getLogger('agentic_devops')
logger.setLevel(logging.DEBUG)
```

#### Network Debugging

```bash
# Monitor SSE stream in terminal
curl -N http://127.0.0.1:5100/ \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","thread_id":null,"stream":true}'

# Watch for events
# Press Ctrl+C to stop
```

---

## Next Steps

### After Successful Setup

1. **Explore Features**:
   - Try different queries
   - Test tool execution
   - Create multiple conversations
   - Test error scenarios

2. **Review Documentation**:
   - `research.md` - Technical decisions
   - `data-model.md` - Data structures
   - `contracts/agui-protocol.yaml` - API specification

3. **Run Tests** (once implemented):
   ```bash
   # Backend tests
   cd app && pytest tests/
   
   # Frontend tests
   cd frontend && npm test
   
   # E2E tests
   cd frontend && npm run test:e2e
   ```

4. **Read Implementation Tasks**:
   - `tasks.md` - Step-by-step implementation guide (generated by `/speckit.tasks`)

### Contributing

1. Create feature branch from `003-copilotkit-frontend`
2. Make changes
3. Run linters: `npm run lint` (frontend), `ruff check .` (backend)
4. Run tests
5. Submit PR

### Getting Help

- **Backend Issues**: Check `app/README.md`
- **Frontend Issues**: Check `frontend/README.md` (once created)
- **AG-UI Protocol**: See `contracts/agui-protocol.yaml`
- **Architecture**: Review `research.md` and `data-model.md`

---

## Production Considerations (Future)

This quickstart is for **local development only**. For production deployment:

- [ ] Use environment-based configuration (not `.env` files)
- [ ] Enable HTTPS for both frontend and backend
- [ ] Implement authentication/authorization
- [ ] Add rate limiting and CORS restrictions
- [ ] Use persistent storage for conversation threads
- [ ] Set up monitoring and logging infrastructure
- [ ] Configure CDN for frontend assets
- [ ] Implement proper error tracking (Sentry, etc.)

See `DEPLOYMENT.md` for production setup guidance (to be created).

---

## Summary

**Backend**: FastAPI server on `http://127.0.0.1:5100` with AG-UI protocol  
**Frontend**: React + Vite app on `http://localhost:5173` with CopilotKit  
**Communication**: SSE streaming for real-time responses  
**Tools**: Server-side (get_time_zone) and client-side (future) tool execution

**Estimated Setup Time**: 5-10 minutes  
**Key Files**:
- Backend: `app/.env`, `app/agui_server.py`
- Frontend: `frontend/.env.local`, `frontend/src/main.tsx`

Happy coding! 🚀
