"""WebSocket manager for real-time event streaming."""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates.

    Handles:
    - Connection lifecycle (connect/disconnect)
    - Broadcasting events to all connected clients
    - Individual client messaging
    - Connection health monitoring
    """

    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        self._connections: set[WebSocket] = set()
        self._connection_lock = asyncio.Lock()
        self._running = False
        self._heartbeat_task: asyncio.Task[None] | None = None

    @property
    def connection_count(self) -> int:
        """Get current number of connected clients."""
        return len(self._connections)

    async def start(self) -> None:
        """Start the WebSocket manager."""
        if self._running:
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager and close all connections."""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task

        # Close all connections
        async with self._connection_lock:
            for websocket in list(self._connections):
                with contextlib.suppress(Exception):
                    await websocket.close()
            self._connections.clear()

        logger.info("WebSocket manager stopped")

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()

        async with self._connection_lock:
            self._connections.add(websocket)

        logger.info(
            "WebSocket client connected",
            total_connections=self.connection_count,
        )

        # Send welcome message
        await self._send_to_client(
            websocket,
            {
                "type": "connected",
                "message": "Connected to GhostStorm",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._connection_lock:
            self._connections.discard(websocket)

        logger.info(
            "WebSocket client disconnected",
            total_connections=self.connection_count,
        )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: Message dict to broadcast (will be JSON serialized)
        """
        if not self._connections:
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now(UTC).isoformat()

        data = json.dumps(message, default=str)

        async with self._connection_lock:
            disconnected = set()

            for websocket in self._connections:
                try:
                    await websocket.send_text(data)
                except Exception as e:
                    logger.debug("Failed to send to client", error=str(e))
                    disconnected.add(websocket)

            # Remove disconnected clients
            self._connections -= disconnected

    async def _send_to_client(self, websocket: WebSocket, message: dict[str, Any]) -> bool:
        """Send a message to a specific client.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            data = json.dumps(message, default=str)
            await websocket.send_text(data)
            return True
        except Exception as e:
            logger.debug("Failed to send to client", error=str(e))
            return False

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat messages to keep connections alive."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds

                if self._connections:
                    await self.broadcast(
                        {
                            "type": "heartbeat",
                            "connections": self.connection_count,
                        }
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error", error=str(e))


# Global WebSocket manager instance
ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint handler.

    Handles the full lifecycle of a WebSocket connection:
    1. Accept connection
    2. Process incoming messages
    3. Handle disconnection
    """
    await ws_manager.connect(websocket)

    try:
        while True:
            # Wait for messages from client (handle both text and binary)
            message = await websocket.receive()

            if message["type"] == "websocket.receive":
                if "text" in message:
                    data = message["text"]
                    try:
                        parsed = json.loads(data)
                        await _handle_client_message(websocket, parsed)
                    except json.JSONDecodeError:
                        await ws_manager._send_to_client(
                            websocket,
                            {
                                "type": "error",
                                "message": "Invalid JSON",
                            },
                        )
                elif "bytes" in message:
                    # Binary messages are not supported
                    await ws_manager._send_to_client(
                        websocket,
                        {
                            "type": "error",
                            "message": "Binary messages not supported",
                        },
                    )
            elif message["type"] == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
    finally:
        await ws_manager.disconnect(websocket)


async def _handle_client_message(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Handle incoming messages from WebSocket clients.

    Supported message types:
    - ping: Respond with pong
    - subscribe: Subscribe to specific event types
    - unsubscribe: Unsubscribe from event types
    """
    msg_type = message.get("type", "")

    if msg_type == "ping":
        await ws_manager._send_to_client(
            websocket,
            {
                "type": "pong",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    elif msg_type == "subscribe":
        # Future: Handle event type subscriptions
        await ws_manager._send_to_client(
            websocket,
            {
                "type": "subscribed",
                "events": message.get("events", ["*"]),
            },
        )

    elif msg_type == "get_stats":
        # Return current stats
        try:
            from ghoststorm.api.routes.metrics import get_metrics

            metrics = await get_metrics()
            await ws_manager._send_to_client(
                websocket,
                {
                    "type": "stats",
                    "data": metrics.model_dump(),
                },
            )
        except Exception as e:
            await ws_manager._send_to_client(
                websocket,
                {
                    "type": "error",
                    "message": str(e),
                },
            )

    else:
        await ws_manager._send_to_client(
            websocket,
            {
                "type": "error",
                "message": f"Unknown message type: {msg_type}",
            },
        )
