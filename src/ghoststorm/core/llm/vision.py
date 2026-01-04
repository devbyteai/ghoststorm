"""Vision module for screenshot-based LLM analysis."""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ghoststorm.core.browser.protocol import IPage

logger = structlog.get_logger(__name__)


class VisionMode(str, Enum):
    """Vision mode for LLM analysis."""

    OFF = "off"  # No vision, DOM only
    AUTO = "auto"  # Use vision when DOM analysis is uncertain
    ALWAYS = "always"  # Always include screenshot


class VisionDetailLevel(str, Enum):
    """Detail level for screenshot analysis."""

    LOW = "low"  # Faster, less detail (512px)
    HIGH = "high"  # Slower, more detail (full res)
    AUTO = "auto"  # Let model decide


@dataclass
class VisionConfig:
    """Configuration for vision analysis."""

    mode: VisionMode = VisionMode.AUTO
    detail_level: VisionDetailLevel = VisionDetailLevel.AUTO
    max_width: int = 1280  # Max screenshot width
    max_height: int = 800  # Max screenshot height
    quality: int = 80  # JPEG quality (if using JPEG)
    format: str = "png"  # png or jpeg


@dataclass
class VisionAnalysis:
    """Result of vision analysis."""

    description: str  # What the model sees
    elements: list[dict[str, Any]] = field(default_factory=list)  # Detected elements
    suggested_action: dict[str, Any] | None = None  # Suggested next action
    coordinates: tuple[int, int] | None = None  # Click coordinates if applicable
    confidence: float = 0.0
    raw_response: str = ""


class BaseVisionProvider(ABC):
    """Base class for vision-capable LLM providers."""

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """Check if provider supports vision."""
        pass

    @property
    @abstractmethod
    def vision_models(self) -> list[str]:
        """List of vision-capable models."""
        pass

    @abstractmethod
    async def analyze_screenshot(
        self,
        screenshot: bytes,
        prompt: str,
        detail_level: VisionDetailLevel = VisionDetailLevel.AUTO,
    ) -> VisionAnalysis:
        """
        Analyze a screenshot with the vision model.

        Args:
            screenshot: PNG/JPEG screenshot bytes
            prompt: What to analyze/look for
            detail_level: Level of detail for analysis

        Returns:
            Vision analysis result
        """
        pass


async def capture_screenshot(
    page: IPage,
    config: VisionConfig | None = None,
) -> bytes:
    """
    Capture screenshot from page for vision analysis.

    Args:
        page: Browser page
        config: Vision configuration

    Returns:
        Screenshot bytes (PNG)
    """
    config = config or VisionConfig()

    # Get viewport size
    viewport = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")

    # Calculate scale if needed
    scale = 1.0
    if viewport.get("width", 0) > config.max_width:
        scale = config.max_width / viewport["width"]

    # Take screenshot
    screenshot = await page.screenshot(
        type=config.format,
        quality=config.quality if config.format == "jpeg" else None,
        full_page=False,  # Just viewport for speed
    )

    return screenshot


def encode_screenshot(screenshot: bytes) -> str:
    """Encode screenshot to base64 for API transmission."""
    return base64.b64encode(screenshot).decode("utf-8")


def get_image_media_type(screenshot: bytes) -> str:
    """Detect image media type from bytes."""
    if screenshot[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    elif screenshot[:2] == b"\xff\xd8":
        return "image/jpeg"
    elif screenshot[:4] == b"RIFF" and screenshot[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"  # Default


# Vision prompts for browser automation

VISION_ANALYSIS_PROMPT = """Analyze this screenshot of a web page.

Task: {task}

Describe what you see and identify:
1. The current state of the page
2. Key interactive elements (buttons, links, inputs)
3. Any popups, modals, or overlays
4. The best action to accomplish the task

Respond with JSON:
{{
    "description": "What the page shows",
    "elements": [
        {{"type": "button", "text": "Submit", "location": "center-right"}},
        ...
    ],
    "suggested_action": {{
        "type": "click",
        "target": "description of element to click",
        "coordinates": [x, y],  // approximate pixel coordinates
        "reason": "why this action"
    }},
    "confidence": 0.9,
    "is_complete": false
}}"""

VISION_ELEMENT_FIND_PROMPT = """Find this element in the screenshot:

Element description: {description}

Return the approximate pixel coordinates (x, y) of the element's center.
If multiple matches, return the most likely one.
If not found, return null.

Respond with JSON:
{{
    "found": true,
    "coordinates": [x, y],
    "confidence": 0.9,
    "element_description": "what you found"
}}"""

VISION_CAPTCHA_PROMPT = """Analyze this screenshot for CAPTCHA challenges.

Look for:
- reCAPTCHA widgets
- hCaptcha challenges
- Image selection grids
- Text-based CAPTCHAs
- Slider puzzles
- "Verify you're human" prompts

Respond with JSON:
{{
    "has_captcha": true/false,
    "captcha_type": "recaptcha" | "hcaptcha" | "image_select" | "text" | "slider" | "unknown",
    "location": [x, y],  // coordinates if found
    "description": "what you see"
}}"""


def build_vision_prompt(task: str) -> str:
    """Build vision analysis prompt."""
    return VISION_ANALYSIS_PROMPT.format(task=task)


def build_element_find_prompt(description: str) -> str:
    """Build element finding prompt."""
    return VISION_ELEMENT_FIND_PROMPT.format(description=description)
