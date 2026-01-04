# GhostStorm

[![CI](https://github.com/devbyteai/ghoststorm/actions/workflows/ci.yml/badge.svg)](https://github.com/devbyteai/ghoststorm/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/devbyteai/ghoststorm/graph/badge.svg)](https://codecov.io/gh/devbyteai/ghoststorm)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://ghcr.io/devbyteai/ghoststorm)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://devbyteai.github.io/ghoststorm)

High-performance traffic automation framework with enterprise-grade anti-detection, full network anonymity, and AI-powered browser control.

## Built With

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama">
  <img src="https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic">
</p>

### Core Technologies

| Category | Technologies |
|----------|--------------|
| **Language** | Python 3.12+, Async/Await |
| **Browser Engines** | Playwright, Patchright, Camoufox |
| **Web Framework** | FastAPI, WebSocket, Uvicorn |
| **AI/LLM** | Ollama, OpenAI, Anthropic |
| **Anti-Detection** | BrowserForge, Custom Stealth Scripts |
| **Proxy** | SOCKS5, HTTP/S, Tor, Bright Data, Decodo |
| **Data** | Pydantic, aiofiles, orjson |
| **Testing** | Pytest, 982 tests |
| **DevOps** | Docker, Docker Compose, GitHub Actions |

---

## Web Dashboard

GhostStorm includes a modern web-based control panel for managing all automation tasks.

```bash
# Start the dashboard
python -m ghoststorm.api

# Open in browser
http://localhost:8000
```

### Dashboard Pages

| Page | Description |
|------|-------------|
| **Tasks** | 6-step task wizard with platform detection, proxy selection, fingerprint config |
| **Proxies** | Proxy management, health checking, aggregation from 20+ sources |
| **Data** | User agents, screen sizes, referrers, device profiles browser |
| **Zefoy** | TikTok view boosting with captcha solving |
| **Engine** | Browser engine control, worker management, real-time metrics |
| **AI Control** | LLM mode selection (Off/Assist/Autonomous), vision settings |
| **Algorithms** | Custom TikTok Gorgon signature algorithms |
| **Settings** | Global configuration, API keys, provider settings |

### AI Assistant Sidebar

Built-in AI assistant powered by **Ollama** (local LLM) with full project access and expert knowledge of the GhostStorm architecture.

**Core Features:**
- **Chat Interface**: Natural language interaction (`Cmd+K` to toggle)
- **File Operations**: Read, write, search files in your project
- **Command Execution**: Run shell commands with approval system
- **Docker Integration**: One-click Ollama container management with GPU support

**Expert Knowledge Built-In:**
The AI assistant has comprehensive understanding of:
- Browser automation patterns (Patchright, Camoufox, Playwright)
- Anti-detection techniques (fingerprinting, evasion, stealth)
- Proxy management and rotation strategies
- Flow recording and LLM-driven replay
- Plugin system architecture and hook specifications
- All configuration options and their effects

**Self-Discovery Mode:**
When the AI needs deeper context, it automatically explores the codebase:
- Searches for implementations (`class.*Provider`)
- Reads source files for accurate answers
- Navigates to key modules (orchestrator, interfaces, models)
- Never guesses - always verifies against actual code

**What It Can Help With:**
- Debugging browser automation issues
- Configuring campaigns, proxies, fingerprints
- Writing automation scripts and flows
- Troubleshooting anti-detection failures
- Understanding and modifying the codebase
- Implementing new plugins

**Recommended Models:**
| Model | VRAM | Use Case |
|-------|------|----------|
| `qwen2.5-coder:32b` | 20GB | Best for code tasks |
| `deepseek-coder:33b` | 22GB | Excellent coding |
| `deepseek-coder-v2:16b` | 10GB | Great for 12GB cards |
| `qwen2.5-coder:7b` | 5GB | Budget option |

### Docker Container Management

```bash
# Automatic container management from UI
# Or manual:
docker run -d --name ghoststorm-ollama --gpus all \
  -v ollama_data:/root/.ollama -p 11434:11434 \
  ollama/ollama:latest
```

---

## Goal-Based Flow Recorder

Record browser flows once, replay infinitely with variation. Each execution takes a **different path** to achieve the same goal - preventing detection through behavioral fingerprinting.

### Recording a Flow

1. Open **Tasks** page → Click **Record Flow** (red button)
2. Configure **Stealth Options**:
   - **Hide IP (Proxy)**: Route through proxy during recording
   - **Fake Identity**: Random browser fingerprint
   - **Block WebRTC**: Prevent IP leak via WebRTC
   - **Canvas/WebGL Noise**: Anti-fingerprinting noise injection
3. Enter flow name and start URL → Click **Start Recording**
4. Browser opens with **floating toolbar**:
   - 🔴 Recording indicator with pause/resume
   - 📌 **Mark Checkpoint** - Save goal points
   - ⏹ **Stop & Save** - Finalize flow
5. Navigate, click, interact - mark checkpoints at key moments
6. Stop recording → Flow saved to library

### Checkpoint Types

| Type | Use Case |
|------|----------|
| `navigation` | Page navigation complete |
| `click` | Button/link clicked |
| `input` | Form field filled |
| `wait` | Wait for element/condition |
| `scroll` | Scroll to position |
| `external` | External link clicked |
| `custom` | Any custom action |

### Executing Recorded Flows

1. Open **Flows** library (purple button)
2. Select a flow → **Execute**
3. Configure:
   - **Browser Engine**: Camoufox (recommended), Patchright, Playwright
   - **Variation Level**: Low/Medium/High
   - **Workers**: Concurrent executions
   - **Proxy Pool**: Optional specific pool

### How Variation Works

The LLM executes each checkpoint using **AUTONOMOUS mode**:
- Reads checkpoint goal description
- Analyzes current page (DOM + optional vision)
- Finds **different elements** that achieve the same goal
- Uses **CoherenceEngine** for consistent persona behavior
- Takes **different paths** each run while achieving identical outcomes

---

## Browser Engines

| Engine | Stealth Level | Best For |
|--------|---------------|----------|
| **Patchright** | High | Chromium with CDP bypass, general automation |
| **Camoufox** | Maximum | Firefox with C++ fingerprint spoofing (0% headless detection) |
| **Playwright** | Standard | Multi-browser support (Chromium/Firefox/WebKit) |

---

## Network Anonymity (Full IP Protection)

| Protection | Method |
|------------|--------|
| **DNS Leak Prevention** | DNS-over-HTTPS (DoH) via Google DNS on all browsers |
| **IPv6 Leak Prevention** | Disabled across all browser engines |
| **WebRTC Leak Prevention** | ICE servers stripped at runtime |
| **Proxy Bypass Protection** | All HTTP/HTTPS traffic forced through proxy |
| **TLS Fingerprint Impersonation** | curl_cffi with 13+ browser profiles |
| **Accept-Language Randomization** | Per-request header variation (10 variants) |

---

## Anti-Fingerprinting (20+ Vectors Protected)

| Vector | Protection Method |
|--------|-------------------|
| **Canvas** | Per-render noise with pixel variation |
| **WebGL** | 13 parameters randomized |
| **Audio** | Microsecond timing jitter |
| **Fonts** | Whitelist-based blocking |
| **Sec-CH-UA Headers** | Client hints fully spoofed |
| **Storage Tracking** | localStorage/sessionStorage cleared, IndexedDB blocked |
| **Timezone-Locale** | 58 timezone mappings to prevent mismatches |
| **Geolocation** | 50m coordinate jitter per request |
| **Navigator Properties** | All automation indicators removed |
| **Plugin Enumeration** | Realistic Chrome plugin array |
| **Battery API** | Randomized values |
| **CDP Detection** | Runtime traces removed |

---

## Device Fingerprints

- **2505+ device profiles** from `devices.json`
- **755-line stealth JavaScript** comprehensive anti-detection script
- **BrowserForge integration** for dynamic fingerprint generation
- **iOS device spoofing** with 114 Apple device models
- **Mobile in-app browser** fingerprints

---

## Proxy Management

| Provider | Description |
|----------|-------------|
| **File-based** | Load proxies from text files |
| **Rotating** | Round-robin, weighted, random strategies |
| **Dynamic Auth** | Chrome extension for authenticated proxies |
| **Tor Integration** | SOCKS5 proxy with circuit rotation |
| **Tor Browser** | Full Tor Browser with native fingerprint |
| **Bright Data** | Residential/datacenter proxy integration |
| **Decodo** | Decodo proxy integration |
| **Premium API** | Generic premium proxy API support |
| **Aggregator** | 20+ public proxy sources (47,000+ proxies) |

---

## Human Behavior Simulation

| Behavior | Features |
|----------|----------|
| **Mouse Movement** | Bezier curves, micro-movements, tremor simulation, overshoot |
| **ML Mouse** | Machine learning trained on real human mouse patterns |
| **Scrolling** | Momentum-based, reading pauses, natural deceleration |
| **Keyboard** | Realistic WPM, occasional typos, variable delays |
| **Timing** | Variable dwell times, action-specific delays, micro-breaks |
| **CoherenceEngine** | Cross-fingerprint consistency, persona-based behavior |

---

## LLM-Powered Automation

Three modes for AI-controlled browsing:

| Mode | Description |
|------|-------------|
| **Off** | Manual automation using scripts |
| **Assist** | AI suggests actions, you approve |
| **Autonomous** | AI executes tasks independently |

**Vision Mode:**
- `off`: DOM analysis only
- `auto`: Vision as fallback when DOM fails
- `always`: Screenshot analysis for every action

**Supported Providers:**
- OpenAI (GPT-4o, GPT-4)
- Anthropic (Claude)
- Ollama (Local - Qwen, Llama, CodeLlama)

---

## Platform Automation

| Platform | Features |
|----------|----------|
| **TikTok** | Video watching, profile visits, bio clicks, variable watch times |
| **Instagram** | Reels, stories, posts, profile automation with in-app browser simulation |
| **YouTube** | Videos, Shorts, channels, description clicks |
| **DEXTools** | Trending campaigns, pair explorer, social clicking, chart interaction |
| **Zefoy** | TikTok view boosting with OCR captcha solving |
| **Generic** | Configurable automation for any website |

---

## DEXTools Trending Campaign

Push any token to DEXTools trending with realistic visitor simulation. Natural human behavior patterns prevent detection while maintaining high view velocity.

### Behavior Distribution

| Behavior | Weight | Actions |
|----------|--------|---------|
| **Passive** | 60% | View page, hover chart, leave |
| **Light** | 30% | View + 1 interaction (social click or tab) |
| **Engaged** | 10% | Multiple social clicks, tab switches, extended dwell |

### Visit Distribution Modes

| Mode | Pattern |
|------|---------|
| **Natural** | Exponential gaps simulating real traffic |
| **Even** | Uniform distribution over duration |
| **Burst** | Clustered activity with quiet periods |

### Quick Start

```python
from ghoststorm.plugins.automation.dextools_campaign import (
    run_dextools_campaign,
    CampaignConfig,
)

# Simple usage
result = await run_dextools_campaign(
    pair_url="https://www.dextools.io/app/ether/pair-explorer/0x...",
    num_visitors=100,
    duration_hours=24.0,
    proxy_provider=my_proxy_provider,
    browser_launcher=playwright.chromium,
)

print(f"Success rate: {result.stats.success_rate * 100}%")
print(f"Avg dwell time: {result.stats.avg_dwell_time_s}s")
```

### Campaign Configuration

```python
config = CampaignConfig(
    pair_url="https://www.dextools.io/app/ether/pair-explorer/0x...",

    # Scale
    num_visitors=100,
    duration_hours=24.0,

    # Concurrency
    max_concurrent=5,
    min_delay_between_visitors_s=10.0,
    max_delay_between_visitors_s=60.0,

    # Distribution
    distribution_mode="natural",  # natural, even, burst

    # Behavior
    behavior_mode="realistic",    # realistic, passive, light, engaged
    dwell_time_min=30.0,
    dwell_time_max=120.0,

    # Browser
    headless=True,
    browser_engine="patchright",
)
```

### Human-Like Features

- **Bezier curve mouse movement** with tremor simulation
- **Natural scrolling** with momentum and reading pauses
- **Chart hovering** at random positions
- **Variable dwell times** based on behavior profile
- **Social link clicking** opens and closes tabs naturally
- **Tab switching** with realistic delays
- **Micro-interactions** during idle periods

### Real-Time Monitoring

```python
campaign = DEXToolsTrendingCampaign(config, proxy_provider, browser_launcher)

# Progress callback
def on_progress(stats):
    print(f"Completed: {stats.completed_visitors}/{stats.total_visitors}")
    print(f"Success rate: {stats.success_rate * 100}%")

campaign.on_progress(on_progress)
await campaign.start()
```

### Campaign Stats

| Metric | Description |
|--------|-------------|
| `completed_visitors` | Successfully completed visits |
| `failed_visitors` | Failed visits |
| `success_rate` | Completion percentage |
| `passive/light/engaged_count` | Behavior distribution |
| `total_social_clicks` | Social links clicked |
| `total_tab_clicks` | Chart tabs clicked |
| `avg_dwell_time_s` | Average time on page |

---

## Installation

### Quick Start (Recommended)

```bash
# Clone the repository
git clone https://github.com/devbyteai/ghoststorm.git
cd ghoststorm

# Install with uv (recommended)
uv sync --all-extras --dev

# Install browser
uv run patchright install chromium

# Start the dashboard
make dev
```

### Alternative Installation Methods

```bash
# With pip
pip install ghoststorm

# With Docker
docker compose up -d

# Development in GitHub Codespaces (one-click)
# Click "Code" → "Codespaces" → "Create codespace"
```

### Browser Engines

```bash
# Patchright (recommended - high stealth)
uv run patchright install chromium

# Camoufox (maximum stealth - Firefox based)
pip install camoufox && python -m camoufox fetch

# Playwright (multi-browser)
playwright install chromium firefox webkit
```

---

## Quick Start

### Option 1: Web Dashboard

```bash
make dev
# Open http://localhost:8000
```

### Option 2: CLI

```bash
# Visit URLs with human simulation
ghoststorm visit urls.txt --workers 5 --headless

# With proxy rotation
ghoststorm visit urls.txt --proxy-file proxies.txt --workers 10

# Test proxies
ghoststorm proxy test --file proxies.txt --concurrent 20
```

### Option 3: Python API

```python
import asyncio
from ghoststorm.core.engine.orchestrator import Orchestrator
from ghoststorm.core.models.task import Task, TaskType, TaskConfig
from ghoststorm.core.models.config import GhostStormConfig

async def main():
    config = GhostStormConfig()
    orchestrator = Orchestrator(config)
    await orchestrator.start()

    task = Task(
        url="https://example.com",
        task_type=TaskType.VISIT,
        config=TaskConfig(
            human_simulation=True,
            scroll_page=True,
            dwell_time=(5.0, 15.0),
        )
    )

    result = await orchestrator.run_task(task)
    print(f"Completed: {result.status}")
    await orchestrator.stop()

asyncio.run(main())
```

> **More examples:** See the [`examples/`](examples/) folder for complete working code.

---

## Configuration

### Default Configuration

```yaml
engine:
  default: patchright
  fallback_chain: [patchright, playwright]
  headless: true
  stealth_level: high
  timeout: 30000

concurrency:
  max_workers: 10
  max_contexts_per_browser: 5
  task_timeout: 120

proxy:
  rotation_strategy: weighted
  health_check_interval: 300
  max_consecutive_failures: 3

fingerprint:
  provider: browserforge
  randomize_per_session: true
  consistency: strict

behavior:
  human_simulation: true
  dwell_time_s: [5.0, 15.0]
  scroll_on_visit: true
```

---

## API Endpoints

### Core APIs

| Endpoint | Description |
|----------|-------------|
| `POST /api/tasks` | Create new task |
| `GET /api/tasks` | List all tasks |
| `GET /api/tasks/{id}` | Get task status |
| `DELETE /api/tasks/{id}` | Cancel task |
| `GET /api/proxies` | List proxies |
| `POST /api/proxies/test` | Test proxies |
| `GET /api/metrics` | Dashboard metrics |

### Flow Recording APIs

| Endpoint | Description |
|----------|-------------|
| `GET /api/flows` | List all flows |
| `POST /api/flows/record/start` | Start recording |
| `POST /api/flows/record/{id}/stop` | Stop recording |
| `POST /api/flows/{id}/execute` | Execute flow |
| `GET /api/flows/{id}` | Get flow details |

### AI Assistant APIs

| Endpoint | Description |
|----------|-------------|
| `POST /api/assistant/chat` | Chat with AI |
| `GET /api/assistant/files` | Browse files |
| `POST /api/assistant/execute` | Run command |
| `GET /api/assistant/models` | List Ollama models |
| `POST /api/assistant/models/pull` | Install model |
| `GET /api/assistant/docker/status` | Docker status |
| `POST /api/assistant/docker/start` | Start Ollama container |

---

## Data Files

```
data/
├── user_agents/          # 49,778 browser user agents
│   ├── aggregated.txt    # All unique user agents
│   ├── android.txt       # Android device UAs
│   ├── iphone.txt        # iPhone UAs
│   └── ...
├── screen_sizes/         # Device resolutions
├── referrers/            # Traffic sources
│   ├── search_engines.txt
│   ├── social_media.txt
│   ├── video_platforms.txt
│   └── direct.txt
├── fingerprints/
│   └── devices.json      # 2505 device profiles
├── evasion/
│   └── stealth_template.js
├── proxies/
│   ├── aggregated.txt    # 47,208 proxies
│   └── proxies.txt       # Active proxy list
├── flows/                # Recorded flow storage
└── blacklists/
    └── default.txt
```

---

## Architecture

```
ghoststorm/
├── src/ghoststorm/
│   ├── api/
│   │   ├── routes/           # FastAPI endpoints
│   │   │   ├── tasks.py
│   │   │   ├── flows.py
│   │   │   ├── assistant.py
│   │   │   └── ...
│   │   ├── static/           # Web dashboard
│   │   │   ├── js/app.js
│   │   │   ├── js/sidebar.js
│   │   │   ├── pages/
│   │   │   └── index.html
│   │   └── schemas.py
│   ├── core/
│   │   ├── assistant/        # AI assistant agent
│   │   ├── engine/           # Orchestrator, workers
│   │   ├── events/           # Event bus
│   │   ├── flow/             # Flow recorder/executor
│   │   ├── llm/              # LLM providers
│   │   └── models/           # Data models
│   ├── plugins/
│   │   ├── automation/       # Platform automation
│   │   ├── behavior/         # Human simulation
│   │   ├── browsers/         # Engine implementations
│   │   ├── evasion/          # Anti-detection
│   │   ├── fingerprints/     # Fingerprint generators
│   │   ├── network/          # TLS/rate limiting
│   │   └── proxies/          # Proxy providers
│   └── cli/                  # Typer CLI
├── config/
├── data/
└── tests/
```

---

## Tor Integration

### Method 1: Tor SOCKS5 Proxy

```python
from ghoststorm.plugins.proxies import TorProxyProvider, TorConfig

config = TorConfig(
    socks_host="127.0.0.1",
    socks_port=9050,
    control_port=9051,
    control_password="your_password",
    circuit_strategy=TorCircuitStrategy.ROTATE_PER_SESSION,
)

provider = TorProxyProvider(config)
await provider.initialize()
proxy = await provider.get_proxy()  # socks5://127.0.0.1:9050
await provider.rotate_circuit()     # New IP
```

### Method 2: Tor Browser

```python
from ghoststorm.plugins.proxies import TorBrowserLauncher

launcher = TorBrowserLauncher(
    browser_path="/path/to/tor-browser/Browser/firefox"
)
await launcher.launch("https://example.com")
await launcher.restart("https://example.com")  # New identity
await launcher.kill()
```

---

## Security Verification

Test your anonymity at these sites:

| Site | Tests |
|------|-------|
| [ipleak.net](https://ipleak.net) | IP, DNS, WebRTC, IPv6 leaks |
| [browserleaks.com](https://browserleaks.com) | Canvas, WebGL, Audio, Fonts |
| [coveryourtracks.eff.org](https://coveryourtracks.eff.org) | Fingerprint uniqueness |
| [creepjs.com](https://creepjs.com) | Advanced fingerprint detection |
| [bot.sannysoft.com](https://bot.sannysoft.com) | Automation detection |

**Expected Results:**
- No DNS/WebRTC/IPv6 leaks
- Unique fingerprint per session
- No automation indicators detected

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + K` | Toggle AI Assistant sidebar |
| `Escape` | Close sidebar/modals |

---

## Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 20+ (for web dashboard)
- Docker (optional)

### Setup

```bash
# Clone and install
git clone https://github.com/devbyteai/ghoststorm.git
cd ghoststorm
uv sync --all-extras --dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests
make test

# Start development server
make dev
```

### Available Commands

```bash
make help          # Show all commands
make dev           # Start dev server with hot reload
make test          # Run all tests
make test-cov      # Run tests with coverage
make lint          # Run linter
make format        # Format code
make typecheck     # Run type checker
make build         # Build package
make docker        # Build Docker image
make docs          # Build documentation
```

### Development with Docker

```bash
# Start full dev environment (API + Ollama + Redis)
docker compose -f docker-compose.dev.yml up -d

# View logs
docker compose -f docker-compose.dev.yml logs -f ghoststorm
```

### IDE Setup

The repository includes configurations for VS Code:
- `.vscode/settings.json` - Editor settings, formatters
- `.vscode/launch.json` - Debug configurations
- `.vscode/extensions.json` - Recommended extensions

**GitHub Codespaces:** One-click development environment. Click "Code" → "Codespaces" → "Create codespace".

---

## Examples

Working code examples in the [`examples/`](examples/) folder:

| Example | Description |
|---------|-------------|
| [`basic_visit.py`](examples/basic_visit.py) | Simple URL visit with human simulation |
| [`batch_visits.py`](examples/batch_visits.py) | Concurrent batch processing |
| [`with_proxies.py`](examples/with_proxies.py) | Proxy rotation and management |
| [`flow_recording.py`](examples/flow_recording.py) | Record and replay browser flows |
| [`llm_automation.py`](examples/llm_automation.py) | AI-powered autonomous browsing |
| [`stealth_config.py`](examples/stealth_config.py) | Anti-detection configuration |

```bash
# Run any example
uv run python examples/basic_visit.py
```

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`) and linting (`make lint`)
5. Commit your changes
6. Push to the branch
7. Open a Pull Request

### Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

### Security

Report security vulnerabilities privately via [GitHub Security Advisories](https://github.com/devbyteai/ghoststorm/security/advisories/new). See [SECURITY.md](SECURITY.md) for details.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features and future direction.

---

## Support

- [Documentation](https://devbyteai.github.io/ghoststorm)
- [GitHub Issues](https://github.com/devbyteai/ghoststorm/issues)
- [GitHub Discussions](https://github.com/devbyteai/ghoststorm/discussions)

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with obsessive attention to anti-detection by <a href="https://github.com/devbyteai">devbyteai</a></sub>
</p>
