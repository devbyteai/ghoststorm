"""File-based proxy provider."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
import structlog

from ghoststorm.core.models.proxy import Proxy, ProxyHealth, RotationStrategy

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger(__name__)


class FileProxyProvider:
    """Proxy provider that loads proxies from a text file."""

    name = "file"

    def __init__(
        self,
        file_path: Path | str | None = None,
        proxies: list[str] | None = None,
    ) -> None:
        """
        Initialize file proxy provider.

        Args:
            file_path: Path to proxy file
            proxies: Optional list of proxy strings
        """
        self._file_path = Path(file_path) if file_path else None
        self._initial_proxies = proxies or []
        self._proxies: list[Proxy] = []
        self._health: dict[str, ProxyHealth] = {}
        self._lock = asyncio.Lock()
        self._current_index = 0

    @property
    def total_proxies(self) -> int:
        return len(self._proxies)

    @property
    def healthy_proxies(self) -> int:
        return sum(1 for h in self._health.values() if h.is_healthy)

    async def initialize(self) -> None:
        """Load proxies from file."""
        if self._initial_proxies:
            for proxy_str in self._initial_proxies:
                try:
                    proxy = Proxy.from_string(proxy_str)
                    self._proxies.append(proxy)
                    self._health[proxy.id] = ProxyHealth(proxy=proxy, is_healthy=True)
                except Exception as e:
                    logger.warning("Failed to parse proxy", proxy=proxy_str, error=str(e))

        if self._file_path and self._file_path.exists():
            await self._load_from_file()

        logger.info("Proxy provider initialized", count=len(self._proxies))

    async def _load_from_file(self) -> None:
        """Load proxies from file."""
        try:
            content = self._file_path.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    proxy = Proxy.from_string(line)
                    if proxy.id not in [p.id for p in self._proxies]:
                        self._proxies.append(proxy)
                        self._health[proxy.id] = ProxyHealth(proxy=proxy, is_healthy=True)
                except Exception as e:
                    logger.warning("Failed to parse proxy", line=line, error=str(e))
        except Exception as e:
            logger.error("Failed to load proxy file", path=str(self._file_path), error=str(e))

    async def get_proxy(
        self,
        *,
        strategy: RotationStrategy | None = None,
        country: str | None = None,
        proxy_type: str | None = None,
        sticky_session: str | None = None,
    ) -> Proxy:
        """Get a proxy based on strategy."""
        strategy = strategy or RotationStrategy.RANDOM

        async with self._lock:
            # Filter proxies
            candidates = self._proxies.copy()

            if country:
                candidates = [p for p in candidates if p.country == country]

            if proxy_type:
                candidates = [p for p in candidates if p.category.value == proxy_type]

            # Filter by health
            healthy_candidates = [
                p
                for p in candidates
                if self._health.get(p.id, ProxyHealth(proxy=p, is_healthy=True)).is_healthy
            ]

            if not healthy_candidates:
                # Fall back to all candidates if none healthy
                healthy_candidates = candidates

            if not healthy_candidates:
                raise NoProxyAvailableError("No proxies available matching criteria")

            # Select based on strategy
            if strategy == RotationStrategy.RANDOM:
                return random.choice(healthy_candidates)

            elif strategy == RotationStrategy.ROUND_ROBIN:
                proxy = healthy_candidates[self._current_index % len(healthy_candidates)]
                self._current_index += 1
                return proxy

            elif strategy == RotationStrategy.WEIGHTED:
                # Weight by health score
                weights = []
                for p in healthy_candidates:
                    health = self._health.get(p.id)
                    weight = health.weight if health else 1.0
                    weights.append(max(0.1, weight))

                return random.choices(healthy_candidates, weights=weights, k=1)[0]

            elif strategy == RotationStrategy.FASTEST:
                # Sort by latency
                sorted_proxies = sorted(
                    healthy_candidates,
                    key=lambda p: self._health.get(
                        p.id, ProxyHealth(proxy=p, is_healthy=True)
                    ).latency_ms
                    or float("inf"),
                )
                return sorted_proxies[0]

            else:
                return random.choice(healthy_candidates)

    async def mark_success(self, proxy: Proxy, latency_ms: float) -> None:
        """Mark proxy as successful."""
        async with self._lock:
            if proxy.id in self._health:
                self._health[proxy.id].mark_success(latency_ms)
            else:
                health = ProxyHealth(proxy=proxy, is_healthy=True)
                health.mark_success(latency_ms)
                self._health[proxy.id] = health

    async def mark_failure(self, proxy: Proxy, error: str | None = None) -> None:
        """Mark proxy as failed."""
        async with self._lock:
            if proxy.id in self._health:
                self._health[proxy.id].mark_failure(error)
            else:
                health = ProxyHealth(proxy=proxy, is_healthy=True)
                health.mark_failure(error)
                self._health[proxy.id] = health

    async def health_check(
        self,
        *,
        test_url: str = "https://httpbin.org/ip",
        timeout: float = 10.0,
        concurrent: int = 10,
    ) -> list[ProxyHealth]:
        """Run health checks on all proxies."""
        semaphore = asyncio.Semaphore(concurrent)

        async def check_proxy(proxy: Proxy) -> ProxyHealth:
            async with semaphore:
                start = datetime.now()
                try:
                    async with aiohttp.ClientSession() as session:
                        proxy_url = proxy.url
                        async with session.get(
                            test_url,
                            proxy=proxy_url,
                            timeout=aiohttp.ClientTimeout(total=timeout),
                        ) as response:
                            if response.status == 200:
                                latency = (datetime.now() - start).total_seconds() * 1000
                                health = self._health.get(
                                    proxy.id, ProxyHealth(proxy=proxy, is_healthy=True)
                                )
                                health.mark_success(latency)
                                return health
                            else:
                                health = self._health.get(
                                    proxy.id, ProxyHealth(proxy=proxy, is_healthy=True)
                                )
                                health.mark_failure(f"Status {response.status}")
                                return health
                except Exception as e:
                    health = self._health.get(proxy.id, ProxyHealth(proxy=proxy, is_healthy=True))
                    health.mark_failure(str(e))
                    return health

        tasks = [check_proxy(proxy) for proxy in self._proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_results = []
        for result in results:
            if isinstance(result, ProxyHealth):
                health_results.append(result)

        logger.info(
            "Health check complete",
            total=len(self._proxies),
            healthy=sum(1 for h in health_results if h.is_healthy),
        )

        return health_results

    async def get_all(self) -> AsyncIterator[Proxy]:
        """Iterate over all proxies."""
        for proxy in self._proxies:
            yield proxy

    async def add_proxy(self, proxy: Proxy) -> None:
        """Add a proxy to the pool."""
        async with self._lock:
            if proxy.id not in [p.id for p in self._proxies]:
                self._proxies.append(proxy)
                self._health[proxy.id] = ProxyHealth(proxy=proxy, is_healthy=True)

    async def remove_proxy(self, proxy: Proxy) -> None:
        """Remove a proxy from the pool."""
        async with self._lock:
            self._proxies = [p for p in self._proxies if p.id != proxy.id]
            self._health.pop(proxy.id, None)

    async def refresh(self) -> None:
        """Reload proxies from file."""
        if self._file_path:
            async with self._lock:
                self._proxies.clear()
                self._health.clear()
            await self._load_from_file()

    async def close(self) -> None:
        """Clean up resources."""
        pass


class NoProxyAvailableError(Exception):
    """Raised when no proxy is available."""

    pass
