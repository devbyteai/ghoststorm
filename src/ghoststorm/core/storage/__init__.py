"""Storage layer for GhostStorm persistence."""

from ghoststorm.core.storage.database import (
    Database,
    DatabaseConfig,
    close_database,
    get_database,
)
from ghoststorm.core.storage.models import (
    ApiKey,
    Base,
    CaptchaResult,
    EventLog,
    Fingerprint,
    MetricSample,
    Proxy,
    ProxyHealthStatus,
    ProxyProtocol,
    Session,
    Task,
    TaskStatus,
)

__all__ = [
    # Database
    "Database",
    "DatabaseConfig",
    "get_database",
    "close_database",
    # Models
    "Base",
    "Task",
    "TaskStatus",
    "Proxy",
    "ProxyProtocol",
    "ProxyHealthStatus",
    "Fingerprint",
    "Session",
    "MetricSample",
    "EventLog",
    "CaptchaResult",
    "ApiKey",
]
