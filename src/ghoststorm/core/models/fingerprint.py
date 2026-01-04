"""Fingerprint and device profile data models."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

# Timezone to compatible locale mapping for realistic fingerprints
# An obvious mismatch (e.g., Asia/Tokyo + en-US) reveals fake fingerprints
TIMEZONE_LOCALE_MAP: dict[str, list[str]] = {
    # Americas
    "America/New_York": ["en-US", "en"],
    "America/Chicago": ["en-US", "en"],
    "America/Denver": ["en-US", "en"],
    "America/Los_Angeles": ["en-US", "en"],
    "America/Anchorage": ["en-US", "en"],
    "America/Toronto": ["en-CA", "en-US", "en", "fr-CA"],
    "America/Vancouver": ["en-CA", "en-US", "en"],
    "America/Mexico_City": ["es-MX", "es"],
    "America/Sao_Paulo": ["pt-BR", "pt"],
    "America/Buenos_Aires": ["es-AR", "es"],
    # Europe
    "Europe/London": ["en-GB", "en"],
    "Europe/Paris": ["fr-FR", "fr"],
    "Europe/Berlin": ["de-DE", "de"],
    "Europe/Madrid": ["es-ES", "es"],
    "Europe/Rome": ["it-IT", "it"],
    "Europe/Amsterdam": ["nl-NL", "nl"],
    "Europe/Brussels": ["nl-BE", "fr-BE", "nl", "fr"],
    "Europe/Zurich": ["de-CH", "fr-CH", "it-CH", "de", "fr"],
    "Europe/Vienna": ["de-AT", "de"],
    "Europe/Warsaw": ["pl-PL", "pl"],
    "Europe/Prague": ["cs-CZ", "cs"],
    "Europe/Stockholm": ["sv-SE", "sv"],
    "Europe/Oslo": ["nb-NO", "no"],
    "Europe/Copenhagen": ["da-DK", "da"],
    "Europe/Helsinki": ["fi-FI", "fi"],
    "Europe/Moscow": ["ru-RU", "ru"],
    "Europe/Kiev": ["uk-UA", "uk", "ru-UA"],
    "Europe/Istanbul": ["tr-TR", "tr"],
    "Europe/Athens": ["el-GR", "el"],
    "Europe/Lisbon": ["pt-PT", "pt"],
    "Europe/Dublin": ["en-IE", "en"],
    # Asia
    "Asia/Tokyo": ["ja-JP", "ja"],
    "Asia/Seoul": ["ko-KR", "ko"],
    "Asia/Shanghai": ["zh-CN", "zh"],
    "Asia/Hong_Kong": ["zh-HK", "zh-TW", "en-HK", "zh"],
    "Asia/Taipei": ["zh-TW", "zh"],
    "Asia/Singapore": ["en-SG", "zh-SG", "en", "zh"],
    "Asia/Bangkok": ["th-TH", "th"],
    "Asia/Ho_Chi_Minh": ["vi-VN", "vi"],
    "Asia/Jakarta": ["id-ID", "id"],
    "Asia/Manila": ["en-PH", "fil-PH", "en"],
    "Asia/Kolkata": ["hi-IN", "en-IN", "en"],
    "Asia/Dubai": ["ar-AE", "en-AE", "ar", "en"],
    "Asia/Tel_Aviv": ["he-IL", "he", "en-IL"],
    # Oceania
    "Australia/Sydney": ["en-AU", "en"],
    "Australia/Melbourne": ["en-AU", "en"],
    "Australia/Brisbane": ["en-AU", "en"],
    "Australia/Perth": ["en-AU", "en"],
    "Pacific/Auckland": ["en-NZ", "en"],
    # Africa
    "Africa/Johannesburg": ["en-ZA", "af-ZA", "en"],
    "Africa/Cairo": ["ar-EG", "ar"],
    "Africa/Lagos": ["en-NG", "en"],
    "Africa/Nairobi": ["en-KE", "sw-KE", "en"],
}


def validate_timezone_locale(timezone_id: str, locale: str) -> bool:
    """Check if timezone and locale are a realistic combination.

    Args:
        timezone_id: IANA timezone identifier (e.g., "America/New_York")
        locale: BCP 47 locale code (e.g., "en-US")

    Returns:
        True if the combination is realistic, False if obviously fake
    """
    # Get compatible locales for this timezone
    compatible_locales = TIMEZONE_LOCALE_MAP.get(timezone_id)

    if compatible_locales is None:
        # Unknown timezone - check region prefix as fallback
        for tz_prefix, locales in TIMEZONE_LOCALE_MAP.items():
            region = tz_prefix.split("/")[0]
            if timezone_id.startswith(region + "/"):
                # Same region, accept similar language
                locale_lang = locale.split("-")[0]
                for compat_locale in locales:
                    if compat_locale.startswith(locale_lang):
                        return True
        # Can't validate - accept it
        return True

    # Check if locale matches any compatible locale
    locale_lang = locale.split("-")[0]
    for compat_locale in compatible_locales:
        if locale == compat_locale or locale_lang == compat_locale.split("-")[0]:
            return True

    return False


def get_compatible_locale(timezone_id: str) -> str:
    """Get a compatible locale for a given timezone.

    Args:
        timezone_id: IANA timezone identifier

    Returns:
        A locale that matches the timezone region
    """
    compatible_locales = TIMEZONE_LOCALE_MAP.get(timezone_id)
    if compatible_locales:
        return compatible_locales[0]

    # Fallback based on region
    region = timezone_id.split("/")[0] if "/" in timezone_id else ""
    region_defaults = {
        "America": "en-US",
        "Europe": "en-GB",
        "Asia": "en-US",
        "Australia": "en-AU",
        "Pacific": "en-US",
        "Africa": "en-US",
    }
    return region_defaults.get(region, "en-US")


@dataclass
class ScreenConfig:
    """Screen/viewport configuration."""

    width: int
    height: int
    device_scale_factor: float = 1.0
    color_depth: int = 24
    pixel_depth: int = 24
    available_width: int | None = None
    available_height: int | None = None

    def __post_init__(self) -> None:
        """Set defaults for available dimensions."""
        if self.available_width is None:
            self.available_width = self.width
        if self.available_height is None:
            self.available_height = self.height - 40  # Account for taskbar

    def to_viewport(self) -> dict[str, Any]:
        """Convert to Playwright viewport format."""
        return {
            "width": self.width,
            "height": self.height,
            "deviceScaleFactor": self.device_scale_factor,
        }


@dataclass
class WebGLConfig:
    """WebGL fingerprint configuration."""

    vendor: str = "Google Inc. (NVIDIA)"
    renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0)"
    unmasked_vendor: str | None = None
    unmasked_renderer: str | None = None

    def __post_init__(self) -> None:
        """Set defaults."""
        if self.unmasked_vendor is None:
            self.unmasked_vendor = self.vendor
        if self.unmasked_renderer is None:
            self.unmasked_renderer = self.renderer


@dataclass
class GeolocationConfig:
    """Geolocation configuration."""

    latitude: float
    longitude: float
    accuracy: float = 100.0
    altitude: float | None = None
    altitude_accuracy: float | None = None
    heading: float | None = None
    speed: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Playwright geolocation format."""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
        }

    def with_jitter(self, meters: float = 50.0) -> GeolocationConfig:
        """Create a new GeolocationConfig with random coordinate jitter.

        Adds realistic variation to prevent static coordinate detection.
        Same exact coordinates every time is a fingerprinting signal.

        Args:
            meters: Maximum jitter distance in meters (default 50m)

        Returns:
            New GeolocationConfig with slightly offset coordinates
        """
        # Convert meters to approximate degrees
        # At equator: 1 degree ≈ 111,320 meters
        # This is approximate but good enough for jitter
        degree_jitter = meters / 111320.0

        jitter_lat = random.uniform(-degree_jitter, degree_jitter)
        jitter_lon = random.uniform(-degree_jitter, degree_jitter)

        # Also vary accuracy slightly (real devices don't report exact same accuracy)
        accuracy_jitter = random.uniform(0.8, 1.2)

        return GeolocationConfig(
            latitude=self.latitude + jitter_lat,
            longitude=self.longitude + jitter_lon,
            accuracy=self.accuracy * accuracy_jitter,
            altitude=self.altitude,
            altitude_accuracy=self.altitude_accuracy,
            heading=self.heading,
            speed=self.speed,
        )

    @classmethod
    def from_coords(
        cls,
        latitude: float,
        longitude: float,
        *,
        accuracy: float = 100.0,
        add_jitter: bool = True,
        jitter_meters: float = 50.0,
    ) -> GeolocationConfig:
        """Create GeolocationConfig from coordinates with optional jitter.

        Args:
            latitude: Base latitude
            longitude: Base longitude
            accuracy: GPS accuracy in meters
            add_jitter: Whether to add random jitter (recommended)
            jitter_meters: Maximum jitter distance

        Returns:
            GeolocationConfig with realistic coordinates
        """
        config = cls(latitude=latitude, longitude=longitude, accuracy=accuracy)
        if add_jitter:
            return config.with_jitter(jitter_meters)
        return config


@dataclass
class CanvasNoiseConfig:
    """Canvas fingerprint noise configuration."""

    enabled: bool = True
    noise_r: float = 0.1
    noise_g: float = 0.1
    noise_b: float = 0.1
    noise_a: float = 0.0


@dataclass
class NetworkConfig:
    """Network conditions configuration."""

    connection_type: str = "wifi"  # wifi, 4g, 3g, 2g, ethernet
    effective_type: str = "4g"
    downlink: float = 10.0  # Mbps
    rtt: int = 50  # Round-trip time in ms
    save_data: bool = False


@dataclass
class Fingerprint:
    """Complete browser fingerprint."""

    id: str = field(default_factory=lambda: str(uuid4()))

    # Navigator properties
    user_agent: str = ""
    platform: str = "Win32"
    vendor: str = "Google Inc."
    language: str = "en-US"
    languages: list[str] = field(default_factory=lambda: ["en-US", "en"])
    hardware_concurrency: int = 8
    device_memory: int = 8
    max_touch_points: int = 0

    # Screen
    screen: ScreenConfig = field(default_factory=lambda: ScreenConfig(1920, 1080))

    # WebGL
    webgl: WebGLConfig = field(default_factory=WebGLConfig)

    # Canvas noise
    canvas_noise: CanvasNoiseConfig = field(default_factory=CanvasNoiseConfig)

    # Timezone and locale
    timezone_id: str = "America/New_York"
    locale: str = "en-US"

    # Geolocation
    geolocation: GeolocationConfig | None = None

    # Network
    network: NetworkConfig = field(default_factory=NetworkConfig)

    # Fonts (subset to expose)
    fonts: list[str] = field(
        default_factory=lambda: [
            "Arial",
            "Arial Black",
            "Calibri",
            "Cambria",
            "Comic Sans MS",
            "Consolas",
            "Courier New",
            "Georgia",
            "Impact",
            "Lucida Console",
            "Segoe UI",
            "Tahoma",
            "Times New Roman",
            "Trebuchet MS",
            "Verdana",
        ]
    )

    # Plugins (empty for modern browsers)
    plugins: list[dict[str, str]] = field(default_factory=list)

    # Battery
    battery_charging: bool = True
    battery_level: float = 0.85
    battery_charging_time: int = 0
    battery_discharging_time: int = float("inf")  # type: ignore

    # Media devices
    audio_inputs: int = 1
    audio_outputs: int = 2
    video_inputs: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for injection."""
        return {
            "id": self.id,
            "navigator": {
                "userAgent": self.user_agent,
                "platform": self.platform,
                "vendor": self.vendor,
                "language": self.language,
                "languages": self.languages,
                "hardwareConcurrency": self.hardware_concurrency,
                "deviceMemory": self.device_memory,
                "maxTouchPoints": self.max_touch_points,
            },
            "screen": {
                "width": self.screen.width,
                "height": self.screen.height,
                "availWidth": self.screen.available_width,
                "availHeight": self.screen.available_height,
                "colorDepth": self.screen.color_depth,
                "pixelDepth": self.screen.pixel_depth,
                "devicePixelRatio": self.screen.device_scale_factor,
            },
            "webgl": {
                "vendor": self.webgl.vendor,
                "renderer": self.webgl.renderer,
                "unmaskedVendor": self.webgl.unmasked_vendor,
                "unmaskedRenderer": self.webgl.unmasked_renderer,
            },
            "canvas": {
                "noiseEnabled": self.canvas_noise.enabled,
                "noiseR": self.canvas_noise.noise_r,
                "noiseG": self.canvas_noise.noise_g,
                "noiseB": self.canvas_noise.noise_b,
                "noiseA": self.canvas_noise.noise_a,
            },
            "timezone": self.timezone_id,
            "locale": self.locale,
            "fonts": self.fonts,
            "plugins": self.plugins,
            "battery": {
                "charging": self.battery_charging,
                "level": self.battery_level,
                "chargingTime": self.battery_charging_time,
                "dischargingTime": self.battery_discharging_time,
            },
            "mediaDevices": {
                "audioInputs": self.audio_inputs,
                "audioOutputs": self.audio_outputs,
                "videoInputs": self.video_inputs,
            },
            "network": {
                "type": self.network.connection_type,
                "effectiveType": self.network.effective_type,
                "downlink": self.network.downlink,
                "rtt": self.network.rtt,
                "saveData": self.network.save_data,
            },
        }


@dataclass
class FingerprintConstraints:
    """Constraints for fingerprint generation."""

    browsers: list[str] | None = None  # chrome, firefox, safari, edge
    os_list: list[str] | None = None  # windows, macos, linux, android, ios
    device_types: list[str] | None = None  # desktop, mobile, tablet
    min_screen_width: int | None = None
    max_screen_width: int | None = None
    locales: list[str] | None = None
    countries: list[str] | None = None


@dataclass
class DeviceProfile:
    """Pre-defined device profile."""

    id: str
    name: str
    device_type: str  # desktop, mobile, tablet
    os: str  # windows, macos, linux, android, ios
    browser: str  # chrome, firefox, safari, edge

    # Device specifics
    user_agent: str
    platform: str
    vendor: str

    # Screen
    screen_width: int
    screen_height: int
    device_scale_factor: float = 1.0

    # Locale
    locale: str = "en-US"
    timezone: str = "America/New_York"

    # Optional geolocation
    latitude: float | None = None
    longitude: float | None = None
    country_code: str | None = None

    # Hardware
    hardware_concurrency: int = 8
    device_memory: int = 8
    max_touch_points: int = 0

    # WebGL
    webgl_vendor: str = "Google Inc."
    webgl_renderer: str = "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)"

    # Network
    connection_type: str = "wifi"

    # Fonts (OS-specific)
    fonts: list[str] = field(default_factory=list)

    # Raw data (for custom fields)
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_fingerprint(self) -> Fingerprint:
        """Convert device profile to fingerprint."""
        geolocation = None
        if self.latitude is not None and self.longitude is not None:
            geolocation = GeolocationConfig(
                latitude=self.latitude,
                longitude=self.longitude,
            )

        return Fingerprint(
            id=f"fp-{self.id}",
            user_agent=self.user_agent,
            platform=self.platform,
            vendor=self.vendor,
            language=self.locale.split("-")[0],
            languages=[self.locale, self.locale.split("-")[0]],
            hardware_concurrency=self.hardware_concurrency,
            device_memory=self.device_memory,
            max_touch_points=self.max_touch_points,
            screen=ScreenConfig(
                width=self.screen_width,
                height=self.screen_height,
                device_scale_factor=self.device_scale_factor,
            ),
            webgl=WebGLConfig(
                vendor=self.webgl_vendor,
                renderer=self.webgl_renderer,
            ),
            timezone_id=self.timezone,
            locale=self.locale,
            geolocation=geolocation,
            network=NetworkConfig(connection_type=self.connection_type),
            fonts=self.fonts if self.fonts else None,  # type: ignore
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type,
            "os": self.os,
            "browser": self.browser,
            "user_agent": self.user_agent,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "locale": self.locale,
            "timezone": self.timezone,
            "country_code": self.country_code,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceProfile:
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", "Unknown Device"),
            device_type=data.get("device_type", data.get("deviceType", "desktop")),
            os=data.get("os", "windows"),
            browser=data.get("browser", "chrome"),
            user_agent=data.get("user_agent", data.get("userAgent", "")),
            platform=data.get("platform", "Win32"),
            vendor=data.get("vendor", "Google Inc."),
            screen_width=data.get("screen_width", data.get("screenWidth", 1920)),
            screen_height=data.get("screen_height", data.get("screenHeight", 1080)),
            device_scale_factor=data.get("device_scale_factor", data.get("deviceScaleFactor", 1.0)),
            locale=data.get("locale", "en-US"),
            timezone=data.get("timezone", "America/New_York"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            country_code=data.get("country_code", data.get("countryCode")),
            hardware_concurrency=data.get(
                "hardware_concurrency", data.get("hardwareConcurrency", 8)
            ),
            device_memory=data.get("device_memory", data.get("deviceMemory", 8)),
            max_touch_points=data.get("max_touch_points", data.get("maxTouchPoints", 0)),
            webgl_vendor=data.get("webgl_vendor", data.get("webglVendor", "Google Inc.")),
            webgl_renderer=data.get("webgl_renderer", data.get("webglRenderer", "")),
            connection_type=data.get("connection_type", data.get("connectionType", "wifi")),
            fonts=data.get("fonts", []),
            raw_data=data,
        )
