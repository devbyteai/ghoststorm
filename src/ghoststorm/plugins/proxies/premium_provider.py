"""Base class for premium (paid) proxy providers."""

from __future__ import annotations

import asyncio
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

import aiohttp
import structlog

from ghoststorm.core.models.proxy import (
    Proxy,
    ProxyCategory,
    ProxyHealth,
    RotationStrategy,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger(__name__)


@dataclass
class ProviderCredentials:
    """Credentials for a premium provider."""

    provider: str
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    customer_id: str | None = None
    zone: str | None = None


@dataclass
class ProviderStats:
    """Usage statistics for a premium provider."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    bandwidth_bytes: int = 0
    last_request: datetime | None = None

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "bandwidth_bytes": self.bandwidth_bytes,
            "bandwidth_mb": round(self.bandwidth_bytes / 1024 / 1024, 2),
            "success_rate": round(self.success_rate * 100, 1),
            "last_request": self.last_request.isoformat() if self.last_request else None,
        }


class PremiumProxyProvider(ABC):
    """Base class for premium (paid) proxy providers.

    Premium providers generate proxy URLs dynamically based on credentials
    and targeting options. They don't maintain a local proxy list but instead
    connect to the provider's gateway server.
    """

    # Override in subclasses
    name: str = "premium"
    endpoint_host: str = ""
    endpoint_port: int = 0
    category: ProxyCategory = ProxyCategory.RESIDENTIAL

    def __init__(
        self,
        username: str,
        password: str,
        *,
        country: str | None = None,
        city: str | None = None,
        state: str | None = None,
        session_type: Literal["rotating", "sticky"] = "rotating",
        session_duration: int = 10,  # minutes for sticky sessions
        **kwargs: Any,
    ) -> None:
        """Initialize premium provider.

        Args:
            username: Provider username/account ID
            password: Provider password
            country: Target country code (e.g., 'us', 'gb')
            city: Target city (if supported)
            state: Target state (if supported)
            session_type: 'rotating' (new IP each request) or 'sticky' (maintain IP)
            session_duration: Duration for sticky sessions in minutes
        """
        self.username = username
        self.password = password
        self.country = country.lower() if country else None
        self.city = city
        self.state = state
        self.session_type = session_type
        self.session_duration = session_duration
        self._stats = ProviderStats()
        self._active_sessions: dict[str, str] = {}  # session_id -> proxy_url
        self._lock = asyncio.Lock()
        self._initialized = False

    @property
    def total_proxies(self) -> int:
        """Premium providers have unlimited proxies from the gateway."""
        return -1  # Unlimited

    @property
    def healthy_proxies(self) -> int:
        """Premium providers are always healthy (provider manages this)."""
        return -1  # Unlimited

    @property
    def stats(self) -> ProviderStats:
        """Get usage statistics."""
        return self._stats

    async def initialize(self) -> None:
        """Initialize the provider."""
        self._initialized = True
        logger.info(
            "Premium provider initialized",
            provider=self.name,
            country=self.country,
            session_type=self.session_type,
        )

    @abstractmethod
    def build_proxy_url(
        self,
        *,
        session_id: str | None = None,
        country: str | None = None,
        city: str | None = None,
    ) -> str:
        """Build the proxy URL with authentication and targeting.

        Args:
            session_id: Session ID for sticky sessions
            country: Override country for this request
            city: Override city for this request

        Returns:
            Full proxy URL like http://user:pass@host:port
        """
        ...

    def _generate_session_id(self) -> str:
        """Generate a unique session ID for sticky sessions."""
        return secrets.token_hex(8)

    async def get_proxy(
        self,
        *,
        strategy: RotationStrategy | None = None,
        country: str | None = None,
        proxy_type: str | None = None,
        sticky_session: str | None = None,
    ) -> Proxy:
        """Get a proxy from this provider.

        Args:
            strategy: Ignored for premium providers (handled internally)
            country: Override country for this request
            proxy_type: Ignored for premium (always HTTP/HTTPS)
            sticky_session: Session ID for sticky sessions

        Returns:
            Proxy instance configured for this provider
        """
        async with self._lock:
            # Handle sticky sessions
            session_id = None
            if self.session_type == "sticky" or sticky_session:
                session_id = sticky_session or self._generate_session_id()

            # Build the proxy URL
            url = self.build_proxy_url(
                session_id=session_id,
                country=country or self.country,
                city=self.city,
            )

            # Parse the URL to create Proxy object
            proxy = Proxy.from_string(url)
            proxy.provider = self.name
            proxy.category = self.category
            proxy.country = country or self.country

            # Track the session
            if session_id:
                self._active_sessions[session_id] = url

            return proxy

    async def mark_success(self, proxy: Proxy, latency_ms: float) -> None:
        """Mark a successful request."""
        async with self._lock:
            self._stats.total_requests += 1
            self._stats.successful_requests += 1
            self._stats.last_request = datetime.now()

    async def mark_failure(self, proxy: Proxy, error: str | None = None) -> None:
        """Mark a failed request."""
        async with self._lock:
            self._stats.total_requests += 1
            self._stats.failed_requests += 1
            self._stats.last_request = datetime.now()

        logger.warning(
            "Premium proxy request failed",
            provider=self.name,
            error=error,
        )

    async def test_connection(self, test_url: str = "https://httpbin.org/ip") -> dict[str, Any]:
        """Test the provider connection.

        Returns:
            Dict with 'success', 'latency_ms', 'ip', 'error'
        """
        proxy = await self.get_proxy()
        start = datetime.now()

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    test_url,
                    proxy=proxy.url,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response,
            ):
                if response.status == 200:
                    data = await response.json()
                    latency = (datetime.now() - start).total_seconds() * 1000
                    return {
                        "success": True,
                        "latency_ms": round(latency, 2),
                        "ip": data.get("origin", "unknown"),
                        "provider": self.name,
                        "country": self.country,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "provider": self.name,
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.name,
            }

    async def health_check(
        self,
        *,
        test_url: str = "https://httpbin.org/ip",
        timeout: float = 10.0,
        concurrent: int = 1,
    ) -> list[ProxyHealth]:
        """Health check for premium provider.

        Premium providers don't maintain a list of proxies to check.
        This just tests the gateway connection.
        """
        result = await self.test_connection(test_url)
        proxy = await self.get_proxy()
        health = ProxyHealth(
            proxy=proxy,
            is_healthy=result["success"],
            latency_ms=result.get("latency_ms"),
            last_check=datetime.now(),
            error_message=result.get("error"),
        )
        if result["success"]:
            health.last_success = datetime.now()
            health.successful_requests = 1
        return [health]

    async def get_all(self) -> AsyncIterator[Proxy]:
        """Premium providers don't have a fixed list.

        This generates a single proxy for iteration compatibility.
        """
        yield await self.get_proxy()

    async def add_proxy(self, proxy: Proxy) -> None:
        """Not applicable for premium providers."""
        pass

    async def remove_proxy(self, proxy: Proxy) -> None:
        """Not applicable for premium providers."""
        pass

    async def refresh(self) -> None:
        """Refresh doesn't apply to premium providers."""
        pass

    async def close(self) -> None:
        """Clean up resources."""
        self._active_sessions.clear()
        logger.info("Premium provider closed", provider=self.name)

    def to_config(self) -> dict[str, Any]:
        """Export configuration for saving."""
        return {
            "provider": self.name,
            "username": self.username,
            "password": self.password,
            "country": self.country,
            "city": self.city,
            "state": self.state,
            "session_type": self.session_type,
            "session_duration": self.session_duration,
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> PremiumProxyProvider:
        """Create provider from saved configuration."""
        return cls(
            username=config["username"],
            password=config["password"],
            country=config.get("country"),
            city=config.get("city"),
            state=config.get("state"),
            session_type=config.get("session_type", "rotating"),
            session_duration=config.get("session_duration", 10),
        )
