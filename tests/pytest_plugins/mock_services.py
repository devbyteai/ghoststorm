"""Mock services for E2E testing without real external dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# MOCK OLLAMA SERVICE
# ============================================================================


@dataclass
class MockOllamaService:
    """Mock Ollama LLM service for testing."""

    models: list[dict[str, str]] = field(
        default_factory=lambda: [
            {"name": "llama3.2", "size": "2.0GB"},
            {"name": "qwen2.5-coder:7b", "size": "4.4GB"},
            {"name": "mistral", "size": "4.1GB"},
        ]
    )
    chat_responses: list[str] = field(
        default_factory=lambda: [
            "I can help you with that task.",
            "Let me analyze this page for you.",
            "Based on my analysis, here's what I found.",
        ]
    )
    _response_index: int = 0

    def get_next_response(self) -> str:
        """Get next chat response (cycles through responses)."""
        response = self.chat_responses[self._response_index % len(self.chat_responses)]
        self._response_index += 1
        return response

    async def mock_tags(self) -> dict[str, Any]:
        """Mock /api/tags endpoint."""
        return {"models": self.models}

    async def mock_generate(self, prompt: str) -> dict[str, str]:
        """Mock /api/generate endpoint."""
        return {"response": self.get_next_response()}

    async def mock_chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Mock /api/chat endpoint."""
        return {
            "message": {
                "role": "assistant",
                "content": self.get_next_response(),
            },
            "done": True,
        }

    async def mock_pull(self, model: str) -> dict[str, str]:
        """Mock /api/pull endpoint."""
        return {"status": "success"}

    async def mock_delete(self, model: str) -> dict[str, str]:
        """Mock /api/delete endpoint."""
        self.models = [m for m in self.models if m["name"] != model]
        return {"status": "success"}


# ============================================================================
# MOCK DOCKER SERVICE
# ============================================================================


@dataclass
class MockDockerService:
    """Mock Docker service for container management testing."""

    container_running: bool = False
    container_exists: bool = False
    container_id: str = "abc123def456"
    gpu_available: bool = True

    async def mock_version(self) -> tuple[str, str, int]:
        """Mock docker version command."""
        return ("24.0.0", "", 0)

    async def mock_ps(self) -> tuple[str, str, int]:
        """Mock docker ps command."""
        if not self.container_exists:
            return ("", "", 0)

        status = "Up 2 hours" if self.container_running else "Exited (0) 2 hours ago"
        return (f"{self.container_id}|{status}", "", 0)

    async def mock_start(self) -> tuple[str, str, int]:
        """Mock docker start command."""
        if not self.container_exists:
            return ("", "Container not found", 1)
        self.container_running = True
        return (self.container_id, "", 0)

    async def mock_stop(self) -> tuple[str, str, int]:
        """Mock docker stop command."""
        if not self.container_exists:
            return ("", "Container not found", 1)
        self.container_running = False
        return (self.container_id, "", 0)

    async def mock_run(self, with_gpu: bool = True) -> tuple[str, str, int]:
        """Mock docker run command."""
        if with_gpu and not self.gpu_available:
            return ("", "Error: could not select device driver with capabilities: [[gpu]]", 1)
        self.container_exists = True
        self.container_running = True
        return (self.container_id, "", 0)

    async def mock_rm(self) -> tuple[str, str, int]:
        """Mock docker rm command."""
        if not self.container_exists:
            return ("", "Container not found", 1)
        self.container_exists = False
        self.container_running = False
        return (self.container_id, "", 0)

    async def mock_logs(self) -> tuple[str, str, int]:
        """Mock docker logs command."""
        if not self.container_exists:
            return ("", "Container not found", 1)
        return ("Ollama started successfully\nListening on :11434", "", 0)


# ============================================================================
# MOCK ORCHESTRATOR
# ============================================================================


def create_mock_orchestrator() -> MagicMock:
    """Create a fully mocked orchestrator for API tests."""
    orchestrator = MagicMock()

    # Core methods
    orchestrator.start = AsyncMock()
    orchestrator.stop = AsyncMock()
    orchestrator.get_health = AsyncMock(
        return_value={
            "level": "healthy",
            "message": "All systems operational",
            "details": {},
        }
    )

    # LLM service
    orchestrator.llm_service = MagicMock()
    orchestrator.llm_service.complete = AsyncMock(return_value="Mock LLM response")
    orchestrator.llm_service.get_providers = MagicMock(
        return_value=[
            {"name": "ollama", "available": True},
            {"name": "openai", "available": False},
        ]
    )

    # LLM controller
    orchestrator.llm_controller = MagicMock()
    orchestrator.llm_controller.mode = "off"
    orchestrator.llm_controller.vision_mode = "off"

    # DOM service
    orchestrator.dom_service = MagicMock()
    orchestrator.dom_service.get_state = AsyncMock(return_value=None)

    # Event bus
    orchestrator.event_bus = MagicMock()
    orchestrator.event_bus.emit = AsyncMock()
    orchestrator.event_bus.subscribe = MagicMock()

    # Watchdog manager
    orchestrator.watchdog_manager = MagicMock()
    orchestrator.watchdog_manager.get_all_status = MagicMock(return_value={})

    return orchestrator


# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture
def mock_ollama_service() -> MockOllamaService:
    """Create mock Ollama service."""
    return MockOllamaService()


@pytest.fixture
def mock_docker_service() -> MockDockerService:
    """Create mock Docker service."""
    return MockDockerService()


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    """Create mock orchestrator."""
    return create_mock_orchestrator()


@pytest.fixture
def patch_ollama(mock_ollama_service: MockOllamaService):
    """Patch httpx.AsyncClient to mock Ollama responses."""
    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()

        async def mock_get(url: str, **kwargs: Any) -> MagicMock:
            response = MagicMock()
            if "/api/tags" in url:
                response.status_code = 200
                response.json = lambda: {"models": mock_ollama_service.models}
            else:
                response.status_code = 404
            return response

        async def mock_post(url: str, **kwargs: Any) -> MagicMock:
            response = MagicMock()
            response.status_code = 200

            if "/api/generate" in url:
                response.json = lambda: {"response": mock_ollama_service.get_next_response()}
            elif "/api/chat" in url:
                response.json = lambda: {
                    "message": {
                        "role": "assistant",
                        "content": mock_ollama_service.get_next_response(),
                    },
                    "done": True,
                }
            elif "/api/pull" in url:
                response.json = lambda: {"status": "success"}

            return response

        client_instance.get = mock_get
        client_instance.post = mock_post
        mock_client.return_value.__aenter__.return_value = client_instance

        yield mock_ollama_service


@pytest.fixture
def patch_docker(mock_docker_service: MockDockerService):
    """Patch asyncio.create_subprocess_exec to mock Docker commands."""

    async def mock_subprocess(*args: Any, **kwargs: Any) -> MagicMock:
        proc = MagicMock()
        cmd = " ".join(str(a) for a in args)

        if "docker version" in cmd:
            stdout, stderr, code = await mock_docker_service.mock_version()
        elif "docker ps" in cmd:
            stdout, stderr, code = await mock_docker_service.mock_ps()
        elif "docker start" in cmd:
            stdout, stderr, code = await mock_docker_service.mock_start()
        elif "docker stop" in cmd:
            stdout, stderr, code = await mock_docker_service.mock_stop()
        elif "docker run" in cmd:
            with_gpu = "--gpus" in cmd
            stdout, stderr, code = await mock_docker_service.mock_run(with_gpu)
        elif "docker rm" in cmd:
            stdout, stderr, code = await mock_docker_service.mock_rm()
        elif "docker logs" in cmd:
            stdout, stderr, code = await mock_docker_service.mock_logs()
        else:
            stdout, stderr, code = "", "", 0

        proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
        proc.returncode = code
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_subprocess):
        yield mock_docker_service


@pytest.fixture
def service_mode(request: pytest.FixtureRequest) -> str:
    """Determine if running in mock or real mode."""
    if request.config.getoption("--run-real") and "real" in request.keywords:
        return "real"
    return "mock"
