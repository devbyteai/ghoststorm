"""Human behavior simulation interface definitions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ghoststorm.core.interfaces.browser import IPage


@runtime_checkable
class IBehaviorSimulator(Protocol):
    """Contract for human behavior simulators."""

    @property
    def name(self) -> str:
        """Simulator name."""
        ...

    async def move_mouse(
        self,
        page: IPage,
        x: int,
        y: int,
        *,
        steps: int | None = None,
        speed: str = "normal",
        add_tremor: bool = True,
    ) -> None:
        """
        Move mouse to position with human-like trajectory.

        Args:
            page: The page to interact with
            x: Target X coordinate
            y: Target Y coordinate
            steps: Number of intermediate steps (auto if None)
            speed: Movement speed ('slow', 'normal', 'fast')
            add_tremor: Add hand tremor effect
        """
        ...

    async def click(
        self,
        page: IPage,
        selector: str | None = None,
        *,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        click_count: int = 1,
        pre_delay: tuple[int, int] = (50, 200),
        post_delay: tuple[int, int] = (100, 300),
    ) -> None:
        """
        Click with human-like behavior.

        Args:
            page: The page to interact with
            selector: CSS selector to click (mutually exclusive with x/y)
            x: X coordinate (mutually exclusive with selector)
            y: Y coordinate (mutually exclusive with selector)
            button: Mouse button ('left', 'right', 'middle')
            click_count: Number of clicks (2 for double-click)
            pre_delay: Random delay before click (min, max) ms
            post_delay: Random delay after click (min, max) ms
        """
        ...

    async def type_text(
        self,
        page: IPage,
        selector: str,
        text: str,
        *,
        wpm: tuple[int, int] = (40, 80),
        mistakes: bool = True,
        mistake_rate: float = 0.02,
    ) -> None:
        """
        Type text with human-like patterns.

        Args:
            page: The page to interact with
            selector: Input selector
            text: Text to type
            wpm: Words per minute range (min, max)
            mistakes: Whether to make and correct typos
            mistake_rate: Probability of typo per character
        """
        ...

    async def scroll(
        self,
        page: IPage,
        *,
        direction: str = "down",
        amount: int | None = None,
        speed: str = "normal",
        smooth: bool = True,
    ) -> None:
        """
        Scroll with human-like behavior.

        Args:
            page: The page to interact with
            direction: Scroll direction ('up', 'down', 'left', 'right')
            amount: Scroll amount in pixels (random if None)
            speed: Scroll speed ('slow', 'normal', 'fast')
            smooth: Use smooth scrolling
        """
        ...

    async def scroll_to_element(
        self,
        page: IPage,
        selector: str,
        *,
        align: str = "center",
        smooth: bool = True,
    ) -> None:
        """
        Scroll to bring element into view.

        Args:
            page: The page to interact with
            selector: Element selector
            align: Alignment ('start', 'center', 'end')
            smooth: Use smooth scrolling
        """
        ...

    async def random_mouse_movement(
        self,
        page: IPage,
        *,
        duration_ms: tuple[int, int] = (500, 2000),
        movements: tuple[int, int] = (2, 5),
    ) -> None:
        """
        Make random mouse movements.

        Args:
            page: The page to interact with
            duration_ms: Total duration range in ms
            movements: Number of movements range
        """
        ...

    async def wait_human(
        self,
        *,
        min_ms: int = 500,
        max_ms: int = 3000,
        distribution: str = "normal",
    ) -> None:
        """
        Wait with human-like variability.

        Args:
            min_ms: Minimum wait time in ms
            max_ms: Maximum wait time in ms
            distribution: Distribution type ('uniform', 'normal', 'exponential')
        """
        ...

    async def simulate_reading(
        self,
        page: IPage,
        *,
        wpm: int = 250,
        scroll_probability: float = 0.3,
    ) -> None:
        """
        Simulate reading page content.

        Args:
            page: The page to interact with
            wpm: Reading speed in words per minute
            scroll_probability: Probability of scrolling while reading
        """
        ...

    async def hover(
        self,
        page: IPage,
        selector: str,
        *,
        duration_ms: tuple[int, int] = (200, 800),
    ) -> None:
        """
        Hover over element with human-like timing.

        Args:
            page: The page to interact with
            selector: Element selector
            duration_ms: Hover duration range in ms
        """
        ...
