"""Tests for AsyncEventBus and Event classes."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from ghoststorm.core.events.bus import AsyncEventBus, Event, EventHandler
from ghoststorm.core.events.types import EventType


# ============================================================================
# EVENT DATACLASS TESTS
# ============================================================================


class TestEventCreation:
    """Tests for Event dataclass creation."""

    def test_event_with_required_fields(self):
        """Test Event creation with only type."""
        event = Event(type=EventType.ENGINE_STARTED)
        assert event.type == EventType.ENGINE_STARTED
        assert isinstance(event.id, str)
        assert len(event.id) == 36  # UUID format
        assert event.data == {}
        assert event.source == "unknown"
        assert isinstance(event.timestamp, float)

    def test_event_with_all_fields(self):
        """Test Event creation with all fields specified."""
        ts = time.time()
        event = Event(
            type=EventType.TASK_STARTED,
            data={"task_id": 123},
            source="test_module",
            timestamp=ts,
            id="custom-id-123",
            correlation_id="corr-456",
            parent_id="parent-789",
        )
        assert event.type == EventType.TASK_STARTED
        assert event.data == {"task_id": 123}
        assert event.source == "test_module"
        assert event.timestamp == ts
        assert event.id == "custom-id-123"
        assert event.correlation_id == "corr-456"
        assert event.parent_id == "parent-789"

    def test_event_default_source_becomes_unknown(self):
        """Test that empty source defaults to 'unknown'."""
        event = Event(type=EventType.ENGINE_STARTED, source="")
        assert event.source == "unknown"

    def test_event_generates_unique_ids(self):
        """Test that each event gets a unique ID."""
        events = [Event(type=EventType.ENGINE_STARTED) for _ in range(100)]
        ids = [e.id for e in events]
        assert len(set(ids)) == 100  # All unique

    def test_event_timestamp_auto_generated(self):
        """Test that timestamp is automatically set to current time."""
        before = time.time()
        event = Event(type=EventType.ENGINE_STARTED)
        after = time.time()
        assert before <= event.timestamp <= after

    def test_event_correlation_id_defaults_to_none(self):
        """Test that correlation_id defaults to None."""
        event = Event(type=EventType.ENGINE_STARTED)
        assert event.correlation_id is None

    def test_event_parent_id_defaults_to_none(self):
        """Test that parent_id defaults to None."""
        event = Event(type=EventType.ENGINE_STARTED)
        assert event.parent_id is None


class TestEventToDict:
    """Tests for Event.to_dict() serialization."""

    def test_to_dict_contains_all_fields(self):
        """Test that to_dict includes all event fields."""
        event = Event(
            type=EventType.TASK_COMPLETED,
            data={"result": "success"},
            source="worker",
            correlation_id="corr-123",
            parent_id="parent-456",
        )
        result = event.to_dict()

        assert result["id"] == event.id
        assert result["type"] == "task.completed"  # EventType.value
        assert result["data"] == {"result": "success"}
        assert result["source"] == "worker"
        assert result["timestamp"] == event.timestamp
        assert result["correlation_id"] == "corr-123"
        assert result["parent_id"] == "parent-456"

    def test_to_dict_uses_event_type_value(self):
        """Test that to_dict converts EventType to string value."""
        event = Event(type=EventType.BROWSER_LAUNCHED)
        result = event.to_dict()
        assert result["type"] == "browser.launched"

    def test_to_dict_with_none_correlation(self):
        """Test to_dict with None correlation and parent IDs."""
        event = Event(type=EventType.ENGINE_STARTED)
        result = event.to_dict()
        assert result["correlation_id"] is None
        assert result["parent_id"] is None

    def test_to_dict_with_complex_data(self):
        """Test to_dict with nested data structures."""
        complex_data = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42.5,
        }
        event = Event(type=EventType.DATA_EXTRACTED, data=complex_data)
        result = event.to_dict()
        assert result["data"] == complex_data


class TestEventChild:
    """Tests for Event.child() method."""

    def test_child_creates_new_event(self):
        """Test that child creates a new Event instance."""
        parent = Event(type=EventType.TASK_STARTED, source="worker")
        child = parent.child(EventType.TASK_PROGRESS)
        assert child is not parent
        assert child.id != parent.id

    def test_child_inherits_source(self):
        """Test that child inherits parent's source."""
        parent = Event(type=EventType.TASK_STARTED, source="worker-1")
        child = parent.child(EventType.TASK_PROGRESS)
        assert child.source == "worker-1"

    def test_child_sets_parent_id(self):
        """Test that child's parent_id is set to parent's id."""
        parent = Event(type=EventType.TASK_STARTED)
        child = parent.child(EventType.TASK_PROGRESS)
        assert child.parent_id == parent.id

    def test_child_sets_correlation_id_from_parent_id(self):
        """Test that correlation_id is parent's id when parent has no correlation."""
        parent = Event(type=EventType.TASK_STARTED)
        assert parent.correlation_id is None
        child = parent.child(EventType.TASK_PROGRESS)
        assert child.correlation_id == parent.id

    def test_child_inherits_correlation_id(self):
        """Test that correlation_id is inherited if parent has one."""
        parent = Event(
            type=EventType.TASK_STARTED,
            correlation_id="root-correlation",
        )
        child = parent.child(EventType.TASK_PROGRESS)
        assert child.correlation_id == "root-correlation"

    def test_child_with_custom_data(self):
        """Test that child can have custom data."""
        parent = Event(type=EventType.TASK_STARTED)
        child = parent.child(EventType.TASK_PROGRESS, data={"progress": 50})
        assert child.data == {"progress": 50}

    def test_child_with_none_data(self):
        """Test that child with None data defaults to empty dict."""
        parent = Event(type=EventType.TASK_STARTED)
        child = parent.child(EventType.TASK_PROGRESS, data=None)
        assert child.data == {}

    def test_child_chain_maintains_correlation(self):
        """Test that correlation_id is maintained through multiple generations."""
        root = Event(type=EventType.TASK_STARTED)
        child1 = root.child(EventType.TASK_PROGRESS)
        child2 = child1.child(EventType.TASK_PROGRESS)
        child3 = child2.child(EventType.TASK_COMPLETED)

        # All should share the same correlation_id (root's id)
        assert child1.correlation_id == root.id
        assert child2.correlation_id == root.id
        assert child3.correlation_id == root.id

        # Parent IDs form a chain
        assert child1.parent_id == root.id
        assert child2.parent_id == child1.id
        assert child3.parent_id == child2.id


# ============================================================================
# ASYNC EVENT BUS INITIALIZATION TESTS
# ============================================================================


class TestAsyncEventBusInit:
    """Tests for AsyncEventBus initialization."""

    def test_default_max_queue_size(self):
        """Test default max_queue_size is 10000."""
        bus = AsyncEventBus()
        assert bus._queue.maxsize == 10000

    def test_custom_max_queue_size(self):
        """Test custom max_queue_size."""
        bus = AsyncEventBus(max_queue_size=100)
        assert bus._queue.maxsize == 100

    def test_initial_state_not_running(self):
        """Test that bus is not running initially."""
        bus = AsyncEventBus()
        assert bus.is_running is False

    def test_initial_queue_is_empty(self):
        """Test that queue is empty initially."""
        bus = AsyncEventBus()
        assert bus.queue_size == 0

    def test_initial_stats_are_zero(self):
        """Test that all stats start at zero."""
        bus = AsyncEventBus()
        stats = bus.stats
        assert stats["events_published"] == 0
        assert stats["events_processed"] == 0
        assert stats["handlers_invoked"] == 0
        assert stats["handler_errors"] == 0

    def test_stats_returns_copy(self):
        """Test that stats property returns a copy."""
        bus = AsyncEventBus()
        stats1 = bus.stats
        stats1["events_published"] = 999
        stats2 = bus.stats
        assert stats2["events_published"] == 0


# ============================================================================
# ASYNC EVENT BUS LIFECYCLE TESTS
# ============================================================================


class TestAsyncEventBusLifecycle:
    """Tests for AsyncEventBus start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        """Test that start sets is_running to True."""
        bus = AsyncEventBus()
        await bus.start()
        assert bus.is_running is True
        await bus.stop()

    @pytest.mark.asyncio
    async def test_start_creates_processing_task(self):
        """Test that start creates a processing task."""
        bus = AsyncEventBus()
        await bus.start()
        assert bus._processing_task is not None
        await bus.stop()

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self):
        """Test that calling start multiple times is safe."""
        bus = AsyncEventBus()
        await bus.start()
        task1 = bus._processing_task
        await bus.start()  # Second call should be no-op
        task2 = bus._processing_task
        assert task1 is task2
        await bus.stop()

    @pytest.mark.asyncio
    async def test_stop_sets_not_running(self):
        """Test that stop sets is_running to False."""
        bus = AsyncEventBus()
        await bus.start()
        await bus.stop()
        assert bus.is_running is False

    @pytest.mark.asyncio
    async def test_stop_cancels_processing_task(self):
        """Test that stop cancels the processing task."""
        bus = AsyncEventBus()
        await bus.start()
        await bus.stop()
        assert bus._processing_task is None

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self):
        """Test that calling stop multiple times is safe."""
        bus = AsyncEventBus()
        await bus.start()
        await bus.stop()
        await bus.stop()  # Second call should be no-op
        assert bus.is_running is False

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        """Test that stop without start is safe."""
        bus = AsyncEventBus()
        await bus.stop()  # Should not raise
        assert bus.is_running is False

    @pytest.mark.asyncio
    async def test_stop_processes_remaining_events(self):
        """Test that stop processes remaining events in queue."""
        bus = AsyncEventBus()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.ENGINE_STARTED, handler)

        # Add events to queue without starting the bus
        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))
        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))

        # Mark as running briefly so stop will process events
        bus._running = True
        await bus.stop()

        assert len(received) == 2


# ============================================================================
# ASYNC EVENT BUS SUBSCRIBE TESTS
# ============================================================================


class TestAsyncEventBusSubscribe:
    """Tests for AsyncEventBus.subscribe()."""

    @pytest.mark.asyncio
    async def test_subscribe_returns_unsubscribe_function(self):
        """Test that subscribe returns an unsubscribe function."""
        bus = AsyncEventBus()

        async def handler(event: Event) -> None:
            pass

        unsubscribe = bus.subscribe(EventType.ENGINE_STARTED, handler)
        assert callable(unsubscribe)

    @pytest.mark.asyncio
    async def test_subscribe_specific_event_type(self):
        """Test subscribing to specific event type."""
        bus = AsyncEventBus()
        await bus.start()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.ENGINE_STARTED, handler)

        event = Event(type=EventType.ENGINE_STARTED)
        await bus.publish(event)
        await asyncio.wait_for(
            asyncio.sleep(0.1), timeout=1.0
        )  # Allow processing

        assert len(received) == 1
        assert received[0].id == event.id
        await bus.stop()

    @pytest.mark.asyncio
    async def test_subscribe_wildcard_receives_all_events(self):
        """Test subscribing with None receives all events."""
        bus = AsyncEventBus()
        await bus.start()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(None, handler)  # Wildcard

        await bus.emit(EventType.ENGINE_STARTED)
        await bus.emit(EventType.BROWSER_LAUNCHED)
        await bus.emit(EventType.TASK_STARTED)
        await asyncio.sleep(0.15)

        assert len(received) == 3
        await bus.stop()

    @pytest.mark.asyncio
    async def test_subscribe_multiple_handlers_same_type(self):
        """Test multiple handlers for same event type."""
        bus = AsyncEventBus()
        await bus.start()
        received1 = []
        received2 = []

        async def handler1(event: Event) -> None:
            received1.append(event)

        async def handler2(event: Event) -> None:
            received2.append(event)

        bus.subscribe(EventType.ENGINE_STARTED, handler1)
        bus.subscribe(EventType.ENGINE_STARTED, handler2)

        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)

        assert len(received1) == 1
        assert len(received2) == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_via_returned_function(self):
        """Test unsubscribing via the returned function."""
        bus = AsyncEventBus()
        await bus.start()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        unsubscribe = bus.subscribe(EventType.ENGINE_STARTED, handler)

        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)
        assert len(received) == 1

        unsubscribe()

        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)
        assert len(received) == 1  # No new events received
        await bus.stop()


# ============================================================================
# ASYNC EVENT BUS UNSUBSCRIBE TESTS
# ============================================================================


class TestAsyncEventBusUnsubscribe:
    """Tests for AsyncEventBus.unsubscribe()."""

    @pytest.mark.asyncio
    async def test_unsubscribe_specific_handler(self):
        """Test unsubscribing a specific handler."""
        bus = AsyncEventBus()
        await bus.start()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.ENGINE_STARTED, handler)
        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)
        assert len(received) == 1

        bus.unsubscribe(EventType.ENGINE_STARTED, handler)
        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)
        assert len(received) == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_wildcard_handler(self):
        """Test unsubscribing a wildcard handler."""
        bus = AsyncEventBus()
        await bus.start()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(None, handler)
        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)
        assert len(received) == 1

        bus.unsubscribe(None, handler)
        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)
        assert len(received) == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_handler_is_safe(self):
        """Test unsubscribing a handler that wasn't subscribed is safe."""
        bus = AsyncEventBus()

        async def handler(event: Event) -> None:
            pass

        # Should not raise
        bus.unsubscribe(EventType.ENGINE_STARTED, handler)
        bus.unsubscribe(None, handler)


# ============================================================================
# ASYNC EVENT BUS PUBLISH TESTS
# ============================================================================


class TestAsyncEventBusPublish:
    """Tests for AsyncEventBus.publish() and publish_sync()."""

    @pytest.mark.asyncio
    async def test_publish_increments_events_published(self):
        """Test that publish increments events_published stat."""
        bus = AsyncEventBus()
        await bus.publish(Event(type=EventType.ENGINE_STARTED))
        await bus.publish(Event(type=EventType.ENGINE_STARTED))
        assert bus.stats["events_published"] == 2

    @pytest.mark.asyncio
    async def test_publish_adds_to_queue(self):
        """Test that publish adds event to queue."""
        bus = AsyncEventBus()
        assert bus.queue_size == 0
        await bus.publish(Event(type=EventType.ENGINE_STARTED))
        assert bus.queue_size == 1

    @pytest.mark.asyncio
    async def test_publish_sync_increments_events_published(self):
        """Test that publish_sync increments events_published stat."""
        bus = AsyncEventBus()
        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))
        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))
        assert bus.stats["events_published"] == 2

    @pytest.mark.asyncio
    async def test_publish_sync_adds_to_queue(self):
        """Test that publish_sync adds event to queue."""
        bus = AsyncEventBus()
        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))
        assert bus.queue_size == 1

    @pytest.mark.asyncio
    async def test_publish_sync_drops_event_when_queue_full(self):
        """Test that publish_sync drops events when queue is full."""
        bus = AsyncEventBus(max_queue_size=2)
        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))
        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))
        assert bus.queue_size == 2
        assert bus.stats["events_published"] == 2

        # This should be dropped
        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))
        assert bus.queue_size == 2
        # events_published should NOT increment for dropped events
        assert bus.stats["events_published"] == 2


# ============================================================================
# ASYNC EVENT BUS EMIT TESTS
# ============================================================================


class TestAsyncEventBusEmit:
    """Tests for AsyncEventBus.emit() convenience method."""

    @pytest.mark.asyncio
    async def test_emit_creates_and_publishes_event(self):
        """Test that emit creates and publishes an event."""
        bus = AsyncEventBus()
        await bus.start()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.TASK_STARTED, handler)

        returned_event = await bus.emit(EventType.TASK_STARTED, data={"task": "test"})
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].id == returned_event.id
        assert received[0].type == EventType.TASK_STARTED
        assert received[0].data == {"task": "test"}
        await bus.stop()

    @pytest.mark.asyncio
    async def test_emit_returns_created_event(self):
        """Test that emit returns the created event."""
        bus = AsyncEventBus()
        event = await bus.emit(EventType.ENGINE_STARTED, data={"key": "value"}, source="test")
        assert isinstance(event, Event)
        assert event.type == EventType.ENGINE_STARTED
        assert event.data == {"key": "value"}
        assert event.source == "test"

    @pytest.mark.asyncio
    async def test_emit_with_none_data(self):
        """Test emit with None data defaults to empty dict."""
        bus = AsyncEventBus()
        event = await bus.emit(EventType.ENGINE_STARTED, data=None)
        assert event.data == {}

    @pytest.mark.asyncio
    async def test_emit_with_empty_source(self):
        """Test emit with empty source defaults to 'unknown'."""
        bus = AsyncEventBus()
        event = await bus.emit(EventType.ENGINE_STARTED, source="")
        assert event.source == "unknown"


# ============================================================================
# ASYNC EVENT BUS HANDLER EXECUTION TESTS
# ============================================================================


class TestAsyncEventBusHandlerExecution:
    """Tests for handler execution behavior."""

    @pytest.mark.asyncio
    async def test_handlers_run_concurrently(self):
        """Test that multiple handlers run concurrently."""
        bus = AsyncEventBus()
        await bus.start()
        execution_times = []

        async def slow_handler1(event: Event) -> None:
            start = time.time()
            await asyncio.sleep(0.1)
            execution_times.append(("h1", time.time() - start))

        async def slow_handler2(event: Event) -> None:
            start = time.time()
            await asyncio.sleep(0.1)
            execution_times.append(("h2", time.time() - start))

        bus.subscribe(EventType.ENGINE_STARTED, slow_handler1)
        bus.subscribe(EventType.ENGINE_STARTED, slow_handler2)

        start = time.time()
        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.15)  # Wait for handlers
        total_time = time.time() - start

        # If handlers ran concurrently, total time should be ~0.15s not ~0.35s
        assert total_time < 0.25
        assert len(execution_times) == 2
        await bus.stop()

    @pytest.mark.asyncio
    async def test_handler_error_does_not_crash_bus(self):
        """Test that handler errors don't crash the event bus."""
        bus = AsyncEventBus()
        await bus.start()
        received = []

        async def failing_handler(event: Event) -> None:
            raise ValueError("Handler failed!")

        async def working_handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.ENGINE_STARTED, failing_handler)
        bus.subscribe(EventType.ENGINE_STARTED, working_handler)

        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)

        # Working handler should still have been called
        assert len(received) == 1
        # Bus should still be running
        assert bus.is_running is True
        await bus.stop()

    @pytest.mark.asyncio
    async def test_handler_error_increments_error_stat(self):
        """Test that handler errors increment handler_errors stat."""
        bus = AsyncEventBus()
        await bus.start()

        async def failing_handler(event: Event) -> None:
            raise ValueError("Handler failed!")

        bus.subscribe(EventType.ENGINE_STARTED, failing_handler)

        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)

        assert bus.stats["handler_errors"] == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_handlers_invoked_stat_incremented(self):
        """Test that handlers_invoked stat is incremented for each handler."""
        bus = AsyncEventBus()
        await bus.start()

        async def handler1(event: Event) -> None:
            pass

        async def handler2(event: Event) -> None:
            pass

        bus.subscribe(EventType.ENGINE_STARTED, handler1)
        bus.subscribe(EventType.ENGINE_STARTED, handler2)

        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)

        assert bus.stats["handlers_invoked"] == 2
        await bus.stop()

    @pytest.mark.asyncio
    async def test_events_processed_stat_incremented(self):
        """Test that events_processed stat is incremented."""
        bus = AsyncEventBus()
        await bus.start()

        async def handler(event: Event) -> None:
            pass

        bus.subscribe(EventType.ENGINE_STARTED, handler)

        await bus.emit(EventType.ENGINE_STARTED)
        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.15)

        assert bus.stats["events_processed"] == 2
        await bus.stop()

    @pytest.mark.asyncio
    async def test_no_handlers_does_not_error(self):
        """Test that publishing with no handlers doesn't error."""
        bus = AsyncEventBus()
        await bus.start()

        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)

        assert bus.stats["events_processed"] == 1
        assert bus.stats["handlers_invoked"] == 0
        assert bus.is_running is True
        await bus.stop()


# ============================================================================
# ASYNC EVENT BUS WILDCARD HANDLER TESTS
# ============================================================================


class TestAsyncEventBusWildcardHandlers:
    """Tests for wildcard handler behavior."""

    @pytest.mark.asyncio
    async def test_wildcard_receives_all_event_types(self):
        """Test wildcard handler receives all event types."""
        bus = AsyncEventBus()
        await bus.start()
        received_types = []

        async def wildcard_handler(event: Event) -> None:
            received_types.append(event.type)

        bus.subscribe(None, wildcard_handler)

        await bus.emit(EventType.ENGINE_STARTED)
        await bus.emit(EventType.BROWSER_LAUNCHED)
        await bus.emit(EventType.TASK_STARTED)
        await bus.emit(EventType.PAGE_LOADED)
        await asyncio.sleep(0.2)

        assert EventType.ENGINE_STARTED in received_types
        assert EventType.BROWSER_LAUNCHED in received_types
        assert EventType.TASK_STARTED in received_types
        assert EventType.PAGE_LOADED in received_types
        await bus.stop()

    @pytest.mark.asyncio
    async def test_wildcard_and_specific_both_called(self):
        """Test both wildcard and specific handlers are called."""
        bus = AsyncEventBus()
        await bus.start()
        wildcard_received = []
        specific_received = []

        async def wildcard_handler(event: Event) -> None:
            wildcard_received.append(event)

        async def specific_handler(event: Event) -> None:
            specific_received.append(event)

        bus.subscribe(None, wildcard_handler)
        bus.subscribe(EventType.ENGINE_STARTED, specific_handler)

        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)

        assert len(wildcard_received) == 1
        assert len(specific_received) == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_multiple_wildcard_handlers(self):
        """Test multiple wildcard handlers all receive events."""
        bus = AsyncEventBus()
        await bus.start()
        received1 = []
        received2 = []

        async def handler1(event: Event) -> None:
            received1.append(event)

        async def handler2(event: Event) -> None:
            received2.append(event)

        bus.subscribe(None, handler1)
        bus.subscribe(None, handler2)

        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)

        assert len(received1) == 1
        assert len(received2) == 1
        await bus.stop()


# ============================================================================
# ASYNC EVENT BUS PROPERTIES TESTS
# ============================================================================


class TestAsyncEventBusProperties:
    """Tests for AsyncEventBus properties."""

    def test_queue_size_reflects_queue_state(self):
        """Test queue_size reflects actual queue state."""
        bus = AsyncEventBus()
        assert bus.queue_size == 0

        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))
        assert bus.queue_size == 1

        bus.publish_sync(Event(type=EventType.ENGINE_STARTED))
        assert bus.queue_size == 2

    @pytest.mark.asyncio
    async def test_is_running_reflects_state(self):
        """Test is_running reflects actual running state."""
        bus = AsyncEventBus()
        assert bus.is_running is False

        await bus.start()
        assert bus.is_running is True

        await bus.stop()
        assert bus.is_running is False

    def test_stats_returns_all_expected_keys(self):
        """Test stats returns all expected keys."""
        bus = AsyncEventBus()
        stats = bus.stats
        assert "events_published" in stats
        assert "events_processed" in stats
        assert "handlers_invoked" in stats
        assert "handler_errors" in stats


# ============================================================================
# ASYNC EVENT BUS INTEGRATION TESTS
# ============================================================================


class TestAsyncEventBusIntegration:
    """Integration tests for AsyncEventBus."""

    @pytest.mark.asyncio
    async def test_full_event_flow(self):
        """Test complete event flow from publish to handler."""
        bus = AsyncEventBus()
        await bus.start()
        results = []

        async def handler(event: Event) -> None:
            results.append({
                "id": event.id,
                "type": event.type,
                "data": event.data,
                "source": event.source,
            })

        bus.subscribe(EventType.TASK_COMPLETED, handler)

        await bus.emit(
            EventType.TASK_COMPLETED,
            data={"result": "success", "duration": 1.5},
            source="worker-1",
        )

        await asyncio.wait_for(asyncio.sleep(0.15), timeout=1.0)

        assert len(results) == 1
        assert results[0]["type"] == EventType.TASK_COMPLETED
        assert results[0]["data"] == {"result": "success", "duration": 1.5}
        assert results[0]["source"] == "worker-1"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_high_volume_events(self):
        """Test handling high volume of events."""
        bus = AsyncEventBus()
        await bus.start()
        received_count = [0]

        async def handler(event: Event) -> None:
            received_count[0] += 1

        bus.subscribe(EventType.ENGINE_STARTED, handler)

        # Publish 100 events
        for i in range(100):
            await bus.emit(EventType.ENGINE_STARTED, data={"index": i})

        # Wait for processing
        await asyncio.wait_for(asyncio.sleep(0.5), timeout=2.0)

        assert received_count[0] == 100
        assert bus.stats["events_published"] == 100
        assert bus.stats["events_processed"] == 100
        await bus.stop()

    @pytest.mark.asyncio
    async def test_event_ordering_preserved(self):
        """Test that events are processed in order."""
        bus = AsyncEventBus()
        await bus.start()
        received_order = []

        async def handler(event: Event) -> None:
            received_order.append(event.data["order"])

        bus.subscribe(EventType.TASK_PROGRESS, handler)

        for i in range(10):
            await bus.emit(EventType.TASK_PROGRESS, data={"order": i})

        await asyncio.sleep(0.2)

        assert received_order == list(range(10))
        await bus.stop()

    @pytest.mark.asyncio
    async def test_restart_after_stop(self):
        """Test that bus can be restarted after stop."""
        bus = AsyncEventBus()
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.ENGINE_STARTED, handler)

        # First cycle
        await bus.start()
        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)
        await bus.stop()
        assert len(received) == 1

        # Second cycle
        await bus.start()
        await bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)
        await bus.stop()
        assert len(received) == 2


# ============================================================================
# EVENT BUS FIXTURE TESTS
# ============================================================================


class TestEventBusFixture:
    """Tests using the event_bus fixture from conftest."""

    @pytest.mark.asyncio
    async def test_fixture_provides_running_bus(self, event_bus):
        """Test that event_bus fixture provides a running bus."""
        assert event_bus.is_running is True

    @pytest.mark.asyncio
    async def test_fixture_can_publish_events(self, event_bus):
        """Test that fixture bus can publish events."""
        received = []

        async def handler(event: Event) -> None:
            received.append(event)

        event_bus.subscribe(EventType.ENGINE_STARTED, handler)
        await event_bus.emit(EventType.ENGINE_STARTED)
        await asyncio.sleep(0.1)

        assert len(received) == 1
