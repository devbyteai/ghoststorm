"""Instagram Automation Plugin.

Provides human-like automation for Instagram including:
- Reels watching with natural scroll patterns
- Story viewing and link clicking
- Profile visits and bio link clicking
- In-app WebView simulation for external links

Designed to avoid detection by mimicking real user behavior.
"""

from __future__ import annotations

import asyncio
import contextlib
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

import structlog

from ghoststorm.plugins.automation.base import (
    BioClickResult,
    SessionResult,
    SocialMediaAutomation,
    SocialPlatform,
    StoryViewResult,
    SwipeResult,
    VideoWatchOutcome,
    WatchResult,
)
from ghoststorm.plugins.automation.social_media_behavior import (
    InAppBrowserBehavior,
    StoryWatchBehavior,
    UserInterest,
    VideoWatchBehavior,
)
from ghoststorm.plugins.automation.view_tracking import (
    get_view_tracker,
)

if TYPE_CHECKING:
    from ghoststorm.plugins.behavior.coherence_engine import (
        CoherenceEngine,
    )
    from ghoststorm.plugins.network.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)


class InstagramAction(Enum):
    """Instagram automation actions."""

    WATCH_REEL = "watch_reel"
    VIEW_STORY = "view_story"
    CLICK_STORY_LINK = "click_story_link"
    CLICK_BIO_LINK = "click_bio_link"
    SCROLL_REELS = "scroll_reels"
    VISIT_PROFILE = "visit_profile"
    NAVIGATE_TO_REELS = "navigate_to_reels"
    LIKE_REEL = "like_reel"
    SAVE_REEL = "save_reel"


@dataclass
class InstagramSelectors:
    """Selectors for Instagram mobile web UI elements.

    Note: These target the mobile web version (instagram.com).
    Selectors may need updates if Instagram changes their UI.
    """

    # Reels container
    reel_container: str = "[data-testid='reels-viewer']"
    reel_video: str = "video"
    reel_wrapper: str = "article"

    # Engagement buttons
    like_button: str = "[aria-label='Like']"
    comment_button: str = "[aria-label='Comment']"
    share_button: str = "[aria-label='Share Post']"
    save_button: str = "[aria-label='Save']"

    # Story elements
    story_container: str = "[data-testid='story-viewer']"
    story_ring: str = "[data-testid='user-avatar']"
    story_link_sticker: str = "[data-testid='story-link-sticker']"
    story_next_area: str = ".story-next"
    story_prev_area: str = ".story-prev"
    story_close_button: str = "[aria-label='Close']"
    story_progress_bar: str = ".story-progress"

    # Profile elements
    profile_link: str = "header a[href*='/']"
    profile_username: str = "header h2"
    profile_bio_link: str = "[data-testid='bio-link']"
    profile_link_tree: str = "a[href*='linktr.ee'], a[href*='linkin.bio']"
    follow_button: str = "[data-testid='follow-button']"

    # Navigation
    home_tab: str = "[aria-label='Home']"
    reels_tab: str = "[aria-label='Reels']"
    explore_tab: str = "[aria-label='Explore']"
    profile_tab: str = "[aria-label='Profile']"

    # Caption and audio
    caption_text: str = "[data-testid='post-content'] span"
    audio_info: str = "[data-testid='audio-attribution']"

    # Loading
    loading_spinner: str = "[aria-label='Loading']"


@dataclass
class InstagramConfig:
    """Configuration for Instagram automation."""

    # Target URL or username
    target_url: str = ""
    target_username: str = ""
    target_reel_urls: list[str] = field(default_factory=list)

    # Reel watching behavior
    min_reel_watch_percent: float = 0.4
    max_reel_watch_percent: float = 1.2
    reel_skip_probability: float = 0.35

    # Story behavior
    story_skip_probability: float = 0.20
    story_link_click_probability: float = 0.25
    min_story_view_seconds: float = 2.0
    max_story_view_seconds: float = 8.0

    # Bio link clicking
    bio_link_click_probability: float = 0.20
    profile_visit_probability: float = 0.12

    # Engagement (set to 0 for passive watching)
    like_probability: float = 0.0
    save_probability: float = 0.0
    comment_probability: float = 0.0

    # Session parameters
    reels_per_session: tuple[int, int] = (5, 20)
    stories_per_profile: tuple[int, int] = (1, 5)

    # In-app browser simulation
    simulate_inapp_browser: bool = True
    inapp_dwell_time: tuple[float, float] = (10.0, 60.0)

    # Timing
    swipe_speed_range: tuple[int, int] = (300, 700)  # ms
    page_load_delay: tuple[float, float] = (2.0, 5.0)

    # Rate limits (per hour)
    max_story_views: int = 80
    max_reel_views: int = 100
    max_profile_visits: int = 60
    max_bio_clicks: int = 20
    max_story_link_clicks: int = 15

    # Mobile viewport
    viewport_width: int = 390
    viewport_height: int = 844


# Instagram WebView JavaScript interface injection
INSTAGRAM_JS_INTERFACE = """
window.InstagramInterface = {
    requestClose: function() {
        console.log('Instagram close requested');
    },
    getAppVersion: function() {
        return '312.0.0.38.113';
    },
    getDeviceID: function() {
        return window._igDeviceId || '';
    },
    trackEvent: function(event, params) {
        console.log('Instagram track:', event, params);
    },
    onReady: function() {
        console.log('Instagram interface ready');
    },
    getSharedData: function() {
        return window._sharedData || {};
    }
};

// Set device ID
window._igDeviceId = '{device_id}';
window._igAppId = '936619743392459';
"""

# Instagram-specific headers for WebView
INSTAGRAM_HEADERS = {
    "X-IG-App-ID": "936619743392459",
    "X-IG-Device-ID": "",  # Filled per session
    "X-IG-Connection-Type": "WIFI",
    "X-IG-Capabilities": "3brTvw8=",
    "X-IG-Band-Speed-KB-s": "4000",
}


@dataclass
class LinkClickResult:
    """Result of clicking a story or bio link."""

    success: bool
    link_type: Literal["story", "bio"]
    target_url: str | None = None
    dwell_time: float = 0.0
    error: str | None = None


class InstagramAutomation(SocialMediaAutomation):
    """Instagram automation plugin.

    Simulates human-like Instagram browsing behavior for:
    - Reels watching with natural scroll patterns
    - Story viewing and link clicking
    - Profile visits and bio link clicks
    - In-app WebView simulation

    Usage:
        automation = InstagramAutomation(config=InstagramConfig(
            target_username="someuser",
            reels_per_session=(5, 15),
        ))

        async with browser.new_context() as context:
            page = await context.new_page()
            result = await automation.run(page)
    """

    name = "instagram"
    platform = SocialPlatform.INSTAGRAM

    def __init__(
        self,
        config: InstagramConfig | None = None,
        selectors: InstagramSelectors | None = None,
        coherence_engine: CoherenceEngine | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize Instagram automation.

        Args:
            config: Instagram automation configuration
            selectors: UI element selectors
            coherence_engine: Behavior coherence engine
            rate_limiter: Rate limiting engine
        """
        super().__init__(coherence_engine, rate_limiter)
        self.config = config or InstagramConfig()
        self.selectors = selectors or InstagramSelectors()

        # Initialize behavior models
        self.watch_behavior = VideoWatchBehavior(
            platform="instagram",
            interest_level=UserInterest.MEDIUM,
        )
        self.story_behavior = StoryWatchBehavior()
        self.inapp_behavior = InAppBrowserBehavior(platform="instagram")

        # Session tracking
        self._reels_watched = 0
        self._stories_viewed = 0
        self._profiles_visited = 0
        self._bio_clicks = 0
        self._story_link_clicks = 0

        # Device ID for this session
        self._device_id = self._generate_device_id()

    def _generate_device_id(self) -> str:
        """Generate a realistic Instagram device ID."""
        import hashlib
        import uuid

        return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

    async def _setup_context(self, page: Any) -> None:
        """Setup page context for Instagram automation.

        Injects JavaScript interface and configures headers.
        """
        try:
            # Inject Instagram JS interface
            js_code = INSTAGRAM_JS_INTERFACE.replace("{device_id}", self._device_id)
            await page.add_init_script(js_code)

            # Set mobile viewport
            await page.set_viewport_size(
                {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }
            )

            # Set extra headers
            headers = INSTAGRAM_HEADERS.copy()
            headers["X-IG-Device-ID"] = self._device_id
            await page.context.set_extra_http_headers(headers)

            logger.info(
                "[INSTAGRAM_SETUP] Context configured successfully",
                device_id=self._device_id,
                viewport_width=self.config.viewport_width,
                viewport_height=self.config.viewport_height,
                js_interface_injected=True,
            )
        except Exception as e:
            logger.error(
                "[INSTAGRAM_SETUP] Failed to configure context",
                error=str(e),
            )

    async def _get_video_duration(self, page: Any) -> float | None:
        """Try to get the current reel video duration."""
        try:
            video = page.locator(self.selectors.reel_video).first
            duration = await video.evaluate("el => el.duration")
            return float(duration) if duration else None
        except Exception:
            return None

    async def watch_video(
        self,
        page: Any,
        duration: float | None = None,
    ) -> WatchResult:
        """Watch the current reel with human-like behavior.

        Alias for watch_reel for base class compatibility.
        """
        return await self.watch_reel(page, duration)

    async def watch_reel(
        self,
        page: Any,
        duration: float | None = None,
    ) -> WatchResult:
        """Watch the current reel with human-like behavior.

        Args:
            page: Browser page object
            duration: Optional forced watch duration

        Returns:
            WatchResult with watch statistics
        """
        try:
            # Get video duration
            video_duration = await self._get_video_duration(page)

            # Generate watch duration if not specified
            if duration is None:
                watch_time, outcome_str = self.watch_behavior.generate_watch_duration(
                    video_duration=video_duration,
                    content_interest=random.uniform(0.3, 0.7),
                )
            else:
                watch_time = duration
                outcome_str = "full"

            # Apply coherence modifiers
            if self._session_state:
                modifiers = self.coherence_engine.get_behavior_modifiers(self._session_state)
                watch_time *= modifiers.get("dwell_time_factor", 1.0)

            logger.info(
                "[INSTAGRAM_WATCH] Starting reel watch",
                reel_number=self._reels_watched + 1,
                planned_watch_time_s=round(watch_time, 2),
                video_duration_s=round(video_duration, 2) if video_duration else "unknown",
                expected_outcome=outcome_str,
            )

            # Actually wait (simulate watching)
            await asyncio.sleep(watch_time)

            # Calculate completion rate
            completion_rate = watch_time / video_duration if video_duration else 1.0

            # Determine outcome
            outcome = self._determine_watch_outcome(watch_time, video_duration)

            # Record in behavior model
            self.watch_behavior.record_video_watched()
            self._reels_watched += 1

            # Record action
            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "watch")

            logger.info(
                "[INSTAGRAM_WATCH] Reel watch completed",
                reel_number=self._reels_watched,
                actual_watch_time_s=round(watch_time, 2),
                completion_rate_pct=round(completion_rate * 100, 1),
                outcome=outcome.value,
            )

            return WatchResult(
                success=True,
                outcome=outcome,
                watch_duration=watch_time,
                video_duration=video_duration,
                completion_rate=completion_rate,
                replays=int(completion_rate) if completion_rate > 1 else 0,
            )

        except Exception as e:
            logger.error(
                "[INSTAGRAM_WATCH] Reel watch failed",
                reel_number=self._reels_watched + 1,
                error=str(e),
            )
            return WatchResult(
                success=False,
                outcome=VideoWatchOutcome.SKIPPED,
                watch_duration=0.0,
                video_duration=None,
                completion_rate=0.0,
                error=str(e),
            )

    async def swipe_to_next(self, page: Any) -> SwipeResult:
        """Swipe up to go to the next reel.

        Args:
            page: Browser page object

        Returns:
            SwipeResult
        """
        # Generate scroll timing
        pause, intensity = self.watch_behavior.generate_scroll_timing()

        # Wait before swiping
        await asyncio.sleep(pause)

        # Generate swipe gesture
        gesture = self.generate_swipe(
            viewport_width=self.config.viewport_width,
            viewport_height=self.config.viewport_height,
            direction="up",
            intensity=intensity,
        )

        # Execute swipe
        result = await self.execute_swipe(page, gesture)

        # Wait for reel to load
        if result.success:
            await self._random_delay(0.5, 1.5)

        return result

    async def view_stories(
        self,
        page: Any,
        username: str | None = None,
        max_stories: int | None = None,
    ) -> StoryViewResult:
        """View stories from a profile.

        Args:
            page: Browser page object
            username: Optional username to navigate to first
            max_stories: Maximum stories to view

        Returns:
            StoryViewResult
        """
        try:
            logger.info(
                "[INSTAGRAM_STORY] Starting story viewing session",
                username=username,
                max_stories=max_stories,
                stories_viewed_so_far=self._stories_viewed,
            )

            # Navigate to profile if username provided
            if username:
                profile_url = f"https://www.instagram.com/{username}/"
                await page.goto(profile_url)
                await self._wait_for_navigation(page)
                await self._random_delay(*self.config.page_load_delay)

            # Look for story ring indicator
            story_ring = page.locator(self.selectors.story_ring)
            if not await story_ring.count():
                logger.warning(
                    "[INSTAGRAM_STORY] No active stories found",
                    username=username,
                )
                return StoryViewResult(
                    success=False,
                    error="No active stories found",
                )

            # Click to open stories
            if not await self._safe_click(page, self.selectors.story_ring):
                logger.warning(
                    "[INSTAGRAM_STORY] Failed to open story viewer",
                    username=username,
                )
                return StoryViewResult(
                    success=False,
                    error="Failed to open stories",
                )

            await self._random_delay(1.0, 2.0)

            # Determine max stories
            if max_stories is None:
                max_stories = random.randint(*self.config.stories_per_profile)

            stories_viewed = 0
            link_clicked = False
            total_duration = 0.0

            for _i in range(max_stories):
                # Check for link sticker
                has_link = await page.locator(self.selectors.story_link_sticker).count() > 0

                # Generate view behavior
                view_duration, action = self.story_behavior.generate_view_duration(
                    has_link=has_link,
                )

                # Watch the story
                await asyncio.sleep(view_duration)
                total_duration += view_duration
                stories_viewed += 1
                self._stories_viewed += 1

                # Handle link click
                if action == "link_clicked" and has_link:
                    link_result = await self.click_story_link(page)
                    if link_result.success:
                        link_clicked = True
                        self._story_link_clicks += 1

                # Decide how to advance
                if self.story_behavior.should_tap_back() and stories_viewed > 1:
                    # Tap back
                    await self._safe_click(page, self.selectors.story_prev_area)
                    await self._random_delay(0.5, 1.5)

                elif self.story_behavior.should_tap_forward():
                    # Tap forward
                    await self._safe_click(page, self.selectors.story_next_area)
                else:
                    # Wait for auto-advance
                    await asyncio.sleep(0.5)

                # Check if stories ended (redirected back to profile or home)
                if "stories" not in page.url.lower():
                    break

            # Close stories if still open
            with contextlib.suppress(Exception):
                await self._safe_click(page, self.selectors.story_close_button)

            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "view_stories")

            logger.info(
                "[INSTAGRAM_STORY] Story viewing completed",
                username=username,
                stories_viewed=stories_viewed,
                link_clicked=link_clicked,
                total_duration_s=round(total_duration, 2),
                total_stories_session=self._stories_viewed,
            )

            return StoryViewResult(
                success=True,
                stories_viewed=stories_viewed,
                link_clicked=link_clicked,
                total_duration=total_duration,
            )

        except Exception as e:
            logger.error(
                "[INSTAGRAM_STORY] Story viewing failed",
                username=username,
                error=str(e),
            )
            return StoryViewResult(
                success=False,
                error=str(e),
            )

    async def click_story_link(self, page: Any) -> LinkClickResult:
        """Click a story link sticker.

        Args:
            page: Browser page object

        Returns:
            LinkClickResult
        """
        try:
            logger.info(
                "[INSTAGRAM_STORY_LINK] Attempting to click story link sticker",
                story_link_clicks_so_far=self._story_link_clicks,
            )

            link_sticker = page.locator(self.selectors.story_link_sticker)
            if not await link_sticker.count():
                logger.warning(
                    "[INSTAGRAM_STORY_LINK] No link sticker found in story",
                )
                return LinkClickResult(
                    success=False,
                    link_type="story",
                    error="No link sticker found",
                )

            # Get link URL if possible
            target_url = await link_sticker.get_attribute("href")
            logger.debug(
                "[INSTAGRAM_STORY_LINK] Found link sticker",
                target_url=target_url,
            )

            # Click the sticker
            if await self._safe_click(page, self.selectors.story_link_sticker):
                # Wait for in-app browser to load
                await self._wait_for_navigation(page, timeout=15000)

                # Simulate in-app browser behavior
                result = await self._simulate_inapp_browser(page, "story")

                logger.info(
                    "[INSTAGRAM_STORY_LINK] Story link click completed",
                    target_url=target_url,
                    dwell_time_s=round(result.get("dwell_time", 0.0), 2),
                )

                return LinkClickResult(
                    success=True,
                    link_type="story",
                    target_url=target_url,
                    dwell_time=result.get("dwell_time", 0.0),
                )

            logger.warning(
                "[INSTAGRAM_STORY_LINK] Failed to click link sticker element",
            )
            return LinkClickResult(
                success=False,
                link_type="story",
                error="Failed to click link sticker",
            )

        except Exception as e:
            logger.error(
                "[INSTAGRAM_STORY_LINK] Story link click failed",
                error=str(e),
            )
            return LinkClickResult(
                success=False,
                link_type="story",
                error=str(e),
            )

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
        try:
            logger.info(
                "[INSTAGRAM_BIO_CLICK] Starting bio link click sequence",
                username=username,
                bio_clicks_so_far=self._bio_clicks,
            )

            # Navigate to profile if username provided
            if username:
                profile_url = f"https://www.instagram.com/{username}/"
                logger.debug(
                    "[INSTAGRAM_BIO_CLICK] Navigating to profile first",
                    profile_url=profile_url,
                )
                await page.goto(profile_url)
                await self._wait_for_navigation(page)
                await self._random_delay(*self.config.page_load_delay)

            # Look for bio link (could be direct or link tree)
            bio_link = page.locator(self.selectors.profile_bio_link)
            if not await bio_link.count():
                # Try link tree style links
                bio_link = page.locator(self.selectors.profile_link_tree)
                if not await bio_link.count():
                    logger.warning(
                        "[INSTAGRAM_BIO_CLICK] No bio link found on profile",
                        username=username,
                    )
                    return BioClickResult(
                        success=False,
                        error="No bio link found",
                    )

            # Get link URL
            target_url = await bio_link.first.get_attribute("href")
            logger.debug(
                "[INSTAGRAM_BIO_CLICK] Found bio link",
                target_url=target_url,
            )

            # Click the link
            if await self._safe_click(page, self.selectors.profile_bio_link):
                self._bio_clicks += 1

                # Simulate in-app browser behavior
                result = await self._simulate_inapp_browser(page, "bio")

                if self._session_state:
                    self.coherence_engine.record_action(self._session_state, "click", target_url)

                logger.info(
                    "[INSTAGRAM_BIO_CLICK] Bio link click completed",
                    target_url=target_url,
                    dwell_time_s=round(result.get("dwell_time", 0.0), 2),
                    total_bio_clicks=self._bio_clicks,
                )

                return BioClickResult(
                    success=True,
                    target_url=target_url,
                    dwell_time=result.get("dwell_time", 0.0),
                )

            logger.warning(
                "[INSTAGRAM_BIO_CLICK] Failed to click bio link element",
            )
            return BioClickResult(
                success=False,
                error="Failed to click bio link",
            )

        except Exception as e:
            logger.error(
                "[INSTAGRAM_BIO_CLICK] Bio link click failed",
                username=username,
                error=str(e),
            )
            return BioClickResult(
                success=False,
                error=str(e),
            )

    def _extract_reel_id(self, url: str) -> str:
        """Extract reel ID from Instagram URL.

        Args:
            url: Instagram reel URL

        Returns:
            Reel ID string
        """
        # Handle various Instagram reel URL formats:
        # https://www.instagram.com/reel/ABC123xyz/
        # https://www.instagram.com/reels/ABC123xyz/
        # https://www.instagram.com/p/ABC123xyz/
        if "/reel/" in url:
            reel_id = url.split("/reel/")[1].split("/")[0].split("?")[0]
        elif "/reels/" in url:
            reel_id = url.split("/reels/")[1].split("/")[0].split("?")[0]
        elif "/p/" in url:
            reel_id = url.split("/p/")[1].split("/")[0].split("?")[0]
        else:
            # Fallback - use hash of URL
            import hashlib

            reel_id = hashlib.md5(url.encode()).hexdigest()[:16]

        return reel_id

    async def watch_direct_reel(
        self,
        page: Any,
        reel_url: str,
        watch_duration: float | None = None,
        proxy_id: str = "",
        fingerprint_id: str = "",
    ) -> WatchResult:
        """Watch a specific Instagram Reel URL directly.

        This method navigates directly to a reel URL and watches it,
        which is useful for boosting views on specific content.

        Args:
            page: Browser page object
            reel_url: Full Instagram reel URL
            watch_duration: Optional forced duration (uses behavior model if None)
            proxy_id: Proxy identifier for view tracking
            fingerprint_id: Fingerprint identifier for view tracking

        Returns:
            WatchResult with watch statistics
        """
        reel_id = self._extract_reel_id(reel_url)
        view_tracker = get_view_tracker()

        logger.info(
            "[INSTAGRAM_DIRECT] Starting direct reel watch",
            reel_url=reel_url[:60] + "...",
            reel_id=reel_id,
            proxy_id=proxy_id[:8] + "..." if proxy_id else "none",
            fingerprint_id=fingerprint_id[:8] + "..." if fingerprint_id else "none",
        )

        # Check if we can view this reel (rate limiting)
        can_view, reason = view_tracker.can_view(
            video_id=reel_id,
            platform="instagram",
            proxy_id=proxy_id,
            fingerprint_id=fingerprint_id,
        )

        if not can_view:
            logger.warning(
                "[INSTAGRAM_DIRECT] View blocked by rate limiter",
                reel_id=reel_id,
                reason=reason,
            )
            return WatchResult(
                success=False,
                outcome=VideoWatchOutcome.SKIPPED,
                watch_duration=0.0,
                video_duration=None,
                completion_rate=0.0,
                error=f"Rate limited: {reason}",
            )

        try:
            # Navigate to the reel
            await page.goto(reel_url)
            await self._wait_for_navigation(page)
            await self._random_delay(*self.config.page_load_delay)

            logger.debug(
                "[INSTAGRAM_DIRECT] Reel page loaded",
                current_url=page.url,
                reel_id=reel_id,
            )

            # Get video duration
            video_duration = await self._get_video_duration(page)

            # Generate watch duration based on behavior model
            if watch_duration is None:
                watch_time, _outcome_str = self.watch_behavior.generate_watch_duration(
                    video_duration=video_duration,
                    content_interest=random.uniform(0.5, 0.9),  # Higher interest for target reels
                )
                # Ensure minimum watch time for view to count (3 seconds for Instagram)
                min_watch = view_tracker.get_minimum_watch_time("instagram")
                watch_time = max(watch_time, min_watch + random.uniform(0.5, 2.0))
            else:
                watch_time = watch_duration

            # Apply coherence modifiers
            if self._session_state:
                modifiers = self.coherence_engine.get_behavior_modifiers(self._session_state)
                watch_time *= modifiers.get("dwell_time_factor", 1.0)

            logger.info(
                "[INSTAGRAM_DIRECT] Watching reel",
                reel_id=reel_id,
                planned_watch_time_s=round(watch_time, 2),
                video_duration_s=round(video_duration, 2) if video_duration else "unknown",
                min_for_view_s=view_tracker.get_minimum_watch_time("instagram"),
            )

            # Actually watch (wait)
            await asyncio.sleep(watch_time)

            # Calculate completion
            completion_rate = watch_time / video_duration if video_duration else 1.0
            outcome = self._determine_watch_outcome(watch_time, video_duration)

            # Record the view
            view_counted = view_tracker.record_view(
                video_id=reel_id,
                platform="instagram",
                proxy_id=proxy_id,
                fingerprint_id=fingerprint_id,
                watch_duration=watch_time,
            )

            # Record in behavior model
            self.watch_behavior.record_video_watched()
            self._reels_watched += 1

            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "watch")

            logger.info(
                "[INSTAGRAM_DIRECT] Direct reel watch completed",
                reel_id=reel_id,
                watch_duration_s=round(watch_time, 2),
                completion_rate_pct=round(completion_rate * 100, 1),
                outcome=outcome.value,
                view_counted=view_counted,
            )

            return WatchResult(
                success=True,
                outcome=outcome,
                watch_duration=watch_time,
                video_duration=video_duration,
                completion_rate=completion_rate,
                replays=int(completion_rate) if completion_rate > 1 else 0,
            )

        except Exception as e:
            logger.error(
                "[INSTAGRAM_DIRECT] Direct reel watch failed",
                reel_url=reel_url[:60] + "...",
                reel_id=reel_id,
                error=str(e),
            )
            return WatchResult(
                success=False,
                outcome=VideoWatchOutcome.SKIPPED,
                watch_duration=0.0,
                video_duration=None,
                completion_rate=0.0,
                error=str(e),
            )

    async def watch_direct_reels(
        self,
        page: Any,
        reel_urls: list[str] | None = None,
        delay_between: tuple[float, float] = (5.0, 15.0),
        proxy_id: str = "",
        fingerprint_id: str = "",
    ) -> list[WatchResult]:
        """Watch multiple specific Instagram Reel URLs directly.

        Args:
            page: Browser page object
            reel_urls: List of reel URLs (uses config.target_reel_urls if None)
            delay_between: Min/max delay between reels
            proxy_id: Proxy identifier for view tracking
            fingerprint_id: Fingerprint identifier for view tracking

        Returns:
            List of WatchResults
        """
        # Use config if not provided
        if reel_urls is None:
            reel_urls = self.config.target_reel_urls

        if not reel_urls:
            logger.warning(
                "[INSTAGRAM_DIRECT_BATCH] No reel URLs provided",
            )
            return []

        logger.info(
            "[INSTAGRAM_DIRECT_BATCH] ========== STARTING DIRECT REEL BATCH ==========",
            total_reels=len(reel_urls),
            delay_between_min_s=delay_between[0],
            delay_between_max_s=delay_between[1],
        )

        results = []

        for idx, reel_url in enumerate(reel_urls):
            logger.info(
                "[INSTAGRAM_DIRECT_BATCH] Processing reel",
                reel_index=idx + 1,
                total_reels=len(reel_urls),
                reel_url=reel_url[:60] + "...",
            )

            result = await self.watch_direct_reel(
                page=page,
                reel_url=reel_url,
                proxy_id=proxy_id,
                fingerprint_id=fingerprint_id,
            )
            results.append(result)

            # Delay between reels (except for last)
            if idx < len(reel_urls) - 1:
                delay = random.uniform(*delay_between)
                logger.debug(
                    "[INSTAGRAM_DIRECT_BATCH] Waiting between reels",
                    delay_s=round(delay, 2),
                )
                await asyncio.sleep(delay)

        # Log batch statistics
        successful = sum(1 for r in results if r.success)
        total_watch_time = sum(r.watch_duration for r in results)

        logger.info(
            "[INSTAGRAM_DIRECT_BATCH] ========== DIRECT REEL BATCH COMPLETED ==========",
            total_reels=len(reel_urls),
            successful_watches=successful,
            failed_watches=len(results) - successful,
            total_watch_time_s=round(total_watch_time, 2),
        )

        return results

    async def _simulate_inapp_browser(
        self,
        page: Any,
        source: Literal["story", "bio"],
    ) -> dict[str, Any]:
        """Simulate Instagram in-app browser behavior.

        Args:
            page: Browser page object
            source: Where the link was clicked from

        Returns:
            Dict with simulation results
        """
        result = {"dwell_time": 0.0}

        try:
            # Wait for page load
            await self._wait_for_navigation(page, timeout=15000)

            # Generate dwell time
            dwell_time = self.inapp_behavior.generate_dwell_time()
            dwell_time = min(
                dwell_time,
                random.uniform(*self.config.inapp_dwell_time),
            )
            result["dwell_time"] = dwell_time

            # Simulate reading/scrolling
            scroll_pattern = self.inapp_behavior.generate_scroll_pattern()
            elapsed = 0.0

            for scroll_pos, pause_time in scroll_pattern[:7]:  # Limit scrolls
                try:
                    await page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                    await asyncio.sleep(min(pause_time, 2.0))
                    elapsed += pause_time
                except Exception:
                    break

                if self.inapp_behavior.should_return_to_app(elapsed):
                    break

            # Navigate back to Instagram
            await page.go_back()
            await self._random_delay(1.0, 2.0)

        except Exception as e:
            logger.warning("In-app browser simulation error", error=str(e))

        return result

    async def visit_profile(self, page: Any, username: str | None = None) -> bool:
        """Visit a profile from current context.

        Args:
            page: Browser page object
            username: Optional username to navigate to directly

        Returns:
            True if navigation succeeded
        """
        try:
            if username:
                profile_url = f"https://www.instagram.com/{username}/"
                await page.goto(profile_url)
            else:
                # Click profile link from current reel
                if not await self._safe_click(page, self.selectors.profile_link):
                    return False

            await self._wait_for_navigation(page)
            await self._random_delay(*self.config.page_load_delay)
            self._profiles_visited += 1

            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "navigate", page.url)

            return True

        except Exception as e:
            logger.warning("Failed to visit profile", error=str(e))
            return False

    async def simulate_reels_session(
        self,
        page: Any,
        target_profile: str | None = None,
        reels_to_watch: int | None = None,
    ) -> SessionResult:
        """Simulate a Reels browsing session.

        Args:
            page: Browser page object
            target_profile: Optional profile to visit during session
            reels_to_watch: Number of reels (uses config if None)

        Returns:
            SessionResult with full session statistics
        """
        start_time = datetime.now(UTC)
        session = self._create_session()
        watch_results: list[WatchResult] = []
        errors: list[str] = []

        # Determine session length
        if reels_to_watch is None:
            reels_to_watch = self.watch_behavior.generate_session_length()

        reels_to_watch = min(reels_to_watch, self.config.max_reel_views)

        logger.info(
            "[INSTAGRAM_SESSION] ========== STARTING REELS SESSION ==========",
            target_reels=reels_to_watch,
            target_profile=target_profile,
            session_id=session.session_id if session else "unknown",
            persona=session.persona.value if session else "unknown",
            config_skip_prob=self.config.reel_skip_probability,
            config_bio_click_prob=self.config.bio_link_click_probability,
            config_story_link_prob=self.config.story_link_click_probability,
        )

        bio_links_clicked = 0
        story_links_clicked = 0
        profiles_visited = 0

        try:
            # Navigate to Instagram Reels
            await page.goto("https://www.instagram.com/reels/")
            await self._wait_for_navigation(page)
            await self._random_delay(*self.config.page_load_delay)

            for i in range(reels_to_watch):
                logger.debug(
                    "[INSTAGRAM_SESSION] Processing reel iteration",
                    reel_index=i + 1,
                    total_target=reels_to_watch,
                    progress_pct=round((i / reels_to_watch) * 100, 1),
                )

                # Check for break
                if self.watch_behavior.should_take_break():
                    break_duration = self.watch_behavior.generate_break_duration()
                    logger.info(
                        "[INSTAGRAM_SESSION] Taking human break",
                        break_duration_s=round(break_duration, 2),
                        reels_watched_so_far=len(watch_results),
                    )
                    await asyncio.sleep(break_duration)

                    if self._session_state:
                        self.coherence_engine.record_break(self._session_state, break_duration)

                # Watch current reel
                watch_result = await self.watch_reel(page)
                watch_results.append(watch_result)

                if not watch_result.success:
                    errors.append(watch_result.error or "Watch failed")

                # Decide on next action
                if self.watch_behavior.should_visit_profile():
                    # Visit profile
                    if await self.visit_profile(page):
                        profiles_visited += 1

                        # Maybe view stories
                        if random.random() < 0.3:
                            story_result = await self.view_stories(page)
                            if story_result.link_clicked:
                                story_links_clicked += 1

                        # Maybe click bio link
                        if self.watch_behavior.should_click_bio():
                            bio_result = await self.click_bio_link(page)
                            if bio_result.success:
                                bio_links_clicked += 1

                        # Navigate back to Reels
                        await page.goto("https://www.instagram.com/reels/")
                        await self._random_delay(1.0, 2.0)

                # Check if should scroll back
                if self.watch_behavior.should_scroll_back() and i > 0:
                    await self.swipe_to_previous(page)
                    await self._random_delay(1.0, 3.0)
                    await self.swipe_to_next(page)

                # Swipe to next reel
                swipe_result = await self.swipe_to_next(page)
                if not swipe_result.success:
                    errors.append(swipe_result.error or "Swipe failed")

            # Visit target profile if specified
            if target_profile and await self.visit_profile(page, target_profile):
                profiles_visited += 1

                # View stories if available
                story_result = await self.view_stories(page)
                if story_result.link_clicked:
                    story_links_clicked += 1

                # Click bio link with configured probability
                if random.random() < self.config.bio_link_click_probability:
                    bio_result = await self.click_bio_link(page)
                    if bio_result.success:
                        bio_links_clicked += 1

        except Exception as e:
            errors.append(str(e))
            logger.error(
                "[INSTAGRAM_SESSION] Session error occurred",
                error=str(e),
                reels_watched_before_error=len(watch_results),
            )

        end_time = datetime.now(UTC)
        session_duration = (end_time - start_time).total_seconds()

        # End coherence session
        if self._session_state:
            self.coherence_engine.end_session(self._session_state.session_id)

        # Calculate session statistics
        successful_watches = sum(1 for w in watch_results if w.success)
        avg_watch_time = (
            sum(w.watch_duration for w in watch_results) / len(watch_results)
            if watch_results
            else 0
        )

        logger.info(
            "[INSTAGRAM_SESSION] ========== SESSION COMPLETED ==========",
            success=len(errors) == 0,
            session_duration_s=round(session_duration, 2),
            session_duration_min=round(session_duration / 60, 1),
            reels_watched=len(watch_results),
            successful_watches=successful_watches,
            avg_watch_time_s=round(avg_watch_time, 2),
            profiles_visited=profiles_visited,
            bio_links_clicked=bio_links_clicked,
            story_links_clicked=story_links_clicked,
            error_count=len(errors),
            errors=errors if errors else None,
        )

        return SessionResult(
            success=len(errors) == 0,
            platform=SocialPlatform.INSTAGRAM,
            start_time=start_time,
            end_time=end_time,
            videos_watched=len(watch_results),
            bio_links_clicked=bio_links_clicked,
            story_links_clicked=story_links_clicked,
            profiles_visited=profiles_visited,
            errors=errors,
            watch_results=watch_results,
        )

    async def swipe_to_previous(self, page: Any) -> SwipeResult:
        """Swipe down to go to the previous reel.

        Args:
            page: Browser page object

        Returns:
            SwipeResult
        """
        gesture = self.generate_swipe(
            viewport_width=self.config.viewport_width,
            viewport_height=self.config.viewport_height,
            direction="down",
            intensity="deliberate",
        )

        return await self.execute_swipe(page, gesture)

    async def run(
        self,
        page: Any,
        url: str | None = None,
        proxy_id: str = "",
        fingerprint_id: str = "",
    ) -> SessionResult:
        """Run the full Instagram automation sequence.

        Priority:
        1. If target_reel_urls are configured, watch those reels directly
        2. Otherwise, run Reels session with optional profile visit

        Args:
            page: Browser page object
            url: Optional starting URL
            proxy_id: Proxy identifier for view tracking
            fingerprint_id: Fingerprint identifier for view tracking

        Returns:
            SessionResult
        """
        logger.info(
            "[INSTAGRAM_RUN] Starting Instagram automation run",
            url=url,
            target_username=self.config.target_username,
            target_reel_urls_count=len(self.config.target_reel_urls),
            mode="direct_reels" if self.config.target_reel_urls else "reels_session",
        )

        # Setup context
        await self._setup_context(page)
        start_time = datetime.now(UTC)
        self._create_session()

        # PRIORITY 1: If target reel URLs are configured, watch them directly
        if self.config.target_reel_urls:
            logger.info(
                "[INSTAGRAM_RUN] Running in DIRECT REEL mode",
                reel_count=len(self.config.target_reel_urls),
            )

            watch_results = await self.watch_direct_reels(
                page=page,
                reel_urls=self.config.target_reel_urls,
                proxy_id=proxy_id,
                fingerprint_id=fingerprint_id,
            )

            end_time = datetime.now(UTC)

            # End coherence session
            if self._session_state:
                self.coherence_engine.end_session(self._session_state.session_id)

            errors = [r.error for r in watch_results if r.error]

            return SessionResult(
                success=len(errors) == 0,
                platform=SocialPlatform.INSTAGRAM,
                start_time=start_time,
                end_time=end_time,
                videos_watched=len(watch_results),
                bio_links_clicked=0,
                story_links_clicked=0,
                profiles_visited=0,
                errors=errors,
                watch_results=watch_results,
            )

        # PRIORITY 2: Run Reels session
        target_profile = None
        if url:
            # Extract username from URL if profile link
            if "instagram.com/" in url:
                parts = url.split("instagram.com/")[1].split("/")
                if parts and parts[0] not in ["reels", "stories", "explore"]:
                    target_profile = parts[0].split("?")[0]
                    logger.debug(
                        "[INSTAGRAM_RUN] Extracted target profile from URL",
                        target_profile=target_profile,
                    )
        elif self.config.target_username:
            target_profile = self.config.target_username

        # Run Reels session
        return await self.simulate_reels_session(
            page,
            target_profile=target_profile,
        )

    async def run_batch(
        self,
        page: Any,
        profiles: list[str],
        delay_between: tuple[float, float] = (30.0, 90.0),
    ) -> list[SessionResult]:
        """Run automation on multiple profiles.

        Args:
            page: Browser page object
            profiles: List of usernames to visit
            delay_between: Min/max delay between profiles

        Returns:
            List of SessionResults
        """
        logger.info(
            "[INSTAGRAM_BATCH] ========== STARTING BATCH RUN ==========",
            total_profiles=len(profiles),
            profiles=profiles,
            delay_between_min_s=delay_between[0],
            delay_between_max_s=delay_between[1],
        )

        results = []

        for idx, profile in enumerate(profiles):
            logger.info(
                "[INSTAGRAM_BATCH] Processing profile in batch",
                profile=profile,
                profile_index=idx + 1,
                total_profiles=len(profiles),
            )

            result = await self.simulate_reels_session(
                page,
                target_profile=profile,
                reels_to_watch=random.randint(3, 10),
            )
            results.append(result)

            if profile != profiles[-1]:
                delay = random.uniform(*delay_between)
                logger.debug(
                    "[INSTAGRAM_BATCH] Waiting between profiles",
                    delay_s=round(delay, 2),
                    next_profile=profiles[idx + 1],
                )
                await asyncio.sleep(delay)

        # Calculate batch statistics
        total_reels = sum(r.videos_watched for r in results)
        total_bio_clicks = sum(r.bio_links_clicked for r in results)
        total_story_clicks = sum(r.story_links_clicked for r in results)
        successful_sessions = sum(1 for r in results if r.success)

        logger.info(
            "[INSTAGRAM_BATCH] ========== BATCH RUN COMPLETED ==========",
            total_profiles=len(profiles),
            successful_sessions=successful_sessions,
            total_reels_watched=total_reels,
            total_bio_clicks=total_bio_clicks,
            total_story_clicks=total_story_clicks,
        )

        return results
