"""Browser engine plugins."""

from ghoststorm.core.registry.hookspecs import hookimpl
from ghoststorm.core.registry.manager import PluginManager
from ghoststorm.plugins.browsers.camoufox_plugin import (
    CamoufoxConfig,
    CamoufoxContext,
    CamoufoxEngine,
    CamoufoxPage,
)
from ghoststorm.plugins.browsers.patchright_plugin import PatchrightEngine
from ghoststorm.plugins.browsers.playwright_plugin import PlaywrightEngine


class BrowsersPlugin:
    """Plugin that registers browser engines."""

    @hookimpl
    def register_browser_engines(self):
        """Register available browser engines.

        Order represents detection resistance (highest first):
        1. Camoufox (10) - C++ level fingerprint spoofing
        2. Patchright (9) - Patched Playwright CDP
        3. Playwright (5) - Standard automation
        """
        return [CamoufoxEngine, PatchrightEngine, PlaywrightEngine]


def register(manager: PluginManager) -> None:
    """Register browser plugins."""
    manager.register(BrowsersPlugin(), name="browsers")


__all__ = [
    # Camoufox types
    "CamoufoxConfig",
    "CamoufoxContext",
    # Engines
    "CamoufoxEngine",
    "CamoufoxPage",
    "PatchrightEngine",
    "PlaywrightEngine",
    # Registration
    "register",
]
