"""Core module - minimal foundation with interfaces and models."""

from ghoststorm.core.events.bus import AsyncEventBus, Event, EventType
from ghoststorm.core.registry.manager import PluginManager

__all__ = [
    "AsyncEventBus",
    "Event",
    "EventType",
    "PluginManager",
]
