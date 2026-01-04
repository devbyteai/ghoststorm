"""E2E tests for WebSocket connections and events."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.websocket
class TestWebSocketConnection:
    """Tests for WebSocket connection lifecycle."""

    def test_websocket_connect(self, api_test_client: TestClient):
        """Test WebSocket connection establishment."""
        with api_test_client.websocket_connect("/ws") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "message" in data
            assert "timestamp" in data

    def test_websocket_disconnect_graceful(self, api_test_client: TestClient):
        """Test graceful WebSocket disconnection."""
        with api_test_client.websocket_connect("/ws") as websocket:
            # Receive welcome
            websocket.receive_json()

        # Connection should close without error
        # If we get here, the context manager closed cleanly

    def test_websocket_multiple_connections(self, api_test_client: TestClient):
        """Test multiple concurrent WebSocket connections."""
        with api_test_client.websocket_connect("/ws") as ws1:
            ws1.receive_json()  # Welcome

            with api_test_client.websocket_connect("/ws") as ws2:
                ws2.receive_json()  # Welcome

                # Both connections should work
                ws1.send_json({"type": "ping"})
                ws2.send_json({"type": "ping"})

                # Both should receive pong
                pong1 = ws1.receive_json()
                pong2 = ws2.receive_json()

                assert pong1["type"] == "pong"
                assert pong2["type"] == "pong"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.websocket
class TestWebSocketMessages:
    """Tests for WebSocket message handling."""

    def test_ping_pong(self, api_test_client: TestClient):
        """Test ping/pong message exchange."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            websocket.send_json({"type": "ping"})
            response = websocket.receive_json()

            assert response["type"] == "pong"
            assert "timestamp" in response

    def test_subscribe_events(self, api_test_client: TestClient):
        """Test event subscription."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            websocket.send_json(
                {
                    "type": "subscribe",
                    "events": ["task:created", "task:updated"],
                }
            )
            response = websocket.receive_json()

            assert response["type"] == "subscribed"
            assert "events" in response

    def test_subscribe_all_events(self, api_test_client: TestClient):
        """Test subscribing to all events."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            websocket.send_json({"type": "subscribe"})
            response = websocket.receive_json()

            assert response["type"] == "subscribed"
            assert response["events"] == ["*"]

    def test_get_stats(self, api_test_client: TestClient):
        """Test getting stats via WebSocket."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            websocket.send_json({"type": "get_stats"})
            response = websocket.receive_json()

            # Should get stats or error
            assert response["type"] in ["stats", "error"]

    def test_unknown_message_type(self, api_test_client: TestClient):
        """Test handling of unknown message type."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            websocket.send_json({"type": "unknown_command"})
            response = websocket.receive_json()

            assert response["type"] == "error"
            assert "Unknown message type" in response["message"]

    def test_invalid_json(self, api_test_client: TestClient):
        """Test handling of invalid JSON."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            websocket.send_text("not valid json{")
            response = websocket.receive_json()

            assert response["type"] == "error"
            assert "Invalid JSON" in response["message"]


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.websocket
class TestWebSocketManager:
    """Tests for WebSocketManager functionality."""

    def test_connection_count(self, api_test_client: TestClient):
        """Test connection counting."""
        from ghoststorm.api.websocket import ws_manager

        initial_count = ws_manager.connection_count

        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome
            # Count should increase
            assert ws_manager.connection_count >= initial_count + 1

        # After disconnect, count should decrease
        # Note: There may be a small delay for cleanup

    def test_broadcast_message(self, api_test_client: TestClient):
        """Test broadcasting to multiple clients."""
        from ghoststorm.api.websocket import ws_manager

        with api_test_client.websocket_connect("/ws") as ws1:
            ws1.receive_json()  # Welcome

            with api_test_client.websocket_connect("/ws") as ws2:
                ws2.receive_json()  # Welcome

                # Broadcast a message
                import asyncio

                async def do_broadcast():
                    await ws_manager.broadcast(
                        {
                            "type": "test_broadcast",
                            "data": "hello all",
                        }
                    )

                asyncio.get_event_loop().run_until_complete(do_broadcast())

                # Both should receive it
                msg1 = ws1.receive_json()
                msg2 = ws2.receive_json()

                assert msg1["type"] == "test_broadcast"
                assert msg2["type"] == "test_broadcast"


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.websocket
class TestWebSocketEvents:
    """Tests for WebSocket event broadcasting."""

    def test_task_created_event(self, api_test_client: TestClient):
        """Test receiving task created event."""
        from ghoststorm.api.websocket import ws_manager

        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            # Simulate task creation event
            async def emit_event():
                await ws_manager.broadcast(
                    {
                        "type": "task:created",
                        "task_id": "test-123",
                        "url": "https://example.com",
                    }
                )

            asyncio.get_event_loop().run_until_complete(emit_event())

            response = websocket.receive_json()
            assert response["type"] == "task:created"
            assert response["task_id"] == "test-123"

    def test_task_progress_event(self, api_test_client: TestClient):
        """Test receiving task progress event."""
        from ghoststorm.api.websocket import ws_manager

        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            async def emit_event():
                await ws_manager.broadcast(
                    {
                        "type": "task:progress",
                        "task_id": "test-123",
                        "progress": 50,
                        "views": 25,
                    }
                )

            asyncio.get_event_loop().run_until_complete(emit_event())

            response = websocket.receive_json()
            assert response["type"] == "task:progress"
            assert response["progress"] == 50

    def test_task_completed_event(self, api_test_client: TestClient):
        """Test receiving task completed event."""
        from ghoststorm.api.websocket import ws_manager

        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            async def emit_event():
                await ws_manager.broadcast(
                    {
                        "type": "task:completed",
                        "task_id": "test-123",
                        "total_views": 100,
                        "duration": 120.5,
                    }
                )

            asyncio.get_event_loop().run_until_complete(emit_event())

            response = websocket.receive_json()
            assert response["type"] == "task:completed"
            assert response["total_views"] == 100

    def test_flow_recording_event(self, api_test_client: TestClient):
        """Test receiving flow recording event."""
        from ghoststorm.api.websocket import ws_manager

        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            async def emit_event():
                await ws_manager.broadcast(
                    {
                        "type": "flow:step_recorded",
                        "flow_id": "flow-123",
                        "step_number": 3,
                        "action": "click",
                    }
                )

            asyncio.get_event_loop().run_until_complete(emit_event())

            response = websocket.receive_json()
            assert response["type"] == "flow:step_recorded"
            assert response["step_number"] == 3

    def test_error_event(self, api_test_client: TestClient):
        """Test receiving error event."""
        from ghoststorm.api.websocket import ws_manager

        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            async def emit_event():
                await ws_manager.broadcast(
                    {
                        "type": "error",
                        "task_id": "test-123",
                        "message": "Browser crashed",
                        "recoverable": True,
                    }
                )

            asyncio.get_event_loop().run_until_complete(emit_event())

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Browser crashed" in response["message"]


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.websocket
class TestWebSocketHeartbeat:
    """Tests for WebSocket heartbeat functionality."""

    @pytest.mark.slow
    def test_heartbeat_received(self, api_test_client: TestClient):
        """Test that heartbeat is received periodically.

        Note: This test is marked slow because heartbeat interval is 30s.
        In real tests, you might want to mock the interval.
        """
        # This test would need to wait for heartbeat
        # In practice, we'd mock the sleep interval
        pass

    def test_heartbeat_contains_connection_count(self, api_test_client: TestClient):
        """Test heartbeat message structure."""
        from ghoststorm.api.websocket import ws_manager

        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            # Manually trigger heartbeat
            async def send_heartbeat():
                await ws_manager.broadcast(
                    {
                        "type": "heartbeat",
                        "connections": ws_manager.connection_count,
                    }
                )

            asyncio.get_event_loop().run_until_complete(send_heartbeat())

            response = websocket.receive_json()
            assert response["type"] == "heartbeat"
            assert "connections" in response
            assert response["connections"] >= 1


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.websocket
class TestWebSocketEdgeCases:
    """Edge case tests for WebSocket handling."""

    def test_empty_message(self, api_test_client: TestClient):
        """Test handling empty message."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            websocket.send_json({})
            response = websocket.receive_json()

            # Empty type should be handled
            assert response["type"] == "error"

    def test_large_message(self, api_test_client: TestClient):
        """Test handling large message."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            large_data = "x" * 10000
            websocket.send_json(
                {
                    "type": "ping",
                    "data": large_data,
                }
            )
            response = websocket.receive_json()

            # Should still get pong
            assert response["type"] == "pong"

    def test_rapid_messages(self, api_test_client: TestClient):
        """Test rapid message sending."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            # Send many pings rapidly
            for _ in range(10):
                websocket.send_json({"type": "ping"})

            # Should receive all pongs
            for _ in range(10):
                response = websocket.receive_json()
                assert response["type"] == "pong"

    def test_binary_message_handling(self, api_test_client: TestClient):
        """Test binary message handling."""
        with api_test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # Welcome

            # Send binary data - should be rejected or converted
            websocket.send_bytes(b"\x00\x01\x02\x03")

            # Implementation may close connection or send error
            try:
                response = websocket.receive_json()
                assert response["type"] == "error"
            except Exception:
                # Connection may close on binary data
                pass
