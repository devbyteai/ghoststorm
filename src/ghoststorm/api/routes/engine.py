"""Generic Automation Engine API routes."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger(__name__)
router = APIRouter()

# Job tracking
_jobs: dict[str, dict[str, Any]] = {}
_stats = {"total": 0, "successful": 0, "failed": 0}

# Preset directories
PRESETS_DIR = Path(__file__).parent.parent.parent.parent.parent / "config" / "presets"
CUSTOM_PRESETS_DIR = PRESETS_DIR / "custom"


def _load_presets() -> dict[str, dict[str, Any]]:
    """Load all presets from YAML files."""
    presets = {}

    # Load built-in presets
    if PRESETS_DIR.exists():
        for yaml_file in PRESETS_DIR.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    preset = yaml.safe_load(f)
                    if preset and "id" in preset:
                        preset["builtin"] = True
                        presets[preset["id"]] = preset
            except Exception as e:
                logger.warning(f"Failed to load preset {yaml_file}", error=str(e))

    # Load custom presets
    if CUSTOM_PRESETS_DIR.exists():
        for yaml_file in CUSTOM_PRESETS_DIR.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    preset = yaml.safe_load(f)
                    if preset and "id" in preset:
                        preset["builtin"] = False
                        presets[preset["id"]] = preset
            except Exception as e:
                logger.warning(f"Failed to load custom preset {yaml_file}", error=str(e))

    return presets


# Load presets on module init
_presets_cache: dict[str, dict[str, Any]] = {}


def get_presets() -> dict[str, dict[str, Any]]:
    """Get all presets, reloading if needed."""
    global _presets_cache
    if not _presets_cache:
        _presets_cache = _load_presets()
    return _presets_cache


def reload_presets() -> None:
    """Force reload presets from disk."""
    global _presets_cache
    _presets_cache = _load_presets()


class EngineStartRequest(BaseModel):
    """Request to start an engine job."""

    # Site config
    url: str
    name: str = "Custom"
    preset: str | None = None

    # Goal detection
    goal_keywords: list[str] = []

    # Selectors
    selectors: dict[str, list[str]] = {}
    captcha_selectors: dict[str, str] = {}

    # Actions to perform
    actions: list[dict[str, Any]] = []

    # Browser settings
    headless: bool = True
    proxy: str | None = None
    solve_captcha: bool = True

    # Timeouts
    max_iterations: int = 30


class EngineTestRequest(BaseModel):
    """Quick test request."""

    url: str
    headless: bool = True
    screenshot: bool = True


@router.get("/stats")
async def get_engine_stats() -> dict:
    """Get engine statistics."""
    running = sum(1 for j in _jobs.values() if j.get("status") == "running")
    return {
        "total": _stats["total"],
        "successful": _stats["successful"],
        "failed": _stats["failed"],
        "running": running,
    }


class PresetSaveRequest(BaseModel):
    """Request to save a custom preset."""

    id: str
    name: str
    description: str = ""
    category: str = "custom"
    url: str = ""
    goal_keywords: list[str] = []
    captcha_selectors: dict[str, str] = {}
    actions: list[dict[str, Any]] = []
    settings: dict[str, Any] = {}


@router.get("/presets")
async def list_presets(category: str | None = None) -> dict:
    """Get available presets, optionally filtered by category."""
    presets = get_presets()

    if category:
        filtered = {k: v for k, v in presets.items() if v.get("category") == category}
        return {"presets": filtered}

    return {"presets": presets}


@router.get("/presets/categories")
async def get_preset_categories() -> dict:
    """Get list of preset categories."""
    presets = get_presets()
    categories = set()
    for preset in presets.values():
        if cat := preset.get("category"):
            categories.add(cat)
    return {"categories": sorted(categories)}


@router.get("/presets/{preset_id}")
async def get_preset(preset_id: str) -> dict:
    """Get a specific preset by ID."""
    presets = get_presets()
    if preset_id not in presets:
        raise HTTPException(status_code=404, detail="Preset not found")
    return presets[preset_id]


@router.post("/presets")
async def save_preset(request: PresetSaveRequest) -> dict:
    """Save a custom preset."""
    # Ensure custom presets directory exists
    CUSTOM_PRESETS_DIR.mkdir(parents=True, exist_ok=True)

    # Create preset data
    preset_data = {
        "id": request.id,
        "name": request.name,
        "description": request.description,
        "category": request.category,
        "url": request.url,
        "goal_keywords": request.goal_keywords,
        "captcha_selectors": request.captcha_selectors,
        "actions": request.actions,
        "settings": request.settings,
    }

    # Save to file
    preset_file = CUSTOM_PRESETS_DIR / f"{request.id}.yaml"
    try:
        with open(preset_file, "w") as f:
            yaml.dump(preset_data, f, default_flow_style=False, sort_keys=False)

        # Reload presets cache
        reload_presets()

        return {"status": "saved", "id": request.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save preset: {e}")


@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: str) -> dict:
    """Delete a custom preset."""
    presets = get_presets()

    if preset_id not in presets:
        raise HTTPException(status_code=404, detail="Preset not found")

    if presets[preset_id].get("builtin"):
        raise HTTPException(status_code=400, detail="Cannot delete built-in presets")

    # Delete file
    preset_file = CUSTOM_PRESETS_DIR / f"{preset_id}.yaml"
    try:
        if preset_file.exists():
            preset_file.unlink()

        # Reload presets cache
        reload_presets()

        return {"status": "deleted", "id": preset_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete preset: {e}")


@router.post("/presets/reload")
async def reload_presets_endpoint() -> dict:
    """Force reload all presets from disk."""
    reload_presets()
    presets = get_presets()
    return {"status": "reloaded", "count": len(presets)}


@router.get("/jobs")
async def get_engine_jobs() -> dict:
    """Get all engine jobs."""
    return {"jobs": list(_jobs.values())}


@router.get("/jobs/{job_id}")
async def get_engine_job(job_id: str) -> dict:
    """Get specific engine job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@router.delete("/jobs/{job_id}")
async def cancel_engine_job(job_id: str) -> dict:
    """Cancel an engine job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    _jobs[job_id]["status"] = "cancelled"
    return {"status": "cancelled", "job_id": job_id}


@router.post("/test")
async def quick_test(request: EngineTestRequest) -> dict:
    """Quick test - just navigate and screenshot."""
    from ghoststorm.plugins.automation.engine import AutomationEngine, EngineConfig

    config = EngineConfig(
        url=request.url,
        name="QuickTest",
        headless=request.headless,
        goal_keywords=[],  # No goal, just navigate
        max_iterations=1,
    )

    engine = AutomationEngine(config)

    try:
        # Manual browser init and navigate
        await engine._init_browser()
        await engine._page.goto(request.url, timeout=30000)
        await asyncio.sleep(2)

        # Get page info
        title = await engine._page.title()
        url = engine._page.url

        # Get page text
        try:
            text = await engine._page.inner_text("body")
            text = text[:500]
        except Exception:
            text = ""

        # Screenshot
        screenshot_path = "/tmp/engine_test.png"
        if request.screenshot:
            await engine._page.screenshot(path=screenshot_path)

        await engine._cleanup()

        return {
            "success": True,
            "title": title,
            "url": url,
            "text_preview": text,
            "screenshot": screenshot_path if request.screenshot else None,
        }

    except Exception as e:
        await engine._cleanup()
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/analyze")
async def analyze_page(request: EngineTestRequest) -> dict:
    """Quick test with page analysis - detects elements and suggests config."""
    from ghoststorm.plugins.automation.engine import AutomationEngine, EngineConfig
    from ghoststorm.plugins.automation.page_detector import PageDetector

    config = EngineConfig(
        url=request.url,
        name="Analyze",
        headless=request.headless,
        goal_keywords=[],
        max_iterations=1,
    )

    engine = AutomationEngine(config)

    try:
        # Init browser and navigate
        await engine._init_browser()
        await engine._page.goto(request.url, timeout=30000)
        await asyncio.sleep(2)

        # Get basic page info
        title = await engine._page.title()
        url = engine._page.url

        try:
            text = await engine._page.inner_text("body")
            text_preview = text[:500]
        except Exception:
            text_preview = ""

        # Screenshot
        screenshot_path = "/tmp/engine_analyze.png"
        if request.screenshot:
            await engine._page.screenshot(path=screenshot_path)

        # Run page detection
        detector = PageDetector()
        detection = await detector.analyze_page(engine._page)

        await engine._cleanup()

        return {
            "success": True,
            "title": title,
            "url": url,
            "text_preview": text_preview,
            "screenshot": screenshot_path if request.screenshot else None,
            "detection": {
                "page_type": detection.page_type,
                "confidence": detection.confidence,
                "detected_elements": [
                    {
                        "type": e.type,
                        "selector": e.selector,
                        "text": e.text,
                        "confidence": e.confidence,
                    }
                    for e in detection.detected_elements
                ],
                "suggested_goal_keywords": detection.suggested_goal_keywords,
                "suggested_captcha_selectors": detection.suggested_captcha_selectors,
                "suggested_actions": detection.suggested_actions,
            },
        }

    except Exception as e:
        await engine._cleanup()
        return {
            "success": False,
            "error": str(e),
            "detection": None,
        }


@router.post("/start")
async def start_engine_job(request: EngineStartRequest) -> dict:
    """Start a new engine job."""
    from ghoststorm.plugins.automation.engine import AutomationEngine, EngineConfig

    if not request.url:
        return {"error": "URL is required"}

    # Apply preset if specified
    presets = get_presets()
    if request.preset and request.preset in presets:
        preset = presets[request.preset]
        if not request.goal_keywords:
            request.goal_keywords = preset.get("goal_keywords", [])
        if not request.captcha_selectors:
            request.captcha_selectors = preset.get("captcha_selectors", {})
        # Apply settings from preset if available
        if settings := preset.get("settings"):
            if "max_iterations" in settings and request.max_iterations == 30:
                request.max_iterations = settings["max_iterations"]
            if "headless" in settings:
                request.headless = settings["headless"]
            if "solve_captcha" in settings:
                request.solve_captcha = settings["solve_captcha"]

    job_id = str(uuid4())[:8]

    job_data = {
        "job_id": job_id,
        "status": "running",
        "url": request.url,
        "name": request.name,
        "states_visited": [],
        "actions_completed": [],
        "captchas_solved": 0,
        "config": {
            "goal_keywords": request.goal_keywords,
            "headless": request.headless,
            "solve_captcha": request.solve_captcha,
            "max_iterations": request.max_iterations,
        },
        "created_at": datetime.now(UTC).isoformat(),
        "logs": [],
        "screenshots": [],
        "error": None,
    }

    _jobs[job_id] = job_data
    _stats["total"] += 1

    # Run in background
    asyncio.create_task(_run_engine_job(job_id, request))

    return {"job_id": job_id, "status": "started"}


async def _run_engine_job(job_id: str, request: EngineStartRequest) -> None:
    """Run engine job in background."""
    from ghoststorm.plugins.automation.engine import AutomationEngine, EngineConfig

    job = _jobs[job_id]

    try:
        config = EngineConfig(
            url=request.url,
            name=request.name,
            goal_keywords=request.goal_keywords,
            selectors=request.selectors,
            captcha_selectors=request.captcha_selectors,
            actions=request.actions,
            headless=request.headless,
            proxy=request.proxy,
            solve_captcha=request.solve_captcha,
            max_iterations=request.max_iterations,
        )

        engine = AutomationEngine(config)
        result = await engine.run()

        job["status"] = "completed" if result.success else "failed"
        job["success"] = result.success
        job["states_visited"] = result.states_visited
        job["actions_completed"] = result.actions_completed
        job["captchas_solved"] = result.captchas_solved
        job["duration"] = result.duration
        job["logs"] = result.logs
        job["screenshots"] = result.screenshots
        job["error"] = result.error
        job["completed_at"] = datetime.now(UTC).isoformat()

        if result.success:
            _stats["successful"] += 1
        else:
            _stats["failed"] += 1

    except Exception as e:
        logger.error(f"[ENGINE] Job {job_id} failed", error=str(e))
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = datetime.now(UTC).isoformat()
        _stats["failed"] += 1
