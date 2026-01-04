"""Automation plugins for specific platforms."""

from ghoststorm.plugins.automation.base import (
    BioClickResult,
    SessionResult,
    SocialMediaAutomation,
    SocialPlatform,
    StoryViewResult,
    SwipeResult,
    VideoWatchOutcome,
    WatchResult,
)
from ghoststorm.plugins.automation.dextools import (
    BEHAVIOR_WEIGHTS,
    DEXToolsAction,
    DEXToolsAutomation,
    DEXToolsConfig,
    DEXToolsSelectors,
    VisitorBehavior,
    VisitResult,
)
from ghoststorm.plugins.automation.dextools_campaign import (
    CampaignConfig,
    CampaignResult,
    CampaignStats,
    CampaignStatus,
    DEXToolsTrendingCampaign,
    run_dextools_campaign,
)
from ghoststorm.plugins.automation.instagram import (
    InstagramAction,
    InstagramAutomation,
    InstagramConfig,
    InstagramSelectors,
)
from ghoststorm.plugins.automation.social_media_behavior import (
    InAppBrowserBehavior,
    StoryWatchBehavior,
    UserInterest,
    VideoWatchBehavior,
)
from ghoststorm.plugins.automation.tiktok import (
    TikTokAction,
    TikTokAutomation,
    TikTokConfig,
    TikTokSelectors,
)
from ghoststorm.plugins.automation.view_tracking import (
    PLATFORM_REQUIREMENTS,
    ViewTrackingManager,
    get_view_tracker,
    reset_view_tracker,
)
from ghoststorm.plugins.automation.youtube import (
    YouTubeAction,
    YouTubeAutomation,
    YouTubeConfig,
    YouTubeSelectors,
)
from ghoststorm.plugins.automation.zefoy import (
    ZefoyAutomation,
    ZefoyConfig,
    ZefoyResult,
    check_zefoy_services,
)

__all__ = [
    "BEHAVIOR_WEIGHTS",
    "PLATFORM_REQUIREMENTS",
    "BioClickResult",
    "CampaignConfig",
    "CampaignResult",
    "CampaignStats",
    "CampaignStatus",
    "DEXToolsAction",
    # DEXTools
    "DEXToolsAutomation",
    "DEXToolsConfig",
    "DEXToolsSelectors",
    # DEXTools Campaign
    "DEXToolsTrendingCampaign",
    "InAppBrowserBehavior",
    "InstagramAction",
    # Instagram
    "InstagramAutomation",
    "InstagramConfig",
    "InstagramSelectors",
    "SessionResult",
    # Base classes
    "SocialMediaAutomation",
    "SocialPlatform",
    "StoryViewResult",
    "StoryWatchBehavior",
    "SwipeResult",
    "TikTokAction",
    # TikTok
    "TikTokAutomation",
    "TikTokConfig",
    "TikTokSelectors",
    "UserInterest",
    # Behavior
    "VideoWatchBehavior",
    "VideoWatchOutcome",
    # View Tracking
    "ViewTrackingManager",
    "VisitResult",
    "VisitorBehavior",
    "WatchResult",
    "YouTubeAction",
    # YouTube
    "YouTubeAutomation",
    "YouTubeConfig",
    "YouTubeSelectors",
    # Zefoy
    "ZefoyAutomation",
    "ZefoyConfig",
    "ZefoyResult",
    "check_zefoy_services",
    "get_view_tracker",
    "reset_view_tracker",
    "run_dextools_campaign",
]
