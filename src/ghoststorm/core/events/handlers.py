"""Base event handler classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ghoststorm.core.events.bus import Event
    from ghoststorm.core.events.types import EventType


class EventHandler(ABC):
    """Base class for event handlers."""

    @property
    @abstractmethod
    def handled_events(self) -> list[EventType]:
        """List of event types this handler processes."""
        ...

    @abstractmethod
    async def handle(self, event: Event) -> None:
        """
        Handle an event.

        Args:
            event: The event to handle
        """
        ...

    async def __call__(self, event: Event) -> None:
        """Make handler callable."""
        if event.type in self.handled_events:
            await self.handle(event)


class LoggingHandler(EventHandler):
    """Handler that logs all events."""

    def __init__(self, event_types: list[EventType] | None = None) -> None:
        """
        Initialize logging handler.

        Args:
            event_types: Event types to log (None for all)
        """
        import structlog

        self._event_types = event_types or []
        self._logger = structlog.get_logger(__name__)

    @property
    def handled_events(self) -> list[EventType]:
        """Return handled event types."""
        return self._event_types

    async def handle(self, event: Event) -> None:
        """Log the event."""
        self._logger.info(
            "Event received",
            event_id=event.id,
            event_type=event.type.value,
            source=event.source,
            data=event.data,
        )

    async def __call__(self, event: Event) -> None:
        """Handle all events if no filter, otherwise filter."""
        if not self._event_types or event.type in self._event_types:
            await self.handle(event)


class MetricsHandler(EventHandler):
    """Handler that collects metrics from events."""

    def __init__(self) -> None:
        """Initialize metrics handler."""
        from ghoststorm.core.events.types import EventType

        self._counters: dict[str, int] = {}
        self._event_types = [
            EventType.TASK_COMPLETED,
            EventType.TASK_FAILED,
            EventType.PROXY_SUCCESS,
            EventType.PROXY_FAILED,
            EventType.CAPTCHA_DETECTED,
            EventType.BOT_DETECTED,
        ]

    @property
    def handled_events(self) -> list[EventType]:
        """Return handled event types."""
        return self._event_types

    async def handle(self, event: Event) -> None:
        """Increment counter for event type."""
        key = event.type.value
        self._counters[key] = self._counters.get(key, 0) + 1

    def get_metrics(self) -> dict[str, int]:
        """Get collected metrics."""
        return self._counters.copy()

    def reset(self) -> None:
        """Reset all counters."""
        self._counters.clear()


class CompositeHandler(EventHandler):
    """Handler that delegates to multiple handlers."""

    def __init__(self, handlers: list[EventHandler]) -> None:
        """
        Initialize composite handler.

        Args:
            handlers: List of handlers to delegate to
        """
        self._handlers = handlers

    @property
    def handled_events(self) -> list[EventType]:
        """Return all handled event types from all handlers."""
        events = set()
        for handler in self._handlers:
            events.update(handler.handled_events)
        return list(events)

    async def handle(self, event: Event) -> None:
        """Delegate to all handlers."""
        import asyncio

        tasks = [handler(event) for handler in self._handlers]
        await asyncio.gather(*tasks, return_exceptions=True)
