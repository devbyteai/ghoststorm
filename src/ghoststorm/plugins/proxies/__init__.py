"""Proxy provider plugins."""

from ghoststorm.core.registry.hookspecs import hookimpl
from ghoststorm.core.registry.manager import PluginManager
from ghoststorm.plugins.proxies.dynamic_auth import DynamicProxyAuth, ProxyCredentials
from ghoststorm.plugins.proxies.file_provider import FileProxyProvider
from ghoststorm.plugins.proxies.rotating_provider import RotatingProxyProvider
from ghoststorm.plugins.proxies.tor_provider import (
    TorBrowserLauncher,
    TorCircuitStrategy,
    TorConfig,
    TorProxyProvider,
)


class ProxiesPlugin:
    """Plugin that registers proxy providers."""

    @hookimpl
    def register_proxy_providers(self):
        """Register available proxy providers."""
        return [FileProxyProvider, RotatingProxyProvider, TorProxyProvider]


def register(manager: PluginManager) -> None:
    """Register proxy plugins."""
    manager.register(ProxiesPlugin(), name="proxies")


__all__ = [
    # File-based
    "FileProxyProvider",
    "RotatingProxyProvider",
    # Dynamic auth
    "DynamicProxyAuth",
    "ProxyCredentials",
    # Tor
    "TorProxyProvider",
    "TorBrowserLauncher",
    "TorConfig",
    "TorCircuitStrategy",
    # Registration
    "register",
]
