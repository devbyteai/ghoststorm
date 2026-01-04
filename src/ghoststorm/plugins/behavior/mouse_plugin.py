"""Mouse behavior simulation with Bezier curves and natural movement patterns."""

from __future__ import annotations

import asyncio
import contextlib
import math
import random
from dataclasses import dataclass
from typing import Any


@dataclass
class Point:
    """2D coordinate point."""

    x: float
    y: float


class MouseBehavior:
    """Simulate human-like mouse movements.

    Features:
    - Bezier curve trajectories (not linear)
    - Natural acceleration/deceleration
    - Micro-movements and tremor simulation
    - Random overshooting and correction
    - Variable speed based on distance
    """

    name = "mouse"

    def __init__(
        self,
        *,
        min_steps: int = 20,
        max_steps: int = 50,
        overshoot_probability: float = 0.15,
        tremor_amplitude: float = 1.5,
        base_delay_ms: float = 5.0,
    ) -> None:
        self.min_steps = min_steps
        self.max_steps = max_steps
        self.overshoot_probability = overshoot_probability
        self.tremor_amplitude = tremor_amplitude
        self.base_delay_ms = base_delay_ms

    def _bezier_curve(
        self,
        start: Point,
        end: Point,
        control1: Point,
        control2: Point,
        t: float,
    ) -> Point:
        """Calculate point on cubic Bezier curve."""
        u = 1 - t
        return Point(
            x=(u**3) * start.x
            + 3 * (u**2) * t * control1.x
            + 3 * u * (t**2) * control2.x
            + (t**3) * end.x,
            y=(u**3) * start.y
            + 3 * (u**2) * t * control1.y
            + 3 * u * (t**2) * control2.y
            + (t**3) * end.y,
        )

    def _generate_control_points(self, start: Point, end: Point) -> tuple[Point, Point]:
        """Generate natural-looking control points for Bezier curve."""
        distance = math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)

        # Control point deviation based on distance
        deviation = min(distance * 0.3, 100)

        # First control point - near start, random offset
        c1 = Point(
            x=start.x + (end.x - start.x) * 0.25 + random.uniform(-deviation, deviation),
            y=start.y + (end.y - start.y) * 0.25 + random.uniform(-deviation, deviation),
        )

        # Second control point - near end, random offset
        c2 = Point(
            x=start.x + (end.x - start.x) * 0.75 + random.uniform(-deviation, deviation),
            y=start.y + (end.y - start.y) * 0.75 + random.uniform(-deviation, deviation),
        )

        return c1, c2

    def _apply_tremor(self, point: Point) -> Point:
        """Apply subtle tremor to simulate human hand shake."""
        return Point(
            x=point.x + random.gauss(0, self.tremor_amplitude),
            y=point.y + random.gauss(0, self.tremor_amplitude),
        )

    def _calculate_delay(self, progress: float, distance: float) -> float:
        """Calculate delay between movements with acceleration curve."""
        # Slow start, fast middle, slow end (ease-in-out)
        speed_multiplier = 1 - 4 * (progress - 0.5) ** 2  # Parabola peaking at 0.5

        # Longer distance = faster overall movement
        distance_factor = max(0.5, min(2.0, 500 / max(distance, 1)))

        delay = self.base_delay_ms * (0.5 + speed_multiplier) * distance_factor
        return max(1, delay + random.uniform(-2, 2))

    def generate_path(self, start: Point, end: Point) -> list[Point]:
        """Generate human-like mouse path from start to end."""
        distance = math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)

        # More steps for longer distances
        num_steps = int(
            self.min_steps + (self.max_steps - self.min_steps) * min(distance / 1000, 1)
        )

        # Generate control points
        c1, c2 = self._generate_control_points(start, end)

        # Generate path points
        path = []
        for i in range(num_steps + 1):
            t = i / num_steps
            point = self._bezier_curve(start, end, c1, c2, t)

            # Apply tremor (less at start and end)
            tremor_factor = 1 - abs(2 * t - 1)
            if tremor_factor > 0.2:
                point = self._apply_tremor(point)

            path.append(point)

        # Random overshoot and correction
        if random.random() < self.overshoot_probability:
            overshoot_amount = random.uniform(5, 20)
            dx = end.x - start.x
            dy = end.y - start.y
            magnitude = max(math.sqrt(dx * dx + dy * dy), 1)

            overshoot_point = Point(
                x=end.x + (dx / magnitude) * overshoot_amount,
                y=end.y + (dy / magnitude) * overshoot_amount,
            )
            path.append(overshoot_point)

            # Correction back to target
            correction_steps = random.randint(3, 7)
            for i in range(1, correction_steps + 1):
                t = i / correction_steps
                path.append(
                    Point(
                        x=overshoot_point.x + (end.x - overshoot_point.x) * t,
                        y=overshoot_point.y + (end.y - overshoot_point.y) * t,
                    )
                )

        return path

    async def move_to(self, page: Any, x: float, y: float) -> None:
        """Move mouse to target position with human-like trajectory.

        Args:
            page: Browser page object with mouse.move() method
            x: Target X coordinate
            y: Target Y coordinate
        """
        # Get current position (default to center if unknown)
        try:
            current = await page.evaluate(
                "() => ({x: window._mouseX || window.innerWidth/2, y: window._mouseY || window.innerHeight/2})"
            )
            start = Point(current["x"], current["y"])
        except Exception:
            start = Point(400, 300)

        end = Point(x, y)
        path = self.generate_path(start, end)
        distance = math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)

        for i, point in enumerate(path):
            progress = i / max(len(path) - 1, 1)
            delay = self._calculate_delay(progress, distance)

            try:
                await page.mouse.move(point.x, point.y)
                # Track position for next movement
                await page.evaluate(
                    f"() => {{ window._mouseX = {point.x}; window._mouseY = {point.y}; }}"
                )
            except Exception:
                pass

            await asyncio.sleep(delay / 1000)

    async def click(
        self,
        page: Any,
        x: float,
        y: float,
        *,
        button: str = "left",
        click_count: int = 1,
    ) -> None:
        """Click at position with human-like movement and timing.

        Args:
            page: Browser page object
            x: Target X coordinate
            y: Target Y coordinate
            button: Mouse button (left, right, middle)
            click_count: Number of clicks (1 for single, 2 for double)
        """
        # Move to position first
        await self.move_to(page, x, y)

        # Small pause before click
        await asyncio.sleep(random.uniform(0.05, 0.15))

        # Perform click(s)
        for i in range(click_count):
            if i > 0:
                await asyncio.sleep(random.uniform(0.08, 0.15))

            # Random hold duration
            hold_time = random.uniform(0.05, 0.12)

            try:
                await page.mouse.down(button=button)
                await asyncio.sleep(hold_time)
                await page.mouse.up(button=button)
            except Exception:
                pass

    async def drag(
        self,
        page: Any,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
    ) -> None:
        """Perform drag operation with human-like movement.

        Args:
            page: Browser page object
            start_x: Start X coordinate
            start_y: Start Y coordinate
            end_x: End X coordinate
            end_y: End Y coordinate
        """
        # Move to start
        await self.move_to(page, start_x, start_y)
        await asyncio.sleep(random.uniform(0.1, 0.2))

        # Press and hold
        try:
            await page.mouse.down()
        except Exception:
            return

        await asyncio.sleep(random.uniform(0.05, 0.1))

        # Drag to end
        start = Point(start_x, start_y)
        end = Point(end_x, end_y)
        path = self.generate_path(start, end)
        distance = math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)

        for i, point in enumerate(path):
            progress = i / max(len(path) - 1, 1)
            delay = self._calculate_delay(progress, distance) * 1.5  # Slower for drag

            with contextlib.suppress(Exception):
                await page.mouse.move(point.x, point.y)

            await asyncio.sleep(delay / 1000)

        # Release
        await asyncio.sleep(random.uniform(0.05, 0.1))
        with contextlib.suppress(Exception):
            await page.mouse.up()
