"""Comprehensive tests for API schemas."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ghoststorm.api.schemas import (
    PRESETS,
    BehaviorConfigSchema,
    ConfigPreset,
    DEXToolsConfigSchema,
    EngineConfigSchema,
    GenericConfigSchema,
    InstagramConfigSchema,
    MetricsResponse,
    PlatformDetectRequest,
    PlatformDetectResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TikTokConfigSchema,
    WebSocketEvent,
    YouTubeConfigSchema,
    detect_platform,
)

# ============================================================================
# DETECT_PLATFORM FUNCTION TESTS
# ============================================================================


class TestDetectPlatformTikTok:
    """Tests for TikTok URL detection."""

    def test_tiktok_video_url(self):
        """Detect TikTok video URL with video ID extraction."""
        url = "https://tiktok.com/@username/video/1234567890"
        platform, metadata = detect_platform(url)

        assert platform == "tiktok"
        assert metadata["url"] == url
        assert metadata["video_id"] == "1234567890"

    def test_tiktok_video_url_with_dot_in_username(self):
        """Detect TikTok video URL with dots in username."""
        url = "https://tiktok.com/@user.name.123/video/9876543210"
        platform, metadata = detect_platform(url)

        assert platform == "tiktok"
        assert metadata["video_id"] == "9876543210"

    def test_tiktok_profile_url(self):
        """Detect TikTok profile URL with username extraction."""
        url = "https://tiktok.com/@cooluser123"
        platform, metadata = detect_platform(url)

        assert platform == "tiktok"
        assert metadata["username"] == "cooluser123"
        assert "video_id" not in metadata

    def test_tiktok_vm_short_url(self):
        """Detect vm.tiktok.com short URL."""
        url = "https://vm.tiktok.com/abc123XYZ"
        platform, metadata = detect_platform(url)

        assert platform == "tiktok"
        assert metadata["username"] == "abc123XYZ"

    def test_tiktok_t_short_url(self):
        """Detect tiktok.com/t/ short URL."""
        url = "https://tiktok.com/t/ZTR8abc123"
        platform, metadata = detect_platform(url)

        assert platform == "tiktok"
        assert metadata["username"] == "ZTR8abc123"

    def test_tiktok_case_insensitive(self):
        """TikTok detection should be case insensitive."""
        url = "https://TIKTOK.COM/@UserName/VIDEO/1234567890"
        platform, metadata = detect_platform(url)

        assert platform == "tiktok"
        assert metadata["video_id"] == "1234567890"


class TestDetectPlatformInstagram:
    """Tests for Instagram URL detection."""

    def test_instagram_reel_url(self):
        """Detect Instagram reel URL with post ID extraction."""
        url = "https://instagram.com/reel/ABC123xyz-_"
        platform, metadata = detect_platform(url)

        assert platform == "instagram"
        assert metadata["post_id"] == "ABC123xyz-_"

    def test_instagram_post_url(self):
        """Detect Instagram post URL with post ID extraction."""
        url = "https://instagram.com/p/XYZ789abc"
        platform, metadata = detect_platform(url)

        assert platform == "instagram"
        assert metadata["post_id"] == "XYZ789abc"

    def test_instagram_stories_url(self):
        """Detect Instagram stories URL with username and story ID."""
        url = "https://instagram.com/stories/testuser/123456789012345678"
        platform, metadata = detect_platform(url)

        assert platform == "instagram"
        assert metadata["username"] == "testuser"
        assert metadata["story_id"] == "123456789012345678"

    def test_instagram_profile_url(self):
        """Detect Instagram profile URL with username extraction."""
        url = "https://instagram.com/username123"
        platform, metadata = detect_platform(url)

        assert platform == "instagram"
        assert metadata["username"] == "username123"

    def test_instagram_profile_url_with_trailing_slash(self):
        """Detect Instagram profile URL with trailing slash."""
        url = "https://instagram.com/cool.user/"
        platform, metadata = detect_platform(url)

        assert platform == "instagram"
        assert metadata["username"] == "cool.user"

    def test_instagram_www_subdomain(self):
        """Detect Instagram URL with www subdomain."""
        url = "https://www.instagram.com/reel/ABC123"
        platform, metadata = detect_platform(url)

        assert platform == "instagram"
        assert metadata["post_id"] == "ABC123"


class TestDetectPlatformYouTube:
    """Tests for YouTube URL detection."""

    def test_youtube_watch_url(self):
        """Detect YouTube watch URL with video ID extraction."""
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        platform, metadata = detect_platform(url)

        assert platform == "youtube"
        assert metadata["video_id"] == "dQw4w9WgXcQ"

    def test_youtube_shorts_url(self):
        """Detect YouTube shorts URL with short ID extraction."""
        url = "https://youtube.com/shorts/abc123XYZ_-"
        platform, metadata = detect_platform(url)

        assert platform == "youtube"
        assert metadata["short_id"] == "abc123XYZ_-"

    def test_youtube_short_url(self):
        """Detect youtu.be short URL with video ID extraction."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        platform, metadata = detect_platform(url)

        assert platform == "youtube"
        assert metadata["video_id"] == "dQw4w9WgXcQ"

    def test_youtube_channel_at_url(self):
        """Detect YouTube channel URL with @ format."""
        url = "https://youtube.com/@channelname"
        platform, metadata = detect_platform(url)

        assert platform == "youtube"
        assert metadata["channel"] == "channelname"

    def test_youtube_channel_id_url(self):
        """Detect YouTube channel URL with channel ID."""
        url = "https://youtube.com/channel/UCabcdef123456"
        platform, metadata = detect_platform(url)

        assert platform == "youtube"
        assert metadata["channel"] == "UCabcdef123456"

    def test_youtube_www_subdomain(self):
        """Detect YouTube URL with www subdomain."""
        url = "https://www.youtube.com/watch?v=test123"
        platform, metadata = detect_platform(url)

        assert platform == "youtube"
        assert metadata["video_id"] == "test123"


class TestDetectPlatformDEXTools:
    """Tests for DEXTools URL detection."""

    def test_dextools_pair_explorer_url(self):
        """Detect DEXTools pair explorer URL with pair address extraction."""
        url = (
            "https://dextools.io/app/ether/pair-explorer/0x1234567890abcdef1234567890abcdef12345678"
        )
        platform, metadata = detect_platform(url)

        assert platform == "dextools"
        assert metadata["pair_address"] == "0x1234567890abcdef1234567890abcdef12345678"

    def test_dextools_different_chain(self):
        """Detect DEXTools URL for different chains."""
        url = "https://dextools.io/app/bsc/pair-explorer/0xabcdef1234567890abcdef1234567890abcdef12"
        platform, metadata = detect_platform(url)

        assert platform == "dextools"
        assert metadata["pair_address"] == "0xabcdef1234567890abcdef1234567890abcdef12"


class TestDetectPlatformGeneric:
    """Tests for generic/unknown URL detection."""

    def test_generic_unknown_url(self):
        """Unknown URLs return generic platform."""
        url = "https://example.com/some/path"
        platform, metadata = detect_platform(url)

        assert platform == "generic"
        assert metadata["url"] == url

    def test_generic_random_domain(self):
        """Random domains return generic platform."""
        url = "https://randomsite.net/page?query=value"
        platform, metadata = detect_platform(url)

        assert platform == "generic"
        assert metadata["url"] == url

    def test_detect_platform_strips_whitespace(self):
        """URLs should have whitespace stripped."""
        url = "  https://tiktok.com/@user/video/123  "
        platform, metadata = detect_platform(url)

        assert platform == "tiktok"
        assert metadata["url"] == url.strip()


# ============================================================================
# TASKCREATE SCHEMA TESTS
# ============================================================================


class TestTaskCreate:
    """Tests for TaskCreate schema."""

    def test_task_create_minimal(self):
        """Create task with minimal required fields."""
        task = TaskCreate(url="https://example.com")

        assert task.url == "https://example.com"
        assert task.platform is None
        assert task.mode == "batch"
        assert task.workers == 1
        assert task.repeat == 1
        assert task.config == {}

    def test_task_create_adds_https(self):
        """URL without protocol gets https:// prepended."""
        task = TaskCreate(url="example.com/path")

        assert task.url == "https://example.com/path"

    def test_task_create_preserves_http(self):
        """URL with http:// is preserved."""
        task = TaskCreate(url="http://example.com")

        assert task.url == "http://example.com"

    def test_task_create_preserves_https(self):
        """URL with https:// is preserved."""
        task = TaskCreate(url="https://example.com")

        assert task.url == "https://example.com"

    def test_task_create_strips_whitespace(self):
        """URL whitespace is stripped."""
        task = TaskCreate(url="  https://example.com  ")

        assert task.url == "https://example.com"

    def test_task_create_with_platform(self):
        """Create task with explicit platform."""
        task = TaskCreate(url="https://example.com", platform="tiktok")

        assert task.platform == "tiktok"

    def test_task_create_debug_mode(self):
        """Create task with debug mode."""
        task = TaskCreate(url="https://example.com", mode="debug")

        assert task.mode == "debug"

    def test_task_create_workers_range(self):
        """Workers must be between 1 and 50."""
        task = TaskCreate(url="https://example.com", workers=25)
        assert task.workers == 25

        with pytest.raises(ValidationError):
            TaskCreate(url="https://example.com", workers=0)

        with pytest.raises(ValidationError):
            TaskCreate(url="https://example.com", workers=51)

    def test_task_create_repeat_range(self):
        """Repeat must be between 1 and 1000."""
        task = TaskCreate(url="https://example.com", repeat=500)
        assert task.repeat == 500

        with pytest.raises(ValidationError):
            TaskCreate(url="https://example.com", repeat=0)

        with pytest.raises(ValidationError):
            TaskCreate(url="https://example.com", repeat=1001)

    def test_task_create_with_config(self):
        """Create task with custom config."""
        config = {"min_watch_percent": 0.5, "skip_probability": 0.2}
        task = TaskCreate(url="https://example.com", config=config)

        assert task.config == config


# ============================================================================
# TASKRESPONSE SCHEMA TESTS
# ============================================================================


class TestTaskResponse:
    """Tests for TaskResponse schema."""

    def test_task_response_serialization(self):
        """TaskResponse serializes correctly."""
        now = datetime.utcnow()
        response = TaskResponse(
            task_id="task-123",
            status="running",
            platform="tiktok",
            url="https://tiktok.com/@user",
            mode="batch",
            workers=5,
            progress=0.5,
            created_at=now,
        )

        assert response.task_id == "task-123"
        assert response.status == "running"
        assert response.platform == "tiktok"
        assert response.progress == 0.5
        assert response.results is None
        assert response.error is None

    def test_task_response_with_results(self):
        """TaskResponse with results and completion times."""
        now = datetime.utcnow()
        response = TaskResponse(
            task_id="task-456",
            status="completed",
            platform="youtube",
            url="https://youtube.com/watch?v=abc",
            mode="batch",
            workers=3,
            progress=1.0,
            results={"views": 100, "success_rate": 0.95},
            created_at=now,
            started_at=now,
            completed_at=now,
        )

        assert response.status == "completed"
        assert response.progress == 1.0
        assert response.results["views"] == 100

    def test_task_response_with_error(self):
        """TaskResponse with error status."""
        now = datetime.utcnow()
        response = TaskResponse(
            task_id="task-789",
            status="failed",
            platform="instagram",
            url="https://instagram.com/reel/abc",
            mode="debug",
            workers=1,
            progress=0.3,
            error="Connection timeout",
            created_at=now,
        )

        assert response.status == "failed"
        assert response.error == "Connection timeout"


class TestTaskListResponse:
    """Tests for TaskListResponse schema."""

    def test_task_list_response(self):
        """TaskListResponse aggregates task counts."""
        now = datetime.utcnow()
        tasks = [
            TaskResponse(
                task_id="1",
                status="running",
                platform="tiktok",
                url="https://tiktok.com/@a",
                mode="batch",
                workers=1,
                progress=0.5,
                created_at=now,
            ),
            TaskResponse(
                task_id="2",
                status="completed",
                platform="youtube",
                url="https://youtube.com/watch?v=b",
                mode="batch",
                workers=1,
                progress=1.0,
                created_at=now,
            ),
        ]

        response = TaskListResponse(
            tasks=tasks,
            total=10,
            running=2,
            completed=5,
            failed=3,
        )

        assert len(response.tasks) == 2
        assert response.total == 10
        assert response.running == 2


# ============================================================================
# PLATFORM CONFIG SCHEMA TESTS
# ============================================================================


class TestTikTokConfigSchema:
    """Tests for TikTokConfigSchema defaults and validation."""

    def test_tiktok_config_defaults(self):
        """TikTok config has correct default values."""
        config = TikTokConfigSchema()

        assert config.target_video_urls == []
        assert config.min_watch_percent == 0.3
        assert config.max_watch_percent == 1.5
        assert config.skip_probability == 0.30
        assert config.bio_click_probability == 0.15
        assert config.profile_visit_probability == 0.10
        assert config.videos_per_session_min == 10
        assert config.videos_per_session_max == 30
        assert config.swipe_speed_min == 300
        assert config.swipe_speed_max == 800
        assert config.inapp_dwell_time_min == 10.0
        assert config.inapp_dwell_time_max == 60.0

    def test_tiktok_config_watch_percent_validation(self):
        """Watch percent must be in valid range."""
        config = TikTokConfigSchema(min_watch_percent=0.5, max_watch_percent=2.0)
        assert config.min_watch_percent == 0.5
        assert config.max_watch_percent == 2.0

        with pytest.raises(ValidationError):
            TikTokConfigSchema(min_watch_percent=-0.1)

        with pytest.raises(ValidationError):
            TikTokConfigSchema(min_watch_percent=1.5)  # max is 1

        with pytest.raises(ValidationError):
            TikTokConfigSchema(max_watch_percent=4.0)  # max is 3

    def test_tiktok_config_probability_validation(self):
        """Probabilities must be between 0 and 1."""
        with pytest.raises(ValidationError):
            TikTokConfigSchema(skip_probability=1.5)

        with pytest.raises(ValidationError):
            TikTokConfigSchema(bio_click_probability=-0.1)


class TestInstagramConfigSchema:
    """Tests for InstagramConfigSchema defaults and validation."""

    def test_instagram_config_defaults(self):
        """Instagram config has correct default values."""
        config = InstagramConfigSchema()

        assert config.target_reel_urls == []
        assert config.min_reel_watch_percent == 0.4
        assert config.max_reel_watch_percent == 1.2
        assert config.reel_skip_probability == 0.35
        assert config.story_skip_probability == 0.20
        assert config.story_link_click_probability == 0.25
        assert config.bio_link_click_probability == 0.20
        assert config.profile_visit_probability == 0.12
        assert config.reels_per_session_min == 5
        assert config.reels_per_session_max == 20
        assert config.simulate_inapp_browser is True
        assert config.inapp_dwell_time_min == 10.0
        assert config.inapp_dwell_time_max == 60.0

    def test_instagram_config_custom_values(self):
        """Instagram config accepts custom values."""
        config = InstagramConfigSchema(
            target_reel_urls=["https://instagram.com/reel/abc"],
            min_reel_watch_percent=0.6,
            simulate_inapp_browser=False,
        )

        assert len(config.target_reel_urls) == 1
        assert config.min_reel_watch_percent == 0.6
        assert config.simulate_inapp_browser is False


class TestYouTubeConfigSchema:
    """Tests for YouTubeConfigSchema defaults and validation."""

    def test_youtube_config_defaults(self):
        """YouTube config has correct default values, including min_watch_seconds=30."""
        config = YouTubeConfigSchema()

        assert config.target_video_urls == []
        assert config.target_short_urls == []
        assert config.content_mode == "videos"
        assert config.min_watch_percent == 0.30
        assert config.max_watch_percent == 0.90
        assert config.min_watch_seconds == 30.0  # Critical for YouTube view counting
        assert config.skip_probability == 0.20
        assert config.description_click_probability == 0.10
        assert config.channel_visit_probability == 0.08
        assert config.videos_per_session_min == 5
        assert config.videos_per_session_max == 15
        assert config.shorts_per_session_min == 10
        assert config.shorts_per_session_max == 30

    def test_youtube_config_content_modes(self):
        """YouTube config accepts different content modes."""
        for mode in ["videos", "shorts", "mixed"]:
            config = YouTubeConfigSchema(content_mode=mode)
            assert config.content_mode == mode

    def test_youtube_config_min_watch_seconds_validation(self):
        """min_watch_seconds must be at least 1."""
        config = YouTubeConfigSchema(min_watch_seconds=45.0)
        assert config.min_watch_seconds == 45.0

        with pytest.raises(ValidationError):
            YouTubeConfigSchema(min_watch_seconds=0.5)


class TestDEXToolsConfigSchema:
    """Tests for DEXToolsConfigSchema."""

    def test_dextools_config_defaults(self):
        """DEXTools config has correct default values."""
        config = DEXToolsConfigSchema()

        assert config.pair_url == ""
        assert config.click_social_links is True
        assert config.click_chart_tabs is False  # Default is False for safer automation
        assert config.dwell_time_min == 30.0
        assert config.dwell_time_max == 120.0


class TestGenericConfigSchema:
    """Tests for GenericConfigSchema."""

    def test_generic_config_defaults(self):
        """Generic config has correct default values."""
        config = GenericConfigSchema()

        assert config.dwell_time_min == 10.0
        assert config.dwell_time_max == 60.0
        assert config.click_links is False
        assert config.scroll_page is True


class TestEngineConfigSchema:
    """Tests for EngineConfigSchema."""

    def test_engine_config_defaults(self):
        """Engine config has correct default values."""
        config = EngineConfigSchema()

        assert config.workers == 5
        assert config.proxy_provider == "file"
        assert config.fingerprint_rotation == "per_session"
        assert config.browser_engine == "patchright"
        assert config.headless is True
        assert config.evasion_level == "maximum"
        assert config.request_timeout == 30.0
        assert config.retry_attempts == 3

    def test_engine_config_workers_validation(self):
        """Workers must be between 1 and 50."""
        with pytest.raises(ValidationError):
            EngineConfigSchema(workers=0)

        with pytest.raises(ValidationError):
            EngineConfigSchema(workers=51)


class TestBehaviorConfigSchema:
    """Tests for BehaviorConfigSchema."""

    def test_behavior_config_defaults(self):
        """Behavior config has correct default values."""
        config = BehaviorConfigSchema()

        assert config.mouse_movement == "bezier"
        assert config.typing_speed_min == 40
        assert config.typing_speed_max == 80
        assert config.scroll_behavior == "natural"
        assert config.session_duration_min == 5.0
        assert config.session_duration_max == 20.0


# ============================================================================
# PLATFORM DETECTION REQUEST/RESPONSE TESTS
# ============================================================================


class TestPlatformDetectRequest:
    """Tests for PlatformDetectRequest schema."""

    def test_platform_detect_request(self):
        """PlatformDetectRequest stores URL."""
        request = PlatformDetectRequest(url="https://tiktok.com/@user")
        assert request.url == "https://tiktok.com/@user"


class TestPlatformDetectResponse:
    """Tests for PlatformDetectResponse schema."""

    def test_platform_detect_response(self):
        """PlatformDetectResponse serializes correctly."""
        response = PlatformDetectResponse(
            platform="youtube",
            detected=True,
            metadata={"url": "https://youtube.com/watch?v=abc", "video_id": "abc"},
        )

        assert response.platform == "youtube"
        assert response.detected is True
        assert response.metadata["video_id"] == "abc"

    def test_platform_detect_response_not_detected(self):
        """PlatformDetectResponse for generic/unknown URL."""
        response = PlatformDetectResponse(
            platform="generic",
            detected=False,
            metadata={"url": "https://unknown.com"},
        )

        assert response.platform == "generic"
        assert response.detected is False


# ============================================================================
# METRICS RESPONSE TESTS
# ============================================================================


class TestMetricsResponse:
    """Tests for MetricsResponse schema."""

    def test_metrics_response_defaults(self):
        """MetricsResponse has correct default values."""
        now = datetime.utcnow()
        metrics = MetricsResponse(timestamp=now, uptime_seconds=3600.0)

        assert metrics.timestamp == now
        assert metrics.uptime_seconds == 3600.0
        assert metrics.tasks_pending == 0
        assert metrics.tasks_running == 0
        assert metrics.tasks_completed == 0
        assert metrics.tasks_failed == 0
        assert metrics.tasks_per_minute == 0.0
        assert metrics.proxies_total == 0
        assert metrics.proxies_healthy == 0
        assert metrics.proxies_failed == 0
        assert metrics.sessions_active == 0
        assert metrics.pages_visited == 0
        assert metrics.workers_active == 0
        assert metrics.workers_total == 0

    def test_metrics_response_with_values(self):
        """MetricsResponse with actual metric values."""
        now = datetime.utcnow()
        metrics = MetricsResponse(
            timestamp=now,
            uptime_seconds=7200.0,
            tasks_pending=5,
            tasks_running=10,
            tasks_completed=100,
            tasks_failed=3,
            tasks_per_minute=2.5,
            proxies_total=50,
            proxies_healthy=45,
            proxies_failed=5,
            sessions_active=10,
            pages_visited=500,
            workers_active=8,
            workers_total=10,
        )

        assert metrics.tasks_running == 10
        assert metrics.proxies_healthy == 45
        assert metrics.workers_active == 8


# ============================================================================
# WEBSOCKET EVENT TESTS
# ============================================================================


class TestWebSocketEvent:
    """Tests for WebSocketEvent schema."""

    def test_websocket_event_minimal(self):
        """WebSocketEvent with minimal fields."""
        event = WebSocketEvent(type="ping")

        assert event.type == "ping"
        assert event.task_id is None
        assert event.data == {}
        assert event.timestamp is not None

    def test_websocket_event_with_task(self):
        """WebSocketEvent with task data."""
        event = WebSocketEvent(
            type="task_progress",
            task_id="task-123",
            data={"progress": 0.5, "views": 50},
        )

        assert event.type == "task_progress"
        assert event.task_id == "task-123"
        assert event.data["progress"] == 0.5

    def test_websocket_event_types(self):
        """WebSocketEvent accepts various event types."""
        for event_type in [
            "task_created",
            "task_started",
            "task_completed",
            "task_failed",
            "metrics_update",
            "log",
        ]:
            event = WebSocketEvent(type=event_type)
            assert event.type == event_type


# ============================================================================
# PRESETS TESTS
# ============================================================================


class TestPresets:
    """Tests for configuration presets."""

    def test_presets_exist(self):
        """All expected presets exist."""
        assert "stealth" in PRESETS
        assert "normal" in PRESETS
        assert "fast" in PRESETS

    def test_stealth_preset(self):
        """Stealth preset has conservative settings."""
        preset = PRESETS["stealth"]

        assert isinstance(preset, ConfigPreset)
        assert preset.name == "Stealth"
        assert preset.platform == "generic"
        assert preset.config["skip_probability"] == 0.35
        assert preset.config["videos_per_session_min"] == 5
        assert preset.config["videos_per_session_max"] == 15
        assert preset.config["swipe_speed_min"] == 500
        assert preset.config["swipe_speed_max"] == 1200

    def test_normal_preset(self):
        """Normal preset has balanced settings."""
        preset = PRESETS["normal"]

        assert preset.name == "Normal"
        assert preset.config["skip_probability"] == 0.25
        assert preset.config["videos_per_session_min"] == 10
        assert preset.config["videos_per_session_max"] == 25
        assert preset.config["swipe_speed_min"] == 300
        assert preset.config["swipe_speed_max"] == 800

    def test_fast_preset(self):
        """Fast preset has aggressive settings."""
        preset = PRESETS["fast"]

        assert preset.name == "Fast"
        assert preset.config["skip_probability"] == 0.40
        assert preset.config["videos_per_session_min"] == 15
        assert preset.config["videos_per_session_max"] == 40
        assert preset.config["swipe_speed_min"] == 200
        assert preset.config["swipe_speed_max"] == 500

    def test_preset_descriptions(self):
        """Presets have meaningful descriptions."""
        assert "Maximum anti-detection" in PRESETS["stealth"].description
        assert "Balanced" in PRESETS["normal"].description
        assert "Speed-focused" in PRESETS["fast"].description


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_detect_platform_empty_string(self):
        """Empty URL returns generic."""
        platform, _metadata = detect_platform("")
        assert platform == "generic"

    def test_detect_platform_whitespace_only(self):
        """Whitespace-only URL returns generic."""
        platform, _metadata = detect_platform("   ")
        assert platform == "generic"

    def test_task_create_url_required(self):
        """TaskCreate requires URL."""
        with pytest.raises(ValidationError):
            TaskCreate()

    def test_progress_boundaries(self):
        """TaskResponse progress must be 0-1."""
        now = datetime.utcnow()

        # Valid boundaries
        TaskResponse(
            task_id="1",
            status="pending",
            platform="generic",
            url="https://x.com",
            mode="batch",
            workers=1,
            progress=0.0,
            created_at=now,
        )
        TaskResponse(
            task_id="2",
            status="completed",
            platform="generic",
            url="https://x.com",
            mode="batch",
            workers=1,
            progress=1.0,
            created_at=now,
        )

        # Invalid progress
        with pytest.raises(ValidationError):
            TaskResponse(
                task_id="3",
                status="running",
                platform="generic",
                url="https://x.com",
                mode="batch",
                workers=1,
                progress=-0.1,
                created_at=now,
            )

        with pytest.raises(ValidationError):
            TaskResponse(
                task_id="4",
                status="running",
                platform="generic",
                url="https://x.com",
                mode="batch",
                workers=1,
                progress=1.5,
                created_at=now,
            )

    def test_config_schema_field_ranges(self):
        """Config schemas enforce field ranges."""
        # Videos per session min must be >= 1
        with pytest.raises(ValidationError):
            TikTokConfigSchema(videos_per_session_min=0)

        # Swipe speed min must be >= 100
        with pytest.raises(ValidationError):
            TikTokConfigSchema(swipe_speed_min=50)

        # Dwell time must be >= 1
        with pytest.raises(ValidationError):
            GenericConfigSchema(dwell_time_min=0.5)
