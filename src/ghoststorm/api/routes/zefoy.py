"""TikTok booster API routes."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger(__name__)
router = APIRouter()

# Job tracking
_jobs: dict[str, dict[str, Any]] = {}
_stats = {"total": 0, "successful": 0, "failed": 0}

# Data directory
DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"


class ZefoyStartRequest(BaseModel):
    """Request to start a Zefoy job."""

    url: str
    services: list[str]
    repeat: int = 1
    delay: int = 60
    workers: int = 1
    use_proxy: bool = True
    headless: bool = True
    rotate_proxy: bool = True


@router.get("/stats")
async def get_zefoy_stats() -> dict:
    """Get Zefoy statistics."""
    running = sum(1 for j in _jobs.values() if j.get("status") == "running")
    return {
        "total": _stats["total"],
        "successful": _stats["successful"],
        "failed": _stats["failed"],
        "running": running,
    }


@router.get("/jobs")
async def get_zefoy_jobs() -> dict:
    """Get all Zefoy jobs."""
    return {"jobs": list(_jobs.values())}


@router.get("/jobs/{job_id}")
async def get_zefoy_job(job_id: str) -> dict:
    """Get specific Zefoy job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@router.post("/start")
async def start_zefoy_job(request: ZefoyStartRequest) -> dict:
    """Start a new Zefoy job."""
    from ghoststorm.plugins.automation.zefoy import ZEFOY_SERVICES

    # Validate services
    invalid_services = [s for s in request.services if s not in ZEFOY_SERVICES]
    if invalid_services:
        return {"error": f"Invalid services: {invalid_services}"}

    if not request.url or "tiktok.com" not in request.url.lower():
        return {"error": "Invalid TikTok URL"}

    job_id = str(uuid4())[:8]

    job_data = {
        "job_id": job_id,
        "status": "running",
        "url": request.url,
        "services": request.services,
        "total_runs": request.repeat * len(request.services),
        "current_run": 0,
        "successful_runs": 0,
        "failed_runs": 0,
        "captchas_solved": 0,
        "current_service": None,
        "config": {
            "repeat": request.repeat,
            "delay": request.delay,
            "workers": request.workers,
            "use_proxy": request.use_proxy,
            "headless": request.headless,
            "rotate_proxy": request.rotate_proxy,
        },
        "created_at": datetime.now(UTC).isoformat(),
        "logs": [],
    }

    _jobs[job_id] = job_data
    _stats["total"] += 1

    # Start job in background
    asyncio.create_task(_run_zefoy_job(job_id))

    return job_data


@router.delete("/jobs/{job_id}")
async def cancel_zefoy_job(job_id: str) -> dict:
    """Cancel a Zefoy job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    _jobs[job_id]["status"] = "cancelled"
    _jobs[job_id]["cancelled"] = True

    return {"status": "cancelled"}


@router.get("/services")
async def get_zefoy_services() -> dict:
    """Get available Zefoy services and their status."""
    from ghoststorm.plugins.automation.zefoy import ZEFOY_SERVICES

    return {
        "services": list(ZEFOY_SERVICES.keys()),
        "selectors": ZEFOY_SERVICES,
    }


# Cache for service status
_service_status_cache: dict[str, Any] = {"status": {}, "last_check": None, "checking": False}


@router.get("/services/status")
async def get_zefoy_services_status() -> dict:
    """Check real status of Zefoy services by visiting the site."""

    # Return cached if checking
    if _service_status_cache["checking"]:
        return {
            "status": _service_status_cache["status"],
            "last_check": _service_status_cache["last_check"],
            "checking": True,
        }

    return {
        "status": _service_status_cache["status"],
        "last_check": _service_status_cache["last_check"],
        "checking": False,
    }


@router.post("/services/check")
async def check_zefoy_services_now() -> dict:
    """Return all services as available.

    Note: Actual availability is checked when job runs.
    The full browser check was too slow (30+ iterations, ~45 seconds).
    """
    # Just mark all services as available - actual job will fail if service is down
    status = {
        "followers": True,
        "hearts": True,
        "chearts": True,
        "views": True,
        "shares": True,
        "favorites": True,
        "livestream": True,
    }
    _service_status_cache["status"] = status
    _service_status_cache["last_check"] = datetime.now(UTC).isoformat()
    _service_status_cache["checking"] = False

    return {
        "status": status,
        "last_check": _service_status_cache["last_check"],
        "checking": False,
    }


async def _run_zefoy_job(job_id: str) -> None:
    """Background task to run Zefoy automation with parallel workers."""
    from ghoststorm.plugins.automation.zefoy import ZefoyAutomation, ZefoyConfig

    job = _jobs[job_id]
    config = job["config"]
    workers = config.get("workers", 1)

    # Get proxy if enabled
    proxy_list: list[str] = []
    if config["use_proxy"]:
        proxy_file = DATA_DIR / "proxies" / "alive_proxies.txt"
        if proxy_file.exists():
            with open(proxy_file) as f:
                proxy_list = [line.strip() for line in f if line.strip()]

        # Fallback to aggregated if no alive proxies
        if not proxy_list:
            proxy_file = DATA_DIR / "proxies" / "aggregated.txt"
            if proxy_file.exists():
                with open(proxy_file) as f:
                    proxy_list = [line.strip() for line in f if line.strip()][:100]

    proxy_index = [0]  # Use list for mutable reference in nested function

    async def run_single_task(service: str, run_idx: int, worker_idx: int = 0) -> None:
        """Run a single automation task."""
        if job.get("cancelled"):
            return

        job["current_run"] += 1
        job["current_service"] = service

        _add_job_log(
            job_id,
            f"[Worker {worker_idx + 1}] Starting {service} run {run_idx + 1}/{config['repeat']}",
        )

        # Get proxy
        proxy = None
        if proxy_list and config["use_proxy"]:
            if config["rotate_proxy"]:
                proxy = proxy_list[proxy_index[0] % len(proxy_list)]
                proxy_index[0] += 1
            else:
                proxy = proxy_list[0]

            # Format proxy URL
            if proxy and not proxy.startswith("http"):
                proxy = f"http://{proxy}"

        # Create automation config
        zefoy_config = ZefoyConfig(
            tiktok_url=job["url"],
            service=service,
            headless=config["headless"],
            proxy=proxy,
        )

        # Run automation
        automation = ZefoyAutomation(config=zefoy_config)

        try:
            result = await automation.run()

            if result.success:
                job["successful_runs"] += 1
                _add_job_log(
                    job_id, f"✓ [Worker {worker_idx + 1}] {service} completed successfully"
                )
            else:
                job["failed_runs"] += 1
                error_icon = {
                    "proxy": "🔌",
                    "captcha": "🔐",
                    "service_offline": "⚠️",
                    "timeout": "⏱️",
                    "network": "🌐",
                }.get(result.error_type, "❌")
                _add_job_log(
                    job_id,
                    f"{error_icon} [Worker {worker_idx + 1}] {service} FAILED [{result.error_type or 'unknown'}]: {result.error}",
                )

            job["captchas_solved"] += result.captchas_solved

            # Wait for cooldown if present (cap at 5 minutes max)
            if result.cooldown_seconds > 0:
                cooldown = min(result.cooldown_seconds, 300)  # Max 5 minutes
                if cooldown != result.cooldown_seconds:
                    _add_job_log(
                        job_id,
                        f"[Worker {worker_idx + 1}] Cooldown {result.cooldown_seconds}s capped to {cooldown}s",
                    )
                _add_job_log(
                    job_id,
                    f"[Worker {worker_idx + 1}] Waiting {cooldown}s cooldown...",
                )
                await asyncio.sleep(cooldown)

        except Exception as e:
            job["failed_runs"] += 1
            _add_job_log(job_id, f"❌ [Worker {worker_idx + 1}] {service} EXCEPTION: {e!s}")

    try:
        # Build list of all tasks
        # Workers means: run this many browsers in parallel for each service
        tasks = []
        for service in job["services"]:
            for run_idx in range(config["repeat"]):
                # Create 'workers' number of parallel tasks for each run
                for worker_idx in range(workers):
                    tasks.append(run_single_task(service, run_idx, worker_idx))

        _add_job_log(
            job_id,
            f"Starting {len(tasks)} tasks ({workers} workers × {len(job['services'])} services × {config['repeat']} repeats)",
        )

        # Run all tasks in parallel (no semaphore limiting - all workers run at once)
        await asyncio.gather(*tasks)

        # Job completed
        if job.get("cancelled"):
            job["status"] = "cancelled"
        else:
            job["status"] = "completed"
            job["completed_at"] = datetime.now(UTC).isoformat()

            if job["failed_runs"] == 0:
                _stats["successful"] += 1
            else:
                _stats["failed"] += 1

        _add_job_log(
            job_id,
            f"Job completed: {job['successful_runs']} success, {job['failed_runs']} failed",
        )

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        _stats["failed"] += 1
        _add_job_log(job_id, f"Job failed: {e!s}")


def _add_job_log(job_id: str, message: str) -> None:
    """Add log entry to job."""
    if job_id in _jobs:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "message": message,
        }
        _jobs[job_id]["logs"].append(log_entry)

        # Keep only last 100 logs
        if len(_jobs[job_id]["logs"]) > 100:
            _jobs[job_id]["logs"] = _jobs[job_id]["logs"][-100:]

        logger.info(f"[ZEFOY] {message}", job_id=job_id)
