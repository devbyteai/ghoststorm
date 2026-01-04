# GhostStorm

**AI-Powered Web Automation Platform**

GhostStorm is a comprehensive automation platform for web tasks across multiple platforms including TikTok, Instagram, YouTube, and DEXTools.

## Features

- **Multi-Platform Support**: TikTok, Instagram, YouTube, DEXTools, and more
- **AI-Powered Automation**: LLM integration for intelligent flow generation
- **Flow Recording**: Record and replay browser interactions
- **Proxy Management**: Auto-rotation with premium provider support
- **Real-Time Dashboard**: WebSocket-powered monitoring
- **Checkpoint System**: Resume flows from any point
- **Docker Support**: Easy containerized deployment

## Quick Start

```bash
# Install
git clone https://github.com/devbyteai/ghoststorm.git
cd ghoststorm
uv sync --all-extras --dev

# Run
make dev
```

Open http://localhost:8000 to access the dashboard.

## Documentation

- [Quick Start](quickstart.md) - Get running in 5 minutes
- [Architecture](architecture.md) - System design and components
- [API Reference](api.md) - REST and WebSocket API
- [Contributing](contributing.md) - How to contribute

## License

MIT License - See [LICENSE](https://github.com/devbyteai/ghoststorm/blob/main/LICENSE)
