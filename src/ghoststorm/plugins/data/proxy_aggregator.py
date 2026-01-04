"""Proxy aggregator for downloading and managing proxy lists from multiple sources."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

import aiohttp


@dataclass
class ProxySource:
    """A proxy source definition."""

    name: str
    url: str
    proxy_type: str = "http"  # http, socks4, socks5
    enabled: bool = True


class ProxyAggregator:
    """Aggregates proxies from multiple GitHub and public sources.

    Downloads proxy lists from various sources, deduplicates them,
    and saves to the data/proxies directory.

    Usage:
        ```python
        aggregator = ProxyAggregator()
        count = await aggregator.refresh_all()
        print(f"Downloaded {count} proxies")
        ```
    """

    # Proxy sources - verified working as of 2024
    SOURCES: list[ProxySource] = [
        # Tier 1: Massive lists
        ProxySource(
            "mishakorzik",
            "https://raw.githubusercontent.com/mishakorzik/100000-Proxy/main/proxy.txt",
        ),
        ProxySource(
            "ercin_http",
            "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/http.txt",
        ),
        ProxySource(
            "ercin_socks4",
            "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "ercin_socks5",
            "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/socks5.txt",
            "socks5",
        ),
        ProxySource(
            "speedx_http", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
        ),
        ProxySource(
            "speedx_socks4",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "speedx_socks5",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "socks5",
        ),
        # Tier 2: Fresh/verified lists
        ProxySource(
            "prxchk_http", "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt"
        ),
        ProxySource(
            "prxchk_socks4",
            "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "prxchk_socks5",
            "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
            "socks5",
        ),
        ProxySource(
            "monosans", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"
        ),
        ProxySource(
            "hookzof_socks5",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "socks5",
        ),
        # Tier 3: Additional sources
        ProxySource(
            "murong_http", "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt"
        ),
        ProxySource(
            "murong_socks4",
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "murong_socks5",
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt",
            "socks5",
        ),
        ProxySource(
            "seven_http",
            "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/http.txt",
        ),
        ProxySource(
            "seven_socks4",
            "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/socks4.txt",
            "socks4",
        ),
        ProxySource(
            "seven_socks5",
            "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/socks5.txt",
            "socks5",
        ),
        ProxySource("alii_http", "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt"),
        ProxySource(
            "p4p_http", "https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt"
        ),
        ProxySource(
            "jetkai",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
        ),
        ProxySource(
            "clarketm",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        ),
        ProxySource(
            "sunny", "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"
        ),
    ]

    # IP:PORT pattern
    PROXY_PATTERN = re.compile(r"^(\d{1,3}\.){3}\d{1,3}:\d{2,5}$")

    def __init__(
        self,
        output_dir: str | Path | None = None,
        timeout: float = 30.0,
        max_concurrent: int = 10,
    ) -> None:
        """Initialize proxy aggregator.

        Args:
            output_dir: Directory to save proxy files
            timeout: Request timeout in seconds
            max_concurrent: Max concurrent downloads
        """
        if output_dir is None:
            # Default to data/proxies relative to this file
            self.output_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "proxies"
        else:
            self.output_dir = Path(output_dir)

        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _download_source(
        self,
        session: aiohttp.ClientSession,
        source: ProxySource,
    ) -> list[str]:
        """Download proxies from a single source.

        Args:
            session: aiohttp session
            source: Proxy source to download

        Returns:
            List of proxy strings
        """
        if not source.enabled:
            return []

        async with self._semaphore:
            try:
                async with session.get(source.url) as response:
                    if response.status != 200:
                        return []

                    content = await response.text()
                    lines = content.strip().split("\n")

                    # Filter valid proxies
                    proxies = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Extract IP:PORT if present
                            if self.PROXY_PATTERN.match(line):
                                proxies.append(line)
                            elif ":" in line:
                                # Try to extract IP:PORT from formatted lines
                                parts = line.split()
                                if parts and self.PROXY_PATTERN.match(parts[0]):
                                    proxies.append(parts[0])

                    return proxies

            except Exception:
                return []

    async def refresh_all(self, deduplicate: bool = False) -> int:
        """Download proxies from all sources.

        Args:
            deduplicate: Whether to remove duplicate proxies

        Returns:
            Total number of proxies downloaded
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        all_proxies: list[str] = []

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            tasks = [self._download_source(session, source) for source in self.SOURCES]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_proxies.extend(result)

        if deduplicate:
            all_proxies = list(set(all_proxies))

        # Save to aggregated.txt
        output_path = self.output_dir / "aggregated.txt"
        with open(output_path, "w") as f:
            f.write("\n".join(all_proxies))

        return len(all_proxies)

    async def refresh_by_type(self) -> dict[str, int]:
        """Download and organize proxies by type.

        Returns:
            Dict of proxy type to count
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        proxies_by_type: dict[str, list[str]] = {
            "http": [],
            "socks4": [],
            "socks5": [],
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for source in self.SOURCES:
                proxies = await self._download_source(session, source)
                proxies_by_type[source.proxy_type].extend(proxies)

        # Save by type
        counts = {}
        for proxy_type, proxies in proxies_by_type.items():
            unique_proxies = list(set(proxies))
            type_dir = self.output_dir / proxy_type
            type_dir.mkdir(exist_ok=True)

            output_path = type_dir / "all.txt"
            with open(output_path, "w") as f:
                f.write("\n".join(unique_proxies))

            counts[proxy_type] = len(unique_proxies)

        return counts

    def get_source_count(self) -> int:
        """Get number of enabled sources."""
        return sum(1 for s in self.SOURCES if s.enabled)

    def add_source(self, name: str, url: str, proxy_type: str = "http") -> None:
        """Add a new proxy source.

        Args:
            name: Source identifier
            url: URL to fetch proxies from
            proxy_type: Type of proxies (http, socks4, socks5)
        """
        self.SOURCES.append(ProxySource(name, url, proxy_type))

    def disable_source(self, name: str) -> bool:
        """Disable a source by name.

        Args:
            name: Source name to disable

        Returns:
            True if source was found and disabled
        """
        for source in self.SOURCES:
            if source.name == name:
                source.enabled = False
                return True
        return False
