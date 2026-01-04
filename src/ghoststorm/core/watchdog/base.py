"""Base watchdog class for monitoring and recovery."""

from __future__ import annotations

import asyncio
import contextlib
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

from ghoststorm.core.events.types import EventType
from ghoststorm.core.watchdog.models import (
    FailureInfo,
    HealthLevel,
    HealthStatus,
    RecoveryAction,
    RecoveryResult,
    WatchdogConfig,
    WatchdogState,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ghoststorm.core.events.bus import AsyncEventBus, Event

logger = structlog.get_logger(__name__)


class BaseWatchdog(ABC):
    """
    Base class for all watchdogs.

    Watchdogs monitor system components via events and can trigger
    recovery actions when failures are detected.

    Subclasses must:
    1. Define MONITORS - list of EventTypes to listen for
    2. Define EMITS - list of EventTypes this watchdog can emit
    3. Implement _handle_event() - process monitored events
    4. Implement check_health() - return current health status
    """

    # Events this watchdog listens to
    MONITORS: list[EventType] = []

    # Events this watchdog can emit
    EMITS: list[EventType] = []

    def __init__(
        self,
        event_bus: AsyncEventBus,
        config: WatchdogConfig,
        name: str | None = None,
    ) -> None:
        """
        Initialize the watchdog.

        Args:
            event_bus: Event bus for subscribing and publishing
            config: Watchdog configuration
            name: Optional custom name (defaults to class name)
        """
        self.event_bus = event_bus
        self.config = config
        self.name = name or self.__class__.__name__

        # State tracking
        self._state = WatchdogState(name=self.name)
        self._unsubscribers: list[Callable[[], None]] = []
        self._health_check_task: asyncio.Task[None] | None = None
        self._recovery_lock = asyncio.Lock()
        self._consecutive_failures = 0
        self._last_recovery: datetime | None = None

        # Alert callback
        self._alert_callback: Callable[[Any], None] | None = None

    @property
    def state(self) -> WatchdogState:
        """Get current watchdog state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if watchdog is running."""
        return self._state.running

    async def start(self) -> None:
        """Start the watchdog and subscribe to events."""
        if self._state.running:
            logger.warning("Watchdog already running", name=self.name)
            return

        if not self.config.enabled:
            logger.info("Watchdog disabled", name=self.name)
            return

        # Subscribe to monitored events
        for event_type in self.MONITORS:
            unsubscribe = self.event_bus.subscribe(event_type, self._on_event)
            self._unsubscribers.append(unsubscribe)

        # Start periodic health checks
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        self._state.running = True
        self._state.enabled = True

        logger.info(
            "Watchdog started",
            name=self.name,
            monitors=[e.value for e in self.MONITORS],
        )

    async def stop(self) -> None:
        """Stop the watchdog and unsubscribe from events."""
        if not self._state.running:
            return

        # Stop health check loop
        if self._health_check_task:
            self._health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_check_task
            self._health_check_task = None

        # Unsubscribe from events
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

        self._state.running = False
        logger.info("Watchdog stopped", name=self.name)

    def set_alert_callback(self, callback: Callable[[Any], None]) -> None:
        """Set callback for alerts."""
        self._alert_callback = callback

    async def _on_event(self, event: Event) -> None:
        """Handle incoming events."""
        self._state.total_events += 1

        try:
            await self._handle_event(event)
        except Exception as e:
            logger.exception(
                "Error handling event in watchdog",
                watchdog=self.name,
                event_type=event.type.value,
                error=str(e),
            )

    @abstractmethod
    async def _handle_event(self, event: Event) -> None:
        """
        Process a monitored event.

        Subclasses implement this to detect failures and trigger recovery.

        Args:
            event: The event to process
        """
        pass

    @abstractmethod
    async def check_health(self) -> HealthStatus:
        """
        Check the current health of the monitored component.

        Returns:
            HealthStatus indicating current health
        """
        pass

    async def recover(self, failure: FailureInfo) -> RecoveryResult:
        """
        Attempt to recover from a failure.

        Default implementation just logs. Subclasses should override
        for specific recovery logic.

        Args:
            failure: Information about the failure

        Returns:
            RecoveryResult indicating outcome
        """
        logger.info(
            "Recovery not implemented",
            watchdog=self.name,
            failure=failure.failure_type,
        )
        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.NONE,
            message="No recovery action implemented",
        )

    async def detect_failure(self, failure: FailureInfo) -> None:
        """
        Handle a detected failure.

        Tracks the failure, optionally triggers recovery,
        and emits alerts as needed.

        Args:
            failure: Information about the detected failure
        """
        self._state.failures_detected += 1
        self._consecutive_failures += 1

        logger.warning(
            "Failure detected",
            watchdog=self.name,
            failure_type=failure.failure_type,
            error=failure.error,
            consecutive=self._consecutive_failures,
        )

        # Update health status
        self._state.health = HealthStatus(
            level=failure.severity,
            message=f"Failure: {failure.failure_type}",
            details={"error": failure.error, "context": failure.context},
        )

        # Check if we should attempt recovery
        if self.config.auto_recovery and failure.recoverable:
            await self._attempt_recovery(failure)

        # Check if we should send an alert
        if self._consecutive_failures >= self.config.alert_threshold:
            await self._send_alert(failure)

    async def _attempt_recovery(self, failure: FailureInfo) -> None:
        """Attempt recovery with rate limiting."""
        async with self._recovery_lock:
            # Check cooldown
            if self._last_recovery:
                elapsed = (datetime.now() - self._last_recovery).total_seconds()
                if elapsed < self.config.recovery_cooldown:
                    logger.debug(
                        "Recovery cooldown active",
                        watchdog=self.name,
                        remaining=self.config.recovery_cooldown - elapsed,
                    )
                    return

            # Check max attempts
            if self._state.recoveries_attempted >= self.config.max_recovery_attempts:
                logger.warning(
                    "Max recovery attempts reached",
                    watchdog=self.name,
                    attempts=self._state.recoveries_attempted,
                )
                return

            # Attempt recovery
            self._state.recoveries_attempted += 1
            self._last_recovery = datetime.now()

            start_time = time.time()

            try:
                result = await self.recover(failure)
                result.duration_ms = (time.time() - start_time) * 1000

                if result.success:
                    self._state.recoveries_successful += 1
                    self._consecutive_failures = 0
                    logger.info(
                        "Recovery successful",
                        watchdog=self.name,
                        action=result.action_taken.value,
                        duration_ms=result.duration_ms,
                    )
                else:
                    logger.warning(
                        "Recovery failed",
                        watchdog=self.name,
                        action=result.action_taken.value,
                        message=result.message,
                    )

            except Exception as e:
                logger.exception(
                    "Recovery raised exception",
                    watchdog=self.name,
                    error=str(e),
                )

    async def _send_alert(self, failure: FailureInfo) -> None:
        """Send an alert notification."""
        from ghoststorm.core.watchdog.models import WatchdogAlert

        alert = WatchdogAlert(
            watchdog_name=self.name,
            level=failure.severity,
            title=f"[{self.name}] {failure.failure_type}",
            message=failure.error,
            failure=failure,
        )

        # Emit to event bus
        await self.event_bus.emit(
            EventType.ENGINE_ERROR,
            {
                "watchdog": self.name,
                "alert": alert.to_dict(),
            },
            source=self.name,
        )

        # Call callback if set
        if self._alert_callback:
            try:
                self._alert_callback(alert)
            except Exception as e:
                logger.exception("Alert callback failed", error=str(e))

        logger.error(
            "Watchdog alert",
            watchdog=self.name,
            level=failure.severity.value,
            message=failure.error,
        )

    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while self._state.running:
            try:
                await asyncio.sleep(self.config.health_check_interval)

                health = await self.check_health()
                self._state.health = health
                self._state.last_check = datetime.now()

                if health.is_healthy:
                    self._state.health.checks_passed += 1
                else:
                    self._state.health.checks_failed += 1

                logger.debug(
                    "Health check complete",
                    watchdog=self.name,
                    level=health.level.value,
                    score=health.score,
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(
                    "Health check failed",
                    watchdog=self.name,
                    error=str(e),
                )
                self._state.health = HealthStatus(
                    level=HealthLevel.UNKNOWN,
                    message=f"Health check error: {e}",
                )
