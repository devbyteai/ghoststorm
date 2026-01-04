"""Built-in plugins for GhostStorm."""

from ghoststorm.core.registry.manager import PluginManager


def register(manager: PluginManager) -> None:
    """Register all built-in plugins."""
    # Import and register plugin modules
    from ghoststorm.plugins import browsers, fingerprints, proxies

    browsers.register(manager)
    proxies.register(manager)
    fingerprints.register(manager)
