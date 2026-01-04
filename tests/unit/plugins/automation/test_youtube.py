"""Unit tests for YouTube automation plugin."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghoststorm.plugins.automation.youtube import (
    YouTubeAction,
    YouTubeAutomation,
    YouTubeConfig,
    YouTubeSelectors,
)
from ghoststorm.plugins.automation.base import (
    BioClickResult,
    SocialPlatform,
    VideoWatchOutcome,
)


# ============================================================================
# Concrete Subclass - YouTubeAutomation is abstract (missing click_bio_link)
# ============================================================================


class ConcreteYouTubeAutomation(YouTubeAutomation):
    """Concrete implementation of YouTubeAutomation for testing.

    YouTubeAutomation doesn't implement click_bio_link since YouTube
    uses click_description_link instead. We provide a stub for testing.
    """

    async def click_bio_link(
        self,
        page: Any,
        username: str | None = None,
    ) -> BioClickResult:
        """YouTube doesn't have bio links - redirect to description link."""
        return await self.click_description_link(page)


# ============================================================================
# YouTubeConfig Dataclass Tests
# ============================================================================


class TestYouTubeConfig:
    """Tests for YouTubeConfig dataclass."""

    def test_default_min_watch_seconds(self):
        """Test that default min_watch_seconds is 30.0 (YouTube requirement)."""
        config = YouTubeConfig()
        assert config.min_watch_seconds == 30.0

    def test_custom_config(self):
        """Test creating YouTubeConfig with custom values."""
        config = YouTubeConfig(
            target_url="https://youtube.com/@testchannel",
            target_video_urls=["https://youtube.com/watch?v=abc123"],
            target_short_urls=["https://youtube.com/shorts/xyz789"],
            target_channel="testchannel",
            content_mode="shorts",
            min_watch_percent=0.50,
            max_watch_percent=0.95,
            min_watch_seconds=45.0,
            skip_probability=0.10,
            rewatch_probability=0.10,
            like_probability=0.05,
            subscribe_probability=0.02,
            description_click_probability=0.15,
            channel_visit_probability=0.10,
            videos_per_session=(10, 20),
            shorts_per_session=(20, 50),
            viewport_width=414,
            viewport_height=896,
        )

        assert config.target_url == "https://youtube.com/@testchannel"
        assert config.target_video_urls == ["https://youtube.com/watch?v=abc123"]
        assert config.target_short_urls == ["https://youtube.com/shorts/xyz789"]
        assert config.target_channel == "testchannel"
        assert config.content_mode == "shorts"
        assert config.min_watch_percent == 0.50
        assert config.max_watch_percent == 0.95
        assert config.min_watch_seconds == 45.0
        assert config.skip_probability == 0.10
        assert config.rewatch_probability == 0.10
        assert config.like_probability == 0.05
        assert config.subscribe_probability == 0.02
        assert config.description_click_probability == 0.15
        assert config.channel_visit_probability == 0.10
        assert config.videos_per_session == (10, 20)
        assert config.shorts_per_session == (20, 50)
        assert config.viewport_width == 414
        assert config.viewport_height == 896

    def test_default_config_values(self):
        """Test all default config values."""
        config = YouTubeConfig()

        assert config.target_url == ""
        assert config.target_video_urls == []
        assert config.target_short_urls == []
        assert config.target_channel == ""
        assert config.content_mode == "videos"
        assert config.min_watch_percent == 0.30
        assert config.max_watch_percent == 0.90
        assert config.min_watch_seconds == 30.0
        assert config.skip_probability == 0.20
        assert config.rewatch_probability == 0.05
        assert config.like_probability == 0.0
        assert config.subscribe_probability == 0.0
        assert config.comment_probability == 0.0
        assert config.description_click_probability == 0.10
        assert config.channel_visit_probability == 0.08
        assert config.videos_per_session == (5, 15)
        assert config.shorts_per_session == (10, 30)
        assert config.swipe_speed_range == (300, 700)
        assert config.inter_video_delay == (2.0, 8.0)
        assert config.page_load_delay == (3.0, 8.0)
        assert config.inapp_dwell_time == (15.0, 90.0)
        assert config.max_videos_per_session == 20
        assert config.max_shorts_per_session == 40
        assert config.max_channel_visits == 30
        assert config.max_description_clicks == 10
        assert config.viewport_width == 390
        assert config.viewport_height == 844


# ============================================================================
# YouTubeSelectors Dataclass Tests
# ============================================================================


class TestYouTubeSelectors:
    """Tests for YouTubeSelectors dataclass."""

    def test_selector_strings_exist(self):
        """Test that all selector strings are defined and non-empty."""
        selectors = YouTubeSelectors()

        # Video player selectors
        assert selectors.video_player == "video"
        assert selectors.video_container == "#player-container"
        assert selectors.player_controls == ".ytp-chrome-bottom"

        # Engagement button selectors
        assert selectors.like_button == "#segmented-like-button button"
        assert selectors.dislike_button == "#segmented-dislike-button button"
        assert selectors.share_button == "#top-level-buttons-computed ytd-button-renderer:nth-child(3)"
        assert selectors.subscribe_button == "#subscribe-button button"

        # Description and info selectors
        assert selectors.description_expand == "#description-inline-expander"
        assert selectors.description_content == "#description-inline-expander #plain-snippet-text"
        assert selectors.description_links == "#description a[href]"

        # Channel info selectors
        assert selectors.channel_link == "#owner a"
        assert selectors.channel_name == "#owner #channel-name"
        assert selectors.channel_avatar == "#owner #avatar"

        # Video info selectors
        assert selectors.video_title == "h1.ytd-video-primary-info-renderer"
        assert selectors.view_count == "#info-container span.view-count"

        # Shorts specific selectors
        assert selectors.shorts_container == "#shorts-player"
        assert selectors.shorts_video == "#shorts-player video"
        assert selectors.shorts_like == "[aria-label='Like']"
        assert selectors.shorts_comment == "[aria-label='Comments']"
        assert selectors.shorts_share == "[aria-label='Share']"

        # Navigation selectors
        assert selectors.home_tab == "[title='Home']"
        assert selectors.shorts_tab == "[title='Shorts']"
        assert selectors.subscriptions_tab == "[title='Subscriptions']"
        assert selectors.search_button == "#search-icon-legacy"

        # Loading selectors
        assert selectors.loading_spinner == "ytd-video-primary-info-renderer[loading]"
        assert selectors.skeleton_loading == ".ytd-thumbnail-overlay-loading-preview-renderer"

    def test_selectors_are_strings(self):
        """Test that all selectors are non-empty strings."""
        selectors = YouTubeSelectors()

        for attr_name in dir(selectors):
            if not attr_name.startswith("_"):
                value = getattr(selectors, attr_name)
                assert isinstance(value, str), f"{attr_name} should be a string"
                assert len(value) > 0, f"{attr_name} should not be empty"


# ============================================================================
# YouTubeAutomation Class Tests
# ============================================================================


class TestYouTubeAutomationInit:
    """Tests for YouTubeAutomation initialization."""

    def test_init_without_config(self):
        """Test initialization without config uses defaults."""
        automation = ConcreteYouTubeAutomation()

        assert automation.config is not None
        assert isinstance(automation.config, YouTubeConfig)
        assert automation.config.min_watch_seconds == 30.0
        assert automation.selectors is not None
        assert isinstance(automation.selectors, YouTubeSelectors)

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = YouTubeConfig(
            target_video_urls=["https://youtube.com/watch?v=test123"],
            min_watch_seconds=45.0,
            content_mode="shorts",
        )
        automation = ConcreteYouTubeAutomation(config=config)

        assert automation.config is config
        assert automation.config.min_watch_seconds == 45.0
        assert automation.config.content_mode == "shorts"
        assert automation.config.target_video_urls == ["https://youtube.com/watch?v=test123"]

    def test_init_with_custom_selectors(self):
        """Test initialization with custom selectors."""
        selectors = YouTubeSelectors(
            video_player="custom-video",
            shorts_container="custom-shorts",
        )
        automation = ConcreteYouTubeAutomation(selectors=selectors)

        assert automation.selectors is selectors
        assert automation.selectors.video_player == "custom-video"
        assert automation.selectors.shorts_container == "custom-shorts"

    def test_name_property(self):
        """Test that name property returns 'youtube'."""
        automation = ConcreteYouTubeAutomation()
        assert automation.name == "youtube"

    def test_platform_property(self):
        """Test that platform property returns YOUTUBE."""
        automation = ConcreteYouTubeAutomation()
        assert automation.platform == SocialPlatform.YOUTUBE


class TestExtractVideoId:
    """Tests for _extract_video_id method."""

    def test_extract_video_id_watch_url(self):
        """Test extracting video ID from standard watch URL."""
        automation = ConcreteYouTubeAutomation()

        video_id = automation._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_watch_url_with_params(self):
        """Test extracting video ID from watch URL with additional parameters."""
        automation = ConcreteYouTubeAutomation()

        video_id = automation._extract_video_id(
            "https://www.youtube.com/watch?v=abc123&t=120&list=PLxyz"
        )
        assert video_id == "abc123"

    def test_extract_video_id_watch_url_with_hash(self):
        """Test extracting video ID from watch URL with hash fragment."""
        automation = ConcreteYouTubeAutomation()

        video_id = automation._extract_video_id(
            "https://www.youtube.com/watch?v=xyz789#t=30"
        )
        assert video_id == "xyz789"

    def test_extract_video_id_shorts_url(self):
        """Test extracting video ID from Shorts URL."""
        automation = ConcreteYouTubeAutomation()

        video_id = automation._extract_video_id("https://www.youtube.com/shorts/abcdef12345")
        assert video_id == "abcdef12345"

    def test_extract_video_id_shorts_url_with_params(self):
        """Test extracting video ID from Shorts URL with parameters."""
        automation = ConcreteYouTubeAutomation()

        video_id = automation._extract_video_id(
            "https://www.youtube.com/shorts/short123?feature=share"
        )
        assert video_id == "short123"

    def test_extract_video_id_youtu_be_url(self):
        """Test extracting video ID from youtu.be short URL."""
        automation = ConcreteYouTubeAutomation()

        video_id = automation._extract_video_id("https://youtu.be/video_id_here")
        assert video_id == "video_id_here"

    def test_extract_video_id_youtu_be_with_params(self):
        """Test extracting video ID from youtu.be URL with parameters."""
        automation = ConcreteYouTubeAutomation()

        video_id = automation._extract_video_id("https://youtu.be/short_id?t=60")
        assert video_id == "short_id"

    def test_extract_video_id_mobile_url(self):
        """Test extracting video ID from mobile YouTube URL."""
        automation = ConcreteYouTubeAutomation()

        video_id = automation._extract_video_id("https://m.youtube.com/watch?v=mobile123")
        assert video_id == "mobile123"

    def test_extract_video_id_fallback(self):
        """Test fallback to hash for unrecognized URL format."""
        automation = ConcreteYouTubeAutomation()

        video_id = automation._extract_video_id("https://youtube.com/some/unknown/path")
        # Should return a 16-character hash
        assert len(video_id) == 16


# ============================================================================
# watch_video Method Tests
# ============================================================================


class TestWatchVideo:
    """Tests for watch_video method."""

    @pytest.mark.asyncio
    async def test_watch_video_enforces_30s_minimum(self, mock_page):
        """Test that watch_video enforces 30 second minimum watch time."""
        config = YouTubeConfig(min_watch_seconds=30.0)
        automation = ConcreteYouTubeAutomation(config=config)

        # Set up video duration (60 seconds)
        mock_page.set_locator_duration("video", 60.0)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch.object(automation.watch_behavior, "generate_watch_duration") as mock_gen:
                # Simulate behavior wanting to watch only 10 seconds
                mock_gen.return_value = (10.0, "partial")

                result = await automation.watch_video(mock_page)

                assert result.success is True
                # Should have called sleep with at least 30 seconds
                mock_sleep.assert_called()
                actual_sleep_time = mock_sleep.call_args[0][0]
                assert actual_sleep_time >= 30.0, (
                    f"Watch time should be at least 30s, got {actual_sleep_time}"
                )

    @pytest.mark.asyncio
    async def test_watch_video_success_with_duration(self, mock_page):
        """Test watch_video with explicit duration."""
        automation = ConcreteYouTubeAutomation()

        mock_page.set_locator_duration("video", 120.0)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await automation.watch_video(mock_page, duration=45.0)

            assert result.success is True
            assert result.watch_duration == 45.0
            assert result.video_duration == 120.0
            assert result.outcome == VideoWatchOutcome.PARTIAL
            mock_sleep.assert_called_once_with(45.0)

    @pytest.mark.asyncio
    async def test_watch_video_increments_counter(self, mock_page):
        """Test that watch_video increments the videos watched counter."""
        automation = ConcreteYouTubeAutomation()
        initial_count = automation._videos_watched

        mock_page.set_locator_duration("video", 60.0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await automation.watch_video(mock_page, duration=35.0)

        assert automation._videos_watched == initial_count + 1

    @pytest.mark.asyncio
    async def test_watch_video_returns_completion_rate(self, mock_page):
        """Test that watch_video calculates correct completion rate."""
        automation = ConcreteYouTubeAutomation()

        mock_page.set_locator_duration("video", 100.0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.watch_video(mock_page, duration=50.0)

        assert result.completion_rate == 0.5


# ============================================================================
# watch_short Method Tests
# ============================================================================


class TestWatchShort:
    """Tests for watch_short method."""

    @pytest.mark.asyncio
    async def test_watch_short_success(self, mock_page):
        """Test watch_short basic success case."""
        automation = ConcreteYouTubeAutomation()

        mock_page.set_locator_duration("video", 30.0)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await automation.watch_short(mock_page, duration=20.0)

            assert result.success is True
            assert result.watch_duration == 20.0
            mock_sleep.assert_called_once_with(20.0)

    @pytest.mark.asyncio
    async def test_watch_short_increments_counter(self, mock_page):
        """Test that watch_short increments the shorts watched counter."""
        automation = ConcreteYouTubeAutomation()
        initial_count = automation._shorts_watched

        mock_page.set_locator_duration("video", 30.0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await automation.watch_short(mock_page, duration=15.0)

        assert automation._shorts_watched == initial_count + 1

    @pytest.mark.asyncio
    async def test_watch_short_generates_duration_if_not_provided(self, mock_page):
        """Test that watch_short uses behavior model when duration not provided."""
        automation = ConcreteYouTubeAutomation()

        mock_page.set_locator_duration("video", 45.0)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch.object(automation.watch_behavior, "generate_watch_duration") as mock_gen:
                mock_gen.return_value = (25.0, "partial")

                result = await automation.watch_short(mock_page)

                assert result.success is True
                mock_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_short_handles_missing_duration(self, mock_page):
        """Test watch_short when video duration is not available."""
        automation = ConcreteYouTubeAutomation()

        # Set locator to return None for duration
        mock_page.set_locator_duration("video", None)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.watch_short(mock_page, duration=10.0)

            # Should still succeed, video_duration will be randomly generated
            assert result.success is True


# ============================================================================
# click_description_link Method Tests
# ============================================================================


class TestClickDescriptionLink:
    """Tests for click_description_link method."""

    @pytest.mark.asyncio
    async def test_click_description_link_no_links(self, mock_page):
        """Test click_description_link when no links are found."""
        automation = ConcreteYouTubeAutomation()

        # Set up expand button and no links
        mock_page.set_locator_count(automation.selectors.description_expand, 1)
        mock_page.set_locator_count(automation.selectors.description_links, 0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.click_description_link(mock_page)

        assert result.success is False
        assert "No links" in result.error

    @pytest.mark.asyncio
    async def test_click_description_link_success(self, mock_page):
        """Test click_description_link success case."""
        automation = ConcreteYouTubeAutomation()

        # Create a mock locator with links
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=2)

        mock_link = MagicMock()
        mock_link.get_attribute = AsyncMock(return_value="https://example.com/link")
        mock_link.click = AsyncMock()
        mock_locator.nth = MagicMock(return_value=mock_link)

        # Set up expand button
        expand_locator = MagicMock()
        expand_locator.count = AsyncMock(return_value=1)

        original_locator = mock_page.locator

        def custom_locator(selector):
            if selector == automation.selectors.description_links:
                return mock_locator
            if selector == automation.selectors.description_expand:
                return expand_locator
            return original_locator(selector)

        mock_page.locator = custom_locator

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(automation.inapp_behavior, "generate_dwell_time", return_value=20.0):
                with patch.object(automation.inapp_behavior, "generate_scroll_pattern", return_value=[]):
                    with patch.object(automation.inapp_behavior, "should_return_to_app", return_value=True):
                        result = await automation.click_description_link(mock_page)

        assert result.success is True
        assert result.target_url == "https://example.com/link"

    @pytest.mark.asyncio
    async def test_click_description_link_increments_counter(self, mock_page):
        """Test that click_description_link increments the click counter."""
        automation = ConcreteYouTubeAutomation()
        initial_count = automation._description_clicks

        # Create a mock locator with links
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)

        mock_link = MagicMock()
        mock_link.get_attribute = AsyncMock(return_value="https://example.com")
        mock_link.click = AsyncMock()
        mock_locator.nth = MagicMock(return_value=mock_link)

        expand_locator = MagicMock()
        expand_locator.count = AsyncMock(return_value=0)

        original_locator = mock_page.locator

        def custom_locator(selector):
            if selector == automation.selectors.description_links:
                return mock_locator
            if selector == automation.selectors.description_expand:
                return expand_locator
            return original_locator(selector)

        mock_page.locator = custom_locator

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(automation.inapp_behavior, "generate_dwell_time", return_value=10.0):
                with patch.object(automation.inapp_behavior, "generate_scroll_pattern", return_value=[]):
                    with patch.object(automation.inapp_behavior, "should_return_to_app", return_value=True):
                        await automation.click_description_link(mock_page)

        assert automation._description_clicks == initial_count + 1


# ============================================================================
# visit_channel Method Tests
# ============================================================================


class TestVisitChannel:
    """Tests for visit_channel method."""

    @pytest.mark.asyncio
    async def test_visit_channel_direct_navigation(self, mock_page):
        """Test visit_channel with direct channel handle."""
        automation = ConcreteYouTubeAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.visit_channel(mock_page, channel="testchannel")

        assert result is True
        assert mock_page.url == "https://www.youtube.com/@testchannel"

    @pytest.mark.asyncio
    async def test_visit_channel_increments_counter(self, mock_page):
        """Test that visit_channel increments the channels visited counter."""
        automation = ConcreteYouTubeAutomation()
        initial_count = automation._channels_visited

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await automation.visit_channel(mock_page, channel="somechannel")

        assert automation._channels_visited == initial_count + 1

    @pytest.mark.asyncio
    async def test_visit_channel_from_current_video(self, mock_page):
        """Test visit_channel clicking channel link from current video."""
        automation = ConcreteYouTubeAutomation()

        # Set up the channel link locator
        mock_page.set_locator_count(automation.selectors.channel_link, 1)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.visit_channel(mock_page, channel=None)

        assert result is True


# ============================================================================
# watch_direct_video Method Tests
# ============================================================================


class TestWatchDirectVideo:
    """Tests for watch_direct_video method."""

    @pytest.mark.asyncio
    async def test_watch_direct_video_success(self, mock_page):
        """Test watch_direct_video success case."""
        automation = ConcreteYouTubeAutomation()

        video_url = "https://youtube.com/watch?v=test123"
        mock_page.set_locator_duration("video", 120.0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch(
                "ghoststorm.plugins.automation.youtube.get_view_tracker"
            ) as mock_tracker:
                tracker_instance = MagicMock()
                tracker_instance.can_view.return_value = (True, None)
                tracker_instance.get_minimum_watch_time.return_value = 30.0
                tracker_instance.record_view.return_value = True
                mock_tracker.return_value = tracker_instance

                result = await automation.watch_direct_video(
                    mock_page,
                    video_url=video_url,
                    watch_duration=35.0,
                )

        assert result.success is True
        assert result.watch_duration == 35.0
        assert mock_page.url == video_url

    @pytest.mark.asyncio
    async def test_watch_direct_video_rate_limited(self, mock_page):
        """Test watch_direct_video when rate limited."""
        automation = ConcreteYouTubeAutomation()

        video_url = "https://youtube.com/watch?v=limited123"

        with patch(
            "ghoststorm.plugins.automation.youtube.get_view_tracker"
        ) as mock_tracker:
            tracker_instance = MagicMock()
            tracker_instance.can_view.return_value = (False, "Rate limit exceeded")
            mock_tracker.return_value = tracker_instance

            result = await automation.watch_direct_video(
                mock_page,
                video_url=video_url,
            )

        assert result.success is False
        assert "Rate limited" in result.error

    @pytest.mark.asyncio
    async def test_watch_direct_video_extracts_video_id(self, mock_page):
        """Test that watch_direct_video correctly extracts video ID."""
        automation = ConcreteYouTubeAutomation()

        video_url = "https://youtube.com/watch?v=unique_id_123"
        mock_page.set_locator_duration("video", 60.0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch(
                "ghoststorm.plugins.automation.youtube.get_view_tracker"
            ) as mock_tracker:
                tracker_instance = MagicMock()
                tracker_instance.can_view.return_value = (True, None)
                tracker_instance.get_minimum_watch_time.return_value = 30.0
                tracker_instance.record_view.return_value = True
                mock_tracker.return_value = tracker_instance

                await automation.watch_direct_video(
                    mock_page,
                    video_url=video_url,
                    watch_duration=35.0,
                )

                # Verify video_id was passed correctly
                call_args = tracker_instance.can_view.call_args
                assert call_args[1]["video_id"] == "unique_id_123"


# ============================================================================
# simulate_shorts_session Method Tests
# ============================================================================


class TestSimulateShortsSession:
    """Tests for simulate_shorts_session method."""

    @pytest.mark.asyncio
    async def test_simulate_shorts_session_basic_flow(self, mock_page):
        """Test basic shorts session flow."""
        config = YouTubeConfig(
            shorts_per_session=(2, 3),
            max_shorts_per_session=3,
        )
        automation = ConcreteYouTubeAutomation(config=config)

        mock_page.set_locator_duration("video", 30.0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                with patch.object(automation.watch_behavior, "generate_watch_duration") as mock_gen:
                    mock_gen.return_value = (15.0, "partial")

                    with patch.object(automation, "swipe_to_next") as mock_swipe:
                        mock_swipe.return_value = MagicMock(success=True, error=None)

                        result = await automation.simulate_shorts_session(
                            mock_page,
                            shorts_to_watch=2,
                        )

        assert result.platform == SocialPlatform.YOUTUBE
        assert result.videos_watched == 2
        # Swipe should be called for each short
        assert mock_swipe.call_count == 2

    @pytest.mark.asyncio
    async def test_simulate_shorts_session_navigates_to_shorts(self, mock_page):
        """Test that shorts session navigates to the shorts page."""
        automation = ConcreteYouTubeAutomation()

        mock_page.set_locator_duration("video", 30.0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                with patch.object(automation, "watch_short") as mock_watch:
                    mock_watch.return_value = MagicMock(success=True, error=None)
                    with patch.object(automation, "swipe_to_next") as mock_swipe:
                        mock_swipe.return_value = MagicMock(success=True, error=None)

                        await automation.simulate_shorts_session(
                            mock_page,
                            shorts_to_watch=1,
                        )

        assert mock_page.url == "https://www.youtube.com/shorts"

    @pytest.mark.asyncio
    async def test_simulate_shorts_session_respects_max_shorts(self, mock_page):
        """Test that shorts session respects max_shorts_per_session limit."""
        config = YouTubeConfig(
            max_shorts_per_session=5,
        )
        automation = ConcreteYouTubeAutomation(config=config)

        mock_page.set_locator_duration("video", 30.0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                with patch.object(automation, "watch_short") as mock_watch:
                    mock_watch.return_value = MagicMock(success=True, error=None)
                    with patch.object(automation, "swipe_to_next") as mock_swipe:
                        mock_swipe.return_value = MagicMock(success=True, error=None)

                        # Request 10 shorts but max is 5
                        result = await automation.simulate_shorts_session(
                            mock_page,
                            shorts_to_watch=10,
                        )

        assert result.videos_watched == 5

    @pytest.mark.asyncio
    async def test_simulate_shorts_session_handles_break(self, mock_page):
        """Test that shorts session handles break correctly."""
        automation = ConcreteYouTubeAutomation()

        mock_page.set_locator_duration("video", 30.0)

        break_taken = False

        def should_take_break_side_effect():
            nonlocal break_taken
            if not break_taken:
                break_taken = True
                return True
            return False

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(
                automation.watch_behavior,
                "should_take_break",
                side_effect=should_take_break_side_effect,
            ):
                with patch.object(
                    automation.watch_behavior,
                    "generate_break_duration",
                    return_value=5.0,
                ):
                    with patch.object(automation, "watch_short") as mock_watch:
                        mock_watch.return_value = MagicMock(success=True, error=None)
                        with patch.object(automation, "swipe_to_next") as mock_swipe:
                            mock_swipe.return_value = MagicMock(success=True, error=None)

                            result = await automation.simulate_shorts_session(
                                mock_page,
                                shorts_to_watch=3,
                            )

        # Session should complete
        assert result.platform == SocialPlatform.YOUTUBE


# ============================================================================
# YouTubeAction Enum Tests
# ============================================================================


class TestYouTubeAction:
    """Tests for YouTubeAction enum."""

    def test_action_values(self):
        """Test that all action values are correct."""
        assert YouTubeAction.WATCH_VIDEO == "watch_video"
        assert YouTubeAction.WATCH_SHORT == "watch_short"
        assert YouTubeAction.SWIPE_UP == "swipe_up"
        assert YouTubeAction.SWIPE_DOWN == "swipe_down"
        assert YouTubeAction.CLICK_DESCRIPTION_LINK == "click_description_link"
        assert YouTubeAction.VISIT_CHANNEL == "visit_channel"
        assert YouTubeAction.LIKE_VIDEO == "like_video"
        assert YouTubeAction.SUBSCRIBE == "subscribe"
        assert YouTubeAction.SEARCH == "search"
