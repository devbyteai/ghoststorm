"""Smart rotating proxy provider with advanced strategies."""

from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict
from collections.abc import AsyncIterator

import structlog

from ghoststorm.core.models.proxy import Proxy, ProxyHealth, RotationStrategy
from ghoststorm.plugins.proxies.file_provider import FileProxyProvider, NoProxyAvailableError

logger = structlog.get_logger(__name__)


class RotatingProxyProvider:
    """
    Advanced proxy provider with intelligent rotation.

    Features:
    - Multiple rotation strategies
    - Automatic health-based exclusion
    - Sticky sessions
    - Rate limiting per proxy
    - Geographic filtering
    """

    name = "rotating"

    def __init__(
        self,
        providers: list[FileProxyProvider] | None = None,
        default_strategy: RotationStrategy = RotationStrategy.WEIGHTED,
        cooldown_seconds: float = 5.0,
        max_failures_before_exclude: int = 3,
    ) -> None:
        """
        Initialize rotating proxy provider.

        Args:
            providers: List of underlying proxy providers
            default_strategy: Default rotation strategy
            cooldown_seconds: Cooldown between uses of same proxy
            max_failures_before_exclude: Max failures before temporary exclusion
        """
        self._providers = providers or []
        self._default_strategy = default_strategy
        self._cooldown_seconds = cooldown_seconds
        self._max_failures = max_failures_before_exclude

        # State
        self._all_proxies: list[Proxy] = []
        self._health: dict[str, ProxyHealth] = {}
        self._last_used: dict[str, float] = {}
        self._usage_count: dict[str, int] = defaultdict(int)
        self._sticky_sessions: dict[str, Proxy] = {}
        self._excluded: set[str] = set()
        self._lock = asyncio.Lock()

    @property
    def total_proxies(self) -> int:
        return len(self._all_proxies)

    @property
    def healthy_proxies(self) -> int:
        return sum(1 for h in self._health.values() if h.is_healthy)

    async def initialize(self) -> None:
        """Initialize all underlying providers."""
        for provider in self._providers:
            await provider.initialize()

            async for proxy in provider.get_all():
                if proxy.id not in [p.id for p in self._all_proxies]:
                    self._all_proxies.append(proxy)
                    self._health[proxy.id] = ProxyHealth(proxy=proxy, is_healthy=True)

        logger.info("Rotating provider initialized", count=len(self._all_proxies))

    async def add_provider(self, provider: FileProxyProvider) -> None:
        """Add a new underlying provider."""
        await provider.initialize()
        self._providers.append(provider)

        async for proxy in provider.get_all():
            if proxy.id not in [p.id for p in self._all_proxies]:
                self._all_proxies.append(proxy)
                self._health[proxy.id] = ProxyHealth(proxy=proxy, is_healthy=True)

    async def get_proxy(
        self,
        *,
        strategy: RotationStrategy | None = None,
        country: str | None = None,
        proxy_type: str | None = None,
        sticky_session: str | None = None,
    ) -> Proxy:
        """Get a proxy based on strategy."""
        strategy = strategy or self._default_strategy

        # Handle sticky sessions
        if sticky_session and sticky_session in self._sticky_sessions:
            proxy = self._sticky_sessions[sticky_session]
            if self._is_available(proxy):
                return proxy
            # Session proxy unavailable, get a new one
            del self._sticky_sessions[sticky_session]

        async with self._lock:
            candidates = self._get_candidates(country, proxy_type)

            if not candidates:
                raise NoProxyAvailableError("No proxies available matching criteria")

            proxy = self._select_proxy(candidates, strategy)

            # Track usage
            self._last_used[proxy.id] = time.time()
            self._usage_count[proxy.id] += 1

            # Store sticky session
            if sticky_session:
                self._sticky_sessions[sticky_session] = proxy

            return proxy

    def _get_candidates(
        self,
        country: str | None,
        proxy_type: str | None,
    ) -> list[Proxy]:
        """Get candidate proxies matching filters."""
        now = time.time()

        candidates = []
        for proxy in self._all_proxies:
            # Skip excluded
            if proxy.id in self._excluded:
                continue

            # Check cooldown
            last_used = self._last_used.get(proxy.id, 0)
            if now - last_used < self._cooldown_seconds:
                continue

            # Check health
            health = self._health.get(proxy.id)
            if health and not health.is_healthy:
                continue

            # Apply filters
            if country and proxy.country != country:
                continue

            if proxy_type and proxy.category.value != proxy_type:
                continue

            candidates.append(proxy)

        return candidates

    def _select_proxy(
        self,
        candidates: list[Proxy],
        strategy: RotationStrategy,
    ) -> Proxy:
        """Select a proxy based on strategy."""
        if strategy == RotationStrategy.RANDOM:
            return random.choice(candidates)

        elif strategy == RotationStrategy.ROUND_ROBIN:
            # Select least recently used
            sorted_proxies = sorted(
                candidates,
                key=lambda p: self._last_used.get(p.id, 0),
            )
            return sorted_proxies[0]

        elif strategy == RotationStrategy.LEAST_USED:
            sorted_proxies = sorted(
                candidates,
                key=lambda p: self._usage_count.get(p.id, 0),
            )
            return sorted_proxies[0]

        elif strategy == RotationStrategy.FASTEST:
            sorted_proxies = sorted(
                candidates,
                key=lambda p: (
                    self._health.get(p.id).latency_ms
                    if self._health.get(p.id) and self._health.get(p.id).latency_ms
                    else float("inf")
                ),
            )
            return sorted_proxies[0]

        elif strategy == RotationStrategy.WEIGHTED:
            weights = []
            for p in candidates:
                health = self._health.get(p.id)
                base_weight = health.weight if health else 1.0

                # Penalize heavily used proxies
                usage = self._usage_count.get(p.id, 0)
                usage_penalty = max(0.1, 1.0 - (usage / 100))

                weight = base_weight * usage_penalty
                weights.append(max(0.01, weight))

            return random.choices(candidates, weights=weights, k=1)[0]

        else:
            return random.choice(candidates)

    def _is_available(self, proxy: Proxy) -> bool:
        """Check if a proxy is available for use."""
        if proxy.id in self._excluded:
            return False

        health = self._health.get(proxy.id)
        if health and not health.is_healthy:
            return False

        now = time.time()
        last_used = self._last_used.get(proxy.id, 0)
        if now - last_used < self._cooldown_seconds:
            return False

        return True

    async def mark_success(self, proxy: Proxy, latency_ms: float) -> None:
        """Mark proxy as successful."""
        async with self._lock:
            if proxy.id in self._health:
                self._health[proxy.id].mark_success(latency_ms)
            else:
                health = ProxyHealth(proxy=proxy, is_healthy=True)
                health.mark_success(latency_ms)
                self._health[proxy.id] = health

            # Remove from excluded if it was there
            self._excluded.discard(proxy.id)

    async def mark_failure(self, proxy: Proxy, error: str | None = None) -> None:
        """Mark proxy as failed."""
        async with self._lock:
            if proxy.id in self._health:
                self._health[proxy.id].mark_failure(error)

                # Check for exclusion
                if self._health[proxy.id].consecutive_failures >= self._max_failures:
                    self._excluded.add(proxy.id)
                    logger.warning(
                        "Proxy excluded",
                        proxy_id=proxy.id,
                        failures=self._health[proxy.id].consecutive_failures,
                    )
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
        results = []

        for provider in self._providers:
            provider_results = await provider.health_check(
                test_url=test_url,
                timeout=timeout,
                concurrent=concurrent,
            )
            results.extend(provider_results)

        # Update our health cache
        async with self._lock:
            for health in results:
                self._health[health.proxy.id] = health

                # Update exclusions
                if not health.is_healthy:
                    if health.consecutive_failures >= self._max_failures:
                        self._excluded.add(health.proxy.id)
                else:
                    self._excluded.discard(health.proxy.id)

        return results

    async def get_all(self) -> AsyncIterator[Proxy]:
        """Iterate over all proxies."""
        for proxy in self._all_proxies:
            yield proxy

    async def add_proxy(self, proxy: Proxy) -> None:
        """Add a proxy to the pool."""
        async with self._lock:
            if proxy.id not in [p.id for p in self._all_proxies]:
                self._all_proxies.append(proxy)
                self._health[proxy.id] = ProxyHealth(proxy=proxy, is_healthy=True)

    async def remove_proxy(self, proxy: Proxy) -> None:
        """Remove a proxy from the pool."""
        async with self._lock:
            self._all_proxies = [p for p in self._all_proxies if p.id != proxy.id]
            self._health.pop(proxy.id, None)
            self._last_used.pop(proxy.id, None)
            self._usage_count.pop(proxy.id, None)
            self._excluded.discard(proxy.id)

    async def refresh(self) -> None:
        """Refresh all providers."""
        for provider in self._providers:
            await provider.refresh()

        # Rebuild proxy list
        async with self._lock:
            self._all_proxies.clear()

            for provider in self._providers:
                async for proxy in provider.get_all():
                    if proxy.id not in [p.id for p in self._all_proxies]:
                        self._all_proxies.append(proxy)
                        if proxy.id not in self._health:
                            self._health[proxy.id] = ProxyHealth(proxy=proxy, is_healthy=True)

    async def close(self) -> None:
        """Clean up resources."""
        for provider in self._providers:
            await provider.close()

    def get_stats(self) -> dict:
        """Get provider statistics."""
        return {
            "total_proxies": len(self._all_proxies),
            "healthy_proxies": self.healthy_proxies,
            "excluded_proxies": len(self._excluded),
            "active_sessions": len(self._sticky_sessions),
            "strategy": self._default_strategy.value,
        }
