"""Zefoy TikTok Booster Automation.

Automates Zefoy.com to boost TikTok engagement:
- Followers, Hearts, Views, Shares, Favorites, Live Stream
- Uses Patchright/Playwright for browser automation
- OCR-based captcha solving (Tesseract)
- Proxy rotation support
"""

from __future__ import annotations

import asyncio
import builtins
import contextlib
import random
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

ZEFOY_URL = "https://zefoy.com"

# Service button XPath selectors (from reference implementation)
ZEFOY_SERVICES = {
    "followers": "/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button",
    "hearts": "/html/body/div[5]/div[1]/div[3]/div[2]/div[2]/div/button",
    "chearts": "/html/body/div[5]/div[1]/div[3]/div[2]/div[3]/div/button",
    "views": "/html/body/div[5]/div[1]/div[3]/div[2]/div[4]/div/button",
    "shares": "/html/body/div[5]/div[1]/div[3]/div[2]/div[5]/div/button",
    "favorites": "/html/body/div[5]/div[1]/div[3]/div[2]/div[6]/div/button",
}

# Div number mapping for each service's form container
SERVICE_DIV_MAP = {
    "followers": "2",
    "hearts": "3",
    "chearts": "4",
    "views": "5",
    "shares": "6",
    "favorites": "7",
}

# Captcha box XPath
CAPTCHA_BOX_XPATH = "/html/body/div[4]/div[2]/form/div/div"


@dataclass
class ZefoyConfig:
    """Configuration for Zefoy automation."""

    tiktok_url: str
    service: str
    headless: bool = True
    proxy: str | None = None

    # Timeouts
    page_load_timeout: int = 30000
    captcha_timeout: int = 60
    action_timeout: int = 10000

    # Delays
    human_delay_min: float = 1.0
    human_delay_max: float = 3.0

    # Retries
    max_captcha_retries: int = 5
    max_action_retries: int = 3


@dataclass
class ZefoyResult:
    """Result from Zefoy automation."""

    success: bool
    service: str
    captchas_solved: int = 0
    cooldown_seconds: int = 0
    error: str | None = None
    error_type: str | None = None  # proxy, captcha, service_offline, network, timeout, unknown
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ZefoyAutomation:
    """Zefoy.com automation for TikTok boosting.

    Workflow:
    1. Navigate to Zefoy.com
    2. Solve initial captcha
    3. Select service (Followers, Hearts, etc.)
    4. Submit TikTok URL
    5. Solve captcha if presented
    6. Click "Search" and "Send" buttons
    7. Wait for cooldown, repeat
    """

    def __init__(self, config: ZefoyConfig) -> None:
        self.config = config
        self._captchas_solved = 0
        self._page: Any = None
        self._browser: Any = None
        self._playwright: Any = None

    async def run(self) -> ZefoyResult:
        """Run the Zefoy automation sequence."""
        start_time = datetime.now(UTC)

        if self.config.service not in ZEFOY_SERVICES:
            return ZefoyResult(
                success=False,
                service=self.config.service,
                error=f"Invalid service: {self.config.service}",
            )

        service_xpath = ZEFOY_SERVICES[self.config.service]
        div_num = SERVICE_DIV_MAP.get(self.config.service, "2")

        try:
            await self._init_browser()

            logger.info(
                "[ZEFOY] Navigating to Zefoy",
                service=self.config.service,
                proxy=self.config.proxy[:30] + "..." if self.config.proxy else None,
            )

            await self._page.goto(ZEFOY_URL, timeout=self.config.page_load_timeout)
            await self._random_delay()

            # SMART STATE MACHINE: Handle ads, captcha, and reach services page
            logger.info("[ZEFOY] Starting smart navigation to services page...")
            reached_services = await self._reach_services_page()

            if not reached_services:
                return ZefoyResult(
                    success=False,
                    service=self.config.service,
                    captchas_solved=self._captchas_solved,
                    error="Failed to reach services page after multiple attempts",
                    error_type="navigation",
                )

            # Click service button - try multiple selectors
            logger.info("[ZEFOY] Selecting service", service=self.config.service)

            # Hide any blocking ads first
            await self._hide_ad_overlays()
            await asyncio.sleep(1)

            # Try multiple selectors for the service button
            service_btn = None
            service_selectors = [
                f"xpath={service_xpath}",  # Original XPath
                f"button:has-text('{self.config.service.title()}')",  # Text match
                f"#t-{self.config.service}-button",  # ID selector
                f"button[class*='{self.config.service}']",  # Class match
            ]

            for sel in service_selectors:
                try:
                    btn = self._page.locator(sel).first
                    if await btn.count() and await btn.is_visible():
                        service_btn = btn
                        logger.info(f"[ZEFOY] Found service button with: {sel}")
                        break
                except Exception:
                    pass

            if not service_btn:
                # Debug: log what buttons are on the page
                try:
                    all_btns = await self._page.locator("button").all()
                    logger.debug(f"[ZEFOY] Found {len(all_btns)} buttons on page")
                    for i, btn in enumerate(all_btns[:10]):
                        txt = await btn.inner_text()
                        logger.debug(f"[ZEFOY] Button {i}: '{txt[:30]}'")
                except Exception:
                    pass

                return ZefoyResult(
                    success=False,
                    service=self.config.service,
                    captchas_solved=self._captchas_solved,
                    error="Service button not found - Zefoy layout may have changed",
                    error_type="service_offline",
                )

            # Check if service is enabled
            is_enabled = await service_btn.is_enabled()
            if not is_enabled:
                return ZefoyResult(
                    success=False,
                    service=self.config.service,
                    captchas_solved=self._captchas_solved,
                    error=f"Service '{self.config.service}' is currently OFFLINE on Zefoy",
                    error_type="service_offline",
                )

            await service_btn.click(force=True)
            await self._random_delay()
            await self._hide_ad_overlays()

            # Wait for form to appear
            await asyncio.sleep(2)

            # Find URL input with multiple selectors
            logger.info("[ZEFOY] Entering TikTok URL")
            url_input = None
            url_selectors = [
                "input[type='search']",  # Zefoy uses type='search'
                "input[placeholder*='Video URL' i]",  # Exact placeholder match
                "input.form-control",  # Class match
                f"xpath=/html/body/div[4]/div[{div_num}]/div/form/div/input",
                f"xpath=/html/body/div[5]/div[{div_num}]/div/form/div/input",
                "input[placeholder*='tiktok' i]",
                "input[placeholder*='video' i]",
                "input[placeholder*='url' i]",
                "form input[type='text']",
                "form input[type='search']",
            ]
            for sel in url_selectors:
                try:
                    locator = self._page.locator(sel)
                    count = await locator.count()
                    for i in range(count):
                        inp = locator.nth(i)
                        if await inp.is_visible():
                            url_input = inp
                            logger.info(f"[ZEFOY] Found URL input with: {sel} (index {i})")
                            break
                    if url_input:
                        break
                except Exception:
                    pass

            if not url_input:
                # Debug: save screenshot and log all visible inputs
                try:
                    await self._page.screenshot(path="/tmp/zefoy_no_url_input.png")
                    logger.info("[ZEFOY] Debug screenshot saved to /tmp/zefoy_no_url_input.png")

                    all_inputs = await self._page.locator("input").all()
                    logger.info(f"[ZEFOY] Found {len(all_inputs)} input elements")
                    for i, inp in enumerate(all_inputs[:10]):
                        try:
                            is_visible = await inp.is_visible()
                            placeholder = await inp.get_attribute("placeholder") or ""
                            inp_type = await inp.get_attribute("type") or ""
                            inp_class = await inp.get_attribute("class") or ""
                            logger.info(
                                f"[ZEFOY] Input {i}: visible={is_visible}, type={inp_type}, placeholder={placeholder[:30]}, class={inp_class[:30]}"
                            )
                        except Exception:
                            pass

                    # Also check forms
                    forms = await self._page.locator("form").all()
                    logger.info(f"[ZEFOY] Found {len(forms)} forms on page")
                except Exception as e:
                    logger.debug(f"[ZEFOY] Debug failed: {e}")

                return ZefoyResult(
                    success=False,
                    service=self.config.service,
                    captchas_solved=self._captchas_solved,
                    error="URL input not found",
                    error_type="service_offline",
                )

            await url_input.fill(self.config.tiktok_url)
            await self._random_delay()

            # Find and click search button
            logger.info("[ZEFOY] Clicking search button")
            search_btn = None
            search_selectors = [
                f"xpath=/html/body/div[4]/div[{div_num}]/div/form/div/div/button",
                f"xpath=/html/body/div[5]/div[{div_num}]/div/form/div/div/button",
                "button:has-text('Search')",
                "button:has-text('search')",
                "form button[type='submit']",
                "form button",
            ]
            for sel in search_selectors:
                try:
                    btn = self._page.locator(sel).first
                    if await btn.count() and await btn.is_visible():
                        search_btn = btn
                        logger.info(f"[ZEFOY] Found search button with: {sel}")
                        break
                except Exception:
                    pass

            if search_btn:
                try:
                    await search_btn.click(force=True, timeout=5000)
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.warning(f"[ZEFOY] Search button click failed: {e}")

            # Hide ads after search
            await self._hide_ad_overlays()

            # XPaths for result elements
            send_btn_xpath = f"/html/body/div[5]/div[{div_num}]/div/div/div[1]/div/form/button"
            cooldown_xpath = f"/html/body/div[5]/div[{div_num}]/div/div/h4"

            # Check for cooldown or success
            cooldown_el = self._page.locator(f"xpath={cooldown_xpath}")
            cooldown_text = ""
            try:
                await cooldown_el.wait_for(timeout=5000)
                cooldown_text = await cooldown_el.text_content() or ""
            except Exception:
                pass

            # If cooldown message, parse and return
            if "wait" in cooldown_text.lower() or "second" in cooldown_text.lower():
                cooldown = self._parse_cooldown(cooldown_text)
                logger.info(f"[ZEFOY] Cooldown detected: {cooldown}s")
                return ZefoyResult(
                    success=True,  # Cooldown means it worked previously
                    service=self.config.service,
                    captchas_solved=self._captchas_solved,
                    cooldown_seconds=cooldown,
                    duration=(datetime.now(UTC) - start_time).total_seconds(),
                )

            # Click send button - try multiple selectors
            logger.info("[ZEFOY] Clicking send button")
            send_btn = None
            send_selectors = [
                f"xpath={send_btn_xpath}",
                "button:has-text('Send')",
                "button:has-text('send')",
                "button:has-text('Submit')",
                "button.btn-success",
                "button.btn-primary",
                "form button:visible",
            ]
            for sel in send_selectors:
                try:
                    locator = self._page.locator(sel)
                    count = await locator.count()
                    for i in range(count):
                        btn = locator.nth(i)
                        if await btn.is_visible():
                            send_btn = btn
                            logger.info(f"[ZEFOY] Found send button with: {sel} (index {i})")
                            break
                    if send_btn:
                        break
                except Exception:
                    pass

            if send_btn:
                try:
                    await send_btn.click(force=True, timeout=5000)
                    await asyncio.sleep(3)  # Wait for result to appear
                    await self._hide_ad_overlays()

                    # Debug: take screenshot and log page state
                    try:
                        await self._page.screenshot(path="/tmp/zefoy_after_send.png")
                        logger.info("[ZEFOY] Debug screenshot saved to /tmp/zefoy_after_send.png")

                        # Log any visible messages
                        page_text = await self._page.inner_text("body")
                        # Look for success/error/cooldown keywords
                        if "successfully" in page_text.lower():
                            logger.info("[ZEFOY] Found 'successfully' in page text")
                        if (
                            "wait" in page_text.lower()
                            or "second" in page_text.lower()
                            or "minute" in page_text.lower()
                        ):
                            logger.info("[ZEFOY] Found cooldown keywords in page text")
                        if "error" in page_text.lower() or "invalid" in page_text.lower():
                            logger.info("[ZEFOY] Found error keywords in page text")

                        # Log h4 elements (likely contains messages)
                        h4_els = await self._page.locator("h4").all()
                        for h4 in h4_els:
                            try:
                                if await h4.is_visible():
                                    txt = await h4.inner_text()
                                    if txt.strip():
                                        logger.info(f"[ZEFOY] Visible h4: '{txt.strip()[:50]}'")
                            except Exception:
                                pass
                    except Exception as e:
                        logger.debug(f"[ZEFOY] Debug after send failed: {e}")

                except Exception as e:
                    logger.warning(f"[ZEFOY] Send button click failed: {e}")
            else:
                # Debug: take screenshot and list visible buttons
                try:
                    await self._page.screenshot(path="/tmp/zefoy_no_send.png")
                    logger.info("[ZEFOY] Debug screenshot saved to /tmp/zefoy_no_send.png")
                    all_btns = await self._page.locator("button:visible").all()
                    logger.info(f"[ZEFOY] Visible buttons: {len(all_btns)}")
                    for i, btn in enumerate(all_btns[:10]):
                        try:
                            txt = await btn.inner_text()
                            logger.info(f"[ZEFOY] Button {i}: '{txt[:30]}'")
                        except Exception:
                            pass
                except Exception:
                    pass
                logger.warning("[ZEFOY] Send button not found")

            # Check success
            success = await self._check_success()
            cooldown = await self._get_cooldown_time(div_num)

            duration = (datetime.now(UTC) - start_time).total_seconds()

            logger.info(
                "[ZEFOY] Automation completed",
                service=self.config.service,
                success=success,
                captchas_solved=self._captchas_solved,
                cooldown_seconds=cooldown,
                duration_s=round(duration, 2),
            )

            return ZefoyResult(
                success=success,
                service=self.config.service,
                captchas_solved=self._captchas_solved,
                cooldown_seconds=cooldown,
                duration=duration,
            )

        except Exception as e:
            error_str = str(e).lower()
            error_type = "unknown"
            error_msg = str(e)

            # Categorize the error
            if "timeout" in error_str or "timed out" in error_str:
                error_type = "timeout"
                error_msg = f"Page load timeout - check internet/proxy connection: {e}"
            elif "proxy" in error_str or "tunnel" in error_str or "connect" in error_str:
                error_type = "proxy"
                error_msg = f"Proxy connection failed: {e}"
            elif "net::" in error_str or "network" in error_str or "err_" in error_str:
                error_type = "network"
                error_msg = f"Network error: {e}"
            elif "captcha" in error_str:
                error_type = "captcha"
                error_msg = f"Captcha error: {e}"

            logger.error("[ZEFOY] Automation failed", error=error_msg, error_type=error_type)
            return ZefoyResult(
                success=False,
                service=self.config.service,
                captchas_solved=self._captchas_solved,
                error=error_msg,
                error_type=error_type,
            )

        finally:
            await self._cleanup()

    async def _init_browser(self) -> None:
        """Initialize Patchright/Playwright browser."""
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
                "--single-process",
            ],
        }

        if self.config.proxy:
            launch_args["proxy"] = {"server": self.config.proxy}

        self._browser = await self._playwright.chromium.launch(**launch_args)

        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        self._page = await context.new_page()

    async def _cleanup(self) -> None:
        """Clean up browser resources."""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass

    async def _reach_services_page(self) -> bool:
        """Smart state machine - keep analyzing page and taking actions until we reach services.

        TOOLKIT:
        - hide_ads: Remove ad overlays blocking interaction
        - close_modals: Close Bootstrap modals
        - click_ad_button: Click "View a short ad" to start ad
        - wait_and_close_ad: Wait for ad X button and close it
        - solve_captcha: OCR solve captcha
        - detect_state: Analyze what page we're on

        GOAL: Reach the services page (Followers, Hearts, Views buttons visible)
        """
        from ghoststorm.plugins.captcha.zefoy_ocr import ZefoyOCRSolver

        MAX_ITERATIONS = 30  # Max attempts to reach goal
        solver = ZefoyOCRSolver()

        for iteration in range(MAX_ITERATIONS):
            logger.info(f"[ZEFOY] === Iteration {iteration + 1}/{MAX_ITERATIONS} ===")

            # STEP 1: Always clean up first
            await self._hide_ad_overlays()
            await self._close_modals()
            await asyncio.sleep(0.5)

            # STEP 2: Analyze current page state
            state = await self._detect_page_state()
            logger.info(f"[ZEFOY] Current state: {state['type']}")

            # STEP 3: Take action based on state
            if state["type"] == "SERVICES":
                logger.info("[ZEFOY] 🎯 GOAL REACHED - Services page!")
                return True

            elif state["type"] == "BLOCKED":
                # Something is blocking us - REMOVE IT
                logger.info(f"[ZEFOY] 🚧 BLOCKED by: {state['detail']} - Removing...")
                await self._remove_blocker(state.get("blocker", {}))
                await asyncio.sleep(1)

            elif state["type"] == "AD_WALL":
                # Need to click "View a short ad"
                logger.info("[ZEFOY] 📺 Action: Clicking ad button...")
                await self._toolkit_click_ad_button()

            elif state["type"] == "AD_PLAYING":
                # Wait for ad to finish, look for X
                logger.info("[ZEFOY] ⏳ Action: Waiting for ad to finish...")
                await self._toolkit_wait_for_ad_close()

            elif state["type"] == "CAPTCHA":
                # Solve the captcha
                logger.info("[ZEFOY] 🔐 Action: Solving captcha...")
                solved = await self._toolkit_solve_captcha(solver)
                if solved:
                    self._captchas_solved += 1

            elif state["type"] == "LOADING":
                # Just wait
                logger.info("[ZEFOY] ⏳ Action: Waiting for page load...")
                await asyncio.sleep(2)

            elif state["type"] == "UNKNOWN":
                # Try generic cleanup and wait
                logger.warning(f"[ZEFOY] ❓ Unknown state: {state['detail']}")
                await self._hide_ad_overlays()
                await self._close_modals()
                await asyncio.sleep(2)

            # Small delay between iterations
            await asyncio.sleep(1)

        logger.error("[ZEFOY] Failed to reach services page after max iterations")
        return False

    async def _detect_page_state(self) -> dict:
        """SMART page state detection - check what we can ACTUALLY interact with."""
        try:
            page_text = await self._page.inner_text("body")
            page_text_lower = page_text.lower()

            # GOAL CHECK: Are we on services page?
            # Look for multiple service keywords - if we see these, we're on the main page
            service_keywords = [
                "followers",
                "hearts",
                "views",
                "shares",
                "favorites",
                "comments hearts",
                "live stream",
            ]
            matches = sum(1 for s in service_keywords if s in page_text_lower)
            if matches >= 2:  # At least 2 service names visible = we're on services page
                logger.debug(f"[ZEFOY] Found {matches} service keywords on page")
                # Even if buttons aren't directly clickable yet, we've reached the goal
                return {"type": "SERVICES", "detail": f"Services page ({matches} services visible)"}

            # Check what's BLOCKING us (if anything)
            blocker = await self._find_blocker()
            if blocker:
                return {"type": "BLOCKED", "detail": blocker["type"], "blocker": blocker}

            # Check for AD_WALL
            if "view a short ad" in page_text_lower or "unlock more content" in page_text_lower:
                ad_btn = self._page.locator("button, a").filter(has_text="View a short ad").first
                if await ad_btn.count() and await ad_btn.is_visible():
                    return {"type": "AD_WALL", "detail": "Ad button visible"}

            # Check for CAPTCHA (only if we can interact with it)
            captcha_input = self._page.locator("#captchatoken")
            captcha_img = self._page.locator("img.img-thumbnail")
            if await captcha_input.count() and await captcha_img.count():
                if await captcha_input.is_visible() and await captcha_img.is_visible():
                    # Verify we can actually interact
                    try:
                        await captcha_input.click(
                            timeout=2000, trial=True
                        )  # trial=True just checks
                        return {"type": "CAPTCHA", "detail": "Captcha interactable"}
                    except Exception:
                        # Something blocking - find and report it
                        blocker = await self._find_blocker()
                        if blocker:
                            return {
                                "type": "BLOCKED",
                                "detail": blocker["type"],
                                "blocker": blocker,
                            }

            # Check for LOADING
            if "loading" in page_text_lower and len(page_text) < 500:
                return {"type": "LOADING", "detail": "Page loading"}

            return {"type": "UNKNOWN", "detail": f"Text: {page_text[:150]}"}

        except Exception as e:
            return {"type": "UNKNOWN", "detail": f"Error: {e}"}

    async def _find_blocker(self) -> dict | None:
        """Find what's ACTUALLY blocking interaction - only real blockers."""
        # Priority 1: Google Ad iframes (these are the main blockers)
        ad_selectors = [
            ("iframe[id^='aswift']", "google_ad"),
            ("iframe[title*='Advertisement']", "ad_iframe"),
            ("ins.adsbygoogle[data-ad-status='filled']", "adsense_filled"),
        ]
        for selector, blocker_type in ad_selectors:
            try:
                el = self._page.locator(selector)
                count = await el.count()
                if count:
                    for i in range(min(count, 5)):
                        item = el.nth(i)
                        if await item.is_visible():
                            bbox = await item.bounding_box()
                            # Only consider large visible ad iframes as blockers
                            if bbox and bbox["width"] > 200 and bbox["height"] > 200:
                                logger.debug(
                                    f"[ZEFOY] Found ad blocker: {selector} size={bbox['width']}x{bbox['height']}"
                                )
                                return {"type": blocker_type, "selector": selector, "bbox": bbox}
            except Exception:
                pass

        # Priority 2: Bootstrap modal that's actually shown
        try:
            modal = self._page.locator(".modal.show, .modal.in")
            if await modal.count() and await modal.first.is_visible():
                logger.debug("[ZEFOY] Found modal blocker")
                return {"type": "bootstrap_modal", "selector": ".modal.show"}
        except Exception:
            pass

        # Priority 3: Google funding choices dialog
        try:
            fc_dialog = self._page.locator(".fc-dialog, .fc-monetization-dialog")
            if await fc_dialog.count() and await fc_dialog.first.is_visible():
                logger.debug("[ZEFOY] Found funding choices dialog")
                return {"type": "fc_dialog", "selector": ".fc-dialog"}
        except Exception:
            pass

        # NOT a blocker if we can't find specific blocking elements
        return None

    async def _can_interact_with_services(self) -> bool:
        """Check if we can actually click on service buttons."""
        service_selectors = [
            "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button",
            "button:has-text('Followers')",
            "button:has-text('Views')",
            "button:has-text('Hearts')",
        ]
        for sel in service_selectors:
            try:
                btn = self._page.locator(sel).first
                if await btn.count() and await btn.is_visible():
                    # Try a trial click to see if it's blocked
                    await btn.click(timeout=1000, trial=True)
                    return True
            except Exception:
                pass
        return False

    async def _remove_blocker(self, blocker: dict) -> bool:
        """Remove a detected blocker."""
        logger.info(f"[ZEFOY] Removing blocker: {blocker['type']}")

        # Strategy 1: Hide via JavaScript
        await self._hide_ad_overlays()

        # Strategy 2: If it's a modal, try to close it
        if "modal" in blocker["type"]:
            await self._close_modals()

        # Strategy 3: Click close button if visible
        close_selectors = [
            "button.close",
            ".btn-close",
            "[aria-label='Close']",
            "button:has-text('×')",
            "button:has-text('X')",
            "button:has-text('Close')",
        ]
        for sel in close_selectors:
            try:
                btn = self._page.locator(sel).first
                if await btn.count() and await btn.is_visible():
                    await btn.click(force=True, timeout=2000)
                    await asyncio.sleep(1)
                    logger.info(f"[ZEFOY] Clicked close button: {sel}")
                    return True
            except Exception:
                pass

        # Strategy 4: For ad iframes - wait for countdown and click X
        if "ad" in blocker["type"]:
            # Try clicking top-right corner (common X location)
            try:
                viewport = self._page.viewport_size
                if viewport:
                    for x_offset in [30, 50, 20]:
                        await self._page.mouse.click(viewport["width"] - x_offset, x_offset)
                        await asyncio.sleep(0.5)
            except Exception:
                pass

        return False

    async def _toolkit_click_ad_button(self) -> bool:
        """Toolkit: Click the 'View a short ad' button."""
        try:
            ad_btn = self._page.locator("button, a").filter(has_text="View a short ad").first
            if await ad_btn.count():
                await ad_btn.click(timeout=5000)
                await asyncio.sleep(2)
                return True
        except Exception as e:
            logger.debug(f"[ZEFOY] Click ad button failed: {e}")
        return False

    async def _toolkit_wait_for_ad_close(self) -> bool:
        """Toolkit: Wait for ad to finish and close it."""
        for wait_sec in range(35):  # Wait up to 35 seconds
            await asyncio.sleep(1)

            # Hide ads
            await self._hide_ad_overlays()

            # Check if captcha appeared (ad done)
            captcha_input = self._page.locator("#captchatoken")
            if await captcha_input.count() and await captcha_input.is_visible():
                logger.info("[ZEFOY] Captcha appeared - ad complete!")
                return True

            # Check if services appeared
            page_text = await self._page.inner_text("body")
            if "followers" in page_text.lower() or "hearts" in page_text.lower():
                logger.info("[ZEFOY] Services appeared!")
                return True

            # After 28 seconds, try clicking top-right X
            if wait_sec >= 28:
                try:
                    viewport = self._page.viewport_size
                    if viewport:
                        await self._page.mouse.click(viewport["width"] - 30, 30)
                except Exception:
                    pass

            if wait_sec % 10 == 0:
                logger.info(f"[ZEFOY] Waiting for ad... {wait_sec}s")

        return False

    async def _toolkit_solve_captcha(self, solver) -> bool:
        """Toolkit: Solve the captcha."""
        try:
            # Hide ads first
            await self._hide_ad_overlays()

            # Get captcha image
            captcha_img = self._page.locator("img.img-thumbnail").first
            if not await captcha_img.count():
                return False

            # Screenshot and solve
            captcha_bytes = await captcha_img.screenshot()
            solution = solver.solve(captcha_bytes)

            if not solution:
                logger.warning("[ZEFOY] OCR returned no solution")
                return False

            logger.info(f"[ZEFOY] OCR solution: {solution}")

            # Fill input
            captcha_input = self._page.locator(
                "#captchatoken, input.form-control[type='text']"
            ).first
            if await captcha_input.count() and await captcha_input.is_visible():
                await captcha_input.clear()
                await captcha_input.fill(solution.lower())
                await asyncio.sleep(0.5)

                # Hide ads before clicking submit
                await self._hide_ad_overlays()

                # Click submit
                submit_btn = self._page.locator(
                    "button.submit-captcha, button[type='submit']"
                ).first
                if await submit_btn.count():
                    try:
                        await submit_btn.click(force=True, timeout=5000)
                    except Exception:
                        await submit_btn.evaluate("el => el.click()")

                    await asyncio.sleep(2)
                    return True

        except Exception as e:
            logger.warning(f"[ZEFOY] Captcha solve failed: {e}")

        return False

    async def _handle_ads(self) -> None:
        """Legacy method - now just calls the smart state machine."""
        try:
            await asyncio.sleep(2)

            # STEP 1: LOOK at the page - get ALL text
            page_text = await self._page.inner_text("body")
            logger.info(f"[ZEFOY] Page text preview: {page_text[:200]}...")

            # STEP 2: Is there "View a short ad" button?
            if "view a short ad" in page_text.lower() or "unlock more content" in page_text.lower():
                logger.info("[ZEFOY] SAW: Ad wall detected!")

                # Find and click the ad button
                ad_btn = self._page.locator("button, a").filter(has_text="View a short ad").first
                if await ad_btn.count():
                    logger.info("[ZEFOY] Clicking 'View a short ad' button...")
                    await ad_btn.click(timeout=5000)
                    await asyncio.sleep(3)
                else:
                    # Try alternative selectors
                    for sel in [
                        "button:has-text('View')",
                        "a:has-text('View')",
                        "button:has-text('ad')",
                    ]:
                        try:
                            btn = self._page.locator(sel).first
                            if await btn.count() and await btn.is_visible():
                                await btn.click(timeout=5000)
                                logger.info(f"[ZEFOY] Clicked: {sel}")
                                await asyncio.sleep(3)
                                break
                        except Exception:
                            pass

            # STEP 3: Wait for ad, LOOK for close button every second
            for i in range(60):
                # Check if we see captcha form (by actual elements, not text!)
                # The captcha input has id="captchatoken" or class="form-control"
                # The captcha image has class="img-thumbnail"
                try:
                    captcha_input = self._page.locator(
                        "#captchatoken, input.form-control[type='text']"
                    ).first
                    captcha_img = self._page.locator("img.img-thumbnail").first

                    if await captcha_input.count() and await captcha_input.is_visible():
                        if await captcha_img.count() and await captcha_img.is_visible():
                            logger.info("[ZEFOY] SAW: Captcha form detected! Ad complete.")
                            return  # Exit _handle_ads - captcha is ready
                except Exception:
                    pass

                # Check if we see service buttons (even better - means already solved!)
                try:
                    service_btn = self._page.locator(
                        "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button"
                    )
                    if await service_btn.count() and await service_btn.is_visible():
                        logger.info("[ZEFOY] SAW: Services visible! Already solved.")
                        return  # Exit _handle_ads
                except Exception:
                    pass

                # LOOK for ANY close/X button - check MAIN PAGE first
                close_clicked = False
                close_selectors = [
                    "button.close",
                    ".close",
                    "button:has-text('×')",
                    "button:has-text('X')",
                    "button:has-text('Close')",
                    "button:has-text('Skip')",
                    "[class*='close']",
                    "[aria-label='Close']",
                    ".btn-close",
                    "[class*='dismiss']",
                ]

                for sel in close_selectors:
                    try:
                        close_btn = self._page.locator(sel).first
                        if await close_btn.count() and await close_btn.is_visible():
                            bbox = await close_btn.bounding_box()
                            if bbox:
                                x = bbox["x"] + bbox["width"] / 2
                                y = bbox["y"] + bbox["height"] / 2
                                await self._page.mouse.click(x, y)
                                logger.info(
                                    f"[ZEFOY] CLICKED close on main page at ({x:.0f}, {y:.0f})"
                                )
                                close_clicked = True
                                await asyncio.sleep(2)
                                break
                    except Exception:
                        pass

                # Check ALL IFRAMES for close buttons (ad is in iframe!)
                if not close_clicked:
                    for frame in self._page.frames:
                        if frame == self._page.main_frame:
                            continue
                        try:
                            # Log iframe URL for debugging
                            frame_url = frame.url
                            if i == 30:  # Log at 30 seconds when X should appear
                                logger.info(f"[ZEFOY] Checking iframe: {frame_url[:50]}...")

                            for sel in close_selectors:
                                try:
                                    close_btn = frame.locator(sel).first
                                    if await close_btn.count() and await close_btn.is_visible():
                                        bbox = await close_btn.bounding_box()
                                        if bbox:
                                            x = bbox["x"] + bbox["width"] / 2
                                            y = bbox["y"] + bbox["height"] / 2
                                            await self._page.mouse.click(x, y)
                                            logger.info(
                                                f"[ZEFOY] CLICKED close in IFRAME at ({x:.0f}, {y:.0f})"
                                            )
                                            close_clicked = True
                                            await asyncio.sleep(2)
                                            break
                                except Exception:
                                    pass
                            if close_clicked:
                                break
                        except Exception:
                            pass

                # At 30 seconds, the X button appears in TOP RIGHT corner
                # It's a white X on dark background - click by position!
                if i >= 28 and not close_clicked:
                    try:
                        # Get viewport size
                        viewport = self._page.viewport_size
                        if viewport:
                            # X button is in top-right corner (about 30px from edges)
                            x_pos = viewport["width"] - 30
                            y_pos = 30
                            logger.info(f"[ZEFOY] Clicking TOP-RIGHT X at ({x_pos}, {y_pos})")
                            await self._page.mouse.click(x_pos, y_pos)
                            await asyncio.sleep(2)

                            # Check if ad closed
                            page_text = await self._page.inner_text("body")
                            if "captcha" in page_text.lower() or "verify" in page_text.lower():
                                logger.info("[ZEFOY] X clicked! Ad closed, captcha visible!")
                                close_clicked = True
                                break
                    except Exception as e:
                        logger.warning(f"[ZEFOY] Top-right click failed: {e}")

                # Also try to find any clickable element in top-right area
                if i >= 28 and not close_clicked:
                    try:
                        # Look for SVG, span, div with close-like attributes in top-right
                        top_right_selectors = [
                            "svg[class*='close']",
                            "svg[aria-label*='close' i]",
                            "span[class*='close']",
                            "div[class*='close']",
                            "[class*='modal'] [class*='close']",
                            "[class*='overlay'] [class*='close']",
                            "svg path",  # Often close icons are SVG paths
                        ]
                        for sel in top_right_selectors:
                            try:
                                els = self._page.locator(sel)
                                count = await els.count()
                                for idx in range(count):
                                    el = els.nth(idx)
                                    if await el.is_visible():
                                        bbox = await el.bounding_box()
                                        if bbox and bbox["x"] > 1000:  # Right side of screen
                                            x = bbox["x"] + bbox["width"] / 2
                                            y = bbox["y"] + bbox["height"] / 2
                                            logger.info(
                                                f"[ZEFOY] Found top-right element: {sel} at ({x:.0f}, {y:.0f})"
                                            )
                                            await self._page.mouse.click(x, y)
                                            close_clicked = True
                                            await asyncio.sleep(2)
                                            break
                            except Exception:
                                pass
                            if close_clicked:
                                break
                    except Exception:
                        pass

                # At 30s, SCRAPE THE HTML to find the X button element
                if i == 30 and not close_clicked:
                    try:
                        # Save screenshot
                        await self._page.screenshot(path="/tmp/zefoy_ad_30sec.png", full_page=True)
                        logger.info("[ZEFOY] Saved screenshot at 30s")

                        # SCRAPE HTML - dump the DOM
                        html = await self._page.content()
                        with open("/tmp/zefoy_ad_30sec.html", "w") as f:
                            f.write(html)
                        logger.info("[ZEFOY] Saved HTML at 30s: /tmp/zefoy_ad_30sec.html")

                        # Find ALL clickable elements and log them
                        clickables = await self._page.locator(
                            "button, a, [onclick], [role='button'], svg, [class*='close'], [class*='dismiss']"
                        ).all()
                        logger.info(f"[ZEFOY] Found {len(clickables)} clickable elements")

                        for idx, el in enumerate(clickables[:30]):  # First 30
                            try:
                                if await el.is_visible():
                                    bbox = await el.bounding_box()
                                    tag = await el.evaluate("el => el.tagName")
                                    classes = await el.get_attribute("class") or ""
                                    text = ""
                                    with contextlib.suppress(builtins.BaseException):
                                        text = (await el.inner_text())[:30]
                                    if bbox:
                                        logger.info(
                                            f"[ZEFOY] Element {idx}: {tag} class='{classes[:50]}' text='{text}' at ({bbox['x']:.0f},{bbox['y']:.0f})"
                                        )
                            except:
                                pass
                    except Exception as e:
                        logger.warning(f"[ZEFOY] HTML scrape failed: {e}")

                if i % 10 == 0:
                    logger.info(f"[ZEFOY] Waiting... {i}s (looking for close button)")

                await asyncio.sleep(1)

            # STEP 4: Press Escape and check final state
            await self._page.keyboard.press("Escape")
            await asyncio.sleep(1)

            page_text = await self._page.inner_text("body")
            logger.info(f"[ZEFOY] Final page: {page_text[:100]}...")

        except Exception as e:
            logger.warning(f"[ZEFOY] Ad handling error: {e}")

    async def _close_modals(self) -> None:
        """Close any modal overlays like #gpq that block interaction."""
        # Try multiple times as modals may have animations
        for _attempt in range(5):
            closed_any = False

            # Broad search for ANY close/X button on the page
            close_selectors = [
                # Specific modal selectors
                "#gpq .close",
                "#gpq button.close",
                "#gpq [data-dismiss='modal']",
                ".modal.show .close",
                ".modal.show button.close",
                ".modal [data-dismiss='modal']",
                # Generic close buttons
                "button.close",
                ".close",
                "button[aria-label='Close']",
                "[aria-label='Close']",
                # X button variations
                "button:has-text('×')",
                "button:has-text('✕')",
                "button:has-text('✖')",
                "button:has-text('X')",
                "button:has-text('x')",
                # Common close button classes
                ".btn-close",
                "[class*='close-btn']",
                "[class*='closeBtn']",
                "[class*='modal-close']",
                # Ad-specific close buttons
                ".ad-close",
                "[class*='ad'] .close",
                "[class*='ad'] button:has-text('×')",
                # iFrame close buttons
                "iframe + .close",
            ]

            for selector in close_selectors:
                try:
                    close_btn = self._page.locator(selector).first
                    if await close_btn.count() and await close_btn.is_visible():
                        logger.info(f"[ZEFOY] Found close button: {selector}")
                        await close_btn.click(timeout=3000)
                        logger.info(f"[ZEFOY] Clicked close button: {selector}")
                        closed_any = True
                        await asyncio.sleep(1)
                        break
                except Exception:
                    pass

            # Try to find close button by looking at all visible buttons
            if not closed_any:
                try:
                    all_buttons = self._page.locator("button")
                    count = await all_buttons.count()
                    for i in range(min(count, 20)):  # Check first 20 buttons
                        btn = all_buttons.nth(i)
                        if await btn.is_visible():
                            text = await btn.inner_text()
                            classes = await btn.get_attribute("class") or ""
                            # Check if it looks like a close button
                            if any(x in text.lower() for x in ["×", "✕", "x", "close"]) or any(
                                x in classes.lower() for x in ["close", "dismiss"]
                            ):
                                logger.info(
                                    f"[ZEFOY] Found close-like button: text='{text}' class='{classes}'"
                                )
                                await btn.click(timeout=3000)
                                logger.info("[ZEFOY] Clicked close-like button")
                                closed_any = True
                                await asyncio.sleep(1)
                                break
                except Exception as e:
                    logger.debug(f"[ZEFOY] Error scanning buttons: {e}")

            # Press Escape key
            try:
                await self._page.keyboard.press("Escape")
                await asyncio.sleep(0.5)
            except Exception:
                pass

            # Check if captcha or services are visible now (success condition)
            try:
                service_btn = self._page.locator(
                    "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button"
                )
                if await service_btn.count() and await service_btn.is_visible():
                    logger.info("[ZEFOY] Services visible, modal handling complete")
                    return

                captcha = self._page.locator(f"xpath={CAPTCHA_BOX_XPATH}")
                if await captcha.count() and await captcha.is_visible():
                    logger.info("[ZEFOY] Captcha visible, modal handling complete")
                    return
            except Exception:
                pass

            if not closed_any:
                # Take screenshot for debugging
                try:
                    await self._page.screenshot(path="/tmp/zefoy_modal_debug.png")
                    logger.debug("[ZEFOY] Saved debug screenshot to /tmp/zefoy_modal_debug.png")
                except Exception:
                    pass
                break

            await asyncio.sleep(0.5)

    async def _random_delay(self) -> None:
        """Wait for a random human-like duration."""
        delay = random.uniform(self.config.human_delay_min, self.config.human_delay_max)
        await asyncio.sleep(delay)

    def _parse_cooldown(self, text: str) -> int:
        """Parse cooldown time from text like 'Please wait 2 minute(s) 30 second(s)'."""
        try:
            minutes = 0
            seconds = 0
            # Extract minutes
            if "minute" in text.lower():
                parts = text.lower().split("minute")
                num_part = parts[0].split()[-1]
                minutes = (
                    int(re.search(r"\d+", num_part).group()) if re.search(r"\d+", num_part) else 0
                )
            # Extract seconds
            if "second" in text.lower():
                parts = text.lower().split("second")
                num_part = parts[0].split()[-1]
                seconds = (
                    int(re.search(r"\d+", num_part).group()) if re.search(r"\d+", num_part) else 0
                )
            return minutes * 60 + seconds + 5  # +5 buffer
        except Exception:
            return 60  # Default 60s

    async def _has_captcha(self) -> bool:
        """Check if captcha is present."""
        captcha_selectors = [
            "img[src*='captcha']",
            "img.img-thumbnail",
            "input[placeholder*='captcha' i]",
            "input[name*='captcha' i]",
        ]

        for selector in captcha_selectors:
            try:
                if await self._page.locator(selector).count():
                    return True
            except Exception:
                pass
        return False

    async def _hide_ad_overlays(self) -> None:
        """Hide ad iframes/overlays that block interaction with the page."""
        try:
            # Use JavaScript to hide all ad-related elements
            await self._page.evaluate("""
                () => {
                    // Hide all Google ad iframes
                    document.querySelectorAll('iframe[id^="aswift"], iframe[title*="Advertisement"], iframe[src*="googleads"], iframe[src*="doubleclick"]').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                    });
                    // Hide adsbygoogle containers
                    document.querySelectorAll('.adsbygoogle, ins.adsbygoogle').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                    });
                    // Hide Google Funding Choices dialogs
                    document.querySelectorAll('.fc-dialog, .fc-monetization-dialog, .fc-dialog-container, .fc-message-root, div.fc-consent-root').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                    });
                    // Remove any overlay backdrop
                    document.querySelectorAll('.fc-dialog-overlay, .fc-ab-root').forEach(el => {
                        el.remove();
                    });
                }
            """)
            logger.debug("[ZEFOY] Hid ad overlays")
        except Exception as e:
            logger.debug(f"[ZEFOY] Failed to hide ad overlays: {e}")

        # Also try to click away Funding Choices dialog
        await self._close_funding_choices()

    async def _close_funding_choices(self) -> bool:
        """Close Google Funding Choices consent dialog."""
        try:
            # Look for "View a short ad" button inside fc-dialog and click it
            fc_buttons = [
                ".fc-button",
                ".fc-cta-consent",
                ".fc-primary-button",
                "button:has-text('View')",
                "button:has-text('Accept')",
                ".fc-dialog button",
            ]
            for sel in fc_buttons:
                try:
                    btn = self._page.locator(sel).first
                    if await btn.count() and await btn.is_visible():
                        await btn.click(force=True, timeout=2000)
                        logger.info(f"[ZEFOY] Clicked funding choices button: {sel}")
                        await asyncio.sleep(1)
                        return True
                except Exception:
                    pass

            # Try to close via JS
            await self._page.evaluate("""
                () => {
                    // Remove the entire fc-root
                    document.querySelectorAll('div.fc-consent-root, div.fc-ab-root').forEach(el => el.remove());
                }
            """)
        except Exception as e:
            logger.debug(f"[ZEFOY] Failed to close funding choices: {e}")
        return False

    async def _solve_captcha(self) -> bool:
        """Solve captcha using OCR."""
        from ghoststorm.plugins.captcha.zefoy_ocr import ZefoyOCRSolver

        for attempt in range(self.config.max_captcha_retries):
            # Always try to close modals and hide ads first - they block interaction
            await self._close_modals()
            await self._hide_ad_overlays()

            logger.debug(
                "[ZEFOY] Attempting captcha solve",
                attempt=attempt + 1,
                max_attempts=self.config.max_captcha_retries,
            )

            # Check if services visible (captcha already solved)
            try:
                service_btn = self._page.locator(
                    "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button"
                )
                if await service_btn.count() and await service_btn.is_visible():
                    logger.info("[ZEFOY] Services already visible, captcha passed")
                    return True
            except Exception:
                pass

            # Find captcha image using XPath for more precision
            captcha_img = self._page.locator(f"xpath={CAPTCHA_BOX_XPATH}//img").first

            # Fallback to CSS selectors
            if not await captcha_img.count():
                captcha_img = self._page.locator("img.img-thumbnail, img[src*='captcha']").first

            if not await captcha_img.count():
                # No captcha visible - might be success
                await asyncio.sleep(1)
                continue

            try:
                # Screenshot captcha
                captcha_bytes = await captcha_img.screenshot()

                # Solve with OCR
                solver = ZefoyOCRSolver()
                solution = solver.solve(captcha_bytes)

                if not solution:
                    logger.warning("[ZEFOY] OCR returned no solution")
                    continue

                logger.debug("[ZEFOY] OCR solution", solution=solution)

                # Find VISIBLE captcha text input (not hidden!)
                captcha_input = None

                # Try XPath first
                xpath_input = self._page.locator(
                    f"xpath={CAPTCHA_BOX_XPATH}//input[@type='text']"
                ).first
                if await xpath_input.count() and await xpath_input.is_visible():
                    captcha_input = xpath_input

                # Try visible text input in form
                if not captcha_input:
                    visible_inputs = self._page.locator("form input[type='text']:visible").first
                    if await visible_inputs.count():
                        captcha_input = visible_inputs

                # Try any visible text input
                if not captcha_input:
                    all_visible = self._page.locator("input[type='text']:visible").first
                    if await all_visible.count():
                        captcha_input = all_visible

                if captcha_input and await captcha_input.count():
                    await captcha_input.clear()
                    await captcha_input.fill(solution.lower())
                    logger.info(f"[ZEFOY] Filled captcha: {solution.lower()}")
                    await asyncio.sleep(0.5)

                    # Submit using XPath first
                    submit_btn = self._page.locator(f"xpath={CAPTCHA_BOX_XPATH}//button").first

                    # Fallback to CSS
                    if not await submit_btn.count():
                        submit_btn = self._page.locator(
                            "button.submit-captcha, button[type='submit'], input[type='submit']"
                        ).first

                    if await submit_btn.count():
                        # Hide ads again right before clicking
                        await self._hide_ad_overlays()

                        # Try force click first (bypasses actionability checks)
                        try:
                            await submit_btn.click(force=True, timeout=5000)
                        except Exception:
                            # Fallback to JavaScript click
                            try:
                                await submit_btn.evaluate("el => el.click()")
                                logger.debug("[ZEFOY] Used JS click for submit")
                            except Exception as e:
                                logger.warning(f"[ZEFOY] Submit click failed: {e}")

                        await asyncio.sleep(2)

                        # Close any modal that might pop up
                        await self._close_modals()
                        await self._hide_ad_overlays()

                        # Check if services now visible (multiple detection methods)
                        services_visible = False

                        # Method 1: XPath for service button
                        service_btn = self._page.locator(
                            "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button"
                        )
                        if await service_btn.count() and await service_btn.is_visible():
                            services_visible = True

                        # Method 2: Look for service-specific elements
                        if not services_visible:
                            service_ids = [
                                "#t-followers-button",
                                "#t-views-button",
                                "#t-hearts-button",
                                "#t-shares-button",
                            ]
                            for sid in service_ids:
                                try:
                                    btn = self._page.locator(sid)
                                    if await btn.count() and await btn.is_visible():
                                        services_visible = True
                                        logger.info(f"[ZEFOY] Found service button: {sid}")
                                        break
                                except Exception:
                                    pass

                        # Method 3: Look for input field to enter TikTok URL (means we're past captcha)
                        if not services_visible:
                            url_input = self._page.locator(
                                "input[placeholder*='tiktok'], input[placeholder*='video'], input[name*='url']"
                            )
                            if await url_input.count() and await url_input.is_visible():
                                services_visible = True
                                logger.info("[ZEFOY] Found TikTok URL input - past captcha!")

                        if services_visible:
                            self._captchas_solved += 1
                            logger.info("[ZEFOY] Captcha solved successfully - services visible!")
                            return True

                        # Log current page state for debugging
                        page_text = await self._page.inner_text("body")
                        logger.debug(f"[ZEFOY] Page after submit: {page_text[:200]}...")

            except Exception as e:
                logger.warning("[ZEFOY] Captcha attempt failed", error=str(e))

            # Try to reload captcha for fresh image
            try:
                reload_btn = self._page.locator(
                    "a:has-text('reload'), button:has-text('Reload'), .reload-captcha"
                ).first
                if await reload_btn.count():
                    await reload_btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

        return False

    async def _get_cooldown_time(self, div_num: str = "2") -> int:
        """Parse cooldown timer from page."""
        # First try: search page text for cooldown pattern
        try:
            page_text = await self._page.inner_text("body")
            if "please wait" in page_text.lower() or "before trying" in page_text.lower():
                cooldown = self._parse_cooldown(page_text)
                if cooldown > 0:
                    return cooldown
        except Exception:
            pass

        # Fallback: try XPath
        try:
            cooldown_xpath = f"/html/body/div[5]/div[{div_num}]/div/div/h4"
            timer_element = self._page.locator(f"xpath={cooldown_xpath}")
            if await timer_element.count():
                text = await timer_element.text_content()
                if text and ("wait" in text.lower() or "second" in text.lower()):
                    return self._parse_cooldown(text)
        except Exception:
            pass

        return 0

    async def _check_success(self) -> bool:
        """Check if the action was successful."""
        try:
            page_text = await self._page.inner_text("body")
            page_text_lower = page_text.lower()

            # Success indicators in page text
            if "successfully" in page_text_lower:
                return True
            if "sent" in page_text_lower and (
                "heart" in page_text_lower or "like" in page_text_lower
            ):
                return True

            # Cooldown message means it worked previously
            if "please wait" in page_text_lower and (
                "second" in page_text_lower or "minute" in page_text_lower
            ):
                return True

            if "before trying again" in page_text_lower:
                return True

        except Exception:
            pass

        # Fallback: check for specific locators
        success_indicators = [
            "text='Successfully'",
            ".alert-success",
        ]
        for indicator in success_indicators:
            try:
                if await self._page.locator(indicator).count():
                    return True
            except Exception:
                pass

        return False


async def check_zefoy_services() -> dict[str, bool]:
    """Check which Zefoy services are currently available.

    Must handle ad popup and solve captcha before service buttons are visible.

    Returns:
        Dict mapping service name to availability status
    """
    try:
        from patchright.async_api import async_playwright
    except ImportError:
        from playwright.async_api import async_playwright

    status = dict.fromkeys(ZEFOY_SERVICES, False)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            logger.info("[ZEFOY_CHECK] Navigating to Zefoy...")
            await page.goto(ZEFOY_URL, timeout=30000)
            await asyncio.sleep(3)

            # Handle ad popup first
            logger.info("[ZEFOY_CHECK] Checking for ads...")
            await _handle_ads_standalone(page)

            # Wait for and solve captcha
            logger.info("[ZEFOY_CHECK] Solving captcha...")
            captcha_solved = await _solve_captcha_standalone(page)

            if not captcha_solved:
                logger.warning("[ZEFOY_CHECK] Captcha not solved, services may not be visible")
                # Still try to check - maybe captcha was already solved
                await asyncio.sleep(2)

            # Wait for service buttons to appear
            logger.info("[ZEFOY_CHECK] Checking service availability...")
            try:
                first_service_xpath = ZEFOY_SERVICES["followers"]
                await page.wait_for_selector(f"xpath={first_service_xpath}", timeout=15000)
            except Exception:
                logger.warning("[ZEFOY_CHECK] Service buttons not visible after captcha")

            # Check each service
            for service, xpath in ZEFOY_SERVICES.items():
                try:
                    btn = page.locator(f"xpath={xpath}")
                    if await btn.count():
                        # Check if button is enabled (not grayed out)
                        is_enabled = await btn.is_enabled()
                        # Also check if it has disabled class or style
                        classes = await btn.get_attribute("class") or ""
                        is_disabled_class = (
                            "disabled" in classes.lower() or "nonec" in classes.lower()
                        )
                        status[service] = is_enabled and not is_disabled_class
                        logger.debug(
                            f"[ZEFOY_CHECK] {service}: enabled={is_enabled}, disabled_class={is_disabled_class}"
                        )
                    else:
                        status[service] = False
                except Exception as e:
                    logger.debug(f"[ZEFOY_CHECK] Error checking {service}: {e}")
                    status[service] = False

            logger.info("[ZEFOY_CHECK] Service status", status=status)

        except Exception as e:
            logger.error(f"[ZEFOY_CHECK] Failed to check services: {e}")

        finally:
            await browser.close()

    return status


async def _close_modals_standalone(page) -> None:
    """Close any modal overlays (standalone version)."""
    for _attempt in range(5):
        closed_any = False

        # Broad search for ANY close/X button
        close_selectors = [
            "#gpq .close",
            "#gpq button.close",
            ".modal.show .close",
            ".modal [data-dismiss='modal']",
            "button.close",
            ".close",
            "button[aria-label='Close']",
            "[aria-label='Close']",
            "button:has-text('×')",
            "button:has-text('✕')",
            "button:has-text('X')",
            ".btn-close",
            "[class*='close-btn']",
            ".ad-close",
        ]

        for selector in close_selectors:
            try:
                close_btn = page.locator(selector).first
                if await close_btn.count() and await close_btn.is_visible():
                    logger.info(f"[ZEFOY_CHECK] Found close button: {selector}")
                    await close_btn.click(timeout=3000)
                    closed_any = True
                    await asyncio.sleep(1)
                    break
            except Exception:
                pass

        # Scan all buttons for close-like ones
        if not closed_any:
            try:
                all_buttons = page.locator("button")
                count = await all_buttons.count()
                for i in range(min(count, 20)):
                    btn = all_buttons.nth(i)
                    if await btn.is_visible():
                        text = await btn.inner_text()
                        classes = await btn.get_attribute("class") or ""
                        if any(x in text.lower() for x in ["×", "✕", "x", "close"]) or any(
                            x in classes.lower() for x in ["close", "dismiss"]
                        ):
                            logger.info(f"[ZEFOY_CHECK] Found close-like button: '{text}'")
                            await btn.click(timeout=3000)
                            closed_any = True
                            await asyncio.sleep(1)
                            break
            except Exception:
                pass

        # Press Escape
        try:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
        except Exception:
            pass

        # Check if services or captcha visible (success)
        try:
            service_btn = page.locator(
                "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button"
            )
            if await service_btn.count() and await service_btn.is_visible():
                logger.info("[ZEFOY_CHECK] Services visible, modal closed")
                return
            captcha = page.locator(f"xpath={CAPTCHA_BOX_XPATH}")
            if await captcha.count() and await captcha.is_visible():
                logger.info("[ZEFOY_CHECK] Captcha visible, modal closed")
                return
        except Exception:
            pass

        if not closed_any:
            break

        await asyncio.sleep(0.5)


async def _handle_ads_standalone(page) -> None:
    """Handle content unlock ads (standalone version for status check)."""
    await asyncio.sleep(2)

    # Check for content unlock ad - "View a short ad" button
    view_ad_selectors = [
        "button:has-text('View a short ad')",
        "a:has-text('View a short ad')",
        "div:has-text('View a short ad') >> button",
        "button:has-text('Watch')",
        "button:has-text('View ad')",
        "button:has-text('Continue')",
    ]

    ad_clicked = False
    for selector in view_ad_selectors:
        try:
            btn = page.locator(selector).first
            if await btn.count() and await btn.is_visible():
                logger.info(f"[ZEFOY_CHECK] Found ad button: {selector}")
                await btn.click(timeout=5000)
                ad_clicked = True
                await asyncio.sleep(3)
                break
        except Exception:
            pass

    if ad_clicked:
        logger.info("[ZEFOY_CHECK] Waiting for ad to complete...")
        for _i in range(60):
            # Check if captcha or service visible
            try:
                captcha_visible = await page.locator(f"xpath={CAPTCHA_BOX_XPATH}").count()
                if captcha_visible:
                    logger.info("[ZEFOY_CHECK] Ad done, captcha visible")
                    break
            except Exception:
                pass

            try:
                service_btn = page.locator(
                    "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button"
                )
                if await service_btn.count():
                    logger.info("[ZEFOY_CHECK] Ad done, services visible")
                    break
            except Exception:
                pass

            # Look for skip/close
            for skip_sel in ["button:has-text('Skip')", "button:has-text('Close')"]:
                try:
                    skip_btn = page.locator(skip_sel).first
                    if await skip_btn.count() and await skip_btn.is_visible():
                        await skip_btn.click(timeout=2000)
                        break
                except Exception:
                    pass

            await asyncio.sleep(1)

        await asyncio.sleep(2)

    # Close any modals including #gpq
    await _close_modals_standalone(page)


async def _solve_captcha_standalone(page, max_attempts: int = 5) -> bool:
    """Solve captcha (standalone version for status check)."""
    from ghoststorm.plugins.captcha.zefoy_ocr import ZefoyOCRSolver

    solver = ZefoyOCRSolver()

    for attempt in range(1, max_attempts + 1):
        # Close any blocking modals first
        await _close_modals_standalone(page)

        try:
            # Check if services already visible
            service_btn = page.locator(
                "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button"
            )
            if await service_btn.count() and await service_btn.is_visible():
                logger.info("[ZEFOY_CHECK] Services visible, captcha passed")
                return True

            # Check if captcha is present
            captcha_box = page.locator(f"xpath={CAPTCHA_BOX_XPATH}")
            if not await captcha_box.count():
                await asyncio.sleep(1)
                continue

            # Get captcha image
            captcha_img = page.locator(f"xpath={CAPTCHA_BOX_XPATH}//img").first
            if not await captcha_img.count():
                captcha_img = page.locator("img.img-thumbnail, img[src*='captcha']").first
            if not await captcha_img.count():
                await asyncio.sleep(1)
                continue

            # Screenshot and solve
            img_bytes = await captcha_img.screenshot()
            solution = solver.solve(img_bytes)

            if not solution:
                logger.debug(f"[ZEFOY_CHECK] OCR returned no solution, attempt {attempt}")
                await asyncio.sleep(1)
                continue

            logger.debug(f"[ZEFOY_CHECK] OCR solution: {solution}")

            # Enter solution
            input_field = page.locator(f"xpath={CAPTCHA_BOX_XPATH}//input").first
            if not await input_field.count():
                input_field = page.locator(
                    "input[placeholder*='captcha' i], .captcha-form input"
                ).first

            if await input_field.count():
                await input_field.clear()
                await input_field.fill(solution.lower())
                await asyncio.sleep(0.5)

                # Submit
                submit_btn = page.locator(f"xpath={CAPTCHA_BOX_XPATH}//button").first
                if not await submit_btn.count():
                    submit_btn = page.locator("button.submit-captcha, button[type='submit']").first

                if await submit_btn.count():
                    await submit_btn.click()
                    await asyncio.sleep(2)

                    # Check if solved
                    service_btn = page.locator(
                        "xpath=/html/body/div[5]/div[1]/div[3]/div[2]/div[1]/div/button"
                    )
                    if await service_btn.count():
                        logger.info("[ZEFOY_CHECK] Captcha solved!")
                        return True

        except Exception as e:
            logger.debug(f"[ZEFOY_CHECK] Captcha attempt {attempt} error: {e}")

        await asyncio.sleep(1)

    return False
