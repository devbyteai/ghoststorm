"""Page Analyzer for Zefoy automation.

Scrapes and analyzes page state to make smart decisions:
- Detects current page state (ad wall, ad playing, captcha, services)
- Finds clickable elements dynamically
- Verifies actions completed successfully
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class PageState(Enum):
    """Detected page states."""

    UNKNOWN = "unknown"
    AD_WALL = "ad_wall"  # "View a short ad" button visible
    AD_PLAYING = "ad_playing"  # Ad video/content is playing
    AD_CLOSEABLE = "ad_closeable"  # Ad done, X/close button visible
    CAPTCHA = "captcha"  # Captcha input visible
    SERVICES = "services"  # Service buttons visible (success!)
    ERROR = "error"  # Error message visible


@dataclass
class PageElement:
    """A discovered page element."""

    selector: str
    text: str
    tag: str
    classes: str
    is_visible: bool
    is_button: bool
    is_input: bool
    is_close_button: bool
    bounding_box: dict | None = None


@dataclass
class PageAnalysis:
    """Results of page analysis."""

    state: PageState
    elements: list[PageElement] = field(default_factory=list)
    close_buttons: list[PageElement] = field(default_factory=list)
    action_buttons: list[PageElement] = field(default_factory=list)
    inputs: list[PageElement] = field(default_factory=list)
    captcha_image: bytes | None = None
    error_message: str | None = None
    screenshot: bytes | None = None


class PageAnalyzer:
    """Analyzes Zefoy page state by scraping DOM."""

    # Keywords that indicate close/dismiss buttons
    CLOSE_KEYWORDS = ["×", "✕", "✖", "x", "close", "dismiss", "skip", "cancel"]

    # Keywords that indicate ad-related elements
    AD_KEYWORDS = ["ad", "advertisement", "sponsor", "video", "watch"]

    def __init__(self, page):
        self._page = page

    async def analyze(self) -> PageAnalysis:
        """Scrape and analyze current page state."""
        logger.info("[ANALYZER] Scraping page...")

        # Take screenshot for reference
        try:
            screenshot = await self._page.screenshot()
        except Exception:
            screenshot = None

        # Scrape all interactive elements
        elements = await self._scrape_elements()

        # Categorize elements
        close_buttons = [e for e in elements if e.is_close_button]
        action_buttons = [e for e in elements if e.is_button and not e.is_close_button]
        inputs = [e for e in elements if e.is_input]

        # Detect page state
        state = await self._detect_state(elements)

        # Get captcha image if in captcha state
        captcha_image = None
        if state == PageState.CAPTCHA:
            captcha_image = await self._get_captcha_image()

        # Check for error messages
        error_message = await self._get_error_message()

        analysis = PageAnalysis(
            state=state,
            elements=elements,
            close_buttons=close_buttons,
            action_buttons=action_buttons,
            inputs=inputs,
            captcha_image=captcha_image,
            error_message=error_message,
            screenshot=screenshot,
        )

        logger.info(
            "[ANALYZER] Page state detected",
            state=state.value,
            close_buttons=len(close_buttons),
            action_buttons=len(action_buttons),
            inputs=len(inputs),
        )

        return analysis

    async def _scrape_elements(self) -> list[PageElement]:
        """Scrape all interactive elements from the page."""
        elements = []

        # Get all buttons, links, and inputs
        selectors = [
            ("button", "button"),
            ("a", "link"),
            ("input", "input"),
            ("[role='button']", "role-button"),
            (".close", "close-class"),
            ("[class*='close']", "close-partial"),
            ("[class*='btn']", "btn-class"),
        ]

        for selector, _element_type in selectors:
            try:
                locator = self._page.locator(selector)
                count = await locator.count()

                for i in range(min(count, 50)):  # Limit to 50 per type
                    try:
                        el = locator.nth(i)

                        # Check visibility
                        is_visible = await el.is_visible()
                        if not is_visible:
                            continue

                        # Get element properties
                        text = ""
                        with contextlib.suppress(Exception):
                            text = (await el.inner_text()).strip()[:100]

                        classes = await el.get_attribute("class") or ""
                        tag = await el.evaluate("el => el.tagName.toLowerCase()")

                        # Get bounding box
                        try:
                            bbox = await el.bounding_box()
                        except Exception:
                            bbox = None

                        # Determine element type
                        is_button = tag in ["button", "a"] or "btn" in classes.lower()
                        is_input = tag == "input"
                        is_close = self._is_close_button(text, classes)

                        # Build selector for this element
                        el_id = await el.get_attribute("id")
                        sel = f"#{el_id}" if el_id else f"{selector}:nth-of-type({i + 1})"

                        elements.append(
                            PageElement(
                                selector=sel,
                                text=text,
                                tag=tag,
                                classes=classes,
                                is_visible=is_visible,
                                is_button=is_button,
                                is_input=is_input,
                                is_close_button=is_close,
                                bounding_box=bbox,
                            )
                        )

                    except Exception:
                        continue

            except Exception as e:
                logger.debug(f"[ANALYZER] Error scraping {selector}: {e}")

        return elements

    def _is_close_button(self, text: str, classes: str) -> bool:
        """Check if element looks like a close button."""
        text_lower = text.lower()
        classes_lower = classes.lower()

        # Check text content
        for keyword in self.CLOSE_KEYWORDS:
            if keyword in text_lower:
                return True

        # Check classes
        if any(kw in classes_lower for kw in ["close", "dismiss", "skip"]):
            return True

        # Check for × character specifically
        if "×" in text or "✕" in text or "✖" in text:
            return True

        # Single character 'X' or 'x'
        return text.strip() in ["X", "x"]

    async def _detect_state(self, elements: list[PageElement]) -> PageState:
        """Detect current page state based on elements."""

        # Check for service buttons FIRST (success state - we're done!)
        try:
            service_btn = self._page.locator(
                "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button"
            )
            if await service_btn.count() and await service_btn.is_visible():
                return PageState.SERVICES
        except Exception:
            pass

        # Check for AD WALL - look for "View a short ad" text BEFORE captcha
        # This is critical - ad wall appears BEFORE captcha
        try:
            # Check page text for ad indicators
            page_text = await self._page.inner_text("body")
            page_text_lower = page_text.lower()
            if "view a short ad" in page_text_lower or "unlock more content" in page_text_lower:
                return PageState.AD_WALL
        except Exception:
            pass

        # Also check scraped buttons for ad text
        for el in elements:
            if el.is_button:
                text_lower = el.text.lower()
                if (
                    ("view" in text_lower and "ad" in text_lower)
                    or "unlock" in text_lower
                    or "watch" in text_lower
                ):
                    return PageState.AD_WALL

        # Check for captcha - must have VISIBLE captcha input, not hidden
        try:
            # Look for visible captcha input specifically
            captcha_input = self._page.locator(
                "input[type='text']:visible, input.form-control:visible"
            )
            captcha_form = self._page.locator("form:has(img)")
            if await captcha_input.count() and await captcha_form.count():
                return PageState.CAPTCHA
        except Exception:
            pass

        # Fallback captcha check - image near input
        try:
            captcha_img = self._page.locator("img[src*='captcha']")
            if await captcha_img.count() and await captcha_img.is_visible():
                return PageState.CAPTCHA
        except Exception:
            pass

        # Check for close buttons (ad might be done, need to close)
        close_buttons = [e for e in elements if e.is_close_button and e.is_visible]
        if close_buttons:
            return PageState.AD_CLOSEABLE

        # Check for video/iframe (ad playing)
        try:
            video = self._page.locator("video, iframe[src*='ad'], iframe[src*='video']")
            if await video.count():
                return PageState.AD_PLAYING
        except Exception:
            pass

        return PageState.UNKNOWN

    async def _get_captcha_image(self) -> bytes | None:
        """Get captcha image bytes."""
        try:
            captcha_img = self._page.locator("img.img-thumbnail, img[src*='captcha']").first
            if await captcha_img.count():
                return await captcha_img.screenshot()
        except Exception as e:
            logger.debug(f"[ANALYZER] Failed to get captcha image: {e}")
        return None

    async def _get_error_message(self) -> str | None:
        """Check for error messages on page."""
        error_selectors = [
            ".alert-danger",
            ".error",
            "[class*='error']",
            ".text-danger",
        ]

        for selector in error_selectors:
            try:
                el = self._page.locator(selector).first
                if await el.count() and await el.is_visible():
                    return await el.inner_text()
            except Exception:
                pass

        return None

    async def click_close_button(self) -> bool:
        """Find and click any close button on the page."""
        analysis = await self.analyze()

        if not analysis.close_buttons:
            logger.warning("[ANALYZER] No close buttons found")
            # Save debug screenshot
            if analysis.screenshot:
                try:
                    with open("/tmp/zefoy_no_close.png", "wb") as f:
                        f.write(analysis.screenshot)
                    logger.info("[ANALYZER] Saved debug screenshot to /tmp/zefoy_no_close.png")
                except Exception:
                    pass
            return False

        # Try clicking the first visible close button
        for close_btn in analysis.close_buttons:
            try:
                logger.info(
                    f"[ANALYZER] Clicking close button: text='{close_btn.text}' classes='{close_btn.classes}'"
                )

                # Try multiple selector strategies
                clicked = False

                # Strategy 1: Use the stored selector
                try:
                    btn = self._page.locator(close_btn.selector).first
                    if await btn.count() and await btn.is_visible():
                        await btn.click(timeout=3000)
                        clicked = True
                except Exception:
                    pass

                # Strategy 2: Use bounding box click
                if not clicked and close_btn.bounding_box:
                    try:
                        x = close_btn.bounding_box["x"] + close_btn.bounding_box["width"] / 2
                        y = close_btn.bounding_box["y"] + close_btn.bounding_box["height"] / 2
                        await self._page.mouse.click(x, y)
                        clicked = True
                        logger.info(f"[ANALYZER] Clicked at coordinates ({x}, {y})")
                    except Exception:
                        pass

                if clicked:
                    await asyncio.sleep(1)

                    # Verify the click worked
                    new_analysis = await self.analyze()
                    if new_analysis.state != analysis.state:
                        logger.info(
                            f"[ANALYZER] State changed: {analysis.state.value} -> {new_analysis.state.value}"
                        )
                        return True

            except Exception as e:
                logger.debug(f"[ANALYZER] Failed to click close button: {e}")
                continue

        return False

    async def wait_for_state(self, target_state: PageState, timeout: int = 60) -> bool:
        """Wait for page to reach a target state."""
        logger.info(f"[ANALYZER] Waiting for state: {target_state.value}")

        for i in range(timeout):
            analysis = await self.analyze()

            if analysis.state == target_state:
                logger.info(f"[ANALYZER] Reached target state: {target_state.value}")
                return True

            # If we find close buttons, try clicking them
            if analysis.state == PageState.AD_CLOSEABLE:
                logger.info("[ANALYZER] Found closeable ad, attempting to close...")
                if await self.click_close_button():
                    continue

            if i % 10 == 0:
                logger.info(f"[ANALYZER] Still waiting... current state: {analysis.state.value}")

            await asyncio.sleep(1)

        logger.warning(f"[ANALYZER] Timeout waiting for state: {target_state.value}")
        return False
