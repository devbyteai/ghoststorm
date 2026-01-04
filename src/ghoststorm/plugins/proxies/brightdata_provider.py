"""Bright Data (formerly Luminati) proxy provider.

Bright Data is an enterprise-grade proxy provider offering:
- 150M+ residential IPs
- $8/GB pricing
- Advanced geo-targeting (country, city, ASN, carrier)
- Multiple zones (residential, datacenter, ISP, mobile)
- Sticky and rotating sessions

Endpoint: brd.superproxy.io:22225

Username format:
- Base: brd-customer-{customer_id}-zone-{zone}
- Country: brd-customer-{id}-zone-{zone}-country-us
- Session: brd-customer-{id}-zone-{zone}-session-abc123
"""

from __future__ import annotations

from typing import Any, Literal

from ghoststorm.core.models.proxy import ProxyCategory
from ghoststorm.plugins.proxies.premium_provider import PremiumProxyProvider


class BrightDataProvider(PremiumProxyProvider):
    """Bright Data proxy provider implementation.

    Pricing: ~$8/GB for residential proxies
    Pool size: 150M+ IPs
    Features: Zones, advanced geo-targeting, enterprise features
    """

    name = "brightdata"
    endpoint_host = "brd.superproxy.io"
    endpoint_port = 22225
    category = ProxyCategory.RESIDENTIAL

    # Zone types
    ZONE_RESIDENTIAL = "residential"
    ZONE_DATACENTER = "datacenter"
    ZONE_ISP = "isp"
    ZONE_MOBILE = "mobile"

    def __init__(
        self,
        customer_id: str,
        zone: str,
        password: str,
        *,
        country: str | None = None,
        city: str | None = None,
        state: str | None = None,
        asn: int | None = None,
        carrier: str | None = None,
        session_type: Literal["rotating", "sticky"] = "rotating",
        session_duration: int = 10,
        **kwargs: Any,
    ) -> None:
        """Initialize Bright Data provider.

        Args:
            customer_id: Your Bright Data customer ID (found in dashboard)
            zone: Zone name (e.g., 'residential', 'datacenter', or custom)
            password: Zone password
            country: Target country code
            city: Target city
            state: Target state
            asn: Target ASN number
            carrier: Target mobile carrier (for mobile zone)
            session_type: 'rotating' or 'sticky'
            session_duration: Sticky session duration in minutes
        """
        # Bright Data uses customer_id-zone as the username concept
        super().__init__(
            username=customer_id,  # Store customer_id as username
            password=password,
            country=country,
            city=city,
            state=state,
            session_type=session_type,
            session_duration=session_duration,
            **kwargs,
        )
        self.customer_id = customer_id
        self.zone = zone
        self.asn = asn
        self.carrier = carrier

        # Set category based on zone
        if zone == self.ZONE_DATACENTER:
            self.category = ProxyCategory.DATACENTER
        elif zone == self.ZONE_MOBILE:
            self.category = ProxyCategory.MOBILE
        elif zone == self.ZONE_ISP:
            self.category = ProxyCategory.ISP
        else:
            self.category = ProxyCategory.RESIDENTIAL

    def build_proxy_url(
        self,
        *,
        session_id: str | None = None,
        country: str | None = None,
        city: str | None = None,
    ) -> str:
        """Build Bright Data proxy URL.

        Format: http://brd-customer-{id}-zone-{zone}-country-us:pass@brd.superproxy.io:22225

        Args:
            session_id: Session ID for sticky sessions
            country: Country code override
            city: City name override

        Returns:
            Full proxy URL
        """
        # Build username with all parameters
        user_parts = [f"brd-customer-{self.customer_id}-zone-{self.zone}"]

        if country or self.country:
            user_parts.append(f"country-{(country or self.country).lower()}")

        if city or self.city:
            user_parts.append(f"city-{(city or self.city).lower().replace(' ', '_')}")

        if self.state:
            user_parts.append(f"state-{self.state.lower().replace(' ', '_')}")

        if self.asn:
            user_parts.append(f"asn-{self.asn}")

        if self.carrier:
            user_parts.append(f"carrier-{self.carrier.lower().replace(' ', '_')}")

        if session_id:
            user_parts.append(f"session-{session_id}")

        username = "-".join(user_parts)

        return f"http://{username}:{self.password}@{self.endpoint_host}:{self.endpoint_port}"

    def to_config(self) -> dict[str, Any]:
        """Export configuration for saving."""
        config = super().to_config()
        config.update(
            {
                "customer_id": self.customer_id,
                "zone": self.zone,
                "asn": self.asn,
                "carrier": self.carrier,
            }
        )
        return config

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> BrightDataProvider:
        """Create provider from saved configuration."""
        return cls(
            customer_id=config["customer_id"],
            zone=config["zone"],
            password=config["password"],
            country=config.get("country"),
            city=config.get("city"),
            state=config.get("state"),
            asn=config.get("asn"),
            carrier=config.get("carrier"),
            session_type=config.get("session_type", "rotating"),
            session_duration=config.get("session_duration", 10),
        )
