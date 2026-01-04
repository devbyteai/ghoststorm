# GhostStorm

<div align="center">

[![CI](https://github.com/devbyteai/ghoststorm/actions/workflows/ci.yml/badge.svg)](https://github.com/devbyteai/ghoststorm/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-available-brightgreen.svg)](https://devbyteai.github.io/ghoststorm)

**Undetectable browser automation at scale.**

*Traffic generation, view boosting, and engagement automation with enterprise-grade anti-detection.*

[Getting Started](#quick-start) · [Documentation](https://devbyteai.github.io/ghoststorm) · [Examples](examples/)

</div>

---

## Why GhostStorm?

Most automation tools get detected instantly. GhostStorm was built from the ground up to be **invisible**.

| Problem | GhostStorm Solution |
|---------|---------------------|
| Bot detection | **20+ anti-fingerprinting vectors** - Canvas, WebGL, Audio, Fonts, and more |
| IP blocking | **47,000+ rotating proxies** from 20+ sources including residential pools |
| Behavioral analysis | **Human simulation engine** - Bezier mouse curves, natural scrolling, realistic typing |
| Rate limiting | **Smart throttling** with randomized delays and session management |
| Captcha walls | **Integrated solving** with 2Captcha and AntiCaptcha support |

---

## What Can You Do?

### Traffic & Views
Generate organic-looking traffic to any website. Each visit uses a unique fingerprint, IP, and behavioral pattern.

### Platform Engagement
Automate interactions on **TikTok**, **Instagram**, **YouTube**, and **DEXTools** with platform-specific behavior profiles.

### DEXTools Trending
Push any token to DEXTools trending. Realistic visitor distribution:
- **60%** passive viewers (view and leave)
- **30%** light engagement (one interaction)
- **10%** highly engaged (multiple interactions)

### Flow Recording
Record browser workflows once, replay infinitely. Each replay takes a **different path** to achieve the same goal - defeating behavioral fingerprinting.

### AI-Powered Control
Let AI handle complex automation tasks. Supports local models for complete privacy.

---

## Quick Start

```bash
git clone https://github.com/devbyteai/ghoststorm.git
cd ghoststorm
uv sync --all-extras --dev
make dev
```

Open **http://localhost:8000** for the web dashboard.

---

## Usage Example

```python
from ghoststorm import Orchestrator, Task

async def main():
    engine = Orchestrator()
    await engine.start()

    await engine.run_task(Task(
        url="https://example.com",
        visits=100,
        human_simulation=True
    ))

    await engine.stop()
```

---

## Key Capabilities

| Capability | Details |
|------------|---------|
| **Stealth** | Passes all major bot detection systems |
| **Scale** | Handle thousands of concurrent sessions |
| **Fingerprints** | 2,500+ unique device profiles |
| **Proxies** | Built-in aggregator + premium provider support |
| **Dashboard** | Real-time monitoring and control panel |
| **API** | Full REST API with WebSocket updates |
| **Testing** | 840+ tests for production reliability |

---

## Documentation

- **[Full Documentation](https://devbyteai.github.io/ghoststorm)** - Complete guides and references
- **[API Reference](https://devbyteai.github.io/ghoststorm/api)** - Endpoint documentation
- **[Examples](examples/)** - Working code samples

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">
<sub>Built by <a href="https://github.com/devbyteai">devbyteai</a></sub>
</div>
