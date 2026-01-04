"""Proxy provider interface definitions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ghoststorm.core.models.proxy import Proxy, ProxyHealth, RotationStrategy


@runtime_checkable
class IProxyProvider(Protocol):
    """Contract for proxy providers."""

    @property
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    def total_proxies(self) -> int:
        """Total number of proxies available."""
        ...

    @property
    def healthy_proxies(self) -> int:
        """Number of healthy proxies."""
        ...

    async def initialize(self) -> None:
        """Initialize the provider (load proxies, connect to API, etc.)."""
        ...

    async def get_proxy(
        self,
        *,
        strategy: RotationStrategy | None = None,
        country: str | None = None,
        proxy_type: str | None = None,
        sticky_session: str | None = None,
    ) -> Proxy:
        """
        Get a proxy based on strategy and filters.

        Args:
            strategy: Rotation strategy to use
            country: Filter by country code (e.g., 'US', 'GB')
            proxy_type: Filter by type ('residential', 'datacenter', 'mobile')
            sticky_session: Session ID for sticky sessions

        Returns:
            A Proxy instance

        Raises:
            NoProxyAvailableError: If no matching proxy is available
        """
        ...

    async def mark_success(
        self,
        proxy: Proxy,
        latency_ms: float,
    ) -> None:
        """Mark a proxy as successfully used."""
        ...

    async def mark_failure(
        self,
        proxy: Proxy,
        error: str | None = None,
    ) -> None:
        """Mark a proxy as failed."""
        ...

    async def health_check(
        self,
        *,
        test_url: str = "https://httpbin.org/ip",
        timeout: float = 10.0,
        concurrent: int = 10,
    ) -> list[ProxyHealth]:
        """
        Run health checks on all proxies.

        Args:
            test_url: URL to test against
            timeout: Timeout per request in seconds
            concurrent: Number of concurrent checks

        Returns:
            List of ProxyHealth results
        """
        ...

    async def get_all(self) -> AsyncIterator[Proxy]:
        """Iterate over all proxies."""
        ...

    async def add_proxy(self, proxy: Proxy) -> None:
        """Add a proxy to the pool."""
        ...

    async def remove_proxy(self, proxy: Proxy) -> None:
        """Remove a proxy from the pool."""
        ...

    async def refresh(self) -> None:
        """Refresh proxy list (reload from source)."""
        ...

    async def close(self) -> None:
        """Clean up provider resources."""
        ...
