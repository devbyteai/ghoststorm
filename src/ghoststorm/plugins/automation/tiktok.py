"""TikTok Automation Plugin.

Provides human-like automation for TikTok including:
- For You Page (FYP) browsing with natural swipe patterns
- Video watching with realistic timing distributions
- Profile visits and bio link clicking
- In-app WebView simulation for external links

Designed to avoid detection by mimicking real user behavior.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

from ghoststorm.plugins.automation.base import (
    BioClickResult,
    SessionResult,
    SocialMediaAutomation,
    SocialPlatform,
    SwipeResult,
    VideoWatchOutcome,
    WatchResult,
)
from ghoststorm.plugins.automation.social_media_behavior import (
    InAppBrowserBehavior,
    UserInterest,
    VideoWatchBehavior,
)
from ghoststorm.plugins.automation.view_tracking import (
    get_view_tracker,
)
from ghoststorm.plugins.behavior.coherence_engine import (
    CoherenceEngine,
)
from ghoststorm.plugins.network.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)


class TikTokAction(Enum):
    """TikTok automation actions."""

    WATCH_VIDEO = "watch_video"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    CLICK_PROFILE = "click_profile"
    CLICK_BIO_LINK = "click_bio_link"
    LIKE_VIDEO = "like_video"
    VIEW_COMMENTS = "view_comments"
    SHARE_VIDEO = "share_video"
    SEARCH = "search"


@dataclass
class TikTokSelectors:
    """Selectors for TikTok mobile web UI elements.

    Note: These target the mobile web version (m.tiktok.com).
    Selectors may need updates if TikTok changes their UI.
    """

    # Video container
    video_container: str = "[data-e2e='recommend-list-item-container']"
    video_player: str = "video"
    video_wrapper: str = ".tiktok-web-player"

    # Engagement buttons (right side)
    like_button: str = "[data-e2e='like-icon']"
    comment_button: str = "[data-e2e='comment-icon']"
    share_button: str = "[data-e2e='share-icon']"
    favorite_button: str = "[data-e2e='undefined-icon']"

    # Profile elements
    profile_link: str = "[data-e2e='video-author-avatar']"
    profile_username: str = "[data-e2e='video-author-uniqueid']"
    profile_name: str = "[data-e2e='video-author-nickname']"

    # Bio and links
    bio_link: str = "[data-e2e='user-link']"
    profile_bio: str = "[data-e2e='user-bio']"
    follow_button: str = "[data-e2e='follow-button']"

    # Caption and music
    caption_text: str = "[data-e2e='video-desc']"
    music_info: str = "[data-e2e='video-music']"

    # Navigation
    fyp_tab: str = "[data-e2e='nav-foryou']"
    following_tab: str = "[data-e2e='nav-following']"
    search_input: str = "[data-e2e='search-user-input']"

    # Swipe area (full screen for video feed)
    swipe_area: str = "[data-e2e='recommend-list-item-container']"

    # Loading indicators
    loading_spinner: str = ".loading-spinner"
    video_loading: str = "[data-e2e='video-loading']"


@dataclass
class TikTokConfig:
    """Configuration for TikTok automation."""

    # Target URL or username
    target_url: str = ""
    target_username: str = ""
    target_video_urls: list[str] = field(default_factory=list)

    # Watch behavior
    min_watch_percent: float = 0.3
    max_watch_percent: float = 1.5
    skip_probability: float = 0.30
    rewatch_probability: float = 0.10

    # Engagement (set to 0 for passive watching)
    like_probability: float = 0.0
    follow_probability: float = 0.0
    comment_probability: float = 0.0

    # Bio link clicking
    bio_click_probability: float = 0.15
    profile_visit_probability: float = 0.10

    # Session parameters
    videos_per_session: tuple[int, int] = (10, 30)
    session_duration_minutes: tuple[int, int] = (5, 20)

    # Timing
    swipe_speed_range: tuple[int, int] = (300, 800)  # ms
    inter_video_delay: tuple[float, float] = (0.5, 2.0)
    page_load_delay: tuple[float, float] = (3.0, 8.0)

    # In-app browser dwell time
    inapp_dwell_time: tuple[float, float] = (10.0, 60.0)

    # Rate limits (per hour)
    max_profile_views: int = 100
    max_bio_clicks: int = 15
    max_videos_per_session: int = 50

    # Mobile viewport
    viewport_width: int = 390
    viewport_height: int = 844


# TikTok WebView JavaScript bridge injection
TIKTOK_JS_BRIDGE = """
window.TikTokJSBridge = {
    invoke: function(method, params, callback) {
        console.log('TikTok bridge invoke:', method, params);
        if (callback) callback({success: true});
    },
    call: function(method, params) {
        console.log('TikTok bridge call:', method, params);
        return {success: true};
    },
    _callbacks: {},
    _callbackId: 0
};

window.byted_acrawler = {
    init: function(config) {
        console.log('Acrawler init:', config);
    },
    sign: function(params) {
        return '';  // Signature placeholder
    }
};
"""

# TikTok-specific headers for WebView
TIKTOK_HEADERS = {
    "x-tt-token": "",
    "x-tt-logid": "",
    "x-tt-trace-id": "",
}


class TikTokAutomation(SocialMediaAutomation):
    """TikTok automation plugin.

    Simulates human-like TikTok browsing behavior for:
    - FYP (For You Page) video watching
    - Profile visits and bio link clicks
    - Natural swipe and scroll patterns

    Usage:
        automation = TikTokAutomation(config=TikTokConfig(
            target_username="someuser",
            videos_per_session=(10, 20),
        ))

        async with browser.new_context() as context:
            page = await context.new_page()
            result = await automation.run(page)
    """

    name = "tiktok"
    platform = SocialPlatform.TIKTOK

    def __init__(
        self,
        config: TikTokConfig | None = None,
        selectors: TikTokSelectors | None = None,
        coherence_engine: CoherenceEngine | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize TikTok automation.

        Args:
            config: TikTok automation configuration
            selectors: UI element selectors
            coherence_engine: Behavior coherence engine
            rate_limiter: Rate limiting engine
        """
        super().__init__(coherence_engine, rate_limiter)
        self.config = config or TikTokConfig()
        self.selectors = selectors or TikTokSelectors()

        # Initialize behavior model
        self.watch_behavior = VideoWatchBehavior(
            platform="tiktok",
            interest_level=UserInterest.MEDIUM,
        )
        self.inapp_behavior = InAppBrowserBehavior(platform="tiktok")

        # Session tracking
        self._videos_watched = 0
        self._profiles_visited = 0
        self._bio_clicks = 0

    async def _setup_context(self, page: Any) -> None:
        """Setup page context for TikTok automation.

        Injects JavaScript bridge and configures headers.
        """
        try:
            # Inject TikTok JS bridge
            await page.add_init_script(TIKTOK_JS_BRIDGE)

            # Set mobile viewport
            await page.set_viewport_size({
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            })

            logger.info(
                "[TIKTOK_SETUP] Context configured successfully",
                viewport_width=self.config.viewport_width,
                viewport_height=self.config.viewport_height,
                js_bridge_injected=True,
            )
        except Exception as e:
            logger.error(
                "[TIKTOK_SETUP] Failed to configure context",
                error=str(e),
            )

    async def _get_video_duration(self, page: Any) -> float | None:
        """Try to get the current video duration."""
        try:
            video = page.locator(self.selectors.video_player).first
            duration = await video.evaluate("el => el.duration")
            return float(duration) if duration else None
        except Exception:
            return None

    async def watch_video(
        self,
        page: Any,
        duration: float | None = None,
    ) -> WatchResult:
        """Watch the current video with human-like behavior.

        Args:
            page: Browser page object
            duration: Optional forced watch duration (uses model if None)

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
                modifiers = self.coherence_engine.get_behavior_modifiers(
                    self._session_state
                )
                watch_time *= modifiers.get("dwell_time_factor", 1.0)

            logger.info(
                "[TIKTOK_WATCH] Starting video watch",
                video_number=self._videos_watched + 1,
                planned_watch_time_s=round(watch_time, 2),
                video_duration_s=round(video_duration, 2) if video_duration else "unknown",
                expected_outcome=outcome_str,
            )

            # Actually wait (simulate watching)
            await asyncio.sleep(watch_time)

            # Calculate completion rate
            completion_rate = (
                watch_time / video_duration if video_duration else 1.0
            )

            # Determine outcome
            outcome = self._determine_watch_outcome(watch_time, video_duration)

            # Record in behavior model
            self.watch_behavior.record_video_watched()
            self._videos_watched += 1

            # Record action
            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "watch")

            logger.info(
                "[TIKTOK_WATCH] Video watch completed",
                video_number=self._videos_watched,
                actual_watch_time_s=round(watch_time, 2),
                completion_rate_pct=round(completion_rate * 100, 1),
                outcome=outcome.value,
                replays=int(completion_rate) if completion_rate > 1 else 0,
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
                "[TIKTOK_WATCH] Video watch failed",
                video_number=self._videos_watched + 1,
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
        """Swipe up to go to the next video.

        Args:
            page: Browser page object

        Returns:
            SwipeResult
        """
        # Generate scroll timing
        pause, intensity = self.watch_behavior.generate_scroll_timing()

        logger.debug(
            "[TIKTOK_SWIPE] Preparing swipe to next video",
            pre_swipe_pause_s=round(pause, 2),
            intensity=intensity,
        )

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

        # Wait for video to load
        if result.success:
            await self._random_delay(0.5, 1.5)
            logger.info(
                "[TIKTOK_SWIPE] Swiped to next video successfully",
                direction="up",
                intensity=intensity,
                duration_ms=result.duration_ms,
            )
        else:
            logger.warning(
                "[TIKTOK_SWIPE] Swipe to next video failed",
                error=result.error,
            )

        return result

    async def swipe_to_previous(self, page: Any) -> SwipeResult:
        """Swipe down to go to the previous video.

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

    async def visit_profile(self, page: Any) -> bool:
        """Visit the current video creator's profile.

        Args:
            page: Browser page object

        Returns:
            True if navigation succeeded
        """
        try:
            logger.info(
                "[TIKTOK_PROFILE] Attempting to visit profile",
                profiles_visited_so_far=self._profiles_visited,
            )

            # Click profile avatar
            if await self._safe_click(page, self.selectors.profile_link):
                await self._wait_for_navigation(page)
                await self._random_delay(*self.config.page_load_delay)
                self._profiles_visited += 1

                if self._session_state:
                    self.coherence_engine.record_action(
                        self._session_state, "navigate", page.url
                    )

                logger.info(
                    "[TIKTOK_PROFILE] Profile visit successful",
                    profile_url=page.url,
                    total_profiles_visited=self._profiles_visited,
                )
                return True

            logger.warning(
                "[TIKTOK_PROFILE] Failed to click profile link",
                selector=self.selectors.profile_link,
            )
            return False

        except Exception as e:
            logger.error(
                "[TIKTOK_PROFILE] Profile visit failed with exception",
                error=str(e),
            )
            return False

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
                "[TIKTOK_BIO_CLICK] Starting bio link click sequence",
                username=username,
                bio_clicks_so_far=self._bio_clicks,
            )

            # Navigate to profile if username provided
            if username:
                profile_url = f"https://www.tiktok.com/@{username}"
                logger.debug(
                    "[TIKTOK_BIO_CLICK] Navigating to profile first",
                    profile_url=profile_url,
                )
                await page.goto(profile_url)
                await self._wait_for_navigation(page)
                await self._random_delay(*self.config.page_load_delay)

            # Look for bio link
            bio_link = page.locator(self.selectors.bio_link)
            if not await bio_link.count():
                logger.warning(
                    "[TIKTOK_BIO_CLICK] No bio link found on profile",
                    username=username,
                    current_url=page.url,
                )
                return BioClickResult(
                    success=False,
                    error="No bio link found",
                )

            # Get link URL
            target_url = await bio_link.get_attribute("href")
            logger.debug(
                "[TIKTOK_BIO_CLICK] Found bio link",
                target_url=target_url,
            )

            # Click the link
            if await self._safe_click(page, self.selectors.bio_link):
                self._bio_clicks += 1

                # Wait for page load
                await self._wait_for_navigation(page, timeout=15000)

                # Simulate in-app browser behavior
                dwell_time = self.inapp_behavior.generate_dwell_time()
                dwell_time = min(
                    dwell_time,
                    random.uniform(*self.config.inapp_dwell_time),
                )

                logger.info(
                    "[TIKTOK_BIO_CLICK] Entered external page via in-app browser",
                    target_url=target_url,
                    planned_dwell_time_s=round(dwell_time, 2),
                )

                # Simulate reading/scrolling on external page
                scroll_pattern = self.inapp_behavior.generate_scroll_pattern()
                scrolls_performed = 0
                for scroll_pos, pause_time in scroll_pattern[:5]:  # Limit scrolls
                    try:
                        await page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                        await asyncio.sleep(min(pause_time, 2.0))
                        scrolls_performed += 1
                    except Exception:
                        break

                    if self.inapp_behavior.should_return_to_app(dwell_time * 0.3):
                        break

                # Navigate back
                await page.go_back()
                await self._random_delay(1.0, 2.0)

                if self._session_state:
                    self.coherence_engine.record_action(
                        self._session_state, "click", target_url
                    )

                logger.info(
                    "[TIKTOK_BIO_CLICK] Bio link click completed successfully",
                    target_url=target_url,
                    actual_dwell_time_s=round(dwell_time, 2),
                    scrolls_performed=scrolls_performed,
                    total_bio_clicks=self._bio_clicks,
                )

                return BioClickResult(
                    success=True,
                    target_url=target_url,
                    dwell_time=dwell_time,
                )

            logger.warning(
                "[TIKTOK_BIO_CLICK] Failed to click bio link element",
                selector=self.selectors.bio_link,
            )
            return BioClickResult(
                success=False,
                error="Failed to click bio link",
            )

        except Exception as e:
            logger.error(
                "[TIKTOK_BIO_CLICK] Bio link click failed with exception",
                username=username,
                error=str(e),
            )
            return BioClickResult(
                success=False,
                error=str(e),
            )

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from TikTok URL.

        Args:
            url: TikTok video URL

        Returns:
            Video ID string
        """
        # Handle various TikTok URL formats:
        # https://www.tiktok.com/@user/video/7123456789012345678
        # https://vm.tiktok.com/XXXXXXX/
        # https://www.tiktok.com/t/XXXXXXX/
        if "/video/" in url:
            video_id = url.split("/video/")[1].split("?")[0].split("/")[0]
        elif "vm.tiktok.com/" in url or "/t/" in url:
            # Short URLs - use the short code as ID
            parts = url.rstrip("/").split("/")
            video_id = parts[-1].split("?")[0]
        else:
            # Fallback - use hash of URL
            import hashlib
            video_id = hashlib.md5(url.encode()).hexdigest()[:16]

        return video_id

    async def watch_direct_video(
        self,
        page: Any,
        video_url: str,
        watch_duration: float | None = None,
        proxy_id: str = "",
        fingerprint_id: str = "",
    ) -> WatchResult:
        """Watch a specific TikTok video URL directly.

        This method navigates directly to a video URL and watches it,
        which is useful for boosting views on specific content.

        Args:
            page: Browser page object
            video_url: Full TikTok video URL
            watch_duration: Optional forced duration (uses behavior model if None)
            proxy_id: Proxy identifier for view tracking
            fingerprint_id: Fingerprint identifier for view tracking

        Returns:
            WatchResult with watch statistics
        """
        video_id = self._extract_video_id(video_url)
        view_tracker = get_view_tracker()

        logger.info(
            "[TIKTOK_DIRECT] Starting direct video watch",
            video_url=video_url[:60] + "...",
            video_id=video_id,
            proxy_id=proxy_id[:8] + "..." if proxy_id else "none",
            fingerprint_id=fingerprint_id[:8] + "..." if fingerprint_id else "none",
        )

        # Check if we can view this video (rate limiting)
        can_view, reason = view_tracker.can_view(
            video_id=video_id,
            platform="tiktok",
            proxy_id=proxy_id,
            fingerprint_id=fingerprint_id,
        )

        if not can_view:
            logger.warning(
                "[TIKTOK_DIRECT] View blocked by rate limiter",
                video_id=video_id,
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
            # Navigate to the video
            await page.goto(video_url)
            await self._wait_for_navigation(page)
            await self._random_delay(*self.config.page_load_delay)

            logger.debug(
                "[TIKTOK_DIRECT] Video page loaded",
                current_url=page.url,
                video_id=video_id,
            )

            # Get video duration
            video_duration = await self._get_video_duration(page)

            # Generate watch duration based on behavior model
            if watch_duration is None:
                watch_time, outcome_str = self.watch_behavior.generate_watch_duration(
                    video_duration=video_duration,
                    content_interest=random.uniform(0.5, 0.9),  # Higher interest for target videos
                )
                # Ensure minimum watch time for view to count (3 seconds for TikTok)
                min_watch = view_tracker.get_minimum_watch_time("tiktok")
                watch_time = max(watch_time, min_watch + random.uniform(0.5, 2.0))
            else:
                watch_time = watch_duration
                outcome_str = "full"

            # Apply coherence modifiers
            if self._session_state:
                modifiers = self.coherence_engine.get_behavior_modifiers(
                    self._session_state
                )
                watch_time *= modifiers.get("dwell_time_factor", 1.0)

            logger.info(
                "[TIKTOK_DIRECT] Watching video",
                video_id=video_id,
                planned_watch_time_s=round(watch_time, 2),
                video_duration_s=round(video_duration, 2) if video_duration else "unknown",
                min_for_view_s=view_tracker.get_minimum_watch_time("tiktok"),
            )

            # Actually watch (wait)
            await asyncio.sleep(watch_time)

            # Calculate completion
            completion_rate = watch_time / video_duration if video_duration else 1.0
            outcome = self._determine_watch_outcome(watch_time, video_duration)

            # Record the view
            view_counted = view_tracker.record_view(
                video_id=video_id,
                platform="tiktok",
                proxy_id=proxy_id,
                fingerprint_id=fingerprint_id,
                watch_duration=watch_time,
            )

            # Record in behavior model
            self.watch_behavior.record_video_watched()
            self._videos_watched += 1

            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "watch")

            logger.info(
                "[TIKTOK_DIRECT] Direct video watch completed",
                video_id=video_id,
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
                "[TIKTOK_DIRECT] Direct video watch failed",
                video_url=video_url[:60] + "...",
                video_id=video_id,
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

    async def watch_direct_videos(
        self,
        page: Any,
        video_urls: list[str] | None = None,
        delay_between: tuple[float, float] = (5.0, 15.0),
        proxy_id: str = "",
        fingerprint_id: str = "",
    ) -> list[WatchResult]:
        """Watch multiple specific TikTok video URLs directly.

        Args:
            page: Browser page object
            video_urls: List of video URLs (uses config.target_video_urls if None)
            delay_between: Min/max delay between videos
            proxy_id: Proxy identifier for view tracking
            fingerprint_id: Fingerprint identifier for view tracking

        Returns:
            List of WatchResults
        """
        # Use config if not provided
        if video_urls is None:
            video_urls = self.config.target_video_urls

        if not video_urls:
            logger.warning(
                "[TIKTOK_DIRECT_BATCH] No video URLs provided",
            )
            return []

        logger.info(
            "[TIKTOK_DIRECT_BATCH] ========== STARTING DIRECT VIDEO BATCH ==========",
            total_videos=len(video_urls),
            delay_between_min_s=delay_between[0],
            delay_between_max_s=delay_between[1],
        )

        results = []

        for idx, video_url in enumerate(video_urls):
            logger.info(
                "[TIKTOK_DIRECT_BATCH] Processing video",
                video_index=idx + 1,
                total_videos=len(video_urls),
                video_url=video_url[:60] + "...",
            )

            result = await self.watch_direct_video(
                page=page,
                video_url=video_url,
                proxy_id=proxy_id,
                fingerprint_id=fingerprint_id,
            )
            results.append(result)

            # Delay between videos (except for last)
            if idx < len(video_urls) - 1:
                delay = random.uniform(*delay_between)
                logger.debug(
                    "[TIKTOK_DIRECT_BATCH] Waiting between videos",
                    delay_s=round(delay, 2),
                )
                await asyncio.sleep(delay)

        # Log batch statistics
        successful = sum(1 for r in results if r.success)
        total_watch_time = sum(r.watch_duration for r in results)

        logger.info(
            "[TIKTOK_DIRECT_BATCH] ========== DIRECT VIDEO BATCH COMPLETED ==========",
            total_videos=len(video_urls),
            successful_watches=successful,
            failed_watches=len(results) - successful,
            total_watch_time_s=round(total_watch_time, 2),
        )

        return results

    async def simulate_fyp_session(
        self,
        page: Any,
        target_profile: str | None = None,
        videos_to_watch: int | None = None,
    ) -> SessionResult:
        """Simulate a For You Page browsing session.

        Args:
            page: Browser page object
            target_profile: Optional profile to visit during session
            videos_to_watch: Number of videos (uses config if None)

        Returns:
            SessionResult with full session statistics
        """
        start_time = datetime.now(UTC)
        session = self._create_session()
        watch_results: list[WatchResult] = []
        errors: list[str] = []

        # Determine session length
        if videos_to_watch is None:
            videos_to_watch = self.watch_behavior.generate_session_length()

        videos_to_watch = min(
            videos_to_watch,
            self.config.max_videos_per_session,
        )

        logger.info(
            "[TIKTOK_SESSION] ========== STARTING FYP SESSION ==========",
            target_videos=videos_to_watch,
            target_profile=target_profile,
            session_id=session.session_id if session else "unknown",
            persona=session.persona.value if session else "unknown",
            config_skip_prob=self.config.skip_probability,
            config_bio_click_prob=self.config.bio_click_probability,
        )

        # Initialize counters before try block to avoid UnboundLocalError
        bio_links_clicked = 0
        profiles_visited = 0

        try:
            # Navigate to TikTok FYP
            await page.goto("https://www.tiktok.com/foryou")
            await self._wait_for_navigation(page)
            await self._random_delay(*self.config.page_load_delay)

            for i in range(videos_to_watch):
                logger.debug(
                    "[TIKTOK_SESSION] Processing video iteration",
                    video_index=i + 1,
                    total_target=videos_to_watch,
                    progress_pct=round((i / videos_to_watch) * 100, 1),
                )

                # Check for break
                if self.watch_behavior.should_take_break():
                    break_duration = self.watch_behavior.generate_break_duration()
                    logger.info(
                        "[TIKTOK_SESSION] Taking human break",
                        break_duration_s=round(break_duration, 2),
                        videos_watched_so_far=len(watch_results),
                    )
                    await asyncio.sleep(break_duration)

                    if self._session_state:
                        self.coherence_engine.record_break(
                            self._session_state, break_duration
                        )

                # Watch current video
                watch_result = await self.watch_video(page)
                watch_results.append(watch_result)

                if not watch_result.success:
                    errors.append(watch_result.error or "Watch failed")

                # Decide on next action
                if self.watch_behavior.should_visit_profile():
                    # Visit profile
                    if await self.visit_profile(page):
                        profiles_visited += 1

                        # Maybe click bio link
                        if self.watch_behavior.should_click_bio():
                            bio_result = await self.click_bio_link(page)
                            if bio_result.success:
                                bio_links_clicked += 1

                        # Navigate back to FYP
                        await page.go_back()
                        await self._random_delay(1.0, 2.0)

                # Check if should scroll back
                if self.watch_behavior.should_scroll_back() and i > 0:
                    await self.swipe_to_previous(page)
                    await self._random_delay(1.0, 3.0)
                    await self.swipe_to_next(page)

                # Swipe to next video
                swipe_result = await self.swipe_to_next(page)
                if not swipe_result.success:
                    errors.append(swipe_result.error or "Swipe failed")

            # Visit target profile if specified
            if target_profile:
                profile_url = f"https://www.tiktok.com/@{target_profile}"
                await page.goto(profile_url)
                await self._wait_for_navigation(page)
                await self._random_delay(*self.config.page_load_delay)
                profiles_visited += 1

                # Click bio link with configured probability
                if random.random() < self.config.bio_click_probability:
                    bio_result = await self.click_bio_link(page)
                    if bio_result.success:
                        bio_links_clicked += 1

        except Exception as e:
            errors.append(str(e))
            logger.error(
                "[TIKTOK_SESSION] Session error occurred",
                error=str(e),
                videos_watched_before_error=len(watch_results),
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
            if watch_results else 0
        )

        logger.info(
            "[TIKTOK_SESSION] ========== SESSION COMPLETED ==========",
            success=len(errors) == 0,
            session_duration_s=round(session_duration, 2),
            session_duration_min=round(session_duration / 60, 1),
            videos_watched=len(watch_results),
            successful_watches=successful_watches,
            avg_watch_time_s=round(avg_watch_time, 2),
            profiles_visited=profiles_visited,
            bio_links_clicked=bio_links_clicked,
            error_count=len(errors),
            errors=errors if errors else None,
        )

        return SessionResult(
            success=len(errors) == 0,
            platform=SocialPlatform.TIKTOK,
            start_time=start_time,
            end_time=end_time,
            videos_watched=len(watch_results),
            bio_links_clicked=bio_links_clicked,
            story_links_clicked=0,  # TikTok doesn't have stories
            profiles_visited=profiles_visited,
            errors=errors,
            watch_results=watch_results,
        )

    async def run(
        self,
        page: Any,
        url: str | None = None,
        proxy_id: str = "",
        fingerprint_id: str = "",
    ) -> SessionResult:
        """Run the full TikTok automation sequence.

        Priority:
        1. If target_video_urls are configured, watch those videos directly
        2. Otherwise, run FYP session with optional profile visit

        Args:
            page: Browser page object
            url: Optional starting URL
            proxy_id: Proxy identifier for view tracking
            fingerprint_id: Fingerprint identifier for view tracking

        Returns:
            SessionResult
        """
        logger.info(
            "[TIKTOK_RUN] Starting TikTok automation run",
            url=url,
            target_username=self.config.target_username,
            target_video_urls_count=len(self.config.target_video_urls),
            mode="direct_videos" if self.config.target_video_urls else "fyp_session",
        )

        # Setup context
        await self._setup_context(page)
        start_time = datetime.now(UTC)
        session = self._create_session()

        # PRIORITY 1: If target video URLs are configured, watch them directly
        if self.config.target_video_urls:
            logger.info(
                "[TIKTOK_RUN] Running in DIRECT VIDEO mode",
                video_count=len(self.config.target_video_urls),
            )

            watch_results = await self.watch_direct_videos(
                page=page,
                video_urls=self.config.target_video_urls,
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
                platform=SocialPlatform.TIKTOK,
                start_time=start_time,
                end_time=end_time,
                videos_watched=len(watch_results),
                bio_links_clicked=0,
                story_links_clicked=0,
                profiles_visited=0,
                errors=errors,
                watch_results=watch_results,
            )

        # PRIORITY 2: Run FYP session
        target_profile = None
        if url:
            # Extract username from URL if profile link
            if "/@" in url:
                target_profile = url.split("/@")[1].split("/")[0].split("?")[0]
                logger.debug(
                    "[TIKTOK_RUN] Extracted target profile from URL",
                    target_profile=target_profile,
                )
        elif self.config.target_username:
            target_profile = self.config.target_username

        # Run FYP session
        return await self.simulate_fyp_session(
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
            "[TIKTOK_BATCH] ========== STARTING BATCH RUN ==========",
            total_profiles=len(profiles),
            profiles=profiles,
            delay_between_min_s=delay_between[0],
            delay_between_max_s=delay_between[1],
        )

        results = []

        for idx, profile in enumerate(profiles):
            logger.info(
                "[TIKTOK_BATCH] Processing profile in batch",
                profile=profile,
                profile_index=idx + 1,
                total_profiles=len(profiles),
            )

            result = await self.simulate_fyp_session(
                page,
                target_profile=profile,
                videos_to_watch=random.randint(5, 15),
            )
            results.append(result)

            if profile != profiles[-1]:
                delay = random.uniform(*delay_between)
                logger.debug(
                    "[TIKTOK_BATCH] Waiting between profiles",
                    delay_s=round(delay, 2),
                    next_profile=profiles[idx + 1],
                )
                await asyncio.sleep(delay)

        # Calculate batch statistics
        total_videos = sum(r.videos_watched for r in results)
        total_bio_clicks = sum(r.bio_links_clicked for r in results)
        successful_sessions = sum(1 for r in results if r.success)

        logger.info(
            "[TIKTOK_BATCH] ========== BATCH RUN COMPLETED ==========",
            total_profiles=len(profiles),
            successful_sessions=successful_sessions,
            total_videos_watched=total_videos,
            total_bio_clicks=total_bio_clicks,
        )

        return results
