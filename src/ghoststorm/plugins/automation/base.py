"""Social Media Automation Base Class.

Provides abstract base for TikTok and Instagram automation plugins with:
- Common swipe gesture simulation
- In-app WebView fingerprint injection
- Rate limiting integration
- Coherence engine integration
- Result tracking
"""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal

import structlog

from ghoststorm.plugins.behavior.coherence_engine import (
    CoherenceEngine,
    SessionState,
    UserPersona,
    get_coherence_engine,
)
from ghoststorm.plugins.network.rate_limiter import (
    RateLimiter,
    get_rate_limiter,
)

logger = structlog.get_logger(__name__)


class SocialPlatform(str, Enum):
    """Supported social media platforms."""

    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class VideoWatchOutcome(str, Enum):
    """Outcome of watching a video."""

    SKIPPED = "skipped"  # Quick skip < 2 seconds
    PARTIAL = "partial"  # Watched 20-80%
    FULL = "full"  # Watched 80-100%
    REWATCHED = "rewatched"  # Watched > 100%


@dataclass
class WatchResult:
    """Result of watching a video/reel."""

    success: bool
    outcome: VideoWatchOutcome
    watch_duration: float  # seconds
    video_duration: float | None  # seconds, if known
    completion_rate: float  # 0.0 - 2.0+
    replays: int = 0
    error: str | None = None


@dataclass
class SwipeResult:
    """Result of a swipe gesture."""

    success: bool
    direction: str
    duration_ms: int
    distance_px: int
    error: str | None = None


@dataclass
class BioClickResult:
    """Result of clicking a bio link."""

    success: bool
    target_url: str | None = None
    dwell_time: float = 0.0
    error: str | None = None


@dataclass
class StoryViewResult:
    """Result of viewing stories."""

    success: bool
    stories_viewed: int = 0
    link_clicked: bool = False
    total_duration: float = 0.0
    error: str | None = None


@dataclass
class SessionResult:
    """Result of a full automation session."""

    success: bool
    platform: SocialPlatform
    start_time: datetime
    end_time: datetime
    videos_watched: int = 0
    bio_links_clicked: int = 0
    story_links_clicked: int = 0
    profiles_visited: int = 0
    errors: list[str] = field(default_factory=list)
    watch_results: list[WatchResult] = field(default_factory=list)


@dataclass
class TouchPoint:
    """A single touch point in a gesture."""

    x: float
    y: float
    t: float  # time offset in ms from start
    pressure: float = 0.5


@dataclass
class SwipeGesture:
    """A complete swipe gesture with touch points."""

    points: list[TouchPoint]
    duration_ms: int
    direction: Literal["up", "down", "left", "right"]


class SocialMediaAutomation(ABC):
    """Abstract base class for social media automation.

    Provides common functionality for TikTok and Instagram plugins:
    - Swipe gesture generation with natural curves
    - Rate limiting integration
    - Coherence engine integration
    - In-app WebView simulation

    Subclasses must implement platform-specific methods.
    """

    name: str = "social_media"
    platform: SocialPlatform

    def __init__(
        self,
        coherence_engine: CoherenceEngine | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize social media automation.

        Args:
            coherence_engine: Optional coherence engine (uses global if None)
            rate_limiter: Optional rate limiter (uses global if None)
        """
        self.coherence_engine = coherence_engine or get_coherence_engine()
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self._session_state: SessionState | None = None

    def _create_session(self, persona: UserPersona | None = None) -> SessionState:
        """Create a coherent session for this automation."""
        # Default to SCROLLER or CONTENT_CONSUMER for video platforms
        if persona is None:
            persona = random.choice([
                UserPersona.SCANNER,  # Fast browsing
                UserPersona.CASUAL,   # Relaxed viewing
            ])

        self._session_state = self.coherence_engine.create_session(persona=persona)
        logger.info(
            "[SESSION_CREATE] New automation session started",
            platform=self.platform.value if hasattr(self, 'platform') else "unknown",
            persona=persona.value,
            session_id=self._session_state.session_id,
        )
        return self._session_state

    async def _random_delay(
        self,
        min_s: float = 0.5,
        max_s: float = 2.0,
        use_modifiers: bool = True,
    ) -> None:
        """Wait for a random duration, optionally modified by coherence state."""
        base_delay = random.uniform(min_s, max_s)
        modifier_applied = 1.0

        if use_modifiers and self._session_state:
            modifiers = self.coherence_engine.get_behavior_modifiers(self._session_state)
            modifier_applied = modifiers.get("dwell_time_factor", 1.0)
            base_delay *= modifier_applied

        logger.debug(
            "[DELAY] Waiting between actions",
            delay_seconds=round(base_delay, 2),
            modifier=round(modifier_applied, 2),
            range_min=min_s,
            range_max=max_s,
        )
        await asyncio.sleep(base_delay)

    def _generate_swipe_points(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        duration_ms: int,
        num_points: int = 20,
    ) -> list[TouchPoint]:
        """Generate natural swipe gesture points using bezier curves.

        Args:
            start: Starting (x, y) coordinates
            end: Ending (x, y) coordinates
            duration_ms: Swipe duration in milliseconds
            num_points: Number of intermediate points

        Returns:
            List of TouchPoints forming the gesture
        """
        points = []
        start_x, start_y = start
        end_x, end_y = end

        # Calculate control points for bezier curve
        # Add slight lateral drift for natural feel
        mid_x = (start_x + end_x) / 2 + random.uniform(-15, 15)
        mid_y = (start_y + end_y) / 2

        # Control points for cubic bezier
        cp1_x = start_x + random.uniform(-5, 5)
        cp1_y = start_y + (end_y - start_y) * 0.3
        cp2_x = end_x + random.uniform(-5, 5)
        cp2_y = end_y - (end_y - start_y) * 0.3

        for i in range(num_points + 1):
            t = i / num_points

            # Cubic bezier formula
            x = (
                (1 - t) ** 3 * start_x
                + 3 * (1 - t) ** 2 * t * cp1_x
                + 3 * (1 - t) * t ** 2 * cp2_x
                + t ** 3 * end_x
            )
            y = (
                (1 - t) ** 3 * start_y
                + 3 * (1 - t) ** 2 * t * cp1_y
                + 3 * (1 - t) * t ** 2 * cp2_y
                + t ** 3 * end_y
            )

            # Non-linear time progression (accelerate, plateau, decelerate)
            # Using easeInOutQuad
            if t < 0.5:
                time_t = 2 * t * t
            else:
                time_t = 1 - (-2 * t + 2) ** 2 / 2

            time_ms = time_t * duration_ms

            # Variable pressure (higher at start and end)
            pressure = 0.4 + 0.2 * abs(2 * t - 1)

            points.append(TouchPoint(
                x=x + random.uniform(-1, 1),  # Micro jitter
                y=y + random.uniform(-1, 1),
                t=time_ms,
                pressure=pressure,
            ))

        return points

    def generate_swipe(
        self,
        viewport_width: int,
        viewport_height: int,
        direction: Literal["up", "down", "left", "right"] = "up",
        intensity: Literal["flick", "deliberate", "slow"] = "flick",
    ) -> SwipeGesture:
        """Generate a natural swipe gesture.

        Args:
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            direction: Swipe direction
            intensity: Swipe speed/force

        Returns:
            SwipeGesture with touch points
        """
        # Duration based on intensity
        duration_ranges = {
            "flick": (150, 280),
            "deliberate": (300, 500),
            "slow": (500, 800),
        }
        duration_ms = random.randint(*duration_ranges[intensity])

        # Calculate start and end points based on direction
        if direction == "up":
            start_x = viewport_width * random.uniform(0.4, 0.6)
            start_y = viewport_height * random.uniform(0.7, 0.85)
            end_x = start_x + random.uniform(-20, 20)
            end_y = viewport_height * random.uniform(0.15, 0.3)
            distance = abs(start_y - end_y)
        elif direction == "down":
            start_x = viewport_width * random.uniform(0.4, 0.6)
            start_y = viewport_height * random.uniform(0.2, 0.35)
            end_x = start_x + random.uniform(-20, 20)
            end_y = viewport_height * random.uniform(0.7, 0.85)
            distance = abs(end_y - start_y)
        elif direction == "left":
            start_x = viewport_width * random.uniform(0.7, 0.9)
            start_y = viewport_height * random.uniform(0.4, 0.6)
            end_x = viewport_width * random.uniform(0.1, 0.3)
            end_y = start_y + random.uniform(-20, 20)
            distance = abs(start_x - end_x)
        else:  # right
            start_x = viewport_width * random.uniform(0.1, 0.3)
            start_y = viewport_height * random.uniform(0.4, 0.6)
            end_x = viewport_width * random.uniform(0.7, 0.9)
            end_y = start_y + random.uniform(-20, 20)
            distance = abs(end_x - start_x)

        points = self._generate_swipe_points(
            start=(start_x, start_y),
            end=(end_x, end_y),
            duration_ms=duration_ms,
        )

        logger.debug(
            "[SWIPE_GENERATE] Generated swipe gesture",
            direction=direction,
            intensity=intensity,
            duration_ms=duration_ms,
            distance_px=int(distance),
            start_pos=f"({int(start_x)}, {int(start_y)})",
            end_pos=f"({int(end_x)}, {int(end_y)})",
            num_points=len(points),
        )

        return SwipeGesture(
            points=points,
            duration_ms=duration_ms,
            direction=direction,
        )

    async def execute_swipe(
        self,
        page: Any,
        gesture: SwipeGesture,
    ) -> SwipeResult:
        """Execute a swipe gesture on the page.

        Args:
            page: Browser page object
            gesture: SwipeGesture to execute

        Returns:
            SwipeResult
        """
        try:
            if not gesture.points:
                return SwipeResult(
                    success=False,
                    direction=gesture.direction,
                    duration_ms=gesture.duration_ms,
                    distance_px=0,
                    error="No points in gesture",
                )

            # Start touch
            start_point = gesture.points[0]
            await page.touchscreen.tap(start_point.x, start_point.y)

            # Move through points
            last_time = 0.0
            for point in gesture.points[1:]:
                wait_time = (point.t - last_time) / 1000  # Convert to seconds
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                await page.mouse.move(point.x, point.y)
                last_time = point.t

            # Calculate distance
            end_point = gesture.points[-1]
            distance = int(((end_point.x - start_point.x) ** 2 +
                           (end_point.y - start_point.y) ** 2) ** 0.5)

            # Record action in coherence engine
            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "swipe")

            logger.info(
                "[SWIPE_EXECUTE] Swipe gesture completed successfully",
                direction=gesture.direction,
                duration_ms=gesture.duration_ms,
                distance_px=distance,
            )

            return SwipeResult(
                success=True,
                direction=gesture.direction,
                duration_ms=gesture.duration_ms,
                distance_px=distance,
            )

        except Exception as e:
            logger.error(
                "[SWIPE_EXECUTE] Swipe gesture failed",
                direction=gesture.direction,
                duration_ms=gesture.duration_ms,
                error=str(e),
            )
            return SwipeResult(
                success=False,
                direction=gesture.direction,
                duration_ms=gesture.duration_ms,
                distance_px=0,
                error=str(e),
            )

    async def _safe_click(
        self,
        page: Any,
        selector: str,
        timeout: int = 5000,
        use_xpath: bool = False,
    ) -> bool:
        """Safely click an element.

        Args:
            page: Browser page object
            selector: CSS or XPath selector
            timeout: Click timeout in ms
            use_xpath: If True, treat selector as XPath

        Returns:
            True if click succeeded
        """
        try:
            if use_xpath:
                element = page.locator(f"xpath={selector}")
            else:
                element = page.locator(selector)

            await element.click(timeout=timeout)

            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "click")

            logger.debug(
                "[CLICK] Element clicked successfully",
                selector=selector[:50] + "..." if len(selector) > 50 else selector,
                timeout_ms=timeout,
            )
            return True
        except Exception as e:
            logger.warning(
                "[CLICK] Failed to click element",
                selector=selector[:50] + "..." if len(selector) > 50 else selector,
                error=str(e),
            )
            return False

    async def _wait_for_navigation(
        self,
        page: Any,
        timeout: int = 10000,
    ) -> bool:
        """Wait for page navigation to complete."""
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=timeout)
            logger.debug(
                "[NAVIGATION] Page loaded successfully",
                timeout_ms=timeout,
            )
            return True
        except Exception as e:
            logger.warning(
                "[NAVIGATION] Navigation timeout or error",
                timeout_ms=timeout,
                error=str(e),
            )
            return False

    def _determine_watch_outcome(
        self,
        watch_duration: float,
        video_duration: float | None,
    ) -> VideoWatchOutcome:
        """Determine the watch outcome based on duration."""
        if video_duration is None:
            # Unknown video duration, estimate based on watch time
            if watch_duration < 2.0:
                outcome = VideoWatchOutcome.SKIPPED
            elif watch_duration < 10.0:
                outcome = VideoWatchOutcome.PARTIAL
            else:
                outcome = VideoWatchOutcome.FULL

            logger.debug(
                "[WATCH_OUTCOME] Determined watch outcome (unknown duration)",
                watch_duration_s=round(watch_duration, 2),
                outcome=outcome.value,
            )
            return outcome

        completion = watch_duration / video_duration

        if completion < 0.2:
            outcome = VideoWatchOutcome.SKIPPED
        elif completion < 0.8:
            outcome = VideoWatchOutcome.PARTIAL
        elif completion <= 1.1:
            outcome = VideoWatchOutcome.FULL
        else:
            outcome = VideoWatchOutcome.REWATCHED

        logger.debug(
            "[WATCH_OUTCOME] Determined watch outcome",
            watch_duration_s=round(watch_duration, 2),
            video_duration_s=round(video_duration, 2),
            completion_rate=round(completion * 100, 1),
            outcome=outcome.value,
        )
        return outcome

    @abstractmethod
    async def watch_video(
        self,
        page: Any,
        duration: float | None = None,
    ) -> WatchResult:
        """Watch the current video/reel.

        Args:
            page: Browser page object
            duration: Optional forced watch duration

        Returns:
            WatchResult
        """
        pass

    @abstractmethod
    async def swipe_to_next(self, page: Any) -> SwipeResult:
        """Swipe to the next video/reel.

        Args:
            page: Browser page object

        Returns:
            SwipeResult
        """
        pass

    @abstractmethod
    async def click_bio_link(
        self,
        page: Any,
        username: str | None = None,
    ) -> BioClickResult:
        """Click the bio link on a profile.

        Args:
            page: Browser page object
            username: Optional username to navigate to first

        Returns:
            BioClickResult
        """
        pass

    @abstractmethod
    async def run(
        self,
        page: Any,
        url: str | None = None,
    ) -> SessionResult:
        """Run the full automation sequence.

        Args:
            page: Browser page object
            url: Optional starting URL

        Returns:
            SessionResult
        """
        pass
