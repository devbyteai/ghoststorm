"""AI Agent for GhostStorm Assistant.

Integrates with Ollama for local LLM and provides tools for:
- Reading files
- Writing/editing files
- Executing commands
- Searching code
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from ghoststorm.core.assistant.sandbox import (
    CommandSandbox,
    CommandStatus,
    FileSandbox,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

logger = structlog.get_logger(__name__)


class ToolType(Enum):
    """Types of agent tools."""

    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    LIST_FILES = "list_files"
    SEARCH = "search"
    EXECUTE = "execute"


@dataclass
class ToolCall:
    """Represents a tool call from the agent."""

    name: str
    arguments: dict[str, Any]
    requires_approval: bool = False


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool: str
    success: bool
    result: Any
    error: str | None = None


@dataclass
class Message:
    """Chat message."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None


# Best local coding models (in order of preference)
# These 3 are the sweet spot for most users:
#   - qwen2.5-coder:32b   -> 24GB GPU (RTX 3090/4090)
#   - deepseek-coder:33b  -> 24GB GPU (RTX 3090/4090)
#   - deepseek-coder-v2:16b -> 12GB GPU (RTX 3060/4070)
RECOMMENDED_MODELS = [
    "qwen2.5-coder:32b",  # Best coding model (~20GB VRAM)
    "deepseek-coder:33b",  # Excellent coding (~22GB VRAM)
    "deepseek-coder-v2:16b",  # Great for 12GB cards (~10GB VRAM)
    "qwen2.5-coder:14b",  # Good fallback (~10GB VRAM)
    "qwen2.5-coder:7b",  # Budget option (~5GB VRAM)
    "deepseek-coder:6.7b",  # Lightweight (~5GB VRAM)
]


@dataclass
class AgentConfig:
    """Agent configuration."""

    ollama_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434")
    )
    model: str = "qwen2.5-coder:32b"  # Best local coding model
    temperature: float = 0.3  # Lower temp for more precise code
    max_tokens: int = 8192  # Larger context for code
    project_root: str = "."
    command_timeout: float = 30.0


SYSTEM_PROMPT = """You are GhostStorm Assistant, an expert AI integrated into GhostStorm - a production-grade, plugin-based browser automation platform designed for traffic generation, web scraping, and load testing with advanced anti-detection capabilities.

## YOUR ROLE
You are a senior developer specializing in browser automation, anti-detection, and web technologies. You help users:
- Understand and modify the GhostStorm codebase
- Debug browser automation issues
- Configure campaigns, proxies, fingerprints, and behavior settings
- Write automation scripts and flows
- Troubleshoot anti-detection failures

## AVAILABLE TOOLS
Use tools by outputting JSON in this exact format:
```tool
{"name": "tool_name", "arguments": {"arg1": "value1"}}
```

Tools:
- read_file(path): Read file contents - ALWAYS read before editing
- write_file(path, content): Write/edit file (requires approval)
- list_files(path, pattern): List files with glob pattern
- search(query, file_pattern): Search text in codebase
- execute(command): Run shell command

## ARCHITECTURE OVERVIEW

### Core Engine (src/ghoststorm/core/engine/)
- **Orchestrator**: Central coordinator managing all subsystems
- **TaskScheduler**: Priority-based task queue (up to 10,000 concurrent)
- **WorkerPool**: Async workers with lifecycle management
- **CircuitBreaker**: Failure handling, graceful degradation

### Browser Engines (src/ghoststorm/plugins/browsers/)
| Engine | Base | Stealth Level | Use Case |
|--------|------|---------------|----------|
| Patchright | Chromium | High | Default, CDP bypass |
| Camoufox | Firefox | Maximum | C++ fingerprint spoofing |
| Playwright | Multi | Standard | Compatibility fallback |

### Task Types (src/ghoststorm/core/models/task.py)
- VISIT: Page visits with behavior simulation
- SCRAPE: Data extraction with selectors
- LOAD_TEST: Performance/stress testing
- CLICK: Click sequences (sequential/random/all)
- SCREENSHOT: Capture pages
- CUSTOM: Execute custom scripts
- RECORDED_FLOW: Replay recorded flows with variation

### Fingerprint System (src/ghoststorm/plugins/fingerprints/)
2505+ device profiles with protection for:
- Canvas (per-render noise)
- WebGL (13 parameters randomized)
- Audio (microsecond timing jitter)
- Fonts (whitelist-based blocking)
- Navigator properties
- Timezone-Locale (58 validated mappings)
- Battery, Plugins, CDP detection removal

### Proxy System (src/ghoststorm/plugins/proxies/)
Types: HTTP, HTTPS, SOCKS4, SOCKS5
Categories: Residential, Datacenter, Mobile, ISP

Rotation Strategies:
- random, round_robin, weighted, least_used
- fastest, sticky (session affinity), per_request

Providers: File, Rotating, Dynamic Auth, Tor, Bright Data, Decodo, Premium API, Aggregator (47,000+ public)

### Behavior Simulation (src/ghoststorm/plugins/behavior/)
- **Mouse**: Bezier curves, micro-movements, tremor
- **Keyboard**: WPM variation, typos, delays
- **Scroll**: Momentum-based, reading pauses
- **CoherenceEngine**: Session consistency, circadian rhythms, user personas (Casual, Researcher, Shopper, Scanner, PowerUser)

### Flow Recording (src/ghoststorm/core/flow/)
- Record user interactions as checkpoint sequences
- Replay with variation (Low/Medium/High)
- LLM-driven execution finds DIFFERENT elements achieving same goal
- Checkpoint types: Navigation, Click, Input, Wait, Scroll, External, Custom

### LLM Integration (src/ghoststorm/core/llm/)
- Providers: OpenAI, Anthropic, Ollama (local)
- LLMController: Executes browser actions from LLM decisions
- Vision modes: Off, Auto (fallback), Always
- Controller modes: Assist (human approval), Autonomous

### Plugin Hooks (src/ghoststorm/core/registry/hookspecs.py)
Extension points for: engine lifecycle, browser/page lifecycle, task execution, fingerprint/request modification, captcha/bot detection, proxy events, data extraction

## DIRECTORY STRUCTURE
```
src/ghoststorm/
├── api/           # FastAPI routes, WebSocket, schemas
├── cli/           # Typer CLI application
├── core/
│   ├── assistant/ # This AI assistant
│   ├── dom/       # DOM extraction, analysis, selectors
│   ├── engine/    # Orchestrator, scheduler, workers
│   ├── events/    # AsyncEventBus, event types
│   ├── flow/      # Flow recorder, executor, storage
│   ├── llm/       # LLM service, controller, vision
│   ├── models/    # Pydantic models (config, task, flow, etc)
│   ├── registry/  # Plugin manager, hook specs
│   └── watchdog/  # Health monitoring, auto-recovery
├── plugins/
│   ├── automation/  # Platform-specific (TikTok, Instagram, YouTube)
│   ├── behavior/    # Mouse, keyboard, scroll, timing, coherence
│   ├── browsers/    # Patchright, Camoufox, Playwright engines
│   ├── captcha/     # 2Captcha, AntiCaptcha, ZefoyOCR
│   ├── data/        # Proxy aggregator (20+ sources)
│   ├── evasion/     # Stealth scripts, font defender
│   ├── fingerprints/ # BrowserForge, device profiles, iOS spoof
│   ├── network/     # TLS client, rate limiter
│   └── proxies/     # All proxy providers
data/
├── user_agents/   # 49,778 user agents
├── fingerprints/  # 2505 device profiles
├── referrers/     # Traffic source lists
├── algorithms/    # Signature algorithms (TikTok X-Bogus)
├── behavior/      # Watch patterns
└── evasion/       # Stealth templates (755-line anti-detection)
config/            # YAML configuration files
tests/             # 982 tests (e2e, integration, unit)
```

## COMMON USER TASKS

### 1. Campaign Configuration
Config location: config/ghoststorm.yaml or GhostStormConfig model
Key settings: engine type, concurrency, fingerprint provider, proxy rotation, behavior simulation

### 2. Proxy Issues
- Check proxy health: Orchestrator runs health checks every 300s
- Rotation not working: Check rotation_strategy in ProxyConfig
- Authentication: Dynamic auth uses Chrome extension injection
- Tor issues: Check circuit rotation, control port access

### 3. Detection Problems
- Canvas fingerprinting: Increase noise in FingerprintConfig
- WebGL detection: Check webgl_spoof in evasion modules
- Timezone mismatch: Use TimezoneLocaleValidator (58 validated pairs)
- CDP detection: Use Patchright/Camoufox, not plain Playwright

### 4. Flow Recording/Replay
- Recording: FlowRecorder captures checkpoints with reference screenshots
- Replay variance: Set variation level (low/medium/high) in FlowExecutor
- LLM replay: Enable controller_mode="autonomous" in LLMConfig

### 5. Writing Automation Scripts
- Custom task scripts go in task.custom_script field
- Platform automation: See plugins/automation/ for TikTok, Instagram, YouTube patterns
- DOM analysis: Use DOMService.extract() for page structure

## CONFIGURATION REFERENCE

### Engine Config
```python
engine: str = "patchright"  # patchright, camoufox, playwright
fallback_chain: ["patchright", "camoufox", "playwright"]
headless: bool = True
stealth_level: str = "high"  # low, medium, high, paranoid
timeout: int = 30000  # ms
```

### Concurrency Config
```python
max_workers: int = 10  # 1-10000
max_contexts_per_browser: int = 5  # 1-100
max_browsers: int = 1  # 1-100
task_timeout: float = 120.0  # seconds
context_recycle_after: int = 50  # tasks
```

### Behavior Config
```python
human_simulation: bool = True
mouse: str = "bezier"  # bezier, linear, direct
typing_wpm: tuple = (40, 80)  # range
scroll: str = "natural"  # natural, smooth, instant
mistakes_enabled: bool = True
mistake_rate: float = 0.02
```

## GUIDELINES

1. **Read First**: ALWAYS read files before suggesting edits
2. **Explain Actions**: Tell user what you're doing and why
3. **Risk Awareness**: Warn about destructive operations
4. **Code Style**: Follow existing patterns - Python 3.12+, type hints, async/await
5. **Testing**: Project has 982 tests - suggest running relevant tests after changes
6. **No Secrets**: Never commit API keys, proxy credentials, or sensitive data
7. **Anti-Detection Focus**: Always consider how changes affect stealth

## SELF-DISCOVERY

When you need deeper understanding of any component, USE YOUR TOOLS proactively:

**To understand a module:**
```tool
{"name": "list_files", "arguments": {"path": "src/ghoststorm/core/engine", "pattern": "*.py"}}
```

**To find implementations:**
```tool
{"name": "search", "arguments": {"query": "class.*Provider", "file_pattern": "*.py"}}
```

**To read source code:**
```tool
{"name": "read_file", "arguments": {"path": "src/ghoststorm/core/engine/orchestrator.py"}}
```

**Key starting points when exploring:**
- Orchestrator: `core/engine/orchestrator.py` - central coordinator, how everything connects
- Interfaces: `core/interfaces/` - plugin contracts (IPage, IProxyProvider, IFingerprintGenerator)
- Models: `core/models/` - all data structures (config, task, flow, fingerprint, proxy)
- Hooks: `core/registry/hookspecs.py` - all plugin extension points
- Events: `core/events/bus.py` - pub/sub event system

Don't guess - explore the code to give accurate answers.

## DEBUGGING COMMANDS
```bash
# Run tests
pytest tests/ -v

# Type checking
mypy src/ghoststorm/

# Linting
ruff check src/

# Start server
ghoststorm serve --host 0.0.0.0 --port 8080

# Check Ollama
curl http://localhost:11434/api/tags
```

Be direct, accurate, and helpful. When you don't know something, say so and offer to search the codebase.
"""


class Agent:
    """AI Agent with tool execution capabilities."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        *,
        on_tool_approval: Callable[[ToolCall], bool] | None = None,
    ) -> None:
        """Initialize agent.

        Args:
            config: Agent configuration
            on_tool_approval: Callback for tool approval (returns True to approve)
        """
        self.config = config or AgentConfig()
        self.on_tool_approval = on_tool_approval

        # Initialize sandboxes
        project_root = Path(self.config.project_root).resolve()
        self.command_sandbox = CommandSandbox(
            project_root,
            timeout_seconds=self.config.command_timeout,
        )
        self.file_sandbox = FileSandbox(project_root)

        # Conversation history
        self.messages: list[Message] = []
        self._pending_approvals: list[ToolCall] = []

        logger.info(
            "Agent initialized",
            model=self.config.model,
            project_root=str(project_root),
        )

    def reset(self) -> None:
        """Reset conversation history."""
        self.messages = []
        self._pending_approvals = []
        logger.debug("Agent conversation reset")

    async def chat(
        self,
        user_message: str,
        *,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """Send a message and get a response.

        Args:
            user_message: User's message
            stream: Whether to stream the response

        Returns:
            Assistant's response (or async iterator if streaming)
        """
        # Add user message
        self.messages.append(Message(role="user", content=user_message))

        if stream:
            return self._chat_stream()
        else:
            return await self._chat_complete()

    async def _chat_complete(self) -> str:
        """Complete chat without streaming."""
        response = await self._call_ollama()

        # Process any tool calls in the response
        processed_response = await self._process_response(response)

        # Add to history
        self.messages.append(Message(role="assistant", content=processed_response))

        return processed_response

    async def _chat_stream(self) -> AsyncIterator[str]:
        """Stream chat response."""
        full_response = ""

        async for chunk in self._call_ollama_stream():
            full_response += chunk
            yield chunk

        # Process any tool calls after streaming completes
        processed_response = await self._process_response(full_response)

        # If tools were called, yield the additional output
        if processed_response != full_response:
            yield "\n" + processed_response[len(full_response) :]

        # Add to history
        self.messages.append(Message(role="assistant", content=processed_response))

    async def _call_ollama(self) -> str:
        """Call Ollama API for completion."""
        messages = self._build_messages()

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.config.ollama_url}/api/chat",
                    json={
                        "model": self.config.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.config.temperature,
                            "num_predict": self.config.max_tokens,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")

            except httpx.HTTPError as e:
                logger.error("Ollama API error", error=str(e))
                return f"Error connecting to Ollama: {e}"

    async def _call_ollama_stream(self) -> AsyncIterator[str]:
        """Stream from Ollama API."""
        messages = self._build_messages()

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.config.ollama_url}/api/chat",
                    json={
                        "model": self.config.model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": self.config.temperature,
                            "num_predict": self.config.max_tokens,
                        },
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

            except httpx.HTTPError as e:
                logger.error("Ollama streaming error", error=str(e))
                yield f"\nError: {e}"

    def _build_messages(self) -> list[dict[str, str]]:
        """Build messages list for Ollama API."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in self.messages:
            messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                }
            )

        return messages

    async def _process_response(self, response: str) -> str:
        """Process response and execute any tool calls."""
        # Find tool calls in response
        tool_pattern = r"```tool\s*\n({.*?})\s*\n```"
        matches = re.finditer(tool_pattern, response, re.DOTALL)

        processed = response
        tool_outputs = []

        for match in matches:
            try:
                tool_json = json.loads(match.group(1))
                tool_name = tool_json.get("name")
                tool_args = tool_json.get("arguments", {})

                if tool_name:
                    tool_call = ToolCall(
                        name=tool_name,
                        arguments=tool_args,
                        requires_approval=self._requires_approval(tool_name, tool_args),
                    )

                    result = await self._execute_tool(tool_call)
                    tool_outputs.append(f"\n**Tool: {tool_name}**\n{result}")

            except json.JSONDecodeError:
                continue

        if tool_outputs:
            processed += "\n" + "\n".join(tool_outputs)

        return processed

    def _requires_approval(self, tool_name: str, args: dict) -> bool:
        """Check if a tool call requires user approval."""
        if tool_name == "write_file":
            return True
        if tool_name == "execute":
            command = args.get("command", "")
            _, _, requires_approval = self.command_sandbox.validate_command(command)
            return requires_approval
        return False

    async def _execute_tool(self, tool_call: ToolCall) -> str:
        """Execute a tool call."""
        name = tool_call.name
        args = tool_call.arguments

        # Check approval if needed
        if tool_call.requires_approval:
            if self.on_tool_approval and not self.on_tool_approval(tool_call):
                return "[Action requires approval - waiting for user confirmation]"

        try:
            if name == "read_file":
                return await self._tool_read_file(args)
            elif name == "write_file":
                return await self._tool_write_file(args)
            elif name == "list_files":
                return await self._tool_list_files(args)
            elif name == "search":
                return await self._tool_search(args)
            elif name == "execute":
                return await self._tool_execute(args)
            else:
                return f"Unknown tool: {name}"

        except Exception as e:
            logger.error("Tool execution error", tool=name, error=str(e))
            return f"Error: {e}"

    async def _tool_read_file(self, args: dict) -> str:
        """Read file tool."""
        path = args.get("path")
        if not path:
            return "Error: path is required"

        content, error = await self.file_sandbox.read_file(path)
        if error:
            return f"Error: {error}"

        # Truncate if too long
        if len(content) > 10000:
            content = content[:10000] + "\n... (truncated)"

        return f"```\n{content}\n```"

    async def _tool_write_file(self, args: dict) -> str:
        """Write file tool."""
        path = args.get("path")
        content = args.get("content")

        if not path:
            return "Error: path is required"
        if content is None:
            return "Error: content is required"

        _success, error = await self.file_sandbox.write_file(path, content)
        if error:
            return f"Error: {error}"

        return f"File written successfully: {path}"

    async def _tool_list_files(self, args: dict) -> str:
        """List files tool."""
        path = args.get("path", ".")
        pattern = args.get("pattern", "*")

        files, error = await self.file_sandbox.list_files(path, pattern)
        if error:
            return f"Error: {error}"

        if not files:
            return "No files found"

        return "\n".join(files[:50])  # Limit output

    async def _tool_search(self, args: dict) -> str:
        """Search tool."""
        query = args.get("query")
        file_pattern = args.get("file_pattern", "*.py")

        if not query:
            return "Error: query is required"

        matches, error = await self.file_sandbox.search_files(query, ".", file_pattern)
        if error:
            return f"Error: {error}"

        if not matches:
            return f"No matches found for: {query}"

        result = []
        for m in matches[:20]:
            result.append(f"{m['file']}:{m['line']}: {m['content']}")

        return "\n".join(result)

    async def _tool_execute(self, args: dict) -> str:
        """Execute command tool."""
        command = args.get("command")
        if not command:
            return "Error: command is required"

        result = await self.command_sandbox.execute(command)

        if result.status == CommandStatus.BLOCKED:
            return f"Command blocked: {result.blocked_reason}"
        elif result.status == CommandStatus.TIMEOUT:
            return f"Command timed out after {self.config.command_timeout}s"
        elif result.status == CommandStatus.FAILED:
            output = result.stderr or result.stdout
            return f"Command failed (exit {result.exit_code}):\n{output}"
        else:
            return result.stdout or "(no output)"

    def get_pending_approvals(self) -> list[ToolCall]:
        """Get list of tool calls pending approval."""
        return self._pending_approvals.copy()

    def approve_tool(self, tool_call: ToolCall) -> None:
        """Approve a pending tool call."""
        if tool_call in self._pending_approvals:
            self._pending_approvals.remove(tool_call)

    def reject_tool(self, tool_call: ToolCall) -> None:
        """Reject a pending tool call."""
        if tool_call in self._pending_approvals:
            self._pending_approvals.remove(tool_call)

    async def get_context(self) -> dict[str, Any]:
        """Get current application context for the agent."""
        context = {
            "project_root": str(Path(self.config.project_root).resolve()),
            "model": self.config.model,
            "message_count": len(self.messages),
        }

        # Add project info
        try:
            # Check for pyproject.toml
            pyproject = Path(self.config.project_root) / "pyproject.toml"
            if pyproject.exists():
                context["has_pyproject"] = True

            # List main directories
            src = Path(self.config.project_root) / "src"
            if src.exists():
                context["src_dirs"] = [d.name for d in src.iterdir() if d.is_dir()]

        except Exception:
            pass

        return context
