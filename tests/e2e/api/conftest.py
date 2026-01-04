"""Fixtures for API E2E tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
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
async def api_async_client(mock_orchestrator: MagicMock) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for API tests."""
    from ghoststorm.api.app import create_app

    app = create_app(orchestrator=mock_orchestrator)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ============================================================================
# STATE RESET FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_api_state():
    """Reset all in-memory API state between tests."""
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

    try:
        from ghoststorm.api.routes import engine

        if hasattr(engine, "_jobs"):
            engine._jobs.clear()
    except (ImportError, AttributeError):
        pass

    try:
        from ghoststorm.api.routes import proxies

        if hasattr(proxies, "_jobs"):
            proxies._jobs.clear()
    except (ImportError, AttributeError):
        pass

    try:
        from ghoststorm.api.routes import dom

        if hasattr(dom, "_dom_states"):
            dom._dom_states.clear()
    except (ImportError, AttributeError):
        pass

    try:
        from ghoststorm.api.routes import assistant

        if hasattr(assistant, "_agent"):
            assistant._agent = None
        if hasattr(assistant, "_pending_actions"):
            assistant._pending_actions.clear()
    except (ImportError, AttributeError):
        pass


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def sample_task_data() -> dict[str, Any]:
    """Sample task creation data."""
    return {
        "url": "https://www.tiktok.com/@testuser/video/7123456789",
        "platform": "tiktok",
        "config": {
            "workers": 1,
            "headless": True,
            "use_proxy": False,
        },
    }


@pytest.fixture
def sample_flow_data() -> dict[str, Any]:
    """Sample flow creation data."""
    return {
        "name": "Test Flow",
        "description": "A test flow for E2E testing",
        "start_url": "https://example.com",
        "tags": ["test", "e2e"],
    }


@pytest.fixture
def sample_checkpoint_data() -> dict[str, Any]:
    """Sample checkpoint creation data."""
    return {
        "checkpoint_type": "click",
        "goal": "Click the login button",
        "element_description": "Blue button with text 'Login'",
        "selector_hints": ["#login-btn", "button.login"],
        "timing": {
            "min_delay": 0.5,
            "max_delay": 2.0,
            "timeout": 30.0,
        },
    }


@pytest.fixture
def sample_recording_data() -> dict[str, Any]:
    """Sample recording start data."""
    return {
        "name": "Test Recording",
        "start_url": "https://example.com",
        "description": "Testing flow recording",
        "stealth": {
            "use_proxy": False,
            "use_fingerprint": True,
            "block_webrtc": True,
            "canvas_noise": True,
        },
    }


@pytest.fixture
def sample_execution_config() -> dict[str, Any]:
    """Sample flow execution config."""
    return {
        "browser_engine": "patchright",
        "variation_level": "medium",
        "workers": 1,
        "use_proxy": False,
        "checkpoint_timeout": 30.0,
        "capture_screenshots": False,
    }


# ============================================================================
# URL TEST DATA
# ============================================================================


TIKTOK_URLS = [
    "https://www.tiktok.com/@testuser/video/7123456789",
    "https://vm.tiktok.com/ZM8abc123/",
    "https://www.tiktok.com/foryou",
]

INSTAGRAM_URLS = [
    "https://www.instagram.com/reel/ABC123/",
    "https://www.instagram.com/stories/testuser/",
    "https://www.instagram.com/p/XYZ789/",
]

YOUTUBE_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/shorts/abc123",
    "https://youtu.be/xyz789",
]

DEXTOOLS_URLS = [
    "https://www.dextools.io/app/en/ether/pair-explorer/0xdac17f958d2ee523a2206206994597c13d831ec7",
    "https://www.dextools.io/app/en/solana/pair-explorer/abc123def456",
    "https://www.dextools.io/app/en/bsc/pair-explorer/0x456789abc",
    "https://www.dextools.io/app/en/polygon/pair-explorer/0xpoly123",
    "https://www.dextools.io/app/en/arbitrum/pair-explorer/0xarb789",
    "https://www.dextools.io/app/en/base/pair-explorer/0xbase456",
]


@pytest.fixture(params=TIKTOK_URLS)
def tiktok_url(request: pytest.FixtureRequest) -> str:
    """Parametrized TikTok URLs for testing."""
    return request.param


@pytest.fixture(params=INSTAGRAM_URLS)
def instagram_url(request: pytest.FixtureRequest) -> str:
    """Parametrized Instagram URLs for testing."""
    return request.param


@pytest.fixture(params=YOUTUBE_URLS)
def youtube_url(request: pytest.FixtureRequest) -> str:
    """Parametrized YouTube URLs for testing."""
    return request.param


@pytest.fixture(params=DEXTOOLS_URLS)
def dextools_url(request: pytest.FixtureRequest) -> str:
    """Parametrized DEXTools URLs for testing."""
    return request.param


@pytest.fixture
def sample_dextools_task_data() -> dict[str, Any]:
    """Sample DEXTools task creation data."""
    return {
        "url": "https://www.dextools.io/app/en/ether/pair-explorer/0xdac17f958d2ee523a2206206994597c13d831ec7",
        "platform": "dextools",
        "workers": 1,
        "repeat": 1,
        "config": {
            "mode": "single",
            "behavior_mode": "realistic",
            "dwell_time_min": 30.0,
            "dwell_time_max": 90.0,
            "enable_natural_scroll": True,
            "enable_chart_hover": True,
            "enable_mouse_movement": True,
            "enable_social_clicks": True,
            "enable_tab_clicks": False,
        },
    }


@pytest.fixture
def sample_dextools_campaign_data() -> dict[str, Any]:
    """Sample DEXTools campaign task data."""
    return {
        "url": "https://www.dextools.io/app/en/ether/pair-explorer/0xdac17f958d2ee523a2206206994597c13d831ec7",
        "platform": "dextools",
        "workers": 5,
        "repeat": 100,
        "config": {
            "mode": "campaign",
            "num_visitors": 100,
            "duration_hours": 24.0,
            "max_concurrent": 5,
            "distribution_mode": "natural",
            "behavior_mode": "realistic",
            "dwell_time_min": 30.0,
            "dwell_time_max": 120.0,
        },
    }
