"""Browser engine interface definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ghoststorm.core.models.fingerprint import Fingerprint
    from ghoststorm.core.models.proxy import Proxy


@runtime_checkable
class IPage(Protocol):
    """Contract for page interactions."""

    @property
    def url(self) -> str:
        """Current page URL."""
        ...

    async def goto(
        self,
        url: str,
        *,
        wait_until: str = "load",
        timeout: float | None = None,
        referer: str | None = None,
    ) -> None:
        """Navigate to a URL."""
        ...

    async def click(
        self,
        selector: str,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float | None = None,
        timeout: float | None = None,
    ) -> None:
        """Click an element."""
        ...

    async def type(
        self,
        selector: str,
        text: str,
        *,
        delay: float | None = None,
        timeout: float | None = None,
    ) -> None:
        """Type text into an element."""
        ...

    async def fill(
        self,
        selector: str,
        value: str,
        *,
        timeout: float | None = None,
    ) -> None:
        """Fill an input element."""
        ...

    async def screenshot(
        self,
        *,
        path: str | None = None,
        full_page: bool = False,
        type: str = "png",
        quality: int | None = None,
    ) -> bytes:
        """Take a screenshot."""
        ...

    async def evaluate(self, expression: str, *args: Any) -> Any:
        """Evaluate JavaScript in the page context."""
        ...

    async def wait_for_selector(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: float | None = None,
    ) -> Any:
        """Wait for a selector to appear."""
        ...

    async def wait_for_load_state(
        self,
        state: str = "load",
        *,
        timeout: float | None = None,
    ) -> None:
        """Wait for page load state."""
        ...

    async def content(self) -> str:
        """Get page HTML content."""
        ...

    async def title(self) -> str:
        """Get page title."""
        ...

    async def query_selector(self, selector: str) -> Any | None:
        """Query for a single element."""
        ...

    async def query_selector_all(self, selector: str) -> list[Any]:
        """Query for all matching elements."""
        ...

    async def scroll(
        self,
        *,
        x: int = 0,
        y: int = 0,
        behavior: str = "smooth",
    ) -> None:
        """Scroll the page."""
        ...

    async def close(self) -> None:
        """Close the page."""
        ...


@runtime_checkable
class IBrowserContext(Protocol):
    """Contract for browser context (isolated session)."""

    @property
    def pages(self) -> list[IPage]:
        """List of pages in this context."""
        ...

    async def new_page(self) -> IPage:
        """Create a new page in this context."""
        ...

    async def cookies(self, urls: list[str] | None = None) -> list[dict[str, Any]]:
        """Get cookies."""
        ...

    async def add_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """Add cookies."""
        ...

    async def clear_cookies(self) -> None:
        """Clear all cookies."""
        ...

    async def set_extra_http_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers for all requests."""
        ...

    async def route(
        self,
        url: str,
        handler: Any,
    ) -> None:
        """Set up request interception."""
        ...

    async def unroute(self, url: str) -> None:
        """Remove request interception."""
        ...

    async def close(self) -> None:
        """Close the context and all its pages."""
        ...


@runtime_checkable
class IBrowserEngine(Protocol):
    """Contract for all browser engine implementations."""

    @property
    def name(self) -> str:
        """Engine name (e.g., 'patchright', 'camoufox')."""
        ...

    @property
    def detection_resistance(self) -> int:
        """1-10 scale of stealth capability."""
        ...

    @property
    def is_running(self) -> bool:
        """Whether the browser is currently running."""
        ...

    async def launch(
        self,
        *,
        headless: bool = True,
        proxy: Proxy | None = None,
        args: list[str] | None = None,
        slow_mo: float = 0,
        timeout: float = 30000,
    ) -> None:
        """Launch the browser."""
        ...

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
    ) -> IBrowserContext:
        """Create a new isolated browser context."""
        ...

    async def close(self) -> None:
        """Close the browser and all contexts."""
        ...

    async def install(self) -> None:
        """Install browser binaries if needed."""
        ...
