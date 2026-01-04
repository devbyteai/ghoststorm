"""DEXTools trending campaign orchestrator.

Coordinates multiple visitors over time for DEXTools trending push.
"""

from __future__ import annotations

import asyncio
import contextlib
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from ghoststorm.plugins.automation.dextools import (
    DEXToolsAutomation,
    DEXToolsConfig,
    VisitorBehavior,
    VisitResult,
)

if TYPE_CHECKING:
    from ghoststorm.core.interfaces.proxy import IProxyProvider
    from ghoststorm.core.models.proxy import Proxy


class CampaignStatus(Enum):
    """Campaign execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class VisitorResult:
    """Result of a single visitor in the campaign."""

    visitor_id: int
    visit_result: VisitResult
    proxy_used: Proxy | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    @property
    def duration_s(self) -> float:
        """Get duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


@dataclass
class CampaignStats:
    """Real-time campaign statistics."""

    total_visitors: int = 0
    completed_visitors: int = 0
    failed_visitors: int = 0
    in_progress: int = 0

    # Behavior distribution
    passive_count: int = 0
    light_count: int = 0
    engaged_count: int = 0

    # Engagement metrics
    total_social_clicks: int = 0
    total_tab_clicks: int = 0
    total_dwell_time_s: float = 0.0

    # Timing
    started_at: datetime | None = None
    last_visit_at: datetime | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.completed_visitors + self.failed_visitors == 0:
            return 0.0
        return self.completed_visitors / (self.completed_visitors + self.failed_visitors)

    @property
    def avg_dwell_time_s(self) -> float:
        """Average dwell time per visitor."""
        if self.completed_visitors == 0:
            return 0.0
        return self.total_dwell_time_s / self.completed_visitors

    @property
    def elapsed_s(self) -> float:
        """Time elapsed since campaign start."""
        if not self.started_at:
            return 0.0
        return (datetime.now() - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "total_visitors": self.total_visitors,
            "completed_visitors": self.completed_visitors,
            "failed_visitors": self.failed_visitors,
            "in_progress": self.in_progress,
            "success_rate": round(self.success_rate * 100, 1),
            "behavior_distribution": {
                "passive": self.passive_count,
                "light": self.light_count,
                "engaged": self.engaged_count,
            },
            "engagement": {
                "social_clicks": self.total_social_clicks,
                "tab_clicks": self.total_tab_clicks,
                "avg_dwell_time_s": round(self.avg_dwell_time_s, 1),
            },
            "timing": {
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "last_visit_at": self.last_visit_at.isoformat() if self.last_visit_at else None,
                "elapsed_s": round(self.elapsed_s, 1),
            },
        }


@dataclass
class CampaignConfig:
    """Configuration for a DEXTools trending campaign."""

    # Target
    pair_url: str

    # Scale
    num_visitors: int = 100
    duration_hours: float = 24.0

    # Concurrency
    max_concurrent: int = 5
    min_delay_between_visitors_s: float = 10.0
    max_delay_between_visitors_s: float = 60.0

    # Distribution
    distribution_mode: str = "natural"  # natural, even, burst

    # Behavior (passed to DEXToolsConfig)
    behavior_mode: str = "realistic"
    dwell_time_min: float = 30.0
    dwell_time_max: float = 120.0

    # Browser settings
    headless: bool = True
    browser_engine: str = "patchright"  # playwright, patchright, camoufox

    # Retry settings
    max_retries_per_visitor: int = 2
    retry_delay_s: float = 30.0


@dataclass
class CampaignResult:
    """Final result of a campaign run."""

    campaign_id: str
    status: CampaignStatus
    config: CampaignConfig
    stats: CampaignStats
    visitors: list[VisitorResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def duration_s(self) -> float:
        """Total campaign duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "campaign_id": self.campaign_id,
            "status": self.status.value,
            "stats": self.stats.to_dict(),
            "duration_s": round(self.duration_s, 1),
            "errors": self.errors[:10],  # Limit errors in response
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class DEXToolsTrendingCampaign:
    """Orchestrate multiple visitors for DEXTools trending push.

    Distributes visits naturally over time using different proxies
    and varying behavior patterns to simulate organic traffic.

    Usage:
        ```python
        campaign = DEXToolsTrendingCampaign(
            config=CampaignConfig(
                pair_url="https://www.dextools.io/app/ether/pair-explorer/0x...",
                num_visitors=100,
                duration_hours=24.0,
            ),
            proxy_provider=rotating_proxy_provider,
            browser_launcher=browser_launcher,
        )

        # Start campaign (runs in background)
        await campaign.start()

        # Check status
        stats = campaign.get_stats()

        # Stop early if needed
        await campaign.stop()

        # Get final results
        result = campaign.get_result()
        ```
    """

    def __init__(
        self,
        config: CampaignConfig,
        proxy_provider: IProxyProvider | None = None,
        browser_launcher: Any = None,  # BrowserLauncher
    ) -> None:
        self.config = config
        self.proxy_provider = proxy_provider
        self.browser_launcher = browser_launcher

        # Generate campaign ID
        import uuid

        self.campaign_id = str(uuid.uuid4())[:8]

        # State
        self._status = CampaignStatus.PENDING
        self._stats = CampaignStats(total_visitors=config.num_visitors)
        self._visitors: list[VisitorResult] = []
        self._errors: list[str] = []

        # Control
        self._started_at: datetime | None = None
        self._completed_at: datetime | None = None
        self._cancel_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        self._running_tasks: set[asyncio.Task[Any]] = set()
        self._semaphore = asyncio.Semaphore(config.max_concurrent)

        # Progress callback
        self._on_progress: Any = None

    @property
    def status(self) -> CampaignStatus:
        """Get current campaign status."""
        return self._status

    def get_stats(self) -> CampaignStats:
        """Get current campaign statistics."""
        return self._stats

    def get_result(self) -> CampaignResult:
        """Get campaign result."""
        return CampaignResult(
            campaign_id=self.campaign_id,
            status=self._status,
            config=self.config,
            stats=self._stats,
            visitors=self._visitors,
            errors=self._errors,
            started_at=self._started_at,
            completed_at=self._completed_at,
        )

    def on_progress(self, callback: Any) -> None:
        """Set progress callback.

        Callback receives (stats: CampaignStats) on each visitor completion.
        """
        self._on_progress = callback

    async def start(self) -> None:
        """Start the campaign."""
        if self._status == CampaignStatus.RUNNING:
            return

        self._status = CampaignStatus.RUNNING
        self._started_at = datetime.now()
        self._stats.started_at = self._started_at
        self._cancel_event.clear()

        # Calculate visit schedule
        schedule = self._create_visit_schedule()

        # Run visitors
        for visitor_id, delay in schedule:
            if self._cancel_event.is_set():
                break

            # Wait for pause to be cleared
            await self._pause_event.wait()

            # Wait for delay
            if delay > 0:
                try:
                    await asyncio.wait_for(self._cancel_event.wait(), timeout=delay)
                    break  # Cancelled during wait
                except TimeoutError:
                    pass  # Normal - delay completed

            # Launch visitor task
            async with self._semaphore:
                if self._cancel_event.is_set():
                    break

                task = asyncio.create_task(self._run_visitor(visitor_id))
                self._running_tasks.add(task)
                task.add_done_callback(self._running_tasks.discard)

        # Wait for all visitors to complete
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)

        # Finalize
        self._completed_at = datetime.now()
        if self._cancel_event.is_set():
            self._status = CampaignStatus.CANCELLED
        elif self._stats.failed_visitors > self._stats.completed_visitors:
            self._status = CampaignStatus.FAILED
        else:
            self._status = CampaignStatus.COMPLETED

    async def stop(self) -> None:
        """Stop the campaign."""
        self._cancel_event.set()
        self._pause_event.set()  # Unpause to allow clean exit

        # Cancel running tasks
        for task in self._running_tasks:
            task.cancel()

        self._status = CampaignStatus.CANCELLED
        self._completed_at = datetime.now()

    async def pause(self) -> None:
        """Pause the campaign."""
        self._pause_event.clear()
        self._status = CampaignStatus.PAUSED

    async def resume(self) -> None:
        """Resume a paused campaign."""
        self._pause_event.set()
        self._status = CampaignStatus.RUNNING

    def _create_visit_schedule(self) -> list[tuple[int, float]]:
        """Create schedule of (visitor_id, delay_seconds) tuples.

        Distribution modes:
        - natural: Gaussian-like distribution around peak times
        - even: Evenly distributed over duration
        - burst: Bursts of activity with quiet periods
        """
        total_seconds = self.config.duration_hours * 3600
        num_visitors = self.config.num_visitors
        schedule: list[tuple[int, float]] = []

        if self.config.distribution_mode == "even":
            # Even distribution
            interval = total_seconds / num_visitors
            for i in range(num_visitors):
                delay = i * interval
                # Add some randomness
                delay += random.uniform(-interval * 0.2, interval * 0.2)
                schedule.append((i, max(0, delay)))

        elif self.config.distribution_mode == "burst":
            # Burst distribution - clusters of visits
            num_bursts = max(1, num_visitors // 10)
            visitors_per_burst = num_visitors // num_bursts

            burst_starts = sorted(
                [random.uniform(0, total_seconds * 0.9) for _ in range(num_bursts)]
            )

            visitor_id = 0
            for burst_start in burst_starts:
                for _j in range(visitors_per_burst):
                    if visitor_id >= num_visitors:
                        break
                    # Visitors within burst are close together
                    delay = burst_start + random.uniform(0, 300)  # 5 min burst window
                    schedule.append((visitor_id, delay))
                    visitor_id += 1

            # Handle remaining visitors
            while visitor_id < num_visitors:
                delay = random.uniform(0, total_seconds)
                schedule.append((visitor_id, delay))
                visitor_id += 1

        else:  # natural (default)
            # Natural distribution - more activity during "peak" times
            # Simulate a day with peaks in morning and evening
            for i in range(num_visitors):
                # Use exponential distribution for more natural gaps
                base_delay = i * (total_seconds / num_visitors)

                # Add variance
                variance = random.expovariate(1 / (total_seconds / num_visitors / 2))
                delay = base_delay + random.choice([-1, 1]) * variance

                # Clamp to valid range
                delay = max(0, min(total_seconds, delay))

                schedule.append((i, delay))

        # Sort by delay
        schedule.sort(key=lambda x: x[1])

        # Convert absolute times to relative delays
        result: list[tuple[int, float]] = []
        prev_time = 0.0
        for visitor_id, abs_time in schedule:
            delay = abs_time - prev_time
            # Ensure minimum delay between visitors
            delay = max(
                delay,
                random.uniform(
                    self.config.min_delay_between_visitors_s,
                    self.config.max_delay_between_visitors_s,
                ),
            )
            result.append((visitor_id, delay))
            prev_time = abs_time

        return result

    async def _run_visitor(self, visitor_id: int) -> None:
        """Run a single visitor."""
        self._stats.in_progress += 1

        result = VisitorResult(
            visitor_id=visitor_id,
            visit_result=VisitResult(
                success=False,
                url=self.config.pair_url,
                behavior=VisitorBehavior.PASSIVE,
                dwell_time_s=0.0,
            ),
            started_at=datetime.now(),
        )

        try:
            # Get proxy
            proxy = None
            if self.proxy_provider:
                try:
                    proxy = await self.proxy_provider.get_proxy()
                    result.proxy_used = proxy
                except Exception as e:
                    self._errors.append(f"Visitor {visitor_id}: Proxy error: {e}")

            # Create automation config
            dex_config = DEXToolsConfig(
                pair_url=self.config.pair_url,
                behavior_mode=self.config.behavior_mode,
                dwell_time_min=self.config.dwell_time_min,
                dwell_time_max=self.config.dwell_time_max,
            )
            automation = DEXToolsAutomation(dex_config)

            # Run visit with browser
            visit_result = await self._execute_visit(automation, proxy)
            result.visit_result = visit_result

            if visit_result.success:
                self._stats.completed_visitors += 1

                # Update behavior distribution
                if visit_result.behavior == VisitorBehavior.PASSIVE:
                    self._stats.passive_count += 1
                elif visit_result.behavior == VisitorBehavior.LIGHT:
                    self._stats.light_count += 1
                else:
                    self._stats.engaged_count += 1

                # Update engagement metrics
                self._stats.total_social_clicks += visit_result.social_clicks
                self._stats.total_tab_clicks += visit_result.tab_clicks
                self._stats.total_dwell_time_s += visit_result.dwell_time_s

                # Mark proxy success
                if proxy and self.proxy_provider:
                    await self.proxy_provider.mark_success(proxy, 0)
            else:
                self._stats.failed_visitors += 1
                result.error = "; ".join(visit_result.errors)

                # Mark proxy failure
                if proxy and self.proxy_provider:
                    await self.proxy_provider.mark_failure(proxy, result.error)

        except Exception as e:
            self._stats.failed_visitors += 1
            result.error = str(e)
            self._errors.append(f"Visitor {visitor_id}: {e}")

        finally:
            result.completed_at = datetime.now()
            self._stats.in_progress -= 1
            self._stats.last_visit_at = result.completed_at
            self._visitors.append(result)

            # Trigger progress callback
            if self._on_progress:
                with contextlib.suppress(Exception):
                    self._on_progress(self._stats)

    async def _execute_visit(
        self,
        automation: DEXToolsAutomation,
        proxy: Proxy | None = None,
    ) -> VisitResult:
        """Execute a visit using browser launcher.

        This method handles the browser lifecycle.
        """
        if not self.browser_launcher:
            # No browser launcher - create a mock result for testing
            return VisitResult(
                success=False,
                url=automation.config.pair_url,
                behavior=automation._pick_behavior(),
                dwell_time_s=0.0,
                errors=["No browser launcher configured"],
            )

        browser = None
        context = None
        page = None

        try:
            # Launch browser with proxy
            browser_options: dict[str, Any] = {
                "headless": self.config.headless,
            }
            if proxy:
                browser_options["proxy"] = {
                    "server": proxy.server,
                }
                if proxy.has_auth:
                    browser_options["proxy"]["username"] = proxy.username
                    browser_options["proxy"]["password"] = proxy.password

            browser = await self.browser_launcher.launch(**browser_options)
            context = await browser.new_context()
            page = await context.new_page()

            # Run the visit
            result = await automation.run_natural_visit(page)
            return result

        except Exception as e:
            return VisitResult(
                success=False,
                url=automation.config.pair_url,
                behavior=automation._pick_behavior(),
                dwell_time_s=0.0,
                errors=[str(e)],
            )

        finally:
            # Cleanup
            if page:
                with contextlib.suppress(Exception):
                    await page.close()
            if context:
                with contextlib.suppress(Exception):
                    await context.close()
            if browser:
                with contextlib.suppress(Exception):
                    await browser.close()


async def run_dextools_campaign(
    pair_url: str,
    num_visitors: int = 100,
    duration_hours: float = 24.0,
    proxy_provider: IProxyProvider | None = None,
    browser_launcher: Any = None,
    on_progress: Any = None,
    **kwargs: Any,
) -> CampaignResult:
    """Convenience function to run a DEXTools trending campaign.

    Args:
        pair_url: DEXTools pair URL to visit
        num_visitors: Total number of visitors
        duration_hours: Duration to spread visits over
        proxy_provider: Proxy provider for unique IPs
        browser_launcher: Browser launcher instance
        on_progress: Callback for progress updates
        **kwargs: Additional CampaignConfig options

    Returns:
        CampaignResult with final statistics

    Example:
        ```python
        result = await run_dextools_campaign(
            pair_url="https://www.dextools.io/app/ether/pair-explorer/0x...",
            num_visitors=50,
            duration_hours=6.0,
            proxy_provider=my_proxy_provider,
            browser_launcher=playwright.chromium,
        )
        print(f"Success rate: {result.stats.success_rate * 100}%")
        ```
    """
    config = CampaignConfig(
        pair_url=pair_url,
        num_visitors=num_visitors,
        duration_hours=duration_hours,
        **kwargs,
    )

    campaign = DEXToolsTrendingCampaign(
        config=config,
        proxy_provider=proxy_provider,
        browser_launcher=browser_launcher,
    )

    if on_progress:
        campaign.on_progress(on_progress)

    await campaign.start()
    return campaign.get_result()
