"""FastAPI application for GhostStorm Web UI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ghoststorm.api.routes import (
    algorithms,
    assistant,
    config,
    data,
    dom,
    engine,
    flows,
    health,
    llm,
    metrics,
    proxies,
    tasks,
    zefoy,
)
from ghoststorm.api.websocket import ws_manager

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ghoststorm.core.engine.orchestrator import Orchestrator

logger = structlog.get_logger(__name__)

# Global orchestrator reference
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized. Call create_app() first.")
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    global _orchestrator

    logger.info("Starting GhostStorm API")

    # Start WebSocket manager
    await ws_manager.start()

    # Start orchestrator if available
    if _orchestrator is not None:
        try:
            await _orchestrator.start()

            # Subscribe to events for WebSocket broadcast
            async def broadcast_event(event: Any) -> None:
                await ws_manager.broadcast(
                    {
                        "type": event.event_type.value if hasattr(event, "event_type") else "event",
                        "data": event.data if hasattr(event, "data") else {},
                        "timestamp": event.timestamp.isoformat()
                        if hasattr(event, "timestamp")
                        else None,
                    }
                )

            _orchestrator.event_bus.subscribe("*", broadcast_event)
            logger.info("Orchestrator started and event subscription active")
        except Exception as e:
            logger.error("Failed to start orchestrator", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down GhostStorm API")

    if _orchestrator is not None:
        await _orchestrator.stop()

    await ws_manager.stop()


def create_app(orchestrator: Orchestrator | None = None) -> FastAPI:
    """Create FastAPI application.

    Args:
        orchestrator: Optional orchestrator instance. If not provided,
                     the API will run in standalone mode with limited functionality.

    Returns:
        Configured FastAPI application.
    """
    global _orchestrator
    _orchestrator = orchestrator

    app = FastAPI(
        title="GhostStorm",
        description="Traffic automation control panel",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
    app.include_router(config.router, prefix="/api/config", tags=["config"])
    app.include_router(metrics.router, prefix="/api", tags=["metrics"])
    app.include_router(proxies.router, prefix="/api/proxies", tags=["proxies"])
    app.include_router(data.router, prefix="/api/data", tags=["data"])
    app.include_router(zefoy.router, prefix="/api/zefoy", tags=["zefoy"])
    app.include_router(algorithms.router, prefix="/api/algorithms", tags=["algorithms"])
    app.include_router(engine.router, prefix="/api/engine", tags=["engine"])
    app.include_router(health.router, prefix="/api/watchdog", tags=["watchdog"])
    app.include_router(dom.router, prefix="/api/dom", tags=["dom"])
    app.include_router(llm.router, tags=["llm"])
    app.include_router(assistant.router, tags=["assistant"])
    app.include_router(flows.router, tags=["flows"])

    # WebSocket endpoint
    from ghoststorm.api.websocket import websocket_endpoint

    app.add_api_websocket_route("/ws/events", websocket_endpoint)

    # Static files for frontend
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Root endpoint serves frontend
    @app.get("/", include_in_schema=False)
    async def root() -> FileResponse:
        """Serve the frontend control panel."""
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return FileResponse(str(static_dir / "index.html"))

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    logger.info("FastAPI app created", has_orchestrator=orchestrator is not None)
    return app
