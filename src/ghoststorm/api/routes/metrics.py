"""Metrics and health API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter

from ghoststorm.api.schemas import MetricsResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


def _get_orchestrator_stats() -> dict[str, Any]:
    """Get stats from orchestrator if available."""
    try:
        from ghoststorm.api.app import get_orchestrator

        orchestrator = get_orchestrator()

        return {
            "uptime_seconds": orchestrator.uptime,
            "is_running": orchestrator.is_running,
            "workers_active": (
                orchestrator.worker_pool.active_workers
                if hasattr(orchestrator, "worker_pool")
                else 0
            ),
            "workers_total": (
                orchestrator.worker_pool.max_workers if hasattr(orchestrator, "worker_pool") else 0
            ),
        }
    except (RuntimeError, AttributeError):
        return {
            "uptime_seconds": None,
            "is_running": False,
            "workers_active": 0,
            "workers_total": 0,
        }


def _get_task_stats() -> dict[str, int]:
    """Get task statistics from the tasks module."""
    try:
        from ghoststorm.api.routes.tasks import _tasks

        tasks = list(_tasks.values())
        return {
            "tasks_pending": sum(1 for t in tasks if t["status"] == "pending"),
            "tasks_running": sum(1 for t in tasks if t["status"] == "running"),
            "tasks_completed": sum(1 for t in tasks if t["status"] == "completed"),
            "tasks_failed": sum(1 for t in tasks if t["status"] == "failed"),
        }
    except ImportError:
        return {
            "tasks_pending": 0,
            "tasks_running": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
        }


def _get_proxy_stats() -> dict[str, int]:
    """Get proxy statistics."""
    try:
        from ghoststorm.api.app import get_orchestrator

        orchestrator = get_orchestrator()

        if hasattr(orchestrator, "_proxy_provider") and orchestrator._proxy_provider:
            provider = orchestrator._proxy_provider
            return {
                "proxies_total": getattr(provider, "total_count", 0),
                "proxies_healthy": getattr(provider, "healthy_count", 0),
                "proxies_failed": getattr(provider, "failed_count", 0),
            }
    except (RuntimeError, AttributeError):
        pass

    return {
        "proxies_total": 0,
        "proxies_healthy": 0,
        "proxies_failed": 0,
    }


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """Get current dashboard metrics."""
    orch_stats = _get_orchestrator_stats()
    task_stats = _get_task_stats()
    proxy_stats = _get_proxy_stats()

    return MetricsResponse(
        timestamp=datetime.now(UTC),
        uptime_seconds=orch_stats.get("uptime_seconds"),
        tasks_pending=task_stats["tasks_pending"],
        tasks_running=task_stats["tasks_running"],
        tasks_completed=task_stats["tasks_completed"],
        tasks_failed=task_stats["tasks_failed"],
        proxies_total=proxy_stats["proxies_total"],
        proxies_healthy=proxy_stats["proxies_healthy"],
        proxies_failed=proxy_stats["proxies_failed"],
        workers_active=orch_stats.get("workers_active", 0),
        workers_total=orch_stats.get("workers_total", 0),
    )


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    orch_stats = _get_orchestrator_stats()

    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "orchestrator": {
            "running": orch_stats.get("is_running", False),
            "uptime_seconds": orch_stats.get("uptime_seconds"),
        },
    }


@router.get("/stats/summary")
async def get_summary_stats() -> dict[str, Any]:
    """Get summary statistics for the dashboard."""
    orch_stats = _get_orchestrator_stats()
    task_stats = _get_task_stats()
    proxy_stats = _get_proxy_stats()

    total_tasks = sum(task_stats.values())
    success_rate = (task_stats["tasks_completed"] / total_tasks * 100) if total_tasks > 0 else 0.0

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime": {
            "seconds": orch_stats.get("uptime_seconds"),
            "formatted": _format_uptime(orch_stats.get("uptime_seconds")),
        },
        "tasks": {
            "total": total_tasks,
            "pending": task_stats["tasks_pending"],
            "running": task_stats["tasks_running"],
            "completed": task_stats["tasks_completed"],
            "failed": task_stats["tasks_failed"],
            "success_rate_percent": round(success_rate, 1),
        },
        "proxies": {
            "total": proxy_stats["proxies_total"],
            "healthy": proxy_stats["proxies_healthy"],
            "failed": proxy_stats["proxies_failed"],
        },
        "workers": {
            "active": orch_stats.get("workers_active", 0),
            "total": orch_stats.get("workers_total", 0),
        },
    }


def _format_uptime(seconds: float | None) -> str:
    """Format uptime in human-readable format."""
    if seconds is None:
        return "N/A"

    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
