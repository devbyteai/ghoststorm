"""TLS Client with browser fingerprint impersonation using curl_cffi.

This module provides HTTP client capabilities with TLS/JA3/JA4 fingerprint
impersonation to bypass network-level bot detection.

Unlike browser automation, this is for direct HTTP requests that need
to appear as if they're coming from a real browser at the TLS layer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# Randomized Accept-Language values to prevent cross-session tracking
# Each request gets a random value to avoid fingerprinting via static headers
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-US,en;q=0.8",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "en;q=0.9,en-US;q=0.8",
    "en-US,en;q=0.9,es;q=0.8",
    "en-US,en;q=0.9,fr;q=0.7",
    "en-US,en;q=0.9,de;q=0.7",
    "en-GB,en-US;q=0.9,en;q=0.8",
    "en-US;q=0.9,en;q=0.8",
    "en,en-US;q=0.9",
]

# Randomized Accept header variants to prevent fingerprinting
ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
]

# Randomized cache control (some browsers don't send these)
CACHE_CONTROL_OPTIONS = [
    ("Cache-Control", "no-cache"),
    ("Cache-Control", "max-age=0"),
    (None, None),  # Some requests don't include cache headers
]

# Randomized Sec-Fetch-Site variants
SEC_FETCH_SITE_OPTIONS = [
    "none",
    "same-origin",
    "cross-site",
]


def _get_random_accept_language() -> str:
    """Get a randomized Accept-Language header value."""
    return random.choice(ACCEPT_LANGUAGES)


def _get_random_headers() -> dict[str, str]:
    """Get randomized HTTP headers to prevent fingerprinting."""
    headers = {
        "Accept": random.choice(ACCEPT_HEADERS),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": _get_random_accept_language(),
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": random.choice(SEC_FETCH_SITE_OPTIONS),
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

    # Randomly include or exclude cache headers
    cache_option = random.choice(CACHE_CONTROL_OPTIONS)
    if cache_option[0]:
        headers[cache_option[0]] = cache_option[1]
        # Pragma typically accompanies Cache-Control
        if random.random() > 0.3:
            headers["Pragma"] = "no-cache"

    return headers


class BrowserProfile(str, Enum):
    """Available browser profiles for TLS impersonation.

    curl_cffi supports impersonating various browser versions.
    Use the latest versions for best compatibility.
    """

    # Chrome versions (most common, best support)
    CHROME = "chrome"  # Latest available
    CHROME_136 = "chrome136"
    CHROME_133 = "chrome133a"
    CHROME_131 = "chrome131"
    CHROME_124 = "chrome124"
    CHROME_120 = "chrome120"
    CHROME_119 = "chrome119"
    CHROME_116 = "chrome116"
    CHROME_110 = "chrome110"
    CHROME_107 = "chrome107"
    CHROME_104 = "chrome104"
    CHROME_101 = "chrome101"
    CHROME_100 = "chrome100"
    CHROME_99 = "chrome99"

    # Safari versions
    SAFARI = "safari"
    SAFARI_15_3 = "safari15_3"
    SAFARI_15_5 = "safari15_5"

    # Edge (uses Chrome TLS stack)
    EDGE = "edge"
    EDGE_99 = "edge99"
    EDGE_101 = "edge101"


@dataclass
class TLSClientConfig:
    """Configuration for TLS client."""

    # Browser profile to impersonate
    profile: BrowserProfile = BrowserProfile.CHROME

    # Request timeout in seconds
    timeout: float = 30.0

    # Follow redirects
    follow_redirects: bool = True
    max_redirects: int = 10

    # Verify SSL certificates
    verify_ssl: bool = True

    # HTTP/2 support (enabled by default with curl_cffi)
    http2: bool = True

    # HTTP/3 support (experimental)
    http3: bool = False

    # Proxy settings
    proxy: str | None = None

    # Default headers (merged with request headers)
    # Note: Accept-Language is randomized per-request in _merge_headers()
    default_headers: dict[str, str] = field(default_factory=lambda: {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    })

    # Cookie jar persistence
    persist_cookies: bool = True


@dataclass
class TLSResponse:
    """Response from TLS client."""

    status_code: int
    headers: dict[str, str]
    text: str
    content: bytes
    url: str
    cookies: dict[str, str]
    elapsed: float  # seconds
    http_version: str


class TLSClient:
    """HTTP client with TLS fingerprint impersonation.

    Uses curl_cffi to impersonate real browser TLS fingerprints,
    bypassing JA3/JA4 fingerprint detection at the network level.

    Key Features:
    - Impersonates Chrome, Safari, Edge TLS fingerprints
    - HTTP/2 and HTTP/3 support
    - Session persistence with cookies
    - Proxy support with authentication
    - Async and sync APIs

    Usage:
        ```python
        # Async usage
        client = TLSClient(TLSClientConfig(profile=BrowserProfile.CHROME_136))
        await client.init()

        response = await client.get("https://example.com")
        print(response.status_code)

        await client.close()

        # Or use context manager
        async with TLSClient() as client:
            response = await client.get("https://example.com")
        ```
    """

    def __init__(self, config: TLSClientConfig | None = None) -> None:
        """Initialize TLS client.

        Args:
            config: Client configuration
        """
        self.config = config or TLSClientConfig()
        self._session: Any = None
        self._initialized = False

    async def init(self) -> None:
        """Initialize the HTTP session."""
        if self._initialized:
            return

        try:
            from curl_cffi.requests import AsyncSession
        except ImportError:
            logger.error(
                "curl_cffi not installed. Install with: pip install curl_cffi"
            )
            raise ImportError("curl_cffi is required but not installed")

        session_kwargs: dict[str, Any] = {
            "impersonate": self.config.profile.value,
            "timeout": self.config.timeout,
            "verify": self.config.verify_ssl,
            "max_redirects": self.config.max_redirects,
        }

        if self.config.proxy:
            session_kwargs["proxies"] = {
                "http": self.config.proxy,
                "https": self.config.proxy,
            }

        self._session = AsyncSession(**session_kwargs)
        self._initialized = True

        logger.info(
            "TLS client initialized",
            profile=self.config.profile.value,
            http2=self.config.http2,
        )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False

    async def __aenter__(self) -> TLSClient:
        await self.init()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def _merge_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        """Merge custom headers with randomized values to prevent fingerprinting."""
        # Get fresh randomized headers for each request
        merged = _get_random_headers()
        # Apply any custom headers from caller (override randomized ones)
        if headers:
            merged.update(headers)
        return merged

    def _parse_response(self, response: Any, elapsed: float) -> TLSResponse:
        """Parse curl_cffi response into TLSResponse."""
        return TLSResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            text=response.text,
            content=response.content,
            url=str(response.url),
            cookies={k: v for k, v in response.cookies.items()},
            elapsed=elapsed,
            http_version=getattr(response, "http_version", "HTTP/2"),
        )

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> TLSResponse:
        """Make GET request.

        Args:
            url: Request URL
            headers: Additional headers
            params: Query parameters
            timeout: Request timeout (overrides config)

        Returns:
            TLSResponse object
        """
        if not self._initialized:
            await self.init()

        import time
        start = time.monotonic()

        response = await self._session.get(
            url,
            headers=self._merge_headers(headers),
            params=params,
            timeout=timeout or self.config.timeout,
            allow_redirects=self.config.follow_redirects,
        )

        elapsed = time.monotonic() - start
        return self._parse_response(response, elapsed)

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | str | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> TLSResponse:
        """Make POST request.

        Args:
            url: Request URL
            headers: Additional headers
            data: Form data or raw body
            json: JSON body (auto-sets Content-Type)
            timeout: Request timeout

        Returns:
            TLSResponse object
        """
        if not self._initialized:
            await self.init()

        import time
        start = time.monotonic()

        response = await self._session.post(
            url,
            headers=self._merge_headers(headers),
            data=data,
            json=json,
            timeout=timeout or self.config.timeout,
            allow_redirects=self.config.follow_redirects,
        )

        elapsed = time.monotonic() - start
        return self._parse_response(response, elapsed)

    async def put(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | str | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> TLSResponse:
        """Make PUT request."""
        if not self._initialized:
            await self.init()

        import time
        start = time.monotonic()

        response = await self._session.put(
            url,
            headers=self._merge_headers(headers),
            data=data,
            json=json,
            timeout=timeout or self.config.timeout,
            allow_redirects=self.config.follow_redirects,
        )

        elapsed = time.monotonic() - start
        return self._parse_response(response, elapsed)

    async def delete(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> TLSResponse:
        """Make DELETE request."""
        if not self._initialized:
            await self.init()

        import time
        start = time.monotonic()

        response = await self._session.delete(
            url,
            headers=self._merge_headers(headers),
            timeout=timeout or self.config.timeout,
            allow_redirects=self.config.follow_redirects,
        )

        elapsed = time.monotonic() - start
        return self._parse_response(response, elapsed)

    async def head(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> TLSResponse:
        """Make HEAD request."""
        if not self._initialized:
            await self.init()

        import time
        start = time.monotonic()

        response = await self._session.head(
            url,
            headers=self._merge_headers(headers),
            timeout=timeout or self.config.timeout,
            allow_redirects=self.config.follow_redirects,
        )

        elapsed = time.monotonic() - start
        return self._parse_response(response, elapsed)

    def set_proxy(self, proxy: str | None) -> None:
        """Update proxy settings.

        Args:
            proxy: Proxy URL (e.g., "http://user:pass@host:port") or None
        """
        self.config.proxy = proxy
        # Session will use new proxy on next request if re-initialized

    def set_profile(self, profile: BrowserProfile) -> None:
        """Change browser profile (requires re-init).

        Args:
            profile: New browser profile to impersonate
        """
        self.config.profile = profile
        # Mark for re-initialization
        self._initialized = False

    @staticmethod
    def get_supported_profiles() -> list[str]:
        """Get list of supported browser profiles."""
        return [p.value for p in BrowserProfile]


# Convenience function for quick requests
async def fetch(
    url: str,
    *,
    method: str = "GET",
    profile: BrowserProfile = BrowserProfile.CHROME,
    headers: dict[str, str] | None = None,
    data: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    proxy: str | None = None,
    timeout: float = 30.0,
) -> TLSResponse:
    """Quick fetch with TLS impersonation.

    Args:
        url: Request URL
        method: HTTP method
        profile: Browser profile to impersonate
        headers: Request headers
        data: Form data
        json: JSON body
        proxy: Proxy URL
        timeout: Request timeout

    Returns:
        TLSResponse object
    """
    config = TLSClientConfig(profile=profile, proxy=proxy, timeout=timeout)
    async with TLSClient(config) as client:
        if method.upper() == "GET":
            return await client.get(url, headers=headers)
        elif method.upper() == "POST":
            return await client.post(url, headers=headers, data=data, json=json)
        elif method.upper() == "PUT":
            return await client.put(url, headers=headers, data=data, json=json)
        elif method.upper() == "DELETE":
            return await client.delete(url, headers=headers)
        elif method.upper() == "HEAD":
            return await client.head(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
