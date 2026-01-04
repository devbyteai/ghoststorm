"""Fingerprint generator plugins."""

from ghoststorm.core.registry.hookspecs import hookimpl
from ghoststorm.core.registry.manager import PluginManager
from ghoststorm.plugins.fingerprints.browserforge_plugin import BrowserForgeGenerator
from ghoststorm.plugins.fingerprints.device_profiles import DeviceProfilesGenerator
from ghoststorm.plugins.fingerprints.ios_spoof import IosSpoofer
from ghoststorm.plugins.fingerprints.mobile_inapp import (
    InAppProfile,
    MobileDeviceSpec,
    MobileInAppGenerator,
)


class FingerprintsPlugin:
    """Plugin that registers fingerprint generators."""

    @hookimpl
    def register_fingerprint_generators(self):
        """Register available fingerprint generators."""
        return [BrowserForgeGenerator, DeviceProfilesGenerator, MobileInAppGenerator]


def register(manager: PluginManager) -> None:
    """Register fingerprint plugins."""
    manager.register(FingerprintsPlugin(), name="fingerprints")


__all__ = [
    "BrowserForgeGenerator",
    "DeviceProfilesGenerator",
    "InAppProfile",
    "IosSpoofer",
    "MobileDeviceSpec",
    "MobileInAppGenerator",
    "register",
]
