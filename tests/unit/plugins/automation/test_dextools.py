"""Tests for DEXTools automation plugin.

Tests dataclasses, configuration, behavior selection, and automation methods from
ghoststorm.plugins.automation.dextools
"""

from __future__ import annotations

import asyncio
from collections import Counter
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghoststorm.plugins.automation.dextools import (
    BEHAVIOR_WEIGHTS,
    DEXToolsAction,
    DEXToolsAutomation,
    DEXToolsConfig,
    DEXToolsSelectors,
    VisitResult,
    VisitorBehavior,
)
from ghoststorm.plugins.automation.dextools_campaign import (
    CampaignConfig,
    CampaignResult,
    CampaignStats,
    CampaignStatus,
    DEXToolsTrendingCampaign,
)


# ============================================================================
# DEXToolsConfig DATACLASS TESTS
# ============================================================================


class TestDEXToolsConfig:
    """Tests for DEXToolsConfig dataclass."""

    def test_default_values(self):
        """DEXToolsConfig should have correct default values."""
        config = DEXToolsConfig()

        assert config.pair_url == ""
        assert config.mode == "single"
        assert config.num_visitors == 100
        assert config.duration_hours == 24.0
        assert config.behavior_mode == "realistic"
        assert config.dwell_time_min == 30.0
        assert config.dwell_time_max == 120.0
        assert config.enable_natural_scroll is True
        assert config.enable_chart_hover is True
        assert config.enable_mouse_movement is True
        assert config.enable_social_clicks is True
        assert config.enable_tab_clicks is False
        assert config.enable_favorite is False
        assert config.min_delay == 2.0
        assert config.max_delay == 6.0

    def test_custom_config(self):
        """DEXToolsConfig should accept custom values."""
        config = DEXToolsConfig(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0xtest",
            mode="campaign",
            num_visitors=500,
            duration_hours=12.0,
            behavior_mode="passive",
            dwell_time_min=60.0,
            dwell_time_max=180.0,
            enable_natural_scroll=False,
            enable_social_clicks=False,
        )

        assert config.pair_url == "https://www.dextools.io/app/ether/pair-explorer/0xtest"
        assert config.mode == "campaign"
        assert config.num_visitors == 500
        assert config.duration_hours == 12.0
        assert config.behavior_mode == "passive"
        assert config.dwell_time_min == 60.0
        assert config.dwell_time_max == 180.0
        assert config.enable_natural_scroll is False
        assert config.enable_social_clicks is False

    def test_legacy_settings_backward_compat(self):
        """DEXToolsConfig should support legacy settings."""
        config = DEXToolsConfig(
            click_social_links=True,
            click_chart_tabs=True,
            scroll_page=True,
        )

        assert config.click_social_links is True
        assert config.click_chart_tabs is True
        assert config.scroll_page is True


# ============================================================================
# DEXToolsSelectors DATACLASS TESTS
# ============================================================================


class TestDEXToolsSelectors:
    """Tests for DEXToolsSelectors dataclass."""

    def test_social_link_selectors_exist(self):
        """DEXToolsSelectors should have social link selectors."""
        selectors = DEXToolsSelectors()

        assert "twitter.com" in selectors.social_link_twitter or "x.com" in selectors.social_link_twitter
        assert "t.me" in selectors.social_link_telegram
        assert "discord" in selectors.social_link_discord

    def test_chart_selectors_exist(self):
        """DEXToolsSelectors should have chart-related selectors."""
        selectors = DEXToolsSelectors()

        assert selectors.chart_container is not None
        assert selectors.chart_tabs is not None

    def test_ui_element_selectors_exist(self):
        """DEXToolsSelectors should have UI element selectors."""
        selectors = DEXToolsSelectors()

        assert selectors.tab_buttons is not None
        assert selectors.search_input is not None
        assert selectors.modal_container is not None
        assert selectors.favorite_button is not None

    def test_xpath_fallbacks_exist(self):
        """DEXToolsSelectors should have XPath fallback selectors."""
        selectors = DEXToolsSelectors()

        assert selectors.social_link_1_xpath is not None
        assert selectors.social_link_2_xpath is not None
        assert "xpath" in selectors.social_link_1_xpath.lower() or "//" in selectors.social_link_1_xpath

    def test_custom_selectors(self):
        """DEXToolsSelectors should accept custom values."""
        selectors = DEXToolsSelectors(
            chart_container="div.my-custom-chart",
            social_link_twitter="a.custom-twitter",
        )

        assert selectors.chart_container == "div.my-custom-chart"
        assert selectors.social_link_twitter == "a.custom-twitter"


# ============================================================================
# VisitorBehavior ENUM TESTS
# ============================================================================


class TestVisitorBehavior:
    """Tests for VisitorBehavior enum."""

    def test_all_behaviors_present(self):
        """All expected visitor behaviors should be defined."""
        behaviors = list(VisitorBehavior)
        assert len(behaviors) == 3

        assert VisitorBehavior.PASSIVE in behaviors
        assert VisitorBehavior.LIGHT in behaviors
        assert VisitorBehavior.ENGAGED in behaviors

    def test_behavior_values(self):
        """VisitorBehavior values should be correct."""
        assert VisitorBehavior.PASSIVE.value == "passive"
        assert VisitorBehavior.LIGHT.value == "light"
        assert VisitorBehavior.ENGAGED.value == "engaged"


# ============================================================================
# BEHAVIOR_WEIGHTS TESTS
# ============================================================================


class TestBehaviorWeights:
    """Tests for BEHAVIOR_WEIGHTS distribution."""

    def test_weights_sum_to_100(self):
        """Behavior weights should sum to 100."""
        total = sum(BEHAVIOR_WEIGHTS.values())
        assert total == 100

    def test_correct_distribution(self):
        """Behavior weights should match expected distribution."""
        assert BEHAVIOR_WEIGHTS[VisitorBehavior.PASSIVE] == 60
        assert BEHAVIOR_WEIGHTS[VisitorBehavior.LIGHT] == 30
        assert BEHAVIOR_WEIGHTS[VisitorBehavior.ENGAGED] == 10

    def test_all_behaviors_have_weights(self):
        """All behaviors should have corresponding weights."""
        for behavior in VisitorBehavior:
            assert behavior in BEHAVIOR_WEIGHTS


# ============================================================================
# DEXToolsAction ENUM TESTS
# ============================================================================


class TestDEXToolsAction:
    """Tests for DEXToolsAction enum."""

    def test_all_actions_present(self):
        """All expected DEXTools actions should be defined."""
        actions = list(DEXToolsAction)

        assert DEXToolsAction.CLICK_SOCIAL_TWITTER in actions
        assert DEXToolsAction.CLICK_SOCIAL_TELEGRAM in actions
        assert DEXToolsAction.SCROLL_PAGE in actions
        assert DEXToolsAction.HOVER_CHART in actions
        assert DEXToolsAction.MOUSE_IDLE in actions


# ============================================================================
# DEXToolsAutomation CLASS TESTS
# ============================================================================


class TestDEXToolsAutomationInit:
    """Tests for DEXToolsAutomation initialization."""

    def test_init_without_config(self):
        """DEXToolsAutomation should initialize with default config."""
        automation = DEXToolsAutomation()

        assert automation.config is not None
        assert automation.selectors is not None
        assert automation.config.pair_url == ""
        assert automation.config.behavior_mode == "realistic"

    def test_init_with_config(self):
        """DEXToolsAutomation should accept custom config."""
        config = DEXToolsConfig(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0xtest",
            behavior_mode="passive",
        )
        automation = DEXToolsAutomation(config=config)

        assert automation.config.pair_url == "https://www.dextools.io/app/ether/pair-explorer/0xtest"
        assert automation.config.behavior_mode == "passive"

    def test_init_with_selectors(self):
        """DEXToolsAutomation should accept custom selectors."""
        selectors = DEXToolsSelectors(
            chart_container="div.custom-chart",
        )
        automation = DEXToolsAutomation(selectors=selectors)

        assert automation.selectors.chart_container == "div.custom-chart"

    def test_name_property(self):
        """DEXToolsAutomation name should be 'dextools'."""
        automation = DEXToolsAutomation()
        assert automation.name == "dextools"


# ============================================================================
# _pick_behavior TESTS
# ============================================================================


class TestPickBehavior:
    """Tests for _pick_behavior method."""

    def test_realistic_mode_distribution(self):
        """Realistic mode should produce expected distribution over many calls."""
        config = DEXToolsConfig(behavior_mode="realistic")
        automation = DEXToolsAutomation(config=config)

        # Sample many behaviors
        behaviors = [automation._pick_behavior() for _ in range(1000)]
        counter = Counter(behaviors)

        # Check distribution is approximately correct (within 10%)
        passive_pct = counter[VisitorBehavior.PASSIVE] / 1000
        light_pct = counter[VisitorBehavior.LIGHT] / 1000
        engaged_pct = counter[VisitorBehavior.ENGAGED] / 1000

        assert 0.50 <= passive_pct <= 0.70  # ~60% +/- 10%
        assert 0.20 <= light_pct <= 0.40    # ~30% +/- 10%
        assert 0.05 <= engaged_pct <= 0.20  # ~10% +/- 10%

    def test_forced_passive_mode(self):
        """Passive mode should always return PASSIVE."""
        config = DEXToolsConfig(behavior_mode="passive")
        automation = DEXToolsAutomation(config=config)

        for _ in range(100):
            assert automation._pick_behavior() == VisitorBehavior.PASSIVE

    def test_forced_light_mode(self):
        """Light mode should always return LIGHT."""
        config = DEXToolsConfig(behavior_mode="light")
        automation = DEXToolsAutomation(config=config)

        for _ in range(100):
            assert automation._pick_behavior() == VisitorBehavior.LIGHT

    def test_forced_engaged_mode(self):
        """Engaged mode should always return ENGAGED."""
        config = DEXToolsConfig(behavior_mode="engaged")
        automation = DEXToolsAutomation(config=config)

        for _ in range(100):
            assert automation._pick_behavior() == VisitorBehavior.ENGAGED


# ============================================================================
# _get_dwell_time TESTS
# ============================================================================


class TestGetDwellTime:
    """Tests for _get_dwell_time method."""

    def test_passive_dwell_time(self):
        """Passive behavior should have shortest dwell time."""
        automation = DEXToolsAutomation()
        min_dwell, max_dwell = automation._get_dwell_time(VisitorBehavior.PASSIVE)

        assert min_dwell < max_dwell
        assert min_dwell >= 10.0  # At least 10 seconds
        assert max_dwell <= 60.0  # At most 60 seconds

    def test_light_dwell_time(self):
        """Light behavior should have medium dwell time."""
        automation = DEXToolsAutomation()
        min_dwell, max_dwell = automation._get_dwell_time(VisitorBehavior.LIGHT)

        assert min_dwell < max_dwell
        assert min_dwell >= 20.0

    def test_engaged_dwell_time(self):
        """Engaged behavior should have longest dwell time."""
        automation = DEXToolsAutomation()
        min_dwell, max_dwell = automation._get_dwell_time(VisitorBehavior.ENGAGED)

        assert min_dwell < max_dwell
        assert min_dwell >= 45.0


# ============================================================================
# VisitResult DATACLASS TESTS
# ============================================================================


class TestVisitResult:
    """Tests for VisitResult dataclass."""

    def test_default_values(self):
        """VisitResult should have correct default values."""
        result = VisitResult(
            success=True,
            url="https://test.com",
            behavior=VisitorBehavior.PASSIVE,
            dwell_time_s=30.0,
        )

        assert result.success is True
        assert result.url == "https://test.com"
        assert result.behavior == VisitorBehavior.PASSIVE
        assert result.dwell_time_s == 30.0
        assert result.social_clicks == 0
        assert result.tab_clicks == 0
        assert result.actions_performed == []
        assert result.errors == []

    def test_full_result(self):
        """VisitResult should accept all fields."""
        result = VisitResult(
            success=True,
            url="https://test.com",
            behavior=VisitorBehavior.ENGAGED,
            dwell_time_s=90.0,
            actions_performed=["scroll", "hover_chart", "social_click"],
            social_clicks=2,
            tab_clicks=1,
            errors=[],
        )

        assert result.success is True
        assert result.social_clicks == 2
        assert result.tab_clicks == 1
        assert len(result.actions_performed) == 3


# ============================================================================
# ASYNC METHOD TESTS
# ============================================================================


class TestAsyncMethods:
    """Tests for async automation methods."""

    @pytest.mark.asyncio
    async def test_random_delay(self, mock_sleep):
        """_random_delay should sleep for random duration."""
        automation = DEXToolsAutomation()

        await automation._random_delay(1.0, 2.0)

        mock_sleep.assert_called_once()
        call_args = mock_sleep.call_args[0][0]
        assert 1.0 <= call_args <= 2.0

    @pytest.mark.asyncio
    async def test_micro_delay(self, mock_sleep):
        """_micro_delay should sleep for short duration."""
        automation = DEXToolsAutomation()

        await automation._micro_delay()

        mock_sleep.assert_called_once()
        call_args = mock_sleep.call_args[0][0]
        assert 0.1 <= call_args <= 0.5


class TestBezierPoint:
    """Tests for Bezier curve calculation."""

    def test_bezier_start_point(self):
        """Bezier curve at t=0 should be at start point."""
        automation = DEXToolsAutomation()

        p0 = (0.0, 0.0)
        p1 = (100.0, 100.0)
        p2 = (200.0, 100.0)
        p3 = (300.0, 0.0)

        result = automation._bezier_point(0.0, p0, p1, p2, p3)

        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.0)

    def test_bezier_end_point(self):
        """Bezier curve at t=1 should be at end point."""
        automation = DEXToolsAutomation()

        p0 = (0.0, 0.0)
        p1 = (100.0, 100.0)
        p2 = (200.0, 100.0)
        p3 = (300.0, 0.0)

        result = automation._bezier_point(1.0, p0, p1, p2, p3)

        assert result[0] == pytest.approx(300.0)
        assert result[1] == pytest.approx(0.0)

    def test_bezier_midpoint(self):
        """Bezier curve at t=0.5 should be somewhere in between."""
        automation = DEXToolsAutomation()

        p0 = (0.0, 0.0)
        p1 = (100.0, 100.0)
        p2 = (200.0, 100.0)
        p3 = (300.0, 0.0)

        result = automation._bezier_point(0.5, p0, p1, p2, p3)

        assert 0.0 < result[0] < 300.0
        assert result[1] > 0.0  # Curve should be above the baseline


# ============================================================================
# run_natural_visit TESTS
# ============================================================================


class TestRunNaturalVisit:
    """Tests for run_natural_visit method."""

    @pytest.mark.asyncio
    async def test_run_natural_visit_no_url(self, mock_page, mock_sleep):
        """run_natural_visit should fail if no URL provided."""
        config = DEXToolsConfig(pair_url="")
        automation = DEXToolsAutomation(config=config)

        result = await automation.run_natural_visit(mock_page)

        assert result.success is False
        assert "No URL provided" in result.errors

    @pytest.mark.asyncio
    async def test_run_natural_visit_with_url(self, mock_page, mock_sleep):
        """run_natural_visit should navigate to URL."""
        config = DEXToolsConfig(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0xtest",
            dwell_time_min=1.0,  # Fast for tests
            dwell_time_max=2.0,
        )
        automation = DEXToolsAutomation(config=config)

        result = await automation.run_natural_visit(mock_page)

        assert result.url == config.pair_url
        assert result.behavior in list(VisitorBehavior)
        assert "page_load" in result.actions_performed

    @pytest.mark.asyncio
    async def test_run_natural_visit_scroll_performed(self, mock_page, mock_sleep):
        """run_natural_visit should scroll the page."""
        config = DEXToolsConfig(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0xtest",
            enable_natural_scroll=True,
            dwell_time_min=1.0,
            dwell_time_max=2.0,
        )
        automation = DEXToolsAutomation(config=config)

        result = await automation.run_natural_visit(mock_page)

        assert "scroll" in result.actions_performed


# ============================================================================
# test_selectors TESTS
# ============================================================================


class TestTestSelectors:
    """Tests for test_selectors health check method."""

    @pytest.mark.asyncio
    async def test_selectors_returns_status(self, mock_page, mock_sleep):
        """test_selectors should return status dict."""
        automation = DEXToolsAutomation()

        result = await automation.test_selectors(
            mock_page,
            "https://www.dextools.io/app/ether/pair-explorer/0xtest"
        )

        assert "status" in result
        assert "page_loads" in result
        assert "chart_visible" in result
        assert "social_links_found" in result
        assert "errors" in result


# ============================================================================
# CAMPAIGN CONFIG TESTS
# ============================================================================


class TestCampaignConfig:
    """Tests for CampaignConfig dataclass."""

    def test_default_values(self):
        """CampaignConfig should have correct default values."""
        config = CampaignConfig(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0xtest"
        )

        assert config.pair_url == "https://www.dextools.io/app/ether/pair-explorer/0xtest"
        assert config.num_visitors == 100
        assert config.duration_hours == 24.0
        assert config.max_concurrent == 5
        assert config.distribution_mode == "natural"
        assert config.behavior_mode == "realistic"
        assert config.headless is True

    def test_custom_values(self):
        """CampaignConfig should accept custom values."""
        config = CampaignConfig(
            pair_url="https://test.com",
            num_visitors=500,
            duration_hours=12.0,
            max_concurrent=10,
            distribution_mode="burst",
        )

        assert config.num_visitors == 500
        assert config.duration_hours == 12.0
        assert config.max_concurrent == 10
        assert config.distribution_mode == "burst"


# ============================================================================
# CAMPAIGN STATS TESTS
# ============================================================================


class TestCampaignStats:
    """Tests for CampaignStats dataclass."""

    def test_success_rate_calculation(self):
        """success_rate should calculate correctly."""
        stats = CampaignStats(
            total_visitors=100,
            completed_visitors=80,
            failed_visitors=20,
        )

        assert stats.success_rate == 0.8

    def test_success_rate_no_visitors(self):
        """success_rate should return 0 when no visitors."""
        stats = CampaignStats()

        assert stats.success_rate == 0.0

    def test_avg_dwell_time(self):
        """avg_dwell_time_s should calculate correctly."""
        stats = CampaignStats(
            completed_visitors=10,
            total_dwell_time_s=600.0,
        )

        assert stats.avg_dwell_time_s == 60.0

    def test_to_dict(self):
        """to_dict should return serializable dictionary."""
        stats = CampaignStats(
            total_visitors=100,
            completed_visitors=90,
            failed_visitors=10,
        )

        result = stats.to_dict()

        assert "total_visitors" in result
        assert "success_rate" in result
        assert "behavior_distribution" in result
        assert "engagement" in result


# ============================================================================
# CAMPAIGN STATUS TESTS
# ============================================================================


class TestCampaignStatus:
    """Tests for CampaignStatus enum."""

    def test_all_statuses_present(self):
        """All expected campaign statuses should be defined."""
        statuses = list(CampaignStatus)

        assert CampaignStatus.PENDING in statuses
        assert CampaignStatus.RUNNING in statuses
        assert CampaignStatus.PAUSED in statuses
        assert CampaignStatus.COMPLETED in statuses
        assert CampaignStatus.FAILED in statuses
        assert CampaignStatus.CANCELLED in statuses


# ============================================================================
# DEXToolsTrendingCampaign TESTS
# ============================================================================


class TestDEXToolsTrendingCampaign:
    """Tests for DEXToolsTrendingCampaign class."""

    def test_init(self):
        """Campaign should initialize correctly."""
        config = CampaignConfig(
            pair_url="https://test.com",
            num_visitors=50,
        )
        campaign = DEXToolsTrendingCampaign(config=config)

        assert campaign.status == CampaignStatus.PENDING
        assert campaign.campaign_id is not None
        assert len(campaign.campaign_id) == 8

    def test_get_stats(self):
        """get_stats should return CampaignStats."""
        config = CampaignConfig(pair_url="https://test.com")
        campaign = DEXToolsTrendingCampaign(config=config)

        stats = campaign.get_stats()

        assert isinstance(stats, CampaignStats)
        assert stats.total_visitors == 100

    def test_get_result(self):
        """get_result should return CampaignResult."""
        config = CampaignConfig(pair_url="https://test.com")
        campaign = DEXToolsTrendingCampaign(config=config)

        result = campaign.get_result()

        assert isinstance(result, CampaignResult)
        assert result.status == CampaignStatus.PENDING
        assert result.campaign_id == campaign.campaign_id

    def test_create_visit_schedule_even(self):
        """Even distribution should space visits evenly."""
        config = CampaignConfig(
            pair_url="https://test.com",
            num_visitors=10,
            duration_hours=1.0,
            distribution_mode="even",
        )
        campaign = DEXToolsTrendingCampaign(config=config)

        schedule = campaign._create_visit_schedule()

        assert len(schedule) == 10
        # All delays should be non-negative
        for visitor_id, delay in schedule:
            assert delay >= 0

    def test_create_visit_schedule_natural(self):
        """Natural distribution should create varied schedule."""
        config = CampaignConfig(
            pair_url="https://test.com",
            num_visitors=10,
            duration_hours=1.0,
            distribution_mode="natural",
        )
        campaign = DEXToolsTrendingCampaign(config=config)

        schedule = campaign._create_visit_schedule()

        assert len(schedule) == 10

    def test_create_visit_schedule_burst(self):
        """Burst distribution should cluster visits."""
        config = CampaignConfig(
            pair_url="https://test.com",
            num_visitors=20,
            duration_hours=1.0,
            distribution_mode="burst",
        )
        campaign = DEXToolsTrendingCampaign(config=config)

        schedule = campaign._create_visit_schedule()

        assert len(schedule) == 20


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestDEXToolsIntegration:
    """Integration tests for DEXTools automation."""

    @pytest.mark.asyncio
    async def test_full_visit_workflow(self, mock_page, mock_sleep):
        """Test a complete visit workflow."""
        config = DEXToolsConfig(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0xtest",
            behavior_mode="passive",  # Simplest flow
            dwell_time_min=1.0,
            dwell_time_max=2.0,
            enable_social_clicks=False,  # Disable to simplify
            enable_tab_clicks=False,
        )
        automation = DEXToolsAutomation(config=config)

        result = await automation.run_natural_visit(mock_page)

        assert result.success is True
        assert result.behavior == VisitorBehavior.PASSIVE
        assert result.dwell_time_s > 0

    @pytest.mark.asyncio
    async def test_legacy_run_method(self, mock_page, mock_sleep):
        """Legacy run method should still work."""
        config = DEXToolsConfig(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0xtest",
        )
        automation = DEXToolsAutomation(config=config)

        result = await automation.run(mock_page)

        assert isinstance(result, dict)
        assert "success" in result
