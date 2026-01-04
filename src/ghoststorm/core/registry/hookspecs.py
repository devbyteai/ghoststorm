"""Plugin hook specifications using pluggy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pluggy

if TYPE_CHECKING:
    from ghoststorm.core.interfaces.browser import IBrowserContext, IBrowserEngine, IPage
    from ghoststorm.core.interfaces.captcha import ICaptchaSolver
    from ghoststorm.core.interfaces.fingerprint import IFingerprintGenerator
    from ghoststorm.core.interfaces.proxy import IProxyProvider
    from ghoststorm.core.models.config import Config
    from ghoststorm.core.models.fingerprint import Fingerprint
    from ghoststorm.core.models.proxy import Proxy
    from ghoststorm.core.models.task import Task, TaskResult

# Plugin markers
hookspec = pluggy.HookspecMarker("ghoststorm")
hookimpl = pluggy.HookimplMarker("ghoststorm")


class GhostStormSpecs:
    """Hook specifications for the plugin system."""

    # =========================================================================
    # Engine Lifecycle Hooks
    # =========================================================================

    @hookspec
    async def on_engine_start(self, config: Config) -> None:
        """Called when the engine starts."""
        ...

    @hookspec
    async def on_engine_stop(self) -> None:
        """Called when the engine stops."""
        ...

    @hookspec
    async def on_engine_error(self, error: Exception) -> None:
        """Called when the engine encounters an error."""
        ...

    # =========================================================================
    # Browser Lifecycle Hooks
    # =========================================================================

    @hookspec
    async def before_browser_launch(
        self,
        engine_name: str,
        options: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Called before browser launch.

        Can modify launch options by returning a new dict.
        """
        ...

    @hookspec
    async def after_browser_launch(
        self,
        engine: IBrowserEngine,
    ) -> None:
        """Called after browser launch."""
        ...

    @hookspec
    async def before_context_create(
        self,
        options: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Called before creating a browser context.

        Can modify context options by returning a new dict.
        """
        ...

    @hookspec
    async def after_context_create(
        self,
        context: IBrowserContext,
    ) -> None:
        """Called after creating a browser context."""
        ...

    # =========================================================================
    # Page Lifecycle Hooks
    # =========================================================================

    @hookspec
    async def before_page_load(
        self,
        page: IPage,
        url: str,
    ) -> str | None:
        """
        Called before loading a page.

        Can modify the URL by returning a new string.
        """
        ...

    @hookspec
    async def after_page_load(
        self,
        page: IPage,
        url: str,
    ) -> None:
        """Called after page loads."""
        ...

    @hookspec
    async def on_page_error(
        self,
        page: IPage,
        error: Exception,
    ) -> None:
        """Called when a page error occurs."""
        ...

    # =========================================================================
    # Task Lifecycle Hooks
    # =========================================================================

    @hookspec
    async def before_task_execute(
        self,
        task: Task,
    ) -> Task | None:
        """
        Called before task execution.

        Can modify the task by returning a new Task.
        """
        ...

    @hookspec
    async def after_task_execute(
        self,
        task: Task,
        result: TaskResult,
    ) -> None:
        """Called after task execution."""
        ...

    @hookspec
    async def on_task_error(
        self,
        task: Task,
        error: Exception,
    ) -> None:
        """Called when a task error occurs."""
        ...

    @hookspec
    async def on_task_retry(
        self,
        task: Task,
        attempt: int,
    ) -> None:
        """Called when a task is retried."""
        ...

    # =========================================================================
    # Modification Hooks
    # =========================================================================

    @hookspec
    async def modify_fingerprint(
        self,
        fingerprint: Fingerprint,
    ) -> Fingerprint | None:
        """
        Called to modify a fingerprint before use.

        Return modified fingerprint or None to keep original.
        """
        ...

    @hookspec
    async def modify_request(
        self,
        url: str,
        headers: dict[str, str],
    ) -> dict[str, Any] | None:
        """
        Called to modify outgoing requests.

        Return dict with 'url' and 'headers' keys to modify.
        """
        ...

    @hookspec
    async def modify_response(
        self,
        url: str,
        status: int,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any] | None:
        """
        Called to modify responses.

        Return dict with modified values or None.
        """
        ...

    # =========================================================================
    # Detection Hooks
    # =========================================================================

    @hookspec
    async def on_captcha_detected(
        self,
        page: IPage,
        captcha_type: str,
    ) -> bool:
        """
        Called when a CAPTCHA is detected.

        Return True if handled, False otherwise.
        """
        ...

    @hookspec
    async def on_bot_detected(
        self,
        page: IPage,
        detection_type: str,
    ) -> None:
        """Called when bot detection is triggered."""
        ...

    @hookspec
    async def on_rate_limited(
        self,
        page: IPage,
        retry_after: float | None,
    ) -> None:
        """Called when rate limiting is detected."""
        ...

    # =========================================================================
    # Proxy Hooks
    # =========================================================================

    @hookspec
    async def on_proxy_failure(
        self,
        proxy: Proxy,
        error: Exception,
    ) -> Proxy | None:
        """
        Called when a proxy fails.

        Return a replacement proxy or None.
        """
        ...

    @hookspec
    async def on_proxy_success(
        self,
        proxy: Proxy,
        latency_ms: float,
    ) -> None:
        """Called when a proxy succeeds."""
        ...

    # =========================================================================
    # Data Hooks
    # =========================================================================

    @hookspec
    async def on_data_extracted(
        self,
        url: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Called when data is extracted.

        Return modified data or None.
        """
        ...

    @hookspec
    async def on_screenshot_captured(
        self,
        url: str,
        screenshot_data: bytes,
    ) -> None:
        """Called when a screenshot is captured."""
        ...

    # =========================================================================
    # Provider Registration Hooks
    # =========================================================================

    @hookspec
    def register_browser_engines(self) -> list[type[IBrowserEngine]]:
        """
        Register browser engine implementations.

        Return list of browser engine classes.
        """
        ...

    @hookspec
    def register_proxy_providers(self) -> list[type[IProxyProvider]]:
        """
        Register proxy provider implementations.

        Return list of proxy provider classes.
        """
        ...

    @hookspec
    def register_fingerprint_generators(self) -> list[type[IFingerprintGenerator]]:
        """
        Register fingerprint generator implementations.

        Return list of fingerprint generator classes.
        """
        ...

    @hookspec
    def register_captcha_solvers(self) -> list[type[ICaptchaSolver]]:
        """
        Register CAPTCHA solver implementations.

        Return list of CAPTCHA solver classes.
        """
        ...

    # =========================================================================
    # CLI Hooks
    # =========================================================================

    @hookspec
    def register_cli_commands(self, app: Any) -> None:
        """
        Register CLI commands.

        Args:
            app: Typer application instance
        """
        ...

    # =========================================================================
    # Stealth Hooks
    # =========================================================================

    @hookspec
    async def inject_stealth_scripts(
        self,
        page: IPage,
        fingerprint: Fingerprint | None,
    ) -> None:
        """
        Inject stealth/anti-detection scripts into page.

        Called before page navigation.
        """
        ...

    @hookspec
    async def setup_request_interception(
        self,
        context: IBrowserContext,
    ) -> None:
        """
        Set up request interception for a context.

        Called after context creation.
        """
        ...

    # =========================================================================
    # LLM Hooks
    # =========================================================================

    @hookspec
    async def on_llm_decision(
        self,
        task: Task,
        analysis: dict[str, Any],
        action: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """
        Called when LLM makes a decision about browser action.

        Args:
            task: Current task being executed
            analysis: LLM's analysis of the page
            action: Suggested action (or None if task complete)

        Return modified action or None to keep original.
        """
        ...

    @hookspec
    async def on_llm_task_complete(
        self,
        task: Task,
        result: dict[str, Any],
    ) -> None:
        """Called when LLM completes autonomous task execution."""
        ...

    # =========================================================================
    # DOM Hooks
    # =========================================================================

    @hookspec
    async def on_dom_extracted(
        self,
        page: IPage,
        url: str,
        dom_state: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Called when DOM is extracted from a page.

        Args:
            page: The browser page
            url: Current page URL
            dom_state: Extracted DOM state

        Return modified DOM state or None to keep original.
        """
        ...

    @hookspec
    async def on_element_found(
        self,
        page: IPage,
        selector: str,
        element_info: dict[str, Any],
    ) -> None:
        """Called when an element is found via DOM analysis."""
        ...
