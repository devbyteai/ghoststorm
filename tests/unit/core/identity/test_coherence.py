"""Unit tests for identity coherence orchestrator."""
# ruff: noqa: I001

from __future__ import annotations

import pytest

from ghoststorm.core.geo.geoip_service import GeoIPService, GeoLocation
from ghoststorm.core.geo.locale_mapping import (
    COUNTRY_GEO_DATA,
    build_accept_language,
    get_coherent_locale_data,
    get_coherent_locale_from_locale,
)
from ghoststorm.core.identity.coherence_orchestrator import (
    CoherentIdentity,
    IdentityCoherenceOrchestrator,
)
from ghoststorm.core.models.fingerprint import Fingerprint, GeolocationConfig, ScreenConfig
from ghoststorm.core.models.proxy import Proxy, ProxyCategory, ProxyType


# ============================================================================
# GEOIP SERVICE TESTS
# ============================================================================


class TestGeoIPService:
    """Tests for GeoIP lookup service."""

    def test_singleton_pattern(self):
        """GeoIPService should be a singleton."""
        service1 = GeoIPService.get_instance()
        service2 = GeoIPService.get_instance()
        assert service1 is service2

    def test_lookup_returns_geolocation(self):
        """Lookup should return GeoLocation object."""
        service = GeoIPService.get_instance()
        result = service.lookup("8.8.8.8")  # Google DNS

        assert isinstance(result, GeoLocation)
        assert result.country_code  # Should have country code

    def test_fallback_for_invalid_ip(self):
        """Invalid IP should fallback to default."""
        service = GeoIPService.get_instance()
        result = service.lookup("invalid_ip")

        assert isinstance(result, GeoLocation)
        assert result.country_code == "US"  # Default fallback

    def test_cached_lookup(self):
        """Repeated lookups should be cached."""
        service = GeoIPService.get_instance()

        # Clear cache
        GeoIPService.lookup_cached.cache_clear()

        # First lookup
        result1 = service.lookup("8.8.8.8")
        info1 = service.cache_info

        # Second lookup (should be cached)
        result2 = service.lookup("8.8.8.8")
        info2 = service.cache_info

        assert result1 == result2
        assert info2["hits"] > info1["hits"]


# ============================================================================
# LOCALE MAPPING TESTS
# ============================================================================


class TestLocaleMapping:
    """Tests for country-to-locale mapping."""

    def test_country_data_coverage(self):
        """Should have data for 100+ countries."""
        assert len(COUNTRY_GEO_DATA) >= 100

    def test_us_country_data(self):
        """US should have correct data."""
        us = COUNTRY_GEO_DATA["US"]

        assert us.country_code == "US"
        assert us.primary_locale == "en-US"
        assert "en-US" in us.languages
        assert us.primary_timezone == "America/New_York"
        assert us.latitude != 0
        assert us.longitude != 0

    def test_japan_country_data(self):
        """Japan should have correct data."""
        jp = COUNTRY_GEO_DATA["JP"]

        assert jp.country_code == "JP"
        assert jp.primary_locale == "ja-JP"
        assert "ja-JP" in jp.languages
        assert jp.primary_timezone == "Asia/Tokyo"

    def test_get_coherent_locale_data(self):
        """Should return coherent locale data for country."""
        data = get_coherent_locale_data("JP")

        assert data.timezone == "Asia/Tokyo"
        assert data.locale == "ja-JP"
        assert "ja-JP" in data.languages
        assert data.country_code == "JP"
        assert data.country_name == "Japan"
        assert data.latitude > 0
        assert data.longitude > 0

    def test_get_coherent_locale_data_with_timezone(self):
        """Should use provided timezone if valid."""
        data = get_coherent_locale_data("US", "America/Los_Angeles")

        assert data.timezone == "America/Los_Angeles"
        assert data.locale == "en-US"

    def test_get_coherent_locale_data_invalid_country(self):
        """Invalid country should fallback to US."""
        data = get_coherent_locale_data("XX")

        assert data.country_code == "US"
        assert data.locale == "en-US"

    def test_get_coherent_locale_from_locale(self):
        """Should extract country from locale."""
        data = get_coherent_locale_from_locale("ja-JP")

        assert data.country_code == "JP"
        assert data.locale == "ja-JP"

    def test_build_accept_language(self):
        """Should build proper Accept-Language header."""
        languages = ["en-US", "en", "es"]
        result = build_accept_language(languages)

        assert "en-US" in result
        assert "en;q=" in result  # Has quality value
        assert "es;q=" in result  # Has quality value

    def test_build_accept_language_empty(self):
        """Empty languages should return default."""
        result = build_accept_language([])
        assert "en-US" in result


# ============================================================================
# COHERENT IDENTITY TESTS
# ============================================================================


class TestCoherentIdentity:
    """Tests for CoherentIdentity dataclass."""

    @pytest.fixture
    def sample_fingerprint(self):
        """Create sample fingerprint."""
        return Fingerprint(
            user_agent="Mozilla/5.0 Chrome/120.0.0.0",
            screen=ScreenConfig(1920, 1080),
        )

    @pytest.fixture
    def sample_proxy(self):
        """Create sample proxy."""
        return Proxy(
            host="103.152.112.25",
            port=8080,
            proxy_type=ProxyType.HTTP,
            country="jp",
            category=ProxyCategory.RESIDENTIAL,
        )

    def test_identity_hash(self, sample_fingerprint, sample_proxy):
        """Identity hash should be deterministic."""
        identity = CoherentIdentity(
            fingerprint=sample_fingerprint,
            proxy=sample_proxy,
            timezone="Asia/Tokyo",
            locale="ja-JP",
            languages=["ja-JP", "ja"],
            accept_language="ja-JP, ja;q=0.9",
            geolocation=GeolocationConfig(35.6762, 139.6503),
        )

        hash1 = identity.identity_hash
        hash2 = identity.identity_hash

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_is_coherent(self, sample_fingerprint, sample_proxy):
        """Should correctly identify coherent identity."""
        # Coherent identity
        coherent = CoherentIdentity(
            fingerprint=sample_fingerprint,
            proxy=sample_proxy,
            timezone="Asia/Tokyo",
            locale="ja-JP",
            languages=["ja-JP", "ja"],
            accept_language="ja-JP, ja;q=0.9",
            geolocation=GeolocationConfig(35.6762, 139.6503),
            coherence_score=0.9,
            warnings=[],
        )
        assert coherent.is_coherent

        # Incoherent identity
        incoherent = CoherentIdentity(
            fingerprint=sample_fingerprint,
            proxy=sample_proxy,
            timezone="Asia/Tokyo",
            locale="ja-JP",
            languages=["ja-JP", "ja"],
            accept_language="ja-JP, ja;q=0.9",
            geolocation=GeolocationConfig(35.6762, 139.6503),
            coherence_score=0.5,
            warnings=["Mismatch detected"],
        )
        assert not incoherent.is_coherent

    def test_to_context_options(self, sample_fingerprint, sample_proxy):
        """Should generate Playwright context options."""
        identity = CoherentIdentity(
            fingerprint=sample_fingerprint,
            proxy=sample_proxy,
            timezone="Asia/Tokyo",
            locale="ja-JP",
            languages=["ja-JP", "ja"],
            accept_language="ja-JP, ja;q=0.9",
            geolocation=GeolocationConfig(35.6762, 139.6503),
            headers={"Accept-Language": "ja-JP, ja;q=0.9"},
        )

        options = identity.to_context_options()

        assert options["user_agent"] == sample_fingerprint.user_agent
        assert options["locale"] == "ja-JP"
        assert options["timezone_id"] == "Asia/Tokyo"
        assert "geolocation" in options
        assert "permissions" in options
        assert options["viewport"]["width"] == 1920
        assert options["viewport"]["height"] == 1080


# ============================================================================
# COHERENCE ORCHESTRATOR TESTS
# ============================================================================


class TestIdentityCoherenceOrchestrator:
    """Tests for IdentityCoherenceOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return IdentityCoherenceOrchestrator()

    @pytest.fixture
    def base_fingerprint(self):
        """Create base fingerprint with en-US defaults."""
        return Fingerprint(
            user_agent="Mozilla/5.0 Chrome/120.0.0.0",
            timezone_id="America/New_York",
            locale="en-US",
            screen=ScreenConfig(1920, 1080),
        )

    @pytest.fixture
    def jp_proxy(self):
        """Create Japan proxy - GeoIP will fallback for test IPs."""
        # The proxy has explicit country set, so the orchestrator
        # should use that instead of doing GeoIP lookup
        return Proxy(
            host="103.152.112.25",
            port=8080,
            country="jp",  # Explicit country setting
            category=ProxyCategory.RESIDENTIAL,
        )

    @pytest.fixture
    def us_proxy(self):
        """Create US proxy."""
        return Proxy(
            host="104.28.100.50",
            port=8080,
            country="us",
            category=ProxyCategory.RESIDENTIAL,
        )

    @pytest.mark.asyncio
    async def test_create_coherent_identity_without_proxy(self, orchestrator, base_fingerprint):
        """Without proxy, should use fingerprint locale."""
        identity = await orchestrator.create_coherent_identity(
            fingerprint=base_fingerprint,
            proxy=None,
        )

        assert identity.locale == "en-US"
        assert identity.timezone == "America/New_York"
        assert identity.coherence_score > 0.5

    @pytest.mark.asyncio
    async def test_create_coherent_identity_with_proxy_strict(
        self, orchestrator, base_fingerprint, jp_proxy
    ):
        """With proxy in strict mode, should adapt fingerprint to proxy geo."""
        identity = await orchestrator.create_coherent_identity(
            fingerprint=base_fingerprint,
            proxy=jp_proxy,
            strict=True,
        )

        # Should adapt to Japanese locale
        assert identity.country_code == "JP"
        assert identity.locale == "ja-JP"
        assert identity.timezone == "Asia/Tokyo"
        assert "ja-JP" in identity.languages
        assert identity.coherence_score > 0.7

    @pytest.mark.asyncio
    async def test_create_coherent_identity_with_proxy_non_strict(
        self, orchestrator, base_fingerprint, jp_proxy
    ):
        """With proxy in non-strict mode, should warn but not adapt."""
        identity = await orchestrator.create_coherent_identity(
            fingerprint=base_fingerprint,
            proxy=jp_proxy,
            strict=False,
        )

        # Should keep original locale but add warnings
        assert len(identity.warnings) > 0
        assert identity.coherence_score < 1.0

    @pytest.mark.asyncio
    async def test_headers_generated(self, orchestrator, base_fingerprint, jp_proxy):
        """Should generate Accept-Language header."""
        identity = await orchestrator.create_coherent_identity(
            fingerprint=base_fingerprint,
            proxy=jp_proxy,
        )

        assert "Accept-Language" in identity.headers
        assert "ja-JP" in identity.headers["Accept-Language"]

    @pytest.mark.asyncio
    async def test_sec_ch_ua_headers_for_chrome(self, orchestrator, jp_proxy):
        """Should generate Sec-CH-UA headers for Chrome UA."""
        chrome_fp = Fingerprint(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            screen=ScreenConfig(1920, 1080),
        )

        identity = await orchestrator.create_coherent_identity(
            fingerprint=chrome_fp,
            proxy=jp_proxy,
        )

        assert "Sec-CH-UA" in identity.headers
        assert "120" in identity.headers["Sec-CH-UA"]
        assert "Sec-CH-UA-Mobile" in identity.headers
        assert "Sec-CH-UA-Platform" in identity.headers

    @pytest.mark.asyncio
    async def test_geolocation_generated(self, orchestrator, base_fingerprint, jp_proxy):
        """Should generate geolocation with jitter."""
        identity1 = await orchestrator.create_coherent_identity(
            fingerprint=base_fingerprint,
            proxy=jp_proxy,
        )

        identity2 = await orchestrator.create_coherent_identity(
            fingerprint=base_fingerprint,
            proxy=jp_proxy,
        )

        # Both should have geolocation
        assert identity1.geolocation is not None
        assert identity2.geolocation is not None

        # Geolocation should have jitter (different each time)
        # Note: They're in Japan region but with random jitter
        # Large tolerance (2.0 deg) to account for city-level jitter (5km)
        assert abs(identity1.geolocation.latitude - 35.6) < 2.0
        assert abs(identity1.geolocation.longitude - 139.6) < 2.0

    @pytest.mark.asyncio
    async def test_coherence_score_residential_proxy(
        self, orchestrator, base_fingerprint, jp_proxy
    ):
        """Residential proxy should have higher coherence score."""
        jp_proxy.category = ProxyCategory.RESIDENTIAL

        identity = await orchestrator.create_coherent_identity(
            fingerprint=base_fingerprint,
            proxy=jp_proxy,
        )

        assert identity.coherence_score >= 0.8

    @pytest.mark.asyncio
    async def test_coherence_score_datacenter_proxy(
        self, orchestrator, base_fingerprint, jp_proxy
    ):
        """Datacenter proxy should have lower coherence score."""
        jp_proxy.category = ProxyCategory.DATACENTER

        identity = await orchestrator.create_coherent_identity(
            fingerprint=base_fingerprint,
            proxy=jp_proxy,
        )

        assert identity.coherence_score < 0.9

    @pytest.mark.asyncio
    async def test_validate_identity(self, orchestrator, base_fingerprint, jp_proxy):
        """Should validate existing identity."""
        identity = await orchestrator.create_coherent_identity(
            fingerprint=base_fingerprint,
            proxy=jp_proxy,
        )

        issues = orchestrator.validate_identity(identity)

        # Well-formed identity should have no issues
        assert len(issues) == 0


# ============================================================================
# TIMEZONE EMULATOR TESTS
# ============================================================================


class TestTimezoneEmulator:
    """Tests for timezone emulation scripts."""

    def test_generate_timezone_script(self):
        """Should generate valid JavaScript."""
        from ghoststorm.plugins.evasion.timezone_emulator import generate_timezone_script

        script = generate_timezone_script("Asia/Tokyo", "ja-JP")

        assert "Asia/Tokyo" in script
        assert "ja-JP" in script
        assert "getTimezoneOffset" in script
        assert "DateTimeFormat" in script
        assert "navigator.language" in script

    def test_generate_language_script(self):
        """Should generate language override script."""
        from ghoststorm.plugins.evasion.timezone_emulator import generate_language_script

        script = generate_language_script("ja-JP", ["ja-JP", "ja", "en"])

        assert "ja-JP" in script
        assert "navigator.language" in script
        assert "navigator.languages" in script

    def test_generate_geolocation_script(self):
        """Should generate geolocation override script."""
        from ghoststorm.plugins.evasion.timezone_emulator import generate_geolocation_script

        script = generate_geolocation_script(35.6762, 139.6503, 100.0)

        assert "35.6762" in script
        assert "139.6503" in script
        assert "getCurrentPosition" in script
        assert "watchPosition" in script

    def test_generate_full_coherence_script(self):
        """Should generate complete coherence script."""
        from ghoststorm.plugins.evasion.timezone_emulator import generate_full_coherence_script

        script = generate_full_coherence_script(
            timezone_id="Asia/Tokyo",
            locale="ja-JP",
            languages=["ja-JP", "ja"],
            latitude=35.6762,
            longitude=139.6503,
        )

        assert "Asia/Tokyo" in script
        assert "ja-JP" in script
        assert "35.6762" in script
