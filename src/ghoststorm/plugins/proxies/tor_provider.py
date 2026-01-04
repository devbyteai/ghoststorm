"""Tor network proxy provider with circuit rotation."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ghoststorm.core.models.proxy import Proxy, ProxyType


class TorCircuitStrategy(Enum):
    """Strategy for Tor circuit management."""

    STATIC = "static"           # Keep same circuit
    ROTATE_PER_REQUEST = "rotate_per_request"  # New circuit each request
    ROTATE_PER_SESSION = "rotate_per_session"  # New circuit per browser session
    ROTATE_INTERVAL = "rotate_interval"         # Rotate every N seconds


@dataclass
class TorConfig:
    """Configuration for Tor proxy provider."""

    # SOCKS5 proxy settings
    socks_host: str = "127.0.0.1"
    socks_port: int = 9050

    # Control port for circuit rotation
    control_port: int = 9051
    control_password: str = ""
    control_auth_cookie: str | None = None

    # Circuit rotation
    circuit_strategy: TorCircuitStrategy = TorCircuitStrategy.ROTATE_PER_SESSION
    rotation_interval: int = 300  # seconds (for ROTATE_INTERVAL)

    # Connection settings
    connection_timeout: float = 30.0
    verify_connection: bool = True

    # Tor Browser paths (optional, for launcher)
    tor_browser_path: str | None = None
    tor_data_dir: str | None = None


class TorProxyProvider:
    """Tor network proxy provider.

    Provides Tor SOCKS5 proxy with optional circuit rotation
    via the Tor control port. Supports multiple rotation strategies.

    Features:
    - SOCKS5 proxy via Tor daemon
    - Circuit rotation for new IP addresses
    - Control port authentication (password or cookie)
    - Connection verification
    - Multiple rotation strategies

    Requirements:
    - Tor daemon running (tor service)
    - Control port enabled in torrc:
        ControlPort 9051
        HashedControlPassword <password_hash>
      OR
        CookieAuthentication 1

    Usage:
        ```python
        config = TorConfig(
            socks_port=9050,
            control_port=9051,
            control_password="my_password",
            circuit_strategy=TorCircuitStrategy.ROTATE_PER_SESSION,
        )
        provider = TorProxyProvider(config)
        await provider.initialize()

        proxy = await provider.get_proxy()
        # Use proxy with browser...

        await provider.rotate_circuit()  # Get new IP
        ```
    """

    name = "tor"

    def __init__(self, config: TorConfig | None = None) -> None:
        """Initialize Tor proxy provider.

        Args:
            config: Tor configuration
        """
        self.config = config or TorConfig()
        self._is_connected = False
        self._current_ip: str | None = None
        self._rotation_count = 0
        self._control_socket: socket.socket | None = None

    async def initialize(self) -> None:
        """Initialize connection to Tor."""
        if self.config.verify_connection:
            await self._verify_tor_connection()

    async def _verify_tor_connection(self) -> bool:
        """Verify Tor SOCKS5 proxy is accessible.

        Returns:
            True if connection successful
        """
        try:
            # Try to connect to SOCKS port
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.config.socks_host,
                    self.config.socks_port,
                ),
                timeout=self.config.connection_timeout,
            )

            # SOCKS5 handshake (no auth)
            writer.write(b"\x05\x01\x00")
            await writer.drain()

            response = await reader.read(2)
            writer.close()
            await writer.wait_closed()

            if response == b"\x05\x00":
                self._is_connected = True
                return True

            return False

        except Exception:
            self._is_connected = False
            return False

    async def _connect_control_port(self) -> bool:
        """Connect to Tor control port.

        Returns:
            True if connected and authenticated
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.config.socks_host,
                    self.config.control_port,
                ),
                timeout=self.config.connection_timeout,
            )

            # Authenticate
            if self.config.control_password:
                auth_cmd = f'AUTHENTICATE "{self.config.control_password}"\r\n'
            elif self.config.control_auth_cookie:
                # Read cookie file
                cookie_path = Path(self.config.control_auth_cookie)
                if cookie_path.exists():
                    cookie = cookie_path.read_bytes().hex()
                    auth_cmd = f"AUTHENTICATE {cookie}\r\n"
                else:
                    return False
            else:
                auth_cmd = "AUTHENTICATE\r\n"

            writer.write(auth_cmd.encode())
            await writer.drain()

            response = await reader.readline()

            if response.startswith(b"250"):
                self._control_reader = reader
                self._control_writer = writer
                return True

            writer.close()
            await writer.wait_closed()
            return False

        except Exception:
            return False

    async def rotate_circuit(self) -> bool:
        """Request a new Tor circuit (new IP address).

        Sends SIGNAL NEWNYM to Tor control port to get a new circuit.

        Returns:
            True if rotation successful
        """
        try:
            # Connect to control port if not connected
            if not hasattr(self, '_control_writer') or self._control_writer is None:
                if not await self._connect_control_port():
                    return False

            # Send NEWNYM signal
            self._control_writer.write(b"SIGNAL NEWNYM\r\n")
            await self._control_writer.drain()

            response = await self._control_reader.readline()

            if response.startswith(b"250"):
                self._rotation_count += 1
                self._current_ip = None  # Clear cached IP

                # Wait for circuit to be established
                await asyncio.sleep(1.0)
                return True

            return False

        except Exception:
            # Reset connection
            self._control_writer = None
            self._control_reader = None
            return False

    async def get_current_ip(self) -> str | None:
        """Get current exit node IP address.

        Uses check.torproject.org to verify IP.

        Returns:
            Current IP address or None
        """
        # This would need aiohttp or similar to fetch
        # For now, return cached or None
        return self._current_ip

    async def get_proxy(self) -> Proxy:
        """Get Tor SOCKS5 proxy configuration.

        Returns:
            Proxy object configured for Tor
        """
        # Rotate circuit based on strategy
        if self.config.circuit_strategy == TorCircuitStrategy.ROTATE_PER_REQUEST:
            await self.rotate_circuit()

        return Proxy(
            host=self.config.socks_host,
            port=self.config.socks_port,
            proxy_type=ProxyType.SOCKS5,
            username=None,
            password=None,
        )

    async def get_proxy_url(self) -> str:
        """Get Tor proxy as URL string.

        Returns:
            Proxy URL (e.g., socks5://127.0.0.1:9050)
        """
        return f"socks5://{self.config.socks_host}:{self.config.socks_port}"

    async def mark_success(self, latency_ms: float = 0) -> None:
        """Mark proxy usage as successful."""
        pass  # Tor doesn't need health tracking

    async def mark_failure(self, error: str = "") -> None:
        """Mark proxy usage as failed.

        On failure, we can optionally rotate circuit.
        """
        if self.config.circuit_strategy != TorCircuitStrategy.STATIC:
            await self.rotate_circuit()

    async def close(self) -> None:
        """Close control port connection."""
        if hasattr(self, '_control_writer') and self._control_writer:
            self._control_writer.close()
            try:
                await self._control_writer.wait_closed()
            except Exception:
                pass

    @property
    def is_connected(self) -> bool:
        """Whether Tor connection is verified."""
        return self._is_connected

    @property
    def rotation_count(self) -> int:
        """Number of circuit rotations performed."""
        return self._rotation_count

    @property
    def total_proxies(self) -> int:
        """Return 1 as Tor is a single proxy endpoint."""
        return 1

    @property
    def healthy_proxies(self) -> int:
        """Return 1 if connected, 0 otherwise."""
        return 1 if self._is_connected else 0


class TorBrowserLauncher:
    """Launch and manage Tor Browser instances.

    For scenarios where you need the actual Tor Browser
    with its unique fingerprint, not just the Tor network.

    Usage:
        ```python
        launcher = TorBrowserLauncher(
            browser_path="/path/to/tor-browser/Browser/firefox"
        )

        process = await launcher.launch("https://example.com")
        await asyncio.sleep(30)
        await launcher.kill()
        ```
    """

    name = "tor_browser_launcher"

    # Default paths by OS
    DEFAULT_PATHS = {
        "linux": [
            "~/tor-browser/Browser/start-tor-browser",
            "/opt/tor-browser/Browser/start-tor-browser",
            "~/.local/share/tor-browser/Browser/start-tor-browser",
        ],
        "darwin": [
            "/Applications/Tor Browser.app/Contents/MacOS/firefox",
            "~/Applications/Tor Browser.app/Contents/MacOS/firefox",
        ],
        "win32": [
            r"C:\Tor Browser\Browser\firefox.exe",
            r"%USERPROFILE%\Desktop\Tor Browser\Browser\firefox.exe",
            r"%PROGRAMFILES%\Tor Browser\Browser\firefox.exe",
        ],
    }

    def __init__(
        self,
        browser_path: str | None = None,
        profile_path: str | None = None,
    ) -> None:
        """Initialize Tor Browser launcher.

        Args:
            browser_path: Path to Tor Browser executable
            profile_path: Custom profile path (optional)
        """
        self.browser_path = browser_path
        self.profile_path = profile_path
        self._process: asyncio.subprocess.Process | None = None
        self._is_running = False

    def _find_browser_path(self) -> str | None:
        """Auto-detect Tor Browser installation path.

        Returns:
            Path to Tor Browser or None
        """
        import os
        import platform

        system = platform.system().lower()
        if system == "windows":
            system = "win32"

        paths = self.DEFAULT_PATHS.get(system, [])

        for path in paths:
            expanded = os.path.expanduser(os.path.expandvars(path))
            if Path(expanded).exists():
                return expanded

        return None

    async def launch(
        self,
        url: str | None = None,
        *,
        wait_for_ready: bool = True,
        ready_timeout: float = 60.0,
    ) -> bool:
        """Launch Tor Browser.

        Args:
            url: URL to open (optional)
            wait_for_ready: Wait for browser to be ready
            ready_timeout: Timeout for ready wait

        Returns:
            True if launched successfully
        """
        path = self.browser_path or self._find_browser_path()

        if not path or not Path(path).exists():
            return False

        try:
            args = [path]
            if url:
                args.append(url)

            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            self._is_running = True

            if wait_for_ready:
                # Wait for Tor to bootstrap
                await asyncio.sleep(min(10.0, ready_timeout))

            return True

        except Exception:
            return False

    async def open_url(self, url: str) -> bool:
        """Open URL in running Tor Browser.

        Args:
            url: URL to open

        Returns:
            True if successful
        """
        if not self._is_running:
            return await self.launch(url)

        # For already running browser, we'd need different approach
        # This is simplified - just launch new instance
        return await self.launch(url)

    async def kill(self) -> bool:
        """Kill Tor Browser process.

        Returns:
            True if killed successfully
        """
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(
                    self._process.wait(),
                    timeout=5.0,
                )
                self._is_running = False
                return True
            except TimeoutError:
                self._process.kill()
                self._is_running = False
                return True
            except Exception:
                pass

        return False

    async def restart(self, url: str | None = None) -> bool:
        """Restart Tor Browser (new identity).

        Args:
            url: URL to open after restart

        Returns:
            True if restarted successfully
        """
        await self.kill()
        await asyncio.sleep(2.0)  # Wait for cleanup
        return await self.launch(url)

    @property
    def is_running(self) -> bool:
        """Whether Tor Browser is running."""
        return self._is_running

    @property
    def pid(self) -> int | None:
        """Process ID of Tor Browser."""
        if self._process:
            return self._process.pid
        return None
