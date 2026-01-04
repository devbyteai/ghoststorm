# GhostStorm Architecture

## Overview

GhostStorm is a modular automation platform designed for scalable, AI-powered web automation across multiple platforms.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Dashboard                            │
│                    (React + WebSocket)                           │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│                          API Layer                               │
│                    (FastAPI + WebSocket)                         │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│    Engine     │       │   Assistant   │       │    Proxy      │
│  Orchestrator │       │   (LLM/AI)    │       │   Manager     │
└───────┬───────┘       └───────┬───────┘       └───────┬───────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│    Browser    │       │    Ollama     │       │   Providers   │
│   Automation  │       │    OpenAI     │       │   (APIs)      │
│  (Playwright) │       │    Claude     │       │               │
└───────────────┘       └───────────────┘       └───────────────┘
```

## Core Components

### 1. Engine (`src/ghoststorm/engine/`)

The orchestration layer managing task execution:

- **Orchestrator**: Coordinates browser instances and task queues
- **Task Manager**: Handles task lifecycle (create, execute, retry)
- **Flow Engine**: Executes recorded automation flows
- **Checkpoint System**: Enables flow resumption and branching

### 2. Browser (`src/ghoststorm/browser/`)

Browser automation layer:

- **BrowserPool**: Manages browser instance lifecycle
- **PageController**: Handles page navigation and interactions
- **Stealth**: Anti-detection measures (fingerprinting, headers)
- **Recorder**: Captures user actions for flow creation

### 3. Assistant (`src/ghoststorm/assistant/`)

AI-powered automation assistant:

- **Chat Interface**: Natural language task creation
- **Flow Generator**: LLM-generated automation scripts
- **Code Executor**: Sandboxed execution of generated code
- **Docker Integration**: Isolated execution environments

### 4. LLM (`src/ghoststorm/llm/`)

Language model integrations:

- **Providers**: Ollama, OpenAI, Anthropic adapters
- **Streaming**: Real-time response streaming
- **Context Management**: Conversation history and memory

### 5. Proxy (`src/ghoststorm/proxy/`)

Proxy management system:

- **Pool Manager**: Proxy rotation and health checking
- **Scrapers**: Auto-discovery from public sources
- **Premium Providers**: Integration with paid services
- **Validation**: Proxy testing and scoring

### 6. API (`src/ghoststorm/api/`)

REST and WebSocket API:

- **Routes**: RESTful endpoints for all operations
- **WebSocket**: Real-time task updates and events
- **Authentication**: API key and session management

### 7. Web (`src/ghoststorm/web/`)

React dashboard:

- **Pages**: Tasks, Flows, Proxies, Settings, etc.
- **Components**: Reusable UI elements
- **State**: Real-time updates via WebSocket

## Data Flow

### Task Execution

```
1. User creates task (UI/API)
        │
        ▼
2. Task queued in Orchestrator
        │
        ▼
3. Browser instance acquired from pool
        │
        ▼
4. Proxy assigned from pool
        │
        ▼
5. Flow executed with checkpoints
        │
        ▼
6. Results streamed via WebSocket
        │
        ▼
7. Browser/proxy returned to pools
```

### Flow Recording

```
1. User initiates recording
        │
        ▼
2. Browser launched with recorder
        │
        ▼
3. Actions captured (clicks, inputs, navigation)
        │
        ▼
4. LLM analyzes and optimizes flow
        │
        ▼
5. Checkpoints auto-inserted
        │
        ▼
6. Flow saved to library
```

## Configuration

```
config/
├── platforms/          # Platform-specific configs
│   ├── tiktok.json
│   ├── instagram.json
│   └── dextools.json
├── browser/           # Browser settings
├── proxy/             # Proxy provider configs
└── llm/               # LLM provider settings
```

## Testing Strategy

```
tests/
├── unit/              # Isolated component tests
├── integration/       # Service integration tests
├── e2e/              # Full system tests
│   ├── api/          # API endpoint tests
│   ├── ui/           # Playwright UI tests
│   └── journeys/     # Full workflow tests
└── conftest.py       # Shared fixtures
```

## Deployment

### Docker

```bash
docker compose up -d
```

### Manual

```bash
uv sync --all-extras
uv run ghoststorm run
```

## Performance Considerations

- **Connection Pooling**: Database and proxy connections pooled
- **Async I/O**: All I/O operations are async
- **Browser Reuse**: Browsers recycled between tasks
- **Streaming**: Large responses streamed to minimize memory
