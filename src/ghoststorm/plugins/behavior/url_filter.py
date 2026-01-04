"""URL filtering with blacklist/whitelist pattern matching."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class URLFilterConfig:
    """Configuration for URL filtering."""

    blacklist_file: str | None = None
    blacklist_patterns: list[str] = field(default_factory=list)
    whitelist_patterns: list[str] = field(default_factory=list)
    block_external: bool = False
    block_subdomains: bool = False
    use_default_blacklist: bool = True


class URLFilter:
    """Filter URLs based on regex patterns.

    Supports:
    - Blacklist patterns (URLs matching are blocked)
    - Whitelist patterns (if set, only matching URLs allowed)
    - External domain blocking
    - Subdomain blocking
    - Loading patterns from files

    Usage:
        ```python
        config = URLFilterConfig(
            blacklist_patterns=["login", "signup"],
            block_external=True,
        )
        filter = URLFilter(config)

        urls = ["https://example.com/page", "https://example.com/login"]
        allowed = filter.filter_urls(urls, base_domain="example.com")
        # Returns: ["https://example.com/page"]
        ```
    """

    name = "url_filter"

    DEFAULT_BLACKLIST = [
        # Auth pages
        r"login", r"signin", r"sign-in", r"signup", r"sign-up",
        r"register", r"logout", r"auth", r"oauth", r"password", r"forgot",
        # Search/filter
        r"search", r"filter", r"\?q=", r"\?query=",
        # External social
        r"facebook\.com", r"twitter\.com", r"x\.com", r"instagram\.com",
        r"linkedin\.com", r"youtube\.com", r"tiktok\.com",
        # Technical
        r"^mailto:", r"^javascript:", r"^tel:", r"^sms:",
        r"^data:", r"^blob:", r"^#$",
        # Files
        r"\.pdf$", r"\.zip$", r"\.exe$", r"\.dmg$",
        r"\.doc$", r"\.docx$", r"\.xls$", r"\.xlsx$",
        # Legal
        r"privacy-policy", r"terms-of-service", r"cookie-policy",
        r"unsubscribe", r"opt-out",
        # Commerce
        r"cart", r"checkout", r"add-to-cart",
        # Admin
        r"/admin", r"/wp-admin", r"/dashboard",
        # API
        r"/api/", r"\.json$", r"\.xml$",
    ]

    def __init__(self, config: URLFilterConfig | None = None) -> None:
        """Initialize URL filter.

        Args:
            config: Filter configuration
        """
        self.config = config or URLFilterConfig()
        self._blacklist_patterns: list[re.Pattern] = []
        self._whitelist_patterns: list[re.Pattern] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        patterns = list(self.config.blacklist_patterns)

        # Add default blacklist
        if self.config.use_default_blacklist:
            patterns.extend(self.DEFAULT_BLACKLIST)

        # Load from file
        if self.config.blacklist_file:
            patterns.extend(self._load_patterns_from_file(self.config.blacklist_file))

        # Compile blacklist
        for pattern in patterns:
            try:
                self._blacklist_patterns.append(
                    re.compile(pattern, re.IGNORECASE)
                )
            except re.error:
                pass

        # Compile whitelist
        for pattern in self.config.whitelist_patterns:
            try:
                self._whitelist_patterns.append(
                    re.compile(pattern, re.IGNORECASE)
                )
            except re.error:
                pass

    def _load_patterns_from_file(self, filepath: str) -> list[str]:
        """Load patterns from a text file.

        Args:
            filepath: Path to patterns file

        Returns:
            List of pattern strings
        """
        patterns = []
        path = Path(filepath)

        if not path.exists():
            return patterns

        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception:
            pass

        return patterns

    def _get_domain(self, url: str) -> str | None:
        """Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain string or None
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None

    def _get_root_domain(self, domain: str) -> str:
        """Extract root domain from full domain.

        Args:
            domain: Full domain (e.g., sub.example.com)

        Returns:
            Root domain (e.g., example.com)
        """
        parts = domain.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return domain

    def _is_external(self, url: str, base_domain: str) -> bool:
        """Check if URL is external to base domain.

        Args:
            url: URL to check
            base_domain: Base domain to compare against

        Returns:
            True if external
        """
        url_domain = self._get_domain(url)
        if not url_domain:
            return False

        base_root = self._get_root_domain(base_domain)
        url_root = self._get_root_domain(url_domain)

        return url_root != base_root

    def _is_subdomain(self, url: str, base_domain: str) -> bool:
        """Check if URL is on a subdomain.

        Args:
            url: URL to check
            base_domain: Base domain to compare against

        Returns:
            True if on subdomain
        """
        url_domain = self._get_domain(url)
        if not url_domain:
            return False

        # Same domain is not a subdomain
        if url_domain == base_domain:
            return False

        # Check if URL domain ends with base domain
        base_root = self._get_root_domain(base_domain)
        url_root = self._get_root_domain(url_domain)

        if url_root == base_root and url_domain != base_domain:
            return True

        return False

    def _matches_blacklist(self, url: str) -> bool:
        """Check if URL matches any blacklist pattern.

        Args:
            url: URL to check

        Returns:
            True if matches blacklist
        """
        for pattern in self._blacklist_patterns:
            if pattern.search(url):
                return True
        return False

    def _matches_whitelist(self, url: str) -> bool:
        """Check if URL matches any whitelist pattern.

        Args:
            url: URL to check

        Returns:
            True if matches whitelist
        """
        if not self._whitelist_patterns:
            return True  # No whitelist means all allowed

        for pattern in self._whitelist_patterns:
            if pattern.search(url):
                return True
        return False

    def is_allowed(self, url: str, base_domain: str | None = None) -> bool:
        """Check if URL is allowed by all filters.

        Args:
            url: URL to check
            base_domain: Base domain for external/subdomain checks

        Returns:
            True if URL passes all filters
        """
        # Whitelist check (must match if whitelist is set)
        if not self._matches_whitelist(url):
            return False

        # Blacklist check
        if self._matches_blacklist(url):
            return False

        # External domain check
        if base_domain and self.config.block_external:
            if self._is_external(url, base_domain):
                return False

        # Subdomain check
        if base_domain and self.config.block_subdomains:
            if self._is_subdomain(url, base_domain):
                return False

        return True

    def filter_urls(
        self,
        urls: list[str],
        base_domain: str | None = None,
    ) -> list[str]:
        """Filter list of URLs.

        Args:
            urls: List of URLs to filter
            base_domain: Base domain for context

        Returns:
            List of allowed URLs
        """
        return [url for url in urls if self.is_allowed(url, base_domain)]

    def add_blacklist_pattern(self, pattern: str) -> bool:
        """Add a pattern to the blacklist at runtime.

        Args:
            pattern: Regex pattern to add

        Returns:
            True if pattern was added successfully
        """
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            self._blacklist_patterns.append(compiled)
            return True
        except re.error:
            return False

    def add_whitelist_pattern(self, pattern: str) -> bool:
        """Add a pattern to the whitelist at runtime.

        Args:
            pattern: Regex pattern to add

        Returns:
            True if pattern was added successfully
        """
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            self._whitelist_patterns.append(compiled)
            return True
        except re.error:
            return False

    def clear_blacklist(self) -> None:
        """Clear all blacklist patterns."""
        self._blacklist_patterns.clear()

    def clear_whitelist(self) -> None:
        """Clear all whitelist patterns."""
        self._whitelist_patterns.clear()

    @property
    def blacklist_count(self) -> int:
        """Number of blacklist patterns."""
        return len(self._blacklist_patterns)

    @property
    def whitelist_count(self) -> int:
        """Number of whitelist patterns."""
        return len(self._whitelist_patterns)
