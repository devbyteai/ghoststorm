"""Smart referrer distribution for realistic traffic simulation.

Traffic source distribution based on real-world statistics (2024-2025):
- Direct: 40-47% (typed URL, bookmarks, dark social)
- Organic Search: 25-53% (Google, Bing, DuckDuckGo)
- Social: 1-7% (Twitter/X, Reddit, Facebook, LinkedIn)
- Referral: 5-15% (other websites)
- Email: 2-5%
- Paid: 0-5%
- AI Search: ~1-2% (ChatGPT, Perplexity, emerging)

This module generates realistic referrer patterns with variance to avoid detection.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus, urlparse

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TrafficSource:
    """Definition of a traffic source with weight and variance."""

    name: str
    weight: float  # Base weight (0-1)
    variance: float  # Variance range (0-1)

    def get_adjusted_weight(self) -> float:
        """Get weight with random variance applied."""
        adjustment = random.uniform(-self.variance, self.variance)
        return max(0, self.weight + adjustment)


@dataclass
class ReferrerPreset:
    """Preset configuration for referrer distribution."""

    name: str
    description: str
    sources: dict[str, TrafficSource]


# Preset distributions based on real traffic patterns
PRESETS: dict[str, ReferrerPreset] = {
    "realistic": ReferrerPreset(
        name="Realistic",
        description="Balanced traffic matching typical website patterns",
        sources={
            "direct": TrafficSource("direct", 0.45, 0.10),
            "google": TrafficSource("google", 0.25, 0.08),
            "bing": TrafficSource("bing", 0.05, 0.03),
            "social": TrafficSource("social", 0.12, 0.05),
            "referral": TrafficSource("referral", 0.08, 0.04),
            "email": TrafficSource("email", 0.03, 0.02),
            "ai_search": TrafficSource("ai_search", 0.02, 0.01),
        },
    ),
    "search_heavy": ReferrerPreset(
        name="Search Heavy",
        description="High organic search traffic (content/blog sites)",
        sources={
            "direct": TrafficSource("direct", 0.20, 0.05),
            "google": TrafficSource("google", 0.50, 0.10),
            "bing": TrafficSource("bing", 0.10, 0.05),
            "social": TrafficSource("social", 0.08, 0.04),
            "referral": TrafficSource("referral", 0.07, 0.03),
            "email": TrafficSource("email", 0.03, 0.02),
            "ai_search": TrafficSource("ai_search", 0.02, 0.01),
        },
    ),
    "social_viral": ReferrerPreset(
        name="Social Viral",
        description="High social traffic (viral content, trending)",
        sources={
            "direct": TrafficSource("direct", 0.15, 0.05),
            "google": TrafficSource("google", 0.15, 0.05),
            "bing": TrafficSource("bing", 0.02, 0.01),
            "social": TrafficSource("social", 0.55, 0.15),
            "referral": TrafficSource("referral", 0.08, 0.04),
            "email": TrafficSource("email", 0.03, 0.02),
            "ai_search": TrafficSource("ai_search", 0.02, 0.01),
        },
    ),
    "brand_focused": ReferrerPreset(
        name="Brand Focused",
        description="High direct traffic (established brands)",
        sources={
            "direct": TrafficSource("direct", 0.60, 0.10),
            "google": TrafficSource("google", 0.18, 0.05),
            "bing": TrafficSource("bing", 0.04, 0.02),
            "social": TrafficSource("social", 0.08, 0.04),
            "referral": TrafficSource("referral", 0.05, 0.03),
            "email": TrafficSource("email", 0.03, 0.02),
            "ai_search": TrafficSource("ai_search", 0.02, 0.01),
        },
    ),
    "email_campaign": ReferrerPreset(
        name="Email Campaign",
        description="High email traffic (newsletter, marketing)",
        sources={
            "direct": TrafficSource("direct", 0.25, 0.08),
            "google": TrafficSource("google", 0.20, 0.06),
            "bing": TrafficSource("bing", 0.03, 0.02),
            "social": TrafficSource("social", 0.10, 0.05),
            "referral": TrafficSource("referral", 0.07, 0.03),
            "email": TrafficSource("email", 0.33, 0.10),
            "ai_search": TrafficSource("ai_search", 0.02, 0.01),
        },
    ),
}

# Social platform weights (within social traffic)
SOCIAL_PLATFORMS: dict[str, float] = {
    "twitter": 0.28,
    "reddit": 0.22,
    "facebook": 0.20,
    "linkedin": 0.12,
    "youtube": 0.10,
    "tiktok": 0.05,
    "instagram": 0.03,
}

# Search query templates for generating realistic search referrers
SEARCH_QUERY_TEMPLATES: list[str] = [
    "{domain}",
    "{domain} {keyword}",
    "{keyword} site",
    "{keyword} online",
    "best {keyword}",
    "{keyword} review",
    "{keyword} 2025",
    "how to {keyword}",
    "what is {keyword}",
]


@dataclass
class ReferrerDistribution:
    """Generate realistic referrer distribution with variance.

    Features:
    - Weighted random selection from traffic sources
    - Variance applied to prevent detection patterns
    - Realistic URL generation for each source type
    - Support for custom weights
    """

    preset: str = "realistic"
    variance_percent: int = 10

    # Custom weights (override preset when set)
    custom_weights: dict[str, int] | None = None

    # Social platforms to include
    social_platforms: list[str] = field(
        default_factory=lambda: ["twitter", "reddit", "facebook", "linkedin"]
    )

    # Internal state
    _current_sources: dict[str, TrafficSource] = field(default_factory=dict, init=False)
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize sources from preset or custom weights."""
        self._initialize_sources()
        self._stats = {source: 0 for source in self._current_sources}

    def _initialize_sources(self) -> None:
        """Initialize traffic sources from preset or custom config."""
        if self.custom_weights:
            # Convert custom weights (0-100) to TrafficSource objects
            total = sum(self.custom_weights.values())
            variance = self.variance_percent / 100

            self._current_sources = {}
            for name, weight in self.custom_weights.items():
                normalized_weight = weight / total if total > 0 else 0
                self._current_sources[name] = TrafficSource(
                    name=name,
                    weight=normalized_weight,
                    variance=min(variance, normalized_weight * 0.3),  # Cap variance
                )
        else:
            # Use preset
            preset_config = PRESETS.get(self.preset, PRESETS["realistic"])
            self._current_sources = dict(preset_config.sources)

            # Apply global variance modifier
            variance_mod = self.variance_percent / 10  # 10% = 1.0 modifier
            for source in self._current_sources.values():
                source.variance *= variance_mod

    def get_referrer(self, target_url: str) -> str | None:
        """Get a referrer URL based on weighted distribution.

        Args:
            target_url: The target URL being visited

        Returns:
            Referrer URL string or None for direct traffic
        """
        # Calculate adjusted weights
        sources = list(self._current_sources.keys())
        weights = [self._current_sources[s].get_adjusted_weight() for s in sources]

        # Normalize weights
        total = sum(weights)
        if total <= 0:
            return None

        weights = [w / total for w in weights]

        # Select source
        source = random.choices(sources, weights=weights)[0]
        self._stats[source] = self._stats.get(source, 0) + 1

        # Generate referrer URL
        return self._generate_referrer_url(source, target_url)

    def _generate_referrer_url(self, source: str, target_url: str) -> str | None:
        """Generate a realistic referrer URL for the given source.

        Args:
            source: Traffic source type
            target_url: The target URL being visited

        Returns:
            Referrer URL or None for direct
        """
        parsed = urlparse(target_url)
        domain = parsed.netloc.replace("www.", "")
        path_parts = [p for p in parsed.path.split("/") if p]
        keyword = path_parts[0] if path_parts else domain.split(".")[0]

        if source == "direct":
            return None

        elif source == "google":
            query = self._generate_search_query(domain, keyword)
            return f"https://www.google.com/search?q={quote_plus(query)}"

        elif source == "bing":
            query = self._generate_search_query(domain, keyword)
            return f"https://www.bing.com/search?q={quote_plus(query)}"

        elif source == "social":
            return self._generate_social_referrer(target_url)

        elif source == "referral":
            return self._generate_referral_url(domain)

        elif source == "email":
            return self._generate_email_referrer()

        elif source == "ai_search":
            return self._generate_ai_search_referrer(domain, keyword)

        return None

    def _generate_search_query(self, domain: str, keyword: str) -> str:
        """Generate a realistic search query."""
        template = random.choice(SEARCH_QUERY_TEMPLATES)
        return template.format(domain=domain, keyword=keyword)

    def _generate_social_referrer(self, target_url: str) -> str:
        """Generate a social media referrer URL."""
        # Filter to configured platforms
        available = {
            p: w for p, w in SOCIAL_PLATFORMS.items() if p in self.social_platforms
        }

        if not available:
            available = {"twitter": 1.0}

        # Weighted selection
        platform = random.choices(
            list(available.keys()), weights=list(available.values())
        )[0]

        # Platform-specific referrer formats
        referrers = {
            "twitter": [
                "https://t.co/randomstring",
                "https://twitter.com/i/web/status/123456789",
                "https://x.com/user/status/123456789",
            ],
            "reddit": [
                "https://www.reddit.com/r/popular/",
                "https://www.reddit.com/r/technology/comments/abc123/",
                "https://old.reddit.com/r/all/",
            ],
            "facebook": [
                "https://l.facebook.com/l.php",
                "https://www.facebook.com/",
                "https://m.facebook.com/",
            ],
            "linkedin": [
                "https://www.linkedin.com/feed/",
                "https://www.linkedin.com/posts/",
            ],
            "youtube": [
                "https://www.youtube.com/redirect",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            ],
            "tiktok": [
                "https://www.tiktok.com/@user/video/123",
                "https://vm.tiktok.com/abc123/",
            ],
            "instagram": [
                "https://l.instagram.com/",
                "https://www.instagram.com/",
            ],
        }

        return random.choice(referrers.get(platform, ["https://www.google.com/"]))

    def _generate_referral_url(self, domain: str) -> str:
        """Generate a generic referral URL."""
        referral_sites = [
            "https://news.ycombinator.com/item?id=12345",
            "https://medium.com/@user/article-slug",
            "https://dev.to/user/article",
            "https://www.producthunt.com/posts/product",
            "https://slashdot.org/story/123456",
            "https://digg.com/video/something",
            f"https://blog.{domain.split('.')[0]}.io/",
            "https://techcrunch.com/article/",
            "https://mashable.com/article/",
        ]
        return random.choice(referral_sites)

    def _generate_email_referrer(self) -> str:
        """Generate an email campaign referrer."""
        email_referrers = [
            # Gmail/Google
            "https://mail.google.com/mail/u/0/",
            # Outlook
            "https://outlook.live.com/mail/",
            "https://outlook.office.com/mail/",
            # Yahoo
            "https://mail.yahoo.com/",
            # Email marketing platforms (often anonymized)
            "",  # Many email clients don't send referrer
        ]

        # 40% chance of no referrer (common for email)
        if random.random() < 0.4:
            return ""

        return random.choice([r for r in email_referrers if r])

    def _generate_ai_search_referrer(self, domain: str, keyword: str) -> str:
        """Generate an AI search referrer (ChatGPT, Perplexity, etc.)."""
        ai_referrers = [
            "https://chat.openai.com/",
            "https://www.perplexity.ai/search",
            "https://www.bing.com/chat",  # Bing Chat / Copilot
            "https://bard.google.com/",  # Google Bard (now Gemini)
            "https://claude.ai/",
        ]
        return random.choice(ai_referrers)

    def get_stats(self) -> dict[str, Any]:
        """Get distribution statistics.

        Returns:
            Dictionary with counts and percentages per source
        """
        total = sum(self._stats.values())
        if total == 0:
            return {"total": 0, "sources": {}}

        return {
            "total": total,
            "sources": {
                source: {
                    "count": count,
                    "percent": round(count / total * 100, 1),
                }
                for source, count in self._stats.items()
            },
        }

    def reset_stats(self) -> None:
        """Reset distribution statistics."""
        self._stats = {source: 0 for source in self._current_sources}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ReferrerDistribution:
        """Create ReferrerDistribution from configuration dictionary.

        Args:
            config: Configuration dictionary with keys:
                - mode: "realistic", "custom", or "none"
                - preset: Preset name when mode != custom
                - custom weights (direct_weight, google_weight, etc.)
                - variance_percent
                - social_platforms

        Returns:
            Configured ReferrerDistribution instance
        """
        mode = config.get("mode", "realistic")

        if mode == "none":
            # Return distribution that always returns None
            return cls(
                preset="realistic",
                custom_weights={"direct": 100},
            )

        if mode == "custom":
            custom_weights = {
                "direct": config.get("direct_weight", 45),
                "google": config.get("google_weight", 25),
                "bing": config.get("bing_weight", 5),
                "social": config.get("social_weight", 12),
                "referral": config.get("referral_weight", 8),
                "email": config.get("email_weight", 3),
                "ai_search": config.get("ai_search_weight", 2),
            }
        else:
            custom_weights = None

        return cls(
            preset=config.get("preset", "realistic"),
            variance_percent=config.get("variance_percent", 10),
            custom_weights=custom_weights,
            social_platforms=config.get(
                "social_platforms", ["twitter", "reddit", "facebook", "linkedin"]
            ),
        )
