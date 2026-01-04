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
    # Font Defense
    "FontDefender",
    "FontDefenderConfig",
    "FontDefenderPlugin",
    "FontProfile",
    "OSType",
    # Stealth
    "StealthPlugin",
    "get_font_defender",
]
