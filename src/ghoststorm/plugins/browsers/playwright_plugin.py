"""Playwright browser engine - vanilla implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ghoststorm.core.models.fingerprint import Fingerprint
    from ghoststorm.core.models.proxy import Proxy

logger = structlog.get_logger(__name__)


class PlaywrightPage:
    """Wrapper around Playwright page."""

    def __init__(self, page: Any) -> None:
        self._page = page

    @property
    def url(self) -> str:
        return self._page.url

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

    async def close(self) -> None:
        await self._page.close()


class PlaywrightContext:
    """Wrapper around Playwright browser context."""

    def __init__(self, context: Any) -> None:
        self._context = context
        self._pages: list[PlaywrightPage] = []

    @property
    def pages(self) -> list[PlaywrightPage]:
        return self._pages

    async def new_page(self) -> PlaywrightPage:
        page = await self._context.new_page()
        wrapped = PlaywrightPage(page)
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


class PlaywrightEngine:
    """Playwright browser engine implementation (vanilla)."""

    name = "playwright"
    detection_resistance = 5  # Medium stealth (standard Playwright)

    # DNS/IP leak prevention args
    DNS_PROTECTION_ARGS = [
        '--dns-over-https-templates={"servers":[{"template":"https://dns.google/dns-query{?dns}","endpoints":[{"ips":["8.8.8.8","8.8.4.4"]}]}]}',
        "--enable-features=DnsOverHttps",
        # IPv6 leak prevention - IPv6 can bypass proxy
        "--disable-ipv6",
        # WebRTC leak prevention - WebRTC can expose real IP even through proxy
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--disable-features=WebRtcHideLocalIpsWithMdns",
    ]

    def __init__(self) -> None:
        self._playwright: Any = None
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
        args: list[str] | None = None,
        slow_mo: float = 0,
        timeout: float = 30000,
    ) -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed. Install with: pip install playwright")
            raise ImportError("Playwright is required but not installed")

        self._playwright = await async_playwright().start()

        # Build launch args with DNS protection
        launch_args = list(self.DNS_PROTECTION_ARGS)
        if args:
            launch_args.extend(args)

        launch_options: dict[str, Any] = {
            "headless": headless,
            "slow_mo": slow_mo,
            "args": launch_args,
        }

        if proxy:
            launch_options["proxy"] = {
                "server": proxy.server,
            }
            if proxy.has_auth:
                launch_options["proxy"]["username"] = proxy.username
                launch_options["proxy"]["password"] = proxy.password

        self._browser = await self._playwright.chromium.launch(**launch_options)
        self._running = True

        logger.info("Playwright browser launched", headless=headless)

    async def new_context(
        self,
        *,
        fingerprint: Fingerprint | None = None,
        proxy: Proxy | None = None,
        user_agent: str | None = None,
        viewport: dict[str, int] | None = None,
        locale: str = "en-US",
        timezone_id: str | None = None,
        geolocation: dict[str, float] | None = None,
        permissions: list[str] | None = None,
        color_scheme: str | None = None,
        extra_http_headers: dict[str, str] | None = None,
    ) -> PlaywrightContext:
        if not self._browser:
            raise RuntimeError("Browser not launched")

        context_options: dict[str, Any] = {
            "locale": locale,
        }

        # Apply fingerprint settings
        if fingerprint:
            context_options["user_agent"] = fingerprint.user_agent
            context_options["viewport"] = fingerprint.screen.to_viewport()
            context_options["locale"] = fingerprint.locale
            if fingerprint.timezone_id:
                context_options["timezone_id"] = fingerprint.timezone_id
            if fingerprint.geolocation:
                context_options["geolocation"] = fingerprint.geolocation.to_dict()
                context_options["permissions"] = ["geolocation"]
        else:
            if user_agent:
                context_options["user_agent"] = user_agent
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

        if proxy:
            context_options["proxy"] = {
                "server": proxy.server,
            }
            if proxy.has_auth:
                context_options["proxy"]["username"] = proxy.username
                context_options["proxy"]["password"] = proxy.password

        context = await self._browser.new_context(**context_options)
        return PlaywrightContext(context)

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        self._running = False
        logger.info("Playwright browser closed")

    async def install(self) -> None:
        """Install browser binaries."""
        import subprocess

        subprocess.run(["playwright", "install", "chromium"], check=True)
        logger.info("Playwright chromium installed")
