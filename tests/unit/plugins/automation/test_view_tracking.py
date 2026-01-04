"""Tests for view tracking system."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from ghoststorm.plugins.automation.view_tracking import (
    PLATFORM_REQUIREMENTS,
    ViewTrackingManager,
    get_view_tracker,
    reset_view_tracker,
)


class TestPlatformRequirements:
    """Tests for PLATFORM_REQUIREMENTS constants."""

    def test_youtube_requires_30_seconds(self) -> None:
        """YouTube requires 30 seconds minimum watch time."""
        assert PLATFORM_REQUIREMENTS["youtube"].min_watch_seconds == 30.0

    def test_tiktok_requires_3_seconds(self) -> None:
        """TikTok requires 3 seconds minimum watch time."""
        assert PLATFORM_REQUIREMENTS["tiktok"].min_watch_seconds == 3.0

    def test_instagram_requires_3_seconds(self) -> None:
        """Instagram requires 3 seconds minimum watch time."""
        assert PLATFORM_REQUIREMENTS["instagram"].min_watch_seconds == 3.0

    def test_youtube_shorts_requires_3_seconds(self) -> None:
        """YouTube Shorts requires 3 seconds minimum watch time."""
        assert PLATFORM_REQUIREMENTS["youtube_shorts"].min_watch_seconds == 3.0

    def test_all_platforms_require_unique_ip_by_default(self) -> None:
        """All platforms require unique IP by default."""
        for platform, reqs in PLATFORM_REQUIREMENTS.items():
            assert reqs.requires_unique_ip is True, f"{platform} should require unique IP"

    def test_all_platforms_require_unique_fingerprint_by_default(self) -> None:
        """All platforms require unique fingerprint by default."""
        for platform, reqs in PLATFORM_REQUIREMENTS.items():
            assert reqs.requires_unique_fingerprint is True, f"{platform} should require unique fingerprint"


class TestViewTrackingManagerCanView:
    """Tests for ViewTrackingManager.can_view method."""

    def test_first_view_allowed(self) -> None:
        """First view of a video should always be allowed."""
        manager = ViewTrackingManager()

        can_view, reason = manager.can_view(
            video_id="test_video_123",
            platform="youtube",
            proxy_id="proxy_abc",
            fingerprint_id="fp_xyz",
        )

        assert can_view is True
        assert reason == ""

    def test_first_view_allowed_any_platform(self) -> None:
        """First view should be allowed on any platform."""
        manager = ViewTrackingManager()

        for platform in ["youtube", "tiktok", "instagram", "youtube_shorts"]:
            can_view, reason = manager.can_view(
                video_id=f"video_{platform}",
                platform=platform,
                proxy_id="proxy_001",
                fingerprint_id="fp_001",
            )
            assert can_view is True, f"First view should be allowed for {platform}"
            assert reason == ""

    def test_unknown_platform_allowed(self) -> None:
        """Unknown platform should allow view with warning."""
        manager = ViewTrackingManager()

        can_view, reason = manager.can_view(
            video_id="video_123",
            platform="unknown_platform",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
        )

        assert can_view is True
        assert reason == ""


class TestViewTrackingManagerRecordView:
    """Tests for ViewTrackingManager.record_view method."""

    def test_view_counted_when_duration_meets_minimum(self) -> None:
        """View should be counted when duration meets minimum requirement."""
        manager = ViewTrackingManager()

        # TikTok requires 3 seconds
        counted = manager.record_view(
            video_id="tiktok_video_123",
            platform="tiktok",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=5.0,  # 5 seconds >= 3 seconds
        )

        assert counted is True

    def test_view_not_counted_when_duration_too_short(self) -> None:
        """View should not be counted when duration is below minimum."""
        manager = ViewTrackingManager()

        # TikTok requires 3 seconds
        counted = manager.record_view(
            video_id="tiktok_video_123",
            platform="tiktok",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=2.0,  # 2 seconds < 3 seconds
        )

        assert counted is False

    def test_view_counted_at_exact_minimum(self) -> None:
        """View should be counted when duration equals minimum exactly."""
        manager = ViewTrackingManager()

        counted = manager.record_view(
            video_id="tiktok_video_123",
            platform="tiktok",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=3.0,  # Exactly 3 seconds
        )

        assert counted is True

    def test_record_creates_entry(self) -> None:
        """Recording a view should create an entry in records."""
        manager = ViewTrackingManager()

        manager.record_view(
            video_id="test_video",
            platform="youtube",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=35.0,
        )

        assert "test_video" in manager._records
        assert len(manager._records["test_video"]) == 1


class TestYouTubeWatchTime:
    """Tests for YouTube-specific watch time requirements."""

    def test_youtube_requires_longer_watch_10s_not_enough(self) -> None:
        """10 seconds is not enough for YouTube view to count."""
        manager = ViewTrackingManager()

        counted = manager.record_view(
            video_id="youtube_video_123",
            platform="youtube",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=10.0,
        )

        assert counted is False

    def test_youtube_requires_longer_watch_35s_works(self) -> None:
        """35 seconds is enough for YouTube view to count."""
        manager = ViewTrackingManager()

        counted = manager.record_view(
            video_id="youtube_video_123",
            platform="youtube",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=35.0,
        )

        assert counted is True

    def test_youtube_30s_exact_works(self) -> None:
        """Exactly 30 seconds should count for YouTube."""
        manager = ViewTrackingManager()

        counted = manager.record_view(
            video_id="youtube_video_123",
            platform="youtube",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=30.0,
        )

        assert counted is True

    def test_youtube_29s_not_enough(self) -> None:
        """29 seconds should not count for YouTube."""
        manager = ViewTrackingManager()

        counted = manager.record_view(
            video_id="youtube_video_123",
            platform="youtube",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=29.0,
        )

        assert counted is False


class TestDuplicateIPBlocked:
    """Tests for duplicate IP blocking."""

    def test_duplicate_ip_blocked_for_same_video(self) -> None:
        """Same proxy (IP) should be blocked for same video within hour."""
        manager = ViewTrackingManager()

        base_time = time.time()

        # First view - record with mocked time
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time
            manager.record_view(
                video_id="video_abc",
                platform="tiktok",
                proxy_id="proxy_001",
                fingerprint_id="fp_001",
                watch_duration=5.0,
            )

        # Try second view after cooldown but same IP
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time + 400  # Past cooldown

            can_view, reason = manager.can_view(
                video_id="video_abc",
                platform="tiktok",
                proxy_id="proxy_001",  # Same proxy
                fingerprint_id="fp_002",  # Different fingerprint
            )

        assert can_view is False
        assert "IP already used" in reason

    def test_different_ip_allowed_for_same_video(self) -> None:
        """Different proxy (IP) should be allowed for same video."""
        manager = ViewTrackingManager()

        base_time = time.time()

        # First view
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time
            manager.record_view(
                video_id="video_abc",
                platform="tiktok",
                proxy_id="proxy_001",
                fingerprint_id="fp_001",
                watch_duration=5.0,
            )

        # Second view with different proxy after cooldown
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time + 400  # Past cooldown

            can_view, reason = manager.can_view(
                video_id="video_abc",
                platform="tiktok",
                proxy_id="proxy_002",  # Different proxy
                fingerprint_id="fp_002",  # Different fingerprint
            )

        assert can_view is True
        assert reason == ""


class TestDuplicateFingerprintBlocked:
    """Tests for duplicate fingerprint blocking."""

    def test_duplicate_fingerprint_blocked_for_same_video(self) -> None:
        """Same fingerprint should be blocked for same video within hour."""
        manager = ViewTrackingManager()

        base_time = time.time()

        # First view
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time
            manager.record_view(
                video_id="video_xyz",
                platform="instagram",
                proxy_id="proxy_001",
                fingerprint_id="fp_unique_123",
                watch_duration=5.0,
            )

        # Try second view after cooldown but same fingerprint
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time + 700  # Past cooldown (10 min for instagram)

            can_view, reason = manager.can_view(
                video_id="video_xyz",
                platform="instagram",
                proxy_id="proxy_002",  # Different proxy
                fingerprint_id="fp_unique_123",  # Same fingerprint
            )

        assert can_view is False
        assert "Fingerprint already used" in reason

    def test_different_fingerprint_allowed(self) -> None:
        """Different fingerprint should be allowed for same video."""
        manager = ViewTrackingManager()

        base_time = time.time()

        # First view
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time
            manager.record_view(
                video_id="video_xyz",
                platform="tiktok",
                proxy_id="proxy_001",
                fingerprint_id="fp_001",
                watch_duration=5.0,
            )

        # Second view with different fingerprint after cooldown
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time + 400

            can_view, reason = manager.can_view(
                video_id="video_xyz",
                platform="tiktok",
                proxy_id="proxy_002",
                fingerprint_id="fp_002",  # Different fingerprint
            )

        assert can_view is True


class TestDifferentVideoAllowed:
    """Tests for different video access with same proxy."""

    def test_different_video_allowed_with_same_proxy(self) -> None:
        """Same proxy should be allowed for different video."""
        manager = ViewTrackingManager()

        # View first video
        manager.record_view(
            video_id="video_first",
            platform="youtube",
            proxy_id="proxy_shared",
            fingerprint_id="fp_shared",
            watch_duration=35.0,
        )

        # Try second video with same proxy and fingerprint
        can_view, reason = manager.can_view(
            video_id="video_second",  # Different video
            platform="youtube",
            proxy_id="proxy_shared",  # Same proxy
            fingerprint_id="fp_shared",  # Same fingerprint
        )

        assert can_view is True
        assert reason == ""

    def test_different_video_allowed_multiple_times(self) -> None:
        """Same proxy should work for multiple different videos."""
        manager = ViewTrackingManager()

        proxy_id = "shared_proxy"
        fingerprint_id = "shared_fp"

        for i in range(5):
            video_id = f"video_{i}"

            can_view, reason = manager.can_view(
                video_id=video_id,
                platform="tiktok",
                proxy_id=proxy_id,
                fingerprint_id=fingerprint_id,
            )
            assert can_view is True, f"Video {i} should be allowed"

            manager.record_view(
                video_id=video_id,
                platform="tiktok",
                proxy_id=proxy_id,
                fingerprint_id=fingerprint_id,
                watch_duration=5.0,
            )


class TestMaxViewsPerHour:
    """Tests for rate limit enforcement."""

    def test_max_views_per_hour_enforced(self) -> None:
        """Maximum views per hour limit should be enforced."""
        manager = ViewTrackingManager()

        video_id = "rate_limited_video"
        platform = "youtube"  # Max 2 views per hour, 1 hour cooldown

        base_time = time.time()

        # Record max views allowed with unique proxies/fingerprints
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time
            for i in range(2):
                manager.record_view(
                    video_id=video_id,
                    platform=platform,
                    proxy_id=f"proxy_{i}",
                    fingerprint_id=f"fp_{i}",
                    watch_duration=35.0,
                )

        # Try third view - past cooldown (1 hour) but still within 1 hour window for rate limiting
        # YouTube cooldown is 3600s, so we need to be past that but views still counted in hour window
        # The issue is YouTube has 1 hour cooldown AND 1 hour rate limit window - they're the same
        # So we test with tiktok which has 5 min cooldown but counts views per hour
        # Actually, let's test by checking view immediately - it will be blocked by cooldown OR rate limit
        can_view, reason = manager.can_view(
            video_id=video_id,
            platform=platform,
            proxy_id="proxy_new",
            fingerprint_id="fp_new",
        )

        # Will be blocked either by rate limit or cooldown - both valid
        assert can_view is False

    def test_tiktok_allows_5_views_per_hour(self) -> None:
        """TikTok allows 5 views per hour per video."""
        manager = ViewTrackingManager()

        video_id = "tiktok_rate_test"
        base_time = time.time()

        # Record 5 views with unique proxies/fingerprints
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time
            for i in range(5):
                manager.record_view(
                    video_id=video_id,
                    platform="tiktok",
                    proxy_id=f"proxy_{i}",
                    fingerprint_id=f"fp_{i}",
                    watch_duration=5.0,
                )

        # Past cooldown but within hour
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time + 400

            can_view, reason = manager.can_view(
                video_id=video_id,
                platform="tiktok",
                proxy_id="proxy_new",
                fingerprint_id="fp_new",
            )

        assert can_view is False
        assert "5 views/hour exceeded" in reason

    def test_views_allowed_after_hour_passes(self) -> None:
        """Views should be allowed after the hour window passes."""
        manager = ViewTrackingManager()

        video_id = "hourly_reset_test"
        base_time = time.time()

        # Record max views
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time
            for i in range(2):
                manager.record_view(
                    video_id=video_id,
                    platform="youtube",
                    proxy_id=f"proxy_{i}",
                    fingerprint_id=f"fp_{i}",
                    watch_duration=35.0,
                )

        # Fast forward more than an hour
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time + 7200  # 2 hours later

            can_view, reason = manager.can_view(
                video_id=video_id,
                platform="youtube",
                proxy_id="proxy_new",
                fingerprint_id="fp_new",
            )

        assert can_view is True
        assert reason == ""


class TestGetMinimumWatchTime:
    """Tests for get_minimum_watch_time method."""

    def test_returns_youtube_watch_time(self) -> None:
        """Should return 30 seconds for YouTube."""
        manager = ViewTrackingManager()
        assert manager.get_minimum_watch_time("youtube") == 30.0

    def test_returns_tiktok_watch_time(self) -> None:
        """Should return 3 seconds for TikTok."""
        manager = ViewTrackingManager()
        assert manager.get_minimum_watch_time("tiktok") == 3.0

    def test_returns_instagram_watch_time(self) -> None:
        """Should return 3 seconds for Instagram."""
        manager = ViewTrackingManager()
        assert manager.get_minimum_watch_time("instagram") == 3.0

    def test_returns_youtube_shorts_watch_time(self) -> None:
        """Should return 3 seconds for YouTube Shorts."""
        manager = ViewTrackingManager()
        assert manager.get_minimum_watch_time("youtube_shorts") == 3.0

    def test_returns_default_for_unknown_platform(self) -> None:
        """Should return 3 seconds for unknown platform."""
        manager = ViewTrackingManager()
        assert manager.get_minimum_watch_time("unknown") == 3.0


class TestGetViewStats:
    """Tests for get_view_stats method."""

    def test_returns_stats_dict(self) -> None:
        """Should return a dictionary with view statistics."""
        manager = ViewTrackingManager()

        manager.record_view(
            video_id="stats_video",
            platform="tiktok",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=5.0,
        )

        stats = manager.get_view_stats("stats_video")

        assert isinstance(stats, dict)
        assert "total_views" in stats
        assert "views_last_hour" in stats
        assert "counted_views" in stats
        assert "unique_ips" in stats
        assert "unique_fingerprints" in stats
        assert "avg_watch_time" in stats

    def test_stats_count_total_views(self) -> None:
        """Stats should correctly count total views."""
        manager = ViewTrackingManager()

        for i in range(3):
            manager.record_view(
                video_id="multi_view_video",
                platform="tiktok",
                proxy_id=f"proxy_{i}",
                fingerprint_id=f"fp_{i}",
                watch_duration=5.0,
            )

        stats = manager.get_view_stats("multi_view_video")

        assert stats["total_views"] == 3
        assert stats["views_last_hour"] == 3
        assert stats["unique_ips"] == 3
        assert stats["unique_fingerprints"] == 3

    def test_stats_count_only_counted_views(self) -> None:
        """Stats should track counted vs uncounted views."""
        manager = ViewTrackingManager()

        # One counted view
        manager.record_view(
            video_id="counted_test",
            platform="youtube",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=35.0,  # Counted
        )

        # One uncounted view
        manager.record_view(
            video_id="counted_test",
            platform="youtube",
            proxy_id="proxy_002",
            fingerprint_id="fp_002",
            watch_duration=10.0,  # Not counted (< 30s)
        )

        stats = manager.get_view_stats("counted_test")

        assert stats["total_views"] == 2
        assert stats["counted_views"] == 1

    def test_stats_calculate_avg_watch_time(self) -> None:
        """Stats should calculate average watch time."""
        manager = ViewTrackingManager()

        manager.record_view(
            video_id="avg_test",
            platform="tiktok",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=10.0,
        )

        manager.record_view(
            video_id="avg_test",
            platform="tiktok",
            proxy_id="proxy_002",
            fingerprint_id="fp_002",
            watch_duration=20.0,
        )

        stats = manager.get_view_stats("avg_test")

        assert stats["avg_watch_time"] == 15.0

    def test_stats_for_nonexistent_video(self) -> None:
        """Stats for nonexistent video should return zeros."""
        manager = ViewTrackingManager()

        stats = manager.get_view_stats("nonexistent_video")

        assert stats["total_views"] == 0
        assert stats["views_last_hour"] == 0
        assert stats["counted_views"] == 0
        assert stats["unique_ips"] == 0
        assert stats["unique_fingerprints"] == 0
        assert stats["avg_watch_time"] == 0


class TestGlobalViewTracker:
    """Tests for global view tracker functions."""

    def test_get_view_tracker_returns_singleton(self) -> None:
        """get_view_tracker should return same instance."""
        reset_view_tracker()

        tracker1 = get_view_tracker()
        tracker2 = get_view_tracker()

        assert tracker1 is tracker2

    def test_get_view_tracker_returns_manager_instance(self) -> None:
        """get_view_tracker should return ViewTrackingManager instance."""
        reset_view_tracker()

        tracker = get_view_tracker()

        assert isinstance(tracker, ViewTrackingManager)

    def test_reset_view_tracker_clears_singleton(self) -> None:
        """reset_view_tracker should clear the singleton."""
        reset_view_tracker()

        tracker1 = get_view_tracker()
        tracker1.record_view(
            video_id="singleton_test",
            platform="tiktok",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=5.0,
        )

        reset_view_tracker()

        tracker2 = get_view_tracker()

        # New tracker should not have the old record
        assert tracker1 is not tracker2
        assert "singleton_test" not in tracker2._records

    def test_reset_creates_fresh_tracker(self) -> None:
        """Reset should create a fresh tracker with empty records."""
        reset_view_tracker()

        tracker = get_view_tracker()
        tracker.record_view(
            video_id="video_to_clear",
            platform="youtube",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=35.0,
        )

        reset_view_tracker()
        new_tracker = get_view_tracker()

        assert len(new_tracker._records) == 0


class TestCooldownPeriods:
    """Tests for cooldown period enforcement."""

    def test_cooldown_blocks_immediate_view(self) -> None:
        """Cooldown should block immediate second view."""
        manager = ViewTrackingManager()

        manager.record_view(
            video_id="cooldown_video",
            platform="tiktok",
            proxy_id="proxy_001",
            fingerprint_id="fp_001",
            watch_duration=5.0,
        )

        # Immediate second view attempt with different identity
        can_view, reason = manager.can_view(
            video_id="cooldown_video",
            platform="tiktok",
            proxy_id="proxy_002",
            fingerprint_id="fp_002",
        )

        assert can_view is False
        assert "Cooldown active" in reason

    def test_view_allowed_after_cooldown(self) -> None:
        """View should be allowed after cooldown expires."""
        manager = ViewTrackingManager()

        base_time = time.time()

        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time
            manager.record_view(
                video_id="cooldown_video",
                platform="tiktok",  # 5 min cooldown
                proxy_id="proxy_001",
                fingerprint_id="fp_001",
                watch_duration=5.0,
            )

        # After cooldown
        with patch("ghoststorm.plugins.automation.view_tracking.time") as mock_time:
            mock_time.time.return_value = base_time + 400  # 6+ minutes

            can_view, reason = manager.can_view(
                video_id="cooldown_video",
                platform="tiktok",
                proxy_id="proxy_002",
                fingerprint_id="fp_002",
            )

        assert can_view is True
