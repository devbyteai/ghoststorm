"""Plugin registry and management."""

from ghoststorm.core.registry.hookspecs import GhostStormSpecs, hookimpl, hookspec
from ghoststorm.core.registry.manager import PluginManager

__all__ = [
    "GhostStormSpecs",
    "PluginManager",
    "hookimpl",
    "hookspec",
]
