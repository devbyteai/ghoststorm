"""Scroll behavior simulation with natural patterns."""

from __future__ import annotations

import asyncio
import random
from typing import Any


class ScrollBehavior:
    """Simulate human-like scrolling behavior.

    Features:
    - Smooth momentum-based scrolling
    - Variable scroll speeds
    - Reading pauses
    - Random direction changes
    - Scroll-to-element with natural approach
    """

    name = "scroll"

    def __init__(
        self,
        *,
        scroll_speed_range: tuple[int, int] = (100, 400),
        step_delay_range: tuple[float, float] = (0.01, 0.03),
        reading_pause_probability: float = 0.15,
        reading_pause_range: tuple[float, float] = (0.5, 2.0),
    ) -> None:
        self.scroll_speed_range = scroll_speed_range
        self.step_delay_range = step_delay_range
        self.reading_pause_probability = reading_pause_probability
        self.reading_pause_range = reading_pause_range

    def _ease_out_cubic(self, t: float) -> float:
        """Cubic ease-out function for natural deceleration."""
        return 1 - pow(1 - t, 3)

    def _generate_scroll_steps(self, distance: int, direction: int = 1) -> list[int]:
        """Generate scroll steps with natural momentum.

        Args:
            distance: Total distance to scroll
            direction: 1 for down, -1 for up

        Returns:
            List of scroll amounts per step
        """
        abs_distance = abs(distance)
        if abs_distance < 50:
            return [distance]

        # Number of steps based on distance
        num_steps = max(10, min(50, abs_distance // 20))

        steps = []
        accumulated = 0

        for i in range(num_steps):
            progress = i / (num_steps - 1)

            # Use ease-out for momentum feel (fast start, slow end)
            if i < num_steps // 2:
                # Accelerating phase
                factor = self._ease_out_cubic(progress * 2)
            else:
                # Decelerating phase
                factor = 1 - self._ease_out_cubic((progress - 0.5) * 2)

            # Calculate step size
            base_step = abs_distance / num_steps
            step = int(base_step * (0.5 + factor))

            # Add some randomness
            step = int(step * random.uniform(0.8, 1.2))
            step = max(1, step)

            accumulated += step
            steps.append(step * direction)

        # Adjust last step to hit exact distance
        diff = abs_distance - abs(sum(steps))
        if diff != 0 and steps:
            steps[-1] += diff * direction

        return steps

    async def scroll_by(
        self,
        page: Any,
        delta_y: int,
        *,
        smooth: bool = True,
    ) -> None:
        """Scroll page by specified amount.

        Args:
            page: Browser page object
            delta_y: Pixels to scroll (positive = down, negative = up)
            smooth: Use smooth scrolling animation
        """
        if not smooth:
            try:
                await page.evaluate(f"window.scrollBy(0, {delta_y})")
            except Exception:
                pass
            return

        direction = 1 if delta_y > 0 else -1
        steps = self._generate_scroll_steps(delta_y, direction)

        for step in steps:
            try:
                await page.evaluate(f"window.scrollBy(0, {step})")
            except Exception:
                pass

            delay = random.uniform(*self.step_delay_range)
            await asyncio.sleep(delay)

            # Occasional reading pause
            if random.random() < self.reading_pause_probability:
                await asyncio.sleep(random.uniform(*self.reading_pause_range))

    async def scroll_to(
        self,
        page: Any,
        y: int,
        *,
        smooth: bool = True,
    ) -> None:
        """Scroll to specific Y position.

        Args:
            page: Browser page object
            y: Target Y position
            smooth: Use smooth scrolling
        """
        try:
            current_y = await page.evaluate("window.scrollY")
        except Exception:
            current_y = 0

        delta = y - current_y
        await self.scroll_by(page, delta, smooth=smooth)

    async def scroll_to_element(
        self,
        page: Any,
        selector: str,
        *,
        offset: int = -100,
        smooth: bool = True,
    ) -> None:
        """Scroll to bring element into view.

        Args:
            page: Browser page object
            selector: CSS selector for target element
            offset: Offset from top of element (negative = above)
            smooth: Use smooth scrolling
        """
        try:
            # Get element position
            pos = await page.evaluate(f"""
                (() => {{
                    const el = document.querySelector('{selector}');
                    if (!el) return null;
                    const rect = el.getBoundingClientRect();
                    return {{
                        top: rect.top + window.scrollY,
                        height: rect.height
                    }};
                }})()
            """)

            if not pos:
                return

            target_y = pos["top"] + offset
            await self.scroll_to(page, max(0, target_y), smooth=smooth)

        except Exception:
            pass

    async def scroll_to_bottom(
        self,
        page: Any,
        *,
        reading_simulation: bool = True,
        max_time: float = 60.0,
    ) -> None:
        """Scroll to bottom of page with reading simulation.

        Args:
            page: Browser page object
            reading_simulation: Simulate reading behavior
            max_time: Maximum time to spend scrolling
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check time limit
            if asyncio.get_event_loop().time() - start_time > max_time:
                break

            try:
                # Get scroll position info
                info = await page.evaluate("""
                    ({
                        scrollY: window.scrollY,
                        scrollHeight: document.documentElement.scrollHeight,
                        clientHeight: window.innerHeight
                    })
                """)
            except Exception:
                break

            # Check if at bottom
            if info["scrollY"] + info["clientHeight"] >= info["scrollHeight"] - 10:
                break

            # Random scroll amount
            scroll_amount = random.randint(*self.scroll_speed_range)
            await self.scroll_by(page, scroll_amount)

            # Reading simulation
            if reading_simulation and random.random() < self.reading_pause_probability:
                await asyncio.sleep(random.uniform(*self.reading_pause_range))

    async def scroll_to_top(self, page: Any, *, smooth: bool = True) -> None:
        """Scroll to top of page.

        Args:
            page: Browser page object
            smooth: Use smooth scrolling
        """
        await self.scroll_to(page, 0, smooth=smooth)

    async def random_scroll(
        self,
        page: Any,
        *,
        duration: float = 5.0,
        direction_changes: int = 3,
    ) -> None:
        """Perform random scrolling to simulate browsing.

        Args:
            page: Browser page object
            duration: Total duration of random scrolling
            direction_changes: Number of direction changes
        """
        segments = direction_changes + 1
        segment_time = duration / segments

        direction = 1  # Start scrolling down

        for _ in range(segments):
            segment_start = asyncio.get_event_loop().time()

            while asyncio.get_event_loop().time() - segment_start < segment_time:
                scroll_amount = random.randint(50, 200) * direction
                await self.scroll_by(page, scroll_amount)
                await asyncio.sleep(random.uniform(0.2, 0.5))

            # Change direction
            direction *= -1

            # Check bounds
            try:
                info = await page.evaluate("""
                    ({
                        scrollY: window.scrollY,
                        maxScroll: document.documentElement.scrollHeight - window.innerHeight
                    })
                """)

                # Force direction if at bounds
                if info["scrollY"] <= 10:
                    direction = 1
                elif info["scrollY"] >= info["maxScroll"] - 10:
                    direction = -1
            except Exception:
                pass
