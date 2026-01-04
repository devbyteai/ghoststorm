# GhostStorm

[![CI](https://github.com/devbyteai/ghoststorm/actions/workflows/ci.yml/badge.svg)](https://github.com/devbyteai/ghoststorm/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://devbyteai.github.io/ghoststorm)

**Enterprise-grade browser automation with undetectable stealth.** Anti-fingerprinting, proxy rotation, AI-powered control, and human behavior simulation.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
</p>

---

## Features

- **3 Browser Engines** - Patchright, Camoufox (0% detection), Playwright
- **20+ Anti-Detection Vectors** - Canvas, WebGL, Audio, Fonts, Navigator, CDP
- **47,000+ Proxies** - Aggregated from 20+ sources, Tor, Bright Data, Decodo
- **2,500+ Device Fingerprints** - iOS, Android, Desktop profiles
- **Human Behavior Simulation** - Bezier mouse, natural scroll, realistic typing
- **AI-Powered Automation** - Ollama, OpenAI, Anthropic integration
- **Flow Recording** - Record once, replay with variation
- **Platform Automation** - TikTok, Instagram, YouTube, DEXTools
- **Web Dashboard** - Real-time monitoring and control
- **840+ Tests** - Production-ready quality

---

## Quick Start

```bash
# Install
git clone https://github.com/devbyteai/ghoststorm.git && cd ghoststorm
uv sync --all-extras --dev
uv run patchright install chromium

# Run dashboard
make dev  # http://localhost:8000
```

**Or with Docker:**
```bash
docker compose up -d
```

---

## Usage

```python
from ghoststorm.core.engine.orchestrator import Orchestrator
from ghoststorm.core.models.task import Task, TaskType, TaskConfig

async def main():
    orchestrator = Orchestrator()
    await orchestrator.start()

    result = await orchestrator.run_task(Task(
        url="https://example.com",
        task_type=TaskType.VISIT,
        config=TaskConfig(human_simulation=True, scroll_page=True)
    ))

    await orchestrator.stop()
```

See [`examples/`](examples/) for more.

---

## DEXTools Trending

Push tokens to trending with realistic visitor patterns:

```python
from ghoststorm.plugins.automation.dextools_campaign import run_dextools_campaign

result = await run_dextools_campaign(
    pair_url="https://www.dextools.io/app/ether/pair-explorer/0x...",
    num_visitors=100,
    duration_hours=24.0,
)
```

60% passive viewers, 30% light interaction, 10% engaged - mimics real traffic.

---

## Documentation

| Resource | Description |
|----------|-------------|
| [**Full Docs**](https://devbyteai.github.io/ghoststorm) | Complete documentation |
| [**API Reference**](https://devbyteai.github.io/ghoststorm/api) | API endpoints |
| [**Architecture**](https://devbyteai.github.io/ghoststorm/architecture) | System design |
| [**Examples**](examples/) | Working code samples |

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Browser** | Playwright, Patchright, Camoufox |
| **API** | FastAPI, WebSocket, Uvicorn |
| **AI** | Ollama, OpenAI, Anthropic |
| **Stealth** | BrowserForge, Custom evasion scripts |
| **Proxy** | SOCKS5, HTTP/S, Tor, Premium providers |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `make test` and `make lint` before PRs.

---

## License

MIT - See [LICENSE](LICENSE)

<p align="center">
  <sub>Built by <a href="https://github.com/devbyteai">devbyteai</a></sub>
</p>
