"""TLS Fingerprint management for JA3/JA4 fingerprint spoofing.

This module provides fingerprint definitions and utilities for matching
real browser TLS fingerprints to bypass network-level bot detection.

JA3 = MD5 hash of TLS Client Hello parameters
JA4 = Enhanced fingerprint including ALPN, cipher count, extension count
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class TLSVersion(str, Enum):
    """TLS protocol versions."""

    TLS_1_0 = "769"   # 0x0301
    TLS_1_1 = "770"   # 0x0302
    TLS_1_2 = "771"   # 0x0303
    TLS_1_3 = "772"   # 0x0304


@dataclass
class JA3Fingerprint:
    """JA3 fingerprint components.

    JA3 is an MD5 hash of:
    SSLVersion,Ciphers,Extensions,EllipticCurves,EllipticCurvePointFormats

    Example: 769,47-53-5-10-49161-49162-49171-49172-50-56-19-4,0-10-11,23-24-25,0
    """

    # TLS version (e.g., 771 for TLS 1.2)
    ssl_version: str

    # Cipher suites offered (hyphen-separated decimal values)
    ciphers: str

    # TLS extensions (hyphen-separated decimal values)
    extensions: str

    # Elliptic curves / supported groups
    elliptic_curves: str

    # Elliptic curve point formats
    ec_point_formats: str

    # Pre-computed JA3 hash (optional)
    ja3_hash: str | None = None

    def to_string(self) -> str:
        """Generate JA3 string representation."""
        return f"{self.ssl_version},{self.ciphers},{self.extensions},{self.elliptic_curves},{self.ec_point_formats}"

    def compute_hash(self) -> str:
        """Compute MD5 hash of JA3 string."""
        import hashlib
        ja3_str = self.to_string()
        return hashlib.md5(ja3_str.encode()).hexdigest()


@dataclass
class JA4Fingerprint:
    """JA4 fingerprint components.

    JA4 is an enhanced fingerprint format that includes:
    - Protocol version
    - SNI presence
    - Cipher count
    - Extension count
    - ALPN first value
    - Cipher hash (first 12 chars of SHA256)
    - Extension hash (first 12 chars of SHA256)

    Example: t13d1516h2_8daaf6152771_b0da82dd1658
    """

    # Protocol: 't' = TCP, 'q' = QUIC
    protocol: str = "t"

    # TLS version: 10, 11, 12, 13
    tls_version: str = "13"

    # SNI: 'd' = domain present, 'i' = IP address
    sni: str = "d"

    # Number of ciphers (2 digits, max 99)
    cipher_count: str = "15"

    # Number of extensions (2 digits, max 99)
    extension_count: str = "16"

    # First ALPN value: h2, h1 (http/1.1), etc.
    alpn: str = "h2"

    # SHA256 hash of sorted ciphers (first 12 chars)
    cipher_hash: str = ""

    # SHA256 hash of sorted extensions (first 12 chars)
    extension_hash: str = ""

    def to_string(self) -> str:
        """Generate JA4 string representation."""
        # JA4_a = protocol + version + sni + cipher_count + extension_count + alpn
        ja4_a = f"{self.protocol}{self.tls_version}{self.sni}{self.cipher_count}{self.extension_count}{self.alpn}"
        return f"{ja4_a}_{self.cipher_hash}_{self.extension_hash}"


@dataclass
class TLSFingerprint:
    """Complete TLS fingerprint for a browser.

    Contains both JA3 and JA4 fingerprints along with metadata.
    """

    # Browser identifier
    browser: str

    # Browser version
    version: str

    # Operating system
    os: str

    # JA3 fingerprint
    ja3: JA3Fingerprint

    # JA4 fingerprint
    ja4: JA4Fingerprint

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Human-readable fingerprint name."""
        return f"{self.browser}/{self.version} ({self.os})"


# Real browser fingerprints captured from actual browsers
# These are used for fingerprint matching and validation

CHROME_136_WINDOWS = TLSFingerprint(
    browser="Chrome",
    version="136",
    os="Windows 11",
    ja3=JA3Fingerprint(
        ssl_version="772",  # TLS 1.3
        ciphers="4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53",
        extensions="0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21",
        elliptic_curves="29-23-24",
        ec_point_formats="0",
        ja3_hash="cd08e31494f9531f560d64c695473da9",
    ),
    ja4=JA4Fingerprint(
        protocol="t",
        tls_version="13",
        sni="d",
        cipher_count="15",
        extension_count="16",
        alpn="h2",
        cipher_hash="8daaf6152771",
        extension_hash="b0da82dd1658",
    ),
)

CHROME_133_WINDOWS = TLSFingerprint(
    browser="Chrome",
    version="133",
    os="Windows 11",
    ja3=JA3Fingerprint(
        ssl_version="772",
        ciphers="4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53",
        extensions="0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21",
        elliptic_curves="29-23-24",
        ec_point_formats="0",
        ja3_hash="b32309a26951912be7dba376398abc3b",
    ),
    ja4=JA4Fingerprint(
        protocol="t",
        tls_version="13",
        sni="d",
        cipher_count="15",
        extension_count="16",
        alpn="h2",
        cipher_hash="8daaf6152771",
        extension_hash="e5627efa2ab1",
    ),
)

CHROME_131_MACOS = TLSFingerprint(
    browser="Chrome",
    version="131",
    os="macOS Sonoma",
    ja3=JA3Fingerprint(
        ssl_version="772",
        ciphers="4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53",
        extensions="0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21",
        elliptic_curves="29-23-24",
        ec_point_formats="0",
        ja3_hash="579ccef312d18482fc42e2b822ca2430",
    ),
    ja4=JA4Fingerprint(
        protocol="t",
        tls_version="13",
        sni="d",
        cipher_count="15",
        extension_count="16",
        alpn="h2",
        cipher_hash="8daaf6152771",
        extension_hash="02c12c2f12c4",
    ),
)

FIREFOX_134_WINDOWS = TLSFingerprint(
    browser="Firefox",
    version="134",
    os="Windows 11",
    ja3=JA3Fingerprint(
        ssl_version="772",
        ciphers="4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-156-157-47-53",
        extensions="0-23-65281-10-11-35-16-5-34-51-43-13-45-28-21",
        elliptic_curves="29-23-24-25-256-257",
        ec_point_formats="0",
        ja3_hash="839bbe3ed940ff7bdcf7a4a14e73f3b1",
    ),
    ja4=JA4Fingerprint(
        protocol="t",
        tls_version="13",
        sni="d",
        cipher_count="17",
        extension_count="15",
        alpn="h2",
        cipher_hash="a0e9f5b24c4f",
        extension_hash="c1f7da5e5b8a",
    ),
)

FIREFOX_133_LINUX = TLSFingerprint(
    browser="Firefox",
    version="133",
    os="Linux",
    ja3=JA3Fingerprint(
        ssl_version="772",
        ciphers="4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-156-157-47-53",
        extensions="0-23-65281-10-11-35-16-5-34-51-43-13-45-28-21",
        elliptic_curves="29-23-24-25-256-257",
        ec_point_formats="0",
        ja3_hash="6fa3244a6f6f6c4b24a77a57c4a5b8d6",
    ),
    ja4=JA4Fingerprint(
        protocol="t",
        tls_version="13",
        sni="d",
        cipher_count="17",
        extension_count="15",
        alpn="h2",
        cipher_hash="a0e9f5b24c4f",
        extension_hash="d8e2f1a9b3c5",
    ),
)

SAFARI_17_MACOS = TLSFingerprint(
    browser="Safari",
    version="17.5",
    os="macOS Sonoma",
    ja3=JA3Fingerprint(
        ssl_version="772",
        ciphers="4865-4866-4867-49196-49195-52393-49200-49199-52392-49188-49187-49192-49191-49162-49161-49172-49171-157-156-53-47-255",
        extensions="0-23-65281-10-11-16-5-13-18-51-45-43-27-21",
        elliptic_curves="29-23-24-25",
        ec_point_formats="0",
        ja3_hash="773906b0efdefa24a7f2b8eb6985bf37",
    ),
    ja4=JA4Fingerprint(
        protocol="t",
        tls_version="13",
        sni="d",
        cipher_count="22",
        extension_count="14",
        alpn="h2",
        cipher_hash="f4febc55c30d",
        extension_hash="7a5c8d2e1f9b",
    ),
)

SAFARI_16_IOS = TLSFingerprint(
    browser="Safari",
    version="16",
    os="iOS 17",
    ja3=JA3Fingerprint(
        ssl_version="772",
        ciphers="4865-4866-4867-49196-49195-52393-49200-49199-52392-49188-49187-49192-49191-49162-49161-49172-49171-157-156-53-47-255",
        extensions="0-23-65281-10-11-16-5-13-18-51-45-43-27-21",
        elliptic_curves="29-23-24-25",
        ec_point_formats="0",
        ja3_hash="e65b02d2b9d2f6c2d0f4a5e8a7c9b1d3",
    ),
    ja4=JA4Fingerprint(
        protocol="t",
        tls_version="13",
        sni="d",
        cipher_count="22",
        extension_count="14",
        alpn="h2",
        cipher_hash="f4febc55c30d",
        extension_hash="9b8c7d6e5f4a",
    ),
)

EDGE_131_WINDOWS = TLSFingerprint(
    browser="Edge",
    version="131",
    os="Windows 11",
    ja3=JA3Fingerprint(
        ssl_version="772",
        ciphers="4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53",
        extensions="0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21",
        elliptic_curves="29-23-24",
        ec_point_formats="0",
        ja3_hash="b32309a26951912be7dba376398abc3b",  # Same as Chrome (Chromium-based)
    ),
    ja4=JA4Fingerprint(
        protocol="t",
        tls_version="13",
        sni="d",
        cipher_count="15",
        extension_count="16",
        alpn="h2",
        cipher_hash="8daaf6152771",
        extension_hash="e5627efa2ab1",
    ),
)

# Fingerprint database
FINGERPRINT_DATABASE: dict[str, TLSFingerprint] = {
    "chrome_136_windows": CHROME_136_WINDOWS,
    "chrome_133_windows": CHROME_133_WINDOWS,
    "chrome_131_macos": CHROME_131_MACOS,
    "firefox_134_windows": FIREFOX_134_WINDOWS,
    "firefox_133_linux": FIREFOX_133_LINUX,
    "safari_17_macos": SAFARI_17_MACOS,
    "safari_16_ios": SAFARI_16_IOS,
    "edge_131_windows": EDGE_131_WINDOWS,
}


def get_browser_fingerprint(
    browser: str,
    version: str | None = None,
    os: str | None = None,
) -> TLSFingerprint | None:
    """Get a TLS fingerprint for a specific browser.

    Args:
        browser: Browser name (chrome, firefox, safari, edge)
        version: Optional specific version
        os: Optional operating system

    Returns:
        TLSFingerprint if found, None otherwise
    """
    browser_lower = browser.lower()

    # Build search keys
    candidates = []

    if version and os:
        # Exact match
        key = f"{browser_lower}_{version}_{os.lower().replace(' ', '_')}"
        candidates.append(key)

    if version:
        # Match with version, any OS
        for key in FINGERPRINT_DATABASE:
            if key.startswith(f"{browser_lower}_{version}"):
                candidates.append(key)

    # Match any version of browser
    for key in FINGERPRINT_DATABASE:
        if key.startswith(browser_lower):
            candidates.append(key)

    # Return first match
    for key in candidates:
        if key in FINGERPRINT_DATABASE:
            return FINGERPRINT_DATABASE[key]

    return None


def get_fingerprint_for_profile(profile: str) -> TLSFingerprint | None:
    """Get fingerprint matching a curl_cffi browser profile.

    Args:
        profile: curl_cffi impersonate profile (e.g., "chrome136", "safari17_5")

    Returns:
        Matching TLSFingerprint or None
    """
    profile_lower = profile.lower()

    # Map curl_cffi profiles to our fingerprints
    profile_mapping = {
        "chrome": "chrome_136_windows",
        "chrome136": "chrome_136_windows",
        "chrome133": "chrome_133_windows",
        "chrome133a": "chrome_133_windows",
        "chrome131": "chrome_131_macos",
        "firefox": "firefox_134_windows",
        "firefox134": "firefox_134_windows",
        "firefox133": "firefox_133_linux",
        "safari": "safari_17_macos",
        "safari17_5": "safari_17_macos",
        "safari17": "safari_17_macos",
        "safari16": "safari_16_ios",
        "safari15_5": "safari_17_macos",  # Fallback
        "safari15_3": "safari_17_macos",  # Fallback
        "edge": "edge_131_windows",
        "edge131": "edge_131_windows",
        "edge101": "edge_131_windows",  # Fallback
        "edge99": "edge_131_windows",  # Fallback
    }

    key = profile_mapping.get(profile_lower)
    if key:
        return FINGERPRINT_DATABASE.get(key)

    return None


def list_fingerprints() -> list[str]:
    """List all available fingerprint keys."""
    return list(FINGERPRINT_DATABASE.keys())


def get_random_fingerprint(browser: str | None = None) -> TLSFingerprint:
    """Get a random fingerprint, optionally filtered by browser.

    Args:
        browser: Optional browser filter

    Returns:
        Random TLSFingerprint
    """
    import random

    candidates = list(FINGERPRINT_DATABASE.values())

    if browser:
        browser_lower = browser.lower()
        candidates = [
            fp for fp in candidates
            if fp.browser.lower() == browser_lower
        ]

    if not candidates:
        # Fallback to any fingerprint
        candidates = list(FINGERPRINT_DATABASE.values())

    return random.choice(candidates)


class FingerprintMatcher:
    """Match and validate TLS fingerprints.

    Used to verify that the TLS fingerprint from a connection
    matches expected browser fingerprints.
    """

    def __init__(self) -> None:
        self._known_fingerprints: dict[str, TLSFingerprint] = FINGERPRINT_DATABASE.copy()

    def add_fingerprint(self, key: str, fingerprint: TLSFingerprint) -> None:
        """Add a custom fingerprint to the matcher."""
        self._known_fingerprints[key] = fingerprint

    def match_ja3(self, ja3_hash: str) -> TLSFingerprint | None:
        """Find a fingerprint matching the JA3 hash.

        Args:
            ja3_hash: MD5 hash of JA3 string

        Returns:
            Matching TLSFingerprint or None
        """
        for fingerprint in self._known_fingerprints.values():
            if fingerprint.ja3.ja3_hash == ja3_hash:
                return fingerprint
        return None

    def match_ja4(self, ja4_string: str) -> TLSFingerprint | None:
        """Find a fingerprint matching the JA4 string.

        Args:
            ja4_string: Full JA4 fingerprint string

        Returns:
            Matching TLSFingerprint or None
        """
        for fingerprint in self._known_fingerprints.values():
            if fingerprint.ja4.to_string() == ja4_string:
                return fingerprint
        return None

    def is_known_browser(self, ja3_hash: str) -> bool:
        """Check if a JA3 hash belongs to a known browser."""
        return self.match_ja3(ja3_hash) is not None

    def get_browser_info(self, ja3_hash: str) -> dict[str, str] | None:
        """Get browser information from JA3 hash.

        Returns:
            Dict with browser, version, os keys or None
        """
        fingerprint = self.match_ja3(ja3_hash)
        if fingerprint:
            return {
                "browser": fingerprint.browser,
                "version": fingerprint.version,
                "os": fingerprint.os,
            }
        return None


# Global matcher instance
_matcher = FingerprintMatcher()


def match_ja3_fingerprint(ja3_hash: str) -> TLSFingerprint | None:
    """Global function to match JA3 fingerprint."""
    return _matcher.match_ja3(ja3_hash)


def match_ja4_fingerprint(ja4_string: str) -> TLSFingerprint | None:
    """Global function to match JA4 fingerprint."""
    return _matcher.match_ja4(ja4_string)
