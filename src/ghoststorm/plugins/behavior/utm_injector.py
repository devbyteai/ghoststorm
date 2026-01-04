"""UTM parameter injection for traffic attribution."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


@dataclass
class UTMConfig:
    """Configuration for UTM parameter injection."""

    enabled: bool = True

    sources: list[str] = field(
        default_factory=lambda: [
            "google",
            "facebook",
            "twitter",
            "instagram",
            "bing",
            "yahoo",
            "linkedin",
            "reddit",
            "pinterest",
            "tiktok",
            "youtube",
            "duckduckgo",
            "baidu",
            "yandex",
        ]
    )

    mediums: list[str] = field(
        default_factory=lambda: [
            "cpc",
            "organic",
            "referral",
            "social",
            "email",
            "display",
            "affiliate",
            "banner",
            "ppc",
        ]
    )

    campaigns: list[str] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)
    contents: list[str] = field(default_factory=list)

    # Probability settings
    include_campaign_probability: float = 0.3
    include_term_probability: float = 0.2
    include_content_probability: float = 0.1


class UTMInjector:
    """Inject UTM parameters into URLs for traffic attribution.

    UTM parameters are used by analytics tools to track traffic sources.
    This plugin adds fake UTM parameters to simulate organic traffic
    from various sources.

    Parameters injected:
    - utm_source: Traffic source (google, facebook, etc.)
    - utm_medium: Marketing medium (cpc, organic, social, etc.)
    - utm_campaign: Campaign name (optional)
    - utm_term: Search term (optional)
    - utm_content: Content variant (optional)

    Usage:
        ```python
        config = UTMConfig(
            sources=["google", "facebook"],
            mediums=["organic", "referral"],
        )
        injector = UTMInjector(config)

        url = "https://example.com/page"
        modified = injector.inject_utm(url)
        # "https://example.com/page?utm_source=google&utm_medium=organic"
        ```
    """

    name = "utm_injector"

    # Common search terms for organic traffic simulation
    DEFAULT_TERMS = [
        "best",
        "top",
        "review",
        "guide",
        "how to",
        "what is",
        "vs",
        "compare",
        "buy",
        "price",
        "cheap",
        "discount",
        "free",
        "online",
        "near me",
    ]

    def __init__(self, config: UTMConfig | None = None) -> None:
        """Initialize UTM injector.

        Args:
            config: UTM configuration
        """
        self.config = config or UTMConfig()

    def generate_utm_params(self) -> dict[str, str]:
        """Generate random UTM parameters based on config.

        Returns:
            Dictionary of UTM parameters
        """
        if not self.config.enabled:
            return {}

        params = {}

        # Required: source and medium
        if self.config.sources:
            params["utm_source"] = random.choice(self.config.sources)

        if self.config.mediums:
            params["utm_medium"] = random.choice(self.config.mediums)

        # Optional: campaign
        if self.config.campaigns and random.random() < self.config.include_campaign_probability:
            params["utm_campaign"] = random.choice(self.config.campaigns)

        # Optional: term
        terms = self.config.terms or self.DEFAULT_TERMS
        if random.random() < self.config.include_term_probability:
            params["utm_term"] = random.choice(terms)

        # Optional: content
        if self.config.contents and random.random() < self.config.include_content_probability:
            params["utm_content"] = random.choice(self.config.contents)

        return params

    def inject_utm(
        self,
        url: str,
        params: dict[str, str] | None = None,
        *,
        overwrite: bool = False,
    ) -> str:
        """Inject UTM parameters into URL.

        Args:
            url: Original URL
            params: UTM parameters (generates if not provided)
            overwrite: Overwrite existing UTM params if present

        Returns:
            URL with UTM parameters
        """
        if not self.config.enabled:
            return url

        # Generate params if not provided
        utm_params = params or self.generate_utm_params()

        if not utm_params:
            return url

        try:
            parsed = urlparse(url)

            # Parse existing query params
            existing_params = parse_qs(parsed.query, keep_blank_values=True)

            # Flatten single-value lists
            flat_params = {k: v[0] if len(v) == 1 else v for k, v in existing_params.items()}

            # Add UTM params
            for key, value in utm_params.items():
                if overwrite or key not in flat_params:
                    flat_params[key] = value

            # Rebuild URL
            new_query = urlencode(flat_params, doseq=True)
            new_parsed = parsed._replace(query=new_query)

            return urlunparse(new_parsed)

        except Exception:
            return url

    def remove_utm(self, url: str) -> str:
        """Remove all UTM parameters from URL.

        Args:
            url: URL with potential UTM params

        Returns:
            URL without UTM parameters
        """
        try:
            parsed = urlparse(url)
            existing_params = parse_qs(parsed.query, keep_blank_values=True)

            # Filter out UTM params
            filtered = {k: v for k, v in existing_params.items() if not k.startswith("utm_")}

            # Flatten and rebuild
            flat_params = {k: v[0] if len(v) == 1 else v for k, v in filtered.items()}
            new_query = urlencode(flat_params, doseq=True)
            new_parsed = parsed._replace(query=new_query)

            return urlunparse(new_parsed)

        except Exception:
            return url

    def has_utm(self, url: str) -> bool:
        """Check if URL already has UTM parameters.

        Args:
            url: URL to check

        Returns:
            True if URL has any UTM params
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return any(k.startswith("utm_") for k in params)
        except Exception:
            return False

    def get_utm_from_url(self, url: str) -> dict[str, str]:
        """Extract UTM parameters from URL.

        Args:
            url: URL to extract from

        Returns:
            Dictionary of UTM parameters
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return {
                k: v[0] if len(v) == 1 else v for k, v in params.items() if k.startswith("utm_")
            }
        except Exception:
            return {}

    def generate_source_medium_pair(self) -> tuple[str, str]:
        """Generate a realistic source/medium combination.

        Some combinations are more realistic than others:
        - google + organic
        - facebook + social
        - newsletter + email

        Returns:
            Tuple of (source, medium)
        """
        # Weighted realistic combinations
        combinations = [
            ("google", "organic", 0.25),
            ("google", "cpc", 0.15),
            ("facebook", "social", 0.10),
            ("facebook", "cpc", 0.08),
            ("twitter", "social", 0.05),
            ("instagram", "social", 0.05),
            ("linkedin", "social", 0.05),
            ("bing", "organic", 0.05),
            ("bing", "cpc", 0.03),
            ("reddit", "social", 0.04),
            ("youtube", "referral", 0.05),
            ("pinterest", "social", 0.03),
            ("direct", "none", 0.05),
            ("email", "email", 0.02),
        ]

        # Weighted random selection
        total = sum(w for _, _, w in combinations)
        r = random.uniform(0, total)
        cumulative = 0

        for source, medium, weight in combinations:
            cumulative += weight
            if r <= cumulative:
                return (source, medium)

        # Fallback
        return ("google", "organic")

    def inject_realistic_utm(self, url: str) -> str:
        """Inject realistic UTM parameters using weighted combinations.

        Args:
            url: Original URL

        Returns:
            URL with realistic UTM parameters
        """
        source, medium = self.generate_source_medium_pair()

        params = {
            "utm_source": source,
            "utm_medium": medium,
        }

        # Add term for search engines
        if source in ["google", "bing", "yahoo", "duckduckgo", "baidu", "yandex"]:
            if medium == "organic" and random.random() < 0.3:
                terms = self.config.terms or self.DEFAULT_TERMS
                params["utm_term"] = random.choice(terms)

        return self.inject_utm(url, params)
