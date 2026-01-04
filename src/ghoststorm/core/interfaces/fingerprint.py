"""Fingerprint generator interface definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ghoststorm.core.models.fingerprint import (
        DeviceProfile,
        Fingerprint,
        FingerprintConstraints,
    )


@runtime_checkable
class IFingerprintGenerator(Protocol):
    """Contract for fingerprint generators."""

    @property
    def name(self) -> str:
        """Generator name."""
        ...

    @property
    def total_profiles(self) -> int:
        """Total number of device profiles available."""
        ...

    async def initialize(self) -> None:
        """Initialize the generator (load profiles, etc.)."""
        ...

    async def generate(
        self,
        *,
        constraints: FingerprintConstraints | None = None,
        device_profile: DeviceProfile | None = None,
    ) -> Fingerprint:
        """
        Generate a new fingerprint.

        Args:
            constraints: Constraints for fingerprint generation
            device_profile: Specific device profile to use

        Returns:
            A complete Fingerprint instance
        """
        ...

    async def get_random_profile(
        self,
        *,
        browser: str | None = None,
        os: str | None = None,
        device_type: str | None = None,
    ) -> DeviceProfile:
        """
        Get a random device profile matching criteria.

        Args:
            browser: Filter by browser (chrome, firefox, safari, edge)
            os: Filter by OS (windows, macos, linux, android, ios)
            device_type: Filter by device type (desktop, mobile, tablet)

        Returns:
            A DeviceProfile instance
        """
        ...

    async def get_profile_by_id(self, profile_id: str) -> DeviceProfile | None:
        """Get a specific device profile by ID."""
        ...

    async def list_profiles(
        self,
        *,
        browser: str | None = None,
        os: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeviceProfile]:
        """List available device profiles."""
        ...

    async def close(self) -> None:
        """Clean up generator resources."""
        ...
