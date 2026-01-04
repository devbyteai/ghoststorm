"""Page watchdog - monitors page load failures and navigation errors."""

from __future__ import annotations

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


class PageWatchdog(BaseWatchdog):
    """
    Monitors page load and navigation health.

    Detects:
    - Page load failures
    - Navigation timeouts
    - JavaScript errors
    - Empty/blank pages

    Recovery actions:
    - Retry page navigation
    - Skip problematic URL
    - Report blocked domain
    """

    MONITORS = [
        EventType.PAGE_CREATED,
        EventType.PAGE_NAVIGATING,
        EventType.PAGE_LOADED,
        EventType.PAGE_ERROR,
        EventType.PAGE_CLOSED,
        EventType.TASK_FAILED,
        EventType.BLOCKED,
    ]

    EMITS = [
        EventType.ENGINE_ERROR,
    ]

    def __init__(
        self,
        event_bus: AsyncEventBus,
        config: WatchdogConfig,
    ) -> None:
        """Initialize page watchdog."""
        super().__init__(event_bus, config, name="PageWatchdog")

        # State tracking
        self._active_pages = 0
        self._total_pages_created = 0
        self._successful_loads = 0
        self._failed_loads = 0
        self._timeouts = 0
        self._blocked_domains: set[str] = set()

        # Per-domain failure tracking
        self._domain_failures: dict[str, int] = defaultdict(int)
        self._last_activity: datetime | None = None

        # Pending navigations (url -> start_time)
        self._pending_navigations: dict[str, datetime] = {}

    async def _handle_event(self, event: Event) -> None:
        """Process page-related events."""
        self._last_activity = datetime.now()

        match event.type:
            case EventType.PAGE_CREATED:
                self._active_pages += 1
                self._total_pages_created += 1
                logger.debug(
                    "Page created",
                    active=self._active_pages,
                    total=self._total_pages_created,
                )

            case EventType.PAGE_NAVIGATING:
                url = event.data.get("url", "")
                self._pending_navigations[url] = datetime.now()
                logger.debug("Page navigating", url=url)

            case EventType.PAGE_LOADED:
                url = event.data.get("url", "")
                self._successful_loads += 1

                # Remove from pending
                if url in self._pending_navigations:
                    del self._pending_navigations[url]

                logger.debug(
                    "Page loaded",
                    url=url,
                    success_rate=self._get_success_rate(),
                )

            case EventType.PAGE_ERROR:
                await self._handle_page_error(event)

            case EventType.PAGE_CLOSED:
                self._active_pages = max(0, self._active_pages - 1)

            case EventType.TASK_FAILED:
                await self._handle_task_failure(event)

            case EventType.BLOCKED:
                await self._handle_blocked(event)

    async def _handle_page_error(self, event: Event) -> None:
        """Handle page error event."""
        url = event.data.get("url", "unknown")
        error = event.data.get("error", "Unknown page error")
        error_type = event.data.get("error_type", "PageError")

        self._failed_loads += 1

        # Remove from pending
        if url in self._pending_navigations:
            del self._pending_navigations[url]

        # Track domain failures
        domain = self._extract_domain(url)
        if domain:
            self._domain_failures[domain] += 1

        # Determine severity
        severity = HealthLevel.DEGRADED
        action = RecoveryAction.RETRY_PAGE

        if "timeout" in error.lower():
            self._timeouts += 1
            severity = HealthLevel.DEGRADED
        elif "blocked" in error.lower() or "403" in error:
            self._blocked_domains.add(domain)
            severity = HealthLevel.UNHEALTHY
            action = RecoveryAction.SKIP_TASK
        elif "net::" in error.lower():
            severity = HealthLevel.UNHEALTHY
            action = RecoveryAction.ROTATE_PROXY

        failure = FailureInfo(
            watchdog_name=self.name,
            failure_type="page_error",
            error=error,
            error_type=error_type,
            context={"url": url, "domain": domain},
            severity=severity,
            recoverable=True,
            suggested_action=action,
        )

        await self.detect_failure(failure)

    async def _handle_task_failure(self, event: Event) -> None:
        """Handle task failure that may be page-related."""
        error = event.data.get("error", "")

        # Check if this is a page/navigation error
        page_errors = ["navigation", "page", "load", "timeout", "goto"]
        if any(err in error.lower() for err in page_errors):
            event.data.get("url", "unknown")

            failure = FailureInfo(
                watchdog_name=self.name,
                failure_type="navigation_failure",
                error=error,
                context=event.data,
                severity=HealthLevel.DEGRADED,
                recoverable=True,
                suggested_action=RecoveryAction.RETRY_PAGE,
            )

            await self.detect_failure(failure)

    async def _handle_blocked(self, event: Event) -> None:
        """Handle blocked detection."""
        url = event.data.get("url", "")
        domain = self._extract_domain(url)

        if domain:
            self._blocked_domains.add(domain)
            self._domain_failures[domain] += 10  # Heavy penalty

        failure = FailureInfo(
            watchdog_name=self.name,
            failure_type="domain_blocked",
            error=f"Blocked by {domain}",
            context=event.data,
            severity=HealthLevel.UNHEALTHY,
            recoverable=True,
            suggested_action=RecoveryAction.SKIP_TASK,
        )

        await self.detect_failure(failure)

    async def check_health(self) -> HealthStatus:
        """Check page health status."""
        success_rate = self._get_success_rate()

        details = {
            "active_pages": self._active_pages,
            "total_pages": self._total_pages_created,
            "successful_loads": self._successful_loads,
            "failed_loads": self._failed_loads,
            "timeouts": self._timeouts,
            "success_rate": success_rate,
            "blocked_domains": list(self._blocked_domains),
            "pending_navigations": len(self._pending_navigations),
        }

        # Check for stale pending navigations
        stale_count = 0
        now = datetime.now()
        for _url, start_time in self._pending_navigations.items():
            if (now - start_time).total_seconds() > self.config.page_timeout:
                stale_count += 1

        if stale_count > 0:
            details["stale_navigations"] = stale_count

        # Determine health level
        if success_rate < 0.3:
            return HealthStatus(
                level=HealthLevel.CRITICAL,
                message=f"Very low success rate: {success_rate:.1%}",
                details=details,
            )

        if success_rate < 0.7:
            return HealthStatus(
                level=HealthLevel.DEGRADED,
                message=f"Low success rate: {success_rate:.1%}",
                details=details,
            )

        if stale_count > 3:
            return HealthStatus(
                level=HealthLevel.DEGRADED,
                message=f"{stale_count} pages stuck loading",
                details=details,
            )

        if len(self._blocked_domains) > 0:
            return HealthStatus(
                level=HealthLevel.DEGRADED,
                message=f"Blocked on {len(self._blocked_domains)} domains",
                details=details,
            )

        return HealthStatus(
            level=HealthLevel.HEALTHY,
            message=f"Page loading normally ({success_rate:.1%} success)",
            details=details,
        )

    async def recover(self, failure: FailureInfo) -> RecoveryResult:
        """Attempt page recovery."""
        action = failure.suggested_action

        match action:
            case RecoveryAction.RETRY_PAGE:
                # Page retry is handled by task retry logic
                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.RETRY_PAGE,
                    message="Page retry delegated to task handler",
                )
            case RecoveryAction.SKIP_TASK:
                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.SKIP_TASK,
                    message="Task skipped due to blocking",
                )
            case RecoveryAction.ROTATE_PROXY:
                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.ROTATE_PROXY,
                    message="Proxy rotation recommended",
                )
            case _:
                return RecoveryResult(
                    success=False,
                    action_taken=RecoveryAction.NONE,
                    message=f"No handler for action: {action}",
                )

    def _get_success_rate(self) -> float:
        """Calculate page load success rate."""
        total = self._successful_loads + self._failed_loads
        if total == 0:
            return 1.0
        return self._successful_loads / total

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""

    def is_domain_blocked(self, domain: str) -> bool:
        """Check if a domain is known to be blocked."""
        return domain in self._blocked_domains

    def get_domain_failure_count(self, domain: str) -> int:
        """Get failure count for a domain."""
        return self._domain_failures.get(domain, 0)
