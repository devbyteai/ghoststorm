"""Fixtures for journey E2E tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from unittest.mock import MagicMock

# ============================================================================
# API CLIENT FIXTURES
# ============================================================================


@pytest.fixture
def api_test_client(mock_orchestrator: MagicMock) -> TestClient:
    """Create synchronous test client for API tests."""
    from ghoststorm.api.app import create_app

    app = create_app(orchestrator=mock_orchestrator)
    return TestClient(app)


@pytest.fixture
def real_ollama_url(request: pytest.FixtureRequest) -> str:
    """Get the Ollama URL from command line option for real tests."""
    return request.config.getoption("--ollama-url")


# ============================================================================
# STATE RESET FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_journey_state():
    """Reset all in-memory state between journey tests."""
    yield

    # Reset state after test
    try:
        from ghoststorm.api.routes import tasks

        if hasattr(tasks, "_tasks"):
            tasks._tasks.clear()
    except (ImportError, AttributeError):
        pass

    try:
        from ghoststorm.api.routes import flows

        if hasattr(flows, "_active_executions"):
            flows._active_executions.clear()
    except (ImportError, AttributeError):
        pass
