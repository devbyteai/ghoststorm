"""View Tracking System for Social Media Automation.

Tracks views to avoid detection patterns by monitoring:
- Minimum watch times required per platform
- Unique IP/fingerprint per view requirements
- Cooldown periods between repeated views
- Maximum views per video per hour limits

This helps maintain organic-looking behavior patterns and ensures
views actually count on each platform.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ViewRequirements:
    """Platform-specific requirements for views to count."""

    platform: Literal["tiktok", "instagram", "youtube", "youtube_shorts"]
    min_watch_seconds: float
    requires_unique_ip: bool = True
    requires_unique_fingerprint: bool = True
    cooldown_between_views: float = 300.0  # 5 min default
    max_views_per_video_per_hour: int = 3


# Platform-specific view counting requirements
PLATFORM_REQUIREMENTS = {
    "tiktok": ViewRequirements(
        platform="tiktok",
        min_watch_seconds=3.0,
        cooldown_between_views=300.0,  # 5 min
        max_views_per_video_per_hour=5,
    ),
    "instagram": ViewRequirements(
        platform="instagram",
        min_watch_seconds=3.0,
        cooldown_between_views=600.0,  # 10 min
        max_views_per_video_per_hour=3,
    ),
    "youtube": ViewRequirements(
        platform="youtube",
        min_watch_seconds=30.0,  # YouTube requires longer watch for view
        cooldown_between_views=3600.0,  # 1 hour
        max_views_per_video_per_hour=2,
    ),
    "youtube_shorts": ViewRequirements(
        platform="youtube_shorts",
        min_watch_seconds=3.0,  # Shorts are shorter
        cooldown_between_views=300.0,
        max_views_per_video_per_hour=5,
    ),
}


@dataclass
class ViewRecord:
    """Record of a single view."""

    video_id: str
    platform: str
    proxy_id: str
    fingerprint_id: str
    timestamp: float
    watch_duration: float
    counted: bool = False


@dataclass
class ViewTrackingManager:
    """Tracks views to avoid detection patterns.

    Maintains records of views to:
    - Prevent viewing same video too frequently
    - Ensure unique IP/fingerprint combinations
    - Track minimum watch times
    - Monitor view counts per video
    """

    # Internal storage - view records keyed by video_id
    _records: dict[str, list[ViewRecord]] = field(default_factory=dict)
    _cleanup_interval: float = 3600.0  # Clean old records every hour
    _last_cleanup: float = field(default_factory=time.time)

    def can_view(
        self,
        video_id: str,
        platform: Literal["tiktok", "instagram", "youtube", "youtube_shorts"],
        proxy_id: str,
        fingerprint_id: str,
    ) -> tuple[bool, str]:
        """Check if a view can be made without detection risk.

        Args:
            video_id: Unique identifier for the video
            platform: Target platform
            proxy_id: Current proxy identifier
            fingerprint_id: Current fingerprint identifier

        Returns:
            Tuple of (can_view, reason_if_not)
        """
        self._maybe_cleanup()

        requirements = PLATFORM_REQUIREMENTS.get(platform)
        if not requirements:
            logger.warning(
                "[VIEW_TRACK] Unknown platform, allowing view",
                platform=platform,
                video_id=video_id[:20] + "..." if len(video_id) > 20 else video_id,
            )
            return True, ""

        # Get records for this video
        records = self._records.get(video_id, [])
        if not records:
            logger.debug(
                "[VIEW_TRACK] No prior views, allowing",
                platform=platform,
                video_id=video_id[:20] + "..." if len(video_id) > 20 else video_id,
            )
            return True, ""

        now = time.time()
        hour_ago = now - 3600

        # Check views in last hour
        recent_views = [r for r in records if r.timestamp > hour_ago]
        if len(recent_views) >= requirements.max_views_per_video_per_hour:
            reason = f"Max {requirements.max_views_per_video_per_hour} views/hour exceeded"
            logger.info(
                "[VIEW_TRACK] Rate limit exceeded",
                platform=platform,
                video_id=video_id[:20] + "...",
                recent_views=len(recent_views),
                max_allowed=requirements.max_views_per_video_per_hour,
            )
            return False, reason

        # Check cooldown from last view
        if records:
            last_view = max(records, key=lambda r: r.timestamp)
            time_since_last = now - last_view.timestamp
            if time_since_last < requirements.cooldown_between_views:
                wait_time = requirements.cooldown_between_views - time_since_last
                reason = f"Cooldown active, wait {wait_time:.0f}s"
                logger.info(
                    "[VIEW_TRACK] Cooldown active",
                    platform=platform,
                    video_id=video_id[:20] + "...",
                    seconds_remaining=round(wait_time, 0),
                    cooldown_period=requirements.cooldown_between_views,
                )
                return False, reason

        # Check for duplicate IP/fingerprint combo
        if requirements.requires_unique_ip or requirements.requires_unique_fingerprint:
            for record in recent_views:
                ip_match = record.proxy_id == proxy_id
                fp_match = record.fingerprint_id == fingerprint_id

                if requirements.requires_unique_ip and ip_match:
                    reason = "IP already used for this video recently"
                    logger.info(
                        "[VIEW_TRACK] Duplicate IP detected",
                        platform=platform,
                        video_id=video_id[:20] + "...",
                        proxy_id=proxy_id[:8] + "...",
                    )
                    return False, reason

                if requirements.requires_unique_fingerprint and fp_match:
                    reason = "Fingerprint already used for this video recently"
                    logger.info(
                        "[VIEW_TRACK] Duplicate fingerprint detected",
                        platform=platform,
                        video_id=video_id[:20] + "...",
                        fingerprint_id=fingerprint_id[:8] + "...",
                    )
                    return False, reason

        logger.debug(
            "[VIEW_TRACK] View allowed",
            platform=platform,
            video_id=video_id[:20] + "...",
            prior_views=len(records),
            recent_views=len(recent_views),
        )
        return True, ""

    def record_view(
        self,
        video_id: str,
        platform: Literal["tiktok", "instagram", "youtube", "youtube_shorts"],
        proxy_id: str,
        fingerprint_id: str,
        watch_duration: float,
    ) -> bool:
        """Record a completed view.

        Args:
            video_id: Unique identifier for the video
            platform: Target platform
            proxy_id: Proxy identifier used
            fingerprint_id: Fingerprint identifier used
            watch_duration: How long the video was watched

        Returns:
            True if view likely counted (met minimum watch time)
        """
        requirements = PLATFORM_REQUIREMENTS.get(platform)
        min_watch = requirements.min_watch_seconds if requirements else 3.0

        counted = watch_duration >= min_watch

        record = ViewRecord(
            video_id=video_id,
            platform=platform,
            proxy_id=proxy_id,
            fingerprint_id=fingerprint_id,
            timestamp=time.time(),
            watch_duration=watch_duration,
            counted=counted,
        )

        if video_id not in self._records:
            self._records[video_id] = []
        self._records[video_id].append(record)

        logger.info(
            "[VIEW_TRACK] View recorded",
            platform=platform,
            video_id=video_id[:20] + "..." if len(video_id) > 20 else video_id,
            watch_duration_s=round(watch_duration, 2),
            min_required_s=min_watch,
            counted=counted,
            total_views=len(self._records[video_id]),
        )

        return counted

    def get_minimum_watch_time(
        self,
        platform: Literal["tiktok", "instagram", "youtube", "youtube_shorts"],
    ) -> float:
        """Get minimum watch time for view to count.

        Args:
            platform: Target platform

        Returns:
            Minimum watch time in seconds
        """
        requirements = PLATFORM_REQUIREMENTS.get(platform)
        return requirements.min_watch_seconds if requirements else 3.0

    def get_view_stats(self, video_id: str) -> dict:
        """Get statistics for views on a video.

        Args:
            video_id: Video identifier

        Returns:
            Dictionary with view statistics
        """
        records = self._records.get(video_id, [])
        now = time.time()
        hour_ago = now - 3600

        recent = [r for r in records if r.timestamp > hour_ago]
        counted = [r for r in records if r.counted]

        stats = {
            "total_views": len(records),
            "views_last_hour": len(recent),
            "counted_views": len(counted),
            "unique_ips": len(set(r.proxy_id for r in records)),
            "unique_fingerprints": len(set(r.fingerprint_id for r in records)),
            "avg_watch_time": sum(r.watch_duration for r in records) / len(records) if records else 0,
        }

        logger.debug(
            "[VIEW_TRACK] View stats retrieved",
            video_id=video_id[:20] + "..." if len(video_id) > 20 else video_id,
            **stats,
        )

        return stats

    def _maybe_cleanup(self) -> None:
        """Clean up old records if enough time has passed."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = now - 86400  # Keep 24 hours of records

        cleaned = 0
        for video_id in list(self._records.keys()):
            original_count = len(self._records[video_id])
            self._records[video_id] = [
                r for r in self._records[video_id] if r.timestamp > cutoff
            ]
            cleaned += original_count - len(self._records[video_id])

            # Remove empty entries
            if not self._records[video_id]:
                del self._records[video_id]

        self._last_cleanup = now

        if cleaned > 0:
            logger.info(
                "[VIEW_TRACK] Cleaned old records",
                records_removed=cleaned,
                videos_tracked=len(self._records),
            )


# Global view tracking manager instance
_view_tracker: ViewTrackingManager | None = None


def get_view_tracker() -> ViewTrackingManager:
    """Get the global view tracking manager."""
    global _view_tracker
    if _view_tracker is None:
        _view_tracker = ViewTrackingManager()
        logger.info("[VIEW_TRACK] Initialized global view tracking manager")
    return _view_tracker


def reset_view_tracker() -> None:
    """Reset the global view tracking manager (for testing)."""
    global _view_tracker
    _view_tracker = None
