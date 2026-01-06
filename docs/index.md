# GhostStorm Documentation

**AI-Powered Web Automation Platform**

GhostStorm is a comprehensive automation platform for web tasks including browser automation, social media engagement, proxy management, and LLM-powered intelligent interactions.

## Features

- **Browser Automation**: Playwright/Patchright-based browser control with anti-detection
- **AI Control**: LLM integration (Ollama) for intelligent page interaction
- **Proxy Management**: Built-in scraping, testing, and rotation from 50+ sources
- **TikTok Booster**: Zefoy integration for views, likes, and engagement
- **Data Management**: User agents, fingerprints, and evasion techniques
- **Real-Time Dashboard**: WebSocket-powered monitoring and control

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Getting Started](getting-started.md) | Installation and first run |
| [Tasks](tasks.md) | Mass automation task management |
| [Engine](engine.md) | Generic automation engine |
| [AI Control](ai-control.md) | LLM-driven browser automation |
| [TikTok Booster](zefoy.md) | Zefoy integration for TikTok |
| [Proxies](proxies.md) | Proxy management and configuration |
| [Data](data.md) | User agents, fingerprints, and more |
| [Algorithms](algorithms.md) | Platform API signatures |
| [Settings](settings.md) | Application configuration |
| [Troubleshooting](troubleshooting.md) | Common issues and fixes |
| [API Reference](api-reference.md) | REST API documentation |

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd ghoststorm
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
patchright install chromium

# Run
PYTHONPATH=src python -m uvicorn "ghoststorm.api:create_app" --factory --port 8000
```

Open http://localhost:8000 to access the dashboard.

## System Requirements

- Python 3.10+
- 4GB RAM minimum (8GB recommended)
- Modern browser (Chrome/Chromium)
- Internet connection

## Optional Dependencies

| Component | Purpose | Install |
|-----------|---------|---------|
| Ollama | AI Control features | `curl -fsSL https://ollama.com/install.sh \| sh` |
| Tesseract | Captcha solving | `apt install tesseract-ocr` |

## Architecture

```
GhostStorm
├── Web UI (FastAPI + Tailwind)
├── Automation Engine
│   ├── Patchright/Playwright Browser
│   ├── Proxy Rotation
│   └── Anti-Detection
├── LLM Integration (Ollama)
├── Task Queue (Background Jobs)
└── Data Management
```

## License

This software is proprietary. All rights reserved.
