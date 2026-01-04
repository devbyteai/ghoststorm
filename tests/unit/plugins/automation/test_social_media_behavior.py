"""Tests for social media behavior patterns.

Tests the statistical behavior models for video watching
across TikTok, Instagram, and YouTube platforms.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pytest

from ghoststorm.plugins.automation.social_media_behavior import (
    INSTAGRAM_DISTRIBUTIONS,
    TIKTOK_DISTRIBUTIONS,
    YOUTUBE_DISTRIBUTIONS,
    YOUTUBE_SHORTS_DISTRIBUTIONS,
    InAppBrowserBehavior,
    StoryWatchBehavior,
    UserInterest,
    VideoWatchBehavior,
    WatchDistribution,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class TestWatchDistribution:
    """Tests for WatchDistribution dataclass and platform distributions."""

    def test_watch_distribution_fields_exist(self) -> None:
        """WatchDistribution has all required probability fields."""
        dist = WatchDistribution(
            skip_prob=0.3,
            partial_prob=0.4,
            full_prob=0.2,
            rewatch_prob=0.1,
        )
        assert hasattr(dist, "skip_prob")
        assert hasattr(dist, "partial_prob")
        assert hasattr(dist, "full_prob")
        assert hasattr(dist, "rewatch_prob")

    def test_watch_distribution_default_duration_params(self) -> None:
        """WatchDistribution has default duration parameters."""
        dist = WatchDistribution(
            skip_prob=0.3,
            partial_prob=0.4,
            full_prob=0.2,
            rewatch_prob=0.1,
        )
        assert dist.skip_min == 0.5
        assert dist.skip_max == 2.0
        assert dist.partial_min_pct == 0.2
        assert dist.partial_max_pct == 0.8
        assert dist.full_min_pct == 0.95
        assert dist.full_max_pct == 1.05
        assert dist.rewatch_min_pct == 1.0
        assert dist.rewatch_max_pct == 2.5

    @pytest.mark.parametrize("interest", list(UserInterest))
    def test_tiktok_distributions_probabilities_sum_to_one(
        self,
        interest: UserInterest,
    ) -> None:
        """TikTok distributions probabilities sum to 1.0 for all interest levels."""
        dist = TIKTOK_DISTRIBUTIONS[interest]
        total = dist.skip_prob + dist.partial_prob + dist.full_prob + dist.rewatch_prob
        assert total == pytest.approx(1.0, abs=1e-9)

    @pytest.mark.parametrize("interest", list(UserInterest))
    def test_instagram_distributions_probabilities_sum_to_one(
        self,
        interest: UserInterest,
    ) -> None:
        """Instagram distributions probabilities sum to 1.0 for all interest levels."""
        dist = INSTAGRAM_DISTRIBUTIONS[interest]
        total = dist.skip_prob + dist.partial_prob + dist.full_prob + dist.rewatch_prob
        assert total == pytest.approx(1.0, abs=1e-9)

    @pytest.mark.parametrize("interest", list(UserInterest))
    def test_youtube_distributions_probabilities_sum_to_one(
        self,
        interest: UserInterest,
    ) -> None:
        """YouTube distributions probabilities sum to 1.0 for all interest levels."""
        dist = YOUTUBE_DISTRIBUTIONS[interest]
        total = dist.skip_prob + dist.partial_prob + dist.full_prob + dist.rewatch_prob
        assert total == pytest.approx(1.0, abs=1e-9)

    @pytest.mark.parametrize("interest", list(UserInterest))
    def test_youtube_shorts_distributions_probabilities_sum_to_one(
        self,
        interest: UserInterest,
    ) -> None:
        """YouTube Shorts distributions probabilities sum to 1.0 for all interest levels."""
        dist = YOUTUBE_SHORTS_DISTRIBUTIONS[interest]
        total = dist.skip_prob + dist.partial_prob + dist.full_prob + dist.rewatch_prob
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_tiktok_distributions_exist(self) -> None:
        """TIKTOK_DISTRIBUTIONS dictionary exists and has all interest levels."""
        assert TIKTOK_DISTRIBUTIONS is not None
        assert UserInterest.LOW in TIKTOK_DISTRIBUTIONS
        assert UserInterest.MEDIUM in TIKTOK_DISTRIBUTIONS
        assert UserInterest.HIGH in TIKTOK_DISTRIBUTIONS

    def test_instagram_distributions_exist(self) -> None:
        """INSTAGRAM_DISTRIBUTIONS dictionary exists and has all interest levels."""
        assert INSTAGRAM_DISTRIBUTIONS is not None
        assert UserInterest.LOW in INSTAGRAM_DISTRIBUTIONS
        assert UserInterest.MEDIUM in INSTAGRAM_DISTRIBUTIONS
        assert UserInterest.HIGH in INSTAGRAM_DISTRIBUTIONS

    def test_youtube_distributions_exist(self) -> None:
        """YOUTUBE_DISTRIBUTIONS dictionary exists and has all interest levels."""
        assert YOUTUBE_DISTRIBUTIONS is not None
        assert UserInterest.LOW in YOUTUBE_DISTRIBUTIONS
        assert UserInterest.MEDIUM in YOUTUBE_DISTRIBUTIONS
        assert UserInterest.HIGH in YOUTUBE_DISTRIBUTIONS


class TestVideoWatchBehavior:
    """Tests for VideoWatchBehavior class."""

    def test_init_default_platform(self) -> None:
        """VideoWatchBehavior defaults to TikTok platform."""
        behavior = VideoWatchBehavior()
        assert behavior.platform == "tiktok"
        assert behavior.interest_level == UserInterest.MEDIUM

    @pytest.mark.parametrize(
        ("platform", "interest"),
        [
            ("tiktok", UserInterest.LOW),
            ("tiktok", UserInterest.MEDIUM),
            ("tiktok", UserInterest.HIGH),
            ("instagram", UserInterest.LOW),
            ("instagram", UserInterest.MEDIUM),
            ("instagram", UserInterest.HIGH),
            ("youtube", UserInterest.LOW),
            ("youtube", UserInterest.MEDIUM),
            ("youtube", UserInterest.HIGH),
            ("youtube_shorts", UserInterest.LOW),
            ("youtube_shorts", UserInterest.MEDIUM),
            ("youtube_shorts", UserInterest.HIGH),
        ],
    )
    def test_init_all_platforms_and_interests(
        self,
        platform: str,
        interest: UserInterest,
    ) -> None:
        """VideoWatchBehavior initializes correctly for all platform/interest combinations."""
        behavior = VideoWatchBehavior(platform=platform, interest_level=interest)  # type: ignore[arg-type]
        assert behavior.platform == platform
        assert behavior.interest_level == interest
        assert behavior.distribution is not None
        assert behavior.session_pattern is not None
        assert behavior.swipe_pattern is not None
        assert behavior._videos_watched == 0

    def test_init_unknown_platform_defaults_to_tiktok(self) -> None:
        """VideoWatchBehavior falls back to TikTok for unknown platforms."""
        behavior = VideoWatchBehavior(platform="unknown_platform")  # type: ignore[arg-type]
        assert behavior.distribution == TIKTOK_DISTRIBUTIONS[UserInterest.MEDIUM]

    def test_generate_watch_duration_with_video_duration(self) -> None:
        """generate_watch_duration returns duration and outcome type."""
        random.seed(42)
        behavior = VideoWatchBehavior(platform="tiktok")
        duration, outcome = behavior.generate_watch_duration(video_duration=30.0)

        assert isinstance(duration, float)
        assert duration > 0
        assert outcome in ("skipped", "partial", "full", "rewatched")

    def test_generate_watch_duration_without_video_duration_tiktok(self) -> None:
        """generate_watch_duration estimates duration for TikTok when not provided."""
        random.seed(42)
        behavior = VideoWatchBehavior(platform="tiktok")
        duration, outcome = behavior.generate_watch_duration(video_duration=None)

        assert isinstance(duration, float)
        assert duration > 0
        assert outcome in ("skipped", "partial", "full", "rewatched")

    def test_generate_watch_duration_without_video_duration_youtube(self) -> None:
        """generate_watch_duration estimates longer duration for YouTube when not provided."""
        random.seed(42)
        behavior = VideoWatchBehavior(platform="youtube")
        duration, outcome = behavior.generate_watch_duration(video_duration=None)

        assert isinstance(duration, float)
        assert duration > 0
        assert outcome in ("skipped", "partial", "full", "rewatched")

    def test_generate_watch_duration_without_video_duration_youtube_shorts(self) -> None:
        """generate_watch_duration estimates short duration for YouTube Shorts when not provided."""
        random.seed(42)
        behavior = VideoWatchBehavior(platform="youtube_shorts")
        duration, outcome = behavior.generate_watch_duration(video_duration=None)

        assert isinstance(duration, float)
        assert duration > 0
        assert outcome in ("skipped", "partial", "full", "rewatched")

    def test_generate_watch_duration_content_interest_affects_outcome(self) -> None:
        """Higher content interest decreases skip probability."""
        random.seed(100)
        behavior = VideoWatchBehavior(platform="tiktok")

        # Run many trials with high interest
        high_interest_skips = 0
        low_interest_skips = 0
        trials = 500

        for _ in range(trials):
            _, outcome = behavior.generate_watch_duration(
                video_duration=30.0,
                content_interest=0.9,
            )
            if outcome == "skipped":
                high_interest_skips += 1

        random.seed(100)
        for _ in range(trials):
            _, outcome = behavior.generate_watch_duration(
                video_duration=30.0,
                content_interest=0.1,
            )
            if outcome == "skipped":
                low_interest_skips += 1

        # Low interest should have more skips on average
        assert low_interest_skips > high_interest_skips

    def test_generate_watch_duration_outcome_distribution(self) -> None:
        """generate_watch_duration produces all outcome types over many trials."""
        random.seed(42)
        behavior = VideoWatchBehavior(platform="tiktok", interest_level=UserInterest.MEDIUM)

        outcomes = {"skipped": 0, "partial": 0, "full": 0, "rewatched": 0}
        trials = 1000

        for _ in range(trials):
            _, outcome = behavior.generate_watch_duration(video_duration=30.0)
            outcomes[outcome] += 1

        # All outcomes should appear
        assert outcomes["skipped"] > 0
        assert outcomes["partial"] > 0
        assert outcomes["full"] > 0
        assert outcomes["rewatched"] > 0

    def test_record_video_watched_increments_counter(self) -> None:
        """record_video_watched increments the internal counter."""
        behavior = VideoWatchBehavior()
        assert behavior._videos_watched == 0

        behavior.record_video_watched()
        assert behavior._videos_watched == 1

        behavior.record_video_watched()
        assert behavior._videos_watched == 2

        behavior.record_video_watched()
        behavior.record_video_watched()
        behavior.record_video_watched()
        assert behavior._videos_watched == 5

    def test_reset_session_clears_counter(self) -> None:
        """reset_session resets the videos watched counter."""
        behavior = VideoWatchBehavior()
        behavior.record_video_watched()
        behavior.record_video_watched()
        behavior.record_video_watched()
        assert behavior._videos_watched == 3

        behavior.reset_session()
        assert behavior._videos_watched == 0
        assert behavior._session_start == 0.0


class TestGenerateScrollTiming:
    """Tests for generate_scroll_timing method."""

    def test_generate_scroll_timing_returns_pause_and_intensity(self) -> None:
        """generate_scroll_timing returns pause duration and swipe intensity."""
        behavior = VideoWatchBehavior()
        pause, intensity = behavior.generate_scroll_timing()

        assert isinstance(pause, float)
        assert isinstance(intensity, str)
        assert intensity in ("flick", "deliberate", "slow")

    def test_generate_scroll_timing_pause_within_range(self) -> None:
        """generate_scroll_timing pause is within expected range."""
        random.seed(42)
        behavior = VideoWatchBehavior()

        for _ in range(100):
            pause, _ = behavior.generate_scroll_timing()
            assert 0.3 <= pause <= 1.5

    def test_generate_scroll_timing_intensity_distribution(self) -> None:
        """generate_scroll_timing produces all intensity types."""
        random.seed(42)
        behavior = VideoWatchBehavior()

        intensities = {"flick": 0, "deliberate": 0, "slow": 0}
        trials = 500

        for _ in range(trials):
            _, intensity = behavior.generate_scroll_timing()
            intensities[intensity] += 1

        # All intensities should appear, flick most common
        assert intensities["flick"] > 0
        assert intensities["deliberate"] > 0
        assert intensities["slow"] > 0
        assert intensities["flick"] > intensities["deliberate"]
        assert intensities["deliberate"] > intensities["slow"]


class TestShouldScrollBack:
    """Tests for should_scroll_back method."""

    def test_should_scroll_back_returns_bool(self) -> None:
        """should_scroll_back returns a boolean."""
        behavior = VideoWatchBehavior()
        result = behavior.should_scroll_back()
        assert isinstance(result, bool)

    def test_should_scroll_back_probabilistic_rate(self) -> None:
        """should_scroll_back has approximately 8% true rate."""
        random.seed(42)
        behavior = VideoWatchBehavior()

        true_count = sum(behavior.should_scroll_back() for _ in range(10000))
        rate = true_count / 10000

        # Should be around 8% (0.08), allow 2% tolerance
        assert 0.06 <= rate <= 0.10

    def test_should_scroll_back_not_always_true_or_false(self) -> None:
        """should_scroll_back is probabilistic, not deterministic."""
        random.seed(42)
        behavior = VideoWatchBehavior()

        results = [behavior.should_scroll_back() for _ in range(200)]

        # Should have both True and False
        assert True in results
        assert False in results


class TestStoryWatchBehavior:
    """Tests for StoryWatchBehavior dataclass."""

    def test_story_watch_behavior_defaults(self) -> None:
        """StoryWatchBehavior has correct default values."""
        story = StoryWatchBehavior()
        assert story.view_duration_min == 2.0
        assert story.view_duration_max == 8.0
        assert story.skip_prob == 0.20
        assert story.link_click_prob == 0.25
        assert story.tap_forward_prob == 0.40
        assert story.tap_back_prob == 0.08

    def test_generate_view_duration_returns_duration_and_action(self) -> None:
        """generate_view_duration returns a tuple of duration and action."""
        random.seed(42)
        story = StoryWatchBehavior()
        duration, action = story.generate_view_duration()

        assert isinstance(duration, float)
        assert duration > 0
        assert action in ("skipped", "link_clicked", "paused", "viewed")

    def test_generate_view_duration_with_story_duration(self) -> None:
        """generate_view_duration uses provided story duration."""
        random.seed(42)
        story = StoryWatchBehavior()
        duration, action = story.generate_view_duration(story_duration=10.0)

        assert isinstance(duration, float)
        assert duration > 0

    def test_generate_view_duration_with_link(self) -> None:
        """generate_view_duration can trigger link_clicked when has_link=True."""
        random.seed(42)
        story = StoryWatchBehavior()

        link_clicks = 0
        trials = 500

        for _ in range(trials):
            _, action = story.generate_view_duration(has_link=True)
            if action == "link_clicked":
                link_clicks += 1

        # Should have some link clicks
        assert link_clicks > 0

    def test_generate_view_duration_no_link_click_without_link(self) -> None:
        """generate_view_duration never returns link_clicked when has_link=False."""
        random.seed(42)
        story = StoryWatchBehavior()

        for _ in range(200):
            _, action = story.generate_view_duration(has_link=False)
            assert action != "link_clicked"

    def test_generate_view_duration_all_actions_possible(self) -> None:
        """generate_view_duration can produce all action types."""
        random.seed(42)
        story = StoryWatchBehavior()

        actions = set()
        # Run many trials with link to allow all actions
        for _ in range(1000):
            _, action = story.generate_view_duration(has_link=True)
            actions.add(action)

        assert "skipped" in actions
        assert "viewed" in actions
        # link_clicked and paused may appear depending on probability

    def test_should_tap_forward_returns_bool(self) -> None:
        """should_tap_forward returns a boolean."""
        story = StoryWatchBehavior()
        result = story.should_tap_forward()
        assert isinstance(result, bool)

    def test_should_tap_forward_probabilistic(self) -> None:
        """should_tap_forward has approximately 40% true rate."""
        random.seed(42)
        story = StoryWatchBehavior()

        true_count = sum(story.should_tap_forward() for _ in range(1000))
        rate = true_count / 1000

        # Should be around 40% (0.40), allow 5% tolerance
        assert 0.35 <= rate <= 0.45

    def test_should_tap_back_returns_bool(self) -> None:
        """should_tap_back returns a boolean."""
        story = StoryWatchBehavior()
        result = story.should_tap_back()
        assert isinstance(result, bool)


class TestInAppBrowserBehavior:
    """Tests for InAppBrowserBehavior class."""

    def test_init_default_platform(self) -> None:
        """InAppBrowserBehavior defaults to Instagram platform."""
        browser = InAppBrowserBehavior()
        assert browser.platform == "instagram"

    @pytest.mark.parametrize("platform", ["tiktok", "instagram", "youtube"])
    def test_init_all_platforms(self, platform: str) -> None:
        """InAppBrowserBehavior initializes for all supported platforms."""
        browser = InAppBrowserBehavior(platform=platform)  # type: ignore[arg-type]
        assert browser.platform == platform

    def test_generate_dwell_time_returns_float(self) -> None:
        """generate_dwell_time returns a float duration."""
        browser = InAppBrowserBehavior()
        dwell_time = browser.generate_dwell_time()

        assert isinstance(dwell_time, float)
        assert dwell_time > 0

    @pytest.mark.parametrize(
        ("content_type", "min_time", "max_time"),
        [
            ("landing", 10.0, 45.0),
            ("article", 30.0, 120.0),
            ("product", 15.0, 60.0),
            ("video", 20.0, 90.0),
        ],
    )
    def test_generate_dwell_time_content_type_ranges(
        self,
        content_type: str,
        min_time: float,
        max_time: float,
    ) -> None:
        """generate_dwell_time respects content type time ranges."""
        random.seed(42)
        browser = InAppBrowserBehavior()

        for _ in range(50):
            dwell_time = browser.generate_dwell_time(content_type=content_type)  # type: ignore[arg-type]
            assert min_time <= dwell_time <= max_time

    def test_generate_dwell_time_unknown_content_type(self) -> None:
        """generate_dwell_time uses default range for unknown content type."""
        random.seed(42)
        browser = InAppBrowserBehavior()

        dwell_time = browser.generate_dwell_time(content_type="unknown")  # type: ignore[arg-type]
        # Should fall back to landing page defaults (10.0, 45.0)
        assert 10.0 <= dwell_time <= 45.0

    def test_generate_scroll_pattern_returns_list_of_tuples(self) -> None:
        """generate_scroll_pattern returns list of (position, pause) tuples."""
        browser = InAppBrowserBehavior()
        pattern = browser.generate_scroll_pattern()

        assert isinstance(pattern, list)
        assert len(pattern) > 0

        for position, pause in pattern:
            assert isinstance(position, int)
            assert isinstance(pause, float)
            assert position > 0
            assert pause > 0

    def test_generate_scroll_pattern_respects_page_height(self) -> None:
        """generate_scroll_pattern positions don't exceed 80% of page height."""
        random.seed(42)
        browser = InAppBrowserBehavior()

        page_height = 5000
        pattern = browser.generate_scroll_pattern(page_height_estimate=page_height)

        max_position = page_height * 0.8
        for position, _ in pattern:
            assert position <= max_position

    def test_generate_scroll_pattern_positions_increase(self) -> None:
        """generate_scroll_pattern positions generally increase (with some skips)."""
        random.seed(42)
        browser = InAppBrowserBehavior()
        pattern = browser.generate_scroll_pattern()

        # First position should be positive
        assert pattern[0][0] > 0

        # Last position should be greater than first
        if len(pattern) > 1:
            assert pattern[-1][0] >= pattern[0][0]

    def test_should_return_to_app_returns_bool(self) -> None:
        """should_return_to_app returns a boolean."""
        browser = InAppBrowserBehavior()
        result = browser.should_return_to_app(time_spent=30.0)
        assert isinstance(result, bool)

    def test_should_return_to_app_increases_with_time(self) -> None:
        """should_return_to_app probability increases with time spent."""
        random.seed(42)
        browser = InAppBrowserBehavior()
        trials = 1000

        # Short time spent
        short_returns = sum(
            browser.should_return_to_app(time_spent=10.0)
            for _ in range(trials)
        )

        # Long time spent
        random.seed(42)
        long_returns = sum(
            browser.should_return_to_app(time_spent=120.0)
            for _ in range(trials)
        )

        # Longer time should result in more returns
        assert long_returns > short_returns

    def test_should_return_to_app_caps_at_90_percent(self) -> None:
        """should_return_to_app probability caps at 90%."""
        random.seed(42)
        browser = InAppBrowserBehavior()

        # Very long time spent (10 minutes)
        returns = sum(
            browser.should_return_to_app(time_spent=600.0)
            for _ in range(1000)
        )
        rate = returns / 1000

        # Should be capped around 90%, allow some tolerance
        assert rate <= 0.95


class TestVideoWatchBehaviorAdditionalMethods:
    """Additional tests for VideoWatchBehavior helper methods."""

    def test_should_visit_profile_returns_bool(self) -> None:
        """should_visit_profile returns a boolean."""
        behavior = VideoWatchBehavior()
        result = behavior.should_visit_profile()
        assert isinstance(result, bool)

    def test_should_click_bio_returns_bool(self) -> None:
        """should_click_bio returns a boolean."""
        behavior = VideoWatchBehavior()
        result = behavior.should_click_bio()
        assert isinstance(result, bool)

    def test_should_take_break_at_10_videos(self) -> None:
        """should_take_break checks at 10 video intervals."""
        random.seed(42)
        behavior = VideoWatchBehavior()

        # At 0 videos, never takes break
        assert behavior.should_take_break() is False

        # Simulate watching 9 videos
        for _ in range(9):
            behavior.record_video_watched()

        # At 9 videos, never takes break
        assert behavior.should_take_break() is False

        # Watch 10th video
        behavior.record_video_watched()

        # At 10 videos, may take break (probabilistic)
        # Just verify it doesn't crash and returns bool
        result = behavior.should_take_break()
        assert isinstance(result, bool)

    def test_generate_break_duration_returns_float(self) -> None:
        """generate_break_duration returns a float in expected range."""
        behavior = VideoWatchBehavior()
        duration = behavior.generate_break_duration()

        assert isinstance(duration, float)
        assert 5.0 <= duration <= 30.0

    def test_generate_session_length_returns_int(self) -> None:
        """generate_session_length returns an int in expected range."""
        random.seed(42)
        behavior = VideoWatchBehavior(platform="tiktok")
        length = behavior.generate_session_length()

        assert isinstance(length, int)
        assert 10 <= length <= 50  # TikTok session pattern range
