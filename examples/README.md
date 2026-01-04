# GhostStorm Examples

Working examples demonstrating GhostStorm capabilities.

## Getting Started

```bash
# Install GhostStorm
uv sync --all-extras --dev

# Run any example
uv run python examples/basic_visit.py
```

## Examples

| Example | Description |
|---------|-------------|
| `basic_visit.py` | Simple URL visit with human simulation |
| `batch_visits.py` | Concurrent batch processing |
| `with_proxies.py` | Proxy rotation and management |
| `flow_recording.py` | Record and replay browser flows |
| `llm_automation.py` | AI-powered autonomous browsing |
| `stealth_config.py` | Anti-detection configuration |

## Prerequisites

- Python 3.11+
- For LLM examples: Ollama running locally
- For proxy examples: proxies.txt file

## Documentation

See the [full documentation](https://devbyteai.github.io/ghoststorm) for more details.
