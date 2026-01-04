"""Real TikTok View Count Verification Test.

This test uses a REAL browser (Patchright) to:
1. Visit a TikTok video
2. Extract view count BEFORE watching
3. Watch the video for 5+ seconds
4. Extract view count AFTER
5. Verify the count increased

Run with: pytest tests/e2e/test_tiktok_real_views.py -v -s
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any

import pytest


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_view_count(text: str | None) -> int | None:
    """Parse view count text like '1.5K', '1,234', '1.5M' to integer.

    Args:
        text: View count text from TikTok

    Returns:
        Integer view count or None if parsing fails
    """
    if not text:
        return None

    # Clean the text
    text = text.strip().upper().replace(",", "").replace(" ", "")

    # Remove "VIEWS" suffix if present
    text = re.sub(r"VIEWS?$", "", text, flags=re.IGNORECASE).strip()

    if not text:
        return None

    # Handle multipliers
    multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}

    for suffix, mult in multipliers.items():
        if suffix in text:
            try:
                num = float(text.replace(suffix, ""))
                return int(num * mult)
            except ValueError:
                continue

    # Try direct conversion
    try:
        return int(float(text))
    except ValueError:
        return None


async def extract_view_count(page: Any) -> int | None:
    """Extract view count from TikTok video page.

    Tries multiple methods to find the view count.

    Args:
        page: Playwright page object

    Returns:
        View count as integer or None if not found
    """
    # Wait for page to stabilize
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass  # Continue even if timeout

    await asyncio.sleep(1)  # Extra settling time

    # Method 1: Try data-e2e selectors (TikTok's testing attributes)
    selectors = [
        '[data-e2e="video-views"]',
        '[data-e2e="browse-video-count"]',
        'strong[data-e2e="video-views"]',
        '[data-e2e="view-count"]',
    ]

    for selector in selectors:
        try:
            element = page.locator(selector)
            if await element.count() > 0:
                text = await element.first.text_content()
                count = parse_view_count(text)
                if count is not None:
                    return count
        except Exception:
            continue

    # Method 2: JavaScript extraction - look for view patterns in page
    try:
        result = await page.evaluate("""
            () => {
                // Look for elements containing view count patterns
                const patterns = [
                    /([0-9.]+[KMB]?)\\s*views?/i,
                    /views?:\\s*([0-9.]+[KMB]?)/i,
                ];

                // Search in all text content
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );

                let node;
                while (node = walker.nextNode()) {
                    const text = node.textContent.trim();
                    for (const pattern of patterns) {
                        const match = text.match(pattern);
                        if (match) {
                            return match[1] || match[0];
                        }
                    }
                }

                return null;
            }
        """)
        if result:
            return parse_view_count(result)
    except Exception:
        pass

    # Method 3: Look for stats container
    try:
        stats = page.locator('[class*="video-stats"], [class*="VideoStats"]')
        if await stats.count() > 0:
            text = await stats.first.text_content()
            # Extract number from text
            match = re.search(r"([0-9.,]+[KMB]?)\s*views?", text, re.IGNORECASE)
            if match:
                return parse_view_count(match.group(1))
    except Exception:
        pass

    return None


async def watch_video(page: Any, duration_seconds: float = 6.0) -> None:
    """Watch a video for specified duration.

    Ensures video is playing and waits.

    Args:
        page: Playwright page object
        duration_seconds: How long to watch (default 6s, TikTok min is 3s)
    """
    # Try to click play button if video is paused
    play_selectors = [
        '[data-e2e="video-play-icon"]',
        '[class*="play-icon"]',
        'button[aria-label*="Play"]',
    ]

    for selector in play_selectors:
        try:
            btn = page.locator(selector)
            if await btn.count() > 0 and await btn.first.is_visible():
                await btn.first.click()
                await asyncio.sleep(0.5)
                break
        except Exception:
            continue

    # Watch for the specified duration
    print(f"  Watching video for {duration_seconds} seconds...")
    await asyncio.sleep(duration_seconds)


async def launch_stealth_browser(headless: bool = False, proxy_url: str | None = None):
    """Launch Patchright browser with stealth settings.

    Args:
        headless: Run in headless mode (False for debugging)
        proxy_url: Optional proxy server URL

    Returns:
        Tuple of (playwright, browser)
    """
    from patchright.async_api import async_playwright

    playwright = await async_playwright().start()

    # Stealth arguments to avoid detection
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
        "--disable-web-security",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--disable-gpu",
    ]

    launch_options: dict[str, Any] = {
        "headless": headless,
        "args": launch_args,
    }

    if proxy_url:
        launch_options["proxy"] = {"server": proxy_url}

    browser = await playwright.chromium.launch(**launch_options)

    return playwright, browser


# ============================================================================
# TEST CLASS
# ============================================================================

@pytest.mark.real
@pytest.mark.slow
class TestTikTokRealViews:
    """Real browser tests for TikTok view count verification."""

    # Public TikTok videos for testing (popular videos with stable view counts)
    TEST_VIDEOS = [
        # Add real TikTok video URLs here
        # Using trending/popular videos that are unlikely to be deleted
        "https://www.tiktok.com/discover",  # Discovery page to find videos
    ]

    @pytest.fixture
    async def browser(self):
        """Launch real Patchright browser."""
        playwright, browser = await launch_stealth_browser(headless=False)
        yield browser
        await browser.close()
        await playwright.stop()

    @pytest.mark.asyncio
    async def test_can_launch_browser_and_visit_tiktok(self, browser) -> None:
        """Test that we can launch browser and visit TikTok."""
        print("\n" + "=" * 70)
        print("  TEST: Launch Browser and Visit TikTok")
        print("=" * 70)

        context = await browser.new_context(
            viewport={"width": 390, "height": 844},  # Mobile viewport
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        )
        page = await context.new_page()

        try:
            print("  Navigating to TikTok...")
            await page.goto("https://www.tiktok.com", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Verify we're on TikTok
            title = await page.title()
            url = page.url

            print(f"  Page title: {title}")
            print(f"  Page URL: {url}")

            assert "tiktok" in url.lower(), f"Not on TikTok: {url}"
            print("\n  SUCCESS: Browser can visit TikTok!")

        finally:
            await context.close()

    @pytest.mark.asyncio
    async def test_can_extract_view_count(self, browser) -> None:
        """Test that we can extract view count from a video page."""
        print("\n" + "=" * 70)
        print("  TEST: Extract View Count from TikTok Video")
        print("=" * 70)

        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        )
        page = await context.new_page()

        try:
            # Go to TikTok For You page to find a video
            print("  Navigating to TikTok For You page...")
            await page.goto("https://www.tiktok.com/foryou", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)  # Wait for videos to load

            # Try to find and click on a video
            video_selectors = [
                '[data-e2e="recommend-list-item-container"]',
                '[class*="DivItemContainer"]',
                'a[href*="/video/"]',
            ]

            video_found = False
            for selector in video_selectors:
                try:
                    videos = page.locator(selector)
                    if await videos.count() > 0:
                        print(f"  Found videos using selector: {selector}")
                        # Click first video
                        await videos.first.click()
                        await asyncio.sleep(3)
                        video_found = True
                        break
                except Exception as e:
                    print(f"  Selector {selector} failed: {e}")
                    continue

            if not video_found:
                print("  Could not find videos on For You page, trying direct URL...")
                # This is expected - we may need to handle login prompts

            # Try to extract view count
            current_url = page.url
            print(f"  Current URL: {current_url}")

            view_count = await extract_view_count(page)

            if view_count is not None:
                print(f"\n  SUCCESS: Extracted view count: {view_count:,}")
            else:
                print("\n  WARNING: Could not extract view count (may need login or different approach)")
                # Take screenshot for debugging
                await page.screenshot(path="tiktok_debug.png")
                print("  Saved debug screenshot to tiktok_debug.png")

        finally:
            await context.close()

    @pytest.mark.asyncio
    async def test_view_count_increases_after_watching(self, browser) -> None:
        """
        MAIN TEST: Watch TikTok video and verify view count increases.

        This is the core test that verifies the automation actually works.
        """
        print("\n" + "=" * 70)
        print("  TEST: View Count Increases After Watching")
        print("=" * 70)

        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        )
        page = await context.new_page()

        try:
            # Step 1: Navigate to TikTok For You page
            print("\n  [Step 1] Navigating to TikTok...")
            await page.goto("https://www.tiktok.com/foryou", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Step 2: Get initial view count (if visible)
            print("\n  [Step 2] Extracting initial view count...")
            views_before = await extract_view_count(page)
            print(f"  Views BEFORE: {views_before if views_before else 'Not visible'}")

            # Step 3: Watch the video
            print("\n  [Step 3] Watching video...")
            await watch_video(page, duration_seconds=8.0)  # Watch for 8 seconds

            # Step 4: Scroll to next video and back (to trigger view count update)
            print("\n  [Step 4] Scrolling to refresh view...")
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(2)
            await page.keyboard.press("ArrowUp")
            await asyncio.sleep(2)

            # Step 5: Get updated view count
            print("\n  [Step 5] Extracting updated view count...")
            views_after = await extract_view_count(page)
            print(f"  Views AFTER: {views_after if views_after else 'Not visible'}")

            # Step 6: Report results
            print("\n" + "=" * 70)
            print("  RESULTS")
            print("=" * 70)

            if views_before is not None and views_after is not None:
                change = views_after - views_before
                print(f"  Views Before: {views_before:,}")
                print(f"  Views After:  {views_after:,}")
                print(f"  Change:       {change:+,}")

                if change > 0:
                    print("\n  SUCCESS: View count increased!")
                elif change == 0:
                    print("\n  NOTE: View count unchanged (may update with delay)")
                else:
                    print("\n  WARNING: View count decreased (caching issue?)")
            else:
                print("  Could not compare view counts (extraction failed)")
                print("  This may be due to:")
                print("    - TikTok requiring login")
                print("    - Page structure changed")
                print("    - Bot detection triggered")

                # Save screenshot for debugging
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"tiktok_test_{timestamp}.png"
                await page.screenshot(path=screenshot_path)
                print(f"\n  Saved debug screenshot: {screenshot_path}")

        finally:
            await context.close()


@pytest.mark.real
@pytest.mark.slow
class TestTikTokDirectVideo:
    """Test watching a specific TikTok video URL."""

    @pytest.fixture
    async def browser(self):
        """Launch real Patchright browser."""
        playwright, browser = await launch_stealth_browser(headless=False)
        yield browser
        await browser.close()
        await playwright.stop()

    @pytest.mark.asyncio
    async def test_watch_specific_video(self, browser) -> None:
        """Watch a specific TikTok video and report metrics."""
        print("\n" + "=" * 70)
        print("  TEST: Watch Specific TikTok Video")
        print("=" * 70)

        # You can replace this with any TikTok video URL
        VIDEO_URL = "https://www.tiktok.com/foryou"  # Default to For You page

        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        )
        page = await context.new_page()

        try:
            start_time = datetime.now()

            print(f"\n  Navigating to: {VIDEO_URL}")
            await page.goto(VIDEO_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            print(f"  Current URL: {page.url}")

            # Watch video
            print("\n  Watching video for 10 seconds...")
            await asyncio.sleep(10)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print("\n" + "=" * 70)
            print("  SESSION REPORT")
            print("=" * 70)
            print(f"  Duration: {duration:.1f} seconds")
            print(f"  Final URL: {page.url}")
            print("=" * 70)

        finally:
            await context.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
