"""Intelligent rate limiting and proxy management.

Provides smart request throttling and proxy rotation based on:
- Response status codes (429, 503, etc.)
- Detection signals from page content
- Per-domain rate tracking
- Exponential backoff with jitter
- Proxy reputation scoring

Key Features:
- Automatic rate limit detection
- Adaptive backoff strategies
- Proxy health monitoring
- Geographic fingerprint matching
- Honeypot detection
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limit handling strategy."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    ADAPTIVE = "adaptive"


class ProxyHealth(str, Enum):
    """Proxy health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    BANNED = "banned"
    UNKNOWN = "unknown"


@dataclass
class RateLimitState:
    """Rate limit state for a domain."""

    domain: str
    request_count: int = 0
    last_request_time: float = 0.0
    backoff_until: float = 0.0
    consecutive_errors: int = 0
    rate_limit_hits: int = 0
    last_status_code: int = 200

    # Adaptive rate learning
    successful_requests: int = 0
    avg_response_time: float = 0.0
    estimated_rate_limit: float | None = None


@dataclass
class ProxyScore:
    """Proxy reputation score."""

    proxy_id: str
    health: ProxyHealth = ProxyHealth.UNKNOWN

    # Success metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Performance metrics
    avg_response_time: float = 0.0
    last_response_time: float = 0.0

    # Ban tracking per domain
    banned_domains: set[str] = field(default_factory=set)

    # Last check time
    last_check: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.5  # Unknown
        return self.successful_requests / self.total_requests

    @property
    def score(self) -> float:
        """Calculate overall proxy score (0-100)."""
        if self.health == ProxyHealth.BANNED:
            return 0.0
        if self.health == ProxyHealth.UNHEALTHY:
            return 10.0

        # Base score from success rate
        base_score = self.success_rate * 60

        # Response time penalty (slower = lower score)
        if self.avg_response_time > 0:
            time_penalty = min(20, self.avg_response_time / 500)
            base_score -= time_penalty

        # Freshness bonus
        time_since_check = time.time() - self.last_check
        if time_since_check < 300:  # Checked in last 5 min
            base_score += 10
        elif time_since_check < 900:  # Checked in last 15 min
            base_score += 5

        # Health bonus
        health_bonus = {
            ProxyHealth.HEALTHY: 20,
            ProxyHealth.DEGRADED: 5,
            ProxyHealth.UNKNOWN: 0,
        }
        base_score += health_bonus.get(self.health, 0)

        return max(0.0, min(100.0, base_score))


@dataclass
class RateLimiterConfig:
    """Rate limiter configuration."""

    # Base delay between requests (seconds)
    base_delay: float = 1.0

    # Maximum delay after backoff (seconds)
    max_delay: float = 60.0

    # Exponential backoff multiplier
    backoff_multiplier: float = 2.0

    # Jitter factor (0-1)
    jitter_factor: float = 0.3

    # Max consecutive errors before proxy ban
    max_consecutive_errors: int = 5

    # Rate limit detection status codes
    rate_limit_codes: list[int] = field(
        default_factory=lambda: [429, 503, 529, 520, 521, 522, 523, 524]
    )

    # Detection keywords in response
    detection_keywords: list[str] = field(
        default_factory=lambda: [
            "rate limit",
            "too many requests",
            "please wait",
            "blocked",
            "captcha",
            "access denied",
            "bot detected",
            "unusual traffic",
        ]
    )

    # Default strategy
    strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE


class RateLimiter:
    """Intelligent rate limiter with adaptive backoff.

    Monitors request patterns and automatically adjusts delays
    to avoid triggering rate limits while maximizing throughput.

    Usage:
        limiter = RateLimiter()

        # Before each request
        await limiter.wait_if_needed("example.com")

        # After request
        limiter.record_response("example.com", response.status_code, response.text)

        # Check if should rotate proxy
        if limiter.should_rotate_proxy("example.com"):
            proxy = get_new_proxy()
    """

    def __init__(self, config: RateLimiterConfig | None = None) -> None:
        """Initialize rate limiter.

        Args:
            config: Limiter configuration
        """
        self.config = config or RateLimiterConfig()
        self._domain_states: dict[str, RateLimitState] = {}
        self._proxy_scores: dict[str, ProxyScore] = {}
        self._lock = asyncio.Lock()

    def _get_domain_state(self, domain: str) -> RateLimitState:
        """Get or create domain state."""
        if domain not in self._domain_states:
            self._domain_states[domain] = RateLimitState(domain=domain)
        return self._domain_states[domain]

    def _get_proxy_score(self, proxy_id: str) -> ProxyScore:
        """Get or create proxy score."""
        if proxy_id not in self._proxy_scores:
            self._proxy_scores[proxy_id] = ProxyScore(proxy_id=proxy_id)
        return self._proxy_scores[proxy_id]

    async def wait_if_needed(self, domain: str) -> float:
        """Wait if rate limiting is active for domain.

        Args:
            domain: Target domain

        Returns:
            Actual wait time in seconds
        """
        async with self._lock:
            state = self._get_domain_state(domain)
            current_time = time.time()

            # Check if in backoff period
            if current_time < state.backoff_until:
                wait_time = state.backoff_until - current_time
                logger.debug(
                    "Rate limit backoff",
                    domain=domain,
                    wait_seconds=wait_time,
                )
                await asyncio.sleep(wait_time)
                return wait_time

            # Apply base delay with jitter
            time_since_last = current_time - state.last_request_time
            min_delay = self._calculate_delay(state)

            if time_since_last < min_delay:
                wait_time = min_delay - time_since_last
                jitter = wait_time * self.config.jitter_factor * random.random()
                wait_time += jitter
                await asyncio.sleep(wait_time)
                return wait_time

            return 0.0

    def _calculate_delay(self, state: RateLimitState) -> float:
        """Calculate appropriate delay based on state and strategy."""
        base = self.config.base_delay

        if self.config.strategy == RateLimitStrategy.FIXED_DELAY:
            return base

        if self.config.strategy == RateLimitStrategy.LINEAR_BACKOFF:
            return base * (1 + state.consecutive_errors * 0.5)

        if self.config.strategy == RateLimitStrategy.EXPONENTIAL_BACKOFF:
            if state.consecutive_errors > 0:
                return min(
                    self.config.max_delay,
                    base * (self.config.backoff_multiplier**state.consecutive_errors),
                )
            return base

        # Adaptive strategy
        if state.estimated_rate_limit:
            # Stay under estimated limit
            return max(base, 1.0 / state.estimated_rate_limit * 1.2)

        if state.rate_limit_hits > 0:
            # Increase delay based on rate limit history
            return base * (1 + state.rate_limit_hits * 0.3)

        return base

    def record_response(
        self,
        domain: str,
        status_code: int,
        response_text: str = "",
        response_time: float = 0.0,
        proxy_id: str | None = None,
    ) -> bool:
        """Record response and update rate limit state.

        Args:
            domain: Target domain
            status_code: HTTP status code
            response_text: Response body text
            response_time: Response time in seconds
            proxy_id: Proxy used (if any)

        Returns:
            True if rate limit detected
        """
        state = self._get_domain_state(domain)
        current_time = time.time()

        state.request_count += 1
        state.last_request_time = current_time
        state.last_status_code = status_code

        # Check for rate limit
        is_rate_limited = self._is_rate_limited(status_code, response_text)

        if is_rate_limited:
            state.consecutive_errors += 1
            state.rate_limit_hits += 1

            # Calculate backoff
            backoff_seconds = self._calculate_backoff(state)
            state.backoff_until = current_time + backoff_seconds

            logger.warning(
                "Rate limit detected",
                domain=domain,
                status_code=status_code,
                backoff_seconds=backoff_seconds,
            )

            # Update proxy score if applicable
            if proxy_id:
                self._record_proxy_failure(proxy_id, domain)

        elif status_code < 400:
            # Success - reset error count
            state.consecutive_errors = 0
            state.successful_requests += 1

            # Update response time average
            if state.avg_response_time == 0:
                state.avg_response_time = response_time
            else:
                state.avg_response_time = state.avg_response_time * 0.9 + response_time * 0.1

            # Update proxy score
            if proxy_id:
                self._record_proxy_success(proxy_id, response_time)

        else:
            # Other error
            state.consecutive_errors += 1
            if proxy_id:
                self._record_proxy_failure(proxy_id, domain)

        return is_rate_limited

    def _is_rate_limited(self, status_code: int, response_text: str) -> bool:
        """Check if response indicates rate limiting."""
        # Check status code
        if status_code in self.config.rate_limit_codes:
            return True

        # Check response text for detection keywords
        if response_text:
            text_lower = response_text.lower()
            for keyword in self.config.detection_keywords:
                if keyword in text_lower:
                    return True

        return False

    def _calculate_backoff(self, state: RateLimitState) -> float:
        """Calculate backoff duration."""
        base_backoff = self.config.base_delay * (
            self.config.backoff_multiplier ** min(state.consecutive_errors, 10)
        )

        # Add jitter
        jitter = base_backoff * self.config.jitter_factor * random.random()

        return min(self.config.max_delay, base_backoff + jitter)

    def _record_proxy_success(self, proxy_id: str, response_time: float) -> None:
        """Record successful proxy request."""
        score = self._get_proxy_score(proxy_id)
        score.total_requests += 1
        score.successful_requests += 1
        score.last_response_time = response_time
        score.last_check = time.time()

        # Update average response time
        if score.avg_response_time == 0:
            score.avg_response_time = response_time
        else:
            score.avg_response_time = score.avg_response_time * 0.9 + response_time * 0.1

        # Update health
        if score.success_rate > 0.9:
            score.health = ProxyHealth.HEALTHY
        elif score.success_rate > 0.7:
            score.health = ProxyHealth.DEGRADED

    def _record_proxy_failure(self, proxy_id: str, domain: str) -> None:
        """Record proxy failure."""
        score = self._get_proxy_score(proxy_id)
        score.total_requests += 1
        score.failed_requests += 1
        score.last_check = time.time()

        # Check if should mark as banned for this domain
        if score.failed_requests >= self.config.max_consecutive_errors:
            score.banned_domains.add(domain)

        # Update health
        if score.success_rate < 0.3:
            score.health = ProxyHealth.UNHEALTHY
        elif score.success_rate < 0.6:
            score.health = ProxyHealth.DEGRADED

    def should_rotate_proxy(
        self,
        domain: str,
        current_proxy_id: str | None = None,
    ) -> bool:
        """Check if proxy should be rotated.

        Args:
            domain: Target domain
            current_proxy_id: Current proxy ID

        Returns:
            True if rotation recommended
        """
        state = self._get_domain_state(domain)

        # Rotate after consecutive errors
        if state.consecutive_errors >= 3:
            return True

        # Check if current proxy is banned for domain
        if current_proxy_id:
            score = self._get_proxy_score(current_proxy_id)
            if domain in score.banned_domains:
                return True
            if score.health in [ProxyHealth.BANNED, ProxyHealth.UNHEALTHY]:
                return True

        return False

    def get_best_proxy(
        self,
        proxy_ids: list[str],
        domain: str | None = None,
    ) -> str | None:
        """Get best proxy from list based on scores.

        Args:
            proxy_ids: List of available proxy IDs
            domain: Target domain (filters out banned proxies)

        Returns:
            Best proxy ID or None
        """
        if not proxy_ids:
            return None

        # Filter and score proxies
        scored_proxies = []
        for proxy_id in proxy_ids:
            score = self._get_proxy_score(proxy_id)

            # Skip if banned for domain
            if domain and domain in score.banned_domains:
                continue

            # Skip unhealthy/banned
            if score.health in [ProxyHealth.BANNED, ProxyHealth.UNHEALTHY]:
                continue

            scored_proxies.append((proxy_id, score.score))

        if not scored_proxies:
            # All filtered, return random
            return random.choice(proxy_ids)

        # Sort by score (highest first)
        scored_proxies.sort(key=lambda x: x[1], reverse=True)

        # Weighted random selection from top proxies
        # Gives some variety while preferring high-scoring proxies
        top_count = min(5, len(scored_proxies))
        top_proxies = scored_proxies[:top_count]

        # Use scores as weights
        total_score = sum(s for _, s in top_proxies)
        if total_score == 0:
            return top_proxies[0][0]

        rand = random.random() * total_score
        cumulative = 0.0
        for proxy_id, score in top_proxies:
            cumulative += score
            if rand <= cumulative:
                return proxy_id

        return top_proxies[0][0]

    def reset_domain(self, domain: str) -> None:
        """Reset rate limit state for domain."""
        if domain in self._domain_states:
            del self._domain_states[domain]

    def reset_proxy(self, proxy_id: str) -> None:
        """Reset proxy score."""
        if proxy_id in self._proxy_scores:
            del self._proxy_scores[proxy_id]

    def get_domain_stats(self, domain: str) -> dict[str, Any]:
        """Get statistics for domain."""
        state = self._get_domain_state(domain)
        return {
            "domain": domain,
            "request_count": state.request_count,
            "successful_requests": state.successful_requests,
            "rate_limit_hits": state.rate_limit_hits,
            "consecutive_errors": state.consecutive_errors,
            "avg_response_time": state.avg_response_time,
            "in_backoff": time.time() < state.backoff_until,
        }

    def get_proxy_stats(self, proxy_id: str) -> dict[str, Any]:
        """Get statistics for proxy."""
        score = self._get_proxy_score(proxy_id)
        return {
            "proxy_id": proxy_id,
            "health": score.health.value,
            "score": score.score,
            "success_rate": score.success_rate,
            "total_requests": score.total_requests,
            "banned_domains": list(score.banned_domains),
        }


# Global rate limiter instance
_limiter: RateLimiter | None = None


def get_rate_limiter(config: RateLimiterConfig | None = None) -> RateLimiter:
    """Get or create global rate limiter.

    Args:
        config: Optional configuration

    Returns:
        RateLimiter instance
    """
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(config)
    return _limiter
