"""SQLAlchemy database models for GhostStorm persistence.

Provides persistent storage for:
- Task results and history
- Proxy health and statistics
- Session state and cookies
- Fingerprint profiles
- Metrics and analytics
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


class TaskStatus(str, PyEnum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ProxyProtocol(str, PyEnum):
    """Proxy protocol types."""

    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyHealthStatus(str, PyEnum):
    """Proxy health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    BANNED = "banned"
    UNKNOWN = "unknown"


class Task(Base):
    """Task execution record."""

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    batch_id = Column(String(36), index=True, nullable=True)

    # Task details
    url = Column(String(2048), nullable=False)
    task_type = Column(String(50), nullable=False, default="visit")
    priority = Column(Integer, default=0)

    # Execution status
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)

    # Timing
    created_at = Column(DateTime, default=utc_now, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Results
    response_status = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    page_title = Column(String(512), nullable=True)
    screenshot_path = Column(String(512), nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)

    # Context
    proxy_id = Column(String(36), ForeignKey("proxies.id"), nullable=True)
    fingerprint_id = Column(String(36), ForeignKey("fingerprints.id"), nullable=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=True)

    # Configuration (JSON)
    config = Column(JSON, nullable=True)

    # Relationships
    proxy = relationship("Proxy", back_populates="tasks")
    fingerprint = relationship("Fingerprint", back_populates="tasks")
    session = relationship("Session", back_populates="tasks")

    # Indexes
    __table_args__ = (
        Index("idx_tasks_status_created", "status", "created_at"),
        Index("idx_tasks_batch_status", "batch_id", "status"),
    )


class Proxy(Base):
    """Proxy record with health tracking."""

    __tablename__ = "proxies"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Proxy details
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(Enum(ProxyProtocol), default=ProxyProtocol.HTTP)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)

    # Unique constraint on host:port:protocol
    __table_args__ = (
        UniqueConstraint("host", "port", "protocol", name="uq_proxy_endpoint"),
    )

    # Metadata
    country = Column(String(2), nullable=True)  # ISO country code
    city = Column(String(100), nullable=True)
    isp = Column(String(255), nullable=True)
    is_residential = Column(Boolean, default=False)
    is_datacenter = Column(Boolean, default=False)

    # Health status
    health = Column(Enum(ProxyHealthStatus), default=ProxyHealthStatus.UNKNOWN)
    last_check = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)

    # Statistics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    avg_response_time_ms = Column(Float, nullable=True)
    consecutive_failures = Column(Integer, default=0)

    # Scoring
    score = Column(Float, default=50.0)  # 0-100

    # Banned domains (JSON list)
    banned_domains = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    tasks = relationship("Task", back_populates="proxy")

    @property
    def connection_string(self) -> str:
        """Get proxy connection string."""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.protocol.value}://{auth}{self.host}:{self.port}"

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.5
        return self.successful_requests / self.total_requests


class Fingerprint(Base):
    """Browser fingerprint profile."""

    __tablename__ = "fingerprints"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=True)

    # User agent
    user_agent = Column(String(512), nullable=False)
    browser = Column(String(50), nullable=True)
    browser_version = Column(String(20), nullable=True)
    os = Column(String(50), nullable=True)
    os_version = Column(String(20), nullable=True)

    # Screen
    screen_width = Column(Integer, nullable=True)
    screen_height = Column(Integer, nullable=True)
    color_depth = Column(Integer, default=24)
    pixel_ratio = Column(Float, default=1.0)

    # Hardware
    hardware_concurrency = Column(Integer, default=4)
    device_memory = Column(Integer, default=8)

    # Locale
    locale = Column(String(10), default="en-US")
    timezone_id = Column(String(50), nullable=True)

    # WebGL
    webgl_vendor = Column(String(255), nullable=True)
    webgl_renderer = Column(String(255), nullable=True)

    # Canvas noise
    canvas_noise_r = Column(Integer, default=0)
    canvas_noise_g = Column(Integer, default=0)
    canvas_noise_b = Column(Integer, default=0)
    canvas_noise_a = Column(Integer, default=0)

    # Full profile (JSON)
    full_profile = Column(JSON, nullable=True)

    # Usage tracking
    times_used = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    tasks = relationship("Task", back_populates="fingerprint")
    sessions = relationship("Session", back_populates="fingerprint")


class Session(Base):
    """Browser session with state persistence."""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Session identity
    name = Column(String(100), nullable=True)
    user_persona = Column(String(50), nullable=True)

    # Associated fingerprint
    fingerprint_id = Column(String(36), ForeignKey("fingerprints.id"), nullable=True)

    # State
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime, default=utc_now)
    last_activity = Column(DateTime, default=utc_now)
    ended_at = Column(DateTime, nullable=True)

    # Behavior tracking
    pages_visited = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    total_keystrokes = Column(Integer, default=0)
    fatigue_level = Column(Float, default=0.0)

    # Session data (JSON)
    cookies = Column(JSON, default=list)
    local_storage = Column(JSON, default=dict)
    session_storage = Column(JSON, default=dict)

    # Coherence state (JSON)
    coherence_state = Column(JSON, nullable=True)

    # Relationships
    fingerprint = relationship("Fingerprint", back_populates="sessions")
    tasks = relationship("Task", back_populates="session")


class MetricSample(Base):
    """Time-series metric sample."""

    __tablename__ = "metric_samples"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Metric identity
    name = Column(String(100), nullable=False, index=True)
    labels = Column(JSON, default=dict)  # Label key-value pairs

    # Value
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=utc_now, index=True)

    # Indexes
    __table_args__ = (
        Index("idx_metrics_name_time", "name", "timestamp"),
    )


class EventLog(Base):
    """System event log."""

    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default="info")  # debug, info, warning, error
    message = Column(Text, nullable=False)

    # Context
    task_id = Column(String(36), nullable=True)
    proxy_id = Column(String(36), nullable=True)
    session_id = Column(String(36), nullable=True)

    # Additional data
    data = Column(JSON, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=utc_now, index=True)

    # Indexes
    __table_args__ = (
        Index("idx_events_type_time", "event_type", "timestamp"),
    )


class CaptchaResult(Base):
    """CAPTCHA solving result."""

    __tablename__ = "captcha_results"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Challenge details
    captcha_type = Column(String(50), nullable=False)
    site_url = Column(String(2048), nullable=True)
    site_key = Column(String(100), nullable=True)

    # Solution
    success = Column(Boolean, nullable=False)
    solver_used = Column(String(50), nullable=True)
    solution = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)

    # Timing
    solve_time_ms = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=utc_now)

    # Error
    error = Column(Text, nullable=True)


class ApiKey(Base):
    """API authentication keys."""

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Key details
    key_hash = Column(String(64), unique=True, nullable=False)  # SHA-256 hash
    name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    # Permissions
    permissions = Column(JSON, default=list)  # List of permission strings
    rate_limit = Column(Integer, default=1000)  # Requests per hour

    # Status
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    expires_at = Column(DateTime, nullable=True)
