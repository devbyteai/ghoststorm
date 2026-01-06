"""Task management API routes."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from ghoststorm.api.schemas import (
    PlatformDetectRequest,
    PlatformDetectResponse,
    PlatformType,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    detect_platform,
)
from ghoststorm.core.identity import CoherentIdentity, IdentityCoherenceOrchestrator
from ghoststorm.core.models.fingerprint import Fingerprint, ScreenConfig
from ghoststorm.core.models.proxy import Proxy

logger = structlog.get_logger(__name__)
router = APIRouter()


def get_orchestrator():
    """Get orchestrator from app state (lazy import to avoid circular deps)."""
    from ghoststorm.api.app import get_orchestrator as _get_orchestrator

    return _get_orchestrator()


# In-memory task storage (replace with database in production)
_tasks: dict[str, dict[str, Any]] = {}
_task_lock = asyncio.Lock()


async def _get_task(task_id: str) -> dict[str, Any]:
    """Get task by ID with locking."""
    async with _task_lock:
        if task_id not in _tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        return _tasks[task_id]


async def _update_task(task_id: str, updates: dict[str, Any]) -> None:
    """Update task with locking."""
    async with _task_lock:
        if task_id in _tasks:
            _tasks[task_id].update(updates)


async def _execute_with_llm(
    task_id: str,
    page: Any,
    url: str,
    llm_mode: str,
    llm_task: str | None,
    vision_mode: str,
    platform: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute task using LLM controller.

    Args:
        task_id: Task ID
        page: Browser page
        url: Target URL
        llm_mode: "assist" or "autonomous"
        llm_task: Natural language task description
        vision_mode: "off", "auto", or "always"
        platform: Platform type
        config: Task configuration

    Returns:
        Execution result dictionary
    """
    import base64

    from ghoststorm.api.websocket import ws_manager
    from ghoststorm.core.dom.service import DOMService
    from ghoststorm.core.llm.controller import LLMController
    from ghoststorm.core.llm.service import LLMService, LLMServiceConfig

    try:
        # Try to get orchestrator, but work without it
        orchestrator = None
        with contextlib.suppress(Exception):
            orchestrator = get_orchestrator()

        # Initialize LLM services - use orchestrator's if available, else create our own
        if orchestrator and orchestrator.llm_controller:
            llm_controller = orchestrator.llm_controller
            dom_service = orchestrator.dom_service
        else:
            # Initialize standalone LLM services
            logger.info("Initializing standalone LLM services")
            llm_service = LLMService(LLMServiceConfig())
            dom_service = DOMService()
            llm_controller = LLMController(llm_service, dom_service)

        # Register page if orchestrator available
        if orchestrator:
            orchestrator.register_page(task_id, page)

        try:
            # Navigate to URL first
            await page.goto(url)

            # Capture and broadcast initial screenshot
            try:
                screenshot = await page.screenshot(type="png")
                screenshot_b64 = base64.b64encode(screenshot).decode()
                await ws_manager.broadcast(
                    {
                        "type": "visual.screenshot_live",
                        "task_id": task_id,
                        "data": {"screenshot": screenshot_b64},
                    }
                )
            except Exception as e:
                logger.debug("Screenshot capture failed", error=str(e))

            # Broadcast navigation event
            await ws_manager.broadcast(
                {
                    "type": "llm_navigated",
                    "task_id": task_id,
                    "url": url,
                }
            )

            # Build task description
            if not llm_task:
                # Auto-generate based on platform
                if platform == "tiktok":
                    llm_task = f"Watch videos and interact naturally on TikTok at {url}"
                elif platform == "instagram":
                    llm_task = f"Browse and interact with content on Instagram at {url}"
                elif platform == "youtube":
                    llm_task = f"Watch videos on YouTube at {url}"
                else:
                    llm_task = f"Browse and interact with the page at {url}"

            # Extract DOM if service available
            dom_state = None
            if dom_service:
                try:
                    dom_state = await dom_service.extract_dom(page)
                    await ws_manager.broadcast(
                        {
                            "type": "dom_extracted",
                            "task_id": task_id,
                            "elements_count": len(dom_state.elements) if dom_state else 0,
                        }
                    )
                except Exception as e:
                    logger.warning("DOM extraction failed", error=str(e))

            # Execute based on LLM mode
            if llm_mode == "autonomous":
                # Full autonomous execution
                from ghoststorm.core.llm.controller import ControllerMode

                llm_controller.set_mode(ControllerMode.AUTONOMOUS)

                result = await llm_controller.execute_task(page, llm_task)

                # Capture final screenshot
                try:
                    screenshot = await page.screenshot(type="png")
                    screenshot_b64 = base64.b64encode(screenshot).decode()
                    await ws_manager.broadcast(
                        {
                            "type": "visual.screenshot_live",
                            "task_id": task_id,
                            "data": {"screenshot": screenshot_b64},
                        }
                    )
                except Exception:
                    pass

                await ws_manager.broadcast(
                    {
                        "type": "llm_task_complete",
                        "task_id": task_id,
                        "success": result.success,
                        "steps": result.steps_taken,
                    }
                )

                return {
                    "success": result.success,
                    "steps": result.steps_taken,
                    "extracted_data": result.extracted_data or {},
                    "final_url": page.url,
                    "analysis": None,
                    "error": result.error if not result.success else None,
                }

            elif llm_mode == "assist":
                # Assist mode - analyze and suggest, but don't auto-execute
                from ghoststorm.core.llm.controller import ControllerMode

                llm_controller.set_mode(ControllerMode.ASSIST)

                analysis = await llm_controller.analyze_page(page, llm_task)

                # Broadcast analysis for UI
                await ws_manager.broadcast(
                    {
                        "type": "llm_analysis_ready",
                        "task_id": task_id,
                        "analysis": analysis.analysis,
                        "confidence": analysis.confidence,
                        "next_action": analysis.next_action.model_dump()
                        if analysis.next_action
                        else None,
                    }
                )

                return {
                    "success": True,
                    "steps": 0,
                    "extracted_data": {},
                    "final_url": page.url,
                    "analysis": {
                        "text": analysis.analysis,
                        "confidence": analysis.confidence,
                        "suggested_action": analysis.next_action.model_dump()
                        if analysis.next_action
                        else None,
                    },
                }

            return {
                "success": False,
                "error": f"Unknown LLM mode: {llm_mode}",
            }

        finally:
            # Unregister page if orchestrator available
            if orchestrator:
                orchestrator.unregister_page(task_id)

    except Exception as e:
        logger.exception("LLM execution failed", task_id=task_id, error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


async def _run_task(task_id: str, task_data: dict[str, Any]) -> None:
    """Execute a task asynchronously.

    This is the actual task execution logic. Creates a browser context
    and runs the appropriate automation plugin.
    """
    try:
        await _update_task(
            task_id,
            {
                "status": "running",
                "started_at": datetime.now(UTC),
            },
        )

        platform = task_data["platform"]
        url = task_data["url"]
        config = task_data.get("config", {})
        mode = task_data.get("mode", "batch")

        logger.info(
            "Starting task execution",
            task_id=task_id,
            platform=platform,
            url=url,
            mode=mode,
            config_flags={k: v for k, v in config.items() if k.startswith("use_")},
        )

        # Broadcast start event via WebSocket
        from ghoststorm.api.websocket import ws_manager

        await ws_manager.broadcast(
            {
                "type": "task_started",
                "task_id": task_id,
                "platform": platform,
                "url": url,
            }
        )

        # Import data loading utilities
        from ghoststorm.api.routes.data import (
            get_evasion_scripts,
            get_random_proxy,
            get_random_referrer,
            get_random_screen_size,
            get_random_user_agent,
        )

        # Load data based on config flags
        user_agent = None
        if config.get("use_user_agents", True):
            user_agent = get_random_user_agent(config.get("user_agent_source"))
            if user_agent:
                logger.debug("Using custom user agent", user_agent=user_agent[:50])

        screen_size = None
        if config.get("use_screen_sizes", True):
            screen_size = get_random_screen_size()
            if screen_size:
                logger.debug("Using screen size", width=screen_size[0], height=screen_size[1])

        referrer = None
        if config.get("use_referrers", True):
            referrer = get_random_referrer()
            if referrer:
                logger.debug("Using referrer", referrer=referrer)

        proxy = None
        if config.get("use_proxies", True):
            proxy = get_random_proxy()
            if proxy:
                logger.debug("Using proxy", proxy=proxy[:30] + "...")

        evasion_scripts = []
        if config.get("use_evasion", True):
            evasion_scripts = get_evasion_scripts()
            if evasion_scripts:
                logger.debug("Loaded evasion scripts", count=len(evasion_scripts))

        # =====================================================================
        # IDENTITY COHERENCE ORCHESTRATION
        # Ensures proxy geo, fingerprint locale/timezone, and headers all match
        # =====================================================================
        coherent_identity: CoherentIdentity | None = None
        if config.get("use_identity_coherence", True):
            try:
                # Create base fingerprint from loaded data
                base_fingerprint = Fingerprint(
                    user_agent=user_agent or "",
                    screen=ScreenConfig(
                        width=screen_size[0] if screen_size else 1920,
                        height=screen_size[1] if screen_size else 1080,
                    ),
                )

                # Parse proxy string to Proxy object if available
                proxy_obj = None
                if proxy:
                    try:
                        proxy_obj = Proxy.from_string(proxy)
                    except Exception as e:
                        logger.debug("Failed to parse proxy for coherence", error=str(e))

                # Create coherent identity
                orchestrator = IdentityCoherenceOrchestrator.get_instance()
                coherent_identity = await orchestrator.create_coherent_identity(
                    fingerprint=base_fingerprint,
                    proxy=proxy_obj,
                    strict=True,  # Adapt fingerprint to match proxy geo
                )

                logger.info(
                    "Identity coherence generated",
                    score=f"{coherent_identity.coherence_score:.2f}",
                    country=coherent_identity.country_code,
                    locale=coherent_identity.locale,
                    timezone=coherent_identity.timezone,
                    warnings=coherent_identity.warnings[:2] if coherent_identity.warnings else [],
                )

                # Add timezone emulation script
                from ghoststorm.plugins.evasion.timezone_emulator import (
                    generate_timezone_script,
                )

                timezone_script = generate_timezone_script(
                    timezone_id=coherent_identity.timezone,
                    locale=coherent_identity.locale,
                )
                evasion_scripts.append(timezone_script)

            except Exception as e:
                logger.warning("Identity coherence failed, using defaults", error=str(e))
                coherent_identity = None

        # Import browser engine
        try:
            from patchright.async_api import async_playwright
        except ImportError:
            from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Prepare browser launch args
            launch_args: dict[str, Any] = {}
            headless = config.get("headless", True)
            launch_args["headless"] = headless

            # Essential stealth/proxy args
            stealth_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--no-first-run",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                # DNS leak prevention - route DNS through encrypted DoH (with bootstrap IPs)
                '--dns-over-https-templates={"servers":[{"template":"https://dns.google/dns-query{?dns}","endpoints":[{"ips":["8.8.8.8","8.8.4.4"]}]}]}',
                "--enable-features=DnsOverHttps",
                # IPv6 leak prevention - IPv6 can bypass proxy
                "--disable-ipv6",
                # WebRTC leak prevention - WebRTC can expose real IP even through proxy
                "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                # Additional privacy
                "--disable-features=WebRtcHideLocalIpsWithMdns",
                "--disable-sync",
                "--disable-translate",
                "--disable-extensions",
            ]
            launch_args["args"] = stealth_args

            # Add proxy if available
            if proxy:
                # Parse proxy string (format: host:port or user:pass@host:port)
                try:
                    if "@" in proxy:
                        auth, server = proxy.rsplit("@", 1)
                        user, password = auth.split(":", 1)
                        launch_args["proxy"] = {
                            "server": f"http://{server}",
                            "username": user,
                            "password": password,
                        }
                    else:
                        launch_args["proxy"] = {"server": f"http://{proxy}"}
                except Exception as e:
                    logger.warning("Failed to parse proxy", proxy=proxy[:20], error=str(e))

            browser = await p.chromium.launch(**launch_args)

            try:
                # Create context with configured options
                context_args: dict[str, Any] = {}

                # =========================================================
                # APPLY COHERENT IDENTITY (if available)
                # This ensures all browser parameters match the proxy geo
                # =========================================================
                if coherent_identity:
                    # Use coherent identity values
                    context_args["user_agent"] = (
                        coherent_identity.fingerprint.user_agent or user_agent
                    )
                    context_args["locale"] = coherent_identity.locale
                    context_args["timezone_id"] = coherent_identity.timezone
                    context_args["geolocation"] = coherent_identity.geolocation.to_dict()
                    context_args["permissions"] = ["geolocation"]

                    # Merge coherent headers with referrer
                    extra_headers = dict(coherent_identity.headers)
                    if referrer:
                        extra_headers["Referer"] = referrer
                    context_args["extra_http_headers"] = extra_headers

                    # Apply screen size from coherent identity
                    context_args["viewport"] = {
                        "width": coherent_identity.fingerprint.screen.width,
                        "height": coherent_identity.fingerprint.screen.height,
                    }

                    # Mobile settings from fingerprint
                    if coherent_identity.fingerprint.max_touch_points > 0:
                        context_args["is_mobile"] = True
                        context_args["has_touch"] = True

                    logger.debug(
                        "Applied coherent identity to context",
                        locale=coherent_identity.locale,
                        timezone=coherent_identity.timezone,
                        headers=list(extra_headers.keys()),
                    )
                else:
                    # Fallback to original behavior without coherence
                    if user_agent:
                        context_args["user_agent"] = user_agent

                    # Apply screen size / viewport
                    if platform in ("tiktok", "instagram", "youtube"):
                        # Use mobile viewport for social media
                        if screen_size:
                            context_args["viewport"] = {
                                "width": screen_size[0],
                                "height": screen_size[1],
                            }
                        else:
                            context_args["viewport"] = {"width": 390, "height": 844}
                        context_args["is_mobile"] = True
                        context_args["has_touch"] = True
                    elif screen_size:
                        context_args["viewport"] = {
                            "width": screen_size[0],
                            "height": screen_size[1],
                        }

                    # Apply referrer if set
                    if referrer:
                        context_args["extra_http_headers"] = {"Referer": referrer}

                context = await browser.new_context(**context_args)

                # Inject evasion scripts
                if evasion_scripts:
                    for script in evasion_scripts:
                        await context.add_init_script(script)

                page = await context.new_page()

                # Get LLM mode
                llm_mode = task_data.get("llm_mode", "off")
                llm_task_desc = task_data.get("llm_task")
                vision_mode = task_data.get("vision_mode", "auto")

                # If LLM mode is enabled, use LLM-driven execution
                if llm_mode != "off":
                    result = await _execute_with_llm(
                        task_id=task_id,
                        page=page,
                        url=url,
                        llm_mode=llm_mode,
                        llm_task=llm_task_desc,
                        vision_mode=vision_mode,
                        platform=platform,
                        config=config,
                    )

                    # Update task with LLM result
                    if result:
                        results_data = {
                            "success": result.get("success", False),
                            "llm_mode": llm_mode,
                            "steps_taken": result.get("steps", 0),
                            "extracted_data": result.get("extracted_data", {}),
                            "final_url": result.get("final_url"),
                        }

                        await _update_task(
                            task_id,
                            {
                                "status": "completed" if result.get("success") else "failed",
                                "progress": 1.0,
                                "completed_at": datetime.now(UTC),
                                "results": results_data,
                                "llm_analysis": result.get("analysis"),
                                "error": result.get("error"),
                            },
                        )

                        await ws_manager.broadcast(
                            {
                                "type": "task_completed"
                                if result.get("success")
                                else "task_failed",
                                "task_id": task_id,
                                "results": results_data,
                                "llm_mode": llm_mode,
                                "error": result.get("error"),
                            }
                        )

                        logger.info(
                            "LLM task completed",
                            task_id=task_id,
                            llm_mode=llm_mode,
                            success=result.get("success"),
                        )
                        return

                # Execute based on platform (non-LLM mode)
                result = None
                if platform == "tiktok":
                    from ghoststorm.plugins.automation.tiktok import (
                        TikTokAutomation,
                        TikTokConfig,
                    )

                    # Check for unsupported content types
                    if "/photo/" in url:
                        raise ValueError(
                            "Photo URLs are not supported. Please use a video URL (/video/) or profile URL (@username)."
                        )
                    if "/live/" in url:
                        raise ValueError(
                            "Live stream URLs are not supported. Please use a video URL (/video/) or profile URL (@username)."
                        )

                    # Build config - handle video URLs
                    video_urls = config.get("target_video_urls", [])
                    if not video_urls and "video" in url:
                        video_urls = [url]

                    tiktok_config = TikTokConfig(
                        target_url=url,
                        target_video_urls=video_urls,
                        target_username=config.get("target_username", ""),
                        min_watch_percent=config.get("min_watch_percent", 0.3),
                        max_watch_percent=config.get("max_watch_percent", 1.5),
                        skip_probability=config.get("skip_probability", 0.30),
                        bio_click_probability=config.get("bio_click_probability", 0.15),
                        videos_per_session=tuple(config.get("videos_per_session", [10, 30])),
                    )

                    automation = TikTokAutomation(config=tiktok_config)
                    result = await automation.run(page, url=url)

                elif platform == "instagram":
                    from ghoststorm.plugins.automation.instagram import (
                        InstagramAutomation,
                        InstagramConfig,
                    )

                    reel_urls = config.get("target_reel_urls", [])
                    if not reel_urls and "reel" in url:
                        reel_urls = [url]

                    insta_config = InstagramConfig(
                        target_url=url,
                        target_reel_urls=reel_urls,
                        bio_link_click_probability=config.get("bio_link_click_probability", 0.15),
                        story_link_click_probability=config.get(
                            "story_link_click_probability", 0.10
                        ),
                        reels_per_session=tuple(config.get("reels_per_session", [10, 30])),
                    )

                    automation = InstagramAutomation(config=insta_config)
                    result = await automation.run(page, url=url)

                elif platform == "youtube":
                    from ghoststorm.plugins.automation.youtube import (
                        YouTubeAutomation,
                        YouTubeConfig,
                    )

                    video_urls = config.get("target_video_urls", [])
                    short_urls = config.get("target_short_urls", [])
                    if not video_urls and "watch" in url:
                        video_urls = [url]
                    if not short_urls and "shorts" in url:
                        short_urls = [url]

                    yt_config = YouTubeConfig(
                        target_url=url,
                        target_video_urls=video_urls,
                        target_short_urls=short_urls,
                        min_watch_seconds=config.get("min_watch_seconds", 30),
                        description_click_probability=config.get(
                            "description_click_probability", 0.10
                        ),
                    )

                    automation = YouTubeAutomation(config=yt_config)
                    result = await automation.run(page, url=url)

                elif platform == "dextools":
                    from ghoststorm.plugins.automation.dextools import (
                        DEXToolsAutomation,
                        DEXToolsConfig,
                    )

                    dex_config = DEXToolsConfig(
                        pair_url=url,
                        behavior_mode=config.get("behavior_mode", "realistic"),
                        dwell_time_min=config.get("dwell_time_min", 30.0),
                        dwell_time_max=config.get("dwell_time_max", 120.0),
                        enable_natural_scroll=config.get("enable_natural_scroll", True),
                        enable_chart_hover=config.get("enable_chart_hover", True),
                        enable_mouse_movement=config.get("enable_mouse_movement", True),
                        enable_social_clicks=config.get("enable_social_clicks", True),
                        enable_tab_clicks=config.get("enable_tab_clicks", False),
                        enable_favorite=config.get("enable_favorite", False),
                        min_delay=config.get("min_delay", 2.0),
                        max_delay=config.get("max_delay", 6.0),
                    )

                    automation = DEXToolsAutomation(config=dex_config)
                    visit_result = await automation.run_natural_visit(page, url=url)

                    result = {
                        "success": visit_result.success,
                        "behavior": visit_result.behavior.value,
                        "dwell_time": visit_result.dwell_time_s,
                        "social_clicks": visit_result.social_clicks,
                        "tab_clicks": visit_result.tab_clicks,
                        "actions": visit_result.actions_performed,
                        "errors": visit_result.errors,
                    }

                else:
                    # Generic URL visit
                    await page.goto(url)
                    dwell_time = config.get("dwell_time", 10)
                    await asyncio.sleep(dwell_time)
                    result = {"success": True, "dwell_time": dwell_time}

                # Update progress
                await _update_task(task_id, {"progress": 1.0})

                # Build result summary
                if hasattr(result, "videos_watched"):
                    results_data = {
                        "success": result.success,
                        "videos_watched": result.videos_watched,
                        "bio_links_clicked": result.bio_links_clicked,
                        "profiles_visited": getattr(result, "profiles_visited", 0),
                        "errors": result.errors if result.errors else [],
                        "duration_seconds": (result.end_time - result.start_time).total_seconds()
                        if hasattr(result, "end_time")
                        else 0,
                    }
                else:
                    results_data = (
                        {"success": True, **result}
                        if isinstance(result, dict)
                        else {"success": True}
                    )

                # Determine actual status - failed if errors and no results
                total_activity = (
                    results_data.get("videos_watched", 0)
                    + results_data.get("bio_links_clicked", 0)
                    + results_data.get("profiles_visited", 0)
                )
                has_errors = bool(results_data.get("errors"))

                if has_errors and total_activity == 0:
                    # Had errors and achieved nothing = failed
                    error_summary = "; ".join(results_data.get("errors", [])[:3])  # First 3 errors
                    await _update_task(
                        task_id,
                        {
                            "status": "failed",
                            "progress": 1.0,
                            "completed_at": datetime.now(UTC),
                            "results": results_data,
                            "error": error_summary or "Task completed with no results",
                        },
                    )
                    await ws_manager.broadcast(
                        {
                            "type": "task_failed",
                            "task_id": task_id,
                            "error": error_summary,
                            "results": results_data,
                        }
                    )
                else:
                    # Success or partial success
                    await _update_task(
                        task_id,
                        {
                            "status": "completed",
                            "progress": 1.0,
                            "completed_at": datetime.now(UTC),
                            "results": results_data,
                        },
                    )
                    await ws_manager.broadcast(
                        {
                            "type": "task_completed",
                            "task_id": task_id,
                            "results": results_data,
                        }
                    )

                logger.info(
                    "Task completed",
                    task_id=task_id,
                    platform=platform,
                    results=results_data,
                )

            finally:
                await browser.close()

    except Exception as e:
        logger.error("Task failed", task_id=task_id, error=str(e))

        # Broadcast failure
        try:
            from ghoststorm.api.websocket import ws_manager

            await ws_manager.broadcast(
                {
                    "type": "task_failed",
                    "task_id": task_id,
                    "error": str(e),
                }
            )
        except Exception:
            pass

        await _update_task(
            task_id,
            {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now(UTC),
            },
        )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    """Create a new task.

    Auto-detects platform from URL if not specified.
    Supports batch mode (multi-worker) and debug mode (single session).
    """
    # Detect platform if not provided
    if task.platform is None:
        platform, metadata = detect_platform(task.url)
    else:
        platform = task.platform
        _, metadata = detect_platform(task.url)

    task_id = str(uuid4())[:12]
    now = datetime.now(UTC)

    # Merge behavior config into main config
    config = task.config.copy() if task.config else {}
    if task.behavior:
        config["behavior"] = task.behavior

    task_data = {
        "task_id": task_id,
        "status": "pending",
        "platform": platform,
        "url": task.url,
        "mode": task.mode,
        "workers": task.workers if task.mode == "batch" else 1,
        "repeat": task.repeat,
        "config": config,
        "metadata": metadata,
        "progress": 0.0,
        "results": None,
        "error": None,
        "created_at": now,
        "started_at": None,
        "completed_at": None,
        # LLM/AI fields
        "llm_mode": task.llm_mode,
        "llm_task": task.llm_task,
        "vision_mode": task.vision_mode,
        "llm_analysis": None,
    }

    async with _task_lock:
        _tasks[task_id] = task_data

    logger.info(
        "Task created",
        task_id=task_id,
        platform=platform,
        mode=task.mode,
        workers=task.workers,
    )

    # Start task execution in background
    background_tasks.add_task(_run_task, task_id, task_data)

    return TaskResponse(**task_data)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status_filter: str | None = None,
    platform: PlatformType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> TaskListResponse:
    """List all tasks with optional filtering."""
    async with _task_lock:
        tasks = list(_tasks.values())

    # Apply filters
    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]
    if platform:
        tasks = [t for t in tasks if t["platform"] == platform]

    # Sort by created_at descending
    tasks.sort(key=lambda t: t["created_at"], reverse=True)

    # Pagination
    total = len(tasks)
    tasks = tasks[offset : offset + limit]

    # Calculate stats
    all_tasks = list(_tasks.values())
    running = sum(1 for t in all_tasks if t["status"] == "running")
    completed = sum(1 for t in all_tasks if t["status"] == "completed")
    failed = sum(1 for t in all_tasks if t["status"] == "failed")

    return TaskListResponse(
        tasks=[TaskResponse(**t) for t in tasks],
        total=total,
        running=running,
        completed=completed,
        failed=failed,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """Get task details by ID."""
    task = await _get_task(task_id)
    return TaskResponse(**task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_task(task_id: str) -> None:
    """Cancel a running or pending task."""
    task = await _get_task(task_id)

    if task["status"] in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status: {task['status']}",
        )

    await _update_task(
        task_id,
        {
            "status": "cancelled",
            "completed_at": datetime.now(UTC),
        },
    )

    logger.info("Task cancelled", task_id=task_id)


@router.post("/detect", response_model=PlatformDetectResponse)
async def detect_platform_endpoint(request: PlatformDetectRequest) -> PlatformDetectResponse:
    """Detect platform from a URL."""
    platform, metadata = detect_platform(request.url)

    return PlatformDetectResponse(
        platform=platform,
        detected=platform != "generic",
        metadata=metadata,
    )


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    """Retry a failed or cancelled task."""
    task = await _get_task(task_id)

    if task["status"] not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed or cancelled tasks",
        )

    # Create new task with same config
    new_task_id = str(uuid4())[:12]
    now = datetime.now(UTC)

    new_task_data = {
        **task,
        "task_id": new_task_id,
        "status": "pending",
        "progress": 0.0,
        "results": None,
        "error": None,
        "created_at": now,
        "started_at": None,
        "completed_at": None,
    }

    async with _task_lock:
        _tasks[new_task_id] = new_task_data

    background_tasks.add_task(_run_task, new_task_id, new_task_data)

    logger.info("Task retried", original_id=task_id, new_id=new_task_id)
    return TaskResponse(**new_task_data)
