"""Watchdog system for monitoring and auto-recovery."""

from ghoststorm.core.watchdog.base import BaseWatchdog
from ghoststorm.core.watchdog.browser_watchdog import BrowserWatchdog
from ghoststorm.core.watchdog.health_watchdog import HealthWatchdog
from ghoststorm.core.watchdog.manager import WatchdogManager
from ghoststorm.core.watchdog.models import (
    FailureInfo,
    HealthLevel,
    HealthStatus,
    RecoveryAction,
    RecoveryResult,
    WatchdogAlert,
    WatchdogConfig,
    WatchdogState,
)
from ghoststorm.core.watchdog.network_watchdog import NetworkWatchdog
from ghoststorm.core.watchdog.page_watchdog import PageWatchdog

__all__ = [
    # Base classes
    "BaseWatchdog",
    # Watchdog implementations
    "BrowserWatchdog",
    "FailureInfo",
    "HealthLevel",
    "HealthStatus",
    "HealthWatchdog",
    "NetworkWatchdog",
    "PageWatchdog",
    "RecoveryAction",
    "RecoveryResult",
    "WatchdogAlert",
    # Models
    "WatchdogConfig",
    "WatchdogManager",
    "WatchdogState",
]
