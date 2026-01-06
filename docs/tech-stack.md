# Tech Stack & Dependencies

Complete list of technologies and libraries used in GhostStorm.

## Browser Automation

**NOT Selenium, NOT ChromeDriver** - We use modern Playwright-based tools.

| Package | Version | Purpose |
|---------|---------|---------|
| **patchright** | >=1.0.0 | Main browser engine - patched Playwright with anti-detection built-in |
| **playwright** | >=1.49.0 | Base browser automation framework (Chromium, Firefox, WebKit) |
| **camoufox** | >=0.4.0 | Firefox-based stealth browser alternative |

### Why Not Selenium?

- Playwright is faster and more reliable
- Native async support
- Better anti-detection capabilities
- No separate driver downloads needed
- Patchright patches detection vectors automatically

## Anti-Detection & Fingerprinting

| Package | Version | Purpose |
|---------|---------|---------|
| **browserforge** | >=1.2.3 | Generate realistic browser fingerprints (screen, fonts, WebGL, etc.) |
| **geoip2fast** | >=1.2.0 | GeoIP lookup for identity coherence (match IP location to timezone) |

## Web Framework (API & Dashboard)

| Package | Version | Purpose |
|---------|---------|---------|
| **fastapi** | >=0.115.0 | REST API and web server framework |
| **uvicorn** | >=0.32.0 | ASGI server to run FastAPI |
| **websockets** | >=14.0 | Real-time updates to dashboard via WebSocket |

## Async & HTTP

| Package | Version | Purpose |
|---------|---------|---------|
| **aiohttp** | >=3.11.0 | Async HTTP client for API calls, proxy testing |
| **aiofiles** | >=24.1.0 | Async file read/write operations |
| **python-socks** | >=2.5.0 | SOCKS4/SOCKS5 proxy support |

## Data & Configuration

| Package | Version | Purpose |
|---------|---------|---------|
| **pydantic** | >=2.10.0 | Data validation, settings management |
| **pydantic-settings** | >=2.6.0 | Environment-based configuration |
| **orjson** | >=3.10.0 | Fast JSON serialization/deserialization |
| **aiosqlite** | >=0.20.0 | Async SQLite database for task storage |
| **pyyaml** | >=6.0.2 | YAML config file parsing |

## Scraping & HTML Parsing

| Package | Version | Purpose |
|---------|---------|---------|
| **beautifulsoup4** | >=4.12.0 | HTML parsing for proxy scraping |
| **lxml** | >=5.0.0 | Fast XML/HTML parser backend |

## CLI & Terminal

| Package | Version | Purpose |
|---------|---------|---------|
| **typer** | >=0.12.0 | CLI interface framework |
| **rich** | >=13.9.0 | Pretty terminal output, progress bars, tables |

## Logging & Monitoring

| Package | Version | Purpose |
|---------|---------|---------|
| **structlog** | >=24.4.0 | Structured logging with context |
| **prometheus-client** | >=0.21.0 | Metrics for monitoring |
| **psutil** | >=6.0.0 | System resource monitoring (CPU, RAM) |

## Plugin System

| Package | Version | Purpose |
|---------|---------|---------|
| **pluggy** | >=1.5.0 | Plugin architecture for extensibility |

## Optional Dependencies

### Captcha Solving

| Package | Version | Purpose |
|---------|---------|---------|
| **2captcha-python** | >=1.5.0 | 2Captcha API integration |
| **anticaptchaofficial** | >=1.0.0 | Anti-Captcha API integration |

### System Packages (Not Python)

| Package | Purpose | Install |
|---------|---------|---------|
| **Ollama** | Local LLM for AI Control | `curl -fsSL https://ollama.com/install.sh \| sh` |
| **Tesseract OCR** | Local captcha solving | `apt install tesseract-ocr` |

## Frontend (No npm/Node.js!)

All frontend is vanilla JavaScript with CDN libraries:

| Library | Purpose | CDN |
|---------|---------|-----|
| **Tailwind CSS** | Styling | cdn.tailwindcss.com |
| **marked.js** | Markdown rendering | cdn.jsdelivr.net |
| **highlight.js** | Code syntax highlighting | cdn.jsdelivr.net |

No build step, no npm, no webpack - just plain HTML/JS/CSS.

## Development Tools

| Package | Purpose |
|---------|---------|
| **pytest** | Testing framework |
| **pytest-asyncio** | Async test support |
| **pytest-cov** | Code coverage |
| **ruff** | Linting and formatting |
| **mypy** | Type checking |

## Architecture Summary

```
GhostStorm Stack
├── Browser Layer
│   ├── Patchright (primary) - Chromium with anti-detection
│   ├── Playwright (fallback) - Standard automation
│   └── Camoufox (alternative) - Firefox stealth
│
├── Backend Layer
│   ├── FastAPI - REST API
│   ├── WebSockets - Real-time events
│   └── SQLite - Task/data storage
│
├── Anti-Detection Layer
│   ├── BrowserForge - Fingerprint generation
│   ├── Proxy Rotation - IP masking
│   └── Identity Coherence - Human behavior
│
├── AI Layer (Optional)
│   └── Ollama - Local LLM for vision/control
│
└── Frontend Layer
    ├── Tailwind CSS - Styling
    └── Vanilla JS - No framework
```

## Why These Choices?

### Patchright over Selenium
- Modern async architecture
- Built-in anti-detection patches
- No external driver management
- Faster execution

### FastAPI over Flask/Django
- Native async support
- Automatic OpenAPI docs
- Pydantic integration
- WebSocket support built-in

### SQLite over PostgreSQL
- Zero configuration
- Portable (single file)
- Good enough for local automation
- Async support via aiosqlite

### No Frontend Framework
- Simpler deployment
- No build step
- Faster loading
- CDN caching
