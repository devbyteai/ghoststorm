"""High-Volume TikTok View Runner.

Production-grade runner for 1000+ concurrent sessions running for hours.

Usage:
    python -m ghoststorm.runners.high_volume_runner --target-url "https://tiktok.com/@user/video/123" --concurrent 500 --duration 3600

Features:
    - 1000+ concurrent browser contexts
    - Automatic browser/context recycling
    - Memory-aware resource management
    - Real-time stats dashboard
    - Proxy rotation with health checks
    - Graceful shutdown handling
"""

from __future__ import annotations

import asyncio
import gc
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from rich.console import Console
from rich.live import Live
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ghoststorm.core.engine.browser_pool import HighVolumeExecutor

logger = structlog.get_logger(__name__)
console = Console()


@dataclass
class RunnerStats:
    """Statistics for the runner."""

    start_time: datetime = field(default_factory=datetime.now)
    views_attempted: int = 0
    views_successful: int = 0
    views_failed: int = 0
    bytes_downloaded: int = 0
    proxies_used: set = field(default_factory=set)
    errors: dict[str, int] = field(default_factory=dict)

    # Per-minute tracking
    views_per_minute: list[int] = field(default_factory=list)
    _last_minute_views: int = 0
    _last_minute_time: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.views_attempted == 0:
            return 0.0
        return (self.views_successful / self.views_attempted) * 100

    @property
    def elapsed_seconds(self) -> float:
        """Elapsed time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def views_per_hour(self) -> float:
        """Calculate views per hour rate."""
        if self.elapsed_seconds < 1:
            return 0.0
        return (self.views_successful / self.elapsed_seconds) * 3600

    def track_minute(self) -> None:
        """Track views per minute."""
        now = time.time()
        if now - self._last_minute_time >= 60:
            minute_views = self.views_successful - self._last_minute_views
            self.views_per_minute.append(minute_views)
            self._last_minute_views = self.views_successful
            self._last_minute_time = now

    def record_error(self, error_type: str) -> None:
        """Record an error type."""
        self.errors[error_type] = self.errors.get(error_type, 0) + 1


class HighVolumeRunner:
    """
    Production runner for high-volume view generation.

    Supports:
    - 1000+ concurrent sessions
    - Hours of continuous operation
    - Real-time monitoring
    - Graceful resource management
    """

    def __init__(
        self,
        target_url: str,
        concurrent_limit: int = 100,
        max_browsers: int = 10,
        max_contexts_per_browser: int = 20,
        watch_duration: float = 5.0,
        memory_limit_mb: int = 0,
        proxy_list: list[str] | None = None,
        headless: bool = True,
    ) -> None:
        self.target_url = target_url
        self.concurrent_limit = concurrent_limit
        self.max_browsers = max_browsers
        self.max_contexts_per_browser = max_contexts_per_browser
        self.watch_duration = watch_duration
        self.memory_limit_mb = memory_limit_mb
        self.proxy_list = proxy_list or []
        self.headless = headless

        self._stats = RunnerStats()
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._executor: HighVolumeExecutor | None = None
        self._proxy_index = 0
        self._proxy_lock = asyncio.Lock()

    @property
    def stats(self) -> RunnerStats:
        """Get current stats."""
        return self._stats

    async def _browser_factory(self) -> Any:
        """Create a new browser instance."""
        from patchright.async_api import async_playwright

        playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-web-security",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-translate",
            "--metrics-recording-only",
            "--mute-audio",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
        ]

        browser = await playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )

        # Wrap browser to include playwright reference for cleanup
        browser._playwright = playwright
        return browser

    async def _get_next_proxy(self) -> str | None:
        """Get next proxy from rotation."""
        if not self.proxy_list:
            return None

        async with self._proxy_lock:
            proxy = self.proxy_list[self._proxy_index]
            self._proxy_index = (self._proxy_index + 1) % len(self.proxy_list)
            self._stats.proxies_used.add(proxy)
            return proxy

    async def _watch_video(self, page: Any) -> bool:
        """
        Watch a TikTok video for the configured duration.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Navigate to video
            await page.goto(
                self.target_url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            # Wait for video to load
            await asyncio.sleep(1)

            # Try to click play if needed
            play_selectors = [
                '[data-e2e="video-play-icon"]',
                'button[aria-label*="Play"]',
                '[class*="play-icon"]',
            ]

            for selector in play_selectors:
                try:
                    btn = page.locator(selector)
                    if await btn.count() > 0 and await btn.first.is_visible():
                        await btn.first.click()
                        await asyncio.sleep(0.3)
                        break
                except Exception:
                    continue

            # Watch video for configured duration
            await asyncio.sleep(self.watch_duration)

            return True

        except TimeoutError:
            self._stats.record_error("timeout")
            return False
        except Exception as e:
            error_type = type(e).__name__
            self._stats.record_error(error_type)
            logger.debug(f"View failed: {error_type}: {e}")
            return False

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes views."""
        while self._running and not self._shutdown_event.is_set():
            try:
                self._stats.views_attempted += 1

                # Execute view with pooled context
                success = await self._executor.execute(self._watch_video)

                if success:
                    self._stats.views_successful += 1
                else:
                    self._stats.views_failed += 1

                # Track per-minute stats
                self._stats.track_minute()

                # Randomized delay between views to prevent pattern detection
                await asyncio.sleep(random.uniform(0.05, 0.15))

            except Exception as e:
                self._stats.views_failed += 1
                self._stats.record_error(type(e).__name__)
                await asyncio.sleep(random.uniform(0.5, 2.0))  # Randomized backoff

    def _create_stats_table(self) -> Table:
        """Create rich table with current stats."""
        table = Table(title="High-Volume Runner Stats", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        elapsed = str(timedelta(seconds=int(self._stats.elapsed_seconds)))

        table.add_row("Status", "[bold green]RUNNING[/]" if self._running else "[bold red]STOPPED[/]")
        table.add_row("Elapsed Time", elapsed)
        table.add_row("", "")
        table.add_row("[bold]Views[/]", "")
        table.add_row("  Attempted", f"{self._stats.views_attempted:,}")
        table.add_row("  Successful", f"[green]{self._stats.views_successful:,}[/]")
        table.add_row("  Failed", f"[red]{self._stats.views_failed:,}[/]")
        table.add_row("  Success Rate", f"{self._stats.success_rate:.1f}%")
        table.add_row("", "")
        table.add_row("[bold]Performance[/]", "")
        table.add_row("  Views/Hour", f"[bold]{self._stats.views_per_hour:,.0f}[/]")
        table.add_row("  Concurrent", str(self.concurrent_limit))
        table.add_row("  Browsers", str(self.max_browsers))
        table.add_row("  Contexts/Browser", str(self.max_contexts_per_browser))
        table.add_row("", "")
        table.add_row("[bold]Resources[/]", "")

        if self._executor:
            exec_stats = self._executor.stats
            table.add_row("  Active Browsers", str(exec_stats["browser_pool"]["active_browsers"]))
            table.add_row("  Active Contexts", str(exec_stats["context_pool"]["active_contexts"]))
            table.add_row("  Memory (MB)", f"{exec_stats['browser_pool']['memory_mb']:.0f}")

        table.add_row("  Proxies Used", str(len(self._stats.proxies_used)))

        if self._stats.errors:
            table.add_row("", "")
            table.add_row("[bold]Top Errors[/]", "")
            sorted_errors = sorted(self._stats.errors.items(), key=lambda x: x[1], reverse=True)[:5]
            for error_type, count in sorted_errors:
                table.add_row(f"  {error_type}", str(count))

        return table

    async def _stats_display(self) -> None:
        """Display live stats."""
        with Live(self._create_stats_table(), refresh_per_second=2, console=console) as live:
            while self._running and not self._shutdown_event.is_set():
                live.update(self._create_stats_table())
                await asyncio.sleep(0.5)

    async def run(self, duration_seconds: float | None = None) -> RunnerStats:
        """
        Run the high-volume view generator.

        Args:
            duration_seconds: How long to run (None = indefinitely until stopped)

        Returns:
            Final statistics
        """
        self._running = True
        self._shutdown_event.clear()

        console.print("\n[bold cyan]Starting High-Volume Runner[/]")
        console.print(f"  Target: {self.target_url}")
        console.print(f"  Concurrent: {self.concurrent_limit}")
        console.print(f"  Browsers: {self.max_browsers}")
        console.print(f"  Watch Duration: {self.watch_duration}s")
        console.print(f"  Proxies: {len(self.proxy_list)}")
        console.print()

        # Initialize executor
        self._executor = HighVolumeExecutor(
            browser_factory=self._browser_factory,
            max_browsers=self.max_browsers,
            max_contexts_per_browser=self.max_contexts_per_browser,
            max_concurrent=self.concurrent_limit,
            memory_limit_mb=self.memory_limit_mb,
        )

        try:
            await self._executor.start()

            # Start workers
            workers = [
                asyncio.create_task(self._worker(i))
                for i in range(self.concurrent_limit)
            ]

            # Start stats display
            stats_task = asyncio.create_task(self._stats_display())

            # Wait for duration or shutdown
            if duration_seconds:
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=duration_seconds,
                    )
                except TimeoutError:
                    pass  # Duration elapsed normally

            else:
                await self._shutdown_event.wait()

        finally:
            # Stop everything
            self._running = False
            self._shutdown_event.set()

            # Cancel workers
            for worker in workers:
                worker.cancel()

            stats_task.cancel()

            # Stop executor
            if self._executor:
                await self._executor.stop()

            gc.collect()

        return self._stats

    def stop(self) -> None:
        """Signal runner to stop."""
        self._running = False
        self._shutdown_event.set()


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="High-Volume TikTok View Runner")
    parser.add_argument(
        "--target-url",
        required=True,
        help="TikTok video URL to target",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=100,
        help="Number of concurrent sessions (default: 100)",
    )
    parser.add_argument(
        "--browsers",
        type=int,
        default=10,
        help="Number of browser instances (default: 10)",
    )
    parser.add_argument(
        "--contexts-per-browser",
        type=int,
        default=20,
        help="Contexts per browser (default: 20)",
    )
    parser.add_argument(
        "--watch-duration",
        type=float,
        default=5.0,
        help="Seconds to watch each video (default: 5.0)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Total runtime in seconds (default: run until stopped)",
    )
    parser.add_argument(
        "--memory-limit",
        type=int,
        default=0,
        help="Memory limit in MB (0 = no limit)",
    )
    parser.add_argument(
        "--proxy-file",
        type=str,
        default=None,
        help="File with proxy list (one per line)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browsers in headed mode (for debugging)",
    )

    args = parser.parse_args()

    # Load proxies
    proxies = []
    if args.proxy_file and Path(args.proxy_file).exists():
        with open(args.proxy_file) as f:
            proxies = [line.strip() for line in f if line.strip()]
        console.print(f"[green]Loaded {len(proxies)} proxies[/]")

    # Create runner
    runner = HighVolumeRunner(
        target_url=args.target_url,
        concurrent_limit=args.concurrent,
        max_browsers=args.browsers,
        max_contexts_per_browser=args.contexts_per_browser,
        watch_duration=args.watch_duration,
        memory_limit_mb=args.memory_limit,
        proxy_list=proxies,
        headless=not args.headed,
    )

    # Handle shutdown signals
    def signal_handler(sig, frame):
        console.print("\n[yellow]Shutdown signal received, stopping...[/]")
        runner.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run
    try:
        stats = await runner.run(duration_seconds=args.duration)

        # Final report
        console.print("\n" + "=" * 60)
        console.print("[bold cyan]FINAL REPORT[/]")
        console.print("=" * 60)
        console.print(f"Total Runtime: {timedelta(seconds=int(stats.elapsed_seconds))}")
        console.print(f"Views Attempted: {stats.views_attempted:,}")
        console.print(f"Views Successful: [green]{stats.views_successful:,}[/]")
        console.print(f"Views Failed: [red]{stats.views_failed:,}[/]")
        console.print(f"Success Rate: {stats.success_rate:.1f}%")
        console.print(f"Views/Hour: [bold]{stats.views_per_hour:,.0f}[/]")
        console.print(f"Proxies Used: {len(stats.proxies_used)}")

        if stats.errors:
            console.print("\nErrors:")
            for error_type, count in sorted(stats.errors.items(), key=lambda x: x[1], reverse=True):
                console.print(f"  {error_type}: {count}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


if __name__ == "__main__":
    asyncio.run(main())
