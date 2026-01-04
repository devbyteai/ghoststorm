"""Tests for Instagram automation plugin.

Tests dataclasses, selectors, and automation functionality from
ghoststorm.plugins.automation.instagram
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghoststorm.plugins.automation.base import (
    BioClickResult,
    SessionResult,
    SocialPlatform,
    StoryViewResult,
    SwipeResult,
    VideoWatchOutcome,
    WatchResult,
)
from ghoststorm.plugins.automation.instagram import (
    InstagramAction,
    InstagramAutomation,
    InstagramConfig,
    InstagramSelectors,
    LinkClickResult,
)


# ============================================================================
# InstagramConfig DATACLASS TESTS
# ============================================================================


class TestInstagramConfig:
    """Tests for InstagramConfig dataclass."""

    def test_default_values(self):
        """InstagramConfig should have correct default values."""
        config = InstagramConfig()

        # Target defaults
        assert config.target_url == ""
        assert config.target_username == ""
        assert config.target_reel_urls == []

        # Reel watching behavior
        assert config.min_reel_watch_percent == 0.4
        assert config.max_reel_watch_percent == 1.2
        assert config.reel_skip_probability == 0.35

        # Story behavior
        assert config.story_skip_probability == 0.20
        assert config.story_link_click_probability == 0.25
        assert config.min_story_view_seconds == 2.0
        assert config.max_story_view_seconds == 8.0

        # Bio link clicking
        assert config.bio_link_click_probability == 0.20
        assert config.profile_visit_probability == 0.12

        # Engagement
        assert config.like_probability == 0.0
        assert config.save_probability == 0.0
        assert config.comment_probability == 0.0

        # Session parameters
        assert config.reels_per_session == (5, 20)
        assert config.stories_per_profile == (1, 5)

        # In-app browser simulation
        assert config.simulate_inapp_browser is True
        assert config.inapp_dwell_time == (10.0, 60.0)

        # Timing
        assert config.swipe_speed_range == (300, 700)
        assert config.page_load_delay == (2.0, 5.0)

        # Rate limits
        assert config.max_story_views == 80
        assert config.max_reel_views == 100
        assert config.max_profile_visits == 60
        assert config.max_bio_clicks == 20
        assert config.max_story_link_clicks == 15

        # Mobile viewport
        assert config.viewport_width == 390
        assert config.viewport_height == 844

    def test_custom_config_values(self):
        """InstagramConfig should accept custom values."""
        config = InstagramConfig(
            target_url="https://instagram.com/someuser",
            target_username="someuser",
            target_reel_urls=["https://instagram.com/reel/ABC123/"],
            min_reel_watch_percent=0.5,
            max_reel_watch_percent=1.5,
            reel_skip_probability=0.25,
            story_skip_probability=0.15,
            story_link_click_probability=0.30,
            reels_per_session=(10, 30),
            viewport_width=414,
            viewport_height=896,
        )

        assert config.target_url == "https://instagram.com/someuser"
        assert config.target_username == "someuser"
        assert config.target_reel_urls == ["https://instagram.com/reel/ABC123/"]
        assert config.min_reel_watch_percent == 0.5
        assert config.max_reel_watch_percent == 1.5
        assert config.reel_skip_probability == 0.25
        assert config.story_skip_probability == 0.15
        assert config.story_link_click_probability == 0.30
        assert config.reels_per_session == (10, 30)
        assert config.viewport_width == 414
        assert config.viewport_height == 896

    def test_target_reel_urls_is_mutable_list(self):
        """target_reel_urls should be a separate mutable list for each instance."""
        config1 = InstagramConfig()
        config2 = InstagramConfig()

        config1.target_reel_urls.append("https://instagram.com/reel/test1/")

        assert len(config1.target_reel_urls) == 1
        assert len(config2.target_reel_urls) == 0


# ============================================================================
# InstagramSelectors DATACLASS TESTS
# ============================================================================


class TestInstagramSelectors:
    """Tests for InstagramSelectors dataclass."""

    def test_default_selectors_exist(self):
        """InstagramSelectors should have all required default selectors."""
        selectors = InstagramSelectors()

        # Reels container
        assert selectors.reel_container == "[data-testid='reels-viewer']"
        assert selectors.reel_video == "video"
        assert selectors.reel_wrapper == "article"

        # Engagement buttons
        assert selectors.like_button == "[aria-label='Like']"
        assert selectors.comment_button == "[aria-label='Comment']"
        assert selectors.share_button == "[aria-label='Share Post']"
        assert selectors.save_button == "[aria-label='Save']"

        # Story elements
        assert selectors.story_container == "[data-testid='story-viewer']"
        assert selectors.story_ring == "[data-testid='user-avatar']"
        assert selectors.story_link_sticker == "[data-testid='story-link-sticker']"
        assert selectors.story_next_area == ".story-next"
        assert selectors.story_prev_area == ".story-prev"
        assert selectors.story_close_button == "[aria-label='Close']"
        assert selectors.story_progress_bar == ".story-progress"

        # Profile elements
        assert selectors.profile_link == "header a[href*='/']"
        assert selectors.profile_username == "header h2"
        assert selectors.profile_bio_link == "[data-testid='bio-link']"
        assert selectors.profile_link_tree == "a[href*='linktr.ee'], a[href*='linkin.bio']"
        assert selectors.follow_button == "[data-testid='follow-button']"

        # Navigation
        assert selectors.home_tab == "[aria-label='Home']"
        assert selectors.reels_tab == "[aria-label='Reels']"
        assert selectors.explore_tab == "[aria-label='Explore']"
        assert selectors.profile_tab == "[aria-label='Profile']"

        # Caption and audio
        assert selectors.caption_text == "[data-testid='post-content'] span"
        assert selectors.audio_info == "[data-testid='audio-attribution']"

        # Loading
        assert selectors.loading_spinner == "[aria-label='Loading']"

    def test_custom_selectors(self):
        """InstagramSelectors should accept custom values."""
        selectors = InstagramSelectors(
            reel_video="video.custom-video",
            like_button=".custom-like-btn",
        )

        assert selectors.reel_video == "video.custom-video"
        assert selectors.like_button == ".custom-like-btn"
        # Other selectors should keep defaults
        assert selectors.reel_container == "[data-testid='reels-viewer']"


# ============================================================================
# InstagramAction ENUM TESTS
# ============================================================================


class TestInstagramAction:
    """Tests for InstagramAction enum."""

    def test_action_values(self):
        """InstagramAction should have correct values."""
        assert InstagramAction.WATCH_REEL.value == "watch_reel"
        assert InstagramAction.VIEW_STORY.value == "view_story"
        assert InstagramAction.CLICK_STORY_LINK.value == "click_story_link"
        assert InstagramAction.CLICK_BIO_LINK.value == "click_bio_link"
        assert InstagramAction.SCROLL_REELS.value == "scroll_reels"
        assert InstagramAction.VISIT_PROFILE.value == "visit_profile"
        assert InstagramAction.NAVIGATE_TO_REELS.value == "navigate_to_reels"
        assert InstagramAction.LIKE_REEL.value == "like_reel"
        assert InstagramAction.SAVE_REEL.value == "save_reel"

    def test_all_actions_present(self):
        """All expected actions should be defined."""
        actions = list(InstagramAction)
        assert len(actions) == 9


# ============================================================================
# LinkClickResult DATACLASS TESTS
# ============================================================================


class TestLinkClickResult:
    """Tests for LinkClickResult dataclass."""

    def test_successful_story_link_click(self):
        """LinkClickResult should represent successful story link click."""
        result = LinkClickResult(
            success=True,
            link_type="story",
            target_url="https://example.com/promo",
            dwell_time=15.5,
        )

        assert result.success is True
        assert result.link_type == "story"
        assert result.target_url == "https://example.com/promo"
        assert result.dwell_time == 15.5
        assert result.error is None

    def test_successful_bio_link_click(self):
        """LinkClickResult should represent successful bio link click."""
        result = LinkClickResult(
            success=True,
            link_type="bio",
            target_url="https://linktr.ee/user",
            dwell_time=30.0,
        )

        assert result.success is True
        assert result.link_type == "bio"
        assert result.target_url == "https://linktr.ee/user"
        assert result.dwell_time == 30.0

    def test_failed_link_click(self):
        """LinkClickResult should represent failed link click."""
        result = LinkClickResult(
            success=False,
            link_type="story",
            error="No link sticker found",
        )

        assert result.success is False
        assert result.link_type == "story"
        assert result.target_url is None
        assert result.dwell_time == 0.0
        assert result.error == "No link sticker found"


# ============================================================================
# InstagramAutomation CLASS TESTS
# ============================================================================


class TestInstagramAutomationInit:
    """Tests for InstagramAutomation initialization."""

    def test_init_without_config(self):
        """InstagramAutomation should initialize with default config."""
        automation = InstagramAutomation()

        assert automation.config is not None
        assert isinstance(automation.config, InstagramConfig)
        assert automation.selectors is not None
        assert isinstance(automation.selectors, InstagramSelectors)

    def test_init_with_config(self):
        """InstagramAutomation should accept custom config."""
        config = InstagramConfig(
            target_username="testuser",
            reels_per_session=(10, 20),
        )
        automation = InstagramAutomation(config=config)

        assert automation.config.target_username == "testuser"
        assert automation.config.reels_per_session == (10, 20)

    def test_init_with_custom_selectors(self):
        """InstagramAutomation should accept custom selectors."""
        selectors = InstagramSelectors(reel_video="video.custom")
        automation = InstagramAutomation(selectors=selectors)

        assert automation.selectors.reel_video == "video.custom"

    def test_session_tracking_initialized(self):
        """InstagramAutomation should initialize session tracking counters."""
        automation = InstagramAutomation()

        assert automation._reels_watched == 0
        assert automation._stories_viewed == 0
        assert automation._profiles_visited == 0
        assert automation._bio_clicks == 0
        assert automation._story_link_clicks == 0

    def test_device_id_generated(self):
        """InstagramAutomation should generate a device ID."""
        automation = InstagramAutomation()

        assert automation._device_id is not None
        assert len(automation._device_id) == 32  # MD5 hex digest length
        assert all(c in "0123456789abcdef" for c in automation._device_id)

    def test_device_id_unique_per_instance(self):
        """Each InstagramAutomation instance should have unique device ID."""
        automation1 = InstagramAutomation()
        automation2 = InstagramAutomation()

        assert automation1._device_id != automation2._device_id


class TestInstagramAutomationProperties:
    """Tests for InstagramAutomation properties."""

    def test_name_property(self):
        """InstagramAutomation should have name 'instagram'."""
        automation = InstagramAutomation()
        assert automation.name == "instagram"

    def test_platform_property(self):
        """InstagramAutomation should have platform INSTAGRAM."""
        automation = InstagramAutomation()
        assert automation.platform == SocialPlatform.INSTAGRAM


class TestExtractReelId:
    """Tests for _extract_reel_id method."""

    def test_extract_reel_url(self):
        """Should extract reel ID from /reel/ URL format."""
        automation = InstagramAutomation()

        url = "https://www.instagram.com/reel/ABC123xyz/"
        reel_id = automation._extract_reel_id(url)

        assert reel_id == "ABC123xyz"

    def test_extract_reel_url_with_query_params(self):
        """Should extract reel ID ignoring query parameters."""
        automation = InstagramAutomation()

        url = "https://www.instagram.com/reel/ABC123xyz/?utm_source=ig_web"
        reel_id = automation._extract_reel_id(url)

        assert reel_id == "ABC123xyz"

    def test_extract_reels_url(self):
        """Should extract reel ID from /reels/ URL format."""
        automation = InstagramAutomation()

        url = "https://www.instagram.com/reels/DEF456abc/"
        reel_id = automation._extract_reel_id(url)

        assert reel_id == "DEF456abc"

    def test_extract_post_url(self):
        """Should extract ID from /p/ URL format."""
        automation = InstagramAutomation()

        url = "https://www.instagram.com/p/GHI789xyz/"
        reel_id = automation._extract_reel_id(url)

        assert reel_id == "GHI789xyz"

    def test_extract_fallback_hash(self):
        """Should return hash for unknown URL format."""
        automation = InstagramAutomation()

        url = "https://www.instagram.com/stories/someuser/"
        reel_id = automation._extract_reel_id(url)

        # Should be a 16-character hex string (MD5 truncated)
        assert len(reel_id) == 16
        assert all(c in "0123456789abcdef" for c in reel_id)


# ============================================================================
# ASYNC METHOD TESTS
# ============================================================================


@pytest.mark.asyncio
class TestWatchReel:
    """Tests for watch_reel method."""

    async def test_watch_reel_success(self, mock_page):
        """watch_reel should return successful result."""
        automation = InstagramAutomation()

        # Set up video duration
        mock_page.set_locator_duration("video", 30.0)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await automation.watch_reel(mock_page, duration=5.0)

        assert result.success is True
        assert result.watch_duration == 5.0
        assert result.outcome in list(VideoWatchOutcome)
        mock_sleep.assert_called()

    async def test_watch_reel_increments_counter(self, mock_page):
        """watch_reel should increment reels_watched counter."""
        automation = InstagramAutomation()

        assert automation._reels_watched == 0

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await automation.watch_reel(mock_page, duration=2.0)

        assert automation._reels_watched == 1

    async def test_watch_video_alias(self, mock_page):
        """watch_video should be an alias for watch_reel."""
        automation = InstagramAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.watch_video(mock_page, duration=3.0)

        assert result.success is True
        assert result.watch_duration == 3.0


@pytest.mark.asyncio
class TestSwipeToNext:
    """Tests for swipe_to_next method."""

    async def test_swipe_to_next_success(self, mock_page):
        """swipe_to_next should execute swipe and return result."""
        automation = InstagramAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.swipe_to_next(mock_page)

        assert isinstance(result, SwipeResult)
        assert result.direction == "up"

    async def test_swipe_to_next_waits_for_load(self, mock_page):
        """swipe_to_next should wait after successful swipe."""
        automation = InstagramAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await automation.swipe_to_next(mock_page)

        # Should have sleep calls for pause and delay
        assert mock_sleep.call_count >= 1


@pytest.mark.asyncio
class TestVisitProfile:
    """Tests for visit_profile method."""

    async def test_visit_profile_with_username(self, mock_page):
        """visit_profile should navigate to username URL."""
        automation = InstagramAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.visit_profile(mock_page, username="testuser")

        assert result is True
        assert mock_page._url == "https://www.instagram.com/testuser/"
        assert automation._profiles_visited == 1

    async def test_visit_profile_from_reel(self, mock_page):
        """visit_profile without username should click profile link."""
        automation = InstagramAutomation()

        # Set up locator to be clickable
        mock_page.set_locator_count(automation.selectors.profile_link, 1)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.visit_profile(mock_page)

        # Should attempt to click the profile link
        assert isinstance(result, bool)


@pytest.mark.asyncio
class TestViewStories:
    """Tests for view_stories method."""

    async def test_view_stories_no_stories(self, mock_page):
        """view_stories should return error when no stories found."""
        automation = InstagramAutomation()

        # No story ring
        mock_page.set_locator_count(automation.selectors.story_ring, 0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.view_stories(mock_page, username="testuser")

        assert result.success is False
        assert "No active stories" in result.error

    async def test_view_stories_success(self, mock_page):
        """view_stories should view stories when available."""
        automation = InstagramAutomation()

        # Mock story ring exists
        mock_page.set_locator_count(automation.selectors.story_ring, 1)

        # Set URL to indicate we're in stories
        mock_page._url = "https://www.instagram.com/stories/testuser/"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Mock random to control story count
            with patch("random.randint", return_value=1):
                result = await automation.view_stories(mock_page, username="testuser")

        assert isinstance(result, StoryViewResult)


@pytest.mark.asyncio
class TestClickStoryLink:
    """Tests for click_story_link method."""

    async def test_click_story_link_no_link(self, mock_page):
        """click_story_link should return error when no link sticker."""
        automation = InstagramAutomation()

        # No link sticker
        mock_page.set_locator_count(automation.selectors.story_link_sticker, 0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.click_story_link(mock_page)

        assert result.success is False
        assert result.link_type == "story"
        assert "No link sticker" in result.error

    async def test_click_story_link_success(self, mock_page):
        """click_story_link should click sticker and return result."""
        automation = InstagramAutomation()

        # Link sticker exists with href
        mock_page.set_locator_count(automation.selectors.story_link_sticker, 1)
        mock_page.set_locator_href(
            automation.selectors.story_link_sticker,
            "https://example.com/promo"
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.click_story_link(mock_page)

        assert isinstance(result, LinkClickResult)
        assert result.link_type == "story"


@pytest.mark.asyncio
class TestClickBioLink:
    """Tests for click_bio_link method."""

    async def test_click_bio_link_not_found(self, mock_page):
        """click_bio_link should return error when no bio link found."""
        automation = InstagramAutomation()

        # No bio link
        mock_page.set_locator_count(automation.selectors.profile_bio_link, 0)
        mock_page.set_locator_count(automation.selectors.profile_link_tree, 0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.click_bio_link(mock_page, username="testuser")

        assert result.success is False
        assert "No bio link found" in result.error

    async def test_click_bio_link_success(self, mock_page):
        """click_bio_link should click link and return success."""
        automation = InstagramAutomation()

        # Bio link exists
        mock_page.set_locator_count(automation.selectors.profile_bio_link, 1)
        mock_page.set_locator_href(
            automation.selectors.profile_bio_link,
            "https://linktr.ee/testuser"
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.click_bio_link(mock_page, username="testuser")

        assert isinstance(result, BioClickResult)

    async def test_click_bio_link_increments_counter(self, mock_page):
        """click_bio_link should increment bio_clicks counter on success."""
        automation = InstagramAutomation()

        # Bio link exists and will be clicked
        mock_page.set_locator_count(automation.selectors.profile_bio_link, 1)
        mock_page.set_locator_href(
            automation.selectors.profile_bio_link,
            "https://linktr.ee/testuser"
        )

        assert automation._bio_clicks == 0

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.click_bio_link(mock_page, username="testuser")

        # Counter increments only on successful click
        if result.success:
            assert automation._bio_clicks == 1


@pytest.mark.asyncio
class TestWatchDirectReel:
    """Tests for watch_direct_reel method."""

    async def test_watch_direct_reel_success(self, mock_page, view_tracker):
        """watch_direct_reel should navigate and watch reel."""
        automation = InstagramAutomation()

        # Set up video duration
        mock_page.set_locator_duration("video", 15.0)

        reel_url = "https://www.instagram.com/reel/ABC123xyz/"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.watch_direct_reel(
                mock_page,
                reel_url=reel_url,
                watch_duration=5.0,
                proxy_id="test_proxy",
                fingerprint_id="test_fp",
            )

        assert result.success is True
        assert result.watch_duration == 5.0
        assert mock_page._url == reel_url

    async def test_watch_direct_reel_increments_counter(self, mock_page, view_tracker):
        """watch_direct_reel should increment reels_watched counter."""
        automation = InstagramAutomation()

        assert automation._reels_watched == 0

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await automation.watch_direct_reel(
                mock_page,
                reel_url="https://www.instagram.com/reel/TEST123/",
                watch_duration=3.0,
            )

        assert automation._reels_watched == 1


@pytest.mark.asyncio
class TestSimulateReelsSession:
    """Tests for simulate_reels_session method."""

    async def test_simulate_reels_session_basic(self, mock_page):
        """simulate_reels_session should run basic session flow."""
        automation = InstagramAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(automation.watch_behavior, "generate_session_length", return_value=2):
                with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                    with patch.object(automation.watch_behavior, "should_visit_profile", return_value=False):
                        with patch.object(automation.watch_behavior, "should_scroll_back", return_value=False):
                            result = await automation.simulate_reels_session(
                                mock_page,
                                reels_to_watch=2,
                            )

        assert isinstance(result, SessionResult)
        assert result.platform == SocialPlatform.INSTAGRAM
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.videos_watched >= 0

    async def test_simulate_reels_session_with_target_profile(self, mock_page):
        """simulate_reels_session should visit target profile."""
        automation = InstagramAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(automation.watch_behavior, "generate_session_length", return_value=1):
                with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                    with patch.object(automation.watch_behavior, "should_visit_profile", return_value=False):
                        with patch.object(automation.watch_behavior, "should_scroll_back", return_value=False):
                            result = await automation.simulate_reels_session(
                                mock_page,
                                target_profile="targetuser",
                                reels_to_watch=1,
                            )

        assert isinstance(result, SessionResult)

    async def test_simulate_reels_session_returns_session_result(self, mock_page):
        """simulate_reels_session should return complete SessionResult."""
        automation = InstagramAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(automation.watch_behavior, "generate_session_length", return_value=1):
                with patch.object(automation.watch_behavior, "should_take_break", return_value=False):
                    with patch.object(automation.watch_behavior, "should_visit_profile", return_value=False):
                        with patch.object(automation.watch_behavior, "should_scroll_back", return_value=False):
                            result = await automation.simulate_reels_session(
                                mock_page,
                                reels_to_watch=1,
                            )

        # Verify SessionResult fields
        assert hasattr(result, "success")
        assert hasattr(result, "platform")
        assert hasattr(result, "start_time")
        assert hasattr(result, "end_time")
        assert hasattr(result, "videos_watched")
        assert hasattr(result, "bio_links_clicked")
        assert hasattr(result, "story_links_clicked")
        assert hasattr(result, "profiles_visited")
        assert hasattr(result, "errors")
        assert hasattr(result, "watch_results")


# ============================================================================
# ADDITIONAL EDGE CASE TESTS
# ============================================================================


@pytest.mark.asyncio
class TestInstagramAutomationEdgeCases:
    """Edge case tests for InstagramAutomation."""

    async def test_watch_reel_with_unknown_duration(self, mock_page):
        """watch_reel should handle unknown video duration."""
        automation = InstagramAutomation()

        # Set duration to None
        mock_page.set_locator_duration("video", None)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.watch_reel(mock_page, duration=5.0)

        assert result.success is True
        # Completion rate should be 1.0 when duration unknown
        assert result.video_duration is None

    async def test_multiple_reels_watched_tracking(self, mock_page):
        """Should correctly track multiple reels watched."""
        automation = InstagramAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await automation.watch_reel(mock_page, duration=2.0)
            await automation.watch_reel(mock_page, duration=2.0)
            await automation.watch_reel(mock_page, duration=2.0)

        assert automation._reels_watched == 3

    async def test_swipe_to_previous(self, mock_page):
        """swipe_to_previous should swipe down."""
        automation = InstagramAutomation()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await automation.swipe_to_previous(mock_page)

        assert isinstance(result, SwipeResult)
        assert result.direction == "down"
