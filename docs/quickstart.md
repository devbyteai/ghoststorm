# Quick Start Guide

Get GhostStorm running in 5 minutes.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for web dashboard)

## Installation

### Option 1: From Source

```bash
# Clone repository
git clone https://github.com/devbyteai/ghoststorm.git
cd ghoststorm

# Install dependencies
uv sync --all-extras --dev

# Run
uv run ghoststorm run
```

### Option 2: Docker

```bash
docker compose up -d
```

### Option 3: pip

```bash
pip install ghoststorm
ghoststorm run
```

## First Run

1. **Start the server**:
   ```bash
   make dev
   # or
   uv run ghoststorm run --dev
   ```

2. **Open dashboard**: http://localhost:8000

3. **Create your first task**:
   - Enter a URL in the task input
   - Platform is auto-detected
   - Click "Create Task"

4. **Monitor progress**:
   - Real-time updates in the dashboard
   - WebSocket connection shows status

## Configuration

### Environment Variables

```bash
# .env file
GHOSTSTORM_HOST=0.0.0.0
GHOSTSTORM_PORT=8000
GHOSTSTORM_DEBUG=true

# LLM (optional)
OLLAMA_URL=http://localhost:11434
OPENAI_API_KEY=sk-...

# Proxies (optional)
PROXY_PREMIUM_KEY=...
```

### Config Files

```
config/
├── browser.json      # Browser settings
├── proxy.json        # Proxy configuration
└── platforms/        # Platform-specific settings
```

## Common Operations

### Record a Flow

1. Click "Record Flow" in dashboard
2. Interact with the browser
3. Actions are captured automatically
4. Click "Stop" when done
5. Flow is saved to library

### Execute a Flow

1. Go to Flows page
2. Select a flow
3. Click "Execute"
4. Configure instances and proxy settings
5. Monitor execution

### Manage Proxies

1. Go to Proxies page
2. Click "Scrape" to find free proxies
3. Or add premium provider credentials
4. Proxies are auto-validated

## CLI Commands

```bash
# Start server
ghoststorm run [--port 8000] [--dev]

# Run task
ghoststorm task run <url>

# Execute flow
ghoststorm flow execute <flow-id>

# Scrape proxies
ghoststorm proxy scrape

# Health check
ghoststorm health
```

## Troubleshooting

### Browser not launching

```bash
# Install browser dependencies
uv run patchright install chromium
```

### Proxy errors

- Check proxy format: `protocol://user:pass@host:port`
- Validate proxies: Proxies page → Test All

### LLM not responding

- Ensure Ollama is running: `ollama serve`
- Or set OpenAI API key in settings

## Next Steps

- [Architecture](architecture.md) - System design
- [API Reference](api.md) - API documentation
- [Contributing](../CONTRIBUTING.md) - How to contribute
