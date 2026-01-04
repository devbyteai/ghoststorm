"""Async event bus for decoupled communication."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import structlog

from ghoststorm.core.events.types import EventType

logger = structlog.get_logger(__name__)

# Type alias for event handlers
EventHandler = Callable[["Event"], Coroutine[Any, Any, None]]


@dataclass
class Event:
    """Represents an event in the system."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: str(uuid4()))

    # Metadata
    correlation_id: str | None = None
    parent_id: str | None = None

    def __post_init__(self) -> None:
        """Set source if not provided."""
        if not self.source:
            self.source = "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "parent_id": self.parent_id,
        }

    def child(self, event_type: EventType, data: dict[str, Any] | None = None) -> Event:
        """Create a child event linked to this one."""
        return Event(
            type=event_type,
            data=data or {},
            source=self.source,
            correlation_id=self.correlation_id or self.id,
            parent_id=self.id,
        )


class AsyncEventBus:
    """Async event bus for pub/sub communication."""

    def __init__(self, max_queue_size: int = 10000) -> None:
        """
        Initialize the event bus.

        Args:
            max_queue_size: Maximum number of events to queue
        """
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: list[EventHandler] = []
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_queue_size)
        self._processing_task: asyncio.Task[None] | None = None
        self._running = False
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "handlers_invoked": 0,
            "handler_errors": 0,
        }

    async def start(self) -> None:
        """Start the event processing loop."""
        if self._running:
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop the event processing loop."""
        if not self._running:
            return

        self._running = False

        # Process remaining events
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                await self._dispatch(event)
            except asyncio.QueueEmpty:
                break

        # Cancel processing task
        if self._processing_task:
            self._processing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._processing_task
            self._processing_task = None

        logger.info("Event bus stopped", stats=self._stats)

    def subscribe(
        self,
        event_type: EventType | None,
        handler: EventHandler,
    ) -> Callable[[], None]:
        """
        Subscribe to events.

        Args:
            event_type: Event type to subscribe to, or None for all events
            handler: Async handler function

        Returns:
            Unsubscribe function
        """
        if event_type is None:
            self._wildcard_handlers.append(handler)
            return lambda: self._wildcard_handlers.remove(handler)
        else:
            self._handlers[event_type].append(handler)
            return lambda: self._handlers[event_type].remove(handler)

    def unsubscribe(
        self,
        event_type: EventType | None,
        handler: EventHandler,
    ) -> None:
        """
        Unsubscribe from events.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove
        """
        if event_type is None:
            if handler in self._wildcard_handlers:
                self._wildcard_handlers.remove(handler)
        else:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

    async def publish(self, event: Event) -> None:
        """
        Publish an event to the bus.

        Args:
            event: Event to publish
        """
        self._stats["events_published"] += 1
        await self._queue.put(event)

    def publish_sync(self, event: Event) -> None:
        """
        Publish an event synchronously (non-blocking).

        Args:
            event: Event to publish
        """
        try:
            self._queue.put_nowait(event)
            self._stats["events_published"] += 1
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event", event_type=event.type.value)

    async def emit(
        self,
        event_type: EventType,
        data: dict[str, Any] | None = None,
        source: str = "",
    ) -> Event:
        """
        Convenience method to create and publish an event.

        Args:
            event_type: Type of event
            data: Event data
            source: Event source

        Returns:
            The created event
        """
        event = Event(type=event_type, data=data or {}, source=source)
        await self.publish(event)
        return event

    async def _process_events(self) -> None:
        """Background task to process events from queue."""
        while self._running:
            try:
                # Wait for event with timeout to allow clean shutdown
                try:
                    event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except TimeoutError:
                    continue

                await self._dispatch(event)
                self._stats["events_processed"] += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in event processing loop", error=str(e))

    async def _dispatch(self, event: Event) -> None:
        """Dispatch event to all registered handlers."""
        handlers = list(self._handlers.get(event.type, []))
        handlers.extend(self._wildcard_handlers)

        if not handlers:
            return

        # Run all handlers concurrently
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(self._invoke_handler(handler, event))
            tasks.append(task)

        # Wait for all handlers to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _invoke_handler(self, handler: EventHandler, event: Event) -> None:
        """Invoke a single handler with error handling."""
        try:
            self._stats["handlers_invoked"] += 1
            await handler(event)
        except Exception as e:
            self._stats["handler_errors"] += 1
            logger.exception(
                "Handler error",
                handler=handler.__name__,
                event_type=event.type.value,
                error=str(e),
            )

    @property
    def stats(self) -> dict[str, int]:
        """Get event bus statistics."""
        return self._stats.copy()

    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """Check if event bus is running."""
        return self._running


# Re-export for convenience
__all__ = ["AsyncEventBus", "Event", "EventHandler", "EventType"]
