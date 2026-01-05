"""Fast GeoIP lookup service using GeoIP2Fast.

Performance: 100,000+ lookups/sec with LRU caching.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeoLocation:
    """Resolved geolocation data from IP address."""

    country_code: str  # ISO 3166-1 alpha-2: "US", "JP", "DE"
    country_name: str  # Full name: "United States", "Japan"
    timezone: str | None  # IANA timezone: "America/New_York", "Asia/Tokyo"
    latitude: float | None  # Approximate center latitude
    longitude: float | None  # Approximate center longitude
    is_anonymous_proxy: bool = False
    is_satellite_provider: bool = False

    @property
    def is_valid(self) -> bool:
        """Check if geolocation has valid data."""
        return bool(self.country_code and self.country_code != "--")


class GeoIPService:
    """High-performance GeoIP resolution service.

    Uses GeoIP2Fast for blazing fast lookups (<0.00003s per lookup).
    Singleton pattern with LRU caching for maximum performance.
    """

    _instance: GeoIPService | None = None
    _initialized: bool = False

    def __new__(cls) -> GeoIPService:
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize GeoIP database."""
        if GeoIPService._initialized:
            return

        self._db = None
        self._fallback_mode = False

        try:
            import geoip2fast

            self._db = geoip2fast.GeoIP2Fast()
            logger.info("GeoIP2Fast database loaded successfully")
        except ImportError:
            logger.warning("geoip2fast not installed, using fallback country mapping")
            self._fallback_mode = True
        except Exception as e:
            logger.warning(f"Failed to load GeoIP database: {e}, using fallback")
            self._fallback_mode = True

        GeoIPService._initialized = True

    @classmethod
    def get_instance(cls) -> GeoIPService:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton for testing."""
        cls._instance = None
        cls._initialized = False
        cls.lookup_cached.cache_clear()

    @staticmethod
    @lru_cache(maxsize=50000)
    def lookup_cached(ip: str) -> GeoLocation:
        """Cached lookup - static for LRU cache compatibility."""
        service = GeoIPService.get_instance()
        return service._lookup_internal(ip)

    def lookup(self, ip: str) -> GeoLocation:
        """Look up geolocation for IP address.

        Args:
            ip: IPv4 or IPv6 address string

        Returns:
            GeoLocation with country, timezone, and coordinates
        """
        return self.lookup_cached(ip)

    def _lookup_internal(self, ip: str) -> GeoLocation:
        """Internal lookup implementation."""
        if self._fallback_mode or self._db is None:
            return self._fallback_lookup(ip)

        try:
            result = self._db.lookup(ip)

            # Handle different result formats from geoip2fast
            if result is None or (hasattr(result, "country_code") and result.country_code == "--"):
                return GeoLocation(
                    country_code="US",
                    country_name="United States",
                    timezone="America/New_York",
                    latitude=37.0902,
                    longitude=-95.7129,
                )

            return GeoLocation(
                country_code=getattr(result, "country_code", "US") or "US",
                country_name=getattr(result, "country_name", "United States") or "United States",
                timezone=getattr(result, "timezone", None),
                latitude=getattr(result, "latitude", None),
                longitude=getattr(result, "longitude", None),
                is_anonymous_proxy=getattr(result, "is_anonymous_proxy", False),
                is_satellite_provider=getattr(result, "is_satellite_provider", False),
            )
        except Exception as e:
            logger.debug(f"GeoIP lookup failed for {ip}: {e}")
            return self._fallback_lookup(ip)

    def _fallback_lookup(self, ip: str) -> GeoLocation:
        """Fallback when GeoIP database unavailable."""
        # Default to US for fallback
        return GeoLocation(
            country_code="US",
            country_name="United States",
            timezone="America/New_York",
            latitude=37.0902,
            longitude=-95.7129,
        )

    def lookup_batch(self, ips: list[str]) -> dict[str, GeoLocation]:
        """Batch lookup multiple IPs efficiently.

        Args:
            ips: List of IP addresses

        Returns:
            Dict mapping IP to GeoLocation
        """
        return {ip: self.lookup(ip) for ip in ips}

    @property
    def is_available(self) -> bool:
        """Check if GeoIP database is loaded."""
        return self._db is not None and not self._fallback_mode

    @property
    def cache_info(self) -> dict:
        """Get cache statistics."""
        info = self.lookup_cached.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "size": info.currsize,
            "maxsize": info.maxsize,
        }
