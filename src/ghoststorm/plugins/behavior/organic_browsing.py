"""Organic browsing behavior - link extraction and random crawling."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from ghoststorm.plugins.behavior.url_filter import URLFilter, URLFilterConfig


@dataclass
class OrganicBrowsingConfig:
    """Configuration for organic browsing behavior."""

    # Crawl depth
    max_depth: int = 5
    min_links_per_page: int = 1
    max_links_per_page: int = 3

    # Domain behavior
    same_domain_only: bool = True
    follow_external_probability: float = 0.1

    # URL filtering
    blacklist_patterns: list[str] = field(default_factory=list)
    whitelist_patterns: list[str] = field(default_factory=list)
    use_default_blacklist: bool = True

    # Timing
    dwell_time: tuple[float, float] = (5.0, 15.0)
    click_delay: tuple[float, float] = (0.5, 2.0)

    # Behavior
    scroll_before_click: bool = True
    scroll_probability: float = 0.8
    hover_before_click: bool = True
    hover_duration: tuple[float, float] = (0.3, 1.0)


@dataclass
class BrowseSessionResult:
    """Result of an organic browsing session."""

    start_url: str
    visited_urls: list[str] = field(default_factory=list)
    depth_reached: int = 0
    links_clicked: int = 0
    links_extracted: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    success: bool = True


class OrganicBrowsingBehavior:
    """Simulate organic browsing by following links naturally.

    This plugin extracts links from pages and randomly clicks through them,
    simulating how a real user would browse a website. It integrates with
    the URL filter for blacklist/whitelist support.

    Features:
    - Extract all valid links from a page
    - Filter links using blacklist patterns
    - Randomly select and click links
    - Configurable crawl depth
    - Natural dwell times between pages
    - Scroll and hover before clicking

    Usage:
        ```python
        config = OrganicBrowsingConfig(
            max_depth=5,
            same_domain_only=True,
            dwell_time=(5.0, 15.0),
        )
        behavior = OrganicBrowsingBehavior(config)

        result = await behavior.browse_session(page, "https://example.com")
        print(f"Visited {len(result.visited_urls)} pages")
        ```
    """

    name = "organic_browsing"

    def __init__(self, config: OrganicBrowsingConfig | None = None) -> None:
        """Initialize organic browsing behavior.

        Args:
            config: Browsing configuration
        """
        self.config = config or OrganicBrowsingConfig()

        # Initialize URL filter
        filter_config = URLFilterConfig(
            blacklist_patterns=self.config.blacklist_patterns,
            whitelist_patterns=self.config.whitelist_patterns,
            use_default_blacklist=self.config.use_default_blacklist,
            block_external=self.config.same_domain_only,
        )
        self._url_filter = URLFilter(filter_config)

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    async def extract_links(self, page: Any) -> list[str]:
        """Extract all valid links from the current page.

        Args:
            page: Browser page object

        Returns:
            List of absolute URLs
        """
        try:
            # Get current URL for resolving relative links
            current_url = page.url

            # Extract all href attributes
            links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(a => {
                        try {
                            // Get the full URL (handles relative links)
                            return a.href;
                        } catch {
                            return a.getAttribute('href');
                        }
                    }).filter(href => href && href.trim());
                }
            """)

            # Deduplicate and validate
            valid_links = []
            seen = set()

            for link in links:
                # Resolve relative URLs
                if not link.startswith(("http://", "https://")):
                    link = urljoin(current_url, link)

                # Skip duplicates
                if link in seen:
                    continue
                seen.add(link)

                # Basic validation
                parsed = urlparse(link)
                if parsed.scheme in ("http", "https") and parsed.netloc:
                    valid_links.append(link)

            return valid_links

        except Exception:
            return []

    async def filter_links(
        self,
        links: list[str],
        base_domain: str,
    ) -> list[str]:
        """Filter links using URL filter.

        Args:
            links: List of URLs to filter
            base_domain: Base domain for external link detection

        Returns:
            Filtered list of URLs
        """
        return self._url_filter.filter_urls(links, base_domain)

    def select_random_links(
        self,
        links: list[str],
        count: int | None = None,
    ) -> list[str]:
        """Randomly select links to follow.

        Args:
            links: List of candidate URLs
            count: Number of links to select (uses config if not provided)

        Returns:
            Selected URLs
        """
        if not links:
            return []

        if count is None:
            count = random.randint(
                self.config.min_links_per_page,
                min(self.config.max_links_per_page, len(links)),
            )

        count = min(count, len(links))
        return random.sample(links, count)

    async def click_link(
        self,
        page: Any,
        url: str,
    ) -> bool:
        """Click a link with human-like behavior.

        Args:
            page: Browser page object
            url: URL to navigate to

        Returns:
            True if click succeeded
        """
        try:
            # Find the link element
            link_element = await page.query_selector(f'a[href="{url}"]')

            if not link_element:
                # Try partial match
                link_element = await page.query_selector(f'a[href*="{urlparse(url).path}"]')

            if link_element:
                # Scroll into view
                if self.config.scroll_before_click:
                    await link_element.scroll_into_view_if_needed()
                    await asyncio.sleep(random.uniform(0.2, 0.5))

                # Hover before click
                if self.config.hover_before_click:
                    await link_element.hover()
                    await asyncio.sleep(random.uniform(*self.config.hover_duration))

                # Click
                await link_element.click()
                return True

            else:
                # Fallback: direct navigation
                await page.goto(url, wait_until="domcontentloaded")
                return True

        except Exception:
            # Last resort: direct navigation
            try:
                await page.goto(url, wait_until="domcontentloaded")
                return True
            except Exception:
                return False

    async def dwell_on_page(self, page: Any) -> None:
        """Simulate dwelling on a page (reading, scrolling).

        Args:
            page: Browser page object
        """
        dwell_time = random.uniform(*self.config.dwell_time)
        start = time.time()

        while time.time() - start < dwell_time:
            # Random scroll
            if random.random() < self.config.scroll_probability:
                scroll_amount = random.randint(100, 400)
                direction = random.choice([1, -1])
                try:
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount * direction})")
                except Exception:
                    pass

            # Wait a bit
            await asyncio.sleep(random.uniform(0.5, 2.0))

    async def browse_session(
        self,
        page: Any,
        start_url: str,
        config: OrganicBrowsingConfig | None = None,
    ) -> BrowseSessionResult:
        """Run a full organic browsing session.

        Args:
            page: Browser page object
            start_url: Starting URL
            config: Optional config override

        Returns:
            Session results with visited URLs and stats
        """
        cfg = config or self.config
        result = BrowseSessionResult(start_url=start_url)
        start_time = time.time()

        try:
            # Navigate to start URL
            await page.goto(start_url, wait_until="domcontentloaded")
            result.visited_urls.append(start_url)

            base_domain = self._get_domain(start_url)

            # Main browsing loop
            for depth in range(cfg.max_depth):
                result.depth_reached = depth + 1

                # Dwell on current page
                await self.dwell_on_page(page)

                # Extract links
                links = await self.extract_links(page)
                result.links_extracted += len(links)

                # Filter links
                filtered = await self.filter_links(links, base_domain)

                # Remove already visited
                unvisited = [l for l in filtered if l not in result.visited_urls]

                if not unvisited:
                    # No more links to follow
                    break

                # Select random link
                selected = self.select_random_links(unvisited, count=1)

                if not selected:
                    break

                next_url = selected[0]

                # Click delay
                await asyncio.sleep(random.uniform(*cfg.click_delay))

                # Click link
                if await self.click_link(page, next_url):
                    result.visited_urls.append(next_url)
                    result.links_clicked += 1

                    # Wait for page load
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                else:
                    result.errors.append(f"Failed to click: {next_url}")

        except Exception as e:
            result.success = False
            result.errors.append(str(e))

        result.duration_seconds = time.time() - start_time
        return result

    async def browse_multiple(
        self,
        page: Any,
        urls: list[str],
        *,
        delay_between: tuple[float, float] = (30.0, 60.0),
    ) -> list[BrowseSessionResult]:
        """Run browsing sessions for multiple starting URLs.

        Args:
            page: Browser page object
            urls: List of starting URLs
            delay_between: Delay between sessions

        Returns:
            List of session results
        """
        results = []

        for i, url in enumerate(urls):
            result = await self.browse_session(page, url)
            results.append(result)

            # Delay before next session
            if i < len(urls) - 1:
                await asyncio.sleep(random.uniform(*delay_between))

        return results

    async def quick_browse(
        self,
        page: Any,
        url: str,
        depth: int = 3,
    ) -> list[str]:
        """Quick browse session with minimal config.

        Args:
            page: Browser page object
            url: Starting URL
            depth: Number of pages to visit

        Returns:
            List of visited URLs
        """
        config = OrganicBrowsingConfig(
            max_depth=depth,
            dwell_time=(2.0, 5.0),
            scroll_probability=0.5,
        )
        result = await self.browse_session(page, url, config)
        return result.visited_urls
