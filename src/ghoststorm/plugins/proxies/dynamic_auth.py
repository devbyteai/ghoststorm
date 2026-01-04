"""Dynamic Chrome proxy authentication extension generator.

Migrated from: dextools-bot (x11)/lib/proxy.py
Original author's work preserved and enhanced for GhostStorm.

This module generates Chrome extensions on-the-fly for authenticated
proxy support in Selenium/Chrome WebDriver scenarios.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import BinaryIO


@dataclass
class ProxyCredentials:
    """Proxy server credentials."""

    host: str
    port: int
    username: str
    password: str

    @classmethod
    def from_string(cls, proxy_string: str) -> ProxyCredentials:
        """Parse proxy from string format.

        Supported formats:
        - host:port:username:password
        - username:password@host:port
        - host:port (no auth)

        Args:
            proxy_string: Proxy string in supported format

        Returns:
            ProxyCredentials instance

        Raises:
            ValueError: If format is not recognized
        """
        proxy_string = proxy_string.strip()

        # Format: username:password@host:port
        if "@" in proxy_string:
            auth_part, host_part = proxy_string.rsplit("@", 1)
            if ":" in auth_part and ":" in host_part:
                username, password = auth_part.split(":", 1)
                host, port_str = host_part.rsplit(":", 1)
                return cls(
                    host=host,
                    port=int(port_str),
                    username=username,
                    password=password,
                )

        # Format: host:port:username:password
        parts = proxy_string.split(":")
        if len(parts) == 4:
            return cls(
                host=parts[0],
                port=int(parts[1]),
                username=parts[2],
                password=parts[3],
            )
        elif len(parts) == 2:
            # No auth: host:port
            return cls(
                host=parts[0],
                port=int(parts[1]),
                username="",
                password="",
            )

        raise ValueError(
            f"Invalid proxy format: {proxy_string}. "
            "Expected: host:port:user:pass or user:pass@host:port"
        )


# Chrome extension manifest template (Manifest V2)
MANIFEST_JSON = """{
    "version": "1.0.0",
    "manifest_version": 2,
    "name": "GhostStorm Proxy Auth",
    "description": "Dynamic proxy authentication for browser automation",
    "permissions": [
        "proxy",
        "tabs",
        "unlimitedStorage",
        "storage",
        "<all_urls>",
        "webRequest",
        "webRequestBlocking"
    ],
    "background": {
        "scripts": ["background.js"]
    },
    "minimum_chrome_version": "22.0.0"
}"""

# Background script template for proxy configuration
BACKGROUND_JS_TEMPLATE = Template("""
var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "${scheme}",
            host: "${host}",
            port: parseInt(${port})
        },
        bypassList: ${bypass_list}
    }
};

chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            username: "${username}",
            password: "${password}"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {urls: ["<all_urls>"]},
    ['blocking']
);
""")

# Simple background script without auth (for non-authenticated proxies)
BACKGROUND_JS_NO_AUTH_TEMPLATE = Template("""
var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "${scheme}",
            host: "${host}",
            port: parseInt(${port})
        },
        bypassList: ${bypass_list}
    }
};

chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
""")


class DynamicProxyAuth:
    """Generate Chrome extensions for authenticated proxy support.

    This class creates Chrome extensions dynamically that handle
    proxy authentication, bypassing Selenium's limitations with
    authenticated proxies.

    Usage:
        ```python
        generator = DynamicProxyAuth()

        # From credentials object
        creds = ProxyCredentials("proxy.example.com", 8080, "user", "pass")
        ext_path = generator.create_extension(creds, output_dir="./extensions")

        # From string
        ext_path = generator.create_extension_from_string(
            "proxy.example.com:8080:user:pass",
            output_dir="./extensions"
        )

        # Use with Selenium
        options = webdriver.ChromeOptions()
        options.add_extension(ext_path)
        ```
    """

    name = "dynamic_auth"

    def __init__(
        self,
        scheme: str = "http",
        bypass_list: list[str] | None = None,
    ) -> None:
        """Initialize the proxy auth generator.

        Args:
            scheme: Proxy scheme (http, https, socks4, socks5)
            bypass_list: List of hosts to bypass proxy for
        """
        self.scheme = scheme
        self.bypass_list = bypass_list or ["localhost", "127.0.0.1"]

    def generate_background_js(self, credentials: ProxyCredentials) -> str:
        """Generate background.js content for proxy config.

        Args:
            credentials: Proxy credentials

        Returns:
            JavaScript code as string
        """
        bypass_json = str(self.bypass_list).replace("'", '"')

        if credentials.username and credentials.password:
            return BACKGROUND_JS_TEMPLATE.substitute(
                scheme=self.scheme,
                host=credentials.host,
                port=credentials.port,
                username=credentials.username,
                password=credentials.password,
                bypass_list=bypass_json,
            )
        else:
            return BACKGROUND_JS_NO_AUTH_TEMPLATE.substitute(
                scheme=self.scheme,
                host=credentials.host,
                port=credentials.port,
                bypass_list=bypass_json,
            )

    def create_extension_zip(self, credentials: ProxyCredentials) -> bytes:
        """Create extension as in-memory ZIP bytes.

        Args:
            credentials: Proxy credentials

        Returns:
            ZIP file contents as bytes
        """
        background_js = self.generate_background_js(credentials)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", MANIFEST_JSON)
            zf.writestr("background.js", background_js)

        return buffer.getvalue()

    def create_extension(
        self,
        credentials: ProxyCredentials,
        output_path: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> Path:
        """Create extension and save to file.

        Args:
            credentials: Proxy credentials
            output_path: Full path for the extension file
            output_dir: Directory to save extension (auto-names file)

        Returns:
            Path to the created extension file

        Raises:
            ValueError: If neither output_path nor output_dir specified
        """
        if output_path:
            path = Path(output_path)
        elif output_dir:
            dir_path = Path(output_dir)
            dir_path.mkdir(parents=True, exist_ok=True)
            # Create unique filename based on proxy
            filename = f"proxy_{credentials.host}_{credentials.port}.zip"
            path = dir_path / filename
        else:
            raise ValueError("Either output_path or output_dir must be specified")

        path.parent.mkdir(parents=True, exist_ok=True)
        zip_bytes = self.create_extension_zip(credentials)
        path.write_bytes(zip_bytes)

        return path

    def create_extension_from_string(
        self,
        proxy_string: str,
        output_path: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> Path:
        """Create extension from proxy string.

        Args:
            proxy_string: Proxy in format host:port:user:pass
            output_path: Full path for the extension file
            output_dir: Directory to save extension

        Returns:
            Path to the created extension file
        """
        credentials = ProxyCredentials.from_string(proxy_string)
        return self.create_extension(
            credentials,
            output_path=output_path,
            output_dir=output_dir,
        )

    def write_extension_to_stream(
        self,
        credentials: ProxyCredentials,
        stream: BinaryIO,
    ) -> None:
        """Write extension ZIP to a binary stream.

        Args:
            credentials: Proxy credentials
            stream: Binary stream to write to
        """
        zip_bytes = self.create_extension_zip(credentials)
        stream.write(zip_bytes)


def create_proxy_extension(
    proxy_string: str,
    output_path: str | Path,
    scheme: str = "http",
    bypass_list: list[str] | None = None,
) -> Path:
    """Convenience function to create proxy extension.

    Args:
        proxy_string: Proxy in format host:port:user:pass
        output_path: Path to save the extension
        scheme: Proxy scheme (http, https, socks4, socks5)
        bypass_list: Hosts to bypass

    Returns:
        Path to the created extension
    """
    generator = DynamicProxyAuth(scheme=scheme, bypass_list=bypass_list)
    return generator.create_extension_from_string(
        proxy_string,
        output_path=output_path,
    )
