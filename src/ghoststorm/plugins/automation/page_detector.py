"""Page Detector - Analyzes pages and suggests automation configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DetectedElement:
    """A detected interactive element on the page."""

    type: str  # username, password, email, captcha_image, captcha_input, submit, etc.
    selector: str
    text: str = ""
    confidence: float = 0.0
    attributes: dict = field(default_factory=dict)


@dataclass
class PageDetectionResult:
    """Result of page analysis."""

    url: str
    title: str
    page_type: str  # login, registration, captcha, form, social, unknown
    confidence: float
    detected_elements: list[DetectedElement] = field(default_factory=list)
    suggested_goal_keywords: list[str] = field(default_factory=list)
    suggested_captcha_selectors: dict[str, str] | None = None
    suggested_actions: list[dict] = field(default_factory=list)


class PageDetector:
    """Analyzes page structure and suggests automation configuration."""

    # URL patterns for page type detection
    PAGE_TYPE_URL_PATTERNS = {
        "login": [r"login", r"signin", r"sign-in", r"auth", r"sso"],
        "registration": [r"register", r"signup", r"sign-up", r"create.?account", r"join"],
        "contact": [r"contact", r"support", r"feedback", r"help"],
        "social": [r"tiktok", r"instagram", r"youtube", r"twitter", r"facebook", r"zefoy"],
    }

    # Text patterns for page type detection
    PAGE_TYPE_TEXT_PATTERNS = {
        "login": ["sign in", "log in", "login", "username", "password", "forgot password"],
        "registration": ["create account", "sign up", "register", "confirm password", "terms"],
        "contact": ["contact us", "send message", "get in touch", "email us"],
        "social": ["followers", "likes", "views", "hearts", "shares", "subscribers"],
        "captcha": ["captcha", "verify", "human", "robot", "security check"],
    }

    # Element detection patterns
    ELEMENT_PATTERNS = {
        "username": [
            ("input[name*='user' i]", 0.9),
            ("input[name*='login' i]", 0.8),
            ("input[placeholder*='username' i]", 0.9),
            ("input[autocomplete='username']", 0.95),
            ("input[id*='user' i]", 0.7),
        ],
        "email": [
            ("input[type='email']", 0.95),
            ("input[name*='email' i]", 0.9),
            ("input[placeholder*='email' i]", 0.85),
            ("input[autocomplete='email']", 0.95),
        ],
        "password": [
            ("input[type='password']", 0.99),
            ("input[name*='pass' i]", 0.8),
        ],
        "captcha_image": [
            ("img[src*='captcha' i]", 0.95),
            ("img.captcha", 0.9),
            ("img.img-thumbnail", 0.7),
            ("canvas[class*='captcha' i]", 0.85),
            ("#captcha-image", 0.9),
            ("img[alt*='captcha' i]", 0.85),
        ],
        "captcha_input": [
            ("input[name*='captcha' i]", 0.95),
            ("input[placeholder*='captcha' i]", 0.9),
            ("#captchatoken", 0.95),
            ("input[id*='captcha' i]", 0.85),
            ("input[placeholder*='code' i]", 0.6),
        ],
        "submit": [
            ("button[type='submit']", 0.95),
            ("input[type='submit']", 0.95),
            ("button.btn-primary", 0.7),
            ("button:has-text('Submit')", 0.8),
            ("button:has-text('Login')", 0.85),
            ("button:has-text('Sign in')", 0.85),
            ("button:has-text('Send')", 0.75),
        ],
        "search_input": [
            ("input[type='search']", 0.95),
            ("input[placeholder*='search' i]", 0.85),
            ("input[placeholder*='url' i]", 0.8),
            ("input[placeholder*='video' i]", 0.75),
        ],
    }

    # Goal keywords by page type
    GOAL_KEYWORDS = {
        "login": ["dashboard", "welcome", "account", "profile", "home", "logged in"],
        "registration": [
            "verify",
            "confirmation",
            "success",
            "check your email",
            "account created",
        ],
        "contact": ["thank you", "message sent", "we will contact", "received", "submitted"],
        "social": ["followers", "views", "likes", "hearts", "shares", "comments", "success"],
        "captcha": ["success", "verified", "continue", "proceed"],
        "unknown": ["success", "done", "complete", "thank you"],
    }

    async def analyze_page(self, page: Any) -> PageDetectionResult:
        """Analyze a page and return detection results."""
        url = page.url
        title = await page.title()

        # Get page text
        try:
            page_text = await page.inner_text("body")
            page_text_lower = page_text.lower()
        except Exception:
            page_text_lower = ""

        # Detect page type
        page_type, type_confidence = self._detect_page_type(url, page_text_lower)

        # Detect elements
        detected_elements = await self._detect_elements(page)

        # If we found captcha elements, boost captcha page type
        has_captcha = any(e.type.startswith("captcha") for e in detected_elements)
        if has_captcha and page_type != "captcha":
            # It's a page with captcha, but might be login+captcha
            if page_type == "unknown":
                page_type = "captcha"
                type_confidence = 0.8

        # Suggest goal keywords
        suggested_keywords = self._suggest_goal_keywords(page_type, page_text_lower)

        # Suggest captcha selectors
        captcha_selectors = self._suggest_captcha_selectors(detected_elements)

        # Suggest actions based on detected elements
        suggested_actions = self._suggest_actions(page_type, detected_elements)

        return PageDetectionResult(
            url=url,
            title=title,
            page_type=page_type,
            confidence=type_confidence,
            detected_elements=detected_elements,
            suggested_goal_keywords=suggested_keywords,
            suggested_captcha_selectors=captcha_selectors,
            suggested_actions=suggested_actions,
        )

    def _detect_page_type(self, url: str, page_text: str) -> tuple[str, float]:
        """Detect page type based on URL and content."""
        url_lower = url.lower()
        scores: dict[str, float] = {}

        # Check URL patterns
        for page_type, patterns in self.PAGE_TYPE_URL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    scores[page_type] = scores.get(page_type, 0) + 0.4

        # Check text patterns
        for page_type, keywords in self.PAGE_TYPE_TEXT_PATTERNS.items():
            matches = sum(1 for kw in keywords if kw in page_text)
            if matches > 0:
                scores[page_type] = scores.get(page_type, 0) + (0.15 * matches)

        if not scores:
            return "unknown", 0.3

        # Get highest scoring type
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type], 0.95)

        return best_type, confidence

    async def _detect_elements(self, page: Any) -> list[DetectedElement]:
        """Find and categorize interactive elements."""
        detected = []

        for element_type, patterns in self.ELEMENT_PATTERNS.items():
            for selector, base_confidence in patterns:
                try:
                    # Handle playwright text selectors
                    if ":has-text(" in selector:
                        # Skip text selectors for now, they're harder to validate
                        continue

                    locator = page.locator(selector)
                    count = await locator.count()

                    for i in range(min(count, 3)):  # Max 3 elements per selector
                        elem = locator.nth(i)
                        try:
                            if await elem.is_visible():
                                # Get element info
                                await elem.evaluate("el => el.tagName.toLowerCase()")
                                text = ""
                                try:
                                    text = await elem.inner_text()
                                    text = text[:50] if text else ""
                                except Exception:
                                    pass

                                # Get attributes
                                attrs = {}
                                for attr in ["name", "id", "placeholder", "type", "class"]:
                                    try:
                                        val = await elem.get_attribute(attr)
                                        if val:
                                            attrs[attr] = val
                                    except Exception:
                                        pass

                                detected.append(
                                    DetectedElement(
                                        type=element_type,
                                        selector=selector,
                                        text=text,
                                        confidence=base_confidence,
                                        attributes=attrs,
                                    )
                                )
                                break  # Found one for this selector

                        except Exception:
                            continue

                except Exception:
                    continue

        # Deduplicate by type (keep highest confidence)
        seen_types: dict[str, DetectedElement] = {}
        for elem in detected:
            if elem.type not in seen_types or elem.confidence > seen_types[elem.type].confidence:
                seen_types[elem.type] = elem

        return list(seen_types.values())

    def _suggest_goal_keywords(self, page_type: str, page_text: str) -> list[str]:
        """Suggest goal keywords based on page type."""
        keywords = list(self.GOAL_KEYWORDS.get(page_type, self.GOAL_KEYWORDS["unknown"]))

        # Add common success indicators found in page
        success_words = ["success", "complete", "done", "thank", "welcome", "verified"]
        for word in success_words:
            if word in page_text and word not in keywords:
                keywords.append(word)

        return keywords[:8]  # Limit to 8 suggestions

    def _suggest_captcha_selectors(self, elements: list[DetectedElement]) -> dict[str, str] | None:
        """Suggest captcha selectors from detected elements."""
        captcha_image = None
        captcha_input = None
        submit = None

        for elem in elements:
            if elem.type == "captcha_image" and not captcha_image:
                captcha_image = elem.selector
            elif elem.type == "captcha_input" and not captcha_input:
                captcha_input = elem.selector
            elif elem.type == "submit" and not submit:
                submit = elem.selector

        if captcha_image or captcha_input:
            return {
                "image": captcha_image or "",
                "input": captcha_input or "",
                "submit": submit or "button[type='submit']",
            }

        return None

    def _suggest_actions(self, page_type: str, elements: list[DetectedElement]) -> list[dict]:
        """Suggest action sequence based on page type and elements."""
        actions = []

        if page_type == "login":
            # Look for username/email and password fields
            for elem in elements:
                if elem.type in ("username", "email"):
                    actions.append(
                        {
                            "type": "fill",
                            "name": f"Fill {elem.type}",
                            "selectors": [elem.selector],
                            "value": "",  # User needs to fill this
                        }
                    )
                elif elem.type == "password":
                    actions.append(
                        {
                            "type": "fill",
                            "name": "Fill password",
                            "selectors": [elem.selector],
                            "value": "",
                        }
                    )

            # Add submit action
            for elem in elements:
                if elem.type == "submit":
                    actions.append(
                        {
                            "type": "click",
                            "name": "Submit form",
                            "selectors": [elem.selector],
                        }
                    )
                    break

        elif page_type == "social":
            # Look for search/URL input
            for elem in elements:
                if elem.type == "search_input":
                    actions.append(
                        {
                            "type": "fill",
                            "name": "Enter URL",
                            "selectors": [elem.selector],
                            "value": "",
                        }
                    )
                    break

            # Add submit
            for elem in elements:
                if elem.type == "submit":
                    actions.append(
                        {
                            "type": "click",
                            "name": "Submit",
                            "selectors": [elem.selector],
                        }
                    )
                    break

        return actions


async def analyze_page_standalone(url: str, headless: bool = True) -> PageDetectionResult:
    """Standalone function to analyze a page without an existing browser."""
    try:
        from patchright.async_api import async_playwright
    except ImportError:
        from playwright.async_api import async_playwright

    async with await async_playwright().start() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page()

        try:
            await page.goto(url, timeout=30000)
            detector = PageDetector()
            result = await detector.analyze_page(page)
            return result
        finally:
            await browser.close()
