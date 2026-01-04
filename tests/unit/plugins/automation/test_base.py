"""Tests for social media automation base classes.

Tests dataclasses, enums, and base functionality from
ghoststorm.plugins.automation.base
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ghoststorm.plugins.automation.base import (
    BioClickResult,
    SessionResult,
    SocialPlatform,
    SwipeResult,
    VideoWatchOutcome,
    WatchResult,
)

# ============================================================================
# SocialPlatform ENUM TESTS
# ============================================================================


class TestSocialPlatform:
    """Tests for SocialPlatform enum."""

    def test_tiktok_value(self):
        """TIKTOK should have value 'tiktok'."""
        assert SocialPlatform.TIKTOK.value == "tiktok"

    def test_instagram_value(self):
        """INSTAGRAM should have value 'instagram'."""
        assert SocialPlatform.INSTAGRAM.value == "instagram"

    def test_youtube_value(self):
        """YOUTUBE should have value 'youtube'."""
        assert SocialPlatform.YOUTUBE.value == "youtube"

    def test_platform_is_str_enum(self):
        """SocialPlatform should be usable as a string."""
        assert isinstance(SocialPlatform.TIKTOK, str)
        assert SocialPlatform.TIKTOK == "tiktok"

    def test_all_platforms_present(self):
        """All expected platforms should be defined."""
        platforms = list(SocialPlatform)
        assert len(platforms) == 3
        assert SocialPlatform.TIKTOK in platforms
        assert SocialPlatform.INSTAGRAM in platforms
        assert SocialPlatform.YOUTUBE in platforms

    def test_platform_from_string(self):
        """SocialPlatform should be constructible from string value."""
        assert SocialPlatform("tiktok") == SocialPlatform.TIKTOK
        assert SocialPlatform("instagram") == SocialPlatform.INSTAGRAM
        assert SocialPlatform("youtube") == SocialPlatform.YOUTUBE

    def test_invalid_platform_raises(self):
        """Invalid platform string should raise ValueError."""
        with pytest.raises(ValueError):
            SocialPlatform("twitter")


# ============================================================================
# VideoWatchOutcome ENUM TESTS
# ============================================================================


class TestVideoWatchOutcome:
    """Tests for VideoWatchOutcome enum."""

    def test_skipped_value(self):
        """SKIPPED should have value 'skipped'."""
        assert VideoWatchOutcome.SKIPPED.value == "skipped"

    def test_partial_value(self):
        """PARTIAL should have value 'partial'."""
        assert VideoWatchOutcome.PARTIAL.value == "partial"

    def test_full_value(self):
        """FULL should have value 'full'."""
        assert VideoWatchOutcome.FULL.value == "full"

    def test_rewatched_value(self):
        """REWATCHED should have value 'rewatched'."""
        assert VideoWatchOutcome.REWATCHED.value == "rewatched"

    def test_outcome_is_str_enum(self):
        """VideoWatchOutcome should be usable as a string."""
        assert isinstance(VideoWatchOutcome.SKIPPED, str)
        assert VideoWatchOutcome.SKIPPED == "skipped"

    def test_all_outcomes_present(self):
        """All expected outcomes should be defined."""
        outcomes = list(VideoWatchOutcome)
        assert len(outcomes) == 4
        assert VideoWatchOutcome.SKIPPED in outcomes
        assert VideoWatchOutcome.PARTIAL in outcomes
        assert VideoWatchOutcome.FULL in outcomes
        assert VideoWatchOutcome.REWATCHED in outcomes

    def test_outcome_from_string(self):
        """VideoWatchOutcome should be constructible from string value."""
        assert VideoWatchOutcome("skipped") == VideoWatchOutcome.SKIPPED
        assert VideoWatchOutcome("partial") == VideoWatchOutcome.PARTIAL
        assert VideoWatchOutcome("full") == VideoWatchOutcome.FULL
        assert VideoWatchOutcome("rewatched") == VideoWatchOutcome.REWATCHED


# ============================================================================
# WatchResult DATACLASS TESTS
# ============================================================================


class TestWatchResult:
    """Tests for WatchResult dataclass."""

    def test_success_case_full_watch(self):
        """WatchResult should correctly represent a successful full watch."""
        result = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.FULL,
            watch_duration=30.0,
            video_duration=30.0,
            completion_rate=1.0,
        )

        assert result.success is True
        assert result.outcome == VideoWatchOutcome.FULL
        assert result.watch_duration == 30.0
        assert result.video_duration == 30.0
        assert result.completion_rate == 1.0
        assert result.replays == 0
        assert result.error is None

    def test_success_case_with_replays(self):
        """WatchResult should track replays correctly."""
        result = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.REWATCHED,
            watch_duration=45.0,
            video_duration=15.0,
            completion_rate=3.0,
            replays=2,
        )

        assert result.success is True
        assert result.outcome == VideoWatchOutcome.REWATCHED
        assert result.replays == 2
        assert result.completion_rate == 3.0

    def test_success_case_partial_watch(self):
        """WatchResult should correctly represent a partial watch."""
        result = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.PARTIAL,
            watch_duration=15.0,
            video_duration=30.0,
            completion_rate=0.5,
        )

        assert result.success is True
        assert result.outcome == VideoWatchOutcome.PARTIAL
        assert result.completion_rate == 0.5

    def test_success_case_skipped(self):
        """WatchResult should correctly represent a skipped video."""
        result = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.SKIPPED,
            watch_duration=1.5,
            video_duration=30.0,
            completion_rate=0.05,
        )

        assert result.success is True
        assert result.outcome == VideoWatchOutcome.SKIPPED
        assert result.watch_duration < 2.0

    def test_failure_case_with_error(self):
        """WatchResult should correctly represent a failure with error."""
        result = WatchResult(
            success=False,
            outcome=VideoWatchOutcome.SKIPPED,
            watch_duration=0.0,
            video_duration=None,
            completion_rate=0.0,
            error="Video element not found",
        )

        assert result.success is False
        assert result.error == "Video element not found"
        assert result.video_duration is None

    def test_failure_case_timeout(self):
        """WatchResult should handle timeout failures."""
        result = WatchResult(
            success=False,
            outcome=VideoWatchOutcome.PARTIAL,
            watch_duration=5.0,
            video_duration=60.0,
            completion_rate=0.083,
            error="Timeout waiting for video",
        )

        assert result.success is False
        assert result.error is not None
        assert "Timeout" in result.error

    def test_unknown_video_duration(self):
        """WatchResult should handle unknown video duration."""
        result = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.FULL,
            watch_duration=15.0,
            video_duration=None,
            completion_rate=1.0,
        )

        assert result.video_duration is None
        assert result.success is True

    def test_default_values(self):
        """WatchResult should have correct default values."""
        result = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.FULL,
            watch_duration=10.0,
            video_duration=10.0,
            completion_rate=1.0,
        )

        assert result.replays == 0
        assert result.error is None


# ============================================================================
# SwipeResult DATACLASS TESTS
# ============================================================================


class TestSwipeResult:
    """Tests for SwipeResult dataclass."""

    def test_success_swipe_up(self):
        """SwipeResult should represent successful upward swipe."""
        result = SwipeResult(
            success=True,
            direction="up",
            duration_ms=200,
            distance_px=500,
        )

        assert result.success is True
        assert result.direction == "up"
        assert result.duration_ms == 200
        assert result.distance_px == 500
        assert result.error is None

    def test_success_swipe_down(self):
        """SwipeResult should represent successful downward swipe."""
        result = SwipeResult(
            success=True,
            direction="down",
            duration_ms=250,
            distance_px=450,
        )

        assert result.success is True
        assert result.direction == "down"

    def test_success_swipe_left(self):
        """SwipeResult should represent successful left swipe."""
        result = SwipeResult(
            success=True,
            direction="left",
            duration_ms=180,
            distance_px=300,
        )

        assert result.success is True
        assert result.direction == "left"

    def test_success_swipe_right(self):
        """SwipeResult should represent successful right swipe."""
        result = SwipeResult(
            success=True,
            direction="right",
            duration_ms=220,
            distance_px=350,
        )

        assert result.success is True
        assert result.direction == "right"

    def test_failure_with_error(self):
        """SwipeResult should handle failure with error."""
        result = SwipeResult(
            success=False,
            direction="up",
            duration_ms=0,
            distance_px=0,
            error="Touch event failed",
        )

        assert result.success is False
        assert result.error == "Touch event failed"
        assert result.distance_px == 0

    def test_default_error_is_none(self):
        """SwipeResult error should default to None."""
        result = SwipeResult(
            success=True,
            direction="up",
            duration_ms=200,
            distance_px=500,
        )

        assert result.error is None

    def test_flick_swipe_short_duration(self):
        """SwipeResult should support flick gestures (short duration)."""
        result = SwipeResult(
            success=True,
            direction="up",
            duration_ms=150,  # Flick: 150-280ms
            distance_px=600,
        )

        assert result.duration_ms < 300
        assert result.success is True

    def test_slow_swipe_long_duration(self):
        """SwipeResult should support slow gestures (long duration)."""
        result = SwipeResult(
            success=True,
            direction="up",
            duration_ms=700,  # Slow: 500-800ms
            distance_px=400,
        )

        assert result.duration_ms > 500
        assert result.success is True


# ============================================================================
# BioClickResult DATACLASS TESTS
# ============================================================================


class TestBioClickResult:
    """Tests for BioClickResult dataclass."""

    def test_success_with_url(self):
        """BioClickResult should represent successful bio link click."""
        result = BioClickResult(
            success=True,
            target_url="https://example.com/profile",
            dwell_time=5.5,
        )

        assert result.success is True
        assert result.target_url == "https://example.com/profile"
        assert result.dwell_time == 5.5
        assert result.error is None

    def test_success_linktree(self):
        """BioClickResult should handle linktree URLs."""
        result = BioClickResult(
            success=True,
            target_url="https://linktr.ee/username",
            dwell_time=8.0,
        )

        assert result.success is True
        assert "linktr.ee" in result.target_url

    def test_failure_no_link(self):
        """BioClickResult should handle profiles without bio links."""
        result = BioClickResult(
            success=False,
            error="No bio link found",
        )

        assert result.success is False
        assert result.target_url is None
        assert result.dwell_time == 0.0
        assert result.error == "No bio link found"

    def test_failure_click_failed(self):
        """BioClickResult should handle click failures."""
        result = BioClickResult(
            success=False,
            target_url="https://example.com",
            error="Element not clickable",
        )

        assert result.success is False
        assert result.error == "Element not clickable"

    def test_default_values(self):
        """BioClickResult should have correct defaults."""
        result = BioClickResult(success=True)

        assert result.target_url is None
        assert result.dwell_time == 0.0
        assert result.error is None

    def test_zero_dwell_time_immediate_back(self):
        """BioClickResult should support zero dwell time (immediate back)."""
        result = BioClickResult(
            success=True,
            target_url="https://example.com",
            dwell_time=0.0,
        )

        assert result.dwell_time == 0.0
        assert result.success is True

    def test_long_dwell_time(self):
        """BioClickResult should support extended dwell time."""
        result = BioClickResult(
            success=True,
            target_url="https://shop.example.com",
            dwell_time=45.0,
        )

        assert result.dwell_time == 45.0


# ============================================================================
# SessionResult DATACLASS TESTS
# ============================================================================


class TestSessionResult:
    """Tests for SessionResult dataclass."""

    def test_success_tiktok_session(self):
        """SessionResult should represent successful TikTok session."""
        start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 12, 5, 0, tzinfo=UTC)

        result = SessionResult(
            success=True,
            platform=SocialPlatform.TIKTOK,
            start_time=start,
            end_time=end,
            videos_watched=10,
            bio_links_clicked=1,
        )

        assert result.success is True
        assert result.platform == SocialPlatform.TIKTOK
        assert result.videos_watched == 10
        assert result.bio_links_clicked == 1
        assert result.errors == []

    def test_success_instagram_session(self):
        """SessionResult should represent successful Instagram session."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        result = SessionResult(
            success=True,
            platform=SocialPlatform.INSTAGRAM,
            start_time=start,
            end_time=end,
            videos_watched=8,
            story_links_clicked=2,
            profiles_visited=3,
        )

        assert result.platform == SocialPlatform.INSTAGRAM
        assert result.story_links_clicked == 2
        assert result.profiles_visited == 3

    def test_success_youtube_session(self):
        """SessionResult should represent successful YouTube session."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        result = SessionResult(
            success=True,
            platform=SocialPlatform.YOUTUBE,
            start_time=start,
            end_time=end,
            videos_watched=5,
        )

        assert result.platform == SocialPlatform.YOUTUBE
        assert result.videos_watched == 5

    def test_failure_with_errors(self):
        """SessionResult should track multiple errors."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        result = SessionResult(
            success=False,
            platform=SocialPlatform.TIKTOK,
            start_time=start,
            end_time=end,
            videos_watched=2,
            errors=["Network timeout", "Element not found", "Rate limited"],
        )

        assert result.success is False
        assert len(result.errors) == 3
        assert "Rate limited" in result.errors

    def test_default_values(self):
        """SessionResult should have correct default values."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        result = SessionResult(
            success=True,
            platform=SocialPlatform.TIKTOK,
            start_time=start,
            end_time=end,
        )

        assert result.videos_watched == 0
        assert result.bio_links_clicked == 0
        assert result.story_links_clicked == 0
        assert result.profiles_visited == 0
        assert result.errors == []
        assert result.watch_results == []

    def test_with_watch_results(self):
        """SessionResult should store WatchResult list."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        watch1 = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.FULL,
            watch_duration=15.0,
            video_duration=15.0,
            completion_rate=1.0,
        )
        watch2 = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.SKIPPED,
            watch_duration=1.5,
            video_duration=30.0,
            completion_rate=0.05,
        )

        result = SessionResult(
            success=True,
            platform=SocialPlatform.TIKTOK,
            start_time=start,
            end_time=end,
            videos_watched=2,
            watch_results=[watch1, watch2],
        )

        assert len(result.watch_results) == 2
        assert result.watch_results[0].outcome == VideoWatchOutcome.FULL
        assert result.watch_results[1].outcome == VideoWatchOutcome.SKIPPED

    def test_session_duration_calculation(self):
        """Session duration should be calculable from timestamps."""
        start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 12, 10, 30, tzinfo=UTC)

        result = SessionResult(
            success=True,
            platform=SocialPlatform.TIKTOK,
            start_time=start,
            end_time=end,
        )

        duration = (result.end_time - result.start_time).total_seconds()
        assert duration == 630.0  # 10 minutes 30 seconds

    def test_partial_success_with_errors(self):
        """SessionResult can succeed even with some errors."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        result = SessionResult(
            success=True,
            platform=SocialPlatform.INSTAGRAM,
            start_time=start,
            end_time=end,
            videos_watched=7,
            errors=["Minor timeout on video 3"],
        )

        # Session can be marked success even with non-fatal errors
        assert result.success is True
        assert len(result.errors) == 1

    def test_empty_session(self):
        """SessionResult should handle zero-activity sessions."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        result = SessionResult(
            success=False,
            platform=SocialPlatform.TIKTOK,
            start_time=start,
            end_time=end,
            errors=["Failed to load initial page"],
        )

        assert result.success is False
        assert result.videos_watched == 0
        assert result.bio_links_clicked == 0


# ============================================================================
# DATACLASS IMMUTABILITY AND EQUALITY TESTS
# ============================================================================


class TestDataclassProperties:
    """Tests for dataclass behavior and properties."""

    def test_watch_result_equality(self):
        """WatchResult instances with same values should be equal."""
        result1 = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.FULL,
            watch_duration=10.0,
            video_duration=10.0,
            completion_rate=1.0,
        )
        result2 = WatchResult(
            success=True,
            outcome=VideoWatchOutcome.FULL,
            watch_duration=10.0,
            video_duration=10.0,
            completion_rate=1.0,
        )

        assert result1 == result2

    def test_swipe_result_inequality(self):
        """SwipeResult instances with different values should not be equal."""
        result1 = SwipeResult(success=True, direction="up", duration_ms=200, distance_px=500)
        result2 = SwipeResult(success=True, direction="down", duration_ms=200, distance_px=500)

        assert result1 != result2

    def test_bio_click_result_repr(self):
        """BioClickResult should have useful repr."""
        result = BioClickResult(success=True, target_url="https://example.com")
        repr_str = repr(result)

        assert "BioClickResult" in repr_str
        assert "success=True" in repr_str
        assert "example.com" in repr_str

    def test_session_result_mutable_lists(self):
        """SessionResult lists should be mutable after creation."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        result = SessionResult(
            success=True,
            platform=SocialPlatform.TIKTOK,
            start_time=start,
            end_time=end,
        )

        # Should be able to append to lists
        result.errors.append("New error")
        result.watch_results.append(
            WatchResult(
                success=True,
                outcome=VideoWatchOutcome.FULL,
                watch_duration=10.0,
                video_duration=10.0,
                completion_rate=1.0,
            )
        )

        assert len(result.errors) == 1
        assert len(result.watch_results) == 1

    def test_session_result_default_factory_isolation(self):
        """Each SessionResult should have independent default lists."""
        start = datetime.now(UTC)
        end = datetime.now(UTC)

        result1 = SessionResult(
            success=True,
            platform=SocialPlatform.TIKTOK,
            start_time=start,
            end_time=end,
        )
        result2 = SessionResult(
            success=True,
            platform=SocialPlatform.INSTAGRAM,
            start_time=start,
            end_time=end,
        )

        result1.errors.append("Error in result1")

        # result2 should not be affected
        assert len(result2.errors) == 0
        assert len(result1.errors) == 1
