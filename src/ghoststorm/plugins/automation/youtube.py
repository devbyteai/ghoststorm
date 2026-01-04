"""YouTube Automation Plugin.

Provides human-like automation for YouTube including:
- Regular video watching with natural behavior patterns
- YouTube Shorts with vertical swipe patterns
- Description link clicking
- Channel visits
- Direct video URL watching for view boosting

Designed to avoid detection by mimicking real user behavior.

IMPORTANT: YouTube requires 30+ seconds of watch time for a view to count.
"""

from __future__ import annotations

import asyncio
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

if TYPE_CHECKING:
    from ghoststorm.plugins.behavior.coherence_engine import (
        CoherenceEngine,
    )
    from ghoststorm.plugins.network.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)


class YouTubeAction(str, Enum):
    """YouTube automation actions."""

    WATCH_VIDEO = "watch_video"
    WATCH_SHORT = "watch_short"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    CLICK_DESCRIPTION_LINK = "click_description_link"
    VISIT_CHANNEL = "visit_channel"
    LIKE_VIDEO = "like_video"
    SUBSCRIBE = "subscribe"
    SEARCH = "search"


@dataclass
class YouTubeSelectors:
    """Selectors for YouTube mobile web UI elements.

    Note: These target the mobile web version (m.youtube.com).
    Selectors may need updates if YouTube changes their UI.
    """

    # Video player
    video_player: str = "video"
    video_container: str = "#player-container"
    player_controls: str = ".ytp-chrome-bottom"

    # Engagement buttons
    like_button: str = "#segmented-like-button button"
    dislike_button: str = "#segmented-dislike-button button"
    share_button: str = "#top-level-buttons-computed ytd-button-renderer:nth-child(3)"
    subscribe_button: str = "#subscribe-button button"

    # Description and info
    description_expand: str = "#description-inline-expander"
    description_content: str = "#description-inline-expander #plain-snippet-text"
    description_links: str = "#description a[href]"

    # Channel info
    channel_link: str = "#owner a"
    channel_name: str = "#owner #channel-name"
    channel_avatar: str = "#owner #avatar"

    # Video info
    video_title: str = "h1.ytd-video-primary-info-renderer"
    view_count: str = "#info-container span.view-count"

    # Shorts specific
    shorts_container: str = "#shorts-player"
    shorts_video: str = "#shorts-player video"
    shorts_like: str = "[aria-label='Like']"
    shorts_comment: str = "[aria-label='Comments']"
    shorts_share: str = "[aria-label='Share']"

    # Navigation
    home_tab: str = "[title='Home']"
    shorts_tab: str = "[title='Shorts']"
    subscriptions_tab: str = "[title='Subscriptions']"
    search_button: str = "#search-icon-legacy"

    # Loading
    loading_spinner: str = "ytd-video-primary-info-renderer[loading]"
    skeleton_loading: str = ".ytd-thumbnail-overlay-loading-preview-renderer"


@dataclass
class YouTubeConfig:
    """Configuration for YouTube automation."""

    # Target URLs
    target_url: str = ""
    target_video_urls: list[str] = field(default_factory=list)
    target_short_urls: list[str] = field(default_factory=list)
    target_channel: str = ""

    # Content mode
    content_mode: Literal["videos", "shorts", "mixed"] = "videos"

    # Watch behavior - IMPORTANT: YouTube needs 30s min for view count
    min_watch_percent: float = 0.30
    max_watch_percent: float = 0.90
    min_watch_seconds: float = 30.0  # YouTube minimum for view to count
    skip_probability: float = 0.20
    rewatch_probability: float = 0.05

    # Engagement (set to 0 for passive watching)
    like_probability: float = 0.0
    subscribe_probability: float = 0.0
    comment_probability: float = 0.0

    # Description link clicking
    description_click_probability: float = 0.10
    channel_visit_probability: float = 0.08

    # Session parameters
    videos_per_session: tuple[int, int] = (5, 15)
    shorts_per_session: tuple[int, int] = (10, 30)

    # Timing
    swipe_speed_range: tuple[int, int] = (300, 700)  # ms
    inter_video_delay: tuple[float, float] = (2.0, 8.0)
    page_load_delay: tuple[float, float] = (3.0, 8.0)

    # In-app browser dwell time
    inapp_dwell_time: tuple[float, float] = (15.0, 90.0)

    # Rate limits (per hour)
    max_videos_per_session: int = 20
    max_shorts_per_session: int = 40
    max_channel_visits: int = 30
    max_description_clicks: int = 10

    # Mobile viewport
    viewport_width: int = 390
    viewport_height: int = 844


# YouTube WebView JavaScript interface injection
YOUTUBE_JS_INTERFACE = """
window.ytcfg = window.ytcfg || {};
window.ytcfg.set = function(key, val) { window.ytcfg[key] = val; };
window.ytcfg.get = function(key) { return window.ytcfg[key]; };
window.ytcfg.set('INNERTUBE_CONTEXT_CLIENT_NAME', 2);
window.ytcfg.set('INNERTUBE_CONTEXT_CLIENT_VERSION', '19.03.36');
window.ytcfg.set('VISITOR_DATA', '{visitor_id}');
window.ytcfg.set('DEVICE_ID', '{device_id}');
window._ytDeviceId = '{device_id}';
window._ytVisitorId = '{visitor_id}';
window.yt = window.yt || {};
window.yt.player = window.yt.player || {};
"""

# YouTube-specific headers for WebView
YOUTUBE_HEADERS = {
    "X-YouTube-Client-Name": "2",  # Android app
    "X-YouTube-Client-Version": "19.03.36",
    "X-Goog-Visitor-Id": "",  # Filled per session
    "X-YouTube-Device": "",  # Filled per session
}


class YouTubeAutomation(SocialMediaAutomation):
    """YouTube automation plugin.

    Simulates human-like YouTube browsing behavior for:
    - Regular video watching with realistic timing
    - YouTube Shorts vertical feed browsing
    - Description link clicks
    - Channel visits

    IMPORTANT: YouTube requires ~30 seconds of watch time for a view to count.

    Usage:
        automation = YouTubeAutomation(config=YouTubeConfig(
            target_video_urls=["https://youtube.com/watch?v=xxx"],
            min_watch_seconds=30.0,
        ))

        async with browser.new_context() as context:
            page = await context.new_page()
            result = await automation.run(page)
    """

    name = "youtube"
    platform = SocialPlatform.YOUTUBE

    def __init__(
        self,
        config: YouTubeConfig | None = None,
        selectors: YouTubeSelectors | None = None,
        coherence_engine: CoherenceEngine | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize YouTube automation.

        Args:
            config: YouTube automation configuration
            selectors: UI element selectors
            coherence_engine: Behavior coherence engine
            rate_limiter: Rate limiting engine
        """
        super().__init__(coherence_engine, rate_limiter)
        self.config = config or YouTubeConfig()
        self.selectors = selectors or YouTubeSelectors()

        # Initialize behavior models - use youtube or youtube_shorts based on mode
        platform_key = "youtube_shorts" if config and config.content_mode == "shorts" else "youtube"
        self.watch_behavior = VideoWatchBehavior(
            platform=platform_key,
            interest_level=UserInterest.MEDIUM,
        )
        self.inapp_behavior = InAppBrowserBehavior(platform="youtube")

        # Session tracking
        self._videos_watched = 0
        self._shorts_watched = 0
        self._channels_visited = 0
        self._description_clicks = 0

        # Device/visitor IDs for this session
        self._device_id = self._generate_device_id()
        self._visitor_id = self._generate_visitor_id()

    def _generate_device_id(self) -> str:
        """Generate a realistic device ID."""
        import hashlib
        import uuid

        return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

    def _generate_visitor_id(self) -> str:
        """Generate a YouTube visitor ID (22-char base64)."""
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        return "".join(random.choice(chars) for _ in range(22))

    async def _setup_context(self, page: Any) -> None:
        """Setup page context for YouTube automation.

        Injects JavaScript interface and configures headers.
        """
        try:
            # Inject YouTube JS interface
            js_code = YOUTUBE_JS_INTERFACE.replace("{device_id}", self._device_id)
            js_code = js_code.replace("{visitor_id}", self._visitor_id)
            await page.add_init_script(js_code)

            # Set mobile viewport
            await page.set_viewport_size(
                {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }
            )

            # Set extra headers
            headers = YOUTUBE_HEADERS.copy()
            headers["X-Goog-Visitor-Id"] = self._visitor_id
            headers["X-YouTube-Device"] = self._device_id
            await page.context.set_extra_http_headers(headers)

            logger.info(
                "[YOUTUBE_SETUP] Context configured successfully",
                device_id=self._device_id[:8] + "...",
                visitor_id=self._visitor_id[:8] + "...",
                viewport_width=self.config.viewport_width,
                viewport_height=self.config.viewport_height,
            )
        except Exception as e:
            logger.error(
                "[YOUTUBE_SETUP] Failed to configure context",
                error=str(e),
            )

    async def _get_video_duration(self, page: Any) -> float | None:
        """Try to get the current video duration."""
        try:
            video = page.locator(self.selectors.video_player).first
            duration = await video.evaluate("el => el.duration")
            return float(duration) if duration and duration > 0 else None
        except Exception:
            return None

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL.

        Args:
            url: YouTube video URL

        Returns:
            Video ID string
        """
        # Handle various YouTube URL formats:
        # https://www.youtube.com/watch?v=VIDEO_ID
        # https://youtu.be/VIDEO_ID
        # https://www.youtube.com/shorts/VIDEO_ID
        # https://m.youtube.com/watch?v=VIDEO_ID
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0].split("#")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0].split("/")[0]
        elif "/shorts/" in url:
            video_id = url.split("/shorts/")[1].split("?")[0].split("/")[0]
        else:
            # Fallback - use hash of URL
            import hashlib

            video_id = hashlib.md5(url.encode()).hexdigest()[:16]

        return video_id

    async def watch_video(
        self,
        page: Any,
        duration: float | None = None,
    ) -> WatchResult:
        """Watch the current video with human-like behavior.

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
                # Enforce minimum watch time for YouTube view to count
                watch_time = max(watch_time, self.config.min_watch_seconds)
            else:
                watch_time = duration
                outcome_str = "full"

            # Apply coherence modifiers
            if self._session_state:
                modifiers = self.coherence_engine.get_behavior_modifiers(self._session_state)
                watch_time *= modifiers.get("dwell_time_factor", 1.0)

            logger.info(
                "[YOUTUBE_WATCH] Starting video watch",
                video_number=self._videos_watched + 1,
                planned_watch_time_s=round(watch_time, 2),
                video_duration_s=round(video_duration, 2) if video_duration else "unknown",
                expected_outcome=outcome_str,
                min_for_view_s=self.config.min_watch_seconds,
            )

            # Actually wait (simulate watching)
            await asyncio.sleep(watch_time)

            # Calculate completion rate
            completion_rate = watch_time / video_duration if video_duration else 1.0

            # Determine outcome
            outcome = self._determine_watch_outcome(watch_time, video_duration)

            # Record in behavior model
            self.watch_behavior.record_video_watched()
            self._videos_watched += 1

            # Record action
            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "watch")

            logger.info(
                "[YOUTUBE_WATCH] Video watch completed",
                video_number=self._videos_watched,
                actual_watch_time_s=round(watch_time, 2),
                completion_rate_pct=round(completion_rate * 100, 1),
                outcome=outcome.value,
                view_likely_counted=watch_time >= self.config.min_watch_seconds,
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
                "[YOUTUBE_WATCH] Video watch failed",
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

    async def watch_direct_video(
        self,
        page: Any,
        video_url: str,
        watch_duration: float | None = None,
        proxy_id: str = "",
        fingerprint_id: str = "",
    ) -> WatchResult:
        """Watch a specific YouTube video URL directly.

        This method navigates directly to a video URL and watches it,
        ensuring the minimum watch time for the view to count.

        Args:
            page: Browser page object
            video_url: Full YouTube video URL
            watch_duration: Optional forced duration (uses behavior model if None)
            proxy_id: Proxy identifier for view tracking
            fingerprint_id: Fingerprint identifier for view tracking

        Returns:
            WatchResult with watch statistics
        """
        video_id = self._extract_video_id(video_url)
        is_short = "/shorts/" in video_url
        platform_key = "youtube_shorts" if is_short else "youtube"
        view_tracker = get_view_tracker()

        logger.info(
            "[YOUTUBE_DIRECT] Starting direct video watch",
            video_url=video_url[:60] + "...",
            video_id=video_id,
            is_short=is_short,
            proxy_id=proxy_id[:8] + "..." if proxy_id else "none",
            fingerprint_id=fingerprint_id[:8] + "..." if fingerprint_id else "none",
        )

        # Check if we can view this video (rate limiting)
        can_view, reason = view_tracker.can_view(
            video_id=video_id,
            platform=platform_key,
            proxy_id=proxy_id,
            fingerprint_id=fingerprint_id,
        )

        if not can_view:
            logger.warning(
                "[YOUTUBE_DIRECT] View blocked by rate limiter",
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
                "[YOUTUBE_DIRECT] Video page loaded",
                current_url=page.url,
                video_id=video_id,
            )

            # Get video duration
            video_duration = await self._get_video_duration(page)

            # Generate watch duration based on behavior model
            if watch_duration is None:
                min_watch = view_tracker.get_minimum_watch_time(platform_key)

                if is_short:
                    # Shorts are shorter - use shorts behavior
                    watch_time, outcome_str = self.watch_behavior.generate_watch_duration(
                        video_duration=video_duration,
                        content_interest=random.uniform(0.5, 0.9),
                    )
                    watch_time = max(watch_time, min_watch + random.uniform(0.5, 2.0))
                else:
                    # Regular videos need at least 30 seconds for view to count
                    watch_time, _outcome_str = self.watch_behavior.generate_watch_duration(
                        video_duration=video_duration,
                        content_interest=random.uniform(0.5, 0.9),
                    )
                    # Ensure we watch at least 30 seconds + some buffer
                    watch_time = max(watch_time, min_watch + random.uniform(5.0, 15.0))
            else:
                watch_time = watch_duration

            # Apply coherence modifiers
            if self._session_state:
                modifiers = self.coherence_engine.get_behavior_modifiers(self._session_state)
                watch_time *= modifiers.get("dwell_time_factor", 1.0)

            logger.info(
                "[YOUTUBE_DIRECT] Watching video",
                video_id=video_id,
                is_short=is_short,
                planned_watch_time_s=round(watch_time, 2),
                video_duration_s=round(video_duration, 2) if video_duration else "unknown",
                min_for_view_s=view_tracker.get_minimum_watch_time(platform_key),
            )

            # Actually watch (wait)
            await asyncio.sleep(watch_time)

            # Calculate completion
            completion_rate = watch_time / video_duration if video_duration else 1.0
            outcome = self._determine_watch_outcome(watch_time, video_duration)

            # Record the view
            view_counted = view_tracker.record_view(
                video_id=video_id,
                platform=platform_key,
                proxy_id=proxy_id,
                fingerprint_id=fingerprint_id,
                watch_duration=watch_time,
            )

            # Record in behavior model
            self.watch_behavior.record_video_watched()
            if is_short:
                self._shorts_watched += 1
            else:
                self._videos_watched += 1

            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "watch")

            logger.info(
                "[YOUTUBE_DIRECT] Direct video watch completed",
                video_id=video_id,
                is_short=is_short,
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
                "[YOUTUBE_DIRECT] Direct video watch failed",
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
        """Watch multiple specific YouTube video URLs directly.

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
            video_urls = self.config.target_video_urls + self.config.target_short_urls

        if not video_urls:
            logger.warning(
                "[YOUTUBE_DIRECT_BATCH] No video URLs provided",
            )
            return []

        logger.info(
            "[YOUTUBE_DIRECT_BATCH] ========== STARTING DIRECT VIDEO BATCH ==========",
            total_videos=len(video_urls),
            delay_between_min_s=delay_between[0],
            delay_between_max_s=delay_between[1],
        )

        results = []

        for idx, video_url in enumerate(video_urls):
            is_short = "/shorts/" in video_url

            logger.info(
                "[YOUTUBE_DIRECT_BATCH] Processing video",
                video_index=idx + 1,
                total_videos=len(video_urls),
                video_url=video_url[:60] + "...",
                is_short=is_short,
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
                    "[YOUTUBE_DIRECT_BATCH] Waiting between videos",
                    delay_s=round(delay, 2),
                )
                await asyncio.sleep(delay)

        # Log batch statistics
        successful = sum(1 for r in results if r.success)
        total_watch_time = sum(r.watch_duration for r in results)

        logger.info(
            "[YOUTUBE_DIRECT_BATCH] ========== DIRECT VIDEO BATCH COMPLETED ==========",
            total_videos=len(video_urls),
            successful_watches=successful,
            failed_watches=len(results) - successful,
            total_watch_time_s=round(total_watch_time, 2),
            total_watch_time_min=round(total_watch_time / 60, 1),
        )

        return results

    async def watch_short(
        self,
        page: Any,
        duration: float | None = None,
    ) -> WatchResult:
        """Watch the current YouTube Short with human-like behavior.

        Args:
            page: Browser page object
            duration: Optional forced watch duration

        Returns:
            WatchResult with watch statistics
        """
        try:
            # Get video duration - Shorts are typically 15-60 seconds
            video_duration = await self._get_video_duration(page)
            if video_duration is None:
                video_duration = random.uniform(15.0, 60.0)

            # Generate watch duration
            if duration is None:
                watch_time, _outcome_str = self.watch_behavior.generate_watch_duration(
                    video_duration=video_duration,
                    content_interest=random.uniform(0.3, 0.8),
                )
            else:
                watch_time = duration

            # Apply coherence modifiers
            if self._session_state:
                modifiers = self.coherence_engine.get_behavior_modifiers(self._session_state)
                watch_time *= modifiers.get("dwell_time_factor", 1.0)

            logger.info(
                "[YOUTUBE_SHORT] Starting Short watch",
                short_number=self._shorts_watched + 1,
                planned_watch_time_s=round(watch_time, 2),
                video_duration_s=round(video_duration, 2),
            )

            # Actually wait (simulate watching)
            await asyncio.sleep(watch_time)

            # Calculate completion rate
            completion_rate = watch_time / video_duration if video_duration else 1.0
            outcome = self._determine_watch_outcome(watch_time, video_duration)

            self.watch_behavior.record_video_watched()
            self._shorts_watched += 1

            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "watch")

            logger.info(
                "[YOUTUBE_SHORT] Short watch completed",
                short_number=self._shorts_watched,
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
                "[YOUTUBE_SHORT] Short watch failed",
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
        """Swipe up to go to the next Short.

        Args:
            page: Browser page object

        Returns:
            SwipeResult
        """
        # Generate scroll timing
        pause, intensity = self.watch_behavior.generate_scroll_timing()

        logger.debug(
            "[YOUTUBE_SWIPE] Preparing swipe to next Short",
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

        if result.success:
            await self._random_delay(0.5, 1.5)
            logger.info(
                "[YOUTUBE_SWIPE] Swiped to next Short successfully",
                direction="up",
                intensity=intensity,
            )
        else:
            logger.warning(
                "[YOUTUBE_SWIPE] Swipe failed",
                error=result.error,
            )

        return result

    async def swipe_to_previous(self, page: Any) -> SwipeResult:
        """Swipe down to go to the previous Short.

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

    async def click_description_link(
        self,
        page: Any,
    ) -> BioClickResult:
        """Click a link in the video description.

        Args:
            page: Browser page object

        Returns:
            BioClickResult (using same result type for consistency)
        """
        try:
            logger.info(
                "[YOUTUBE_DESC_CLICK] Attempting to click description link",
                description_clicks_so_far=self._description_clicks,
            )

            # First, expand description if collapsed
            expand_btn = page.locator(self.selectors.description_expand)
            if await expand_btn.count():
                try:
                    await self._safe_click(page, self.selectors.description_expand)
                    await self._random_delay(0.5, 1.0)
                except Exception:
                    pass

            # Look for links in description
            links = page.locator(self.selectors.description_links)
            link_count = await links.count()

            if link_count == 0:
                logger.warning(
                    "[YOUTUBE_DESC_CLICK] No links found in description",
                )
                return BioClickResult(
                    success=False,
                    error="No links in description",
                )

            # Pick a random link
            link_index = random.randint(0, link_count - 1)
            target_link = links.nth(link_index)
            target_url = await target_link.get_attribute("href")

            logger.debug(
                "[YOUTUBE_DESC_CLICK] Found description link",
                target_url=target_url,
                link_index=link_index,
                total_links=link_count,
            )

            # Click the link
            await target_link.click()
            self._description_clicks += 1

            # Wait for navigation
            await self._wait_for_navigation(page, timeout=15000)

            # Simulate reading the external page
            dwell_time = self.inapp_behavior.generate_dwell_time()
            dwell_time = min(
                dwell_time,
                random.uniform(*self.config.inapp_dwell_time),
            )

            logger.info(
                "[YOUTUBE_DESC_CLICK] Entered external page",
                target_url=target_url,
                planned_dwell_time_s=round(dwell_time, 2),
            )

            # Simulate scrolling on external page
            scroll_pattern = self.inapp_behavior.generate_scroll_pattern()
            for scroll_pos, pause_time in scroll_pattern[:5]:
                try:
                    await page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                    await asyncio.sleep(min(pause_time, 2.0))
                except Exception:
                    break

                if self.inapp_behavior.should_return_to_app(dwell_time * 0.3):
                    break

            # Navigate back
            await page.go_back()
            await self._random_delay(1.0, 2.0)

            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "click", target_url)

            logger.info(
                "[YOUTUBE_DESC_CLICK] Description link click completed",
                target_url=target_url,
                dwell_time_s=round(dwell_time, 2),
                total_description_clicks=self._description_clicks,
            )

            return BioClickResult(
                success=True,
                target_url=target_url,
                dwell_time=dwell_time,
            )

        except Exception as e:
            logger.error(
                "[YOUTUBE_DESC_CLICK] Description link click failed",
                error=str(e),
            )
            return BioClickResult(
                success=False,
                error=str(e),
            )

    async def visit_channel(
        self,
        page: Any,
        channel: str | None = None,
    ) -> bool:
        """Visit a YouTube channel.

        Args:
            page: Browser page object
            channel: Optional channel handle to navigate to directly

        Returns:
            True if navigation succeeded
        """
        try:
            logger.info(
                "[YOUTUBE_CHANNEL] Attempting channel visit",
                channel=channel,
                channels_visited_so_far=self._channels_visited,
            )

            if channel:
                # Navigate directly to channel
                channel_url = f"https://www.youtube.com/@{channel}"
                await page.goto(channel_url)
            else:
                # Click channel link from current video
                if not await self._safe_click(page, self.selectors.channel_link):
                    return False

            await self._wait_for_navigation(page)
            await self._random_delay(*self.config.page_load_delay)
            self._channels_visited += 1

            if self._session_state:
                self.coherence_engine.record_action(self._session_state, "navigate", page.url)

            logger.info(
                "[YOUTUBE_CHANNEL] Channel visit successful",
                channel_url=page.url,
                total_channels_visited=self._channels_visited,
            )
            return True

        except Exception as e:
            logger.error(
                "[YOUTUBE_CHANNEL] Channel visit failed",
                channel=channel,
                error=str(e),
            )
            return False

    async def simulate_shorts_session(
        self,
        page: Any,
        shorts_to_watch: int | None = None,
    ) -> SessionResult:
        """Simulate a YouTube Shorts browsing session.

        Args:
            page: Browser page object
            shorts_to_watch: Number of Shorts (uses config if None)

        Returns:
            SessionResult with full session statistics
        """
        start_time = datetime.now(UTC)
        session = self._create_session()
        watch_results: list[WatchResult] = []
        errors: list[str] = []

        if shorts_to_watch is None:
            shorts_to_watch = random.randint(*self.config.shorts_per_session)

        shorts_to_watch = min(shorts_to_watch, self.config.max_shorts_per_session)

        logger.info(
            "[YOUTUBE_SHORTS_SESSION] ========== STARTING SHORTS SESSION ==========",
            target_shorts=shorts_to_watch,
            session_id=session.session_id if session else "unknown",
        )

        try:
            # Navigate to YouTube Shorts
            await page.goto("https://www.youtube.com/shorts")
            await self._wait_for_navigation(page)
            await self._random_delay(*self.config.page_load_delay)

            for _i in range(shorts_to_watch):
                # Check for break
                if self.watch_behavior.should_take_break():
                    break_duration = self.watch_behavior.generate_break_duration()
                    logger.info(
                        "[YOUTUBE_SHORTS_SESSION] Taking break",
                        break_duration_s=round(break_duration, 2),
                    )
                    await asyncio.sleep(break_duration)

                # Watch current Short
                watch_result = await self.watch_short(page)
                watch_results.append(watch_result)

                if not watch_result.success:
                    errors.append(watch_result.error or "Watch failed")

                # Swipe to next Short
                swipe_result = await self.swipe_to_next(page)
                if not swipe_result.success:
                    errors.append(swipe_result.error or "Swipe failed")

        except Exception as e:
            errors.append(str(e))
            logger.error(
                "[YOUTUBE_SHORTS_SESSION] Session error",
                error=str(e),
            )

        end_time = datetime.now(UTC)

        if self._session_state:
            self.coherence_engine.end_session(self._session_state.session_id)

        logger.info(
            "[YOUTUBE_SHORTS_SESSION] ========== SESSION COMPLETED ==========",
            success=len(errors) == 0,
            shorts_watched=len(watch_results),
            error_count=len(errors),
        )

        return SessionResult(
            success=len(errors) == 0,
            platform=SocialPlatform.YOUTUBE,
            start_time=start_time,
            end_time=end_time,
            videos_watched=len(watch_results),
            bio_links_clicked=0,
            story_links_clicked=0,
            profiles_visited=self._channels_visited,
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
        """Run the full YouTube automation sequence.

        Priority:
        1. If target_video_urls or target_short_urls are configured, watch them directly
        2. Otherwise, run a Shorts session (or based on content_mode)

        Args:
            page: Browser page object
            url: Optional starting URL
            proxy_id: Proxy identifier for view tracking
            fingerprint_id: Fingerprint identifier for view tracking

        Returns:
            SessionResult
        """
        total_target_urls = len(self.config.target_video_urls) + len(self.config.target_short_urls)

        logger.info(
            "[YOUTUBE_RUN] Starting YouTube automation run",
            url=url,
            target_channel=self.config.target_channel,
            target_video_urls_count=len(self.config.target_video_urls),
            target_short_urls_count=len(self.config.target_short_urls),
            content_mode=self.config.content_mode,
            mode="direct_videos" if total_target_urls > 0 else self.config.content_mode,
        )

        # Setup context
        await self._setup_context(page)
        start_time = datetime.now(UTC)
        self._create_session()

        # PRIORITY 1: If target URLs are configured, watch them directly
        if total_target_urls > 0:
            all_urls = self.config.target_video_urls + self.config.target_short_urls

            logger.info(
                "[YOUTUBE_RUN] Running in DIRECT VIDEO mode",
                video_count=len(all_urls),
            )

            watch_results = await self.watch_direct_videos(
                page=page,
                video_urls=all_urls,
                proxy_id=proxy_id,
                fingerprint_id=fingerprint_id,
            )

            end_time = datetime.now(UTC)

            if self._session_state:
                self.coherence_engine.end_session(self._session_state.session_id)

            errors = [r.error for r in watch_results if r.error]

            return SessionResult(
                success=len(errors) == 0,
                platform=SocialPlatform.YOUTUBE,
                start_time=start_time,
                end_time=end_time,
                videos_watched=len(watch_results),
                bio_links_clicked=self._description_clicks,
                story_links_clicked=0,
                profiles_visited=self._channels_visited,
                errors=errors,
                watch_results=watch_results,
            )

        # PRIORITY 2: Run session based on content_mode
        if self.config.content_mode == "shorts":
            return await self.simulate_shorts_session(page)
        else:
            # For "videos" or "mixed" mode - just do shorts for now
            # (regular video feed browsing is more complex)
            return await self.simulate_shorts_session(page)

    async def run_batch(
        self,
        page: Any,
        video_urls: list[str],
        delay_between: tuple[float, float] = (30.0, 90.0),
        proxy_id: str = "",
        fingerprint_id: str = "",
    ) -> list[WatchResult]:
        """Run automation on multiple videos.

        Args:
            page: Browser page object
            video_urls: List of video URLs to watch
            delay_between: Min/max delay between videos
            proxy_id: Proxy identifier for view tracking
            fingerprint_id: Fingerprint identifier for view tracking

        Returns:
            List of WatchResults
        """
        logger.info(
            "[YOUTUBE_BATCH] ========== STARTING BATCH RUN ==========",
            total_videos=len(video_urls),
            delay_between_min_s=delay_between[0],
            delay_between_max_s=delay_between[1],
        )

        await self._setup_context(page)

        results = await self.watch_direct_videos(
            page=page,
            video_urls=video_urls,
            delay_between=delay_between,
            proxy_id=proxy_id,
            fingerprint_id=fingerprint_id,
        )

        logger.info(
            "[YOUTUBE_BATCH] ========== BATCH RUN COMPLETED ==========",
            total_videos=len(video_urls),
            successful_watches=sum(1 for r in results if r.success),
        )

        return results
