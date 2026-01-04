"""Watchdog manager - orchestrates all watchdogs."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

from ghoststorm.core.watchdog.models import (
    HealthLevel,
    HealthStatus,
    WatchdogConfig,
    WatchdogState,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ghoststorm.core.events.bus import AsyncEventBus
    from ghoststorm.core.watchdog.base import BaseWatchdog

logger = structlog.get_logger(__name__)


class WatchdogManager:
    """
    Manages all watchdogs in the system.

    Responsibilities:
    - Register and unregister watchdogs
    - Start/stop all watchdogs together
    - Aggregate health status from all watchdogs
    - Provide unified alert handling
    """

    def __init__(
        self,
        event_bus: AsyncEventBus,
        config: WatchdogConfig | None = None,
    ) -> None:
        """
        Initialize the watchdog manager.

        Args:
            event_bus: Event bus for watchdog communication
            config: Optional shared config (watchdogs can override)
        """
        self.event_bus = event_bus
        self.config = config or WatchdogConfig()

        self._watchdogs: dict[str, BaseWatchdog] = {}
        self._running = False
        self._started_at: datetime | None = None
        self._alert_handlers: list[Callable[[Any], None]] = []

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running

    @property
    def watchdog_count(self) -> int:
        """Get number of registered watchdogs."""
        return len(self._watchdogs)

    def register(self, watchdog: BaseWatchdog) -> None:
        """
        Register a watchdog.

        Args:
            watchdog: Watchdog instance to register

        Raises:
            ValueError: If watchdog with same name already registered
        """
        if watchdog.name in self._watchdogs:
            raise ValueError(f"Watchdog already registered: {watchdog.name}")

        self._watchdogs[watchdog.name] = watchdog

        # Set up alert forwarding
        watchdog.set_alert_callback(self._forward_alert)

        logger.info("Watchdog registered", name=watchdog.name)

    def unregister(self, name: str) -> bool:
        """
        Unregister a watchdog by name.

        Args:
            name: Name of watchdog to unregister

        Returns:
            True if watchdog was found and removed
        """
        if name in self._watchdogs:
            del self._watchdogs[name]
            logger.info("Watchdog unregistered", name=name)
            return True
        return False

    def get(self, name: str) -> BaseWatchdog | None:
        """
        Get a watchdog by name.

        Args:
            name: Name of watchdog to get

        Returns:
            Watchdog instance or None if not found
        """
        return self._watchdogs.get(name)

    def add_alert_handler(self, handler: Callable[[Any], None]) -> None:
        """
        Add a handler for watchdog alerts.

        Args:
            handler: Callback function for alerts
        """
        self._alert_handlers.append(handler)

    def remove_alert_handler(self, handler: Callable[[Any], None]) -> None:
        """Remove an alert handler."""
        if handler in self._alert_handlers:
            self._alert_handlers.remove(handler)

    async def start(self) -> None:
        """Start all registered watchdogs."""
        if self._running:
            logger.warning("WatchdogManager already running")
            return

        if not self.config.enabled:
            logger.info("WatchdogManager disabled in config")
            return

        logger.info("Starting WatchdogManager", count=len(self._watchdogs))

        # Start all watchdogs concurrently
        start_tasks = []
        for watchdog in self._watchdogs.values():
            start_tasks.append(asyncio.create_task(watchdog.start()))

        await asyncio.gather(*start_tasks, return_exceptions=True)

        self._running = True
        self._started_at = datetime.now()

        logger.info(
            "WatchdogManager started",
            watchdogs=[w.name for w in self._watchdogs.values() if w.is_running],
        )

    async def stop(self) -> None:
        """Stop all watchdogs."""
        if not self._running:
            return

        logger.info("Stopping WatchdogManager")

        # Stop all watchdogs concurrently
        stop_tasks = []
        for watchdog in self._watchdogs.values():
            stop_tasks.append(asyncio.create_task(watchdog.stop()))

        await asyncio.gather(*stop_tasks, return_exceptions=True)

        self._running = False
        logger.info("WatchdogManager stopped")

    async def check_health(self) -> HealthStatus:
        """
        Aggregate health status from all watchdogs.

        Returns:
            Combined HealthStatus
        """
        if not self._watchdogs:
            return HealthStatus(
                level=HealthLevel.HEALTHY,
                message="No watchdogs registered",
            )

        # Collect all health statuses
        health_checks = []
        for watchdog in self._watchdogs.values():
            try:
                health = await asyncio.wait_for(
                    watchdog.check_health(),
                    timeout=5.0,
                )
                health_checks.append((watchdog.name, health))
            except TimeoutError:
                health_checks.append(
                    (
                        watchdog.name,
                        HealthStatus(
                            level=HealthLevel.UNKNOWN,
                            message="Health check timed out",
                        ),
                    )
                )
            except Exception as e:
                health_checks.append(
                    (
                        watchdog.name,
                        HealthStatus(
                            level=HealthLevel.UNKNOWN,
                            message=f"Health check failed: {e}",
                        ),
                    )
                )

        # Determine overall level
        levels = [h.level for _, h in health_checks]
        overall_level = self._aggregate_levels(levels)

        # Build summary
        unhealthy = [name for name, h in health_checks if not h.is_healthy]
        checks_passed = sum(1 for _, h in health_checks if h.is_healthy)
        checks_failed = len(health_checks) - checks_passed

        if unhealthy:
            message = f"Unhealthy watchdogs: {', '.join(unhealthy)}"
        else:
            message = "All watchdogs healthy"

        return HealthStatus(
            level=overall_level,
            message=message,
            details={
                "watchdogs": {name: h.to_dict() for name, h in health_checks},
                "total": len(health_checks),
                "unhealthy": unhealthy,
            },
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    def _aggregate_levels(self, levels: list[HealthLevel]) -> HealthLevel:
        """
        Aggregate multiple health levels into one.

        Uses worst-case logic.
        """
        if not levels:
            return HealthLevel.HEALTHY

        # Priority order (worst first)
        priority = [
            HealthLevel.CRITICAL,
            HealthLevel.UNHEALTHY,
            HealthLevel.DEGRADED,
            HealthLevel.UNKNOWN,
            HealthLevel.HEALTHY,
        ]

        for level in priority:
            if level in levels:
                return level

        return HealthLevel.UNKNOWN

    def _forward_alert(self, alert: Any) -> None:
        """Forward alert to all registered handlers."""
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.exception("Alert handler failed", error=str(e))

    def get_states(self) -> dict[str, WatchdogState]:
        """Get state of all watchdogs."""
        return {name: w.state for name, w in self._watchdogs.items()}

    def get_stats(self) -> dict[str, Any]:
        """Get aggregated statistics."""
        total_events = sum(w.state.total_events for w in self._watchdogs.values())
        total_failures = sum(w.state.failures_detected for w in self._watchdogs.values())
        total_recoveries = sum(w.state.recoveries_attempted for w in self._watchdogs.values())
        successful_recoveries = sum(w.state.recoveries_successful for w in self._watchdogs.values())

        return {
            "running": self._running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "watchdog_count": len(self._watchdogs),
            "active_watchdogs": sum(1 for w in self._watchdogs.values() if w.is_running),
            "total_events_processed": total_events,
            "total_failures_detected": total_failures,
            "total_recoveries_attempted": total_recoveries,
            "successful_recoveries": successful_recoveries,
            "recovery_success_rate": (
                successful_recoveries / total_recoveries if total_recoveries > 0 else 1.0
            ),
            "watchdogs": {name: w.state.to_dict() for name, w in self._watchdogs.items()},
        }
