"""Plugin manager implementation."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from typing import TYPE_CHECKING, Any, TypeVar

import pluggy
import structlog

from ghoststorm.core.registry.hookspecs import GhostStormSpecs

if TYPE_CHECKING:
    from pathlib import Path

    from ghoststorm.core.interfaces.browser import IBrowserEngine
    from ghoststorm.core.interfaces.captcha import ICaptchaSolver
    from ghoststorm.core.interfaces.fingerprint import IFingerprintGenerator
    from ghoststorm.core.interfaces.proxy import IProxyProvider

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class PluginManager:
    """Manages plugin loading, registration, and hook calls."""

    PROJECT_NAME = "ghoststorm"

    def __init__(self) -> None:
        """Initialize the plugin manager."""
        self._pm = pluggy.PluginManager(self.PROJECT_NAME)
        self._pm.add_hookspecs(GhostStormSpecs)

        # Provider registries
        self._browser_engines: dict[str, type[IBrowserEngine]] = {}
        self._proxy_providers: dict[str, type[IProxyProvider]] = {}
        self._fingerprint_generators: dict[str, type[IFingerprintGenerator]] = {}
        self._captcha_solvers: dict[str, type[ICaptchaSolver]] = {}

        # Plugin metadata
        self._loaded_plugins: dict[str, Any] = {}

    @property
    def hook(self) -> Any:
        """Get the hook caller for invoking hooks."""
        return self._pm.hook

    def register(self, plugin: Any, name: str | None = None) -> None:
        """
        Register a plugin.

        Args:
            plugin: Plugin instance or class
            name: Optional plugin name
        """
        plugin_name = name or getattr(plugin, "__name__", str(type(plugin).__name__))

        try:
            self._pm.register(plugin, name=plugin_name)
            self._loaded_plugins[plugin_name] = plugin
            logger.info("Plugin registered", name=plugin_name)

            # Collect provider registrations
            self._collect_providers(plugin)

        except Exception as e:
            logger.error("Failed to register plugin", name=plugin_name, error=str(e))
            raise

    def unregister(self, plugin: Any | None = None, name: str | None = None) -> None:
        """
        Unregister a plugin.

        Args:
            plugin: Plugin instance to unregister
            name: Plugin name to unregister
        """
        try:
            if name:
                plugin = self._loaded_plugins.get(name)
            if plugin:
                self._pm.unregister(plugin)
                plugin_name = name or getattr(plugin, "__name__", str(type(plugin).__name__))
                self._loaded_plugins.pop(plugin_name, None)
                logger.info("Plugin unregistered", name=plugin_name)
        except Exception as e:
            logger.error("Failed to unregister plugin", error=str(e))

    def is_registered(self, name: str) -> bool:
        """Check if a plugin is registered."""
        return name in self._loaded_plugins

    def load_builtin_plugins(self) -> None:
        """Load all built-in plugins from the plugins package."""
        try:
            # Import built-in plugin modules
            from ghoststorm import plugins

            # Iterate over plugin submodules
            plugin_packages = [
                "browsers",
                "proxies",
                "fingerprints",
                "evasion",
                "behavior",
                "network",
                "captcha",
                "extractors",
                "outputs",
            ]

            for pkg_name in plugin_packages:
                try:
                    module = importlib.import_module(f"ghoststorm.plugins.{pkg_name}")
                    if hasattr(module, "register"):
                        module.register(self)
                        logger.debug("Loaded plugin package", package=pkg_name)
                except ImportError as e:
                    logger.debug("Plugin package not found", package=pkg_name, error=str(e))
                except Exception as e:
                    logger.warning("Failed to load plugin package", package=pkg_name, error=str(e))

        except ImportError:
            logger.debug("No built-in plugins package found")

    def load_external_plugins(self, plugin_dir: Path) -> None:
        """
        Load external plugins from a directory.

        Args:
            plugin_dir: Directory containing plugin modules
        """
        if not plugin_dir.exists():
            logger.debug("Plugin directory does not exist", path=str(plugin_dir))
            return

        for plugin_path in plugin_dir.glob("*.py"):
            if plugin_path.name.startswith("_"):
                continue

            try:
                self.load_plugin_from_file(plugin_path)
            except Exception as e:
                logger.warning(
                    "Failed to load external plugin",
                    path=str(plugin_path),
                    error=str(e),
                )

        # Also load plugin packages (directories with __init__.py)
        for plugin_pkg in plugin_dir.iterdir():
            if plugin_pkg.is_dir() and (plugin_pkg / "__init__.py").exists():
                try:
                    self.load_plugin_package(plugin_pkg)
                except Exception as e:
                    logger.warning(
                        "Failed to load plugin package",
                        path=str(plugin_pkg),
                        error=str(e),
                    )

    def load_plugin_from_file(self, path: Path) -> Any:
        """
        Load a plugin from a Python file.

        Args:
            path: Path to the plugin file

        Returns:
            The loaded plugin module
        """
        module_name = f"ghoststorm_plugin_{path.stem}"

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin from {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Register the module as a plugin
        self.register(module, name=path.stem)

        return module

    def load_plugin_package(self, path: Path) -> Any:
        """
        Load a plugin from a package directory.

        Args:
            path: Path to the plugin package

        Returns:
            The loaded plugin module
        """

        # Add parent to path temporarily
        parent = str(path.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)

        try:
            module = importlib.import_module(path.name)
            self.register(module, name=path.name)
            return module
        finally:
            if parent in sys.path:
                sys.path.remove(parent)

    def _collect_providers(self, plugin: Any) -> None:
        """Collect provider registrations from a plugin."""
        # Browser engines
        if hasattr(plugin, "register_browser_engines"):
            try:
                engines = plugin.register_browser_engines()
                if engines:
                    for engine_cls in engines:
                        name = getattr(engine_cls, "name", engine_cls.__name__)
                        self._browser_engines[name] = engine_cls
                        logger.debug("Registered browser engine", name=name)
            except Exception as e:
                logger.warning("Failed to collect browser engines", error=str(e))

        # Proxy providers
        if hasattr(plugin, "register_proxy_providers"):
            try:
                providers = plugin.register_proxy_providers()
                if providers:
                    for provider_cls in providers:
                        name = getattr(provider_cls, "name", provider_cls.__name__)
                        self._proxy_providers[name] = provider_cls
                        logger.debug("Registered proxy provider", name=name)
            except Exception as e:
                logger.warning("Failed to collect proxy providers", error=str(e))

        # Fingerprint generators
        if hasattr(plugin, "register_fingerprint_generators"):
            try:
                generators = plugin.register_fingerprint_generators()
                if generators:
                    for gen_cls in generators:
                        name = getattr(gen_cls, "name", gen_cls.__name__)
                        self._fingerprint_generators[name] = gen_cls
                        logger.debug("Registered fingerprint generator", name=name)
            except Exception as e:
                logger.warning("Failed to collect fingerprint generators", error=str(e))

        # CAPTCHA solvers
        if hasattr(plugin, "register_captcha_solvers"):
            try:
                solvers = plugin.register_captcha_solvers()
                if solvers:
                    for solver_cls in solvers:
                        name = getattr(solver_cls, "name", solver_cls.__name__)
                        self._captcha_solvers[name] = solver_cls
                        logger.debug("Registered CAPTCHA solver", name=name)
            except Exception as e:
                logger.warning("Failed to collect CAPTCHA solvers", error=str(e))

    def get_browser_engine(self, name: str) -> type[IBrowserEngine] | None:
        """Get a browser engine class by name."""
        return self._browser_engines.get(name)

    def get_proxy_provider(self, name: str) -> type[IProxyProvider] | None:
        """Get a proxy provider class by name."""
        return self._proxy_providers.get(name)

    def get_fingerprint_generator(self, name: str) -> type[IFingerprintGenerator] | None:
        """Get a fingerprint generator class by name."""
        return self._fingerprint_generators.get(name)

    def get_captcha_solver(self, name: str) -> type[ICaptchaSolver] | None:
        """Get a CAPTCHA solver class by name."""
        return self._captcha_solvers.get(name)

    def list_browser_engines(self) -> list[str]:
        """List available browser engine names."""
        return list(self._browser_engines.keys())

    def list_proxy_providers(self) -> list[str]:
        """List available proxy provider names."""
        return list(self._proxy_providers.keys())

    def list_fingerprint_generators(self) -> list[str]:
        """List available fingerprint generator names."""
        return list(self._fingerprint_generators.keys())

    def list_captcha_solvers(self) -> list[str]:
        """List available CAPTCHA solver names."""
        return list(self._captcha_solvers.keys())

    def list_plugins(self) -> list[str]:
        """List all loaded plugin names."""
        return list(self._loaded_plugins.keys())

    async def call_hook_async(self, hook_name: str, **kwargs: Any) -> list[Any]:
        """
        Call an async hook and collect results.

        Args:
            hook_name: Name of the hook to call
            **kwargs: Hook arguments

        Returns:
            List of results from all hook implementations
        """
        import asyncio

        hook = getattr(self.hook, hook_name, None)
        if hook is None:
            return []

        results = hook(**kwargs)

        # If results are coroutines, await them
        if results:
            awaitable_results = []
            for result in results:
                if asyncio.iscoroutine(result):
                    awaitable_results.append(result)
                else:
                    awaitable_results.append(asyncio.coroutine(lambda r=result: r)())

            return await asyncio.gather(*awaitable_results, return_exceptions=True)

        return []

    def call_hook_sync(self, hook_name: str, **kwargs: Any) -> list[Any]:
        """
        Call a synchronous hook and collect results.

        Args:
            hook_name: Name of the hook to call
            **kwargs: Hook arguments

        Returns:
            List of results from all hook implementations
        """
        hook = getattr(self.hook, hook_name, None)
        if hook is None:
            return []

        return hook(**kwargs) or []
