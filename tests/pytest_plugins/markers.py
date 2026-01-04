"""Custom pytest markers and CLI options for E2E testing."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command-line options for E2E tests."""
    parser.addoption(
        "--run-real",
        action="store_true",
        default=False,
        help="Run tests against real services (Ollama, browsers, proxies)",
    )
    parser.addoption(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama service URL for real tests",
    )
    parser.addoption(
        "--api-url",
        default="http://localhost:8000",
        help="GhostStorm API URL for E2E tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "api: marks API endpoint tests")
    config.addinivalue_line("markers", "ui: marks UI/Playwright tests")
    config.addinivalue_line("markers", "real: marks tests requiring real services")
    config.addinivalue_line("markers", "mock: marks tests using mocked services")
    config.addinivalue_line("markers", "ollama: marks tests requiring Ollama")
    config.addinivalue_line("markers", "docker: marks tests requiring Docker")
    config.addinivalue_line("markers", "browser: marks tests requiring browser engine")
    config.addinivalue_line("markers", "websocket: marks WebSocket tests")
    config.addinivalue_line("markers", "flow: marks Flow Recorder tests")
    config.addinivalue_line("markers", "assistant: marks AI Assistant tests")


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip real tests unless --run-real flag is provided."""
    if config.getoption("--run-real"):
        # Running real tests - don't skip anything
        return

    skip_real = pytest.mark.skip(reason="Need --run-real option to run real service tests")

    for item in items:
        if "real" in item.keywords:
            item.add_marker(skip_real)
