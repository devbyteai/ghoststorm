"""Data models for the watchdog system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class HealthLevel(str, Enum):
    """Health level indicators."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class RecoveryAction(str, Enum):
    """Types of recovery actions."""

    RESTART_BROWSER = "restart_browser"
    RETRY_PAGE = "retry_page"
    ROTATE_PROXY = "rotate_proxy"
    DISMISS_POPUP = "dismiss_popup"
    CLEAR_CACHE = "clear_cache"
    BACKOFF = "backoff"
    SKIP_TASK = "skip_task"
    NONE = "none"


@dataclass
class WatchdogConfig:
    """Configuration for watchdog behavior."""

    enabled: bool = True
    health_check_interval: float = 30.0
    auto_recovery: bool = True
    max_recovery_attempts: int = 3
    recovery_cooldown: float = 5.0
    alert_threshold: int = 3

    # Per-watchdog settings
    browser_timeout: float = 60.0
    page_timeout: float = 30.0
    network_timeout: float = 15.0

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.health_check_interval < 1.0:
            self.health_check_interval = 1.0
        if self.max_recovery_attempts < 1:
            self.max_recovery_attempts = 1


@dataclass
class HealthStatus:
    """Represents the health status of a component."""

    level: HealthLevel
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    checks_passed: int = 0
    checks_failed: int = 0

    @property
    def is_healthy(self) -> bool:
        """Check if status indicates healthy state."""
        return self.level in (HealthLevel.HEALTHY, HealthLevel.DEGRADED)

    @property
    def score(self) -> float:
        """Calculate health score 0-1."""
        total = self.checks_passed + self.checks_failed
        if total == 0:
            return 1.0 if self.level == HealthLevel.HEALTHY else 0.0
        return self.checks_passed / total

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "score": self.score,
        }


@dataclass
class FailureInfo:
    """Information about a detected failure."""

    watchdog_name: str
    failure_type: str
    error: str
    error_type: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    severity: HealthLevel = HealthLevel.UNHEALTHY
    recoverable: bool = True
    suggested_action: RecoveryAction = RecoveryAction.NONE

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "watchdog_name": self.watchdog_name,
            "failure_type": self.failure_type,
            "error": self.error,
            "error_type": self.error_type,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "suggested_action": self.suggested_action.value,
        }


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""

    success: bool
    action_taken: RecoveryAction
    message: str
    duration_ms: float = 0.0
    attempts: int = 1
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "action_taken": self.action_taken.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "details": self.details,
        }


@dataclass
class WatchdogState:
    """Current state of a watchdog."""

    name: str
    enabled: bool = True
    running: bool = False
    health: HealthStatus = field(
        default_factory=lambda: HealthStatus(level=HealthLevel.UNKNOWN, message="Not yet checked")
    )
    last_check: datetime | None = None
    total_events: int = 0
    failures_detected: int = 0
    recoveries_attempted: int = 0
    recoveries_successful: int = 0

    @property
    def recovery_success_rate(self) -> float:
        """Calculate recovery success rate."""
        if self.recoveries_attempted == 0:
            return 1.0
        return self.recoveries_successful / self.recoveries_attempted

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "running": self.running,
            "health": self.health.to_dict(),
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "total_events": self.total_events,
            "failures_detected": self.failures_detected,
            "recoveries_attempted": self.recoveries_attempted,
            "recoveries_successful": self.recoveries_successful,
            "recovery_success_rate": self.recovery_success_rate,
        }


@dataclass
class WatchdogAlert:
    """Alert generated by a watchdog."""

    watchdog_name: str
    level: HealthLevel
    title: str
    message: str
    failure: FailureInfo | None = None
    recovery: RecoveryResult | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "watchdog_name": self.watchdog_name,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "failure": self.failure.to_dict() if self.failure else None,
            "recovery": self.recovery.to_dict() if self.recovery else None,
            "timestamp": self.timestamp.isoformat(),
        }
