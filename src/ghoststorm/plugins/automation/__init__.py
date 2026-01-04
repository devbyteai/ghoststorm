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
from ghoststorm.plugins.automation.dextools import DEXToolsAutomation
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
    # DEXTools
    "DEXToolsAutomation",
    # Base classes
    "SocialMediaAutomation",
    "SocialPlatform",
    "WatchResult",
    "SwipeResult",
    "BioClickResult",
    "StoryViewResult",
    "SessionResult",
    "VideoWatchOutcome",
    # TikTok
    "TikTokAutomation",
    "TikTokConfig",
    "TikTokSelectors",
    "TikTokAction",
    # Instagram
    "InstagramAutomation",
    "InstagramConfig",
    "InstagramSelectors",
    "InstagramAction",
    # YouTube
    "YouTubeAutomation",
    "YouTubeConfig",
    "YouTubeSelectors",
    "YouTubeAction",
    # Behavior
    "VideoWatchBehavior",
    "StoryWatchBehavior",
    "InAppBrowserBehavior",
    "UserInterest",
    # View Tracking
    "ViewTrackingManager",
    "get_view_tracker",
    "reset_view_tracker",
    "PLATFORM_REQUIREMENTS",
    # Zefoy
    "ZefoyAutomation",
    "ZefoyConfig",
    "ZefoyResult",
    "check_zefoy_services",
]
