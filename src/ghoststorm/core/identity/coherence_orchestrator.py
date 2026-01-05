"""Enterprise-grade identity coherence orchestration.

Ensures all browser identity parameters are coherent:
- Proxy geolocation matches fingerprint timezone/locale
- HTTP headers match fingerprint (Accept-Language, Sec-CH-UA)
- Browser geolocation matches proxy region
- Timezone emulation matches fingerprint

Performance: <1ms identity creation with cached lookups.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ghoststorm.core.geo.geoip_service import GeoIPService
from ghoststorm.core.geo.locale_mapping import (
    get_coherent_locale_data,
    get_coherent_locale_from_locale,
)
from ghoststorm.core.models.fingerprint import (
    Fingerprint,
    GeolocationConfig,
    ScreenConfig,
)

if TYPE_CHECKING:
    from ghoststorm.core.models.proxy import Proxy

logger = logging.getLogger(__name__)


@dataclass
class CoherentIdentity:
    """Fully coherent browser identity.

    All parameters are validated to be consistent with each other,
    preventing detection from parameter mismatches.
    """

    # Core identity components
    fingerprint: Fingerprint
    proxy: Proxy | None

    # Derived coherent values
    timezone: str
    locale: str
    languages: list[str]
    accept_language: str
    geolocation: GeolocationConfig

    # HTTP headers to inject (Accept-Language, Sec-CH-UA, etc.)
    headers: dict[str, str] = field(default_factory=dict)

    # Validation metrics
    coherence_score: float = 1.0  # 0.0 to 1.0
    warnings: list[str] = field(default_factory=list)

    # Country info
    country_code: str = "US"
    country_name: str = "United States"

    @property
    def identity_hash(self) -> str:
        """Unique hash for this identity (for caching/tracking)."""
        data = f"{self.fingerprint.id}:{self.proxy.id if self.proxy else 'none'}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    @property
    def is_coherent(self) -> bool:
        """Check if identity passes coherence checks."""
        return self.coherence_score >= 0.7 and len(self.warnings) == 0

    def to_context_options(self) -> dict:
        """Convert to Playwright/Patchright context options."""
        options = {
            "user_agent": self.fingerprint.user_agent,
            "viewport": {
                "width": self.fingerprint.screen.width,
                "height": self.fingerprint.screen.height,
            },
            "locale": self.locale,
            "timezone_id": self.timezone,
            "geolocation": self.geolocation.to_dict(),
            "permissions": ["geolocation"],
            "extra_http_headers": self.headers,
        }

        # Add device scale factor if not 1.0
        if self.fingerprint.screen.device_scale_factor != 1.0:
            options["device_scale_factor"] = self.fingerprint.screen.device_scale_factor

        # Mobile settings
        if self.fingerprint.max_touch_points > 0:
            options["has_touch"] = True
            options["is_mobile"] = True

        return options


class IdentityCoherenceOrchestrator:
    """Ensures proxy + fingerprint + headers + browser are coherent.

    This is the central orchestrator that:
    1. Takes a proxy and fingerprint
    2. Resolves proxy geolocation via GeoIP
    3. Adapts fingerprint locale/timezone to match proxy
    4. Generates coherent HTTP headers
    5. Returns a fully validated CoherentIdentity

    Usage:
        orchestrator = IdentityCoherenceOrchestrator()
        identity = await orchestrator.create_coherent_identity(
            fingerprint=fingerprint,
            proxy=proxy,
            strict=True,
        )
        # Use identity.to_context_options() for browser context
    """

    _instance: IdentityCoherenceOrchestrator | None = None

    def __init__(self) -> None:
        """Initialize orchestrator with GeoIP service."""
        self._geoip = GeoIPService.get_instance()

    @classmethod
    def get_instance(cls) -> IdentityCoherenceOrchestrator:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def create_coherent_identity(
        self,
        fingerprint: Fingerprint,
        proxy: Proxy | None = None,
        strict: bool = True,
    ) -> CoherentIdentity:
        """Create fully coherent identity from fingerprint + proxy.

        Args:
            fingerprint: Base fingerprint to adapt
            proxy: Proxy to match (if any)
            strict: If True, modify fingerprint to match proxy geo.
                   If False, only warn on mismatches.

        Returns:
            CoherentIdentity with all parameters aligned
        """
        warnings: list[str] = []

        # Step 1: Resolve proxy geolocation
        # Priority: explicit proxy.country > GeoIP lookup > fallback
        proxy_country = None
        proxy_timezone = None
        proxy_coords = None

        if proxy:
            # First priority: explicit country field from proxy
            if proxy.country:
                proxy_country = proxy.country.upper()
                logger.debug(f"Using explicit proxy.country: {proxy_country}")

            # Second: try GeoIP lookup for timezone and coords
            if proxy.host:
                try:
                    geo = self._geoip.lookup(proxy.host)
                    if geo.is_valid:
                        # Use GeoIP country only if no explicit country set
                        if not proxy_country:
                            proxy_country = geo.country_code
                            logger.debug(
                                f"GeoIP resolved country: {proxy.host} -> {proxy_country}"
                            )
                        # Only use GeoIP timezone/coords if country matches
                        # (don't use US coords for a JP proxy)
                        geoip_country_matches = (
                            geo.country_code.upper() == proxy_country
                        )
                        if geoip_country_matches:
                            if geo.timezone:
                                proxy_timezone = geo.timezone
                            if geo.latitude and geo.longitude:
                                proxy_coords = (geo.latitude, geo.longitude)
                            logger.debug(
                                f"GeoIP matched: {geo.timezone}, "
                                f"({geo.latitude}, {geo.longitude})"
                            )
                except Exception as e:
                    logger.debug(f"GeoIP lookup failed for {proxy.host}: {e}")

        # Step 2: Get coherent locale data for country
        if proxy_country:
            locale_data = get_coherent_locale_data(proxy_country, proxy_timezone)
        else:
            # No proxy - use fingerprint's existing locale
            locale_data = get_coherent_locale_from_locale(fingerprint.locale)

        # Step 3: Adapt fingerprint if strict mode
        adapted_fingerprint = fingerprint
        if strict and proxy_country:
            adapted_fingerprint = self._adapt_fingerprint(
                fingerprint,
                timezone=locale_data.timezone,
                locale=locale_data.locale,
                languages=locale_data.languages,
            )
        else:
            # Check for mismatches and warn
            if fingerprint.timezone_id != locale_data.timezone:
                warnings.append(
                    f"Timezone mismatch: fingerprint={fingerprint.timezone_id}, "
                    f"expected={locale_data.timezone}"
                )
            if fingerprint.locale != locale_data.locale:
                warnings.append(
                    f"Locale mismatch: fingerprint={fingerprint.locale}, "
                    f"expected={locale_data.locale}"
                )

        # Step 4: Build HTTP headers
        headers = self._build_coherent_headers(
            fingerprint=adapted_fingerprint,
            locale=locale_data.locale,
            languages=locale_data.languages,
        )

        # Step 5: Build geolocation with jitter
        if proxy_coords:
            geolocation = GeolocationConfig(
                latitude=proxy_coords[0],
                longitude=proxy_coords[1],
                accuracy=100.0,
            ).with_jitter(meters=500)  # Add realistic jitter
        elif adapted_fingerprint.geolocation:
            geolocation = adapted_fingerprint.geolocation.with_jitter(meters=100)
        else:
            # Generate coords from locale data
            geolocation = GeolocationConfig.from_coords(
                latitude=locale_data.latitude,
                longitude=locale_data.longitude,
                accuracy=1000.0,  # City-level accuracy
                add_jitter=True,
                jitter_meters=5000,  # Larger jitter for city center
            )

        # Step 6: Calculate coherence score
        score = self._calculate_coherence_score(
            fingerprint=adapted_fingerprint,
            proxy=proxy,
            locale_data=locale_data,
            warnings=warnings,
        )

        return CoherentIdentity(
            fingerprint=adapted_fingerprint,
            proxy=proxy,
            timezone=locale_data.timezone,
            locale=locale_data.locale,
            languages=locale_data.languages,
            accept_language=locale_data.accept_language,
            geolocation=geolocation,
            headers=headers,
            coherence_score=score,
            warnings=warnings,
            country_code=locale_data.country_code,
            country_name=locale_data.country_name,
        )

    def _adapt_fingerprint(
        self,
        fp: Fingerprint,
        timezone: str,
        locale: str,
        languages: list[str],
    ) -> Fingerprint:
        """Create adapted fingerprint matching geo.

        Creates a new fingerprint with locale/timezone/languages
        adjusted to match the proxy's geolocation.
        """
        # Extract primary language from locale
        primary_language = languages[0].split("-")[0] if languages else "en"

        return Fingerprint(
            id=fp.id,
            user_agent=fp.user_agent,
            platform=fp.platform,
            vendor=fp.vendor,
            language=primary_language,
            languages=languages,
            hardware_concurrency=fp.hardware_concurrency,
            device_memory=fp.device_memory,
            max_touch_points=fp.max_touch_points,
            screen=fp.screen,
            webgl=fp.webgl,
            canvas_noise=fp.canvas_noise,
            timezone_id=timezone,
            locale=locale,
            geolocation=fp.geolocation,
            network=fp.network,
            fonts=fp.fonts,
            plugins=fp.plugins,
            battery_charging=fp.battery_charging,
            battery_level=fp.battery_level,
            battery_charging_time=fp.battery_charging_time,
            battery_discharging_time=fp.battery_discharging_time,
            audio_inputs=fp.audio_inputs,
            audio_outputs=fp.audio_outputs,
            video_inputs=fp.video_inputs,
        )

    def _build_coherent_headers(
        self,
        fingerprint: Fingerprint,
        locale: str,
        languages: list[str],
    ) -> dict[str, str]:
        """Build HTTP headers matching identity.

        Generates:
        - Accept-Language with proper quality values
        - Sec-CH-UA headers for Chrome browsers
        """
        headers: dict[str, str] = {}

        # Accept-Language with quality values
        accept_lang_parts = []
        for i, lang in enumerate(languages[:5]):
            if i == 0:
                accept_lang_parts.append(lang)
            else:
                q = max(0.5, round(0.9 - (i * 0.1), 1))
                accept_lang_parts.append(f"{lang};q={q}")

        headers["Accept-Language"] = ", ".join(accept_lang_parts)

        # Add Sec-CH-UA headers for Chrome
        if fingerprint.user_agent and "Chrome" in fingerprint.user_agent:
            match = re.search(r"Chrome/(\d+)", fingerprint.user_agent)
            if match:
                version = match.group(1)
                headers["Sec-CH-UA"] = (
                    f'"Chromium";v="{version}", '
                    f'"Google Chrome";v="{version}", '
                    f'"Not-A.Brand";v="99"'
                )
                headers["Sec-CH-UA-Mobile"] = (
                    "?1" if fingerprint.max_touch_points > 0 else "?0"
                )
                headers["Sec-CH-UA-Platform"] = (
                    f'"{self._get_platform_name(fingerprint.platform)}"'
                )

        return headers

    def _get_platform_name(self, platform: str) -> str:
        """Convert navigator.platform to Sec-CH-UA-Platform value."""
        platform_map = {
            "Win32": "Windows",
            "Win64": "Windows",
            "Windows": "Windows",
            "MacIntel": "macOS",
            "Macintosh": "macOS",
            "Linux x86_64": "Linux",
            "Linux": "Linux",
            "iPhone": "iOS",
            "iPad": "iOS",
            "Android": "Android",
        }
        return platform_map.get(platform, "Windows")

    def _calculate_coherence_score(
        self,
        fingerprint: Fingerprint,
        proxy: Proxy | None,
        locale_data,
        warnings: list[str],
    ) -> float:
        """Calculate identity coherence score (0.0 to 1.0).

        Higher score = more coherent = harder to detect.
        """
        score = 1.0

        # Deduct for each warning
        score -= len(warnings) * 0.15

        # Deduct if no proxy (less realistic for multi-geo)
        if not proxy:
            score -= 0.05

        # Deduct if datacenter proxy (easier to detect)
        if proxy:
            from ghoststorm.core.models.proxy import ProxyCategory

            if proxy.category == ProxyCategory.DATACENTER:
                score -= 0.2
            elif proxy.category == ProxyCategory.UNKNOWN:
                score -= 0.1

        # Bonus for residential/mobile proxy
        if proxy:
            from ghoststorm.core.models.proxy import ProxyCategory

            if proxy.category in (ProxyCategory.RESIDENTIAL, ProxyCategory.MOBILE):
                score += 0.05

        # Check timezone-locale consistency
        if fingerprint.timezone_id != locale_data.timezone:
            score -= 0.2

        # Check language consistency
        if fingerprint.locale != locale_data.locale:
            score -= 0.15

        return max(0.0, min(1.0, score))

    def validate_identity(self, identity: CoherentIdentity) -> list[str]:
        """Validate an existing identity for coherence issues.

        Returns list of validation errors/warnings.
        """
        issues = []

        # Check timezone-locale match
        expected_locale = get_coherent_locale_data(
            identity.country_code,
            identity.timezone,
        )

        if identity.locale != expected_locale.locale:
            issues.append(
                f"Locale {identity.locale} doesn't match country {identity.country_code}"
            )

        if identity.timezone != expected_locale.timezone:
            issues.append(
                f"Timezone {identity.timezone} unusual for {identity.country_code}"
            )

        # Check Accept-Language header
        if "Accept-Language" not in identity.headers:
            issues.append("Missing Accept-Language header")
        elif identity.locale not in identity.headers["Accept-Language"]:
            issues.append("Accept-Language doesn't contain locale")

        # Check geolocation is set
        if not identity.geolocation:
            issues.append("Missing geolocation")

        return issues


# Convenience function
def get_coherence_orchestrator() -> IdentityCoherenceOrchestrator:
    """Get the singleton coherence orchestrator instance."""
    return IdentityCoherenceOrchestrator.get_instance()
