"""DEXTools automation plugin.

Migrated from: dextools-bot (x11)/*.py
Provides automation for DEXTools pair explorer interactions.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any


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


@dataclass
class DEXToolsSelectors:
    """XPath and CSS selectors for DEXTools UI elements.

    These selectors target the pair explorer page UI.
    Note: XPaths may need updates if DEXTools changes their UI.
    """

    # Social links in pair explorer header
    social_link_1: str = "/html/body/app-root/div[2]/div/main/app-exchange/div/app-pairexplorer/app-layout/div/div/div[1]/div[1]/h3/div/div[1]/a[1]"
    social_link_2: str = "/html/body/app-root/div[2]/div/main/app-exchange/div/app-pairexplorer/app-layout/div/div/div[1]/div[1]/h3/div/div[1]/a[2]"
    social_link_3: str = "/html/body/app-root/div[2]/div/main/app-exchange/div/app-pairexplorer/app-layout/div/div/div[1]/div[1]/h3/div/div[1]/a[3]"
    social_link_4: str = "/html/body/app-root/div[2]/div/main/app-exchange/div/app-pairexplorer/app-layout/div/div/div[1]/div[1]/h3/div/div[1]/a[4]"

    # Chart and data tabs
    chart_tab_button: str = "/html/body/app-root/div[2]/div/main/app-exchange/div/app-pairexplorer/app-layout/div/div/div[2]/div[2]/ul/li[1]/span/button"
    aggregator_link: str = "/html/body/app-root/div[2]/div/main/app-exchange/div/app-pairexplorer/app-layout/div/div/div[2]/div[2]/div/app-aggregator/section/div/div/div/div/div/div/div/div[1]/div[1]/div/div/a"
    tab_button_3: str = "/html/body/app-root/div[2]/div/main/app-exchange/div/app-pairexplorer/app-layout/div/div/div[2]/div[2]/ul/li[1]/button[3]"
    info_button: str = "/html/body/app-root/div[2]/div/main/app-exchange/div/app-pairexplorer/app-layout/div/div/div[2]/div[2]/ul/li[11]/span/span"

    # Modal elements
    modal_confirm_button: str = "/html/body/reach-portal/div[3]/div/div/div/div/div[3]/button"
    modal_close_button: str = "/html/body/ngb-modal-window/div/div/app-more-info-modal/div[2]/button"

    # Search functionality
    search_input: str = "//input[@placeholder='Search']"
    search_result_first: str = "//div[contains(@class, 'search-result')][1]"


@dataclass
class DEXToolsConfig:
    """Configuration for DEXTools automation."""

    # Target pair URL (e.g., ether/pair-explorer/0x...)
    pair_url: str = ""

    # Delays between actions (seconds)
    min_delay: float = 3.0
    max_delay: float = 8.0

    # Page load delays
    initial_load_delay: tuple[float, float] = (8.0, 15.0)

    # Actions to perform
    click_social_links: bool = True
    click_chart_tabs: bool = True
    scroll_page: bool = True
    refresh_at_end: bool = True

    # Number of social links to click (1-4)
    social_links_count: int = 4


class DEXToolsAutomation:
    """Automation plugin for DEXTools pair explorer.

    Provides methods for automating interactions with DEXTools
    pair explorer pages, including clicking social links,
    chart tabs, and simulating user behavior.

    Usage:
        ```python
        automation = DEXToolsAutomation(config=DEXToolsConfig(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0x..."
        ))

        # With ghoststorm page
        async with browser.new_context() as context:
            page = await context.new_page()
            await automation.run(page)
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

    async def _random_delay(
        self,
        min_s: float | None = None,
        max_s: float | None = None,
    ) -> None:
        """Wait for a random duration."""
        min_delay = min_s if min_s is not None else self.config.min_delay
        max_delay = max_s if max_s is not None else self.config.max_delay
        await asyncio.sleep(random.uniform(min_delay, max_delay))

    async def _safe_click(self, page: Any, xpath: str) -> bool:
        """Safely click an element by XPath.

        Args:
            page: Browser page object
            xpath: XPath selector

        Returns:
            True if click succeeded, False otherwise
        """
        try:
            element = page.locator(f"xpath={xpath}")
            await element.click(timeout=5000)
            return True
        except Exception:
            return False

    async def _scroll_page(self, page: Any) -> None:
        """Simulate natural scrolling behavior."""
        try:
            # Scroll to bottom
            await page.keyboard.press("End")
            await self._random_delay(2, 4)

            # Scroll back to top
            await page.keyboard.press("Home")
            await self._random_delay(2, 4)
        except Exception:
            pass

    async def _handle_new_window(self, page: Any, action: callable) -> None:
        """Execute action and handle any new windows that open.

        Args:
            page: Browser page object
            action: Async callable to execute
        """
        try:
            await action()
            await self._random_delay()

            # Switch back to main window if new tab opened
            pages = page.context.pages
            if len(pages) > 1:
                # Close the new tab
                await pages[-1].close()

        except Exception:
            pass

    async def click_social_links(self, page: Any) -> int:
        """Click social links in the pair explorer.

        Args:
            page: Browser page object

        Returns:
            Number of links successfully clicked
        """
        clicked = 0
        social_selectors = [
            self.selectors.social_link_1,
            self.selectors.social_link_2,
            self.selectors.social_link_3,
            self.selectors.social_link_4,
        ]

        for i, selector in enumerate(social_selectors[:self.config.social_links_count]):
            if await self._safe_click(page, selector):
                clicked += 1
                await self._random_delay()

                # Handle new window that may have opened
                try:
                    pages = page.context.pages
                    if len(pages) > 1:
                        await pages[-1].close()
                except Exception:
                    pass

        return clicked

    async def click_chart_tabs(self, page: Any) -> int:
        """Click chart and data tabs.

        Args:
            page: Browser page object

        Returns:
            Number of tabs successfully clicked
        """
        clicked = 0

        # Chart tab button
        if await self._safe_click(page, self.selectors.chart_tab_button):
            clicked += 1
            await self._random_delay()

        # Aggregator link
        if await self._safe_click(page, self.selectors.aggregator_link):
            clicked += 1
            await self._random_delay()

        # Tab button 3
        if await self._safe_click(page, self.selectors.tab_button_3):
            clicked += 1
            await self._random_delay()

        # Info button
        if await self._safe_click(page, self.selectors.info_button):
            clicked += 1
            await self._random_delay()

            # Handle modal if it appears
            try:
                pages = page.context.pages
                if len(pages) > 1:
                    await self._safe_click(pages[-1], self.selectors.modal_confirm_button)
                    await self._random_delay()
                    await pages[-1].close()
            except Exception:
                pass

            # Close info modal
            await self._safe_click(page, self.selectors.modal_close_button)
            await self._random_delay()

        return clicked

    async def search_token(self, page: Any, token_symbol: str) -> bool:
        """Search for a token in the DEXTools search.

        Args:
            page: Browser page object
            token_symbol: Token symbol to search for

        Returns:
            True if search was successful
        """
        try:
            search_input = page.locator(f"xpath={self.selectors.search_input}")
            await search_input.fill(token_symbol)
            await self._random_delay(1, 2)

            # Click first result
            result = page.locator(f"xpath={self.selectors.search_result_first}")
            await result.click(timeout=5000)
            await self._random_delay()

            return True
        except Exception:
            return False

    async def run(
        self,
        page: Any,
        url: str | None = None,
    ) -> dict[str, Any]:
        """Run the full DEXTools automation sequence.

        Args:
            page: Browser page object
            url: Optional URL override (uses config.pair_url if not provided)

        Returns:
            Dictionary with automation results
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
            # Navigate to pair explorer
            await page.goto(target_url)
            await self._random_delay(*self.config.initial_load_delay)

            # Scroll the page
            if self.config.scroll_page:
                await self._scroll_page(page)

            # Click social links
            if self.config.click_social_links:
                results["social_links_clicked"] = await self.click_social_links(page)

            # Click chart tabs
            if self.config.click_chart_tabs:
                results["chart_tabs_clicked"] = await self.click_chart_tabs(page)

            # Refresh at end
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
        """Run automation on multiple URLs.

        Args:
            page: Browser page object
            urls: List of pair explorer URLs
            delay_between: Min/max delay between URLs

        Returns:
            List of results for each URL
        """
        results = []

        for url in urls:
            result = await self.run(page, url)
            results.append(result)

            # Delay before next URL
            if url != urls[-1]:
                await asyncio.sleep(random.uniform(*delay_between))

        return results
