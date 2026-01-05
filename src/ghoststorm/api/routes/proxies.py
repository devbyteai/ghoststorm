"""Proxy management API routes with real website scrapers."""

from __future__ import annotations

import asyncio
import contextlib
import random
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter
from pydantic import BaseModel

from ghoststorm.plugins.data.proxy_aggregator import ProxyAggregator

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
PROXY_PATTERN = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})")

# Randomized headers to prevent fingerprinting during proxy scraping
SCRAPER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

SCRAPER_ACCEPT_LANGUAGES = [
    "en-US,en;q=0.5",
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "en;q=0.9,en-US;q=0.8",
    "en-US,en;q=0.8,es;q=0.6",
]


def _get_random_scraper_headers() -> dict[str, str]:
    """Get randomized headers for proxy scraping to avoid fingerprinting."""
    return {
        "User-Agent": random.choice(SCRAPER_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": random.choice(SCRAPER_ACCEPT_LANGUAGES),
    }


# Job tracking for scrape and test operations
_jobs: dict[str, dict[str, Any]] = {}


def _cleanup_old_jobs(max_age_hours: int = 1) -> int:
    """Remove jobs older than max_age_hours to prevent memory leaks.

    Returns the number of jobs cleaned up.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    expired = []

    for job_id, job in _jobs.items():
        started_at = job.get("started_at")
        if started_at:
            try:
                job_time = datetime.fromisoformat(started_at)
                if job_time < cutoff:
                    expired.append(job_id)
            except (ValueError, TypeError):
                # Invalid timestamp, mark for cleanup
                expired.append(job_id)

    for job_id in expired:
        del _jobs[job_id]

    return len(expired)


def is_valid_proxy(proxy: str) -> bool:
    """Filter out garbage/private/invalid proxies."""
    try:
        ip, port = proxy.split(":")
        port_num = int(port)

        # Invalid port
        if port_num < 1 or port_num > 65535:
            return False

        # Parse IP octets
        octets = [int(x) for x in ip.split(".")]
        if len(octets) != 4:
            return False

        # Check each octet is valid
        for octet in octets:
            if octet < 0 or octet > 255:
                return False

        # Filter private/reserved IPs
        first = octets[0]
        second = octets[1]

        # 0.x.x.x - Invalid
        if first == 0:
            return False
        # 10.x.x.x - Private
        if first == 10:
            return False
        # 127.x.x.x - Loopback
        if first == 127:
            return False
        # 169.254.x.x - Link-local
        if first == 169 and second == 254:
            return False
        # 172.16-31.x.x - Private
        if first == 172 and 16 <= second <= 31:
            return False
        # 192.168.x.x - Private
        if first == 192 and second == 168:
            return False
        # 224-255.x.x.x - Multicast/Reserved
        return not first >= 224
    except Exception:
        return False


def filter_valid_proxies(proxies: set[str]) -> set[str]:
    """Filter a set of proxies to only valid public IPs."""
    return {p for p in proxies if is_valid_proxy(p)}


# ============ PROXY SOURCES (imported from proxy_aggregator.py) ============

# Convert ProxySource dataclass to dict format for backward compatibility
PROXY_SOURCES = [
    {
        "id": source.name,
        "name": source.name.replace("_", " ").title(),
        "url": source.url,
        "type": source.scrape_type,
    }
    for source in ProxyAggregator.SOURCES
    if source.enabled
]

# Keep this for reference - old format was:
# {
#     "id": "freeproxylist",
#     "name": "Free-Proxy-List.net",
#     "url": "https://free-proxy-list.net/",
#     "type": "html_table",
# },

# ============ SCRAPER FUNCTIONS ============


async def scrape_html_table(client: httpx.AsyncClient, url: str) -> set[str]:
    """Scrape proxies from HTML table (free-proxy-list.net style)."""
    proxies = set()
    try:
        response = await client.get(url)
        if response.status_code != 200:
            return proxies

        soup = BeautifulSoup(response.text, "html.parser")

        # Find table rows
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    ip = cells[0].get_text(strip=True)
                    port = cells[1].get_text(strip=True)
                    if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) and port.isdigit():
                        proxies.add(f"{ip}:{port}")
    except Exception:
        pass
    return proxies


async def scrape_proxynova(client: httpx.AsyncClient, url: str) -> set[str]:
    """Scrape ProxyNova (has obfuscated IPs in JS)."""
    proxies = set()
    try:
        response = await client.get(url)
        if response.status_code != 200:
            return proxies

        soup = BeautifulSoup(response.text, "html.parser")
        for row in soup.select("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                # ProxyNova obfuscates IP in script tag
                ip_cell = cells[0]
                script = ip_cell.find("script")
                if script:
                    # Extract IP from document.write()
                    match = re.search(
                        r"'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'", script.string or ""
                    )
                    if match:
                        ip = match.group(1)
                        port = cells[1].get_text(strip=True)
                        if port.isdigit():
                            proxies.add(f"{ip}:{port}")
                else:
                    ip = ip_cell.get_text(strip=True)
                    if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip):
                        port = cells[1].get_text(strip=True)
                        if port.isdigit():
                            proxies.add(f"{ip}:{port}")
    except Exception:
        pass
    return proxies


async def scrape_hidemy(client: httpx.AsyncClient, url: str) -> set[str]:
    """Scrape HideMy.name proxy list."""
    proxies = set()
    try:
        response = await client.get(url)
        if response.status_code != 200:
            return proxies

        soup = BeautifulSoup(response.text, "html.parser")
        for row in soup.select("table tbody tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                ip = cells[0].get_text(strip=True)
                port = cells[1].get_text(strip=True)
                if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) and port.isdigit():
                    proxies.add(f"{ip}:{port}")
    except Exception:
        pass
    return proxies


async def scrape_spys(client: httpx.AsyncClient, url: str) -> set[str]:
    """Scrape Spys.one proxy list (complex JS-encoded IPs)."""
    proxies = set()
    try:
        response = await client.get(url)
        if response.status_code != 200:
            return proxies

        soup = BeautifulSoup(response.text, "html.parser")

        # Spys.one uses font tags with class for proxy display
        for row in soup.select("tr.spy1x, tr.spy1xx"):
            text = row.get_text()
            # Find IP:port pattern in the row text
            matches = PROXY_PATTERN.findall(text)
            for ip, port in matches:
                proxies.add(f"{ip}:{port}")

        # Also try finding in font tags
        for font in soup.select("font.spy14"):
            text = font.get_text()
            match = PROXY_PATTERN.search(text)
            if match:
                proxies.add(f"{match.group(1)}:{match.group(2)}")
    except Exception:
        pass
    return proxies


async def scrape_geonode(client: httpx.AsyncClient, url: str) -> set[str]:
    """Scrape Geonode.com website (not API)."""
    proxies = set()
    try:
        response = await client.get(url)
        if response.status_code != 200:
            return proxies

        soup = BeautifulSoup(response.text, "html.parser")

        # Geonode renders proxies in table or data attributes
        for row in soup.select("table tbody tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                ip = cells[0].get_text(strip=True)
                port = cells[1].get_text(strip=True)
                if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) and port.isdigit():
                    proxies.add(f"{ip}:{port}")

        # Also search for ip:port patterns in the page
        text = soup.get_text()
        for match in PROXY_PATTERN.finditer(text):
            proxies.add(f"{match.group(1)}:{match.group(2)}")
    except Exception:
        pass
    return proxies


async def scrape_proxylistorg(client: httpx.AsyncClient, url: str) -> set[str]:
    """Scrape Proxy-List.org (base64 encoded proxies)."""
    proxies = set()
    try:
        import base64

        response = await client.get(url)
        if response.status_code != 200:
            return proxies

        soup = BeautifulSoup(response.text, "html.parser")

        # Proxy-List.org encodes proxies in base64 within list items
        for li in soup.select("ul.proxy-list li"):
            # The proxy is in a script or encoded
            text = li.get_text(strip=True)
            # Try to find base64 encoded content
            for script in li.find_all("script"):
                if script.string:
                    # Look for Proxy() calls or base64
                    b64_match = re.search(r"Proxy\('([A-Za-z0-9+/=]+)'\)", script.string)
                    if b64_match:
                        try:
                            decoded = base64.b64decode(b64_match.group(1)).decode("utf-8")
                            match = PROXY_PATTERN.search(decoded)
                            if match:
                                proxies.add(f"{match.group(1)}:{match.group(2)}")
                        except Exception:
                            pass

        # Fallback: look for ip:port patterns directly
        text = soup.get_text()
        for match in PROXY_PATTERN.finditer(text):
            proxies.add(f"{match.group(1)}:{match.group(2)}")
    except Exception:
        pass
    return proxies


async def scrape_raw_txt(html: str) -> set[str]:
    """Handle raw text proxy lists (IP:PORT per line).

    Used for API sources like Proxifly, ProxyScrape, Jetkai, TheSpeedX, etc.
    These return plain text with one proxy per line.
    """
    proxies: set[str] = set()
    for line in html.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Handle various formats: IP:PORT, IP:PORT:USER:PASS, etc.
        match = PROXY_PATTERN.match(line)
        if match:
            proxies.add(f"{match.group(1)}:{match.group(2)}")
    return proxies


SCRAPER_MAP = {
    "html_table": scrape_html_table,
    "raw_txt": scrape_raw_txt,  # For API sources (Proxifly, ProxyScrape, etc.)
    "proxynova": scrape_proxynova,
    "hidemy": scrape_hidemy,
    "spys": scrape_spys,
    "geonode": scrape_geonode,
    "proxylistorg": scrape_proxylistorg,
}


# ============ UTILITY FUNCTIONS ============


def count_lines(file_path: Path) -> int:
    """Count non-empty lines in a file."""
    if not file_path.exists():
        return 0
    try:
        with open(file_path) as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def read_proxies(file_path: Path) -> set[str]:
    """Read proxies from a file into a set."""
    if not file_path.exists():
        return set()
    try:
        with open(file_path) as f:
            return {line.strip() for line in f if line.strip()}
    except Exception:
        return set()


# ============ API ENDPOINTS ============


@router.get("/sources")
async def get_sources() -> dict:
    """Get list of proxy sources."""
    return {"sources": PROXY_SOURCES}


@router.get("/stats")
async def get_proxy_stats() -> dict:
    """Get proxy statistics."""
    proxy_dir = DATA_DIR / "proxies"

    total = 0
    alive = 0

    for file_name in ["aggregated.txt", "massive.txt", "sample.txt"]:
        total += count_lines(proxy_dir / file_name)

    alive = count_lines(proxy_dir / "alive_proxies.txt")
    alive += count_lines(proxy_dir / "working_http.txt")

    for proxy_type in ["http", "socks4", "socks5"]:
        type_dir = proxy_dir / proxy_type
        if type_dir.is_dir():
            for f in type_dir.glob("*.txt"):
                total += count_lines(f)

    # Track tested count from metadata file
    tested_file = proxy_dir / ".tested_count"
    tested = 0
    if tested_file.exists():
        try:
            tested = int(tested_file.read_text().strip())
        except (ValueError, OSError):
            tested = 0

    # Calculate accurate stats
    # - If no proxies in files, reset tested count
    if total == 0 and alive == 0:
        # No proxies - reset stale tested count
        if tested_file.exists():
            tested_file.unlink()
        tested = 0
        dead = 0
        untested = 0
    elif tested > 0:
        # Cap tested at total (can't test more than exist)
        tested = min(tested, total + alive)
        dead = max(0, tested - alive)
        untested = max(0, total - tested)
    else:
        # No test run yet - all are untested
        dead = 0
        untested = total

    return {
        "total": total,
        "alive": alive,
        "dead": dead,
        "untested": untested,
        "tested": tested,
    }


@router.post("/scrape/start")
async def start_scrape() -> dict:
    """Start scraping all proxy sources. Returns job_id for tracking."""
    # Cleanup old jobs to prevent memory leak
    _cleanup_old_jobs()

    job_id = str(uuid4())[:8]

    _jobs[job_id] = {
        "type": "scrape",
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "sources_total": len(PROXY_SOURCES),
        "sources_done": 0,
        "current_source": "",
        "proxies_found": 0,
        "results": [],
        "errors": [],
    }

    # Start scraping in background
    asyncio.create_task(_run_scrape_job(job_id))

    return {"job_id": job_id, "sources_total": len(PROXY_SOURCES)}


async def _scrape_with_httpx(url: str) -> set[str]:
    """Tier 1: Fast scrape with httpx (stealth: 2)."""
    proxies: set[str] = set()
    async with httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    ) as client:
        response = await client.get(url)
        if response.status_code != 200:
            return proxies
        proxies = await _extract_proxies_from_html(response.text)
    return proxies


async def _scrape_with_aiohttp(url: str) -> set[str]:
    """Tier 2: aiohttp with different TLS fingerprint (stealth: 3)."""
    import aiohttp

    proxies: set[str] = set()
    # Use randomized headers to prevent fingerprinting
    headers = _get_random_scraper_headers()
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status != 200:
                return proxies
            html = await response.text()
            proxies = await _extract_proxies_from_html(html)
    return proxies


def _scrape_with_curl_cffi_sync(url: str) -> set[str]:
    """Tier 3: curl_cffi impersonating Chrome TLS (stealth: 7)."""
    from curl_cffi import requests as curl_requests

    proxies: set[str] = set()
    response = curl_requests.get(
        url,
        impersonate="chrome120",
        timeout=15,
        allow_redirects=True,
    )
    if response.status_code != 200:
        return proxies
    soup = BeautifulSoup(response.text, "html.parser")
    # Extract from tables
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                ip = cells[0].get_text(strip=True)
                port = cells[1].get_text(strip=True)
                if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) and port.isdigit():
                    proxies.add(f"{ip}:{port}")
    # Also search text
    text = soup.get_text()
    for match in PROXY_PATTERN.finditer(text):
        proxies.add(f"{match.group(1)}:{match.group(2)}")
    return proxies


async def _scrape_with_curl_cffi(url: str) -> set[str]:
    """Tier 3: curl_cffi async wrapper (stealth: 7)."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(None, _scrape_with_curl_cffi_sync, url)


def _scrape_with_cloudscraper_sync(url: str) -> set[str]:
    """Tier 4: cloudscraper for Cloudflare bypass (stealth: 6)."""
    import cloudscraper

    proxies: set[str] = set()
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    response = scraper.get(url, timeout=15)
    if response.status_code != 200:
        return proxies
    soup = BeautifulSoup(response.text, "html.parser")
    # Extract from tables
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                ip = cells[0].get_text(strip=True)
                port = cells[1].get_text(strip=True)
                if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) and port.isdigit():
                    proxies.add(f"{ip}:{port}")
    # Also search text
    text = soup.get_text()
    for match in PROXY_PATTERN.finditer(text):
        proxies.add(f"{match.group(1)}:{match.group(2)}")
    return proxies


async def _scrape_with_cloudscraper(url: str) -> set[str]:
    """Tier 5: cloudscraper async wrapper (stealth: 6)."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(None, _scrape_with_cloudscraper_sync, url)


def _scrape_with_requests_sync(url: str) -> set[str]:
    """Tier 3: requests with different TLS (stealth: 2)."""
    import requests

    proxies: set[str] = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
    if response.status_code != 200:
        return proxies
    soup = BeautifulSoup(response.text, "html.parser")
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                ip = cells[0].get_text(strip=True)
                port = cells[1].get_text(strip=True)
                if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) and port.isdigit():
                    proxies.add(f"{ip}:{port}")
    text = soup.get_text()
    for match in PROXY_PATTERN.finditer(text):
        proxies.add(f"{match.group(1)}:{match.group(2)}")
    return proxies


async def _scrape_with_requests(url: str) -> set[str]:
    """Tier 3: requests async wrapper (stealth: 2)."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(None, _scrape_with_requests_sync, url)


async def _scrape_with_playwright(url: str, browser_context) -> set[str]:
    """Tier 6: Standard Playwright (stealth: 5)."""
    proxies: set[str] = set()
    page = await browser_context.new_page()
    try:
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        content = await page.content()
        proxies = await _extract_proxies_from_html(content)
    finally:
        await page.close()
    return proxies


def _scrape_with_nodriver_sync(url: str) -> set[str]:
    """Tier 8: nodriver pure CDP (stealth: 9)."""
    import nodriver as nd

    proxies: set[str] = set()

    async def _run():
        browser = await nd.start(headless=True)
        page = await browser.get(url)
        await page.sleep(3)
        content = await page.get_content()
        await browser.stop()
        return content

    import asyncio

    try:
        loop = asyncio.new_event_loop()
        content = loop.run_until_complete(_run())
        loop.close()
        soup = BeautifulSoup(content, "html.parser")
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    ip = cells[0].get_text(strip=True)
                    port = cells[1].get_text(strip=True)
                    if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) and port.isdigit():
                        proxies.add(f"{ip}:{port}")
        text = soup.get_text()
        for match in PROXY_PATTERN.finditer(text):
            proxies.add(f"{match.group(1)}:{match.group(2)}")
    except Exception:
        pass
    return proxies


async def _scrape_with_nodriver(url: str) -> set[str]:
    """Tier 8: nodriver async wrapper (stealth: 9)."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(None, _scrape_with_nodriver_sync, url)


def _scrape_with_uc_sync(url: str) -> set[str]:
    """Tier 9: undetected-chromedriver (stealth: 8)."""
    import undetected_chromedriver as uc

    proxies: set[str] = set()
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = None
    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.get(url)
        import time

        time.sleep(3)
        content = driver.page_source
        soup = BeautifulSoup(content, "html.parser")
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 2:
                    ip = cells[0].get_text(strip=True)
                    port = cells[1].get_text(strip=True)
                    if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) and port.isdigit():
                        proxies.add(f"{ip}:{port}")
        text = soup.get_text()
        for match in PROXY_PATTERN.finditer(text):
            proxies.add(f"{match.group(1)}:{match.group(2)}")
    except Exception:
        pass
    finally:
        if driver:
            with contextlib.suppress(Exception):
                driver.quit()
    return proxies


async def _scrape_with_uc(url: str) -> set[str]:
    """Tier 9: undetected-chromedriver async wrapper (stealth: 8)."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(None, _scrape_with_uc_sync, url)


async def _extract_proxies_from_html(html: str) -> set[str]:
    """Extract proxies from HTML content."""
    proxies: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")

    # Extract from tables
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                ip = cells[0].get_text(strip=True)
                port = cells[1].get_text(strip=True)
                if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip) and port.isdigit():
                    proxies.add(f"{ip}:{port}")

    # Also search text for ip:port
    text = soup.get_text()
    for match in PROXY_PATTERN.finditer(text):
        proxies.add(f"{match.group(1)}:{match.group(2)}")

    return proxies


async def _scrape_with_patchright(url: str, browser_context) -> set[str]:
    """Scrape with Patchright (Chromium, stealth level 9)."""
    proxies: set[str] = set()
    page = await browser_context.new_page()
    try:
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)  # Let JS render
        content = await page.content()
        proxies = await _extract_proxies_from_html(content)
    finally:
        await page.close()
    return proxies


async def _scrape_with_camoufox(url: str, browser_context) -> set[str]:
    """Scrape with Camoufox (Firefox C++ spoofing, stealth level 10)."""
    proxies: set[str] = set()
    page = await browser_context.new_page()
    try:
        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)  # Let JS render fully
        content = await page.content()
        proxies = await _extract_proxies_from_html(content)
    finally:
        await page.close()
    return proxies


async def _test_batch_and_save(proxies: set[str], proxy_dir: Path) -> set[str]:
    """Test proxies and immediately save alive ones to file."""
    alive: set[str] = set()
    proxies_list = list(proxies)

    # Use semaphore to limit concurrent tests (prevent resource exhaustion)
    semaphore = asyncio.Semaphore(30)  # Max 30 concurrent tests

    async def test_with_limit(proxy: str) -> tuple[str, bool]:
        async with semaphore:
            result = await _test_single_proxy(proxy, timeout=3.0)
            return proxy, result

    # Test in batches of 50 with semaphore limiting actual concurrency to 30
    for i in range(0, len(proxies_list), 50):
        batch = proxies_list[i : i + 50]
        results = await asyncio.gather(*[test_with_limit(p) for p in batch])
        for proxy, is_alive in results:
            if is_alive:
                alive.add(proxy)

    # Save alive immediately (append to file)
    if alive:
        existing_alive = read_proxies(proxy_dir / "alive_proxies.txt")
        new_alive = alive - existing_alive
        if new_alive:
            with open(proxy_dir / "alive_proxies.txt", "a") as f:
                for proxy in sorted(new_alive):
                    f.write(proxy + "\n")

    return alive


async def _run_scrape_job(job_id: str) -> None:
    """Background task - 10-TIER CASCADE for maximum proxy extraction."""
    job = _jobs[job_id]
    proxy_dir = DATA_DIR / "proxies"
    proxy_dir.mkdir(parents=True, exist_ok=True)

    all_proxies: set[str] = set()
    existing = read_proxies(proxy_dir / "aggregated.txt")

    # Lazy-init browser instances (only when needed)
    playwright_pw = None
    playwright_browser = None
    playwright_ctx = None
    patchright_pw = None
    patchright_browser = None
    patchright_ctx = None
    camoufox_instance = None
    camoufox_ctx = None

    for i, source in enumerate(PROXY_SOURCES):
        job["current_source"] = source["name"]
        proxies: set[str] = set()
        method_used = "httpx"

        try:
            # === TIER 1: httpx (async, stealth 2) ===
            proxies = await _scrape_with_httpx(source["url"])

            # === TIER 2: aiohttp (different TLS, stealth 3) ===
            if len(proxies) == 0:
                method_used = "aiohttp"
                with contextlib.suppress(Exception):
                    proxies = await _scrape_with_aiohttp(source["url"])

            # === TIER 3: requests (sync, Safari UA, stealth 2) ===
            if len(proxies) == 0:
                method_used = "requests"
                with contextlib.suppress(Exception):
                    proxies = await _scrape_with_requests(source["url"])

            # === TIER 4: curl_cffi (Chrome TLS impersonation, stealth 7) ===
            if len(proxies) == 0:
                method_used = "curl_cffi"
                with contextlib.suppress(Exception):
                    proxies = await _scrape_with_curl_cffi(source["url"])

            # === TIER 5: cloudscraper (Cloudflare bypass, stealth 6) ===
            if len(proxies) == 0:
                method_used = "cloudscraper"
                with contextlib.suppress(Exception):
                    proxies = await _scrape_with_cloudscraper(source["url"])

            # === TIER 6: Playwright standard (browser, stealth 5) ===
            if len(proxies) == 0:
                method_used = "playwright"
                if playwright_browser is None:
                    try:
                        from playwright.async_api import async_playwright

                        playwright_pw = await async_playwright().start()
                        playwright_browser = await playwright_pw.chromium.launch(headless=True)
                        playwright_ctx = await playwright_browser.new_context()
                    except ImportError:
                        playwright_ctx = None

                if playwright_ctx:
                    with contextlib.suppress(Exception):
                        proxies = await _scrape_with_playwright(source["url"], playwright_ctx)

            # === TIER 7: Patchright (undetected Chromium, stealth 9) ===
            if len(proxies) == 0:
                method_used = "patchright"
                if patchright_browser is None:
                    try:
                        from patchright.async_api import async_playwright

                        patchright_pw = await async_playwright().start()
                        patchright_browser = await patchright_pw.chromium.launch(
                            headless=True,
                            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                        )
                        patchright_ctx = await patchright_browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                            viewport={"width": 1920, "height": 1080},
                        )
                    except ImportError:
                        patchright_ctx = None

                if patchright_ctx:
                    with contextlib.suppress(Exception):
                        proxies = await _scrape_with_patchright(source["url"], patchright_ctx)

            # === TIER 8: nodriver (pure CDP, stealth 9) ===
            if len(proxies) == 0:
                method_used = "nodriver"
                with contextlib.suppress(Exception):
                    proxies = await _scrape_with_nodriver(source["url"])

            # === TIER 9: undetected-chromedriver (selenium, stealth 8) ===
            if len(proxies) == 0:
                method_used = "uc"
                with contextlib.suppress(Exception):
                    proxies = await _scrape_with_uc(source["url"])

            # === TIER 10: Camoufox (Firefox C++ spoofing, stealth 10) ===
            if len(proxies) == 0:
                method_used = "camoufox"
                if camoufox_instance is None:
                    try:
                        from camoufox.async_api import AsyncCamoufox

                        camoufox_instance = AsyncCamoufox(headless=True, humanize=True)
                        camoufox_browser = await camoufox_instance.__aenter__()
                        camoufox_ctx = await camoufox_browser.new_context()
                    except ImportError:
                        camoufox_ctx = None

                if camoufox_ctx is not None:
                    with contextlib.suppress(Exception):
                        proxies = await _scrape_with_camoufox(source["url"], camoufox_ctx)

            # Filter out garbage/private IPs
            proxies = filter_valid_proxies(proxies)
            new_proxies = proxies - existing - all_proxies
            all_proxies.update(proxies)

            # === INLINE TEST: Test new proxies from this source immediately ===
            alive_from_source: set[str] = set()
            if new_proxies:
                job["status"] = "testing"
                job["testing_source"] = source["name"]
                alive_from_source = await _test_batch_and_save(new_proxies, proxy_dir)
                job["alive_total"] = job.get("alive_total", 0) + len(alive_from_source)
                job["tested_total"] = job.get("tested_total", 0) + len(new_proxies)
                job["status"] = "scraping"

            job["results"].append(
                {
                    "name": source["name"],
                    "found": len(proxies),
                    "new": len(new_proxies),
                    "method": method_used,
                    "success": True,
                    "alive": len(alive_from_source),
                }
            )
        except Exception as e:
            job["results"].append(
                {
                    "name": source["name"],
                    "found": 0,
                    "new": 0,
                    "method": method_used,
                    "success": False,
                    "error": str(e)[:100],
                    "alive": 0,
                }
            )

        job["sources_done"] = i + 1
        job["proxies_found"] = len(all_proxies)

    # Cleanup all browser instances
    if playwright_browser:
        await playwright_browser.close()
    if playwright_pw:
        await playwright_pw.stop()
    if patchright_browser:
        await patchright_browser.close()
    if patchright_pw:
        await patchright_pw.stop()
    if camoufox_instance:
        await camoufox_instance.__aexit__(None, None, None)

    # Save new proxies to aggregated
    new_proxies = all_proxies - existing
    if new_proxies:
        with open(proxy_dir / "aggregated.txt", "a") as f:
            for proxy in sorted(new_proxies):
                f.write(proxy + "\n")

    job["new_added"] = len(new_proxies)
    # Testing happens inline (per-source) - alive_total already updated

    job["status"] = "completed"
    job["completed_at"] = datetime.now(UTC).isoformat()


@router.get("/scrape/active")
async def get_active_scrape_job() -> dict:
    """Get currently running scrape job, if any."""
    for job_id, job in _jobs.items():
        if job.get("type") == "scrape" and job.get("status") in ("running", "testing"):
            return {"job_id": job_id, **job}
    return {"job_id": None}


@router.get("/scrape/{job_id}")
async def get_scrape_status(job_id: str) -> dict:
    """Get scrape job status."""
    if job_id not in _jobs:
        return {"error": "Job not found"}
    return _jobs[job_id]


@router.post("/test/start")
async def start_test(
    source_file: str = "aggregated",
    browser_test: bool = False,
    concurrent: int = 100,
    timeout: float = 5.0,
) -> dict:
    """Start testing proxies from selected file. Returns job_id for tracking.

    Args:
        source_file: Which file to test - "aggregated" (all scraped) or "alive" (known working)
        browser_test: If True, use Playwright browser for testing.
                     This tests CONNECT tunnel support needed for HTTPS.
                     Slower but more accurate for browser automation use.
        concurrent: Number of concurrent tests (default 100, max 500)
        timeout: Timeout per proxy in seconds (default 5.0)
    """
    # Cleanup old jobs to prevent memory leak
    _cleanup_old_jobs()

    proxy_dir = DATA_DIR / "proxies"

    # Select source file
    if source_file == "alive":
        source_path = proxy_dir / "alive_proxies.txt"
        source_name = "alive_proxies.txt"
    else:
        source_path = proxy_dir / "aggregated.txt"
        source_name = "aggregated.txt"

    total = count_lines(source_path)

    if total == 0:
        return {"error": f"No proxies in {source_name}", "total": 0}

    job_id = str(uuid4())[:8]

    _jobs[job_id] = {
        "type": "test",
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "total": total,
        "tested": 0,
        "alive": 0,
        "dead": 0,
        "speed_per_sec": 0,
        "eta_seconds": 0,
        "browser_test": browser_test,
        "concurrent": min(concurrent, 500),
        "timeout": timeout,
        "source_file": source_file,
        "source_path": str(source_path),
    }

    asyncio.create_task(_run_test_job(job_id))

    return {"job_id": job_id, "total": total, "source": source_name, "browser_test": browser_test}


async def _test_single_proxy(proxy: str, timeout: float = 5.0) -> bool:
    """Test if a single proxy is alive using httpx with HTTPS (CONNECT tunnel)."""
    try:
        async with httpx.AsyncClient(
            proxy=f"http://{proxy}",
            timeout=timeout,
            verify=False,  # Skip SSL verification for speed
        ) as client:
            # Use HTTPS to test CONNECT tunnel support (needed for browsers)
            response = await client.get("https://httpbin.org/ip")
            return response.status_code == 200
    except Exception:
        return False


async def _test_proxy_browser(proxy: str, timeout: float = 10.0) -> bool:
    """Test proxy with Playwright browser (CONNECT tunnel support for HTTPS).

    Many proxies that work with httpx fail in browsers because browsers
    require CONNECT tunnel for HTTPS sites. This test verifies the proxy
    actually works for browser automation.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": f"http://{proxy}"},
            )
            context = await browser.new_context()
            page = await context.new_page()

            # Test HTTPS site to verify CONNECT tunnel works
            await page.goto("https://httpbin.org/ip", timeout=int(timeout * 1000))
            content = await page.content()
            await browser.close()

            # Verify we got a valid response
            return "origin" in content
    except Exception:
        return False


async def _run_test_job(job_id: str) -> None:
    """Background task to test proxies from selected source file."""
    job = _jobs[job_id]

    try:
        proxy_dir = DATA_DIR / "proxies"

        # Read from selected source file - resolve to absolute path
        source_path_str = job.get("source_path", str(proxy_dir / "aggregated.txt"))
        source_path = Path(source_path_str).resolve()

        # Validate file exists
        if not source_path.exists():
            job["status"] = "failed"
            job["error"] = f"Source file not found: {source_path.name}"
            return

        all_proxies = list(read_proxies(source_path))

        # Validate proxies were loaded
        if not all_proxies:
            job["status"] = "failed"
            job["error"] = f"No proxies found in {source_path.name}"
            return

        alive_proxies: set[str] = set()
        job["total"] = len(all_proxies)  # Update total for accurate progress

        # Use job settings with safe limits
        use_browser = job.get("browser_test", False)
        batch_size = min(job.get("concurrent", 50), 50)  # Cap at 50
        timeout = job.get("timeout", 5.0)

        # Semaphore to prevent resource exhaustion
        max_concurrent = 5 if use_browser else 30
        semaphore = asyncio.Semaphore(max_concurrent)

        # Browser tests are slower, use smaller batches
        if use_browser:
            batch_size = min(batch_size, 5)  # Max 5 concurrent browser instances

            async def test_func(p):
                async with semaphore:
                    return await _test_proxy_browser(p, timeout)
        else:
            async def test_func(p):
                async with semaphore:
                    return await _test_single_proxy(p, timeout)

        start_time = time.time()
        tested = 0

        for i in range(0, len(all_proxies), batch_size):
            if job.get("cancelled"):
                job["status"] = "cancelled"
                return

            batch = all_proxies[i : i + batch_size]
            results = await asyncio.gather(*[test_func(p) for p in batch])

            for proxy, is_alive in zip(batch, results):
                tested += 1
                if is_alive:
                    alive_proxies.add(proxy)
                    job["alive"] = len(alive_proxies)
                else:
                    job["dead"] = tested - len(alive_proxies)

            job["tested"] = tested

            # Calculate speed and ETA
            elapsed = time.time() - start_time
            if elapsed > 0:
                job["speed_per_sec"] = round(tested / elapsed, 1)
                remaining = len(all_proxies) - tested
                job["eta_seconds"] = (
                    int(remaining / job["speed_per_sec"]) if job["speed_per_sec"] > 0 else 0
                )

        # Save alive proxies - merge with existing to preserve previously working proxies
        existing_alive = read_proxies(proxy_dir / "alive_proxies.txt")
        all_alive = existing_alive | alive_proxies
        new_alive_count = len(alive_proxies - existing_alive)

        with open(proxy_dir / "alive_proxies.txt", "w") as f:
            for proxy in sorted(all_alive):
                f.write(proxy + "\n")

        job["alive_added"] = new_alive_count
        job["total_alive"] = len(all_alive)

        # Save tested count for stats tracking
        tested_file = proxy_dir / ".tested_count"
        tested_file.write_text(str(job.get("tested", len(all_proxies))))

        job["status"] = "completed"
        job["completed_at"] = datetime.now(UTC).isoformat()

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)


@router.get("/test/{job_id}")
async def get_test_status(job_id: str) -> dict:
    """Get test job status."""
    if job_id not in _jobs:
        return {"error": "Job not found"}
    return _jobs[job_id]


@router.post("/test/{job_id}/stop")
async def stop_test(job_id: str) -> dict:
    """Stop a running test job."""
    if job_id not in _jobs:
        return {"error": "Job not found"}

    _jobs[job_id]["cancelled"] = True
    return {"status": "stopping"}


@router.post("/clear-dead")
async def clear_dead_proxies(source_file: str = "alive") -> dict:
    """Test proxies in a file and remove dead ones.

    Args:
        source_file: "alive" for alive_proxies.txt, "aggregated" for aggregated.txt
    """
    proxy_dir = DATA_DIR / "proxies"

    # Select source file
    if source_file == "alive":
        file_path = proxy_dir / "alive_proxies.txt"
    else:
        file_path = proxy_dir / "aggregated.txt"

    if not file_path.exists():
        return {
            "error": f"File {file_path.name} not found",
            "tested": 0,
            "removed": 0,
            "remaining": 0,
        }

    all_proxies = list(read_proxies(file_path))
    if not all_proxies:
        return {
            "error": f"No proxies in {file_path.name}",
            "tested": 0,
            "removed": 0,
            "remaining": 0,
        }

    # Test all proxies with rate limiting
    alive_proxies: set[str] = set()
    batch_size = 50
    semaphore = asyncio.Semaphore(30)  # Max 30 concurrent

    async def test_with_limit(proxy: str) -> tuple[str, bool]:
        async with semaphore:
            return proxy, await _test_single_proxy(proxy)

    for i in range(0, len(all_proxies), batch_size):
        batch = all_proxies[i : i + batch_size]
        results = await asyncio.gather(*[test_with_limit(p) for p in batch])

        for proxy, is_alive in results:
            if is_alive:
                alive_proxies.add(proxy)

    # Save only alive proxies back to the file
    with open(file_path, "w") as f:
        for proxy in sorted(alive_proxies):
            f.write(proxy + "\n")

    removed = len(all_proxies) - len(alive_proxies)

    return {
        "tested": len(all_proxies),
        "removed": removed,
        "remaining": len(alive_proxies),
        "file": file_path.name,
    }


@router.post("/clean")
async def clean_dead_proxies() -> dict:
    """Remove dead proxies from main files."""
    proxy_dir = DATA_DIR / "proxies"

    alive_proxies = read_proxies(proxy_dir / "alive_proxies.txt")
    alive_proxies |= read_proxies(proxy_dir / "working_http.txt")

    if not alive_proxies:
        return {"error": "No alive proxies found to filter against", "removed": 0}

    removed_total = 0
    files_cleaned = []

    for file_name in ["aggregated.txt", "massive.txt", "sample.txt"]:
        file_path = proxy_dir / file_name
        if not file_path.exists():
            continue

        original = read_proxies(file_path)
        cleaned = original & alive_proxies
        removed = len(original) - len(cleaned)

        if removed > 0:
            with open(file_path, "w") as f:
                f.write("\n".join(sorted(cleaned)) + "\n" if cleaned else "")
            removed_total += removed
            files_cleaned.append({"file": file_name, "removed": removed, "remaining": len(cleaned)})

    return {
        "success": True,
        "removed": removed_total,
        "files_cleaned": files_cleaned,
        "alive_count": len(alive_proxies),
    }


class ImportRequest(BaseModel):
    proxies: list[str]


# ============ PREMIUM PROVIDER ENDPOINTS ============

from typing import Literal

# Provider registry and credential storage
_configured_providers: dict[str, Any] = {}
_credential_store = None


def _get_credential_store():
    """Get or create credential store (lazy init)."""
    global _credential_store
    if _credential_store is None:
        from ghoststorm.core.config.credentials import CredentialStore

        _credential_store = CredentialStore(DATA_DIR / "config")
    return _credential_store


def _create_provider(provider_name: str, config: dict[str, Any]):
    """Create a provider instance from config."""
    if provider_name == "decodo":
        from ghoststorm.plugins.proxies.decodo_provider import DecodoProvider

        return DecodoProvider(
            username=config["username"],
            password=config["password"],
            country=config.get("country"),
            city=config.get("city"),
            session_type=config.get("session_type", "rotating"),
        )
    elif provider_name == "brightdata":
        from ghoststorm.plugins.proxies.brightdata_provider import BrightDataProvider

        return BrightDataProvider(
            customer_id=config["customer_id"],
            zone=config.get("zone", "residential"),
            password=config["password"],
            country=config.get("country"),
            city=config.get("city"),
            session_type=config.get("session_type", "rotating"),
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


class ProviderConfig(BaseModel):
    """Configuration for a premium proxy provider."""

    provider: Literal["decodo", "brightdata", "oxylabs", "iproyal", "webshare"]
    # Common fields
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    # Bright Data specific
    customer_id: str | None = None
    zone: str | None = None
    # Targeting
    country: str | None = None
    city: str | None = None
    state: str | None = None
    session_type: Literal["rotating", "sticky"] = "rotating"
    session_duration: int = 10


@router.get("/providers")
async def list_providers() -> dict:
    """List all configured premium providers."""
    store = _get_credential_store()
    providers = []

    for name in ["decodo", "brightdata", "oxylabs", "iproyal", "webshare"]:
        config = store.get(name)
        providers.append(
            {
                "name": name,
                "configured": config is not None,
                "country": config.get("country") if config else None,
                "session_type": config.get("session_type", "rotating") if config else None,
            }
        )

    return {"providers": providers}


@router.get("/providers/{provider_name}")
async def get_provider(provider_name: str) -> dict:
    """Get configuration for a specific provider."""
    store = _get_credential_store()
    config = store.get(provider_name)

    if not config:
        return {"configured": False, "provider": provider_name}

    # Don't expose full password
    safe_config = dict(config)
    if safe_config.get("password"):
        safe_config["password"] = "********"
    if safe_config.get("api_key"):
        safe_config["api_key"] = "********"

    return {"configured": True, "provider": provider_name, "config": safe_config}


@router.post("/providers/configure")
async def configure_provider(config: ProviderConfig) -> dict:
    """Configure a premium proxy provider."""
    store = _get_credential_store()

    # Validate required fields based on provider
    if config.provider == "decodo":
        if not config.username or not config.password:
            return {"success": False, "error": "Decodo requires username and password"}
    elif config.provider == "brightdata":
        if not config.customer_id or not config.password:
            return {"success": False, "error": "Bright Data requires customer_id and password"}
    elif config.provider == "webshare":
        if not config.api_key:
            return {"success": False, "error": "Webshare requires api_key"}
    elif config.provider in ["oxylabs", "iproyal"]:
        if not config.username or not config.password:
            return {"success": False, "error": f"{config.provider} requires username and password"}

    # Save configuration
    cred_data = {
        "provider": config.provider,
        "username": config.username,
        "password": config.password,
        "api_key": config.api_key,
        "customer_id": config.customer_id,
        "zone": config.zone,
        "country": config.country,
        "city": config.city,
        "state": config.state,
        "session_type": config.session_type,
        "session_duration": config.session_duration,
    }

    store.save(config.provider, cred_data)

    return {"success": True, "provider": config.provider, "message": "Provider configured"}


@router.post("/providers/{provider_name}/test")
async def test_provider(provider_name: str) -> dict:
    """Test a configured provider connection."""
    # Special case for Tor
    if provider_name == "tor":
        return await test_tor_connection()

    store = _get_credential_store()
    config = store.get(provider_name)

    if not config:
        return {"success": False, "error": f"Provider {provider_name} is not configured"}

    try:
        provider = _create_provider(provider_name, config)
        await provider.initialize()
        result = await provider.test_connection()
        await provider.close()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


class TorTestRequest(BaseModel):
    """Tor connection test request."""

    port: int = 9050
    host: str = "127.0.0.1"


@router.post("/providers/tor/test")
async def test_tor_connection(request: TorTestRequest | None = None) -> dict:
    """Test Tor SOCKS5 proxy connection."""
    host = request.host if request else "127.0.0.1"
    port = request.port if request else 9050

    try:
        # Try to connect to Tor SOCKS5 port
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=5.0,
        )

        # SOCKS5 handshake (no auth)
        writer.write(b"\x05\x01\x00")
        await writer.drain()

        response = await reader.read(2)
        writer.close()
        await writer.wait_closed()

        if response == b"\x05\x00":
            # Try to get exit IP through Tor
            try:
                import aiohttp
                import aiohttp_socks

                connector = aiohttp_socks.ProxyConnector.from_url(f"socks5://{host}:{port}")
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(
                        "https://check.torproject.org/api/ip",
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return {
                                "connected": True,
                                "ip": data.get("IP", "Unknown"),
                                "is_tor": data.get("IsTor", False),
                                "host": host,
                                "port": port,
                            }
            except Exception:
                pass

            return {
                "connected": True,
                "ip": "Unknown (could not verify)",
                "host": host,
                "port": port,
            }

        return {"connected": False, "error": "Invalid SOCKS5 response"}

    except TimeoutError:
        return {
            "connected": False,
            "error": f"Connection timeout - is Tor running on {host}:{port}?",
        }
    except ConnectionRefusedError:
        return {
            "connected": False,
            "error": f"Connection refused - Tor daemon not running on {host}:{port}",
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.delete("/providers/{provider_name}")
async def remove_provider(provider_name: str) -> dict:
    """Remove a configured provider."""
    store = _get_credential_store()

    if not store.is_configured(provider_name):
        return {"success": False, "error": f"Provider {provider_name} is not configured"}

    store.remove(provider_name)

    # Remove from active instances
    _configured_providers.pop(provider_name, None)

    return {"success": True, "provider": provider_name, "message": "Provider removed"}


@router.post("/import")
async def import_proxies(request: ImportRequest) -> dict:
    """Import proxies from a list."""
    proxy_dir = DATA_DIR / "proxies"
    proxy_dir.mkdir(parents=True, exist_ok=True)

    valid_proxies: set[str] = set()
    for line in request.proxies:
        match = PROXY_PATTERN.search(line)
        if match:
            valid_proxies.add(f"{match.group(1)}:{match.group(2)}")

    if not valid_proxies:
        return {"error": "No valid proxies found", "added": 0, "duplicates": 0}

    existing = read_proxies(proxy_dir / "aggregated.txt")
    new_proxies = valid_proxies - existing

    if new_proxies:
        with open(proxy_dir / "aggregated.txt", "a") as f:
            for proxy in sorted(new_proxies):
                f.write(proxy + "\n")

    return {
        "added": len(new_proxies),
        "duplicates": len(valid_proxies) - len(new_proxies),
    }


@router.get("/export")
async def export_proxies() -> dict:
    """Export all alive proxies."""
    proxy_dir = DATA_DIR / "proxies"

    alive = read_proxies(proxy_dir / "alive_proxies.txt")
    alive |= read_proxies(proxy_dir / "working_http.txt")

    if alive:
        return {"proxies": sorted(alive)}

    all_proxies = read_proxies(proxy_dir / "aggregated.txt")
    if all_proxies:
        return {"proxies": sorted(all_proxies)}

    return {"error": "No proxies to export", "proxies": []}
