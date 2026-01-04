"""Global test fixtures for ghoststorm."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import pytest plugins for E2E testing
from tests.pytest_plugins.markers import (
    pytest_addoption,
    pytest_collection_modifyitems,
    pytest_configure,
)
from tests.pytest_plugins.mock_services import (
    MockDockerService,
    MockOllamaService,
    create_mock_orchestrator,
    mock_docker_service,
    mock_ollama_service,
    mock_orchestrator,
    patch_docker,
    patch_ollama,
    service_mode,
)

# Re-export for pytest discovery
__all__ = [
    "MockDockerService",
    "MockOllamaService",
    "create_mock_orchestrator",
    "mock_docker_service",
    "mock_ollama_service",
    "mock_orchestrator",
    "patch_docker",
    "patch_ollama",
    "pytest_addoption",
    "pytest_collection_modifyitems",
    "pytest_configure",
    "service_mode",
]


# ============================================================================
# MOCK BROWSER COMPONENTS
# ============================================================================


@dataclass
class MockTouchscreen:
    """Mock touchscreen for swipe gestures."""

    tap: AsyncMock = field(default_factory=AsyncMock)


@dataclass
class MockMouse:
    """Mock mouse for movement and clicks."""

    move: AsyncMock = field(default_factory=AsyncMock)
    down: AsyncMock = field(default_factory=AsyncMock)
    up: AsyncMock = field(default_factory=AsyncMock)
    click: AsyncMock = field(default_factory=AsyncMock)


@dataclass
class MockKeyboard:
    """Mock keyboard for typing."""

    type: AsyncMock = field(default_factory=AsyncMock)
    press: AsyncMock = field(default_factory=AsyncMock)
    down: AsyncMock = field(default_factory=AsyncMock)
    up: AsyncMock = field(default_factory=AsyncMock)


class MockLocator:
    """Mock locator for element queries."""

    def __init__(
        self,
        count: int = 1,
        text: str = "",
        href: str | None = None,
        duration: float | None = 30.0,
    ) -> None:
        self._count = count
        self._text = text
        self._href = href
        self._duration = duration

    async def count(self) -> int:
        return self._count

    async def click(self, timeout: int = 5000) -> None:
        pass

    async def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self._href
        return None

    async def evaluate(self, expression: str) -> Any:
        if "duration" in expression:
            return self._duration
        return None

    async def inner_text(self) -> str:
        return self._text

    @property
    def first(self) -> MockLocator:
        return self


class MockPage:
    """Mock Playwright/Patchright page."""

    def __init__(self) -> None:
        self.touchscreen = MockTouchscreen()
        self.mouse = MockMouse()
        self.keyboard = MockKeyboard()
        self._url = "https://example.com"
        self._title = "Test Page"
        self._locators: dict[str, MockLocator] = {}
        self._viewport = {"width": 390, "height": 844}
        self._init_scripts: list[str] = []

    @property
    def url(self) -> str:
        return self._url

    async def goto(self, url: str, **kwargs: Any) -> None:
        self._url = url

    async def title(self) -> str:
        return self._title

    async def wait_for_load_state(self, state: str = "load", timeout: int = 30000) -> None:
        pass

    async def set_viewport_size(self, size: dict[str, int]) -> None:
        self._viewport = size

    async def add_init_script(self, script: str) -> None:
        self._init_scripts.append(script)

    async def evaluate(self, expression: str) -> Any:
        if "_mouseX" in expression:
            return {"x": 200, "y": 400}
        if "scrollTo" in expression:
            return None
        return None

    async def go_back(self) -> None:
        pass

    async def screenshot(self, full_page: bool = False) -> bytes:
        return b"fake_screenshot_data"

    def locator(self, selector: str) -> MockLocator:
        if selector not in self._locators:
            self._locators[selector] = MockLocator()
        return self._locators[selector]

    def set_locator_count(self, selector: str, count: int) -> None:
        """Test helper to configure locator behavior."""
        self._locators[selector] = MockLocator(count=count)

    def set_locator_href(self, selector: str, href: str) -> None:
        """Test helper to configure locator href."""
        if selector in self._locators:
            self._locators[selector]._href = href
        else:
            self._locators[selector] = MockLocator(href=href)

    def set_locator_duration(self, selector: str, duration: float) -> None:
        """Test helper to configure video duration."""
        if selector in self._locators:
            self._locators[selector]._duration = duration
        else:
            self._locators[selector] = MockLocator(duration=duration)


class MockContext:
    """Mock browser context."""

    def __init__(self) -> None:
        self._pages: list[MockPage] = []

    async def new_page(self) -> MockPage:
        page = MockPage()
        self._pages.append(page)
        return page

    async def set_extra_http_headers(self, headers: dict[str, str]) -> None:
        pass

    async def close(self) -> None:
        pass


class MockBrowser:
    """Mock browser instance."""

    def __init__(self) -> None:
        self._contexts: list[MockContext] = []

    async def new_context(self, **kwargs: Any) -> MockContext:
        ctx = MockContext()
        self._contexts.append(ctx)
        return ctx

    async def close(self) -> None:
        pass


# ============================================================================
# PYTEST FIXTURES - BROWSER MOCKS
# ============================================================================


@pytest.fixture
def mock_page() -> MockPage:
    """Create a mock page for testing."""
    return MockPage()


@pytest.fixture
def mock_browser() -> MockBrowser:
    """Create a mock browser for testing."""
    return MockBrowser()


@pytest.fixture
def mock_context() -> MockContext:
    """Create a mock context for testing."""
    return MockContext()


# ============================================================================
# PYTEST FIXTURES - AUTOMATION CONFIGS
# ============================================================================


@pytest.fixture
def tiktok_config():
    """Create test TikTok configuration."""
    from ghoststorm.plugins.automation.tiktok import TikTokConfig

    return TikTokConfig(
        target_username="testuser",
        videos_per_session=(3, 5),
        skip_probability=0.2,
        bio_click_probability=0.1,
        viewport_width=390,
        viewport_height=844,
    )


@pytest.fixture
def instagram_config():
    """Create test Instagram configuration."""
    from ghoststorm.plugins.automation.instagram import InstagramConfig

    return InstagramConfig(
        target_username="testuser",
        reels_per_session=(3, 5),
        reel_skip_probability=0.2,
        bio_link_click_probability=0.1,
    )


@pytest.fixture
def youtube_config():
    """Create test YouTube configuration."""
    from ghoststorm.plugins.automation.youtube import YouTubeConfig

    return YouTubeConfig(
        target_video_urls=["https://youtube.com/watch?v=test123"],
        min_watch_seconds=5.0,  # Shorter for tests
        content_mode="videos",
    )


@pytest.fixture
def dextools_config():
    """Create test DEXTools configuration."""
    from ghoststorm.plugins.automation.dextools import DEXToolsConfig

    return DEXToolsConfig(
        pair_url="https://www.dextools.io/app/en/ether/pair-explorer/0xtest",
        behavior_mode="realistic",
        dwell_time_min=5.0,  # Fast for tests
        dwell_time_max=10.0,
        enable_natural_scroll=True,
        enable_chart_hover=True,
        enable_mouse_movement=False,  # Disable for faster tests
        enable_social_clicks=False,
    )


@pytest.fixture
def dextools_automation(dextools_config):
    """Create test DEXTools automation instance."""
    from ghoststorm.plugins.automation.dextools import DEXToolsAutomation

    return DEXToolsAutomation(config=dextools_config)


@pytest.fixture
def dextools_campaign_config():
    """Create test DEXTools campaign configuration."""
    from ghoststorm.plugins.automation.dextools_campaign import CampaignConfig

    return CampaignConfig(
        pair_url="https://www.dextools.io/app/en/ether/pair-explorer/0xtest",
        num_visitors=10,  # Small for tests
        duration_hours=0.1,  # Very short for tests
        max_concurrent=2,
        distribution_mode="even",
        behavior_mode="realistic",
        dwell_time_min=1.0,
        dwell_time_max=3.0,
    )


# ============================================================================
# PYTEST FIXTURES - BEHAVIOR COMPONENTS
# ============================================================================


@pytest.fixture
def coherence_engine():
    """Create a test coherence engine with deterministic settings."""
    from ghoststorm.plugins.behavior.coherence_engine import (
        CoherenceConfig,
        CoherenceEngine,
    )

    config = CoherenceConfig(
        circadian_enabled=False,
        fatigue_enabled=False,
    )
    return CoherenceEngine(config)


@pytest.fixture
def session_state(coherence_engine):
    """Create a test session state."""
    from ghoststorm.plugins.behavior.coherence_engine import UserPersona

    return coherence_engine.create_session(persona=UserPersona.CASUAL)


# ============================================================================
# PYTEST FIXTURES - VIEW TRACKING
# ============================================================================


@pytest.fixture
def view_tracker():
    """Create a fresh view tracking manager."""
    from ghoststorm.plugins.automation.view_tracking import (
        ViewTrackingManager,
        reset_view_tracker,
    )

    reset_view_tracker()
    return ViewTrackingManager()


# ============================================================================
# PYTEST FIXTURES - EVENT BUS
# ============================================================================


@pytest.fixture
async def event_bus():
    """Create and start an event bus for testing."""
    from ghoststorm.core.events.bus import AsyncEventBus

    bus = AsyncEventBus()
    await bus.start()
    yield bus
    await bus.stop()


# ============================================================================
# PYTEST FIXTURES - API
# ============================================================================


@pytest.fixture
def test_client():
    """Create a test client for the API."""
    from fastapi.testclient import TestClient

    from ghoststorm.api.app import create_app

    app = create_app(orchestrator=None)
    return TestClient(app)


# ============================================================================
# PYTEST FIXTURES - HELPERS
# ============================================================================


@pytest.fixture
def mock_rate_limiter():
    """Create a mock rate limiter that always allows."""
    limiter = MagicMock()
    limiter.acquire = AsyncMock(return_value=True)
    limiter.can_proceed = MagicMock(return_value=True)
    return limiter


@pytest.fixture
def deterministic_random():
    """Make random deterministic for testing."""
    random.seed(42)
    yield random
    # Reset after test
    random.seed()


@pytest.fixture
def mock_sleep(monkeypatch):
    """Mock asyncio.sleep to speed up tests."""
    mock = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", mock)
    return mock
