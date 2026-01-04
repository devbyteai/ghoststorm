"""Fixtures for Playwright UI E2E tests."""

from __future__ import annotations

import asyncio
import subprocess
import time
from typing import AsyncGenerator, Generator

import pytest

# Check if playwright is available
try:
    from playwright.async_api import Browser, BrowserContext, Page, async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ============================================================================
# API SERVER FIXTURE
# ============================================================================


@pytest.fixture(scope="session")
def api_server() -> Generator[str, None, None]:
    """Start API server for UI tests.

    Returns the base URL of the running server.
    """
    import httpx

    base_url = "http://127.0.0.1:8765"

    # Start uvicorn in subprocess
    proc = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "ghoststorm.api.app:create_app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
            "--factory",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    max_wait = 30
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            response = httpx.get(f"{base_url}/health", timeout=2.0)
            if response.status_code == 200:
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("API server failed to start within 30 seconds")

    yield base_url

    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ============================================================================
# PLAYWRIGHT FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser() -> AsyncGenerator[Browser, None]:
    """Launch browser for UI tests."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not installed")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create fresh browser context for each test."""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext, api_server: str) -> AsyncGenerator[Page, None]:
    """Create fresh page for each test."""
    page = await context.new_page()
    page.set_default_timeout(10000)

    # Navigate to base URL
    await page.goto(api_server)
    await page.wait_for_load_state("networkidle")

    yield page

    await page.close()


# ============================================================================
# HELPER FIXTURES
# ============================================================================


@pytest.fixture
def base_url(api_server: str) -> str:
    """Get base URL for API requests from UI tests."""
    return api_server


@pytest.fixture
async def wait_for_websocket(page: Page):
    """Wait for WebSocket connection to be established."""

    async def _wait(timeout: int = 10000):
        await page.wait_for_function(
            """() => {
                const status = document.querySelector('#connection-status span:last-child');
                return status && status.textContent === 'Connected';
            }""",
            timeout=timeout,
        )

    return _wait


@pytest.fixture
async def wait_for_toast(page: Page):
    """Wait for toast notification to appear."""

    async def _wait(text: str | None = None, timeout: int = 5000):
        if text:
            await page.wait_for_selector(
                f".toast:has-text('{text}'), [role='alert']:has-text('{text}')",
                timeout=timeout,
            )
        else:
            await page.wait_for_selector(
                ".toast, [role='alert']",
                timeout=timeout,
            )

    return _wait


@pytest.fixture
async def close_modal(page: Page):
    """Close any open modal."""

    async def _close():
        # Try clicking close button
        close_btn = page.locator("button:has(svg path[d*='M6 18L18 6'])")
        if await close_btn.is_visible():
            await close_btn.click()
            return

        # Try pressing Escape
        await page.keyboard.press("Escape")

    return _close


# ============================================================================
# SCREENSHOT UTILITIES
# ============================================================================


@pytest.fixture
def screenshot_on_failure(page: Page, request: pytest.FixtureRequest):
    """Take screenshot on test failure."""
    yield

    # Check if test failed
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        # Take screenshot
        screenshot_path = f"test-results/screenshots/{request.node.name}.png"
        asyncio.get_event_loop().run_until_complete(
            page.screenshot(path=screenshot_path, full_page=True)
        )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test result for screenshot_on_failure fixture."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
