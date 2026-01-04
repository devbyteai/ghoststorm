"""Proxy data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProxyType(str, Enum):
    """Proxy type classification."""

    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

    @classmethod
    def from_string(cls, value: str) -> ProxyType:
        """Parse proxy type from string."""
        value = value.lower().strip()
        if value in ("http", ""):
            return cls.HTTP
        if value == "https":
            return cls.HTTPS
        if value == "socks4":
            return cls.SOCKS4
        if value in ("socks5", "socks"):
            return cls.SOCKS5
        raise ValueError(f"Unknown proxy type: {value}")


class RotationStrategy(str, Enum):
    """Proxy rotation strategies."""

    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_USED = "least_used"
    FASTEST = "fastest"
    STICKY = "sticky"
    PER_REQUEST = "per_request"


class ProxyCategory(str, Enum):
    """Proxy category (source type)."""

    RESIDENTIAL = "residential"
    DATACENTER = "datacenter"
    MOBILE = "mobile"
    ISP = "isp"
    UNKNOWN = "unknown"


@dataclass
class Proxy:
    """Represents a proxy server."""

    host: str
    port: int
    proxy_type: ProxyType = ProxyType.HTTP
    username: str | None = None
    password: str | None = None
    country: str | None = None
    category: ProxyCategory = ProxyCategory.UNKNOWN

    # Metadata
    id: str | None = None
    provider: str | None = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and normalize proxy data."""
        if not self.id:
            self.id = f"{self.host}:{self.port}"

    @property
    def url(self) -> str:
        """Get proxy URL for Playwright/requests."""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"

    @property
    def server(self) -> str:
        """Get proxy server string (without auth)."""
        return f"{self.proxy_type.value}://{self.host}:{self.port}"

    @property
    def has_auth(self) -> bool:
        """Check if proxy requires authentication."""
        return bool(self.username and self.password)

    @classmethod
    def from_string(cls, proxy_string: str) -> Proxy:
        """
        Parse proxy from various string formats.

        Supported formats:
        - host:port
        - host:port:user:pass
        - type://host:port
        - type://user:pass@host:port
        - user:pass@host:port
        """
        proxy_string = proxy_string.strip()
        proxy_type = ProxyType.HTTP
        username = None
        password = None

        # Handle protocol prefix
        if "://" in proxy_string:
            protocol, rest = proxy_string.split("://", 1)
            proxy_type = ProxyType.from_string(protocol)
            proxy_string = rest

        # Handle auth in URL format (user:pass@host:port)
        if "@" in proxy_string:
            auth, hostport = proxy_string.rsplit("@", 1)
            if ":" in auth:
                username, password = auth.split(":", 1)
            proxy_string = hostport

        # Parse host:port or host:port:user:pass
        parts = proxy_string.split(":")
        if len(parts) == 2:
            host, port = parts
        elif len(parts) == 4:
            host, port, username, password = parts
        elif len(parts) == 5:
            # type:host:port:user:pass (legacy format)
            proxy_type = ProxyType.from_string(parts[0])
            host, port, username, password = parts[1], parts[2], parts[3], parts[4]
        else:
            raise ValueError(f"Invalid proxy format: {proxy_string}")

        return cls(
            host=host,
            port=int(port),
            proxy_type=proxy_type,
            username=username,
            password=password,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "proxy_type": self.proxy_type.value,
            "username": self.username,
            "password": self.password,
            "country": self.country,
            "category": self.category.value,
            "id": self.id,
            "provider": self.provider,
            "tags": self.tags,
        }

    def __hash__(self) -> int:
        """Make proxy hashable."""
        return hash((self.host, self.port, self.proxy_type))

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, Proxy):
            return False
        return (
            self.host == other.host
            and self.port == other.port
            and self.proxy_type == other.proxy_type
        )


@dataclass
class ProxyHealth:
    """Health status of a proxy."""

    proxy: Proxy
    is_healthy: bool
    latency_ms: float | None = None
    last_check: datetime | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    error_message: str | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def weight(self) -> float:
        """Calculate weight for weighted selection."""
        if not self.is_healthy:
            return 0.0
        # Combine success rate and latency
        latency_factor = 1.0
        if self.latency_ms:
            # Lower latency = higher weight
            latency_factor = max(0.1, 1.0 - (self.latency_ms / 5000))
        return self.success_rate * latency_factor

    def mark_success(self, latency_ms: float) -> None:
        """Mark a successful request."""
        self.is_healthy = True
        self.latency_ms = latency_ms
        self.last_success = datetime.now()
        self.last_check = self.last_success
        self.consecutive_failures = 0
        self.total_requests += 1
        self.successful_requests += 1
        self.error_message = None

    def mark_failure(self, error: str | None = None) -> None:
        """Mark a failed request."""
        now = datetime.now()
        self.last_failure = now
        self.last_check = now
        self.consecutive_failures += 1
        self.total_requests += 1
        self.error_message = error

        # Mark unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.is_healthy = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "proxy_id": self.proxy.id,
            "is_healthy": self.is_healthy,
            "latency_ms": self.latency_ms,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": self.success_rate,
            "weight": self.weight,
            "error_message": self.error_message,
        }
