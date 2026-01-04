"""Comprehensive tests for WebSocketManager."""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghoststorm.api.websocket import (
    WebSocketManager,
    _handle_client_message,
    websocket_endpoint,
    ws_manager,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def ws_manager_instance() -> WebSocketManager:
    """Create a fresh WebSocketManager instance for each test."""
    return WebSocketManager()


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket that records all calls."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    ws.receive_text = AsyncMock()
    return ws


@pytest.fixture
def mock_websocket_factory():
    """Factory to create multiple mock WebSockets."""

    def _create():
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        ws.receive_text = AsyncMock()
        return ws

    return _create


# ============================================================================
# TESTS: __init__
# ============================================================================


class TestWebSocketManagerInit:
    """Tests for WebSocketManager initialization."""

    def test_init_empty_connections(self, ws_manager_instance: WebSocketManager) -> None:
        """Test that manager initializes with empty connections set."""
        assert len(ws_manager_instance._connections) == 0
        assert isinstance(ws_manager_instance._connections, set)

    def test_init_not_running(self, ws_manager_instance: WebSocketManager) -> None:
        """Test that manager initializes with _running = False."""
        assert ws_manager_instance._running is False

    def test_init_no_heartbeat_task(self, ws_manager_instance: WebSocketManager) -> None:
        """Test that manager initializes with no heartbeat task."""
        assert ws_manager_instance._heartbeat_task is None

    def test_init_has_connection_lock(self, ws_manager_instance: WebSocketManager) -> None:
        """Test that manager initializes with an asyncio Lock."""
        assert isinstance(ws_manager_instance._connection_lock, asyncio.Lock)


# ============================================================================
# TESTS: connection_count property
# ============================================================================


class TestConnectionCount:
    """Tests for connection_count property."""

    def test_connection_count_empty(self, ws_manager_instance: WebSocketManager) -> None:
        """Test connection count is 0 when no connections."""
        assert ws_manager_instance.connection_count == 0

    def test_connection_count_single(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test connection count returns 1 after adding one connection."""
        ws_manager_instance._connections.add(mock_websocket)
        assert ws_manager_instance.connection_count == 1

    def test_connection_count_multiple(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket_factory,
    ) -> None:
        """Test connection count returns correct value with multiple connections."""
        for _ in range(5):
            ws_manager_instance._connections.add(mock_websocket_factory())
        assert ws_manager_instance.connection_count == 5


# ============================================================================
# TESTS: start()
# ============================================================================


class TestStart:
    """Tests for WebSocketManager.start()."""

    @pytest.mark.asyncio
    async def test_start_sets_running_true(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that start() sets _running to True."""
        with patch.object(ws_manager_instance, "_heartbeat_loop", new_callable=AsyncMock):
            await ws_manager_instance.start()
            assert ws_manager_instance._running is True
            # Cleanup
            ws_manager_instance._running = False
            if ws_manager_instance._heartbeat_task:
                ws_manager_instance._heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await ws_manager_instance._heartbeat_task

    @pytest.mark.asyncio
    async def test_start_creates_heartbeat_task(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that start() creates a heartbeat task."""
        with patch.object(ws_manager_instance, "_heartbeat_loop", new_callable=AsyncMock):
            await ws_manager_instance.start()
            assert ws_manager_instance._heartbeat_task is not None
            assert isinstance(ws_manager_instance._heartbeat_task, asyncio.Task)
            # Cleanup
            ws_manager_instance._running = False
            ws_manager_instance._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await ws_manager_instance._heartbeat_task

    @pytest.mark.asyncio
    async def test_start_idempotent(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that calling start() twice doesn't create duplicate tasks."""
        with patch.object(ws_manager_instance, "_heartbeat_loop", new_callable=AsyncMock):
            await ws_manager_instance.start()
            first_task = ws_manager_instance._heartbeat_task
            await ws_manager_instance.start()
            assert ws_manager_instance._heartbeat_task is first_task
            # Cleanup
            ws_manager_instance._running = False
            if ws_manager_instance._heartbeat_task:
                ws_manager_instance._heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await ws_manager_instance._heartbeat_task

    @pytest.mark.asyncio
    async def test_start_does_not_start_if_already_running(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that start() returns early if already running."""
        ws_manager_instance._running = True
        original_task = ws_manager_instance._heartbeat_task
        await ws_manager_instance.start()
        # Task should not have been created
        assert ws_manager_instance._heartbeat_task is original_task


# ============================================================================
# TESTS: stop()
# ============================================================================


class TestStop:
    """Tests for WebSocketManager.stop()."""

    @pytest.mark.asyncio
    async def test_stop_sets_running_false(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that stop() sets _running to False."""
        ws_manager_instance._running = True
        await ws_manager_instance.stop()
        assert ws_manager_instance._running is False

    @pytest.mark.asyncio
    async def test_stop_cancels_heartbeat_task(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that stop() cancels the heartbeat task."""
        with patch.object(ws_manager_instance, "_heartbeat_loop", new_callable=AsyncMock):
            await ws_manager_instance.start()
            task = ws_manager_instance._heartbeat_task
            await ws_manager_instance.stop()
            assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_stop_clears_connections(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket_factory,
    ) -> None:
        """Test that stop() clears all connections."""
        for _ in range(3):
            ws = mock_websocket_factory()
            ws_manager_instance._connections.add(ws)

        await ws_manager_instance.stop()
        assert len(ws_manager_instance._connections) == 0

    @pytest.mark.asyncio
    async def test_stop_closes_all_websockets(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket_factory,
    ) -> None:
        """Test that stop() calls close() on all connected WebSockets."""
        websockets = [mock_websocket_factory() for _ in range(3)]
        for ws in websockets:
            ws_manager_instance._connections.add(ws)

        await ws_manager_instance.stop()

        for ws in websockets:
            ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_handles_close_exception(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket_factory,
    ) -> None:
        """Test that stop() handles exceptions when closing WebSockets."""
        ws1 = mock_websocket_factory()
        ws2 = mock_websocket_factory()
        ws1.close = AsyncMock(side_effect=Exception("Close failed"))
        ws_manager_instance._connections.add(ws1)
        ws_manager_instance._connections.add(ws2)

        # Should not raise
        await ws_manager_instance.stop()
        assert len(ws_manager_instance._connections) == 0

    @pytest.mark.asyncio
    async def test_stop_without_heartbeat_task(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that stop() works even if heartbeat task is None."""
        assert ws_manager_instance._heartbeat_task is None
        # Should not raise
        await ws_manager_instance.stop()
        assert ws_manager_instance._running is False


# ============================================================================
# TESTS: connect()
# ============================================================================


class TestConnect:
    """Tests for WebSocketManager.connect()."""

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that connect() calls websocket.accept()."""
        await ws_manager_instance.connect(mock_websocket)
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_adds_to_connections(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that connect() adds websocket to _connections set."""
        await ws_manager_instance.connect(mock_websocket)
        assert mock_websocket in ws_manager_instance._connections

    @pytest.mark.asyncio
    async def test_connect_sends_welcome_message(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that connect() sends a welcome message."""
        await ws_manager_instance.connect(mock_websocket)
        mock_websocket.send_text.assert_called_once()
        sent_data = mock_websocket.send_text.call_args[0][0]
        message = json.loads(sent_data)
        assert message["type"] == "connected"
        assert message["message"] == "Connected to GhostStorm"
        assert "timestamp" in message

    @pytest.mark.asyncio
    async def test_connect_increments_connection_count(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket_factory,
    ) -> None:
        """Test that connection count increases after connect."""
        assert ws_manager_instance.connection_count == 0
        await ws_manager_instance.connect(mock_websocket_factory())
        assert ws_manager_instance.connection_count == 1
        await ws_manager_instance.connect(mock_websocket_factory())
        assert ws_manager_instance.connection_count == 2

    @pytest.mark.asyncio
    async def test_connect_multiple_websockets(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket_factory,
    ) -> None:
        """Test connecting multiple WebSockets."""
        websockets = [mock_websocket_factory() for _ in range(5)]
        for ws in websockets:
            await ws_manager_instance.connect(ws)

        assert ws_manager_instance.connection_count == 5
        for ws in websockets:
            assert ws in ws_manager_instance._connections


# ============================================================================
# TESTS: disconnect()
# ============================================================================


class TestDisconnect:
    """Tests for WebSocketManager.disconnect()."""

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_connections(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that disconnect() removes websocket from _connections set."""
        ws_manager_instance._connections.add(mock_websocket)
        await ws_manager_instance.disconnect(mock_websocket)
        assert mock_websocket not in ws_manager_instance._connections

    @pytest.mark.asyncio
    async def test_disconnect_decrements_connection_count(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket_factory,
    ) -> None:
        """Test that connection count decreases after disconnect."""
        ws1 = mock_websocket_factory()
        ws2 = mock_websocket_factory()
        ws_manager_instance._connections.add(ws1)
        ws_manager_instance._connections.add(ws2)

        assert ws_manager_instance.connection_count == 2
        await ws_manager_instance.disconnect(ws1)
        assert ws_manager_instance.connection_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_websocket(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that disconnect() handles non-existent WebSocket gracefully."""
        # Should not raise
        await ws_manager_instance.disconnect(mock_websocket)
        assert ws_manager_instance.connection_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_multiple_times(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that disconnect() can be called multiple times safely."""
        ws_manager_instance._connections.add(mock_websocket)
        await ws_manager_instance.disconnect(mock_websocket)
        await ws_manager_instance.disconnect(mock_websocket)
        assert mock_websocket not in ws_manager_instance._connections


# ============================================================================
# TESTS: broadcast()
# ============================================================================


class TestBroadcast:
    """Tests for WebSocketManager.broadcast()."""

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket_factory,
    ) -> None:
        """Test that broadcast() sends message to all connected clients."""
        websockets = [mock_websocket_factory() for _ in range(3)]
        for ws in websockets:
            ws_manager_instance._connections.add(ws)

        message = {"type": "test", "data": "hello"}
        await ws_manager_instance.broadcast(message)

        for ws in websockets:
            ws.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_adds_timestamp(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that broadcast() adds timestamp if not present."""
        ws_manager_instance._connections.add(mock_websocket)

        message = {"type": "test", "data": "hello"}
        await ws_manager_instance.broadcast(message)

        sent_data = mock_websocket.send_text.call_args[0][0]
        sent_message = json.loads(sent_data)
        assert "timestamp" in sent_message

    @pytest.mark.asyncio
    async def test_broadcast_preserves_existing_timestamp(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that broadcast() preserves existing timestamp."""
        ws_manager_instance._connections.add(mock_websocket)

        custom_timestamp = "2025-01-01T00:00:00Z"
        message = {"type": "test", "timestamp": custom_timestamp}
        await ws_manager_instance.broadcast(message)

        sent_data = mock_websocket.send_text.call_args[0][0]
        sent_message = json.loads(sent_data)
        assert sent_message["timestamp"] == custom_timestamp

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected_clients(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket_factory,
    ) -> None:
        """Test that broadcast() removes clients that fail to receive."""
        ws_good = mock_websocket_factory()
        ws_bad = mock_websocket_factory()
        ws_bad.send_text = AsyncMock(side_effect=Exception("Connection lost"))

        ws_manager_instance._connections.add(ws_good)
        ws_manager_instance._connections.add(ws_bad)

        await ws_manager_instance.broadcast({"type": "test"})

        assert ws_good in ws_manager_instance._connections
        assert ws_bad not in ws_manager_instance._connections

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that broadcast() returns early with no connections."""
        # Should not raise
        await ws_manager_instance.broadcast({"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_serializes_message_to_json(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that broadcast() serializes message to JSON."""
        ws_manager_instance._connections.add(mock_websocket)

        message = {"type": "test", "number": 42, "nested": {"key": "value"}}
        await ws_manager_instance.broadcast(message)

        sent_data = mock_websocket.send_text.call_args[0][0]
        parsed = json.loads(sent_data)
        assert parsed["type"] == "test"
        assert parsed["number"] == 42
        assert parsed["nested"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_broadcast_handles_non_serializable_with_default_str(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that broadcast() uses default=str for non-serializable objects."""
        ws_manager_instance._connections.add(mock_websocket)

        now = datetime.now(UTC)
        message = {"type": "test", "datetime": now}
        await ws_manager_instance.broadcast(message)

        sent_data = mock_websocket.send_text.call_args[0][0]
        parsed = json.loads(sent_data)
        assert parsed["datetime"] == str(now)


# ============================================================================
# TESTS: _send_to_client()
# ============================================================================


class TestSendToClient:
    """Tests for WebSocketManager._send_to_client()."""

    @pytest.mark.asyncio
    async def test_send_to_client_returns_true_on_success(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that _send_to_client() returns True on success."""
        result = await ws_manager_instance._send_to_client(mock_websocket, {"type": "test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_send_to_client_returns_false_on_failure(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that _send_to_client() returns False on failure."""
        mock_websocket.send_text = AsyncMock(side_effect=Exception("Send failed"))
        result = await ws_manager_instance._send_to_client(mock_websocket, {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_client_serializes_to_json(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that _send_to_client() serializes message to JSON."""
        message = {"type": "test", "data": [1, 2, 3]}
        await ws_manager_instance._send_to_client(mock_websocket, message)

        sent_data = mock_websocket.send_text.call_args[0][0]
        parsed = json.loads(sent_data)
        assert parsed == message

    @pytest.mark.asyncio
    async def test_send_to_client_calls_send_text(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that _send_to_client() calls websocket.send_text()."""
        await ws_manager_instance._send_to_client(mock_websocket, {"type": "test"})
        mock_websocket.send_text.assert_called_once()


# ============================================================================
# TESTS: _heartbeat_loop()
# ============================================================================


class TestHeartbeatLoop:
    """Tests for WebSocketManager._heartbeat_loop()."""

    @pytest.mark.asyncio
    async def test_heartbeat_loop_sends_heartbeat_when_running(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that heartbeat loop sends heartbeat messages when running."""
        ws_manager_instance._connections.add(mock_websocket)
        ws_manager_instance._running = True

        with patch("ghoststorm.api.websocket.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Make sleep raise after first call to stop the loop
            call_count = 0

            async def sleep_side_effect(seconds):
                nonlocal call_count
                call_count += 1
                if call_count > 1:
                    ws_manager_instance._running = False

            mock_sleep.side_effect = sleep_side_effect

            await ws_manager_instance._heartbeat_loop()

            # Check heartbeat was sent
            assert mock_websocket.send_text.called

    @pytest.mark.asyncio
    async def test_heartbeat_loop_sleeps_30_seconds(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that heartbeat loop sleeps for 30 seconds."""
        ws_manager_instance._running = True

        with patch("ghoststorm.api.websocket.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            async def stop_after_first(seconds):
                ws_manager_instance._running = False

            mock_sleep.side_effect = stop_after_first

            await ws_manager_instance._heartbeat_loop()

            mock_sleep.assert_called_with(30)

    @pytest.mark.asyncio
    async def test_heartbeat_loop_stops_when_not_running(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that heartbeat loop stops when _running is False."""
        ws_manager_instance._running = False

        # Should return immediately
        await ws_manager_instance._heartbeat_loop()

    @pytest.mark.asyncio
    async def test_heartbeat_loop_handles_cancelled_error(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that heartbeat loop handles CancelledError gracefully."""
        ws_manager_instance._running = True

        with patch("ghoststorm.api.websocket.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError()

            # Should not raise
            await ws_manager_instance._heartbeat_loop()

    @pytest.mark.asyncio
    async def test_heartbeat_loop_no_broadcast_without_connections(
        self,
        ws_manager_instance: WebSocketManager,
    ) -> None:
        """Test that heartbeat loop doesn't broadcast without connections."""
        ws_manager_instance._running = True

        with patch("ghoststorm.api.websocket.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch.object(
                ws_manager_instance, "broadcast", new_callable=AsyncMock
            ) as mock_broadcast:

                async def stop_after_first(seconds):
                    ws_manager_instance._running = False

                mock_sleep.side_effect = stop_after_first

                await ws_manager_instance._heartbeat_loop()

                mock_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_heartbeat_message_format(
        self,
        ws_manager_instance: WebSocketManager,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that heartbeat message has correct format."""
        ws_manager_instance._connections.add(mock_websocket)
        ws_manager_instance._running = True

        with patch("ghoststorm.api.websocket.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            async def stop_after_first(seconds):
                ws_manager_instance._running = False

            mock_sleep.side_effect = stop_after_first

            await ws_manager_instance._heartbeat_loop()

            sent_data = mock_websocket.send_text.call_args[0][0]
            message = json.loads(sent_data)
            assert message["type"] == "heartbeat"
            assert "connections" in message
            assert "timestamp" in message


# ============================================================================
# TESTS: websocket_endpoint()
# ============================================================================


class TestWebsocketEndpoint:
    """Tests for websocket_endpoint function."""

    @pytest.mark.asyncio
    async def test_endpoint_connects_websocket(
        self,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that endpoint connects the websocket."""
        from fastapi import WebSocketDisconnect

        mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        with patch.object(ws_manager, "connect", new_callable=AsyncMock) as mock_connect:
            with patch.object(ws_manager, "disconnect", new_callable=AsyncMock):
                await websocket_endpoint(mock_websocket)
                mock_connect.assert_called_once_with(mock_websocket)

    @pytest.mark.asyncio
    async def test_endpoint_disconnects_on_websocket_disconnect(
        self,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that endpoint disconnects on WebSocketDisconnect."""
        from fastapi import WebSocketDisconnect

        mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        with patch.object(ws_manager, "connect", new_callable=AsyncMock):
            with patch.object(ws_manager, "disconnect", new_callable=AsyncMock) as mock_disconnect:
                await websocket_endpoint(mock_websocket)
                mock_disconnect.assert_called_once_with(mock_websocket)

    @pytest.mark.asyncio
    async def test_endpoint_disconnects_on_exception(
        self,
        mock_websocket: MagicMock,
    ) -> None:
        """Test that endpoint disconnects on general exception."""
        mock_websocket.receive_text = AsyncMock(side_effect=Exception("Error"))

        with patch.object(ws_manager, "connect", new_callable=AsyncMock):
            with patch.object(ws_manager, "disconnect", new_callable=AsyncMock) as mock_disconnect:
                await websocket_endpoint(mock_websocket)
                mock_disconnect.assert_called_once_with(mock_websocket)


# ============================================================================
# TESTS: _handle_client_message()
# ============================================================================


class TestHandleClientMessage:
    """Tests for _handle_client_message function."""

    @pytest.mark.asyncio
    async def test_handle_ping_message(
        self,
        mock_websocket: MagicMock,
    ) -> None:
        """Test handling of ping message."""
        with patch.object(ws_manager, "_send_to_client", new_callable=AsyncMock) as mock_send:
            await _handle_client_message(mock_websocket, {"type": "ping"})

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert call_args[0] == mock_websocket
            assert call_args[1]["type"] == "pong"
            assert "timestamp" in call_args[1]

    @pytest.mark.asyncio
    async def test_handle_subscribe_message(
        self,
        mock_websocket: MagicMock,
    ) -> None:
        """Test handling of subscribe message."""
        with patch.object(ws_manager, "_send_to_client", new_callable=AsyncMock) as mock_send:
            await _handle_client_message(
                mock_websocket, {"type": "subscribe", "events": ["visit", "error"]}
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert call_args[1]["type"] == "subscribed"
            assert call_args[1]["events"] == ["visit", "error"]

    @pytest.mark.asyncio
    async def test_handle_subscribe_default_events(
        self,
        mock_websocket: MagicMock,
    ) -> None:
        """Test handling of subscribe message with default events."""
        with patch.object(ws_manager, "_send_to_client", new_callable=AsyncMock) as mock_send:
            await _handle_client_message(mock_websocket, {"type": "subscribe"})

            call_args = mock_send.call_args[0]
            assert call_args[1]["events"] == ["*"]

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(
        self,
        mock_websocket: MagicMock,
    ) -> None:
        """Test handling of unknown message type."""
        with patch.object(ws_manager, "_send_to_client", new_callable=AsyncMock) as mock_send:
            await _handle_client_message(mock_websocket, {"type": "unknown_type"})

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert call_args[1]["type"] == "error"
            assert "Unknown message type" in call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_handle_message_without_type(
        self,
        mock_websocket: MagicMock,
    ) -> None:
        """Test handling of message without type field."""
        with patch.object(ws_manager, "_send_to_client", new_callable=AsyncMock) as mock_send:
            await _handle_client_message(mock_websocket, {"data": "test"})

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert call_args[1]["type"] == "error"


# ============================================================================
# TESTS: Global ws_manager instance
# ============================================================================


class TestGlobalWsManager:
    """Tests for the global ws_manager instance."""

    def test_global_instance_exists(self) -> None:
        """Test that global ws_manager instance exists."""
        assert ws_manager is not None
        assert isinstance(ws_manager, WebSocketManager)

    def test_global_instance_is_singleton(self) -> None:
        """Test that importing returns the same instance."""
        from ghoststorm.api.websocket import ws_manager as ws_manager_2

        assert ws_manager is ws_manager_2
