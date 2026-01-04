"""Device profiles fingerprint generator using migrated Epic Traffic Bot profiles."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from ghoststorm.core.interfaces.fingerprint import IFingerprintGenerator
from ghoststorm.core.models.fingerprint import (
    CanvasNoiseConfig,
    DeviceProfile,
    Fingerprint,
    GeolocationConfig,
    NavigatorConfig,
    ScreenConfig,
    WebGLConfig,
)
from ghoststorm.core.registry.hookspecs import hookimpl


class DeviceProfilesGenerator(IFingerprintGenerator):
    """Fingerprint generator using 2505+ pre-collected device profiles.

    Profiles migrated from Epic Traffic Bot Pro, containing real-world
    device fingerprints with consistent navigator, screen, WebGL, canvas,
    and font configurations.
    """

    name = "device_profiles"

    def __init__(self, profiles_path: Path | None = None) -> None:
        self._profiles_path = profiles_path or (
            Path(__file__).parent.parent.parent.parent / "data" / "fingerprints" / "devices.json"
        )
        self._profiles: list[dict[str, Any]] = []
        self._loaded = False
        self._by_device_type: dict[str, list[dict[str, Any]]] = {}

    async def initialize(self) -> None:
        """Load device profiles from JSON file."""
        if self._loaded:
            return

        if not self._profiles_path.exists():
            raise FileNotFoundError(f"Device profiles not found: {self._profiles_path}")

        with self._profiles_path.open() as f:
            self._profiles = json.load(f)

        # Index by device type for filtering
        for profile in self._profiles:
            device_type = profile.get("General", {}).get("Device", "UNKNOWN").lower()
            if device_type not in self._by_device_type:
                self._by_device_type[device_type] = []
            self._by_device_type[device_type].append(profile)

        self._loaded = True

    @property
    def total_profiles(self) -> int:
        """Return total number of available profiles."""
        return len(self._profiles)

    def _convert_profile(self, raw: dict[str, Any]) -> Fingerprint:
        """Convert raw profile dict to Fingerprint model."""
        general = raw.get("General", {})
        navigator = raw.get("Navigator", {})
        emulation = raw.get("Emulation", {})

        display = emulation.get("Display", {})
        timezone = emulation.get("Timezone", {})
        canvas = emulation.get("Canvas", {})
        webgl = emulation.get("WebGL", {})
        font = emulation.get("Font", {})
        mobile = emulation.get("Mobile", {})

        # Parse device type
        device_type = general.get("Device", "WINDOWS").lower()
        if device_type == "windows":
            os_type = "windows"
        elif device_type in ("macos", "mac"):
            os_type = "macos"
        elif device_type == "linux":
            os_type = "linux"
        elif device_type in ("android", "mobile"):
            os_type = "android"
        elif device_type in ("ios", "iphone", "ipad"):
            os_type = "ios"
        else:
            os_type = "windows"

        # Determine browser from user agent
        user_agent = navigator.get("User_agent", "")
        if "Firefox" in user_agent:
            browser_type = "firefox"
        elif "Edg" in user_agent:
            browser_type = "edge"
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            browser_type = "safari"
        else:
            browser_type = "chrome"

        # Build screen config
        screen_config = ScreenConfig(
            width=display.get("Width", 1920),
            height=display.get("Height", 1080),
            color_depth=int(display.get("Color_depth", 24)),
            pixel_depth=int(display.get("Pixel_depth", 24)),
            device_pixel_ratio=float(display.get("Scale", 1.0)),
        )

        # Build navigator config
        navigator_config = NavigatorConfig(
            platform=navigator.get("Platform", "Win32"),
            vendor=navigator.get("Vendor", "Google Inc."),
            language=navigator.get("Browser_language", "en-US"),
            languages=[navigator.get("Browser_language", "en-US"), "en"],
            hardware_concurrency=int(navigator.get("Cpu_cores", 4)),
            device_memory=float(navigator.get("Device_memory", 8)),
            oscpu=navigator.get("Operating_system", ""),
        )

        # Build WebGL config
        webgl_config = None
        if webgl.get("WebGL_emulation"):
            webgl_config = WebGLConfig(
                vendor=webgl.get("WebGL_data_value", "WebKit"),
                renderer=webgl.get("WebGL_video_identifier", "WebKit WebGL"),
                unmasked_vendor="Google Inc.",
                unmasked_renderer=webgl.get("WebGL_video_identifier", "ANGLE (Intel)"),
            )

        # Build canvas config
        canvas_config = None
        if canvas.get("Canvas_emulation"):
            canvas_config = CanvasNoiseConfig(
                noise_r=int(canvas.get("Canvas_noise1", 0)),
                noise_g=int(canvas.get("Canvas_noise2", 0)),
                noise_b=int(canvas.get("Canvas_noise3", 0)),
                noise_a=int(canvas.get("Canvas_noise4", 0)),
            )

        # Build geolocation config
        geo_config = None
        if timezone.get("Timezone_emulation"):
            geo_config = GeolocationConfig(
                timezone=timezone.get("Timezone_identifier", "UTC"),
            )

        # Parse fonts
        fonts_str = font.get("Fonts", "")
        fonts_list = [f.strip().strip('"').strip("'") for f in fonts_str.split(",") if f.strip()]

        # Build device profile
        device_profile = DeviceProfile(
            os=os_type,
            os_version=navigator.get("Operating_system", ""),
            browser=browser_type,
            browser_version="",
            device_category="mobile" if mobile.get("Mobile_emulation") else "desktop",
            touch_support=mobile.get("Touch_points", 0) > 0,
        )

        return Fingerprint(
            id=general.get("Unique_id", ""),
            user_agent=user_agent,
            device=device_profile,
            screen=screen_config,
            navigator=navigator_config,
            webgl=webgl_config,
            canvas=canvas_config,
            geolocation=geo_config,
            fonts=fonts_list[:50] if fonts_list else None,  # Limit to 50 fonts
        )

    async def generate(
        self,
        *,
        os_filter: str | None = None,
        browser_filter: str | None = None,
        device_category: str | None = None,
    ) -> Fingerprint:
        """Generate fingerprint from device profiles database.

        Args:
            os_filter: Filter by OS (windows, macos, linux, android, ios)
            browser_filter: Filter by browser (chrome, firefox, edge, safari)
            device_category: Filter by category (desktop, mobile, tablet)

        Returns:
            Fingerprint from the profiles database
        """
        if not self._loaded:
            await self.initialize()

        # Filter profiles
        candidates = self._profiles

        if os_filter:
            os_lower = os_filter.lower()
            device_map = {
                "windows": ["windows"],
                "macos": ["macos", "mac"],
                "linux": ["linux"],
                "android": ["android", "mobile"],
                "ios": ["ios", "iphone", "ipad"],
            }
            valid_devices = device_map.get(os_lower, [os_lower])
            candidates = [
                p for p in candidates
                if p.get("General", {}).get("Device", "").lower() in valid_devices
            ]

        if device_category == "mobile":
            candidates = [
                p for p in candidates
                if p.get("Emulation", {}).get("Mobile", {}).get("Mobile_emulation", False)
            ]
        elif device_category == "desktop":
            candidates = [
                p for p in candidates
                if not p.get("Emulation", {}).get("Mobile", {}).get("Mobile_emulation", False)
            ]

        if browser_filter:
            browser_lower = browser_filter.lower()
            candidates = [
                p for p in candidates
                if browser_lower in p.get("Navigator", {}).get("User_agent", "").lower()
            ]

        if not candidates:
            candidates = self._profiles

        # Select random profile
        profile = random.choice(candidates)
        return self._convert_profile(profile)

    async def get_by_id(self, profile_id: str) -> Fingerprint | None:
        """Get specific fingerprint by ID."""
        if not self._loaded:
            await self.initialize()

        for profile in self._profiles:
            if profile.get("General", {}).get("Unique_id") == profile_id:
                return self._convert_profile(profile)
        return None

    def list_device_types(self) -> list[str]:
        """List available device types."""
        return list(self._by_device_type.keys())

    @hookimpl
    def register_fingerprint_generators(self) -> list[type[IFingerprintGenerator]]:
        """Register this generator with the plugin system."""
        return [DeviceProfilesGenerator]
