"""Camoufox browser engine - Firefox-based anti-detect browser with C++ level fingerprint spoofing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ghoststorm.core.models.fingerprint import Fingerprint
    from ghoststorm.core.models.proxy import Proxy

logger = structlog.get_logger(__name__)


@dataclass
class CamoufoxConfig:
    """Configuration for Camoufox browser.

    Camoufox operates at C++ level, making fingerprint changes
    undetectable through JavaScript inspection.
    """

    # OS spoofing (windows, macos, linux)
    os: str | None = None

    # Human-like cursor movement (built-in C++ implementation)
    humanize: bool = True

    # GeoIP-based fingerprint localization
    geoip: bool = False

    # Custom fonts (defaults to bundled OS fonts)
    fonts: list[str] | None = None

    # Screen dimensions
    screen: dict[str, int] | None = None

    # WebGL (disabled by default, rarely triggers detection)
    webgl: bool = False

    # Additional Firefox preferences
    firefox_prefs: dict[str, Any] = field(default_factory=dict)

    # Addons to install
    addons: list[str] | None = None


class CamoufoxPage:
    """Wrapper around Camoufox page (Playwright Firefox page)."""

    def __init__(self, page: Any) -> None:
        self._page = page

    @property
    def url(self) -> str:
        return self._page.url

    @property
    def mouse(self) -> Any:
        """Access mouse for humanized movement."""
        return self._page.mouse

    @property
    def keyboard(self) -> Any:
        """Access keyboard."""
        return self._page.keyboard

    async def goto(
        self,
        url: str,
        *,
        wait_until: str = "load",
        timeout: float | None = None,
        referer: str | None = None,
    ) -> None:
        options: dict[str, Any] = {"wait_until": wait_until}
        if timeout:
            options["timeout"] = timeout
        if referer:
            options["referer"] = referer
        await self._page.goto(url, **options)

    async def click(
        self,
        selector: str,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float | None = None,
        timeout: float | None = None,
    ) -> None:
        options: dict[str, Any] = {"button": button, "click_count": click_count}
        if delay:
            options["delay"] = delay
        if timeout:
            options["timeout"] = timeout
        await self._page.click(selector, **options)

    async def type(
        self,
        selector: str,
        text: str,
        *,
        delay: float | None = None,
        timeout: float | None = None,
    ) -> None:
        options: dict[str, Any] = {}
        if delay:
            options["delay"] = delay
        if timeout:
            options["timeout"] = timeout
        await self._page.type(selector, text, **options)

    async def fill(
        self,
        selector: str,
        value: str,
        *,
        timeout: float | None = None,
    ) -> None:
        options: dict[str, Any] = {}
        if timeout:
            options["timeout"] = timeout
        await self._page.fill(selector, value, **options)

    async def screenshot(
        self,
        *,
        path: str | None = None,
        full_page: bool = False,
        type: str = "png",
        quality: int | None = None,
    ) -> bytes:
        options: dict[str, Any] = {"full_page": full_page, "type": type}
        if path:
            options["path"] = path
        if quality and type == "jpeg":
            options["quality"] = quality
        return await self._page.screenshot(**options)

    async def evaluate(self, expression: str, *args: Any) -> Any:
        return await self._page.evaluate(expression, *args)

    async def wait_for_selector(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: float | None = None,
    ) -> Any:
        options: dict[str, Any] = {"state": state}
        if timeout:
            options["timeout"] = timeout
        return await self._page.wait_for_selector(selector, **options)

    async def wait_for_load_state(
        self,
        state: str = "load",
        *,
        timeout: float | None = None,
    ) -> None:
        options: dict[str, Any] = {}
        if timeout:
            options["timeout"] = timeout
        await self._page.wait_for_load_state(state, **options)

    async def content(self) -> str:
        return await self._page.content()

    async def title(self) -> str:
        return await self._page.title()

    async def query_selector(self, selector: str) -> Any | None:
        return await self._page.query_selector(selector)

    async def query_selector_all(self, selector: str) -> list[Any]:
        return await self._page.query_selector_all(selector)

    async def scroll(
        self,
        *,
        x: int = 0,
        y: int = 0,
        behavior: str = "smooth",
    ) -> None:
        await self._page.evaluate(
            f"window.scrollTo({{left: {x}, top: {y}, behavior: '{behavior}'}})"
        )

    async def hover(self, selector: str, *, timeout: float | None = None) -> None:
        """Hover over element with human-like movement."""
        options: dict[str, Any] = {}
        if timeout:
            options["timeout"] = timeout
        await self._page.hover(selector, **options)

    async def close(self) -> None:
        await self._page.close()


class CamoufoxContext:
    """Wrapper around Camoufox browser context."""

    def __init__(self, context: Any) -> None:
        self._context = context
        self._pages: list[CamoufoxPage] = []

    @property
    def pages(self) -> list[CamoufoxPage]:
        return self._pages

    async def new_page(self) -> CamoufoxPage:
        page = await self._context.new_page()
        wrapped = CamoufoxPage(page)
        self._pages.append(wrapped)
        return wrapped

    async def cookies(self, urls: list[str] | None = None) -> list[dict[str, Any]]:
        if urls:
            return await self._context.cookies(urls)
        return await self._context.cookies()

    async def add_cookies(self, cookies: list[dict[str, Any]]) -> None:
        await self._context.add_cookies(cookies)

    async def clear_cookies(self) -> None:
        await self._context.clear_cookies()

    async def set_extra_http_headers(self, headers: dict[str, str]) -> None:
        await self._context.set_extra_http_headers(headers)

    async def route(self, url: str, handler: Any) -> None:
        await self._context.route(url, handler)

    async def unroute(self, url: str) -> None:
        await self._context.unroute(url)

    async def close(self) -> None:
        await self._context.close()
        self._pages.clear()


class CamoufoxEngine:
    """Camoufox browser engine implementation.

    Camoufox is a Firefox-based anti-detect browser that operates at C++ level,
    making fingerprint changes completely invisible to JavaScript detection.

    Key Features:
    - 0% headless detection (changes happen before JS can inspect)
    - Built-in human-like cursor movement (C++ implementation)
    - Bundled OS fonts (Windows 11 22H2, macOS Sonoma, Linux TOR)
    - WebGL disabled by default (doesn't trigger WAF detection)
    - Playwright-sandboxed Page Agent (invisible to detection)
    - GeoIP-based fingerprint localization

    Advantages over Patchright:
    - Firefox-based (more fingerprint research exists)
    - C++ level spoofing (undetectable via JS)
    - Built-in humanization (no need for separate behavior plugins)

    Usage:
        ```python
        engine = CamoufoxEngine()
        await engine.launch(headless=True)

        context = await engine.new_context(
            config=CamoufoxConfig(os="windows", humanize=True, geoip=True)
        )
        page = await context.new_page()
        await page.goto("https://example.com")
        ```
    """

    name = "camoufox"
    detection_resistance = 10  # Maximum stealth (C++ level)

    # DNS leak prevention prefs for Firefox
    DNS_PROTECTION_PREFS = {
        # Enable DNS over HTTPS (Trusted Recursive Resolver)
        "network.trr.uri": "https://dns.google/dns-query",
        "network.trr.mode": 3,  # 2=strict DoH only, 3=DoH with fallback
        # Disable DNS prefetching (prevents DNS leaks)
        "network.dns.disablePrefetch": True,
        "network.predictor.enabled": False,
        # Force remote DNS for SOCKS proxies
        "network.proxy.socks_remote_dns": True,
        # IPv6 leak prevention - IPv6 can bypass proxy
        "network.dns.disableIPv6": True,
    }

    def __init__(self) -> None:
        self._camoufox: Any = None
        self._browser: Any = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def launch(
        self,
        *,
        headless: bool = True,
        proxy: Proxy | None = None,
        config: CamoufoxConfig | None = None,
        timeout: float = 30000,
    ) -> None:
        """Launch Camoufox browser.

        Args:
            headless: Run in headless mode (still 0% detection)
            proxy: Proxy configuration
            config: Camoufox-specific configuration
            timeout: Launch timeout in ms
        """
        try:
            from camoufox.async_api import AsyncCamoufox
        except ImportError:
            logger.error("Camoufox not installed. Install with: pip install camoufox[geoip]")
            raise ImportError("Camoufox is required but not installed")

        config = config or CamoufoxConfig()

        # Build launch options
        launch_kwargs: dict[str, Any] = {
            "headless": headless,
            "humanize": config.humanize,
        }

        # OS spoofing
        if config.os:
            launch_kwargs["os"] = config.os

        # GeoIP localization
        if config.geoip:
            launch_kwargs["geoip"] = True

        # Screen dimensions
        if config.screen:
            launch_kwargs["screen"] = config.screen

        # Custom fonts
        if config.fonts:
            launch_kwargs["fonts"] = config.fonts

        # Firefox preferences - always include DNS protection prefs
        firefox_prefs = dict(self.DNS_PROTECTION_PREFS)
        if config.firefox_prefs:
            firefox_prefs.update(config.firefox_prefs)
        launch_kwargs["firefox_user_prefs"] = firefox_prefs

        # Addons
        if config.addons:
            launch_kwargs["addons"] = config.addons

        # Proxy at browser level
        if proxy:
            launch_kwargs["proxy"] = {
                "server": proxy.server,
            }
            if proxy.has_auth:
                launch_kwargs["proxy"]["username"] = proxy.username
                launch_kwargs["proxy"]["password"] = proxy.password

        # Launch with async context manager
        self._camoufox = AsyncCamoufox(**launch_kwargs)
        self._browser = await self._camoufox.__aenter__()
        self._running = True

        logger.info(
            "Camoufox browser launched",
            headless=headless,
            os=config.os,
            humanize=config.humanize,
            geoip=config.geoip,
        )

    async def new_context(
        self,
        *,
        fingerprint: Fingerprint | None = None,
        proxy: Proxy | None = None,
        config: CamoufoxConfig | None = None,
        user_agent: str | None = None,
        viewport: dict[str, int] | None = None,
        locale: str = "en-US",
        timezone_id: str | None = None,
        geolocation: dict[str, float] | None = None,
        permissions: list[str] | None = None,
        color_scheme: str | None = None,
        extra_http_headers: dict[str, str] | None = None,
    ) -> CamoufoxContext:
        """Create a new browser context.

        Note: Camoufox handles most fingerprinting at C++ level during launch.
        Context-level settings are still applied for locale/timezone.
        """
        if not self._browser:
            raise RuntimeError("Browser not launched")

        context_options: dict[str, Any] = {
            "locale": locale,
        }

        # Apply fingerprint settings (limited in Camoufox - most is C++ level)
        if fingerprint:
            # Camoufox ignores user_agent (uses C++ generated one)
            context_options["viewport"] = fingerprint.screen.to_viewport()
            context_options["locale"] = fingerprint.locale
            if fingerprint.timezone_id:
                context_options["timezone_id"] = fingerprint.timezone_id
            if fingerprint.geolocation:
                context_options["geolocation"] = fingerprint.geolocation.to_dict()
                context_options["permissions"] = ["geolocation"]
        else:
            # Note: user_agent is ignored by Camoufox (C++ level spoofing)
            if viewport:
                context_options["viewport"] = viewport
            if timezone_id:
                context_options["timezone_id"] = timezone_id
            if geolocation:
                context_options["geolocation"] = geolocation
                context_options["permissions"] = permissions or ["geolocation"]

        if color_scheme:
            context_options["color_scheme"] = color_scheme

        if extra_http_headers:
            context_options["extra_http_headers"] = extra_http_headers

        # Context-level proxy
        if proxy:
            context_options["proxy"] = {
                "server": proxy.server,
            }
            if proxy.has_auth:
                context_options["proxy"]["username"] = proxy.username
                context_options["proxy"]["password"] = proxy.password

        context = await self._browser.new_context(**context_options)
        return CamoufoxContext(context)

    async def close(self) -> None:
        """Close browser and cleanup."""
        if self._camoufox:
            await self._camoufox.__aexit__(None, None, None)
            self._camoufox = None
            self._browser = None

        self._running = False
        logger.info("Camoufox browser closed")

    @staticmethod
    async def install() -> None:
        """Install Camoufox browser binaries.

        Camoufox auto-downloads on first use, but can be pre-installed.
        """
        try:
            import subprocess

            result = subprocess.run(
                ["python", "-c", "import camoufox; camoufox.install()"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                logger.info("Camoufox browser installed")
            else:
                logger.warning("Camoufox install returned non-zero", stderr=result.stderr)
        except Exception as e:
            logger.error("Failed to install Camoufox", error=str(e))
            raise

    @staticmethod
    def get_default_config(
        os: str = "windows",
        stealth_level: str = "high",
    ) -> CamoufoxConfig:
        """Get recommended configuration for stealth.

        Args:
            os: Target OS to spoof (windows, macos, linux)
            stealth_level: Stealth preset (low, medium, high)

        Returns:
            CamoufoxConfig with recommended settings
        """
        if stealth_level == "high":
            return CamoufoxConfig(
                os=os,
                humanize=True,
                geoip=True,
                webgl=False,  # Disabled for max stealth
                firefox_prefs={
                    # Disable telemetry
                    "toolkit.telemetry.enabled": False,
                    "datareporting.healthreport.uploadEnabled": False,
                    # Privacy settings
                    "privacy.resistFingerprinting": False,  # Camoufox handles this
                    "privacy.trackingprotection.enabled": True,
                    # Disable auto-updates
                    "app.update.enabled": False,
                },
            )
        elif stealth_level == "medium":
            return CamoufoxConfig(
                os=os,
                humanize=True,
                geoip=False,
                webgl=False,
            )
        else:  # low
            return CamoufoxConfig(
                os=os,
                humanize=False,
                geoip=False,
                webgl=True,
            )
