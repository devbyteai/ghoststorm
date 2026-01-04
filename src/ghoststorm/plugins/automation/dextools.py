"""DEXTools automation plugin.

Provides automation for DEXTools pair explorer interactions with
realistic human-like behavior patterns for trending campaigns.
"""

from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class DEXToolsAction(Enum):
    """Available DEXTools automation actions."""

    CLICK_SOCIAL_TWITTER = "social_twitter"
    CLICK_SOCIAL_TELEGRAM = "social_telegram"
    CLICK_SOCIAL_WEBSITE = "social_website"
    CLICK_SOCIAL_DISCORD = "social_discord"
    CLICK_CHART_TAB = "chart_tab"
    CLICK_AGGREGATOR = "aggregator"
    CLICK_INFO_MODAL = "info_modal"
    SCROLL_PAGE = "scroll"
    REFRESH_PAGE = "refresh"
    HOVER_CHART = "hover_chart"
    MOUSE_IDLE = "mouse_idle"


class VisitorBehavior(Enum):
    """Behavior patterns for realistic visitor simulation.

    PASSIVE: 60% of real users - just view and leave
    LIGHT: 30% of real users - view + 1 interaction
    ENGAGED: 10% of real users - multiple interactions
    """

    PASSIVE = "passive"
    LIGHT = "light"
    ENGAGED = "engaged"


# Behavior distribution weights (should sum to 100)
BEHAVIOR_WEIGHTS = {
    VisitorBehavior.PASSIVE: 60,
    VisitorBehavior.LIGHT: 30,
    VisitorBehavior.ENGAGED: 10,
}


@dataclass
class DEXToolsSelectors:
    """Selectors for DEXTools UI elements.

    Includes both XPath and CSS selectors for flexibility.
    Update these when DEXTools changes their UI.

    To find updated selectors:
    1. Open DEXTools pair page in browser
    2. Right-click element → Inspect
    3. Copy selector or XPath
    """

    # Social links - CSS selectors (more stable than XPath)
    social_links_container: str = "div.pair-header a[target='_blank']"
    social_link_twitter: str = "a[href*='twitter.com'], a[href*='x.com']"
    social_link_telegram: str = "a[href*='t.me'], a[href*='telegram']"
    social_link_discord: str = "a[href*='discord']"
    social_link_website: str = "a[href]:not([href*='twitter']):not([href*='t.me']):not([href*='discord'])"

    # XPath fallbacks for social links
    social_link_1_xpath: str = "//div[contains(@class,'pair')]//a[@target='_blank'][1]"
    social_link_2_xpath: str = "//div[contains(@class,'pair')]//a[@target='_blank'][2]"
    social_link_3_xpath: str = "//div[contains(@class,'pair')]//a[@target='_blank'][3]"
    social_link_4_xpath: str = "//div[contains(@class,'pair')]//a[@target='_blank'][4]"

    # Chart area
    chart_container: str = "div.chart-container, div[class*='chart'], canvas"
    chart_tabs: str = "ul.nav-tabs li, div[role='tablist'] button"

    # Tab buttons - try multiple selectors
    tab_buttons: str = "button[role='tab'], .nav-tabs button, ul li button"
    info_button: str = "button[aria-label*='info'], span[class*='info']"

    # Modal elements
    modal_container: str = "div[role='dialog'], .modal, ngb-modal-window"
    modal_close: str = "button[aria-label='Close'], .modal-close, button.close"

    # Search
    search_input: str = "input[placeholder*='Search'], input[type='search']"
    search_results: str = "div[class*='search-result'], div[class*='dropdown'] a"

    # Favorite/star button
    favorite_button: str = "button[aria-label*='favorite'], button[class*='star']"


@dataclass
class DEXToolsConfig:
    """Configuration for DEXTools automation."""

    # Target pair URL
    pair_url: str = ""

    # === Campaign Settings ===
    mode: Literal["single", "campaign"] = "single"
    num_visitors: int = 100
    duration_hours: float = 24.0

    # === Behavior Settings ===
    behavior_mode: Literal["realistic", "passive", "light", "engaged", "custom"] = "realistic"

    # Dwell time (time spent on page)
    dwell_time_min: float = 30.0
    dwell_time_max: float = 120.0

    # === Action Settings ===
    enable_natural_scroll: bool = True
    enable_chart_hover: bool = True
    enable_mouse_movement: bool = True
    enable_social_clicks: bool = True
    enable_tab_clicks: bool = False
    enable_favorite: bool = False

    # === Timing ===
    min_delay: float = 2.0
    max_delay: float = 6.0
    initial_load_delay: tuple[float, float] = (5.0, 10.0)

    # === Legacy settings (backward compatibility) ===
    click_social_links: bool = True
    click_chart_tabs: bool = False
    scroll_page: bool = True
    refresh_at_end: bool = False
    social_links_count: int = 4


@dataclass
class VisitResult:
    """Result of a single visit."""

    success: bool
    url: str
    behavior: VisitorBehavior
    dwell_time_s: float
    actions_performed: list[str] = field(default_factory=list)
    social_clicks: int = 0
    tab_clicks: int = 0
    errors: list[str] = field(default_factory=list)


class DEXToolsAutomation:
    """Automation plugin for DEXTools pair explorer.

    Provides realistic human-like behavior patterns for visiting
    DEXTools pair pages, including natural mouse movement,
    scrolling, and varied engagement levels.

    Usage:
        ```python
        config = DEXToolsConfig(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0x...",
            behavior_mode="realistic",
            dwell_time_min=30.0,
            dwell_time_max=120.0,
        )
        automation = DEXToolsAutomation(config)

        async with browser.new_context() as context:
            page = await context.new_page()
            result = await automation.run_natural_visit(page)
        ```
    """

    name = "dextools"

    def __init__(
        self,
        config: DEXToolsConfig | None = None,
        selectors: DEXToolsSelectors | None = None,
    ) -> None:
        self.config = config or DEXToolsConfig()
        self.selectors = selectors or DEXToolsSelectors()

    # =========================================================================
    # Behavior Selection
    # =========================================================================

    def _pick_behavior(self) -> VisitorBehavior:
        """Pick a random behavior based on realistic distribution."""
        if self.config.behavior_mode == "realistic":
            behaviors = list(BEHAVIOR_WEIGHTS.keys())
            weights = list(BEHAVIOR_WEIGHTS.values())
            return random.choices(behaviors, weights=weights)[0]
        elif self.config.behavior_mode == "passive":
            return VisitorBehavior.PASSIVE
        elif self.config.behavior_mode == "light":
            return VisitorBehavior.LIGHT
        elif self.config.behavior_mode == "engaged":
            return VisitorBehavior.ENGAGED
        else:
            # Custom mode - use realistic
            return random.choices(
                list(BEHAVIOR_WEIGHTS.keys()),
                weights=list(BEHAVIOR_WEIGHTS.values())
            )[0]

    def _get_dwell_time(self, behavior: VisitorBehavior) -> tuple[float, float]:
        """Get dwell time range based on behavior type."""
        if behavior == VisitorBehavior.PASSIVE:
            return (15.0, 45.0)
        elif behavior == VisitorBehavior.LIGHT:
            return (30.0, 90.0)
        else:  # ENGAGED
            return (60.0, 180.0)

    # =========================================================================
    # Timing Helpers
    # =========================================================================

    async def _random_delay(
        self,
        min_s: float | None = None,
        max_s: float | None = None,
    ) -> None:
        """Wait for a random duration."""
        min_delay = min_s if min_s is not None else self.config.min_delay
        max_delay = max_s if max_s is not None else self.config.max_delay
        await asyncio.sleep(random.uniform(min_delay, max_delay))

    async def _micro_delay(self) -> None:
        """Very short delay for micro-interactions."""
        await asyncio.sleep(random.uniform(0.1, 0.5))

    # =========================================================================
    # Natural Mouse Movement
    # =========================================================================

    def _bezier_point(
        self,
        t: float,
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
    ) -> tuple[float, float]:
        """Calculate point on cubic bezier curve."""
        x = (
            (1 - t) ** 3 * p0[0]
            + 3 * (1 - t) ** 2 * t * p1[0]
            + 3 * (1 - t) * t ** 2 * p2[0]
            + t ** 3 * p3[0]
        )
        y = (
            (1 - t) ** 3 * p0[1]
            + 3 * (1 - t) ** 2 * t * p1[1]
            + 3 * (1 - t) * t ** 2 * p2[1]
            + t ** 3 * p3[1]
        )
        return (x, y)

    async def _move_mouse_naturally(
        self,
        page: Any,
        target_x: float,
        target_y: float,
        steps: int = 20,
    ) -> None:
        """Move mouse to target using bezier curve for natural movement."""
        try:
            # Get current position (estimate from viewport center if unknown)
            viewport = page.viewport_size or {"width": 1920, "height": 1080}
            start_x = random.uniform(0, viewport["width"])
            start_y = random.uniform(0, viewport["height"])

            # Generate control points for bezier curve
            ctrl1_x = start_x + random.uniform(-100, 100)
            ctrl1_y = start_y + random.uniform(-50, 50)
            ctrl2_x = target_x + random.uniform(-100, 100)
            ctrl2_y = target_y + random.uniform(-50, 50)

            p0 = (start_x, start_y)
            p1 = (ctrl1_x, ctrl1_y)
            p2 = (ctrl2_x, ctrl2_y)
            p3 = (target_x, target_y)

            # Move along curve
            for i in range(steps + 1):
                t = i / steps
                x, y = self._bezier_point(t, p0, p1, p2, p3)

                # Add slight tremor
                x += random.uniform(-2, 2)
                y += random.uniform(-2, 2)

                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.01, 0.03))

        except Exception:
            # Fallback to direct move
            await page.mouse.move(target_x, target_y)

    async def _mouse_idle_movement(self, page: Any, duration_s: float = 5.0) -> None:
        """Simulate idle mouse movement (small movements while reading)."""
        if not self.config.enable_mouse_movement:
            return

        try:
            viewport = page.viewport_size or {"width": 1920, "height": 1080}
            center_x = viewport["width"] / 2
            center_y = viewport["height"] / 2

            end_time = asyncio.get_event_loop().time() + duration_s

            while asyncio.get_event_loop().time() < end_time:
                # Small random movements around current area
                offset_x = random.uniform(-50, 50)
                offset_y = random.uniform(-30, 30)

                target_x = max(0, min(viewport["width"], center_x + offset_x))
                target_y = max(0, min(viewport["height"], center_y + offset_y))

                await page.mouse.move(target_x, target_y)
                await asyncio.sleep(random.uniform(0.5, 2.0))

                # Occasionally pause (simulating reading)
                if random.random() < 0.3:
                    await asyncio.sleep(random.uniform(1.0, 3.0))

        except Exception:
            pass

    # =========================================================================
    # Natural Scrolling
    # =========================================================================

    async def _natural_scroll(self, page: Any) -> None:
        """Perform natural scrolling behavior."""
        if not self.config.enable_natural_scroll:
            return

        try:
            viewport = page.viewport_size or {"width": 1920, "height": 1080}

            # Scroll down in chunks with varying speeds
            scroll_positions = [0.2, 0.4, 0.6, 0.8, 0.5, 0.3, 0.0]

            for target_pct in scroll_positions:
                # Calculate scroll amount
                target_y = int(viewport["height"] * 3 * target_pct)  # Assume page is 3x viewport

                # Scroll with momentum (multiple small scrolls)
                current = 0
                while abs(current - target_y) > 50:
                    step = min(100, abs(target_y - current)) * (1 if target_y > current else -1)
                    step += random.uniform(-20, 20)  # Add variance

                    await page.mouse.wheel(0, step)
                    current += step
                    await asyncio.sleep(random.uniform(0.05, 0.15))

                # Pause at each position (reading)
                await asyncio.sleep(random.uniform(1.0, 4.0))

                # Sometimes do micro mouse movement while reading
                if random.random() < 0.4:
                    await self._mouse_idle_movement(page, random.uniform(1.0, 3.0))

        except Exception:
            # Fallback to keyboard scroll
            try:
                await page.keyboard.press("End")
                await self._random_delay(2, 4)
                await page.keyboard.press("Home")
            except Exception:
                pass

    # =========================================================================
    # Chart Interaction
    # =========================================================================

    async def _hover_chart(self, page: Any) -> None:
        """Hover over chart area to simulate interest."""
        if not self.config.enable_chart_hover:
            return

        try:
            # Find chart element
            chart = page.locator(self.selectors.chart_container).first
            if await chart.is_visible(timeout=3000):
                box = await chart.bounding_box()
                if box:
                    # Move to random positions within chart
                    for _ in range(random.randint(2, 5)):
                        x = box["x"] + random.uniform(0.2, 0.8) * box["width"]
                        y = box["y"] + random.uniform(0.2, 0.8) * box["height"]

                        await self._move_mouse_naturally(page, x, y)
                        await asyncio.sleep(random.uniform(0.5, 2.0))
        except Exception:
            pass

    # =========================================================================
    # Click Actions
    # =========================================================================

    async def _safe_click(
        self,
        page: Any,
        selector: str,
        timeout: int = 5000,
    ) -> bool:
        """Safely click an element with natural mouse movement."""
        try:
            # Try CSS selector first
            element = page.locator(selector).first

            if await element.is_visible(timeout=timeout):
                box = await element.bounding_box()
                if box:
                    # Move naturally to element center (with slight offset)
                    target_x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
                    target_y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)

                    if self.config.enable_mouse_movement:
                        await self._move_mouse_naturally(page, target_x, target_y)

                    await self._micro_delay()
                    await element.click()
                    return True
            return False
        except Exception:
            return False

    async def _safe_click_xpath(self, page: Any, xpath: str) -> bool:
        """Click element by XPath (fallback)."""
        try:
            element = page.locator(f"xpath={xpath}").first
            await element.click(timeout=5000)
            return True
        except Exception:
            return False

    async def _click_random_social(self, page: Any, max_clicks: int = 1) -> int:
        """Click random social links."""
        if not self.config.enable_social_clicks:
            return 0

        clicked = 0
        social_selectors = [
            self.selectors.social_link_twitter,
            self.selectors.social_link_telegram,
            self.selectors.social_link_discord,
        ]

        # Shuffle and try to click
        random.shuffle(social_selectors)

        for selector in social_selectors[:max_clicks]:
            try:
                if await self._safe_click(page, selector):
                    clicked += 1
                    await self._random_delay(1, 3)

                    # Close any new tabs that opened
                    pages = page.context.pages
                    if len(pages) > 1:
                        await pages[-1].close()
                        await self._micro_delay()
            except Exception:
                continue

        return clicked

    async def _click_random_tab(self, page: Any) -> bool:
        """Click a random tab button."""
        if not self.config.enable_tab_clicks:
            return False

        try:
            tabs = page.locator(self.selectors.tab_buttons)
            count = await tabs.count()

            if count > 0:
                idx = random.randint(0, count - 1)
                await tabs.nth(idx).click()
                return True
        except Exception:
            pass
        return False

    # =========================================================================
    # Dwell (Time on Page)
    # =========================================================================

    async def _dwell(
        self,
        page: Any,
        min_s: float,
        max_s: float,
    ) -> float:
        """Dwell on page with micro-interactions."""
        dwell_time = random.uniform(min_s, max_s)
        elapsed = 0.0

        while elapsed < dwell_time:
            # Random micro-interaction
            action = random.choice(["idle", "scroll_small", "hover", "wait"])

            if action == "idle":
                duration = random.uniform(3.0, 8.0)
                await self._mouse_idle_movement(page, duration)
                elapsed += duration

            elif action == "scroll_small":
                try:
                    scroll_amount = random.uniform(-100, 100)
                    await page.mouse.wheel(0, scroll_amount)
                except Exception:
                    pass
                duration = random.uniform(1.0, 3.0)
                await asyncio.sleep(duration)
                elapsed += duration

            elif action == "hover":
                await self._hover_chart(page)
                elapsed += random.uniform(2.0, 5.0)

            else:  # wait
                duration = random.uniform(2.0, 6.0)
                await asyncio.sleep(duration)
                elapsed += duration

        return dwell_time

    # =========================================================================
    # Selector Health Check
    # =========================================================================

    async def test_selectors(self, page: Any, url: str) -> dict[str, Any]:
        """Test if selectors work on current DEXTools UI.

        Returns:
            Dictionary with test results for each selector type.
        """
        results = {
            "url": url,
            "page_loads": False,
            "chart_visible": False,
            "social_links_found": 0,
            "tabs_found": 0,
            "search_found": False,
            "errors": [],
            "status": "unknown",
        }

        try:
            await page.goto(url, timeout=30000)
            await asyncio.sleep(5)  # Wait for dynamic content
            results["page_loads"] = True

            # Test chart
            try:
                chart = page.locator(self.selectors.chart_container).first
                results["chart_visible"] = await chart.is_visible(timeout=3000)
            except Exception as e:
                results["errors"].append(f"Chart: {e}")

            # Test social links
            try:
                for selector in [
                    self.selectors.social_link_twitter,
                    self.selectors.social_link_telegram,
                    self.selectors.social_link_discord,
                ]:
                    el = page.locator(selector).first
                    if await el.is_visible(timeout=2000):
                        results["social_links_found"] += 1
            except Exception as e:
                results["errors"].append(f"Social: {e}")

            # Test tabs
            try:
                tabs = page.locator(self.selectors.tab_buttons)
                results["tabs_found"] = await tabs.count()
            except Exception as e:
                results["errors"].append(f"Tabs: {e}")

            # Test search
            try:
                search = page.locator(self.selectors.search_input).first
                results["search_found"] = await search.is_visible(timeout=2000)
            except Exception as e:
                results["errors"].append(f"Search: {e}")

            # Determine overall status
            if results["page_loads"] and results["chart_visible"]:
                if results["social_links_found"] >= 2:
                    results["status"] = "ready"
                else:
                    results["status"] = "partial"
            else:
                results["status"] = "broken"

        except Exception as e:
            results["errors"].append(f"Page load: {e}")
            results["status"] = "error"

        return results

    # =========================================================================
    # Main Visit Methods
    # =========================================================================

    async def run_natural_visit(
        self,
        page: Any,
        url: str | None = None,
    ) -> VisitResult:
        """Run a natural visit with realistic behavior.

        This is the main method for the trending campaign.
        """
        target_url = url or self.config.pair_url
        behavior = self._pick_behavior()
        dwell_range = self._get_dwell_time(behavior)

        result = VisitResult(
            success=False,
            url=target_url,
            behavior=behavior,
            dwell_time_s=0.0,
        )

        if not target_url:
            result.errors.append("No URL provided")
            return result

        try:
            # Navigate to page
            await page.goto(target_url)
            await self._random_delay(*self.config.initial_load_delay)
            result.actions_performed.append("page_load")

            # Always: Initial scroll and mouse movement
            await self._natural_scroll(page)
            result.actions_performed.append("scroll")

            # Behavior-specific actions
            if behavior == VisitorBehavior.PASSIVE:
                # Just view - hover chart briefly, dwell, leave
                await self._hover_chart(page)
                result.actions_performed.append("hover_chart")
                result.dwell_time_s = await self._dwell(page, *dwell_range)

            elif behavior == VisitorBehavior.LIGHT:
                # View + 1 interaction
                await self._hover_chart(page)
                result.actions_performed.append("hover_chart")

                # 50% chance social click, 50% chance tab click
                if random.random() < 0.5:
                    clicks = await self._click_random_social(page, max_clicks=1)
                    result.social_clicks = clicks
                    if clicks > 0:
                        result.actions_performed.append("social_click")
                else:
                    if await self._click_random_tab(page):
                        result.tab_clicks = 1
                        result.actions_performed.append("tab_click")

                result.dwell_time_s = await self._dwell(page, *dwell_range)

            else:  # ENGAGED
                # Multiple interactions
                await self._hover_chart(page)
                result.actions_performed.append("hover_chart")

                # Click 1-3 social links
                clicks = await self._click_random_social(page, max_clicks=random.randint(1, 3))
                result.social_clicks = clicks
                if clicks > 0:
                    result.actions_performed.append("social_clicks")

                # Click 1-2 tabs
                for _ in range(random.randint(1, 2)):
                    if await self._click_random_tab(page):
                        result.tab_clicks += 1
                        await self._random_delay(2, 5)

                if result.tab_clicks > 0:
                    result.actions_performed.append("tab_clicks")

                # More scrolling
                await self._natural_scroll(page)

                result.dwell_time_s = await self._dwell(page, *dwell_range)

            result.success = True

        except Exception as e:
            result.errors.append(str(e))

        return result

    async def run(
        self,
        page: Any,
        url: str | None = None,
    ) -> dict[str, Any]:
        """Run automation (legacy method for backward compatibility).

        For new code, use run_natural_visit() instead.
        """
        target_url = url or self.config.pair_url
        if not target_url:
            return {"success": False, "error": "No URL provided"}

        results = {
            "success": True,
            "url": target_url,
            "social_links_clicked": 0,
            "chart_tabs_clicked": 0,
            "errors": [],
        }

        try:
            await page.goto(target_url)
            await self._random_delay(*self.config.initial_load_delay)

            if self.config.scroll_page:
                await self._natural_scroll(page)

            if self.config.click_social_links:
                results["social_links_clicked"] = await self._click_random_social(
                    page, max_clicks=self.config.social_links_count
                )

            if self.config.click_chart_tabs:
                for _ in range(2):
                    if await self._click_random_tab(page):
                        results["chart_tabs_clicked"] += 1
                        await self._random_delay()

            if self.config.refresh_at_end:
                await page.reload()
                await self._random_delay()

        except Exception as e:
            results["success"] = False
            results["errors"].append(str(e))

        return results

    async def run_batch(
        self,
        page: Any,
        urls: list[str],
        delay_between: tuple[float, float] = (30.0, 60.0),
    ) -> list[dict[str, Any]]:
        """Run automation on multiple URLs (legacy method)."""
        results = []

        for url in urls:
            result = await self.run(page, url)
            results.append(result)

            if url != urls[-1]:
                await asyncio.sleep(random.uniform(*delay_between))

        return results
