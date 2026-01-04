"""CAPTCHA solver interface definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ghoststorm.core.interfaces.browser import IPage


@runtime_checkable
class ICaptchaSolver(Protocol):
    """Contract for CAPTCHA solvers."""

    @property
    def name(self) -> str:
        """Solver name."""
        ...

    @property
    def supported_types(self) -> list[str]:
        """List of supported CAPTCHA types."""
        ...

    @property
    def balance(self) -> float | None:
        """Current account balance (if applicable)."""
        ...

    async def initialize(self) -> None:
        """Initialize the solver (validate API key, etc.)."""
        ...

    async def solve_recaptcha_v2(
        self,
        *,
        site_key: str,
        page_url: str,
        invisible: bool = False,
        data_s: str | None = None,
        timeout: float = 120.0,
    ) -> str:
        """
        Solve reCAPTCHA v2.

        Args:
            site_key: reCAPTCHA site key
            page_url: URL of the page with CAPTCHA
            invisible: Whether it's invisible reCAPTCHA
            data_s: data-s parameter if present
            timeout: Maximum time to wait for solution

        Returns:
            The g-recaptcha-response token
        """
        ...

    async def solve_recaptcha_v3(
        self,
        *,
        site_key: str,
        page_url: str,
        action: str = "verify",
        min_score: float = 0.7,
        timeout: float = 120.0,
    ) -> str:
        """
        Solve reCAPTCHA v3.

        Args:
            site_key: reCAPTCHA site key
            page_url: URL of the page
            action: Action name
            min_score: Minimum score required
            timeout: Maximum time to wait

        Returns:
            The g-recaptcha-response token
        """
        ...

    async def solve_hcaptcha(
        self,
        *,
        site_key: str,
        page_url: str,
        invisible: bool = False,
        timeout: float = 120.0,
    ) -> str:
        """
        Solve hCaptcha.

        Args:
            site_key: hCaptcha site key
            page_url: URL of the page
            invisible: Whether it's invisible hCaptcha
            timeout: Maximum time to wait

        Returns:
            The h-captcha-response token
        """
        ...

    async def solve_turnstile(
        self,
        *,
        site_key: str,
        page_url: str,
        action: str | None = None,
        timeout: float = 120.0,
    ) -> str:
        """
        Solve Cloudflare Turnstile.

        Args:
            site_key: Turnstile site key
            page_url: URL of the page
            action: Optional action parameter
            timeout: Maximum time to wait

        Returns:
            The cf-turnstile-response token
        """
        ...

    async def solve_image_captcha(
        self,
        *,
        image_base64: str,
        timeout: float = 60.0,
    ) -> str:
        """
        Solve image-based CAPTCHA.

        Args:
            image_base64: Base64 encoded image
            timeout: Maximum time to wait

        Returns:
            The text solution
        """
        ...

    async def detect_and_solve(
        self,
        page: IPage,
        *,
        timeout: float = 120.0,
    ) -> bool:
        """
        Automatically detect and solve CAPTCHA on page.

        Args:
            page: The page to check for CAPTCHA
            timeout: Maximum time to wait

        Returns:
            True if CAPTCHA was found and solved, False if no CAPTCHA
        """
        ...

    async def report_incorrect(self, task_id: str) -> bool:
        """Report an incorrect solution for refund."""
        ...

    async def get_balance(self) -> float:
        """Get current account balance."""
        ...

    async def close(self) -> None:
        """Clean up solver resources."""
        ...
