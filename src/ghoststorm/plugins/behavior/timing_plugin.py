"""Timing behavior for realistic delays and dwell times."""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class TimingBehavior:
    """Manage realistic timing and delays.

    Features:
    - Variable dwell times
    - Action delays with jitter
    - Page load wait patterns
    - Idle simulation
    - Time-of-day aware pacing
    """

    name = "timing"

    def __init__(
        self,
        *,
        dwell_time_range: tuple[float, float] = (5.0, 30.0),
        action_delay_range: tuple[float, float] = (0.5, 2.0),
        idle_probability: float = 0.1,
        idle_duration_range: tuple[float, float] = (2.0, 8.0),
    ) -> None:
        self.dwell_time_range = dwell_time_range
        self.action_delay_range = action_delay_range
        self.idle_probability = idle_probability
        self.idle_duration_range = idle_duration_range

    async def wait_random(
        self,
        min_seconds: float | None = None,
        max_seconds: float | None = None,
    ) -> float:
        """Wait for a random duration.

        Args:
            min_seconds: Minimum wait time (default from action_delay_range)
            max_seconds: Maximum wait time (default from action_delay_range)

        Returns:
            Actual wait time in seconds
        """
        min_s = min_seconds if min_seconds is not None else self.action_delay_range[0]
        max_s = max_seconds if max_seconds is not None else self.action_delay_range[1]

        wait_time = random.uniform(min_s, max_s)
        await asyncio.sleep(wait_time)
        return wait_time

    async def dwell(
        self,
        *,
        min_time: float | None = None,
        max_time: float | None = None,
        activity_callback: Callable | None = None,
        activity_interval: float = 5.0,
    ) -> float:
        """Simulate staying on a page for a realistic duration.

        Args:
            min_time: Minimum dwell time
            max_time: Maximum dwell time
            activity_callback: Optional async callback to simulate activity
            activity_interval: Interval between activity callbacks

        Returns:
            Total dwell time in seconds
        """
        min_t = min_time if min_time is not None else self.dwell_time_range[0]
        max_t = max_time if max_time is not None else self.dwell_time_range[1]

        total_time = random.uniform(min_t, max_t)
        elapsed = 0.0

        while elapsed < total_time:
            # Determine next interval
            remaining = total_time - elapsed
            interval = min(activity_interval + random.uniform(-1, 1), remaining)

            # Wait for interval
            await asyncio.sleep(interval)
            elapsed += interval

            # Maybe trigger activity
            if activity_callback and elapsed < total_time:
                try:
                    if asyncio.iscoroutinefunction(activity_callback):
                        await activity_callback()
                    else:
                        activity_callback()
                except Exception:
                    pass

            # Random idle period
            if random.random() < self.idle_probability:
                idle_time = random.uniform(*self.idle_duration_range)
                idle_time = min(idle_time, remaining - interval)
                if idle_time > 0:
                    await asyncio.sleep(idle_time)
                    elapsed += idle_time

        return elapsed

    async def wait_for_action(self, action_type: str = "click") -> float:
        """Wait appropriate time before an action.

        Different action types have different natural delays.

        Args:
            action_type: Type of action (click, type, scroll, navigate)

        Returns:
            Wait time in seconds
        """
        delays = {
            "click": (0.3, 1.0),
            "type": (0.5, 1.5),
            "scroll": (0.2, 0.8),
            "navigate": (0.5, 2.0),
            "submit": (0.8, 2.0),
            "hover": (0.1, 0.5),
        }

        delay_range = delays.get(action_type, self.action_delay_range)
        return await self.wait_random(delay_range[0], delay_range[1])

    async def wait_after_action(self, action_type: str = "click") -> float:
        """Wait appropriate time after an action.

        Args:
            action_type: Type of completed action

        Returns:
            Wait time in seconds
        """
        delays = {
            "click": (0.2, 0.6),
            "type": (0.1, 0.4),
            "scroll": (0.1, 0.3),
            "navigate": (1.0, 3.0),
            "submit": (1.5, 4.0),
            "hover": (0.5, 1.5),
        }

        delay_range = delays.get(action_type, (0.2, 0.8))
        return await self.wait_random(delay_range[0], delay_range[1])

    async def wait_for_page_interactive(
        self,
        page,
        *,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> bool:
        """Wait for page to become interactive.

        Args:
            page: Browser page object
            timeout: Maximum wait time
            poll_interval: How often to check

        Returns:
            True if page became interactive, False if timeout
        """
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            try:
                state = await page.evaluate("document.readyState")
                if state in ("interactive", "complete"):
                    # Additional small delay for dynamic content
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    return True
            except Exception:
                pass

            await asyncio.sleep(poll_interval)

        return False

    async def wait_for_network_idle(
        self,
        page,
        *,
        timeout: float = 30.0,
        idle_time: float = 0.5,
    ) -> bool:
        """Wait for network activity to settle.

        Args:
            page: Browser page object
            timeout: Maximum wait time
            idle_time: Required idle duration

        Returns:
            True if network became idle, False if timeout
        """
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            await asyncio.sleep(random.uniform(0.2, 0.5))
            return True
        except Exception:
            return False

    def jitter(self, base_value: float, jitter_percent: float = 0.2) -> float:
        """Add random jitter to a value.

        Args:
            base_value: Base value
            jitter_percent: Percentage of jitter (0.2 = ±20%)

        Returns:
            Value with jitter applied
        """
        jitter_amount = base_value * jitter_percent
        return base_value + random.uniform(-jitter_amount, jitter_amount)

    async def with_jittered_delay(
        self,
        coroutine,
        delay: float,
        jitter_percent: float = 0.2,
    ):
        """Execute coroutine after jittered delay.

        Args:
            coroutine: Async function to execute
            delay: Base delay before execution
            jitter_percent: Jitter percentage

        Returns:
            Result of coroutine
        """
        actual_delay = self.jitter(delay, jitter_percent)
        await asyncio.sleep(actual_delay)
        return await coroutine
