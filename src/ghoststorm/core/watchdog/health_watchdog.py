"""Health watchdog - aggregates system health and provides overall status."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

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

logger = structlog.get_logger(__name__)


class HealthWatchdog(BaseWatchdog):
    """
    Aggregates overall system health.

    Monitors:
    - All major event types
    - Task success/failure rates
    - System resource usage patterns
    - Error frequency and patterns

    Provides:
    - Overall health score
    - System status summary
    - Trend analysis
    """

    MONITORS = [
        # Engine events
        EventType.ENGINE_STARTED,
        EventType.ENGINE_STOPPED,
        EventType.ENGINE_ERROR,
        # Task events
        EventType.TASK_QUEUED,
        EventType.TASK_STARTED,
        EventType.TASK_COMPLETED,
        EventType.TASK_FAILED,
        EventType.TASK_CANCELLED,
        # Worker events
        EventType.WORKER_STARTED,
        EventType.WORKER_STOPPED,
        EventType.WORKER_ERROR,
        # Detection events
        EventType.CAPTCHA_DETECTED,
        EventType.CAPTCHA_SOLVED,
        EventType.CAPTCHA_FAILED,
        EventType.BOT_DETECTED,
        EventType.RATE_LIMITED,
        EventType.BLOCKED,
    ]

    EMITS = [
        EventType.METRICS_COLLECTED,
    ]

    def __init__(
        self,
        event_bus: AsyncEventBus,
        config: WatchdogConfig,
    ) -> None:
        """Initialize health watchdog."""
        super().__init__(event_bus, config, name="HealthWatchdog")

        # Engine state
        self._engine_running = False
        self._engine_start_time: datetime | None = None

        # Task metrics
        self._tasks_queued = 0
        self._tasks_started = 0
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._tasks_cancelled = 0

        # Worker metrics
        self._active_workers = 0
        self._worker_errors = 0

        # Detection metrics
        self._captchas_detected = 0
        self._captchas_solved = 0
        self._captchas_failed = 0
        self._bot_detections = 0
        self._rate_limits = 0
        self._blocks = 0

        # Error tracking
        self._recent_errors: list[dict[str, Any]] = []
        self._error_limit = 100

        # Time windows for rate calculation
        self._last_metrics_time = datetime.now()
        self._tasks_in_window = 0
        self._errors_in_window = 0

    async def _handle_event(self, event: Event) -> None:
        """Process system events for health tracking."""
        match event.type:
            # Engine events
            case EventType.ENGINE_STARTED:
                self._engine_running = True
                self._engine_start_time = datetime.now()

            case EventType.ENGINE_STOPPED:
                self._engine_running = False

            case EventType.ENGINE_ERROR:
                self._track_error(event)

            # Task events
            case EventType.TASK_QUEUED:
                self._tasks_queued += 1

            case EventType.TASK_STARTED:
                self._tasks_started += 1
                self._tasks_in_window += 1

            case EventType.TASK_COMPLETED:
                self._tasks_completed += 1

            case EventType.TASK_FAILED:
                self._tasks_failed += 1
                self._errors_in_window += 1
                self._track_error(event)

            case EventType.TASK_CANCELLED:
                self._tasks_cancelled += 1

            # Worker events
            case EventType.WORKER_STARTED:
                self._active_workers += 1

            case EventType.WORKER_STOPPED:
                self._active_workers = max(0, self._active_workers - 1)

            case EventType.WORKER_ERROR:
                self._worker_errors += 1
                self._track_error(event)

            # Detection events
            case EventType.CAPTCHA_DETECTED:
                self._captchas_detected += 1

            case EventType.CAPTCHA_SOLVED:
                self._captchas_solved += 1

            case EventType.CAPTCHA_FAILED:
                self._captchas_failed += 1
                self._errors_in_window += 1

            case EventType.BOT_DETECTED:
                self._bot_detections += 1
                self._errors_in_window += 1
                self._track_error(event)

            case EventType.RATE_LIMITED:
                self._rate_limits += 1

            case EventType.BLOCKED:
                self._blocks += 1
                self._errors_in_window += 1
                self._track_error(event)

    def _track_error(self, event: Event) -> None:
        """Track an error event."""
        error_entry = {
            "type": event.type.value,
            "data": event.data,
            "timestamp": datetime.now().isoformat(),
        }

        self._recent_errors.append(error_entry)

        # Trim to limit
        if len(self._recent_errors) > self._error_limit:
            self._recent_errors = self._recent_errors[-self._error_limit :]

    async def check_health(self) -> HealthStatus:
        """Calculate overall system health."""
        details = self._get_metrics()

        # Calculate health score components
        scores = []

        # Task success rate (0-100)
        total_tasks = self._tasks_completed + self._tasks_failed
        if total_tasks > 0:
            task_score = (self._tasks_completed / total_tasks) * 100
            scores.append(task_score)
        else:
            scores.append(100)

        # Captcha solve rate (0-100)
        total_captchas = self._captchas_solved + self._captchas_failed
        if total_captchas > 0:
            captcha_score = (self._captchas_solved / total_captchas) * 100
            scores.append(captcha_score)
        else:
            scores.append(100)

        # Detection avoidance (0-100)
        total_detections = self._bot_detections + self._blocks + self._rate_limits
        if self._tasks_started > 0:
            detection_rate = total_detections / self._tasks_started
            detection_score = max(0, (1 - detection_rate) * 100)
            scores.append(detection_score)
        else:
            scores.append(100)

        # Calculate overall score
        overall_score = sum(scores) / len(scores) if scores else 100
        details["health_score"] = overall_score

        # Determine health level
        if not self._engine_running:
            return HealthStatus(
                level=HealthLevel.UNHEALTHY,
                message="Engine not running",
                details=details,
            )

        if overall_score >= 90:
            return HealthStatus(
                level=HealthLevel.HEALTHY,
                message=f"System healthy (score: {overall_score:.0f})",
                details=details,
            )
        elif overall_score >= 70:
            return HealthStatus(
                level=HealthLevel.DEGRADED,
                message=f"System degraded (score: {overall_score:.0f})",
                details=details,
            )
        elif overall_score >= 50:
            return HealthStatus(
                level=HealthLevel.UNHEALTHY,
                message=f"System unhealthy (score: {overall_score:.0f})",
                details=details,
            )
        else:
            return HealthStatus(
                level=HealthLevel.CRITICAL,
                message=f"System critical (score: {overall_score:.0f})",
                details=details,
            )

    async def recover(self, failure: FailureInfo) -> RecoveryResult:
        """Health watchdog doesn't perform recovery itself."""
        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.NONE,
            message="HealthWatchdog monitors only, no recovery actions",
        )

    def _get_metrics(self) -> dict[str, Any]:
        """Get current metrics snapshot."""
        uptime = None
        if self._engine_start_time:
            uptime = (datetime.now() - self._engine_start_time).total_seconds()

        total_tasks = self._tasks_completed + self._tasks_failed
        success_rate = self._tasks_completed / total_tasks if total_tasks > 0 else 1.0

        return {
            "engine_running": self._engine_running,
            "uptime_seconds": uptime,
            "active_workers": self._active_workers,
            "tasks": {
                "queued": self._tasks_queued,
                "started": self._tasks_started,
                "completed": self._tasks_completed,
                "failed": self._tasks_failed,
                "cancelled": self._tasks_cancelled,
                "success_rate": success_rate,
            },
            "captchas": {
                "detected": self._captchas_detected,
                "solved": self._captchas_solved,
                "failed": self._captchas_failed,
            },
            "detections": {
                "bot": self._bot_detections,
                "rate_limited": self._rate_limits,
                "blocked": self._blocks,
            },
            "errors": {
                "worker_errors": self._worker_errors,
                "recent_count": len(self._recent_errors),
            },
        }

    def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent error entries."""
        return self._recent_errors[-limit:]

    def get_task_throughput(self) -> float:
        """Calculate tasks per minute throughput."""
        elapsed = (datetime.now() - self._last_metrics_time).total_seconds()
        if elapsed < 60:
            elapsed = 60  # Minimum 1 minute window

        tasks_per_minute = (self._tasks_in_window / elapsed) * 60
        return tasks_per_minute

    def reset_window_metrics(self) -> None:
        """Reset time window metrics."""
        self._last_metrics_time = datetime.now()
        self._tasks_in_window = 0
        self._errors_in_window = 0
