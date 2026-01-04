"""Mobile In-App WebView Fingerprint Generator.

Generates fingerprints that mimic TikTok, Instagram, and YouTube in-app WebView browsers.
These browsers have specific characteristics that differ from regular mobile browsers.

Key characteristics:
- Platform-specific JavaScript interfaces injected
- Custom user agent strings with app version info
- Specific HTTP headers for API communication
- Mobile-specific viewport and touch configurations
"""

from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import structlog

from ghoststorm.core.interfaces.fingerprint import IFingerprintGenerator
from ghoststorm.core.models.fingerprint import (
    CanvasNoiseConfig,
    DeviceProfile,
    Fingerprint,
    NavigatorConfig,
    ScreenConfig,
    WebGLConfig,
)
from ghoststorm.core.registry.hookspecs import hookimpl

logger = structlog.get_logger(__name__)


@dataclass
class MobileDeviceSpec:
    """Specification for a mobile device model."""

    model: str
    manufacturer: str
    os_version: str
    screen_width: int
    screen_height: int
    pixel_ratio: float
    hardware_concurrency: int
    device_memory: float
    touch_points: int = 5


# Common iOS devices for TikTok/Instagram
IOS_DEVICES = [
    MobileDeviceSpec("iPhone14,2", "Apple", "17.0", 1170, 2532, 3.0, 6, 6),  # iPhone 13 Pro
    MobileDeviceSpec("iPhone14,3", "Apple", "17.0", 1284, 2778, 3.0, 6, 6),  # iPhone 13 Pro Max
    MobileDeviceSpec("iPhone15,2", "Apple", "17.1", 1179, 2556, 3.0, 6, 6),  # iPhone 14 Pro
    MobileDeviceSpec("iPhone15,3", "Apple", "17.1", 1290, 2796, 3.0, 6, 6),  # iPhone 14 Pro Max
    MobileDeviceSpec("iPhone16,1", "Apple", "17.2", 1179, 2556, 3.0, 6, 6),  # iPhone 15 Pro
    MobileDeviceSpec("iPhone16,2", "Apple", "17.2", 1290, 2796, 3.0, 6, 6),  # iPhone 15 Pro Max
    MobileDeviceSpec("iPhone13,4", "Apple", "16.6", 1284, 2778, 3.0, 6, 6),  # iPhone 12 Pro Max
    MobileDeviceSpec("iPhone12,5", "Apple", "16.5", 1242, 2688, 3.0, 6, 4),  # iPhone 11 Pro Max
]

# Common Android devices
ANDROID_DEVICES = [
    MobileDeviceSpec("SM-G998B", "samsung", "13", 1440, 3200, 3.75, 8, 12),  # S21 Ultra
    MobileDeviceSpec("SM-S918B", "samsung", "13", 1440, 3088, 3.0, 8, 12),  # S23 Ultra
    MobileDeviceSpec("SM-G991B", "samsung", "13", 1080, 2400, 2.625, 8, 8),  # S21
    MobileDeviceSpec("Pixel 6", "Google", "13", 1080, 2400, 2.625, 8, 8),
    MobileDeviceSpec("Pixel 6 Pro", "Google", "13", 1440, 3120, 3.5, 8, 12),
    MobileDeviceSpec("Pixel 7", "Google", "14", 1080, 2400, 2.625, 8, 8),
    MobileDeviceSpec("Pixel 7 Pro", "Google", "14", 1440, 3120, 3.5, 8, 12),
    MobileDeviceSpec("OnePlus 11", "OnePlus", "13", 1440, 3216, 3.5, 8, 16),
]


@dataclass
class InAppProfile:
    """In-app WebView profile with platform-specific configuration."""

    platform: Literal["tiktok", "instagram", "youtube"]
    device: MobileDeviceSpec
    os: Literal["ios", "android"]
    app_version: str
    user_agent: str
    device_id: str
    install_id: str | None = None  # TikTok specific
    mid: str | None = None  # Instagram specific
    visitor_id: str | None = None  # YouTube specific
    headers: dict[str, str] = field(default_factory=dict)
    js_interface: str = ""


class MobileInAppGenerator(IFingerprintGenerator):
    """Fingerprint generator for TikTok, Instagram, and YouTube in-app WebViews.

    Generates realistic fingerprints that match the behavior of
    TikTok, Instagram, and YouTube's built-in browsers when opening external links.
    """

    name = "mobile_inapp"

    # Current app versions (update periodically)
    TIKTOK_IOS_VERSION = "32.0.0"
    TIKTOK_ANDROID_VERSION = "32.0.0"
    INSTAGRAM_IOS_VERSION = "312.0.0.38.113"
    INSTAGRAM_ANDROID_VERSION = "312.0.0.38.113"
    YOUTUBE_IOS_VERSION = "19.03.3"
    YOUTUBE_ANDROID_VERSION = "19.03.36"

    def __init__(self, data_path: Path | None = None) -> None:
        """Initialize the generator.

        Args:
            data_path: Path to user agent data files
        """
        self._data_path = data_path or (
            Path(__file__).parent.parent.parent.parent / "data" / "user_agents"
        )
        self._initialized = False
        self._tiktok_agents: list[str] = []
        self._instagram_agents: list[str] = []
        self._youtube_agents: list[str] = []

    async def initialize(self) -> None:
        """Load user agent data if available."""
        if self._initialized:
            return

        # Try to load user agent files
        for filename, target in [
            ("tiktok_inapp.txt", "_tiktok_agents"),
            ("instagram_inapp.txt", "_instagram_agents"),
            ("youtube_inapp.txt", "_youtube_agents"),
        ]:
            filepath = self._data_path / filename
            if filepath.exists():
                with filepath.open() as f:
                    agents = [
                        line.strip() for line in f if line.strip() and not line.startswith("#")
                    ]
                    setattr(self, target, agents)
                    logger.debug(
                        "[FINGERPRINT_INAPP] Loaded user agent file",
                        filename=filename,
                        agent_count=len(agents),
                    )

        self._initialized = True
        logger.info(
            "[FINGERPRINT_INAPP] Mobile in-app fingerprint generator initialized",
            tiktok_agents=len(self._tiktok_agents),
            instagram_agents=len(self._instagram_agents),
            youtube_agents=len(self._youtube_agents),
        )

    def _generate_device_id(self) -> str:
        """Generate a realistic device ID."""
        return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

    def _generate_install_id(self) -> str:
        """Generate a TikTok install ID."""
        return str(random.randint(7000000000000000000, 7999999999999999999))

    def _generate_mid(self) -> str:
        """Generate an Instagram machine ID (mid)."""
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(random.choice(chars) for _ in range(26))

    def _generate_visitor_id(self) -> str:
        """Generate a YouTube visitor ID."""
        # YouTube visitor IDs are typically 22-char base64
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        return "".join(random.choice(chars) for _ in range(22))

    def _build_tiktok_ios_ua(self, device: MobileDeviceSpec, app_version: str) -> str:
        """Build TikTok iOS WebView user agent."""
        return (
            f"Mozilla/5.0 (iPhone; CPU iPhone OS {device.os_version.replace('.', '_')} like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
            f"TikTok/{app_version} (Locale/en-US; App/1000000)"
        )

    def _build_tiktok_android_ua(self, device: MobileDeviceSpec, app_version: str) -> str:
        """Build TikTok Android WebView user agent."""
        return (
            f"Mozilla/5.0 (Linux; Android {device.os_version}; {device.model} "
            f"Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Version/4.0 Chrome/120.0.6099.144 Mobile Safari/537.36 "
            f"TikTok/{app_version}"
        )

    def _build_instagram_ios_ua(self, device: MobileDeviceSpec, app_version: str) -> str:
        """Build Instagram iOS WebView user agent."""
        return (
            f"Mozilla/5.0 (iPhone; CPU iPhone OS {device.os_version.replace('.', '_')} like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
            f"Instagram {app_version} ({device.model}; iOS {device.os_version}; "
            f"en_US; en; scale={device.pixel_ratio:.2f}; "
            f"{device.screen_width}x{device.screen_height}; 548153031)"
        )

    def _build_instagram_android_ua(self, device: MobileDeviceSpec, app_version: str) -> str:
        """Build Instagram Android WebView user agent."""
        dpi = int(device.pixel_ratio * 160)
        return (
            f"Mozilla/5.0 (Linux; Android {device.os_version}; {device.model} "
            f"Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Version/4.0 Chrome/120.0.6099.144 Mobile Safari/537.36 "
            f"Instagram {app_version} Android ({device.os_version.split('.')[0]}/{device.os_version}; "
            f"{dpi}dpi; {device.screen_width}x{device.screen_height}; "
            f"{device.manufacturer}; {device.model})"
        )

    def _build_youtube_ios_ua(self, device: MobileDeviceSpec, app_version: str) -> str:
        """Build YouTube iOS WebView user agent."""
        return (
            f"Mozilla/5.0 (iPhone; CPU iPhone OS {device.os_version.replace('.', '_')} like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
            f"Youtube/{app_version}"
        )

    def _build_youtube_android_ua(self, device: MobileDeviceSpec, app_version: str) -> str:
        """Build YouTube Android WebView user agent."""
        return (
            f"Mozilla/5.0 (Linux; Android {device.os_version}; {device.model} "
            f"Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Version/4.0 Chrome/120.0.6099.144 Mobile Safari/537.36 "
            f"com.google.android.youtube/{app_version}"
        )

    def _build_tiktok_headers(self, device_id: str, install_id: str) -> dict[str, str]:
        """Build TikTok-specific HTTP headers."""
        return {
            "x-tt-device-id": device_id,
            "x-tt-install-id": install_id,
            "x-tt-token": "",
            "x-tt-logid": "",
            "x-tt-trace-id": "",
        }

    def _build_instagram_headers(self, device_id: str, mid: str) -> dict[str, str]:
        """Build Instagram-specific HTTP headers."""
        return {
            "X-IG-App-ID": "936619743392459",
            "X-IG-Device-ID": device_id,
            "X-IG-Connection-Type": "WIFI",
            "X-IG-Capabilities": "3brTvw8=",
            "X-IG-Band-Speed-KB-s": str(random.randint(2000, 8000)),
            "X-MID": mid,
        }

    def _build_youtube_headers(self, device_id: str, visitor_id: str) -> dict[str, str]:
        """Build YouTube-specific HTTP headers."""
        return {
            "X-YouTube-Client-Name": "2",  # Android app
            "X-YouTube-Client-Version": self.YOUTUBE_ANDROID_VERSION,
            "X-Goog-Visitor-Id": visitor_id,
            "X-YouTube-Device": device_id,
            "X-YouTube-Page-CL": str(random.randint(500000000, 600000000)),
            "X-YouTube-Page-Label": "youtube.mobile.android",
        }

    def _build_tiktok_js_interface(self, device_id: str, install_id: str) -> str:
        """Build TikTok JavaScript bridge code."""
        return f"""
window.TikTokJSBridge = {{
    invoke: function(method, params, callback) {{
        console.log('TikTok bridge invoke:', method);
        if (callback) callback({{success: true}});
    }},
    call: function(method, params) {{
        return {{success: true}};
    }},
    _callbacks: {{}},
    _callbackId: 0
}};
window.byted_acrawler = {{
    init: function(config) {{}},
    sign: function(params) {{ return ''; }}
}};
window._ttDeviceId = '{device_id}';
window._ttInstallId = '{install_id}';
"""

    def _build_instagram_js_interface(self, device_id: str, mid: str) -> str:
        """Build Instagram JavaScript bridge code."""
        return f"""
window.InstagramInterface = {{
    requestClose: function() {{}},
    getAppVersion: function() {{ return '312.0.0.38.113'; }},
    getDeviceID: function() {{ return '{device_id}'; }},
    trackEvent: function(event, params) {{}},
    onReady: function() {{}},
    getSharedData: function() {{ return {{}}; }}
}};
window._igDeviceId = '{device_id}';
window._igMid = '{mid}';
window._igAppId = '936619743392459';
"""

    def _build_youtube_js_interface(self, device_id: str, visitor_id: str) -> str:
        """Build YouTube JavaScript bridge code."""
        return f"""
window.ytcfg = window.ytcfg || {{}};
window.ytcfg.set = function(key, val) {{ window.ytcfg[key] = val; }};
window.ytcfg.get = function(key) {{ return window.ytcfg[key]; }};
window.ytcfg.set('INNERTUBE_CONTEXT_CLIENT_NAME', 2);
window.ytcfg.set('INNERTUBE_CONTEXT_CLIENT_VERSION', '{self.YOUTUBE_ANDROID_VERSION}');
window.ytcfg.set('VISITOR_DATA', '{visitor_id}');
window.ytcfg.set('DEVICE_ID', '{device_id}');
window._ytDeviceId = '{device_id}';
window._ytVisitorId = '{visitor_id}';
window.yt = window.yt || {{}};
window.yt.player = window.yt.player || {{}};
"""

    async def generate_inapp_profile(
        self,
        platform: Literal["tiktok", "instagram", "youtube"],
        os: Literal["ios", "android"] | None = None,
        device_id: str | None = None,
    ) -> InAppProfile:
        """Generate an in-app WebView profile.

        Args:
            platform: Target platform (tiktok, instagram, or youtube)
            os: Target OS (random if None)
            device_id: Custom device ID (generated if None)

        Returns:
            InAppProfile with all configuration
        """
        if not self._initialized:
            await self.initialize()

        # Select OS
        if os is None:
            os = random.choice(["ios", "android"])

        # Select device
        devices = IOS_DEVICES if os == "ios" else ANDROID_DEVICES
        device = random.choice(devices)

        # Generate IDs
        if device_id is None:
            device_id = self._generate_device_id()

        install_id = None
        mid = None
        visitor_id = None

        # Build user agent and headers based on platform
        if platform == "tiktok":
            app_version = self.TIKTOK_IOS_VERSION if os == "ios" else self.TIKTOK_ANDROID_VERSION
            install_id = self._generate_install_id()

            if os == "ios":
                user_agent = self._build_tiktok_ios_ua(device, app_version)
            else:
                user_agent = self._build_tiktok_android_ua(device, app_version)

            headers = self._build_tiktok_headers(device_id, install_id)
            js_interface = self._build_tiktok_js_interface(device_id, install_id)

        elif platform == "instagram":
            app_version = (
                self.INSTAGRAM_IOS_VERSION if os == "ios" else self.INSTAGRAM_ANDROID_VERSION
            )
            mid = self._generate_mid()

            if os == "ios":
                user_agent = self._build_instagram_ios_ua(device, app_version)
            else:
                user_agent = self._build_instagram_android_ua(device, app_version)

            headers = self._build_instagram_headers(device_id, mid)
            js_interface = self._build_instagram_js_interface(device_id, mid)

        else:  # youtube
            app_version = self.YOUTUBE_IOS_VERSION if os == "ios" else self.YOUTUBE_ANDROID_VERSION
            visitor_id = self._generate_visitor_id()

            if os == "ios":
                user_agent = self._build_youtube_ios_ua(device, app_version)
            else:
                user_agent = self._build_youtube_android_ua(device, app_version)

            headers = self._build_youtube_headers(device_id, visitor_id)
            js_interface = self._build_youtube_js_interface(device_id, visitor_id)

        logger.info(
            "[FINGERPRINT_INAPP] Generated in-app WebView profile",
            platform=platform,
            os=os,
            device_model=device.model,
            device_manufacturer=device.manufacturer,
            os_version=device.os_version,
            app_version=app_version,
            device_id=device_id[:8] + "...",
            screen_resolution=f"{device.screen_width}x{device.screen_height}",
            pixel_ratio=device.pixel_ratio,
        )

        return InAppProfile(
            platform=platform,
            device=device,
            os=os,
            app_version=app_version,
            user_agent=user_agent,
            device_id=device_id,
            install_id=install_id,
            mid=mid,
            visitor_id=visitor_id,
            headers=headers,
            js_interface=js_interface,
        )

    async def generate(
        self,
        *,
        os_filter: str | None = None,
        browser_filter: str | None = None,
        device_category: str | None = None,
        platform: Literal["tiktok", "instagram", "youtube"] = "instagram",
    ) -> Fingerprint:
        """Generate fingerprint for in-app WebView.

        Args:
            os_filter: Filter by OS (ios, android)
            browser_filter: Ignored (always WebView)
            device_category: Ignored (always mobile)
            platform: Target platform (tiktok, instagram, or youtube)

        Returns:
            Fingerprint configured for in-app WebView
        """
        # Determine OS
        os_type: Literal["ios", "android"] | None = None
        if os_filter:
            os_lower = os_filter.lower()
            if os_lower in ("ios", "iphone", "ipad"):
                os_type = "ios"
            elif os_lower in ("android", "mobile"):
                os_type = "android"

        # Generate in-app profile
        profile = await self.generate_inapp_profile(platform, os_type)

        # Convert to Fingerprint
        device = profile.device

        screen_config = ScreenConfig(
            width=device.screen_width,
            height=device.screen_height,
            color_depth=24,
            pixel_depth=24,
            device_pixel_ratio=device.pixel_ratio,
        )

        navigator_config = NavigatorConfig(
            platform="iPhone" if profile.os == "ios" else "Linux armv8l",
            vendor="Apple Computer, Inc." if profile.os == "ios" else "Google Inc.",
            language="en-US",
            languages=["en-US", "en"],
            hardware_concurrency=device.hardware_concurrency,
            device_memory=device.device_memory,
            max_touch_points=device.touch_points,
        )

        # WebGL config for mobile
        if profile.os == "ios":
            webgl_vendor = "Apple Inc."
            webgl_renderer = "Apple GPU"
        else:
            webgl_vendor = "Qualcomm"
            webgl_renderer = f"Adreno (TM) {random.choice(['650', '660', '730', '740'])}"

        webgl_config = WebGLConfig(
            vendor=webgl_vendor,
            renderer=webgl_renderer,
            unmasked_vendor=webgl_vendor,
            unmasked_renderer=webgl_renderer,
        )

        # Canvas noise
        canvas_config = CanvasNoiseConfig(
            noise_r=random.randint(0, 10),
            noise_g=random.randint(0, 10),
            noise_b=random.randint(0, 10),
            noise_a=random.randint(0, 5),
        )

        device_profile = DeviceProfile(
            os=profile.os,
            os_version=device.os_version,
            browser="webview",
            browser_version=profile.app_version,
            device_category="mobile",
            touch_support=True,
        )

        fingerprint = Fingerprint(
            id=profile.device_id,
            user_agent=profile.user_agent,
            device=device_profile,
            screen=screen_config,
            navigator=navigator_config,
            webgl=webgl_config,
            canvas=canvas_config,
            extra={
                "platform": profile.platform,
                "app_version": profile.app_version,
                "headers": profile.headers,
                "js_interface": profile.js_interface,
                "install_id": profile.install_id,
                "mid": profile.mid,
                "visitor_id": profile.visitor_id,
            },
        )

        logger.info(
            "[FINGERPRINT_INAPP] Generated full fingerprint",
            fingerprint_id=fingerprint.id[:8] + "...",
            platform=profile.platform,
            os=profile.os,
            device_model=device.model,
            webgl_renderer=webgl_renderer,
            screen=f"{screen_config.width}x{screen_config.height}",
            user_agent_preview=profile.user_agent[:60] + "...",
        )

        return fingerprint

    @hookimpl
    def register_fingerprint_generators(self) -> list[type[IFingerprintGenerator]]:
        """Register this generator with the plugin system."""
        return [MobileInAppGenerator]
