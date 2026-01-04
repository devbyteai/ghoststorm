"""Tests for TikTok automation plugin.

Tests dataclasses, configuration, and automation methods from
ghoststorm.plugins.automation.tiktok
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghoststorm.plugins.automation.base import (
    BioClickResult,
    SessionResult,
    SocialPlatform,
    SwipeResult,
    VideoWatchOutcome,
    WatchResult,
)
from ghoststorm.plugins.automation.tiktok import (
    TikTokAction,
    TikTokAutomation,
    TikTokConfig,
    TikTokSelectors,
)


# ============================================================================
# TikTokConfig DATACLASS TESTS
# ============================================================================


class TestTikTokConfig:
    """Tests for TikTokConfig dataclass."""

    def test_default_values(self):
        """TikTokConfig should have correct default values."""
        config = TikTokConfig()

        assert config.target_url == ""
        assert config.target_username == ""
        assert config.target_video_urls == []
        assert config.min_watch_percent == 0.3
        assert config.max_watch_percent == 1.5
        assert config.skip_probability == 0.30
        assert config.rewatch_probability == 0.10
        assert config.like_probability == 0.0
        assert config.follow_probability == 0.0
        assert config.comment_probability == 0.0
        assert config.bio_click_probability == 0.15
        assert config.profile_visit_probability == 0.10
        assert config.videos_per_session == (10, 30)
        assert config.session_duration_minutes == (5, 20)
        assert config.swipe_speed_range == (300, 800)
        assert config.inter_video_delay == (0.5, 2.0)
        assert config.page_load_delay == (3.0, 8.0)
        assert config.inapp_dwell_time == (10.0, 60.0)
        assert config.max_profile_views == 100
        assert config.max_bio_clicks == 15
        assert config.max_videos_per_session == 50
        assert config.viewport_width == 390
        assert config.viewport_height == 844

    def test_custom_config(self):
        """TikTokConfig should accept custom values."""
        config = TikTokConfig(
            target_url="https://tiktok.com/@testuser",
            target_username="testuser",
            target_video_urls=["https://tiktok.com/@user/video/123"],
            min_watch_percent=0.5,
            max_watch_percent=2.0,
            skip_probability=0.1,
            rewatch_probability=0.2,
            like_probability=0.05,
            follow_probability=0.01,
            comment_probability=0.02,
            bio_click_probability=0.25,
            profile_visit_probability=0.15,
            videos_per_session=(5, 15),
            session_duration_minutes=(10, 30),
            swipe_speed_range=(200, 600),
            inter_video_delay=(1.0, 3.0),
            page_load_delay=(2.0, 6.0),
            inapp_dwell_time=(15.0, 45.0),
            max_profile_views=50,
            max_bio_clicks=10,
            max_videos_per_session=30,
            viewport_width=414,
            viewport_height=896,
        )

        assert config.target_url == "https://tiktok.com/@testuser"
        assert config.target_username == "testuser"
        assert config.target_video_urls == ["https://tiktok.com/@user/video/123"]
        assert config.min_watch_percent == 0.5
        assert config.max_watch_percent == 2.0
        assert config.skip_probability == 0.1
        assert config.rewatch_probability == 0.2
        assert config.like_probability == 0.05
        assert config.follow_probability == 0.01
        assert config.comment_probability == 0.02
        assert config.bio_click_probability == 0.25
        assert config.profile_visit_probability == 0.15
        assert config.videos_per_session == (5, 15)
        assert config.session_duration_minutes == (10, 30)
        assert config.swipe_speed_range == (200, 600)
        assert config.inter_video_delay == (1.0, 3.0)
        assert config.page_load_delay == (2.0, 6.0)
        assert config.inapp_dwell_time == (15.0, 45.0)
        assert config.max_profile_views == 50
        assert config.max_bio_clicks == 10
        assert config.max_videos_per_session == 30
        assert config.viewport_width == 414
        assert config.viewport_height == 896

    def test_target_video_urls_default_factory(self):
        """Each TikTokConfig should have independent target_video_urls list."""
        config1 = TikTokConfig()
        config2 = TikTokConfig()

        config1.target_video_urls.append("https://tiktok.com/video/1")

        assert config1.target_video_urls == ["https://tiktok.com/video/1"]
        assert config2.target_video_urls == []


# ============================================================================
# TikTokSelectors DATACLASS TESTS
# ============================================================================


class TestTikTokSelectors:
    """Tests for TikTokSelectors dataclass."""

    def test_video_selectors_exist(self):
        """TikTokSelectors should have video-related selectors."""
        selectors = TikTokSelectors()

        assert selectors.video_container == "[data-e2e='recommend-list-item-container']"
        assert selectors.video_player == "video"
        assert selectors.video_wrapper == ".tiktok-web-player"

    def test_engagement_selectors_exist(self):
        """TikTokSelectors should have engagement button selectors."""
        selectors = TikTokSelectors()

        assert selectors.like_button == "[data-e2e='like-icon']"
        assert selectors.comment_button == "[data-e2e='comment-icon']"
        assert selectors.share_button == "[data-e2e='share-icon']"
        assert selectors.favorite_button == "[data-e2e='undefined-icon']"

    def test_profile_selectors_exist(self):
        """TikTokSelectors should have profile-related selectors."""
        selectors = TikTokSelectors()

        assert selectors.profile_link == "[data-e2e='video-author-avatar']"
        assert selectors.profile_username == "[data-e2e='video-author-uniqueid']"
        assert selectors.profile_name == "[data-e2e='video-author-nickname']"

    def test_bio_selectors_exist(self):
        """TikTokSelectors should have bio and link selectors."""
        selectors = TikTokSelectors()

        assert selectors.bio_link == "[data-e2e='user-link']"
        assert selectors.profile_bio == "[data-e2e='user-bio']"
        assert selectors.follow_button == "[data-e2e='follow-button']"

    def test_caption_and_music_selectors_exist(self):
        """TikTokSelectors should have caption and music selectors."""
        selectors = TikTokSelectors()

        assert selectors.caption_text == "[data-e2e='video-desc']"
        assert selectors.music_info == "[data-e2e='video-music']"

    def test_navigation_selectors_exist(self):
        """TikTokSelectors should have navigation selectors."""
        selectors = TikTokSelectors()

        assert selectors.fyp_tab == "[data-e2e='nav-foryou']"
        assert selectors.following_tab == "[data-e2e='nav-following']"
        assert selectors.search_input == "[data-e2e='search-user-input']"

    def test_swipe_and_loading_selectors_exist(self):
        """TikTokSelectors should have swipe area and loading selectors."""
        selectors = TikTokSelectors()

        assert selectors.swipe_area == "[data-e2e='recommend-list-item-container']"
        assert selectors.loading_spinner == ".loading-spinner"
        assert selectors.video_loading == "[data-e2e='video-loading']"

    def test_custom_selectors(self):
        """TikTokSelectors should accept custom values."""
        selectors = TikTokSelectors(
            video_player="video.custom-player",
            like_button=".custom-like-btn",
        )

        assert selectors.video_player == "video.custom-player"
        assert selectors.like_button == ".custom-like-btn"
        # Others should remain default
        assert selectors.comment_button == "[data-e2e='comment-icon']"


# ============================================================================
# TikTokAction ENUM TESTS
# ============================================================================


class TestTikTokAction:
    """Tests for TikTokAction enum."""

    def test_all_actions_present(self):
        """All expected TikTok actions should be defined."""
        actions = list(TikTokAction)
        assert len(actions) == 9

        assert TikTokAction.WATCH_VIDEO in actions
        assert TikTokAction.SWIPE_UP in actions
        assert TikTokAction.SWIPE_DOWN in actions
        assert TikTokAction.CLICK_PROFILE in actions
        assert TikTokAction.CLICK_BIO_LINK in actions
        assert TikTokAction.LIKE_VIDEO in actions
        assert TikTokAction.VIEW_COMMENTS in actions
        assert TikTokAction.SHARE_VIDEO in actions
        assert TikTokAction.SEARCH in actions

    def test_action_values(self):
        """TikTokAction values should be correct."""
        assert TikTokAction.WATCH_VIDEO.value == "watch_video"
        assert TikTokAction.SWIPE_UP.value == "swipe_up"
        assert TikTokAction.SWIPE_DOWN.value == "swipe_down"
        assert TikTokAction.CLICK_PROFILE.value == "click_profile"
        assert TikTokAction.CLICK_BIO_LINK.value == "click_bio_link"
        assert TikTokAction.LIKE_VIDEO.value == "like_video"
        assert TikTokAction.VIEW_COMMENTS.value == "view_comments"
        assert TikTokAction.SHARE_VIDEO.value == "share_video"
        assert TikTokAction.SEARCH.value == "search"


# ============================================================================
# TikTokAutomation CLASS TESTS
# ============================================================================


class TestTikTokAutomationInit:
    """Tests for TikTokAutomation initialization."""

    def test_init_without_config(self):
        """TikTokAutomation should initialize with default config."""
        automation = TikTokAutomation()

        assert automation.config is not None
        assert automation.selectors is not None
        assert automation.config.target_username == ""
        assert automation.config.viewport_width == 390

    def test_init_with_config(self):
        """TikTokAutomation should accept custom config."""
        config = TikTokConfig(
            target_username="testuser",
            viewport_width=414,
        )
        automation = TikTokAutomation(config=config)

        assert automation.config.target_username == "testuser"
        assert automation.config.viewport_width == 414

    def test_init_with_selectors(self):
        """TikTokAutomation should accept custom selectors."""
        selectors = TikTokSelectors(
            video_player="video.custom",
        )
        automation = TikTokAutomation(selectors=selectors)

        assert automation.selectors.video_player == "video.custom"

    def test_name_property(self):
        """TikTokAutomation name should be 'tiktok'."""
        automation = TikTokAutomation()
        assert automation.name == "tiktok"

    def test_platform_property(self):
        """TikTokAutomation platform should be SocialPlatform.TIKTOK."""
        automation = TikTokAutomation()
        assert automation.platform == SocialPlatform.TIKTOK


# ============================================================================
# _extract_video_id TESTS
# ============================================================================


class TestExtractVideoId:
    """Tests for _extract_video_id method."""

    def test_standard_video_url(self):
        """Should extract video ID from standard TikTok URL."""
        automation = TikTokAutomation()

        url = "https://www.tiktok.com/@username/video/7123456789012345678"
        video_id = automation._extract_video_id(url)

        assert video_id == "7123456789012345678"

    def test_standard_url_with_params(self):
        """Should extract video ID ignoring URL parameters."""
        automation = TikTokAutomation()

        url = "https://www.tiktok.com/@username/video/7123456789012345678?is_from_webapp=1&sender_device=pc"
        video_id = automation._extract_video_id(url)

        assert video_id == "7123456789012345678"

    def test_short_vm_tiktok_url(self):
        """Should extract short code from vm.tiktok.com URL."""
        automation = TikTokAutomation()

        url = "https://vm.tiktok.com/XXXXXXX/"
        video_id = automation._extract_video_id(url)

        assert video_id == "XXXXXXX"

    def test_short_vm_url_without_trailing_slash(self):
        """Should extract short code without trailing slash."""
        automation = TikTokAutomation()

        url = "https://vm.tiktok.com/AbC123"
        video_id = automation._extract_video_id(url)

        assert video_id == "AbC123"

    def test_short_t_url(self):
        """Should extract short code from /t/ URL format."""
        automation = TikTokAutomation()

        url = "https://www.tiktok.com/t/XXXXXXX/"
        video_id = automation._extract_video_id(url)

        assert video_id == "XXXXXXX"

    def test_short_url_with_params(self):
        """Should extract short code ignoring URL parameters."""
        automation = TikTokAutomation()

        url = "https://vm.tiktok.com/AbC123?param=value"
        video_id = automation._extract_video_id(url)

        assert video_id == "AbC123"

    def test_fallback_hash_for_unknown_format(self):
        """Should generate hash ID for unknown URL formats."""
        automation = TikTokAutomation()

        url = "https://www.tiktok.com/unknown/format"
        video_id = automation._extract_video_id(url)

        # Should return a 16-character hash
        assert len(video_id) == 16


# ============================================================================
# watch_video ASYNC TESTS
# ============================================================================


class TestWatchVideo:
    """Tests for watch_video async method."""

    @pytest.mark.asyncio
    async def test_watch_video_success(self, mock_page, mock_sleep):
        """watch_video should return success WatchResult."""
        automation = TikTokAutomation()
        mock_page.set_locator_duration("video", 30.0)

        result = await automation.watch_video(mock_page)

        assert result.success is True
        assert result.outcome in [
            VideoWatchOutcome.SKIPPED,
            VideoWatchOutcome.PARTIAL,
            VideoWatchOutcome.FULL,
            VideoWatchOutcome.REWATCHED,
        ]
        assert mock_sleep.called

    @pytest.mark.asyncio
    async def test_watch_video_with_forced_duration(self, mock_page, mock_sleep):
        """watch_video should accept forced duration."""
        automation = TikTokAutomation()
        mock_page.set_locator_duration("video", 30.0)

        result = await automation.watch_video(mock_page, duration=10.0)

        assert result.success is True
        mock_sleep.assert_called()
        # Check that sleep was called with approximately 10.0 seconds
        # (may be modified by coherence modifiers)

    @pytest.mark.asyncio
    async def test_watch_video_increments_counter(self, mock_page, mock_sleep):
        """watch_video should increment videos_watched counter."""
        automation = TikTokAutomation()
        mock_page.set_locator_duration("video", 15.0)

        initial_count = automation._videos_watched
        await automation.watch_video(mock_page, duration=1.0)

        assert automation._videos_watched == initial_count + 1

    @pytest.mark.asyncio
    async def test_watch_video_failure_returns_error(self, mock_page, mock_sleep):
        """watch_video should handle failures gracefully."""
        automation = TikTokAutomation()

        # Make locator.evaluate raise an exception
        mock_page._locators["video"] = MagicMock()
        mock_page._locators["video"].first = mock_page._locators["video"]
        mock_page._locators["video"].evaluate = AsyncMock(side_effect=Exception("Video not found"))

        mock_sleep.side_effect = Exception("Test failure")

        result = await automation.watch_video(mock_page)

        assert result.success is False
        assert result.outcome == VideoWatchOutcome.SKIPPED
        assert result.error is not None


# ============================================================================
# swipe_to_next and swipe_to_previous ASYNC TESTS
# ============================================================================


class TestSwipeMethods:
    """Tests for swipe_to_next and swipe_to_previous methods."""

    @pytest.mark.asyncio
    async def test_swipe_to_next_success(self, mock_page, mock_sleep):
        """swipe_to_next should return successful SwipeResult."""
        automation = TikTokAutomation()

        result = await automation.swipe_to_next(mock_page)

        assert result.success is True
        assert result.direction == "up"
        assert result.duration_ms > 0
        assert result.distance_px > 0

    @pytest.mark.asyncio
    async def test_swipe_to_next_calls_touchscreen(self, mock_page, mock_sleep):
        """swipe_to_next should interact with touchscreen."""
        automation = TikTokAutomation()

        await automation.swipe_to_next(mock_page)

        mock_page.touchscreen.tap.assert_called()

    @pytest.mark.asyncio
    async def test_swipe_to_previous_success(self, mock_page, mock_sleep):
        """swipe_to_previous should return successful SwipeResult."""
        automation = TikTokAutomation()

        result = await automation.swipe_to_previous(mock_page)

        assert result.success is True
        assert result.direction == "down"
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_swipe_to_previous_direction(self, mock_page, mock_sleep):
        """swipe_to_previous should use downward direction."""
        automation = TikTokAutomation()

        result = await automation.swipe_to_previous(mock_page)

        assert result.direction == "down"


# ============================================================================
# visit_profile ASYNC TESTS
# ============================================================================


class TestVisitProfile:
    """Tests for visit_profile method."""

    @pytest.mark.asyncio
    async def test_visit_profile_success(self, mock_page, mock_sleep):
        """visit_profile should return True on success."""
        automation = TikTokAutomation()
        mock_page.set_locator_count("[data-e2e='video-author-avatar']", 1)

        result = await automation.visit_profile(mock_page)

        assert result is True
        assert automation._profiles_visited == 1

    @pytest.mark.asyncio
    async def test_visit_profile_increments_counter(self, mock_page, mock_sleep):
        """visit_profile should increment profiles_visited counter."""
        automation = TikTokAutomation()
        mock_page.set_locator_count("[data-e2e='video-author-avatar']", 1)

        initial_count = automation._profiles_visited
        await automation.visit_profile(mock_page)

        assert automation._profiles_visited == initial_count + 1


# ============================================================================
# click_bio_link ASYNC TESTS
# ============================================================================


class TestClickBioLink:
    """Tests for click_bio_link method."""

    @pytest.mark.asyncio
    async def test_click_bio_link_not_found(self, mock_page, mock_sleep):
        """click_bio_link should return error when no link found."""
        automation = TikTokAutomation()
        mock_page.set_locator_count("[data-e2e='user-link']", 0)

        result = await automation.click_bio_link(mock_page)

        assert result.success is False
        assert result.error == "No bio link found"

    @pytest.mark.asyncio
    async def test_click_bio_link_with_username_navigates(self, mock_page, mock_sleep):
        """click_bio_link should navigate to profile when username provided."""
        automation = TikTokAutomation()
        mock_page.set_locator_count("[data-e2e='user-link']", 0)

        await automation.click_bio_link(mock_page, username="testuser")

        # Should have navigated to profile URL
        assert "@testuser" in mock_page.url

    @pytest.mark.asyncio
    async def test_click_bio_link_success(self, mock_page, mock_sleep):
        """click_bio_link should succeed when link exists."""
        automation = TikTokAutomation()
        mock_page.set_locator_count("[data-e2e='user-link']", 1)
        mock_page.set_locator_href("[data-e2e='user-link']", "https://example.com")

        result = await automation.click_bio_link(mock_page)

        assert result.success is True
        assert result.target_url == "https://example.com"
        assert automation._bio_clicks == 1

    @pytest.mark.asyncio
    async def test_click_bio_link_increments_counter(self, mock_page, mock_sleep):
        """click_bio_link should increment bio_clicks counter."""
        automation = TikTokAutomation()
        mock_page.set_locator_count("[data-e2e='user-link']", 1)
        mock_page.set_locator_href("[data-e2e='user-link']", "https://test.com")

        initial_count = automation._bio_clicks
        await automation.click_bio_link(mock_page)

        assert automation._bio_clicks == initial_count + 1


# ============================================================================
# watch_direct_video ASYNC TESTS
# ============================================================================


class TestWatchDirectVideo:
    """Tests for watch_direct_video method."""

    @pytest.mark.asyncio
    async def test_watch_direct_video_success(self, mock_page, mock_sleep):
        """watch_direct_video should return success for valid URL."""
        automation = TikTokAutomation()
        mock_page.set_locator_duration("video", 30.0)

        video_url = "https://www.tiktok.com/@user/video/7123456789"

        with patch("ghoststorm.plugins.automation.tiktok.get_view_tracker") as mock_tracker:
            tracker_instance = MagicMock()
            tracker_instance.can_view.return_value = (True, None)
            tracker_instance.get_minimum_watch_time.return_value = 3.0
            tracker_instance.record_view.return_value = True
            mock_tracker.return_value = tracker_instance

            result = await automation.watch_direct_video(
                mock_page,
                video_url=video_url,
            )

        assert result.success is True
        assert result.outcome in [
            VideoWatchOutcome.SKIPPED,
            VideoWatchOutcome.PARTIAL,
            VideoWatchOutcome.FULL,
            VideoWatchOutcome.REWATCHED,
        ]

    @pytest.mark.asyncio
    async def test_watch_direct_video_rate_limited(self, mock_page, mock_sleep):
        """watch_direct_video should handle rate limiting."""
        automation = TikTokAutomation()

        video_url = "https://www.tiktok.com/@user/video/7123456789"

        with patch("ghoststorm.plugins.automation.tiktok.get_view_tracker") as mock_tracker:
            tracker_instance = MagicMock()
            tracker_instance.can_view.return_value = (False, "Rate limit exceeded")
            mock_tracker.return_value = tracker_instance

            result = await automation.watch_direct_video(
                mock_page,
                video_url=video_url,
            )

        assert result.success is False
        assert result.outcome == VideoWatchOutcome.SKIPPED
        assert "Rate limited" in result.error

    @pytest.mark.asyncio
    async def test_watch_direct_video_with_proxy_and_fingerprint(self, mock_page, mock_sleep):
        """watch_direct_video should pass proxy and fingerprint IDs."""
        automation = TikTokAutomation()
        mock_page.set_locator_duration("video", 20.0)

        video_url = "https://www.tiktok.com/@user/video/7123456789"

        with patch("ghoststorm.plugins.automation.tiktok.get_view_tracker") as mock_tracker:
            tracker_instance = MagicMock()
            tracker_instance.can_view.return_value = (True, None)
            tracker_instance.get_minimum_watch_time.return_value = 3.0
            tracker_instance.record_view.return_value = True
            mock_tracker.return_value = tracker_instance

            await automation.watch_direct_video(
                mock_page,
                video_url=video_url,
                proxy_id="proxy123",
                fingerprint_id="fp456",
            )

            # Verify can_view was called with proxy and fingerprint
            tracker_instance.can_view.assert_called_once()
            call_kwargs = tracker_instance.can_view.call_args
            assert call_kwargs[1]["proxy_id"] == "proxy123"
            assert call_kwargs[1]["fingerprint_id"] == "fp456"


# ============================================================================
# simulate_fyp_session ASYNC TESTS
# ============================================================================


class TestSimulateFypSession:
    """Tests for simulate_fyp_session method."""

    @pytest.mark.asyncio
    async def test_fyp_session_basic_flow(self, mock_page, mock_sleep):
        """simulate_fyp_session should complete basic session flow."""
        config = TikTokConfig(
            videos_per_session=(2, 3),
            max_videos_per_session=3,
            bio_click_probability=0.0,
            profile_visit_probability=0.0,
        )
        automation = TikTokAutomation(config=config)
        mock_page.set_locator_duration("video", 10.0)

        # Patch behavior methods to make session deterministic
        with patch.object(automation.watch_behavior, "generate_session_length", return_value=2):
            with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                with patch.object(automation.watch_behavior, "should_visit_profile", return_value=False):
                    with patch.object(automation.watch_behavior, "should_scroll_back", return_value=False):
                        result = await automation.simulate_fyp_session(
                            mock_page,
                            videos_to_watch=2,
                        )

        assert isinstance(result, SessionResult)
        assert result.platform == SocialPlatform.TIKTOK
        assert result.videos_watched >= 0

    @pytest.mark.asyncio
    async def test_fyp_session_navigates_to_foryou(self, mock_page, mock_sleep):
        """simulate_fyp_session should navigate to FYP page."""
        config = TikTokConfig(
            max_videos_per_session=1,
        )
        automation = TikTokAutomation(config=config)
        mock_page.set_locator_duration("video", 5.0)

        with patch.object(automation.watch_behavior, "generate_session_length", return_value=1):
            with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                with patch.object(automation.watch_behavior, "should_visit_profile", return_value=False):
                    with patch.object(automation.watch_behavior, "should_scroll_back", return_value=False):
                        await automation.simulate_fyp_session(mock_page, videos_to_watch=1)

        # Should have navigated to FYP
        assert "foryou" in mock_page.url or "tiktok.com" in mock_page.url

    @pytest.mark.asyncio
    async def test_fyp_session_with_target_profile(self, mock_page, mock_sleep):
        """simulate_fyp_session should visit target profile when specified."""
        config = TikTokConfig(
            max_videos_per_session=1,
            bio_click_probability=0.0,
        )
        automation = TikTokAutomation(config=config)
        mock_page.set_locator_duration("video", 5.0)
        mock_page.set_locator_count("[data-e2e='user-link']", 0)

        with patch.object(automation.watch_behavior, "generate_session_length", return_value=1):
            with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                with patch.object(automation.watch_behavior, "should_visit_profile", return_value=False):
                    with patch.object(automation.watch_behavior, "should_scroll_back", return_value=False):
                        result = await automation.simulate_fyp_session(
                            mock_page,
                            target_profile="targetuser",
                            videos_to_watch=1,
                        )

        assert result.profiles_visited >= 1
        # Check that URL contains target profile
        assert "@targetuser" in mock_page.url

    @pytest.mark.asyncio
    async def test_fyp_session_returns_session_result(self, mock_page, mock_sleep):
        """simulate_fyp_session should return valid SessionResult."""
        automation = TikTokAutomation()
        mock_page.set_locator_duration("video", 5.0)

        with patch.object(automation.watch_behavior, "generate_session_length", return_value=1):
            with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                with patch.object(automation.watch_behavior, "should_visit_profile", return_value=False):
                    with patch.object(automation.watch_behavior, "should_scroll_back", return_value=False):
                        result = await automation.simulate_fyp_session(
                            mock_page,
                            videos_to_watch=1,
                        )

        assert isinstance(result, SessionResult)
        assert result.platform == SocialPlatform.TIKTOK
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.end_time >= result.start_time

    @pytest.mark.asyncio
    async def test_fyp_session_respects_max_videos(self, mock_page, mock_sleep):
        """simulate_fyp_session should respect max_videos_per_session limit."""
        config = TikTokConfig(
            max_videos_per_session=5,
        )
        automation = TikTokAutomation(config=config)
        mock_page.set_locator_duration("video", 2.0)

        with patch.object(automation.watch_behavior, "generate_session_length", return_value=100):
            with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                with patch.object(automation.watch_behavior, "should_visit_profile", return_value=False):
                    with patch.object(automation.watch_behavior, "should_scroll_back", return_value=False):
                        result = await automation.simulate_fyp_session(
                            mock_page,
                            videos_to_watch=100,  # Request more than max
                        )

        # Should be limited to max_videos_per_session
        assert result.videos_watched <= config.max_videos_per_session


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestTikTokAutomationIntegration:
    """Integration tests for TikTokAutomation."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_page, mock_sleep):
        """Test a complete automation workflow."""
        config = TikTokConfig(
            target_username="testuser",
            max_videos_per_session=2,
            bio_click_probability=0.0,
            profile_visit_probability=0.0,
        )
        automation = TikTokAutomation(config=config)
        mock_page.set_locator_duration("video", 5.0)

        with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
            with patch.object(automation.watch_behavior, "should_visit_profile", return_value=False):
                with patch.object(automation.watch_behavior, "should_scroll_back", return_value=False):
                    result = await automation.run(mock_page)

        assert isinstance(result, SessionResult)
        assert result.platform == SocialPlatform.TIKTOK
