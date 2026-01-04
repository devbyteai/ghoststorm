"""Network watchdog - monitors proxy and network health."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

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
    from ghoststorm.core.events.bus import AsyncEventBus, Event

logger = structlog.get_logger(__name__)


class NetworkWatchdog(BaseWatchdog):
    """
    Monitors network and proxy health.

    Detects:
    - Proxy failures
    - Rate limiting
    - Connection timeouts
    - Request failures

    Recovery actions:
    - Rotate to new proxy
    - Implement backoff
    - Skip exhausted proxies
    """

    MONITORS = [
        EventType.PROXY_ASSIGNED,
        EventType.PROXY_SUCCESS,
        EventType.PROXY_FAILED,
        EventType.PROXY_ROTATED,
        EventType.PROXY_EXHAUSTED,
        EventType.PROXY_HEALTH_CHECK,
        EventType.RATE_LIMITED,
        EventType.REQUEST_STARTED,
        EventType.REQUEST_COMPLETED,
        EventType.REQUEST_FAILED,
        EventType.REQUEST_BLOCKED,
    ]

    EMITS = [
        EventType.ENGINE_ERROR,
    ]

    def __init__(
        self,
        event_bus: AsyncEventBus,
        config: WatchdogConfig,
    ) -> None:
        """Initialize network watchdog."""
        super().__init__(event_bus, config, name="NetworkWatchdog")

        # Proxy tracking
        self._active_proxies: set[str] = set()
        self._failed_proxies: set[str] = set()
        self._proxy_success_count: dict[str, int] = defaultdict(int)
        self._proxy_failure_count: dict[str, int] = defaultdict(int)

        # Request tracking
        self._pending_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._timeouts = 0

        # Rate limiting
        self._rate_limit_events = 0
        self._last_rate_limit: datetime | None = None
        self._backoff_until: datetime | None = None

        # General state
        self._last_activity: datetime | None = None

    async def _handle_event(self, event: Event) -> None:
        """Process network-related events."""
        self._last_activity = datetime.now()

        match event.type:
            case EventType.PROXY_ASSIGNED:
                proxy_id = event.data.get("proxy_id", "")
                if proxy_id:
                    self._active_proxies.add(proxy_id)
                logger.debug("Proxy assigned", proxy_id=proxy_id)

            case EventType.PROXY_SUCCESS:
                proxy_id = event.data.get("proxy_id", "")
                if proxy_id:
                    self._proxy_success_count[proxy_id] += 1
                logger.debug("Proxy success", proxy_id=proxy_id)

            case EventType.PROXY_FAILED:
                await self._handle_proxy_failure(event)

            case EventType.PROXY_ROTATED:
                old_proxy = event.data.get("old_proxy_id", "")
                new_proxy = event.data.get("new_proxy_id", "")
                if old_proxy in self._active_proxies:
                    self._active_proxies.remove(old_proxy)
                if new_proxy:
                    self._active_proxies.add(new_proxy)
                logger.debug("Proxy rotated", old=old_proxy, new=new_proxy)

            case EventType.PROXY_EXHAUSTED:
                await self._handle_proxy_exhausted(event)

            case EventType.PROXY_HEALTH_CHECK:
                # Track health check results
                healthy = event.data.get("healthy", True)
                proxy_id = event.data.get("proxy_id", "")
                if not healthy and proxy_id:
                    self._failed_proxies.add(proxy_id)

            case EventType.RATE_LIMITED:
                await self._handle_rate_limit(event)

            case EventType.REQUEST_STARTED:
                self._pending_requests += 1

            case EventType.REQUEST_COMPLETED:
                self._pending_requests = max(0, self._pending_requests - 1)
                self._successful_requests += 1

            case EventType.REQUEST_FAILED:
                await self._handle_request_failure(event)

            case EventType.REQUEST_BLOCKED:
                await self._handle_request_blocked(event)

    async def _handle_proxy_failure(self, event: Event) -> None:
        """Handle proxy failure event."""
        proxy_id = event.data.get("proxy_id", "")
        error = event.data.get("error", "Proxy failed")

        if proxy_id:
            self._proxy_failure_count[proxy_id] += 1
            self._failed_proxies.add(proxy_id)

            # Remove from active if too many failures
            if self._proxy_failure_count[proxy_id] >= 3:
                self._active_proxies.discard(proxy_id)

        failure = FailureInfo(
            watchdog_name=self.name,
            failure_type="proxy_failure",
            error=error,
            context={"proxy_id": proxy_id},
            severity=HealthLevel.DEGRADED,
            recoverable=True,
            suggested_action=RecoveryAction.ROTATE_PROXY,
        )

        await self.detect_failure(failure)

    async def _handle_proxy_exhausted(self, event: Event) -> None:
        """Handle proxy pool exhaustion."""
        failure = FailureInfo(
            watchdog_name=self.name,
            failure_type="proxy_exhausted",
            error="All proxies exhausted",
            context=event.data,
            severity=HealthLevel.CRITICAL,
            recoverable=False,
            suggested_action=RecoveryAction.BACKOFF,
        )

        await self.detect_failure(failure)

    async def _handle_rate_limit(self, event: Event) -> None:
        """Handle rate limiting event."""
        self._rate_limit_events += 1
        self._last_rate_limit = datetime.now()

        # Set backoff period
        backoff_seconds = event.data.get("retry_after", 60)
        self._backoff_until = datetime.now()

        failure = FailureInfo(
            watchdog_name=self.name,
            failure_type="rate_limited",
            error=f"Rate limited, backoff {backoff_seconds}s",
            context=event.data,
            severity=HealthLevel.DEGRADED,
            recoverable=True,
            suggested_action=RecoveryAction.BACKOFF,
        )

        await self.detect_failure(failure)

    async def _handle_request_failure(self, event: Event) -> None:
        """Handle request failure event."""
        self._pending_requests = max(0, self._pending_requests - 1)
        self._failed_requests += 1

        error = event.data.get("error", "Request failed")

        if "timeout" in error.lower():
            self._timeouts += 1

        # Only track if failure rate is high
        total = self._successful_requests + self._failed_requests
        if total > 10 and (self._failed_requests / total) > 0.5:
            failure = FailureInfo(
                watchdog_name=self.name,
                failure_type="high_failure_rate",
                error=f"Request failure rate: {self._failed_requests}/{total}",
                context=event.data,
                severity=HealthLevel.DEGRADED,
                recoverable=True,
                suggested_action=RecoveryAction.ROTATE_PROXY,
            )
            await self.detect_failure(failure)

    async def _handle_request_blocked(self, event: Event) -> None:
        """Handle blocked request."""
        failure = FailureInfo(
            watchdog_name=self.name,
            failure_type="request_blocked",
            error="Request blocked",
            context=event.data,
            severity=HealthLevel.UNHEALTHY,
            recoverable=True,
            suggested_action=RecoveryAction.ROTATE_PROXY,
        )

        await self.detect_failure(failure)

    async def check_health(self) -> HealthStatus:
        """Check network health status."""
        total_requests = self._successful_requests + self._failed_requests
        success_rate = self._successful_requests / total_requests if total_requests > 0 else 1.0

        details = {
            "active_proxies": len(self._active_proxies),
            "failed_proxies": len(self._failed_proxies),
            "pending_requests": self._pending_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "timeouts": self._timeouts,
            "success_rate": success_rate,
            "rate_limit_events": self._rate_limit_events,
        }

        # Check if in backoff
        if self._backoff_until and datetime.now() < self._backoff_until:
            remaining = (self._backoff_until - datetime.now()).total_seconds()
            return HealthStatus(
                level=HealthLevel.DEGRADED,
                message=f"In backoff for {remaining:.0f}s more",
                details=details,
            )

        # Check proxy health
        if len(self._active_proxies) == 0 and len(self._failed_proxies) > 0:
            return HealthStatus(
                level=HealthLevel.CRITICAL,
                message="No healthy proxies available",
                details=details,
            )

        if success_rate < 0.3:
            return HealthStatus(
                level=HealthLevel.CRITICAL,
                message=f"Very low request success rate: {success_rate:.1%}",
                details=details,
            )

        if success_rate < 0.7:
            return HealthStatus(
                level=HealthLevel.DEGRADED,
                message=f"Low request success rate: {success_rate:.1%}",
                details=details,
            )

        if self._rate_limit_events > 5:
            return HealthStatus(
                level=HealthLevel.DEGRADED,
                message=f"Frequent rate limiting ({self._rate_limit_events} events)",
                details=details,
            )

        return HealthStatus(
            level=HealthLevel.HEALTHY,
            message=f"Network healthy ({success_rate:.1%} success)",
            details=details,
        )

    async def recover(self, failure: FailureInfo) -> RecoveryResult:
        """Attempt network recovery."""
        action = failure.suggested_action

        match action:
            case RecoveryAction.ROTATE_PROXY:
                # Emit proxy rotation request
                await self.event_bus.emit(
                    EventType.PROXY_FAILED,
                    {"rotate_requested": True},
                    source=self.name,
                )
                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.ROTATE_PROXY,
                    message="Proxy rotation requested",
                )

            case RecoveryAction.BACKOFF:
                # Just wait
                backoff_time = 30
                logger.info("Implementing backoff", seconds=backoff_time)
                await asyncio.sleep(backoff_time)
                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.BACKOFF,
                    message=f"Backed off for {backoff_time}s",
                )

            case _:
                return RecoveryResult(
                    success=False,
                    action_taken=RecoveryAction.NONE,
                    message=f"No handler for action: {action}",
                )

    def get_proxy_stats(self, proxy_id: str) -> dict:
        """Get statistics for a specific proxy."""
        return {
            "proxy_id": proxy_id,
            "success_count": self._proxy_success_count.get(proxy_id, 0),
            "failure_count": self._proxy_failure_count.get(proxy_id, 0),
            "is_active": proxy_id in self._active_proxies,
            "is_failed": proxy_id in self._failed_proxies,
        }
