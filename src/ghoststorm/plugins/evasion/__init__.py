"""Evasion plugins for anti-detection."""

from ghoststorm.plugins.evasion.font_defender import (
    FontDefender,
    FontDefenderConfig,
    FontDefenderPlugin,
    FontProfile,
    OSType,
    get_font_defender,
)
from ghoststorm.plugins.evasion.stealth_plugin import StealthPlugin

__all__ = [
    # Stealth
    "StealthPlugin",
    # Font Defense
    "FontDefender",
    "FontDefenderConfig",
    "FontDefenderPlugin",
    "FontProfile",
    "OSType",
    "get_font_defender",
]
