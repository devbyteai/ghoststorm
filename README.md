<div align="center">

<img src="assets/logo.svg" alt="GhostStorm" width="180" height="180">

# GhostStorm

[![CI](https://img.shields.io/github/actions/workflow/status/devbyteai/ghoststorm/ci.yml?style=flat-square&label=CI)](https://github.com/devbyteai/ghoststorm/actions)
[![Stars](https://img.shields.io/github/stars/devbyteai/ghoststorm?style=flat-square)](https://github.com/devbyteai/ghoststorm/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://python.org)
[![Docs](https://img.shields.io/badge/docs-available-brightgreen?style=flat-square)](https://devbyteai.github.io/ghoststorm)

### See any page. Control any browser. Detect nothing.

AI-powered browser automation with vision, local LLMs, and enterprise stealth.

[Quick Start](#-quick-start) • [Features](#-features) • [Docs](https://devbyteai.github.io/ghoststorm) • [Examples](examples/)

</div>

---

## ✨ Features

| | |
|---|---|
| 🌐 **Universal Automation** | Works on ANY website — not locked to specific platforms |
| 👁️ **AI Vision** | Sees and understands pages via screenshot analysis |
| 🔒 **Total Privacy** | Hide your real IP, device, location — browse like a ghost |
| 🧠 **Identity Coherence** | Consistent personas with circadian rhythms and fatigue simulation |
| 🤖 **Local LLM** | Ollama integration — 100% private, no API costs |
| 🛡️ **Undetectable** | 20+ anti-fingerprinting vectors, 0% detection rate |
| 🔄 **47,000+ Proxies** | Built-in aggregator with automatic rotation |
| 📹 **Flow Recording** | Record once, replay with variation forever |

---

## 🚀 Quick Start

```bash
git clone https://github.com/devbyteai/ghoststorm.git && cd ghoststorm
uv sync --all-extras --dev && make dev
```

**Open http://localhost:8000** — that's it.

<details>
<summary>🐳 Docker</summary>

```bash
docker compose up -d
```
</details>

---

## 🆚 Why GhostStorm?

| Feature | Other Tools | GhostStorm |
|---------|-------------|------------|
| Works on any site | ❌ Platform-specific | ✅ **Universal** |
| Privacy protection | ⚠️ IP only | ✅ **Full identity (IP, device, location)** |
| Vision AI | ❌ DOM only | ✅ **Screenshot analysis** |
| Local LLM | ❌ Cloud API required | ✅ **Ollama built-in** |
| Bot detection | ⚠️ Often detected | ✅ **Undetectable** |
| Proxy support | ⚠️ Manual setup | ✅ **47K+ built-in** |
| Human behavior | ❌ Basic delays | ✅ **True human behavior** |

---

## 🔒 Private Browsing

Browse without exposing anything real:

- **Real IP** — Hidden
- **Device Profile** — Spoofed
- **Location** — Masked
- **Browser Identity** — Randomized
- **Network Leaks** — Blocked
- **Behavior Pattern** — Human-like

**Zero trace. Zero detection.**

---

## 🧠 Identity Coherence Engine

Not just random behavior — **consistent human personas** that evolve naturally:

- **User Personas** — Distinct behavior profiles
- **Circadian Rhythm** — Time-aware activity patterns
- **Attention States** — Natural focus drift
- **Session Lifecycle** — Realistic engagement arcs
- **Fatigue Modeling** — Extended session realism

Automation that behaves like a real human.

---

## 🎯 Use Cases

<table>
<tr>
<td align="center" width="25%">

### 🔒 Private Browsing
Access any site anonymously with full identity protection

</td>
<td align="center" width="25%">

### 📊 Traffic Generation
Organic visits with unique fingerprints and IPs

</td>
<td align="center" width="25%">

### 📈 DEXTools Trending
Push tokens with realistic visitor patterns

</td>
<td align="center" width="25%">

### 🎬 Platform Engagement
TikTok, Instagram, YouTube with human behavior

</td>
</tr>
</table>

---

## 💻 Usage

```python
from ghoststorm import Orchestrator, Task

async def main():
    engine = Orchestrator()
    await engine.start()

    await engine.run_task(Task(
        url="https://any-website.com",
        visits=100,
        human_simulation=True
    ))
```

See more in [`examples/`](examples/)

---

## 🤖 AI Assistant

Built-in LLM assistant that understands the entire codebase:

- **Chat interface** in the dashboard
- **File operations** — read, write, search
- **Command execution** with approval
- **Local models** via Ollama

Perfect for debugging, writing automation scripts, and extending the project.

---

## 📈 Star History

<a href="https://star-history.com/#devbyteai/ghoststorm&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=devbyteai/ghoststorm&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=devbyteai/ghoststorm&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=devbyteai/ghoststorm&type=Date" />
 </picture>
</a>

---

## 📚 Documentation

| Resource | Link |
|----------|------|
| Full Documentation | [devbyteai.github.io/ghoststorm](https://devbyteai.github.io/ghoststorm) |
| API Reference | [Docs → API](https://devbyteai.github.io/ghoststorm/api) |
| Examples | [`examples/`](examples/) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |

---

## 💜 Support

If you find GhostStorm useful:

**SOL:** `3R6DJ8BcUxMErn3d3Bqp7RV74r4uaFUV3zoQY1H6rChd`

---

## 📄 License

MIT — See [LICENSE](LICENSE)

---

<div align="center">

**[⬆ Back to Top](#ghoststorm)**

Made by [@devbyteai](https://github.com/devbyteai)

</div>
