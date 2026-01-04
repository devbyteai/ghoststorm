"""BrowserForge fingerprint generator plugin."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

import structlog

from ghoststorm.core.models.fingerprint import (
    CanvasNoiseConfig,
    DeviceProfile,
    Fingerprint,
    NetworkConfig,
    ScreenConfig,
    WebGLConfig,
)

if TYPE_CHECKING:
    from ghoststorm.core.models.fingerprint import FingerprintConstraints

logger = structlog.get_logger(__name__)


class BrowserForgeGenerator:
    """
    Fingerprint generator using BrowserForge library.

    BrowserForge uses a Bayesian generative network to create
    realistic browser fingerprints that match real traffic patterns.
    """

    name = "browserforge"

    def __init__(self) -> None:
        self._fg = None
        self._hg = None
        self._profiles: list[DeviceProfile] = []

    @property
    def total_profiles(self) -> int:
        return len(self._profiles)

    async def initialize(self) -> None:
        """Initialize BrowserForge."""
        try:
            from browserforge.fingerprints import FingerprintGenerator
            from browserforge.headers import HeaderGenerator

            self._fg = FingerprintGenerator()
            self._hg = HeaderGenerator()
            logger.info("BrowserForge initialized")
        except ImportError:
            logger.warning(
                "BrowserForge not installed, using fallback generator. "
                "Install with: pip install browserforge"
            )

    async def generate(
        self,
        *,
        constraints: FingerprintConstraints | None = None,
        device_profile: DeviceProfile | None = None,
    ) -> Fingerprint:
        """Generate a fingerprint."""
        if device_profile:
            return device_profile.to_fingerprint()

        if self._fg:
            return await self._generate_browserforge(constraints)
        else:
            return await self._generate_fallback(constraints)

    async def _generate_browserforge(
        self,
        constraints: FingerprintConstraints | None,
    ) -> Fingerprint:
        """Generate using BrowserForge."""
        options: dict[str, Any] = {}

        if constraints:
            if constraints.browsers:
                options["browser"] = random.choice(constraints.browsers)
            if constraints.os_list:
                options["os"] = random.choice(constraints.os_list)

        # Generate fingerprint
        bf_fingerprint = self._fg.generate(**options)

        # Convert to our format
        screen = bf_fingerprint.screen
        navigator = bf_fingerprint.navigator

        fingerprint = Fingerprint(
            user_agent=navigator.userAgent,
            platform=navigator.platform,
            vendor=getattr(navigator, "vendor", "Google Inc."),
            language=getattr(navigator, "language", "en-US"),
            languages=getattr(navigator, "languages", ["en-US", "en"]),
            hardware_concurrency=getattr(navigator, "hardwareConcurrency", 8),
            device_memory=getattr(navigator, "deviceMemory", 8),
            max_touch_points=getattr(navigator, "maxTouchPoints", 0),
            screen=ScreenConfig(
                width=screen.width,
                height=screen.height,
                device_scale_factor=getattr(screen, "devicePixelRatio", 1.0),
                color_depth=getattr(screen, "colorDepth", 24),
            ),
        )

        return fingerprint

    async def _generate_fallback(
        self,
        constraints: FingerprintConstraints | None,
    ) -> Fingerprint:
        """Generate using fallback (no BrowserForge)."""
        # Default user agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        ]

        screens = [
            (1920, 1080),
            (1366, 768),
            (1536, 864),
            (1440, 900),
            (1280, 720),
            (2560, 1440),
        ]

        timezones = [
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
        ]

        webgl_renderers = [
            "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)",
        ]

        ua = random.choice(user_agents)
        width, height = random.choice(screens)

        # Determine platform from user agent
        if "Windows" in ua:
            platform = "Win32"
        elif "Mac" in ua:
            platform = "MacIntel"
        else:
            platform = "Linux x86_64"

        return Fingerprint(
            user_agent=ua,
            platform=platform,
            vendor="Google Inc.",
            language="en-US",
            languages=["en-US", "en"],
            hardware_concurrency=random.choice([4, 8, 12, 16]),
            device_memory=random.choice([4, 8, 16]),
            max_touch_points=0,
            screen=ScreenConfig(
                width=width,
                height=height,
                device_scale_factor=random.choice([1.0, 1.25, 1.5, 2.0]),
            ),
            webgl=WebGLConfig(
                vendor="Google Inc. (NVIDIA)",
                renderer=random.choice(webgl_renderers),
            ),
            canvas_noise=CanvasNoiseConfig(
                enabled=True,
                noise_r=random.uniform(0.05, 0.15),
                noise_g=random.uniform(0.05, 0.15),
                noise_b=random.uniform(0.05, 0.15),
            ),
            timezone_id=random.choice(timezones),
            locale="en-US",
            network=NetworkConfig(
                connection_type=random.choice(["wifi", "4g", "ethernet"]),
            ),
        )

    async def get_random_profile(
        self,
        *,
        browser: str | None = None,
        os: str | None = None,
        device_type: str | None = None,
    ) -> DeviceProfile:
        """Get a random device profile."""
        candidates = self._profiles

        if browser:
            candidates = [p for p in candidates if p.browser == browser]
        if os:
            candidates = [p for p in candidates if p.os == os]
        if device_type:
            candidates = [p for p in candidates if p.device_type == device_type]

        if candidates:
            return random.choice(candidates)

        # Generate a synthetic profile
        fingerprint = await self.generate()
        return DeviceProfile(
            id=f"generated-{fingerprint.id}",
            name="Generated Profile",
            device_type="desktop",
            os="windows",
            browser="chrome",
            user_agent=fingerprint.user_agent,
            platform=fingerprint.platform,
            vendor=fingerprint.vendor,
            screen_width=fingerprint.screen.width,
            screen_height=fingerprint.screen.height,
            locale=fingerprint.locale,
            timezone=fingerprint.timezone_id,
        )

    async def get_profile_by_id(self, profile_id: str) -> DeviceProfile | None:
        """Get a profile by ID."""
        for profile in self._profiles:
            if profile.id == profile_id:
                return profile
        return None

    async def list_profiles(
        self,
        *,
        browser: str | None = None,
        os: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeviceProfile]:
        """List profiles."""
        candidates = self._profiles

        if browser:
            candidates = [p for p in candidates if p.browser == browser]
        if os:
            candidates = [p for p in candidates if p.os == os]

        return candidates[offset : offset + limit]

    async def load_profiles_from_file(self, path: str) -> int:
        """Load device profiles from a JSON file."""
        import json
        from pathlib import Path

        file_path = Path(path)
        if not file_path.exists():
            logger.warning("Profile file not found", path=path)
            return 0

        try:
            with file_path.open() as f:
                data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    profile = DeviceProfile.from_dict(item)
                    self._profiles.append(profile)
            elif isinstance(data, dict):
                for key, item in data.items():
                    if isinstance(item, dict):
                        item["id"] = key
                        profile = DeviceProfile.from_dict(item)
                        self._profiles.append(profile)

            logger.info("Loaded device profiles", count=len(self._profiles), path=path)
            return len(self._profiles)

        except Exception as e:
            logger.error("Failed to load profiles", path=path, error=str(e))
            return 0

    async def close(self) -> None:
        """Clean up resources."""
        self._fg = None
        self._hg = None
