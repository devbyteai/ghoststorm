"""Referrer injection plugin for realistic traffic simulation.

Integrates with the orchestrator to set referrer headers before page load
based on the configured traffic source distribution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from ghoststorm.plugins.referrer.distribution import ReferrerDistribution

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = structlog.get_logger(__name__)


class ReferrerPlugin:
    """Plugin that injects referrer headers based on traffic distribution.

    Hooks into the orchestrator's before_page_load event to set realistic
    referrer headers that match configured traffic source distribution.
    """

    name = "referrer"

    def __init__(self) -> None:
        """Initialize the referrer plugin."""
        self._distribution: ReferrerDistribution | None = None
        self._enabled: bool = True

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the plugin from behavior config.

        Args:
            config: Behavior configuration containing referrer settings
        """
        referrer_config = config.get("referrer", {})

        # Check if referrer mode is "none" (disabled)
        if referrer_config.get("mode") == "none":
            self._enabled = False
            self._distribution = None
            logger.info("Referrer plugin disabled (mode=none)")
            return

        self._enabled = True
        self._distribution = ReferrerDistribution.from_config(referrer_config)
        logger.info(
            "Referrer plugin configured",
            mode=referrer_config.get("mode", "realistic"),
            preset=referrer_config.get("preset", "realistic"),
        )

    async def before_page_load(
        self,
        page: Page,
        url: str,
        **kwargs: Any,
    ) -> None:
        """Set referrer header before page navigation.

        Args:
            page: Playwright page instance
            url: Target URL being loaded
            **kwargs: Additional hook arguments
        """
        if not self._enabled or not self._distribution:
            return

        # Get referrer from distribution
        referrer = self._distribution.get_referrer(url)

        if referrer:
            # Set referrer via extra HTTP headers
            await page.set_extra_http_headers({"Referer": referrer})
            logger.debug("Referrer set", referrer=referrer[:80], target=url[:50])
        else:
            # Clear any existing referrer (direct traffic)
            await page.set_extra_http_headers({"Referer": ""})
            logger.debug("Direct traffic (no referrer)", target=url[:50])

    def get_stats(self) -> dict[str, Any]:
        """Get referrer distribution statistics.

        Returns:
            Statistics dictionary with counts and percentages
        """
        if not self._distribution:
            return {"enabled": False}

        stats = self._distribution.get_stats()
        stats["enabled"] = self._enabled
        return stats

    def reset_stats(self) -> None:
        """Reset distribution statistics."""
        if self._distribution:
            self._distribution.reset_stats()


# Global plugin instance
_plugin_instance: ReferrerPlugin | None = None


def get_referrer_plugin() -> ReferrerPlugin:
    """Get or create the global referrer plugin instance.

    Returns:
        ReferrerPlugin singleton instance
    """
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = ReferrerPlugin()
    return _plugin_instance
