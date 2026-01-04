"""Decodo (formerly Smartproxy) proxy provider.

Decodo is a premium proxy provider offering:
- 115M+ residential IPs
- $3.50/GB pricing
- Geo-targeting by country, city, state
- Sticky and rotating sessions

Endpoint documentation:
- Rotating: gate.smartproxy.com:7777
- Sticky: gate.smartproxy.com:7000

Username format for targeting:
- Base: username
- Country: username-country-us
- City: username-country-us-city-newyork
- Session: username-country-us-session-abc123
"""

from __future__ import annotations

from typing import Any

from ghoststorm.core.models.proxy import ProxyCategory
from ghoststorm.plugins.proxies.premium_provider import PremiumProxyProvider


class DecodoProvider(PremiumProxyProvider):
    """Decodo (Smartproxy) proxy provider implementation.

    Pricing: ~$3.50/GB for residential proxies
    Pool size: 115M+ IPs
    Features: Geo-targeting, sticky sessions, rotating sessions
    """

    name = "decodo"
    endpoint_host = "gate.smartproxy.com"
    endpoint_port = 7777  # Rotating port
    sticky_port = 7000  # Sticky session port
    category = ProxyCategory.RESIDENTIAL

    def build_proxy_url(
        self,
        *,
        session_id: str | None = None,
        country: str | None = None,
        city: str | None = None,
    ) -> str:
        """Build Decodo proxy URL.

        Format: http://user-country-us-session-xyz:pass@gate.smartproxy.com:7000

        Args:
            session_id: Session ID for sticky sessions
            country: Country code (e.g., 'us', 'gb', 'de')
            city: City name (e.g., 'newyork', 'london')

        Returns:
            Full proxy URL
        """
        # Determine port based on session type
        port = self.sticky_port if session_id else self.endpoint_port

        # Build username with targeting parameters
        user_parts = [self.username]

        if country:
            user_parts.append(f"country-{country.lower()}")

        if city:
            # City requires country to be set
            user_parts.append(f"city-{city.lower().replace(' ', '')}")

        if self.state:
            user_parts.append(f"state-{self.state.lower().replace(' ', '')}")

        if session_id:
            user_parts.append(f"session-{session_id}")

        username = "-".join(user_parts)

        return f"http://{username}:{self.password}@{self.endpoint_host}:{port}"

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> DecodoProvider:
        """Create provider from saved configuration."""
        return cls(
            username=config["username"],
            password=config["password"],
            country=config.get("country"),
            city=config.get("city"),
            state=config.get("state"),
            session_type=config.get("session_type", "rotating"),
            session_duration=config.get("session_duration", 10),
        )
