"""Resource Loader - Load all anti-detection resources.

Loads and manages:
- 2.3M+ proxies (authenticated, SOCKS4, basic)
- 222K device fingerprints
- 49K+ user agents
- Screen sizes, referrers, behavior patterns
- Stealth JavaScript
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ProxyType(str, Enum):
    """Proxy quality tiers."""
    AUTHENTICATED = "authenticated"  # ip:port:user:pass - highest quality
    SOCKS4 = "socks4"               # SOCKS4 with country codes
    BASIC = "basic"                  # ip:port only


@dataclass
class Proxy:
    """Proxy configuration."""
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    protocol: str = "http"
    country: str | None = None
    proxy_type: ProxyType = ProxyType.BASIC
    failures: int = 0
    successes: int = 0

    @property
    def url(self) -> str:
        """Get proxy URL for browser."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.failures + self.successes
        if total == 0:
            return 0.5  # Unknown
        return self.successes / total


@dataclass
class DeviceFingerprint:
    """Device fingerprint from devices.json."""
    id: str
    device_type: str  # WINDOWS, ANDROID, IOS, etc.
    user_agent: str
    platform: str
    vendor: str
    viewport: tuple[int, int]
    color_depth: int
    pixel_depth: int
    hardware_concurrency: int
    device_memory: float
    timezone: str
    canvas_noise: tuple[int, int, int, int]
    webgl_vendor: str
    webgl_renderer: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorPattern:
    """TikTok behavior pattern configuration."""
    watch_min_seconds: float
    watch_max_seconds: float
    skip_probability: float
    scroll_probability: float
    pause_probability: float
    interest_level: str


class ResourceLoader:
    """
    Load and manage all anti-detection resources.

    Provides access to:
    - Proxies (prioritized by quality)
    - Device fingerprints (matched by device type)
    - User agents (grouped by platform)
    - Screen sizes (by device type)
    - Referrers (social media focused)
    - Behavior patterns (TikTok specific)
    - Stealth JavaScript template
    """

    # Base paths - relative to project root
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent  # src/ghoststorm/core/resources -> project root
    DATA_ROOT = PROJECT_ROOT / "data"

    def __init__(self, lazy_load: bool = True) -> None:
        """
        Initialize ResourceLoader.

        Args:
            lazy_load: If True, load resources on first access
        """
        self._proxies: dict[ProxyType, list[Proxy]] = {}
        self._fingerprints: list[DeviceFingerprint] = []
        self._fingerprints_by_type: dict[str, list[DeviceFingerprint]] = {}
        self._user_agents: dict[str, list[str]] = {}
        self._screen_sizes: dict[str, list[tuple[int, int]]] = {}
        self._referrers: list[str] = []
        self._behavior_patterns: dict[str, Any] = {}
        self._stealth_js: str = ""

        self._loaded = False
        if not lazy_load:
            self.load_all()

    def load_all(self) -> None:
        """Load all resources."""
        if self._loaded:
            return

        logger.info("[RESOURCES] Loading all resources...")

        self._load_proxies()
        self._load_fingerprints()
        self._load_user_agents()
        self._load_screen_sizes()
        self._load_referrers()
        self._load_behavior_patterns()
        self._load_stealth_js()

        self._loaded = True
        self._log_stats()

    def _log_stats(self) -> None:
        """Log resource statistics."""
        total_proxies = sum(len(p) for p in self._proxies.values())
        logger.info(
            "[RESOURCES] Loaded successfully",
            proxies=total_proxies,
            proxies_auth=len(self._proxies.get(ProxyType.AUTHENTICATED, [])),
            proxies_socks4=len(self._proxies.get(ProxyType.SOCKS4, [])),
            proxies_basic=len(self._proxies.get(ProxyType.BASIC, [])),
            fingerprints=len(self._fingerprints),
            user_agents=sum(len(ua) for ua in self._user_agents.values()),
            tiktok_uas=len(self._user_agents.get("tiktok_inapp", [])),
            referrers=len(self._referrers),
        )

    # =========================================================================
    # PROXY LOADING
    # =========================================================================

    def _load_proxies(self) -> None:
        """Load all proxy types."""
        self._proxies = {
            ProxyType.AUTHENTICATED: [],
            ProxyType.SOCKS4: [],
            ProxyType.BASIC: [],
        }

        # 1. Authenticated proxies (highest priority)
        auth_path = self.DEXTOOLS_ROOT / "Desktop/data/proxies.txt"
        if auth_path.exists():
            self._load_authenticated_proxies(auth_path)

        # 2. SOCKS4 proxies with country codes
        socks4_path = self.DEXTOOLS_ROOT / "socks4.csv"
        if socks4_path.exists():
            self._load_socks4_proxies(socks4_path)

        # 3. Basic proxies (massive volume)
        basic_path = self.DATA_ROOT / "proxies/aggregated.txt"
        if basic_path.exists():
            self._load_basic_proxies(basic_path)

    def _load_authenticated_proxies(self, path: Path) -> None:
        """Load ip:port:user:pass format proxies."""
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split(":")
                    if len(parts) >= 4:
                        proxy = Proxy(
                            host=parts[0],
                            port=int(parts[1]),
                            username=parts[2],
                            password=parts[3],
                            protocol="http",
                            proxy_type=ProxyType.AUTHENTICATED,
                        )
                        self._proxies[ProxyType.AUTHENTICATED].append(proxy)

            logger.debug(f"[RESOURCES] Loaded {len(self._proxies[ProxyType.AUTHENTICATED])} authenticated proxies")
        except Exception as e:
            logger.error(f"[RESOURCES] Failed to load authenticated proxies: {e}")

    def _load_socks4_proxies(self, path: Path) -> None:
        """Load SOCKS4 CSV format: "ip:port","country" """
        try:
            with open(path) as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        addr = row[0].strip('"')
                        country = row[1].strip('"')

                        if ":" in addr:
                            host, port = addr.split(":", 1)
                            proxy = Proxy(
                                host=host,
                                port=int(port),
                                protocol="socks4",
                                country=country,
                                proxy_type=ProxyType.SOCKS4,
                            )
                            self._proxies[ProxyType.SOCKS4].append(proxy)

            logger.debug(f"[RESOURCES] Loaded {len(self._proxies[ProxyType.SOCKS4])} SOCKS4 proxies")
        except Exception as e:
            logger.error(f"[RESOURCES] Failed to load SOCKS4 proxies: {e}")

    def _load_basic_proxies(self, path: Path, limit: int = 100000) -> None:
        """Load basic ip:port format proxies (limited for memory)."""
        try:
            count = 0
            with open(path) as f:
                for line in f:
                    if count >= limit:
                        break

                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    if ":" in line:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            try:
                                proxy = Proxy(
                                    host=parts[0],
                                    port=int(parts[1]),
                                    protocol="http",
                                    proxy_type=ProxyType.BASIC,
                                )
                                self._proxies[ProxyType.BASIC].append(proxy)
                                count += 1
                            except ValueError:
                                continue

            logger.debug(f"[RESOURCES] Loaded {len(self._proxies[ProxyType.BASIC])} basic proxies (limited)")
        except Exception as e:
            logger.error(f"[RESOURCES] Failed to load basic proxies: {e}")

    # =========================================================================
    # FINGERPRINT LOADING
    # =========================================================================

    def _load_fingerprints(self, limit: int = 10000) -> None:
        """Load device fingerprints (limited for memory)."""
        path = self.DATA_ROOT / "fingerprints/devices.json"
        if not path.exists():
            logger.warning(f"[RESOURCES] Fingerprints not found: {path}")
            return

        try:
            with open(path) as f:
                data = json.load(f)

            # Limit for memory
            if len(data) > limit:
                data = random.sample(data, limit)

            for item in data:
                try:
                    fp = self._parse_fingerprint(item)
                    if fp:
                        self._fingerprints.append(fp)

                        # Index by device type
                        device_type = fp.device_type.lower()
                        if device_type not in self._fingerprints_by_type:
                            self._fingerprints_by_type[device_type] = []
                        self._fingerprints_by_type[device_type].append(fp)
                except Exception:
                    continue

            logger.debug(f"[RESOURCES] Loaded {len(self._fingerprints)} fingerprints")
        except Exception as e:
            logger.error(f"[RESOURCES] Failed to load fingerprints: {e}")

    def _parse_fingerprint(self, data: dict) -> DeviceFingerprint | None:
        """Parse a single fingerprint entry."""
        try:
            general = data.get("General", {})
            navigator = data.get("Navigator", {})
            emulation = data.get("Emulation", {})
            display = emulation.get("Display", {})
            canvas = emulation.get("Canvas", {})
            webgl = emulation.get("WebGL", {})
            timezone = emulation.get("Timezone", {})

            return DeviceFingerprint(
                id=general.get("Unique_id", ""),
                device_type=general.get("Device", "WINDOWS"),
                user_agent=navigator.get("User_agent", ""),
                platform=navigator.get("Platform", ""),
                vendor=navigator.get("Vendor", ""),
                viewport=(
                    display.get("Width", 1920),
                    display.get("Height", 1080),
                ),
                color_depth=int(display.get("Color_depth", 24)),
                pixel_depth=int(display.get("Pixel_depth", 24)),
                hardware_concurrency=int(navigator.get("Cpu_cores", 4)),
                device_memory=float(navigator.get("Device_memory", 8)),
                timezone=timezone.get("Timezone_identifier", "UTC"),
                canvas_noise=(
                    int(canvas.get("Canvas_noise1", 0)),
                    int(canvas.get("Canvas_noise2", 0)),
                    int(canvas.get("Canvas_noise3", 0)),
                    int(canvas.get("Canvas_noise4", 0)),
                ),
                webgl_vendor=webgl.get("WebGL_video_identifier", ""),
                webgl_renderer=webgl.get("WebGL_data_key", ""),
                raw=data,
            )
        except Exception:
            return None

    # =========================================================================
    # USER AGENT LOADING
    # =========================================================================

    def _load_user_agents(self) -> None:
        """Load user agents by category."""
        ua_dir = self.DATA_ROOT / "user_agents"
        if not ua_dir.exists():
            return

        # Priority files
        priority_files = [
            ("tiktok_inapp", "tiktok_inapp.txt"),
            ("instagram_inapp", "instagram_inapp.txt"),
            ("iphone", "iphone.txt"),
            ("android", "android.txt"),
            ("windows", "windows.txt"),
            ("mac", "mac.txt"),
        ]

        for category, filename in priority_files:
            path = ua_dir / filename
            if path.exists():
                self._user_agents[category] = self._load_ua_file(path)

        # Load aggregated as fallback
        agg_path = ua_dir / "aggregated.txt"
        if agg_path.exists():
            self._user_agents["aggregated"] = self._load_ua_file(agg_path, limit=5000)

    def _load_ua_file(self, path: Path, limit: int = 1000) -> list[str]:
        """Load user agents from a file."""
        user_agents = []
        try:
            with open(path) as f:
                for line in f:
                    if len(user_agents) >= limit:
                        break

                    line = line.strip()
                    if line and not line.startswith("#"):
                        user_agents.append(line)
        except Exception as e:
            logger.warning(f"[RESOURCES] Failed to load UA file {path}: {e}")

        return user_agents

    # =========================================================================
    # SCREEN SIZE LOADING
    # =========================================================================

    def _load_screen_sizes(self) -> None:
        """Load screen sizes by device type."""
        ss_dir = self.DATA_ROOT / "screen_sizes"
        if not ss_dir.exists():
            return

        for path in ss_dir.glob("*.txt"):
            category = path.stem
            sizes = []

            try:
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if line and "x" in line.lower():
                            parts = line.lower().split("x")
                            if len(parts) == 2:
                                try:
                                    w, h = int(parts[0]), int(parts[1])
                                    sizes.append((w, h))
                                except ValueError:
                                    continue

                if sizes:
                    self._screen_sizes[category] = sizes
            except Exception:
                continue

    # =========================================================================
    # REFERRER LOADING
    # =========================================================================

    def _load_referrers(self) -> None:
        """Load referrer URLs."""
        ref_dir = self.DATA_ROOT / "referrers"
        if not ref_dir.exists():
            return

        # Prioritize social media for TikTok
        priority = ["social_media.txt", "video_platforms.txt", "search_engines.txt"]

        for filename in priority:
            path = ref_dir / filename
            if path.exists():
                try:
                    with open(path) as f:
                        for line in f:
                            line = line.strip()
                            if line and line.startswith("http"):
                                self._referrers.append(line)
                except Exception:
                    continue

    # =========================================================================
    # BEHAVIOR PATTERN LOADING
    # =========================================================================

    def _load_behavior_patterns(self) -> None:
        """Load TikTok behavior patterns."""
        path = self.DATA_ROOT / "behavior/video_watch_patterns.json"
        if not path.exists():
            return

        try:
            with open(path) as f:
                self._behavior_patterns = json.load(f)
        except Exception as e:
            logger.warning(f"[RESOURCES] Failed to load behavior patterns: {e}")

    # =========================================================================
    # STEALTH JS LOADING
    # =========================================================================

    def _load_stealth_js(self) -> None:
        """Load stealth JavaScript template."""
        path = self.DATA_ROOT / "evasion/stealth_template.js"
        if not path.exists():
            return

        try:
            with open(path) as f:
                self._stealth_js = f.read()
        except Exception as e:
            logger.warning(f"[RESOURCES] Failed to load stealth JS: {e}")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def get_proxy(self, proxy_type: ProxyType | None = None) -> Proxy | None:
        """
        Get a random proxy.

        Args:
            proxy_type: Specific type or None for any (prioritized)

        Returns:
            Proxy instance or None if none available
        """
        if not self._loaded:
            self.load_all()

        if proxy_type:
            proxies = self._proxies.get(proxy_type, [])
            return random.choice(proxies) if proxies else None

        # Priority order: authenticated > socks4 > basic
        for ptype in [ProxyType.AUTHENTICATED, ProxyType.SOCKS4, ProxyType.BASIC]:
            proxies = self._proxies.get(ptype, [])
            if proxies:
                return random.choice(proxies)

        return None

    def get_proxies(self, proxy_type: ProxyType, count: int = 10) -> list[Proxy]:
        """Get multiple proxies of a specific type."""
        if not self._loaded:
            self.load_all()

        proxies = self._proxies.get(proxy_type, [])
        if len(proxies) <= count:
            return proxies.copy()
        return random.sample(proxies, count)

    def get_fingerprint(self, device_type: str | None = None) -> DeviceFingerprint | None:
        """
        Get a random device fingerprint.

        Args:
            device_type: Filter by device type (windows, android, ios)

        Returns:
            DeviceFingerprint instance or None
        """
        if not self._loaded:
            self.load_all()

        if device_type:
            fps = self._fingerprints_by_type.get(device_type.lower(), [])
            return random.choice(fps) if fps else None

        return random.choice(self._fingerprints) if self._fingerprints else None

    def get_user_agent(self, category: str = "tiktok_inapp") -> str | None:
        """
        Get a random user agent.

        Args:
            category: UA category (tiktok_inapp, iphone, android, etc.)

        Returns:
            User agent string or None
        """
        if not self._loaded:
            self.load_all()

        uas = self._user_agents.get(category, [])
        if not uas:
            uas = self._user_agents.get("aggregated", [])

        return random.choice(uas) if uas else None

    def get_screen_size(self, device_type: str = "iphone") -> tuple[int, int]:
        """
        Get a random screen size for device type.

        Args:
            device_type: Device type (iphone, android, desktop, etc.)

        Returns:
            (width, height) tuple
        """
        if not self._loaded:
            self.load_all()

        sizes = self._screen_sizes.get(device_type, [])
        if not sizes:
            sizes = self._screen_sizes.get("desktop", [(1920, 1080)])

        return random.choice(sizes) if sizes else (390, 844)  # iPhone default

    def get_referrer(self) -> str:
        """Get a random referrer URL."""
        if not self._loaded:
            self.load_all()

        return random.choice(self._referrers) if self._referrers else "https://www.tiktok.com/"

    def get_behavior_pattern(self, interest_level: str = "medium") -> BehaviorPattern:
        """
        Get TikTok behavior pattern.

        Args:
            interest_level: low, medium, or high

        Returns:
            BehaviorPattern configuration
        """
        if not self._loaded:
            self.load_all()

        tiktok = self._behavior_patterns.get("platforms", {}).get("tiktok", {})
        distributions = tiktok.get("watch_distributions", {})
        pattern = distributions.get(f"{interest_level}_interest", {})

        return BehaviorPattern(
            watch_min_seconds=5.0,
            watch_max_seconds=15.0,
            skip_probability=pattern.get("skip_probability", 0.3),
            scroll_probability=0.5,
            pause_probability=pattern.get("pause_probability", 0.1) if "pause" in str(pattern) else 0.1,
            interest_level=interest_level,
        )

    def get_stealth_js(self, fingerprint: DeviceFingerprint | None = None) -> str:
        """
        Get stealth JavaScript with fingerprint values injected.

        Args:
            fingerprint: Fingerprint to inject values from

        Returns:
            JavaScript code string
        """
        if not self._loaded:
            self.load_all()

        js = self._stealth_js

        if fingerprint:
            # Replace placeholders with fingerprint values
            replacements = {
                "[vendor]": fingerprint.vendor or "Google Inc.",
                "[oscpu]": "",
                "[history.length]": "5",
                "[hardware.concurrency]": str(fingerprint.hardware_concurrency),
                "[device.memory]": str(fingerprint.device_memory),
                "[color.depth]": str(fingerprint.color_depth),
                "[pixel.depth]": str(fingerprint.pixel_depth),
                "[canvasnoiseone]": str(fingerprint.canvas_noise[0]),
                "[canvasnoisetwo]": str(fingerprint.canvas_noise[1]),
                "[canvasnoisethree]": str(fingerprint.canvas_noise[2]),
                "[canvasnoisefour]": str(fingerprint.canvas_noise[3]),
                "[value]": fingerprint.webgl_renderer or "ANGLE",
                "[chrome_browser]": "true",
                "[webgl]": "true",
                "[canvas]": "true",
                "[fonts]": "true",
            }

            for placeholder, value in replacements.items():
                js = js.replace(placeholder, value)

        return js

    @property
    def stats(self) -> dict[str, int]:
        """Get resource statistics."""
        if not self._loaded:
            self.load_all()

        return {
            "proxies_authenticated": len(self._proxies.get(ProxyType.AUTHENTICATED, [])),
            "proxies_socks4": len(self._proxies.get(ProxyType.SOCKS4, [])),
            "proxies_basic": len(self._proxies.get(ProxyType.BASIC, [])),
            "fingerprints": len(self._fingerprints),
            "user_agents": sum(len(ua) for ua in self._user_agents.values()),
            "referrers": len(self._referrers),
        }
