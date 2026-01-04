"""Generic Automation Engine.

Reusable automation engine with:
- Smart state machine
- Blocker detection and removal
- Multiple fallback selectors
- OCR captcha solving
- Configurable for any site
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EngineConfig:
    """Configuration for automation engine."""

    # Target site
    url: str
    name: str = "Generic"

    # Goal detection - keywords that indicate success
    goal_keywords: list[str] = field(default_factory=list)

    # Element selectors (will try each until one works)
    selectors: dict[str, list[str]] = field(default_factory=dict)

    # Actions to perform (in order)
    actions: list[dict[str, Any]] = field(default_factory=list)

    # Browser settings
    headless: bool = True
    proxy: str | None = None

    # Captcha
    solve_captcha: bool = True
    captcha_selectors: dict[str, str] = field(default_factory=lambda: {
        "image": "img.img-thumbnail, img[src*='captcha'], canvas",
        "input": "#captchatoken, input[name='captcha'], input[placeholder*='captcha' i]",
        "submit": "button[type='submit'], .btn-primary, button:has-text('Submit')",
    })

    # Timeouts
    page_load_timeout: int = 30000
    action_timeout: int = 10000
    max_iterations: int = 30

    # Delays
    delay_min: float = 1.0
    delay_max: float = 3.0


@dataclass
class EngineResult:
    """Result from automation engine."""

    success: bool
    site: str
    states_visited: list[str] = field(default_factory=list)
    actions_completed: list[str] = field(default_factory=list)
    captchas_solved: int = 0
    error: str | None = None
    duration: float = 0.0
    screenshots: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


class AutomationEngine:
    """Generic automation engine for any site.

    Features:
    - State machine that analyzes page and takes actions
    - Blocker detection (ads, modals, overlays)
    - Multiple fallback selectors for elements
    - OCR captcha solving
    - Configurable via EngineConfig
    """

    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self._page: Any = None
        self._browser: Any = None
        self._playwright: Any = None
        self._captchas_solved = 0
        self._logs: list[str] = []
        self._screenshots: list[str] = []
        self._states_visited: list[str] = []
        self._actions_completed: list[str] = []

    def _log(self, message: str) -> None:
        """Add to internal log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._logs.append(f"[{timestamp}] {message}")
        logger.info(f"[ENGINE] {message}")

    async def run(self) -> EngineResult:
        """Run the automation."""
        start_time = datetime.now(UTC)
        self._log(f"Starting automation for {self.config.name} at {self.config.url}")

        try:
            await self._init_browser()
            self._log("Browser initialized")

            # Navigate to site
            await self._page.goto(self.config.url, timeout=self.config.page_load_timeout)
            await self._random_delay()
            self._log(f"Navigated to {self.config.url}")

            # Run state machine
            success = await self._run_state_machine()

            # Execute configured actions if we reached goal
            if success and self.config.actions:
                self._log("Executing configured actions...")
                for action in self.config.actions:
                    try:
                        await self._execute_action(action)
                        self._actions_completed.append(action.get("name", "unnamed"))
                    except Exception as e:
                        self._log(f"Action failed: {e}")

            duration = (datetime.now(UTC) - start_time).total_seconds()

            return EngineResult(
                success=success,
                site=self.config.name,
                states_visited=self._states_visited,
                actions_completed=self._actions_completed,
                captchas_solved=self._captchas_solved,
                duration=duration,
                screenshots=self._screenshots,
                logs=self._logs,
            )

        except Exception as e:
            self._log(f"Error: {e}")
            return EngineResult(
                success=False,
                site=self.config.name,
                states_visited=self._states_visited,
                actions_completed=self._actions_completed,
                captchas_solved=self._captchas_solved,
                error=str(e),
                duration=(datetime.now(UTC) - start_time).total_seconds(),
                screenshots=self._screenshots,
                logs=self._logs,
            )

        finally:
            await self._cleanup()

    async def _init_browser(self) -> None:
        """Initialize browser with stealth settings."""
        try:
            from patchright.async_api import async_playwright
        except ImportError:
            from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        launch_args = {
            "headless": self.config.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                # DNS leak prevention - route DNS through encrypted DoH (with bootstrap IPs)
                '--dns-over-https-templates={"servers":[{"template":"https://dns.google/dns-query{?dns}","endpoints":[{"ips":["8.8.8.8","8.8.4.4"]}]}]}',
                "--enable-features=DnsOverHttps",
                # IPv6 leak prevention - IPv6 can bypass proxy
                "--disable-ipv6",
            ],
        }

        if self.config.proxy:
            launch_args["proxy"] = {"server": self.config.proxy}

        self._browser = await self._playwright.chromium.launch(**launch_args)

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
        )

        self._page = await context.new_page()
        # Note: Patchright has built-in stealth, no init script needed

    async def _cleanup(self) -> None:
        """Clean up browser resources."""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass

    async def _run_state_machine(self) -> bool:
        """Run state machine until goal reached or max iterations."""
        for iteration in range(self.config.max_iterations):
            self._log(f"=== Iteration {iteration + 1}/{self.config.max_iterations} ===")

            # Hide blockers
            await self._hide_blockers()

            # Detect current state
            state = await self._detect_state()
            self._states_visited.append(state["type"])
            self._log(f"State: {state['type']} - {state.get('detail', '')}")

            # Take screenshot
            screenshot_path = f"/tmp/engine_{self.config.name}_{iteration}.png"
            try:
                await self._page.screenshot(path=screenshot_path)
                self._screenshots.append(screenshot_path)
            except Exception:
                pass

            # Check if goal reached
            if state["type"] == "GOAL":
                self._log("GOAL REACHED!")
                return True

            # Take action based on state
            if state["type"] == "CAPTCHA" and self.config.solve_captcha:
                await self._solve_captcha()
            elif state["type"] == "BLOCKED":
                await self._remove_blocker(state.get("blocker"))
            elif state["type"] == "CLICKABLE":
                await self._click_element(state.get("element"))
            else:
                # Unknown state, wait and retry
                await asyncio.sleep(2)

            await self._random_delay()

        self._log("Max iterations reached without reaching goal")
        return False

    async def _detect_state(self) -> dict:
        """Detect current page state."""
        try:
            page_text = await self._page.inner_text("body")
            page_text_lower = page_text.lower()
        except Exception:
            page_text_lower = ""

        # Check for GOAL - keywords that indicate success
        if self.config.goal_keywords:
            matches = sum(1 for kw in self.config.goal_keywords if kw.lower() in page_text_lower)
            if matches >= len(self.config.goal_keywords) // 2 + 1:  # Majority match
                return {"type": "GOAL", "detail": f"Found {matches} goal keywords"}

        # Check for CAPTCHA
        captcha_input = self.config.captcha_selectors.get("input", "")
        if captcha_input:
            try:
                el = self._page.locator(captcha_input).first
                if await el.count() and await el.is_visible():
                    return {"type": "CAPTCHA", "detail": "Captcha input visible"}
            except Exception:
                pass

        # Check for BLOCKERS
        blocker = await self._find_blocker()
        if blocker:
            return {"type": "BLOCKED", "detail": blocker["type"], "blocker": blocker}

        # Check for clickable elements from config
        for name, selectors in self.config.selectors.items():
            element = await self._find_element(selectors)
            if element:
                return {"type": "CLICKABLE", "detail": f"Found {name}", "element": element, "name": name}

        return {"type": "UNKNOWN", "detail": page_text_lower[:100]}

    async def _find_blocker(self) -> dict | None:
        """Find blocking elements (ads, modals, overlays)."""
        blocker_selectors = [
            ("iframe[id^='aswift']", "google_ad"),
            ("iframe[title*='Advertisement']", "ad_iframe"),
            (".fc-dialog", "funding_choices"),
            ("div[class*='modal'][style*='display: block']", "modal"),
            ("div[class*='overlay'][style*='display: block']", "overlay"),
            ("div[class*='popup']:not([style*='display: none'])", "popup"),
        ]

        for selector, blocker_type in blocker_selectors:
            try:
                el = self._page.locator(selector).first
                if await el.count() and await el.is_visible():
                    bbox = await el.bounding_box()
                    if bbox and bbox["width"] > 100 and bbox["height"] > 100:
                        return {"type": blocker_type, "selector": selector}
            except Exception:
                pass

        return None

    async def _hide_blockers(self) -> None:
        """Hide/remove blocking elements."""
        try:
            await self._page.evaluate("""
                () => {
                    // Hide ad iframes
                    document.querySelectorAll('iframe[id^="aswift"], iframe[title*="Advertisement"]').forEach(el => {
                        el.style.display = 'none';
                        el.style.pointerEvents = 'none';
                    });
                    // Hide funding choices
                    document.querySelectorAll('.fc-dialog, .fc-consent-root').forEach(el => {
                        el.style.display = 'none';
                    });
                    // Hide common overlays
                    document.querySelectorAll('[class*="overlay"], [class*="modal-backdrop"]').forEach(el => {
                        if (getComputedStyle(el).position === 'fixed') {
                            el.style.display = 'none';
                        }
                    });
                }
            """)
        except Exception:
            pass

        # Try clicking common close buttons
        close_selectors = [
            "button:has-text('Close')",
            "button:has-text('Accept')",
            "button:has-text('I agree')",
            ".close",
            "[aria-label='Close']",
        ]
        for sel in close_selectors:
            try:
                btn = self._page.locator(sel).first
                if await btn.count() and await btn.is_visible():
                    await btn.click(timeout=2000)
                    self._log(f"Clicked close button: {sel}")
                    await asyncio.sleep(0.5)
            except Exception:
                pass

    async def _remove_blocker(self, blocker: dict | None) -> None:
        """Remove a specific blocker."""
        if not blocker:
            return

        self._log(f"Removing blocker: {blocker['type']}")

        try:
            selector = blocker.get("selector", "")
            if selector:
                await self._page.evaluate(f"""
                    document.querySelectorAll('{selector}').forEach(el => {{
                        el.style.display = 'none';
                        el.remove();
                    }});
                """)
        except Exception as e:
            self._log(f"Failed to remove blocker: {e}")

    async def _find_element(self, selectors: list[str]) -> Any:
        """Find element using multiple fallback selectors."""
        for sel in selectors:
            try:
                locator = self._page.locator(sel)
                count = await locator.count()
                for i in range(count):
                    el = locator.nth(i)
                    if await el.is_visible():
                        return el
            except Exception:
                pass
        return None

    async def _click_element(self, element: Any) -> None:
        """Click an element with fallbacks."""
        if not element:
            return

        try:
            await element.click(force=True, timeout=self.config.action_timeout)
            self._log("Clicked element")
        except Exception as e:
            self._log(f"Click failed: {e}")
            # Try JS click fallback
            try:
                await element.evaluate("el => el.click()")
                self._log("JS click succeeded")
            except Exception:
                pass

    async def _solve_captcha(self) -> None:
        """Solve captcha using OCR."""
        self._log("Attempting to solve captcha...")

        try:
            from ghoststorm.plugins.captcha.zefoy_ocr import ZefoyOCRSolver
            solver = ZefoyOCRSolver()
        except ImportError:
            self._log("OCR solver not available")
            return

        # Get captcha image
        img_selector = self.config.captcha_selectors.get("image", "")
        try:
            img_el = await self._find_element([img_selector])
            if not img_el:
                self._log("Captcha image not found")
                return

            img_bytes = await img_el.screenshot()
            solution = solver.solve(img_bytes)

            if not solution:
                self._log("OCR failed to solve captcha")
                return

            self._log(f"OCR solution: {solution}")

            # Enter solution
            input_selector = self.config.captcha_selectors.get("input", "")
            input_el = await self._find_element([input_selector])
            if input_el:
                await input_el.fill(solution)
                self._captchas_solved += 1

                # Click submit
                submit_selector = self.config.captcha_selectors.get("submit", "")
                submit_el = await self._find_element([submit_selector])
                if submit_el:
                    await submit_el.click(force=True)
                    self._log("Submitted captcha")

        except Exception as e:
            self._log(f"Captcha solving error: {e}")

    async def _execute_action(self, action: dict) -> None:
        """Execute a configured action."""
        action_type = action.get("type", "")
        self._log(f"Executing action: {action.get('name', action_type)}")

        if action_type == "click":
            selectors = action.get("selectors", [])
            element = await self._find_element(selectors)
            if element:
                await self._click_element(element)
            else:
                raise Exception(f"Element not found: {selectors}")

        elif action_type == "fill":
            selectors = action.get("selectors", [])
            value = action.get("value", "")
            element = await self._find_element(selectors)
            if element:
                await element.fill(value)
            else:
                raise Exception(f"Input not found: {selectors}")

        elif action_type == "wait":
            seconds = action.get("seconds", 2)
            await asyncio.sleep(seconds)

        elif action_type == "screenshot":
            path = action.get("path", f"/tmp/engine_action_{len(self._screenshots)}.png")
            await self._page.screenshot(path=path)
            self._screenshots.append(path)

    async def _random_delay(self) -> None:
        """Random human-like delay."""
        import random
        delay = random.uniform(self.config.delay_min, self.config.delay_max)
        await asyncio.sleep(delay)
