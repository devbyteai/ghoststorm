"""Health API endpoints for watchdog system."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

logger = structlog.get_logger(__name__)

router = APIRouter()


def _get_orchestrator():
    """Get orchestrator with late import to avoid circular dependency."""
    from ghoststorm.api.app import get_orchestrator
    return get_orchestrator()


@router.get("")
async def get_health() -> dict[str, Any]:
    """
    Get overall system health.

    Returns aggregated health status from all watchdogs.
    """
    try:
        orchestrator = _get_orchestrator()
        health = await orchestrator.get_health()
        return health
    except RuntimeError:
        return {
            "level": "unknown",
            "message": "Orchestrator not initialized",
            "details": {},
        }


@router.get("/watchdogs")
async def get_watchdog_status() -> dict[str, Any]:
    """
    Get status of all individual watchdogs.

    Returns detailed state for each registered watchdog.
    """
    try:
        orchestrator = _get_orchestrator()
        states = orchestrator.watchdog_manager.get_states()
        return {
            "watchdogs": {name: state.to_dict() for name, state in states.items()},
            "count": len(states),
        }
    except RuntimeError:
        return {
            "watchdogs": {},
            "count": 0,
            "error": "Orchestrator not initialized",
        }


@router.get("/watchdogs/{name}")
async def get_watchdog_detail(name: str) -> dict[str, Any]:
    """
    Get detailed status of a specific watchdog.

    Args:
        name: Name of the watchdog (e.g., "BrowserWatchdog")
    """
    try:
        orchestrator = _get_orchestrator()
        watchdog = orchestrator.watchdog_manager.get(name)

        if not watchdog:
            raise HTTPException(
                status_code=404,
                detail=f"Watchdog not found: {name}",
            )

        # Get current health
        health = await watchdog.check_health()

        return {
            "name": name,
            "state": watchdog.state.to_dict(),
            "health": health.to_dict(),
        }
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not initialized",
        )


@router.get("/stats")
async def get_watchdog_stats() -> dict[str, Any]:
    """
    Get aggregated watchdog statistics.

    Returns overall stats including failure counts, recovery rates, etc.
    """
    try:
        orchestrator = _get_orchestrator()
        return orchestrator.watchdog_manager.get_stats()
    except RuntimeError:
        return {
            "running": False,
            "error": "Orchestrator not initialized",
        }


@router.post("/check")
async def trigger_health_check() -> dict[str, Any]:
    """
    Trigger an immediate health check across all watchdogs.

    Returns the results of the health check.
    """
    try:
        orchestrator = _get_orchestrator()
        health = await orchestrator.watchdog_manager.check_health()

        return {
            "triggered": True,
            "result": health.to_dict(),
        }
    except RuntimeError:
        return {
            "triggered": False,
            "error": "Orchestrator not initialized",
        }
