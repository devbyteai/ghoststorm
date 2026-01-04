"""Browser watchdog - monitors browser health and handles crashes."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Coroutine

import structlog

from ghoststorm.core.events.bus import Event
from ghoststorm.core.events.types import EventType
from ghoststorm.core.watchdog.base import BaseWatchdog
from ghoststorm.core.watchdog.models import (
    FailureInfo,
    HealthLevel,
    HealthStatus,
    RecoveryAction,
    RecoveryResult,
    WatchdogConfig,
)

if TYPE_CHECKING:
    from ghoststorm.core.events.bus import AsyncEventBus
    from ghoststorm.core.interfaces.browser import IBrowserEngine

logger = structlog.get_logger(__name__)


class BrowserWatchdog(BaseWatchdog):
    """
    Monitors browser engine health.

    Detects:
    - Browser crashes
    - Browser hangs (no heartbeat)
    - Context creation failures
    - Memory issues

    Recovery actions:
    - Restart browser engine
    - Clear browser data
    - Reduce concurrent contexts
    """

    MONITORS = [
        EventType.BROWSER_LAUNCHING,
        EventType.BROWSER_LAUNCHED,
        EventType.BROWSER_CLOSING,
        EventType.BROWSER_CLOSED,
        EventType.BROWSER_ERROR,
        EventType.ENGINE_ERROR,
        EventType.CONTEXT_CREATED,
        EventType.CONTEXT_CLOSED,
    ]

    EMITS = [
        EventType.ENGINE_ERROR,
    ]

    def __init__(
        self,
        event_bus: AsyncEventBus,
        config: WatchdogConfig,
        browser_engine_getter: Callable[[], IBrowserEngine | None] | None = None,
    ) -> None:
        """
        Initialize browser watchdog.

        Args:
            event_bus: Event bus for communication
            config: Watchdog configuration
            browser_engine_getter: Callable to get current browser engine
        """
        super().__init__(event_bus, config, name="BrowserWatchdog")

        self._browser_engine_getter = browser_engine_getter

        # State tracking
        self._browser_launched = False
        self._launch_time: datetime | None = None
        self._active_contexts = 0
        self._total_contexts_created = 0
        self._last_activity: datetime | None = None
        self._crashes = 0
        self._hangs = 0

        # Restart callback
        self._restart_callback: Callable[[], Coroutine[Any, Any, None]] | None = None

    def set_restart_callback(
        self, callback: Callable[[], Coroutine[Any, Any, None]]
    ) -> None:
        """Set callback for browser restart."""
        self._restart_callback = callback

    async def _handle_event(self, event: Event) -> None:
        """Process browser-related events."""
        self._last_activity = datetime.now()

        match event.type:
            case EventType.BROWSER_LAUNCHING:
                logger.debug("Browser launching", source=event.source)

            case EventType.BROWSER_LAUNCHED:
                self._browser_launched = True
                self._launch_time = datetime.now()
                self._crashes = 0  # Reset crash count on successful launch
                logger.info("Browser launched", source=event.source)

            case EventType.BROWSER_CLOSING:
                logger.debug("Browser closing", source=event.source)

            case EventType.BROWSER_CLOSED:
                if self._browser_launched:
                    # Check if this was unexpected
                    if not event.data.get("expected", False):
                        await self._handle_unexpected_close(event)
                self._browser_launched = False
                self._launch_time = None

            case EventType.BROWSER_ERROR:
                await self._handle_browser_error(event)

            case EventType.ENGINE_ERROR:
                # Check if it's browser-related
                if event.data.get("component") == "browser":
                    await self._handle_browser_error(event)

            case EventType.CONTEXT_CREATED:
                self._active_contexts += 1
                self._total_contexts_created += 1
                logger.debug(
                    "Context created",
                    active=self._active_contexts,
                    total=self._total_contexts_created,
                )

            case EventType.CONTEXT_CLOSED:
                self._active_contexts = max(0, self._active_contexts - 1)
                logger.debug("Context closed", active=self._active_contexts)

    async def _handle_unexpected_close(self, event: Event) -> None:
        """Handle unexpected browser close (crash)."""
        self._crashes += 1

        failure = FailureInfo(
            watchdog_name=self.name,
            failure_type="browser_crash",
            error="Browser closed unexpectedly",
            error_type="BrowserCrash",
            context=event.data,
            severity=HealthLevel.CRITICAL,
            recoverable=True,
            suggested_action=RecoveryAction.RESTART_BROWSER,
        )

        await self.detect_failure(failure)

    async def _handle_browser_error(self, event: Event) -> None:
        """Handle browser error event."""
        error = event.data.get("error", "Unknown error")
        error_type = event.data.get("error_type", "BrowserError")

        # Determine severity based on error type
        severity = HealthLevel.UNHEALTHY
        recoverable = True
        action = RecoveryAction.RESTART_BROWSER

        if "memory" in error.lower():
            severity = HealthLevel.CRITICAL
        elif "timeout" in error.lower():
            self._hangs += 1
            action = RecoveryAction.RESTART_BROWSER
        elif "context" in error.lower():
            severity = HealthLevel.DEGRADED
            action = RecoveryAction.CLEAR_CACHE

        failure = FailureInfo(
            watchdog_name=self.name,
            failure_type="browser_error",
            error=error,
            error_type=error_type,
            context=event.data,
            severity=severity,
            recoverable=recoverable,
            suggested_action=action,
        )

        await self.detect_failure(failure)

    async def check_health(self) -> HealthStatus:
        """Check browser health status."""
        details = {
            "browser_launched": self._browser_launched,
            "active_contexts": self._active_contexts,
            "total_contexts": self._total_contexts_created,
            "crashes": self._crashes,
            "hangs": self._hangs,
        }

        if self._launch_time:
            details["uptime_seconds"] = (
                datetime.now() - self._launch_time
            ).total_seconds()

        # Determine health level
        if not self._browser_launched:
            return HealthStatus(
                level=HealthLevel.UNHEALTHY,
                message="Browser not running",
                details=details,
            )

        if self._crashes >= 3:
            return HealthStatus(
                level=HealthLevel.CRITICAL,
                message=f"Multiple crashes detected ({self._crashes})",
                details=details,
            )

        if self._hangs >= 2:
            return HealthStatus(
                level=HealthLevel.DEGRADED,
                message=f"Browser hangs detected ({self._hangs})",
                details=details,
            )

        # Check for inactivity (potential hang)
        if self._last_activity:
            inactive_seconds = (datetime.now() - self._last_activity).total_seconds()
            if inactive_seconds > self.config.browser_timeout:
                return HealthStatus(
                    level=HealthLevel.DEGRADED,
                    message=f"No activity for {inactive_seconds:.0f}s",
                    details=details,
                )

        return HealthStatus(
            level=HealthLevel.HEALTHY,
            message="Browser running normally",
            details=details,
        )

    async def recover(self, failure: FailureInfo) -> RecoveryResult:
        """Attempt browser recovery."""
        action = failure.suggested_action

        if action == RecoveryAction.RESTART_BROWSER:
            return await self._restart_browser()
        elif action == RecoveryAction.CLEAR_CACHE:
            return await self._clear_cache()
        else:
            return RecoveryResult(
                success=False,
                action_taken=RecoveryAction.NONE,
                message=f"Unknown action: {action}",
            )

    async def _restart_browser(self) -> RecoveryResult:
        """Restart the browser engine."""
        if not self._restart_callback:
            return RecoveryResult(
                success=False,
                action_taken=RecoveryAction.RESTART_BROWSER,
                message="No restart callback configured",
            )

        try:
            logger.info("Attempting browser restart")
            await self._restart_callback()

            # Wait for browser to come back up
            for _ in range(10):
                await asyncio.sleep(1)
                if self._browser_launched:
                    return RecoveryResult(
                        success=True,
                        action_taken=RecoveryAction.RESTART_BROWSER,
                        message="Browser restarted successfully",
                    )

            return RecoveryResult(
                success=False,
                action_taken=RecoveryAction.RESTART_BROWSER,
                message="Browser did not restart in time",
            )

        except Exception as e:
            return RecoveryResult(
                success=False,
                action_taken=RecoveryAction.RESTART_BROWSER,
                message=f"Restart failed: {e}",
            )

    async def _clear_cache(self) -> RecoveryResult:
        """Clear browser cache/data."""
        # This would need browser engine integration
        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.CLEAR_CACHE,
            message="Cache clearing not implemented",
        )
