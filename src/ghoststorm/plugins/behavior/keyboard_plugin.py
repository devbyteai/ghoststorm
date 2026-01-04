"""Keyboard behavior simulation with human-like typing patterns."""

from __future__ import annotations

import asyncio
import random
from typing import Any


class KeyboardBehavior:
    """Simulate human-like keyboard input.

    Features:
    - Variable typing speed (WPM range)
    - Natural pauses between words
    - Occasional typos with correction
    - Different delays for different character types
    - Burst typing patterns
    """

    name = "keyboard"

    # Keyboard layout for typo simulation (QWERTY)
    ADJACENT_KEYS = {
        "a": ["q", "w", "s", "z"],
        "b": ["v", "g", "h", "n"],
        "c": ["x", "d", "f", "v"],
        "d": ["s", "e", "r", "f", "c", "x"],
        "e": ["w", "r", "d", "s"],
        "f": ["d", "r", "t", "g", "v", "c"],
        "g": ["f", "t", "y", "h", "b", "v"],
        "h": ["g", "y", "u", "j", "n", "b"],
        "i": ["u", "o", "k", "j"],
        "j": ["h", "u", "i", "k", "m", "n"],
        "k": ["j", "i", "o", "l", "m"],
        "l": ["k", "o", "p"],
        "m": ["n", "j", "k"],
        "n": ["b", "h", "j", "m"],
        "o": ["i", "p", "l", "k"],
        "p": ["o", "l"],
        "q": ["w", "a"],
        "r": ["e", "t", "f", "d"],
        "s": ["a", "w", "e", "d", "x", "z"],
        "t": ["r", "y", "g", "f"],
        "u": ["y", "i", "j", "h"],
        "v": ["c", "f", "g", "b"],
        "w": ["q", "e", "s", "a"],
        "x": ["z", "s", "d", "c"],
        "y": ["t", "u", "h", "g"],
        "z": ["a", "s", "x"],
    }

    def __init__(
        self,
        *,
        wpm_range: tuple[int, int] = (40, 80),
        typo_probability: float = 0.02,
        word_pause_range: tuple[float, float] = (0.1, 0.4),
        sentence_pause_range: tuple[float, float] = (0.3, 0.8),
        burst_probability: float = 0.1,
    ) -> None:
        self.wpm_range = wpm_range
        self.typo_probability = typo_probability
        self.word_pause_range = word_pause_range
        self.sentence_pause_range = sentence_pause_range
        self.burst_probability = burst_probability

    def _get_char_delay(self, char: str, base_delay: float) -> float:
        """Calculate delay for specific character.

        Different characters take different times to type.
        """
        # Shift characters take longer
        if char.isupper() or char in '!@#$%^&*()_+{}|:"<>?':
            return base_delay * random.uniform(1.2, 1.5)

        # Numbers on top row
        if char.isdigit():
            return base_delay * random.uniform(1.1, 1.3)

        # Punctuation
        if char in ".,;'":
            return base_delay * random.uniform(0.9, 1.1)

        # Regular letters
        return base_delay * random.uniform(0.8, 1.2)

    def _generate_typo(self, char: str) -> str | None:
        """Generate a realistic typo for a character."""
        lower = char.lower()
        if lower in self.ADJACENT_KEYS:
            adjacent = self.ADJACENT_KEYS[lower]
            typo = random.choice(adjacent)
            return typo.upper() if char.isupper() else typo
        return None

    def _wpm_to_delay(self, wpm: int) -> float:
        """Convert WPM to delay between characters in seconds.

        Average word is 5 characters, so:
        chars per minute = wpm * 5
        chars per second = wpm * 5 / 60
        delay = 60 / (wpm * 5) = 12 / wpm
        """
        return 12.0 / wpm

    async def type_text(
        self,
        page: Any,
        text: str,
        *,
        selector: str | None = None,
        clear_first: bool = False,
        simulate_typos: bool = True,
    ) -> None:
        """Type text with human-like patterns.

        Args:
            page: Browser page object
            text: Text to type
            selector: Optional selector to focus before typing
            clear_first: Clear existing content before typing
            simulate_typos: Whether to simulate occasional typos
        """
        # Focus element if selector provided
        if selector:
            try:
                await page.click(selector)
                await asyncio.sleep(random.uniform(0.1, 0.2))
            except Exception:
                pass

        # Clear if requested
        if clear_first:
            try:
                await page.keyboard.press("Control+a")
                await asyncio.sleep(0.05)
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.1, 0.2))
            except Exception:
                pass

        # Calculate base delay from WPM
        current_wpm = random.randint(*self.wpm_range)
        base_delay = self._wpm_to_delay(current_wpm)

        # Track if we're in a "burst" (faster typing)
        in_burst = False
        burst_chars_left = 0

        i = 0
        while i < len(text):
            char = text[i]

            # Check for burst mode
            if not in_burst and random.random() < self.burst_probability:
                in_burst = True
                burst_chars_left = random.randint(3, 8)

            if in_burst:
                burst_chars_left -= 1
                if burst_chars_left <= 0:
                    in_burst = False

            # Calculate delay for this character
            delay = self._get_char_delay(char, base_delay)
            if in_burst:
                delay *= 0.6  # Faster during burst

            # Simulate typo
            if simulate_typos and random.random() < self.typo_probability and char.isalpha():
                typo = self._generate_typo(char)
                if typo:
                    # Type wrong character
                    try:
                        await page.keyboard.type(typo)
                    except Exception:
                        pass
                    await asyncio.sleep(delay)

                    # Brief pause (realizing mistake)
                    await asyncio.sleep(random.uniform(0.15, 0.4))

                    # Delete and retype
                    try:
                        await page.keyboard.press("Backspace")
                    except Exception:
                        pass
                    await asyncio.sleep(random.uniform(0.08, 0.15))

            # Type the correct character
            try:
                await page.keyboard.type(char)
            except Exception:
                pass
            await asyncio.sleep(delay)

            # Add pauses after spaces and punctuation
            if char == " ":
                await asyncio.sleep(random.uniform(*self.word_pause_range))
            elif char in ".!?":
                await asyncio.sleep(random.uniform(*self.sentence_pause_range))

            i += 1

    async def press_key(
        self,
        page: Any,
        key: str,
        *,
        modifiers: list[str] | None = None,
        hold_time: float | None = None,
    ) -> None:
        """Press a key with optional modifiers.

        Args:
            page: Browser page object
            key: Key to press (e.g., "Enter", "Tab", "a")
            modifiers: List of modifier keys (e.g., ["Control", "Shift"])
            hold_time: Optional time to hold the key
        """
        # Press modifiers
        if modifiers:
            for mod in modifiers:
                try:
                    await page.keyboard.down(mod)
                except Exception:
                    pass

        # Press key
        if hold_time:
            try:
                await page.keyboard.down(key)
                await asyncio.sleep(hold_time)
                await page.keyboard.up(key)
            except Exception:
                pass
        else:
            hold = random.uniform(0.05, 0.12)
            try:
                await page.keyboard.down(key)
                await asyncio.sleep(hold)
                await page.keyboard.up(key)
            except Exception:
                pass

        # Release modifiers
        if modifiers:
            for mod in reversed(modifiers):
                try:
                    await page.keyboard.up(mod)
                except Exception:
                    pass

        # Small delay after key press
        await asyncio.sleep(random.uniform(0.05, 0.1))

    async def paste_text(self, page: Any, text: str) -> None:
        """Paste text using clipboard (faster than typing).

        Args:
            page: Browser page object
            text: Text to paste
        """
        try:
            # Set clipboard
            await page.evaluate(f'navigator.clipboard.writeText({text!r})')
            await asyncio.sleep(random.uniform(0.1, 0.2))

            # Paste
            await page.keyboard.press("Control+v")
            await asyncio.sleep(random.uniform(0.1, 0.2))
        except Exception:
            # Fallback to typing
            await self.type_text(page, text, simulate_typos=False)
