"""Social Media Behavior Patterns.

Provides realistic video watching behavior models for TikTok and Instagram:
- Watch duration distributions based on research
- Swipe timing patterns
- Engagement probability models
- Session behavior patterns

Based on statistical analysis of human social media usage.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)


class UserInterest(str, Enum):
    """User interest level affecting watch behavior."""

    LOW = "low"  # Quick skipping
    MEDIUM = "medium"  # Normal browsing
    HIGH = "high"  # Engaged viewing


@dataclass
class WatchDistribution:
    """Watch duration probability distribution."""

    # Probability of each outcome
    skip_prob: float  # Quick skip < 2s
    partial_prob: float  # Partial watch 20-80%
    full_prob: float  # Full watch 80-100%
    rewatch_prob: float  # Rewatch > 100%

    # Duration parameters for each outcome
    skip_min: float = 0.5
    skip_max: float = 2.0
    partial_min_pct: float = 0.2
    partial_max_pct: float = 0.8
    full_min_pct: float = 0.95
    full_max_pct: float = 1.05
    rewatch_min_pct: float = 1.0
    rewatch_max_pct: float = 2.5


# TikTok watch distributions by user interest
TIKTOK_DISTRIBUTIONS = {
    UserInterest.LOW: WatchDistribution(
        skip_prob=0.50,
        partial_prob=0.35,
        full_prob=0.12,
        rewatch_prob=0.03,
    ),
    UserInterest.MEDIUM: WatchDistribution(
        skip_prob=0.30,
        partial_prob=0.40,
        full_prob=0.20,
        rewatch_prob=0.10,
    ),
    UserInterest.HIGH: WatchDistribution(
        skip_prob=0.15,
        partial_prob=0.30,
        full_prob=0.35,
        rewatch_prob=0.20,
    ),
}

# Instagram Reels watch distributions
INSTAGRAM_DISTRIBUTIONS = {
    UserInterest.LOW: WatchDistribution(
        skip_prob=0.45,
        partial_prob=0.40,
        full_prob=0.12,
        rewatch_prob=0.03,
    ),
    UserInterest.MEDIUM: WatchDistribution(
        skip_prob=0.35,
        partial_prob=0.35,
        full_prob=0.25,
        rewatch_prob=0.05,
    ),
    UserInterest.HIGH: WatchDistribution(
        skip_prob=0.20,
        partial_prob=0.30,
        full_prob=0.35,
        rewatch_prob=0.15,
    ),
}

# YouTube regular video watch distributions
# Videos are longer (5-60 min), higher skip if not interested
# CRITICAL: Must watch 30s minimum for view to count
YOUTUBE_DISTRIBUTIONS = {
    UserInterest.LOW: WatchDistribution(
        skip_prob=0.40,
        partial_prob=0.45,
        full_prob=0.12,
        rewatch_prob=0.03,
        # Longer skip times - need 30s for view count
        skip_min=5.0,
        skip_max=35.0,  # Sometimes watch just over threshold
        partial_min_pct=0.10,  # 10% of long videos
        partial_max_pct=0.50,
    ),
    UserInterest.MEDIUM: WatchDistribution(
        skip_prob=0.25,
        partial_prob=0.45,
        full_prob=0.25,
        rewatch_prob=0.05,
        skip_min=20.0,
        skip_max=45.0,
        partial_min_pct=0.20,
        partial_max_pct=0.70,
    ),
    UserInterest.HIGH: WatchDistribution(
        skip_prob=0.10,
        partial_prob=0.35,
        full_prob=0.40,
        rewatch_prob=0.15,
        skip_min=30.0,
        skip_max=60.0,
        partial_min_pct=0.40,
        partial_max_pct=0.90,
    ),
}

# YouTube Shorts watch distributions (similar to TikTok)
YOUTUBE_SHORTS_DISTRIBUTIONS = {
    UserInterest.LOW: WatchDistribution(
        skip_prob=0.45,
        partial_prob=0.38,
        full_prob=0.14,
        rewatch_prob=0.03,
    ),
    UserInterest.MEDIUM: WatchDistribution(
        skip_prob=0.28,
        partial_prob=0.40,
        full_prob=0.22,
        rewatch_prob=0.10,
    ),
    UserInterest.HIGH: WatchDistribution(
        skip_prob=0.12,
        partial_prob=0.30,
        full_prob=0.38,
        rewatch_prob=0.20,
    ),
}


@dataclass
class SwipePattern:
    """Swipe gesture pattern parameters."""

    # Duration ranges (ms)
    flick_duration: tuple[int, int] = (150, 280)
    deliberate_duration: tuple[int, int] = (300, 500)
    slow_duration: tuple[int, int] = (500, 800)

    # Probability of each intensity
    flick_prob: float = 0.6
    deliberate_prob: float = 0.3
    slow_prob: float = 0.1

    # Pause before scroll (seconds)
    pre_scroll_pause: tuple[float, float] = (0.3, 1.5)

    # Probability of scroll back (viewing previous)
    scroll_back_prob: float = 0.08


@dataclass
class SessionPattern:
    """Session behavior pattern parameters."""

    # Videos per session
    videos_min: int = 10
    videos_max: int = 40

    # Session duration (minutes)
    duration_min: float = 5.0
    duration_max: float = 25.0

    # Profile visit probability per video
    profile_visit_prob: float = 0.10

    # Bio link click probability when visiting profile
    bio_click_prob: float = 0.20

    # Like probability (set to 0 for passive watching)
    like_prob: float = 0.0

    # Comment probability (set to 0 for passive watching)
    comment_prob: float = 0.0

    # Break probability per 10 videos
    break_prob: float = 0.15

    # Break duration (seconds)
    break_duration: tuple[float, float] = (5.0, 30.0)


# Platform-specific session patterns
TIKTOK_SESSION = SessionPattern(
    videos_min=10,
    videos_max=50,
    duration_min=5.0,
    duration_max=20.0,
    profile_visit_prob=0.08,
    bio_click_prob=0.15,
)

INSTAGRAM_SESSION = SessionPattern(
    videos_min=5,
    videos_max=25,
    duration_min=5.0,
    duration_max=15.0,
    profile_visit_prob=0.12,
    bio_click_prob=0.20,
)

# YouTube regular video session pattern
YOUTUBE_SESSION = SessionPattern(
    videos_min=3,
    videos_max=15,
    duration_min=10.0,  # Longer videos
    duration_max=60.0,  # Can be very long sessions
    profile_visit_prob=0.08,  # Channel visits
    bio_click_prob=0.10,  # Description link clicks
)

# YouTube Shorts session pattern (similar to TikTok)
YOUTUBE_SHORTS_SESSION = SessionPattern(
    videos_min=10,
    videos_max=40,
    duration_min=5.0,
    duration_max=20.0,
    profile_visit_prob=0.06,
    bio_click_prob=0.08,
)


class VideoWatchBehavior:
    """Statistical model for video watching behavior.

    Generates realistic watch durations and patterns based on
    observed human behavior distributions.
    """

    def __init__(
        self,
        platform: Literal["tiktok", "instagram", "youtube", "youtube_shorts"] = "tiktok",
        interest_level: UserInterest = UserInterest.MEDIUM,
    ) -> None:
        """Initialize video watch behavior model.

        Args:
            platform: Social media platform
            interest_level: User interest level
        """
        self.platform = platform
        self.interest_level = interest_level

        if platform == "tiktok":
            self.distribution = TIKTOK_DISTRIBUTIONS[interest_level]
            self.session_pattern = TIKTOK_SESSION
        elif platform == "instagram":
            self.distribution = INSTAGRAM_DISTRIBUTIONS[interest_level]
            self.session_pattern = INSTAGRAM_SESSION
        elif platform == "youtube":
            self.distribution = YOUTUBE_DISTRIBUTIONS[interest_level]
            self.session_pattern = YOUTUBE_SESSION
        elif platform == "youtube_shorts":
            self.distribution = YOUTUBE_SHORTS_DISTRIBUTIONS[interest_level]
            self.session_pattern = YOUTUBE_SHORTS_SESSION
        else:
            # Default to TikTok behavior
            self.distribution = TIKTOK_DISTRIBUTIONS[interest_level]
            self.session_pattern = TIKTOK_SESSION

        self.swipe_pattern = SwipePattern()
        self._videos_watched = 0
        self._session_start = 0.0

    def generate_watch_duration(
        self,
        video_duration: float | None = None,
        content_interest: float = 0.5,
    ) -> tuple[float, str]:
        """Generate realistic watch duration for a video.

        Uses mixture model:
        - Skip: Quick exit (exponential decay)
        - Partial: Moderate watch (beta distribution around 50%)
        - Full: Complete watch (normal around 100%)
        - Rewatch: Extended viewing (lognormal > 100%)

        Args:
            video_duration: Video length in seconds (uses estimate if None)
            content_interest: Content interest modifier (0-1)

        Returns:
            Tuple of (watch_duration, outcome_type)
        """
        # Estimate video duration if unknown (platform-dependent)
        if video_duration is None:
            if self.platform == "youtube":
                # YouTube videos average 5-15 minutes
                video_duration = random.uniform(300.0, 900.0)
            elif self.platform == "youtube_shorts":
                # Shorts are 15-60 seconds
                video_duration = random.uniform(15.0, 60.0)
            else:
                # TikTok/Instagram Reels average 15-45 seconds
                video_duration = random.uniform(15.0, 45.0)

        # Adjust probabilities based on content interest
        dist = self.distribution
        skip_prob = dist.skip_prob - (content_interest * 0.15)
        full_prob = dist.full_prob + (content_interest * 0.15)
        rewatch_prob = dist.rewatch_prob + (content_interest * 0.10)
        partial_prob = 1.0 - skip_prob - full_prob - rewatch_prob

        # Ensure probabilities are valid
        skip_prob = max(0.05, min(0.7, skip_prob))
        full_prob = max(0.05, min(0.5, full_prob))
        rewatch_prob = max(0.0, min(0.3, rewatch_prob))
        partial_prob = max(0.1, 1.0 - skip_prob - full_prob - rewatch_prob)

        roll = random.random()

        if roll < skip_prob:
            # Quick skip - exponential distribution
            # Mean around 1 second, max around 2 seconds
            duration = self._exponential_sample(
                mean=1.0,
                min_val=dist.skip_min,
                max_val=dist.skip_max,
            )
            logger.debug(
                "[BEHAVIOR_WATCH] Watch decision: SKIP",
                platform=self.platform,
                video_duration_s=round(video_duration, 2),
                watch_duration_s=round(duration, 2),
                content_interest=round(content_interest, 2),
                roll=round(roll, 3),
                threshold=round(skip_prob, 3),
            )
            return duration, "skipped"

        elif roll < skip_prob + partial_prob:
            # Partial watch - beta distribution centered around 50%
            # Shape parameters for beta distribution
            alpha, beta = 2.0, 2.0  # Symmetric around 0.5
            completion = random.betavariate(alpha, beta)
            # Scale to partial range
            completion = dist.partial_min_pct + completion * (
                dist.partial_max_pct - dist.partial_min_pct
            )
            duration = video_duration * completion
            logger.debug(
                "[BEHAVIOR_WATCH] Watch decision: PARTIAL",
                platform=self.platform,
                video_duration_s=round(video_duration, 2),
                watch_duration_s=round(duration, 2),
                completion_pct=round(completion * 100, 1),
                content_interest=round(content_interest, 2),
            )
            return duration, "partial"

        elif roll < skip_prob + partial_prob + full_prob:
            # Full watch - normal distribution around 100%
            completion = random.gauss(1.0, 0.05)
            completion = max(dist.full_min_pct, min(dist.full_max_pct, completion))
            duration = video_duration * completion
            logger.debug(
                "[BEHAVIOR_WATCH] Watch decision: FULL",
                platform=self.platform,
                video_duration_s=round(video_duration, 2),
                watch_duration_s=round(duration, 2),
                completion_pct=round(completion * 100, 1),
                content_interest=round(content_interest, 2),
            )
            return duration, "full"

        else:
            # Rewatch - lognormal distribution for extended viewing
            # Can be 1x to 2.5x video duration
            mu = 0.3  # ln(1.35) roughly
            sigma = 0.4
            multiplier = random.lognormvariate(mu, sigma)
            multiplier = max(dist.rewatch_min_pct, min(dist.rewatch_max_pct, multiplier))
            duration = video_duration * multiplier
            replays = int(multiplier)
            logger.debug(
                "[BEHAVIOR_WATCH] Watch decision: REWATCH",
                platform=self.platform,
                video_duration_s=round(video_duration, 2),
                watch_duration_s=round(duration, 2),
                multiplier=round(multiplier, 2),
                replays=replays,
                content_interest=round(content_interest, 2),
            )
            return duration, "rewatched"

    def _exponential_sample(
        self,
        mean: float,
        min_val: float,
        max_val: float,
    ) -> float:
        """Sample from truncated exponential distribution."""
        sample = random.expovariate(1 / mean)
        return max(min_val, min(max_val, sample + min_val))

    def generate_scroll_timing(self) -> tuple[float, str]:
        """Generate time and intensity before scrolling to next video.

        Returns:
            Tuple of (pause_duration_seconds, swipe_intensity)
        """
        pattern = self.swipe_pattern

        # Pre-scroll pause
        pause = random.uniform(*pattern.pre_scroll_pause)

        # Swipe intensity
        roll = random.random()
        if roll < pattern.flick_prob:
            intensity = "flick"
        elif roll < pattern.flick_prob + pattern.deliberate_prob:
            intensity = "deliberate"
        else:
            intensity = "slow"

        return pause, intensity

    def should_scroll_back(self) -> bool:
        """Determine if user should scroll back to previous video."""
        return random.random() < self.swipe_pattern.scroll_back_prob

    def should_visit_profile(self) -> bool:
        """Determine if user should visit the creator's profile."""
        return random.random() < self.session_pattern.profile_visit_prob

    def should_click_bio(self) -> bool:
        """Determine if user should click the bio link."""
        return random.random() < self.session_pattern.bio_click_prob

    def should_take_break(self) -> bool:
        """Determine if user should take a break."""
        # Check every 10 videos
        if self._videos_watched > 0 and self._videos_watched % 10 == 0:
            return random.random() < self.session_pattern.break_prob
        return False

    def generate_break_duration(self) -> float:
        """Generate a break duration in seconds."""
        return random.uniform(*self.session_pattern.break_duration)

    def generate_session_length(self) -> int:
        """Generate target number of videos for this session."""
        length = random.randint(
            self.session_pattern.videos_min,
            self.session_pattern.videos_max,
        )
        logger.info(
            "[BEHAVIOR_SESSION] Generated session length",
            platform=self.platform,
            target_videos=length,
            min_videos=self.session_pattern.videos_min,
            max_videos=self.session_pattern.videos_max,
        )
        return length

    def record_video_watched(self) -> None:
        """Record that a video was watched."""
        self._videos_watched += 1
        logger.debug(
            "[BEHAVIOR_SESSION] Video watched recorded",
            platform=self.platform,
            total_videos_watched=self._videos_watched,
        )

    def reset_session(self) -> None:
        """Reset session counters."""
        logger.debug(
            "[BEHAVIOR_SESSION] Session reset",
            platform=self.platform,
            videos_watched_before_reset=self._videos_watched,
        )
        self._videos_watched = 0
        self._session_start = 0.0


@dataclass
class StoryWatchBehavior:
    """Behavior model for Instagram Stories viewing."""

    # Base view duration per story (seconds)
    view_duration_min: float = 2.0
    view_duration_max: float = 8.0

    # Skip probability
    skip_prob: float = 0.20

    # Skip duration (seconds)
    skip_duration_min: float = 0.5
    skip_duration_max: float = 1.5

    # Link click probability when link sticker is present
    link_click_prob: float = 0.25

    # Tap forward probability (vs auto-advance)
    tap_forward_prob: float = 0.40

    # Tap back probability
    tap_back_prob: float = 0.08

    # Pause/hold probability
    pause_prob: float = 0.15

    # Pause duration (seconds)
    pause_duration_min: float = 1.0
    pause_duration_max: float = 4.0

    def generate_view_duration(
        self,
        story_duration: float | None = None,
        has_link: bool = False,
    ) -> tuple[float, str]:
        """Generate story view duration.

        Args:
            story_duration: Story duration if known (default 5s for images)
            has_link: Whether story has a link sticker

        Returns:
            Tuple of (view_duration, action)
        """
        if story_duration is None:
            story_duration = 5.0  # Default for images

        # Decide action
        roll = random.random()

        if roll < self.skip_prob:
            # Skip early
            duration = random.uniform(
                self.skip_duration_min,
                self.skip_duration_max,
            )
            logger.debug(
                "[BEHAVIOR_STORY] Story decision: SKIP",
                duration_s=round(duration, 2),
                has_link=has_link,
            )
            return duration, "skipped"

        elif has_link and random.random() < self.link_click_prob:
            # View then click link
            duration = random.uniform(
                self.view_duration_min,
                story_duration * 0.8,
            )
            logger.debug(
                "[BEHAVIOR_STORY] Story decision: LINK_CLICK",
                duration_s=round(duration, 2),
                has_link=has_link,
            )
            return duration, "link_clicked"

        elif random.random() < self.pause_prob:
            # Pause on story
            pause = random.uniform(
                self.pause_duration_min,
                self.pause_duration_max,
            )
            logger.debug(
                "[BEHAVIOR_STORY] Story decision: PAUSE",
                duration_s=round(story_duration + pause, 2),
                pause_s=round(pause, 2),
            )
            return story_duration + pause, "paused"

        else:
            # Normal view
            duration = random.uniform(
                min(self.view_duration_min, story_duration),
                min(self.view_duration_max, story_duration * 1.2),
            )
            logger.debug(
                "[BEHAVIOR_STORY] Story decision: VIEW",
                duration_s=round(duration, 2),
                has_link=has_link,
            )
            return duration, "viewed"

    def should_tap_forward(self) -> bool:
        """Determine if user taps to advance vs waiting."""
        return random.random() < self.tap_forward_prob

    def should_tap_back(self) -> bool:
        """Determine if user taps back to previous story."""
        return random.random() < self.tap_back_prob


class InAppBrowserBehavior:
    """Behavior model for in-app browser after clicking links."""

    def __init__(
        self,
        platform: Literal["tiktok", "instagram", "youtube"] = "instagram",
    ) -> None:
        """Initialize in-app browser behavior.

        Args:
            platform: Source platform
        """
        self.platform = platform

    def generate_dwell_time(
        self,
        content_type: Literal["landing", "article", "product", "video"] = "landing",
    ) -> float:
        """Generate time spent on linked page.

        Args:
            content_type: Type of content on the page

        Returns:
            Dwell time in seconds
        """
        base_times = {
            "landing": (10.0, 45.0),
            "article": (30.0, 120.0),
            "product": (15.0, 60.0),
            "video": (20.0, 90.0),
        }

        min_time, max_time = base_times.get(content_type, (10.0, 45.0))
        dwell_time = random.uniform(min_time, max_time)

        logger.debug(
            "[BEHAVIOR_INAPP] Generated dwell time for external page",
            platform=self.platform,
            content_type=content_type,
            dwell_time_s=round(dwell_time, 2),
            time_range=f"{min_time}-{max_time}s",
        )

        return dwell_time

    def generate_scroll_pattern(
        self,
        page_height_estimate: int = 3000,
    ) -> list[tuple[int, float]]:
        """Generate scroll positions and timings for the page.

        Args:
            page_height_estimate: Estimated page height in pixels

        Returns:
            List of (scroll_position, pause_duration) tuples
        """
        positions = []
        current_pos = 0
        max_pos = page_height_estimate * 0.8  # Usually don't scroll to absolute bottom

        while current_pos < max_pos:
            # Scroll amount varies
            scroll_amount = random.randint(200, 500)
            current_pos = min(current_pos + scroll_amount, max_pos)

            # Pause at this position
            pause = random.uniform(0.5, 3.0)

            positions.append((current_pos, pause))

            # Sometimes skip ahead more
            if random.random() < 0.2:
                current_pos += random.randint(300, 600)

        return positions

    def should_return_to_app(self, time_spent: float) -> bool:
        """Determine if user should return to social media app.

        Args:
            time_spent: Time already spent on page

        Returns:
            True if user should return
        """
        # Probability increases with time
        base_prob = 0.1
        time_factor = time_spent / 60.0  # Increases per minute
        return random.random() < min(0.9, base_prob + time_factor * 0.15)
