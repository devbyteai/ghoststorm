"""Main orchestrator - coordinates all components."""

from __future__ import annotations

import asyncio
import contextlib
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

from ghoststorm.core.engine.circuit_breaker import CircuitBreakerManager
from ghoststorm.core.engine.pool import WorkerPool
from ghoststorm.core.engine.scheduler import TaskScheduler
from ghoststorm.core.events.bus import AsyncEventBus
from ghoststorm.core.events.types import EventType
from ghoststorm.core.registry.manager import PluginManager
from ghoststorm.core.watchdog import (
    BrowserWatchdog,
    HealthWatchdog,
    NetworkWatchdog,
    PageWatchdog,
    WatchdogConfig,
    WatchdogManager,
)

if TYPE_CHECKING:
    from ghoststorm.core.browser.protocol import IPage
    from ghoststorm.core.dom.service import DOMService
    from ghoststorm.core.interfaces.browser import IBrowserEngine
    from ghoststorm.core.interfaces.fingerprint import IFingerprintGenerator
    from ghoststorm.core.interfaces.proxy import IProxyProvider
    from ghoststorm.core.llm.controller import LLMController
    from ghoststorm.core.llm.service import LLMService
    from ghoststorm.core.models.config import Config
    from ghoststorm.core.models.task import Task, TaskResult

logger = structlog.get_logger(__name__)


class Orchestrator:
    """
    Main orchestrator that coordinates all components.

    Manages the lifecycle of:
    - Browser engines
    - Proxy providers
    - Fingerprint generators
    - Task scheduling and execution
    - Event distribution
    - Plugin management
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the orchestrator.

        Args:
            config: Application configuration
        """
        self.config = config
        self.id = str(uuid4())[:8]

        # Core components
        self.event_bus = AsyncEventBus()
        self.plugin_manager = PluginManager()
        self.scheduler = TaskScheduler(
            max_queue_size=config.concurrency.queue_size,
            rate_limit_per_minute=None,  # TODO: Add to config
        )
        self.worker_pool = WorkerPool(
            max_workers=config.concurrency.max_workers,
            task_timeout=config.concurrency.task_timeout,
        )
        self.circuit_breakers = CircuitBreakerManager()

        # Watchdog system
        watchdog_config = WatchdogConfig(
            enabled=config.watchdog.enabled,
            health_check_interval=config.watchdog.health_check_interval,
            auto_recovery=config.watchdog.auto_recovery,
            max_recovery_attempts=config.watchdog.max_recovery_attempts,
            recovery_cooldown=config.watchdog.recovery_cooldown,
            alert_threshold=config.watchdog.alert_threshold,
            browser_timeout=config.watchdog.browser_timeout,
            page_timeout=config.watchdog.page_timeout,
            network_timeout=config.watchdog.network_timeout,
        )
        self.watchdog_manager = WatchdogManager(self.event_bus, watchdog_config)
        self._watchdog_config = watchdog_config

        # Providers (initialized on start)
        self._browser_engine: IBrowserEngine | None = None
        self._proxy_provider: IProxyProvider | None = None
        self._fingerprint_generator: IFingerprintGenerator | None = None

        # LLM & DOM services (initialized on start if enabled)
        self.llm_service: LLMService | None = None
        self.llm_controller: LLMController | None = None
        self.dom_service: DOMService | None = None

        # Active pages by task ID (for LLM API access)
        self._active_pages: dict[str, IPage] = {}

        # State
        self._running = False
        self._started_at: datetime | None = None
        self._processing_task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self._running

    @property
    def uptime(self) -> float | None:
        """Get uptime in seconds."""
        if self._started_at:
            return (datetime.now() - self._started_at).total_seconds()
        return None

    async def start(self) -> None:
        """Start the orchestrator and all components."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        logger.info("Starting orchestrator", id=self.id)

        try:
            # Start event bus
            await self.event_bus.start()

            # Load plugins
            self.plugin_manager.load_builtin_plugins()
            if self.config.plugins.enabled and self.config.plugins.directory.exists():
                self.plugin_manager.load_external_plugins(self.config.plugins.directory)

            # Call engine start hooks
            await self.plugin_manager.call_hook_async(
                "on_engine_start",
                config=self.config,
            )

            # Initialize providers
            await self._initialize_providers()

            # Initialize LLM and DOM services if enabled
            await self._initialize_intelligence_services()

            # Initialize and start watchdogs
            await self._initialize_watchdogs()
            await self.watchdog_manager.start()

            # Start worker pool
            await self.worker_pool.start()

            # Start task processing loop
            self._processing_task = asyncio.create_task(self._process_tasks())

            self._running = True
            self._started_at = datetime.now()

            await self.event_bus.emit(
                EventType.ENGINE_STARTED,
                {"orchestrator_id": self.id},
                source="orchestrator",
            )

            logger.info("Orchestrator started", id=self.id)

        except Exception as e:
            logger.exception("Failed to start orchestrator", error=str(e))
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the orchestrator and all components."""
        if not self._running:
            return

        logger.info("Stopping orchestrator", id=self.id)

        await self.event_bus.emit(
            EventType.ENGINE_STOPPING,
            {"orchestrator_id": self.id},
            source="orchestrator",
        )

        self._running = False

        # Stop task processing
        if self._processing_task:
            self._processing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._processing_task
            self._processing_task = None

        # Stop worker pool
        await self.worker_pool.stop()

        # Stop watchdogs
        await self.watchdog_manager.stop()

        # Close providers
        await self._close_providers()

        # Call engine stop hooks
        await self.plugin_manager.call_hook_async("on_engine_stop")

        # Stop event bus
        await self.event_bus.stop()

        await self.event_bus.emit(
            EventType.ENGINE_STOPPED,
            {"orchestrator_id": self.id},
            source="orchestrator",
        )

        logger.info("Orchestrator stopped", id=self.id)

    async def submit_task(self, task: Task) -> bool:
        """
        Submit a task for execution.

        Args:
            task: Task to submit

        Returns:
            True if submitted successfully
        """
        if not self._running:
            raise RuntimeError("Orchestrator is not running")

        success = await self.scheduler.enqueue(task)

        if success:
            await self.event_bus.emit(
                EventType.TASK_QUEUED,
                {"task_id": task.id, "url": task.url, "type": task.task_type.value},
                source="orchestrator",
            )

        return success

    async def submit_batch(
        self,
        tasks: list[Task],
    ) -> str:
        """
        Submit a batch of tasks.

        Args:
            tasks: Tasks to submit

        Returns:
            Batch ID
        """
        batch_id = str(uuid4())[:8]

        for task in tasks:
            task.metadata["batch_id"] = batch_id

        count = await self.scheduler.enqueue_many(tasks)

        await self.event_bus.emit(
            EventType.BATCH_STARTED,
            {"batch_id": batch_id, "total_tasks": len(tasks), "queued": count},
            source="orchestrator",
        )

        logger.info("Batch submitted", batch_id=batch_id, count=count)
        return batch_id

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task immediately.

        Args:
            task: Task to execute

        Returns:
            TaskResult
        """
        if not self._running:
            raise RuntimeError("Orchestrator is not running")

        # Call before_task hooks
        modified_tasks = await self.plugin_manager.call_hook_async(
            "before_task_execute",
            task=task,
        )
        for result in modified_tasks:
            if result is not None:
                task = result
                break

        await self.event_bus.emit(
            EventType.TASK_STARTED,
            {"task_id": task.id, "url": task.url},
            source="orchestrator",
        )

        # Execute through worker pool
        result = await self.worker_pool.execute(
            task,
            executor=self._execute_task,
        )

        # Call after_task hooks
        await self.plugin_manager.call_hook_async(
            "after_task_execute",
            task=task,
            result=result,
        )

        event_type = EventType.TASK_COMPLETED if result.success else EventType.TASK_FAILED
        await self.event_bus.emit(
            event_type,
            {
                "task_id": task.id,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "error": result.error,
            },
            source="orchestrator",
        )

        return result

    async def _execute_task(self, task: Task) -> TaskResult:
        """
        Internal task execution logic.

        This is where the actual browser automation happens.
        """
        from ghoststorm.core.models.task import TaskResult, TaskStatus

        started_at = datetime.now()

        try:
            # Get browser context
            if not self._browser_engine:
                raise RuntimeError("No browser engine available")

            # Get fingerprint if enabled
            fingerprint = None
            if self._fingerprint_generator and self.config.fingerprint.randomize_per_session:
                fingerprint = await self._fingerprint_generator.generate()

                # Apply fingerprint modifications from plugins
                modified = await self.plugin_manager.call_hook_async(
                    "modify_fingerprint",
                    fingerprint=fingerprint,
                )
                for result in modified:
                    if result is not None:
                        fingerprint = result
                        break

            # Get proxy if configured
            proxy = None
            if self._proxy_provider:
                proxy = await self._proxy_provider.get_proxy()
                task.proxy_id = proxy.id

            # Create browser context
            context = await self._browser_engine.new_context(
                fingerprint=fingerprint,
                proxy=proxy,
            )

            try:
                # Create page
                page = await context.new_page()

                # Register page for LLM API access
                self.register_page(task.id, page)

                # Inject stealth scripts
                await self.plugin_manager.call_hook_async(
                    "inject_stealth_scripts",
                    page=page,
                    fingerprint=fingerprint,
                )

                # Navigate to URL
                await self.plugin_manager.call_hook_async(
                    "before_page_load",
                    page=page,
                    url=task.url,
                )

                await page.goto(task.url, wait_until=task.config.wait_until)

                await self.plugin_manager.call_hook_async(
                    "after_page_load",
                    page=page,
                    url=task.url,
                )

                # Extract DOM if configured
                dom_state = None
                if task.config.extract_dom and self.dom_service:
                    try:
                        dom_state = await self.dom_service.extract_dom(page)
                        await self.plugin_manager.call_hook_async(
                            "on_dom_extracted",
                            page=page,
                            url=task.url,
                            dom_state=dom_state.to_dict() if dom_state else {},
                        )
                    except Exception as e:
                        logger.warning("DOM extraction failed", error=str(e))

                # Handle LLM mode
                from ghoststorm.core.models.task import LLMMode

                llm_result = None
                if task.config.llm_mode != LLMMode.OFF and self.llm_controller:
                    try:
                        from ghoststorm.core.llm.controller import ControllerMode
                        from ghoststorm.core.llm.service import ProviderType

                        # Set controller mode based on task config
                        if task.config.llm_mode == LLMMode.AUTONOMOUS:
                            self.llm_controller.set_mode(ControllerMode.AUTONOMOUS)

                            # Get provider if specified
                            provider = None
                            if task.config.llm_provider:
                                provider = ProviderType(task.config.llm_provider)

                            # Execute LLM task
                            llm_task = task.config.llm_task or f"Complete task on {task.url}"
                            llm_result = await self.llm_controller.execute_task(
                                page, llm_task, provider
                            )

                            # Call hook
                            await self.plugin_manager.call_hook_async(
                                "on_llm_task_complete",
                                task=task,
                                result=llm_result.model_dump() if llm_result else {},
                            )

                        elif task.config.llm_mode == LLMMode.ASSIST:
                            # In assist mode, just analyze the page
                            self.llm_controller.set_mode(ControllerMode.ASSIST)
                            provider = None
                            if task.config.llm_provider:
                                provider = ProviderType(task.config.llm_provider)

                            llm_task = task.config.llm_task or f"Analyze page at {task.url}"
                            analysis = await self.llm_controller.analyze_page(
                                page, llm_task, provider
                            )

                            # Call hook
                            await self.plugin_manager.call_hook_async(
                                "on_llm_decision",
                                task=task,
                                analysis={
                                    "analysis": analysis.analysis,
                                    "confidence": analysis.confidence,
                                },
                                action=analysis.next_action.model_dump()
                                if analysis.next_action
                                else None,
                            )

                    except Exception as e:
                        logger.warning("LLM execution failed", error=str(e))

                # Get page info
                final_url = page.url
                title = await page.title()

                # Take screenshot if configured
                screenshot_path = None
                if task.config.take_screenshot:
                    await page.screenshot(
                        full_page=task.config.screenshot_full_page,
                    )
                    # Save screenshot (simplified)
                    screenshot_path = f"./output/screenshots/{task.id}.png"

                # Extract data if configured
                extracted_data = {}
                if llm_result and llm_result.extracted_data:
                    extracted_data = llm_result.extracted_data

                # Mark proxy success
                if proxy and self._proxy_provider:
                    latency = (datetime.now() - started_at).total_seconds() * 1000
                    await self._proxy_provider.mark_success(proxy, latency)

                return TaskResult(
                    task_id=task.id,
                    success=True,
                    status=TaskStatus.COMPLETED,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    duration_ms=(datetime.now() - started_at).total_seconds() * 1000,
                    final_url=final_url,
                    page_title=title,
                    extracted_data=extracted_data,
                    screenshot_path=screenshot_path,
                    proxy_used=proxy.id if proxy else None,
                    fingerprint_used=fingerprint.id if fingerprint else None,
                )

            finally:
                # Unregister page
                self.unregister_page(task.id)
                await context.close()

        except Exception as e:
            logger.exception("Task execution failed", task_id=task.id, error=str(e))

            # Mark proxy failure
            if task.proxy_id and self._proxy_provider:
                try:
                    proxy = await self._proxy_provider.get_proxy()  # Get same proxy
                    await self._proxy_provider.mark_failure(proxy, str(e))
                except Exception:
                    pass

            return TaskResult(
                task_id=task.id,
                success=False,
                status=TaskStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(),
                duration_ms=(datetime.now() - started_at).total_seconds() * 1000,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _process_tasks(self) -> None:
        """Background task processing loop."""
        logger.info("Task processing loop started")

        while self._running:
            try:
                # Get next task
                task = await self.scheduler.dequeue(timeout=1.0)

                if task is None:
                    continue

                # Execute task
                asyncio.create_task(self.execute_task(task))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in task processing loop", error=str(e))
                await asyncio.sleep(1)

        logger.info("Task processing loop stopped")

    async def _initialize_watchdogs(self) -> None:
        """Initialize and register all watchdogs."""
        # Browser watchdog with restart callback
        browser_watchdog = BrowserWatchdog(
            self.event_bus,
            self._watchdog_config,
        )
        browser_watchdog.set_restart_callback(self._restart_browser_engine)
        self.watchdog_manager.register(browser_watchdog)

        # Page watchdog
        page_watchdog = PageWatchdog(
            self.event_bus,
            self._watchdog_config,
        )
        self.watchdog_manager.register(page_watchdog)

        # Network watchdog
        network_watchdog = NetworkWatchdog(
            self.event_bus,
            self._watchdog_config,
        )
        self.watchdog_manager.register(network_watchdog)

        # Health watchdog (aggregates all health)
        health_watchdog = HealthWatchdog(
            self.event_bus,
            self._watchdog_config,
        )
        self.watchdog_manager.register(health_watchdog)

        logger.info(
            "Watchdogs initialized",
            count=self.watchdog_manager.watchdog_count,
        )

    async def _restart_browser_engine(self) -> None:
        """Restart the browser engine (used by BrowserWatchdog)."""
        logger.info("Restarting browser engine")

        if self._browser_engine:
            try:
                await self._browser_engine.close()
            except Exception as e:
                logger.warning("Error closing browser for restart", error=str(e))

        # Re-initialize browser
        engine_name = self.config.engine.default
        engine_cls = self.plugin_manager.get_browser_engine(engine_name)

        if engine_cls:
            self._browser_engine = engine_cls()
            await self._browser_engine.launch(
                headless=self.config.engine.headless,
            )
            logger.info("Browser engine restarted", name=engine_name)

            # Emit event
            await self.event_bus.emit(
                EventType.BROWSER_LAUNCHED,
                {"engine": engine_name, "restarted": True},
                source="orchestrator",
            )

    async def _initialize_providers(self) -> None:
        """Initialize all providers."""
        # Browser engine
        engine_name = self.config.engine.default
        engine_cls = self.plugin_manager.get_browser_engine(engine_name)

        if engine_cls:
            self._browser_engine = engine_cls()
            await self._browser_engine.launch(
                headless=self.config.engine.headless,
            )
            logger.info("Browser engine initialized", name=engine_name)
        else:
            logger.warning("No browser engine available", requested=engine_name)

        # Proxy provider
        if self.config.proxy.providers:
            provider_config = self.config.proxy.providers[0]
            provider_cls = self.plugin_manager.get_proxy_provider(provider_config.type)

            if provider_cls:
                self._proxy_provider = provider_cls()
                await self._proxy_provider.initialize()
                logger.info("Proxy provider initialized", type=provider_config.type)

        # Fingerprint generator
        gen_name = self.config.fingerprint.provider
        gen_cls = self.plugin_manager.get_fingerprint_generator(gen_name)

        if gen_cls:
            self._fingerprint_generator = gen_cls()
            await self._fingerprint_generator.initialize()
            logger.info("Fingerprint generator initialized", name=gen_name)

    async def _close_providers(self) -> None:
        """Close all providers."""
        if self._browser_engine:
            try:
                await self._browser_engine.close()
            except Exception as e:
                logger.warning("Error closing browser engine", error=str(e))

        if self._proxy_provider:
            try:
                await self._proxy_provider.close()
            except Exception as e:
                logger.warning("Error closing proxy provider", error=str(e))

        if self._fingerprint_generator:
            try:
                await self._fingerprint_generator.close()
            except Exception as e:
                logger.warning("Error closing fingerprint generator", error=str(e))

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "id": self.id,
            "running": self._running,
            "uptime": self.uptime,
            "queue_size": self.scheduler.size,
            "active_workers": self.worker_pool.active_workers,
            "scheduler": self.scheduler.stats,
            "worker_pool": self.worker_pool.stats,
            "event_bus": self.event_bus.stats,
            "circuit_breakers": self.circuit_breakers.get_stats(),
            "watchdogs": self.watchdog_manager.get_stats(),
        }

    async def get_health(self) -> dict[str, Any]:
        """Get overall system health from watchdogs."""
        health = await self.watchdog_manager.check_health()
        return health.to_dict()

    def get_page_for_task(self, task_id: str) -> IPage | None:
        """
        Get active page for a task.

        Used by LLM API endpoints to access browser pages.

        Args:
            task_id: Task ID

        Returns:
            Active page or None if not found
        """
        return self._active_pages.get(task_id)

    def register_page(self, task_id: str, page: IPage) -> None:
        """Register an active page for a task."""
        self._active_pages[task_id] = page

    def unregister_page(self, task_id: str) -> None:
        """Unregister a page when task completes."""
        self._active_pages.pop(task_id, None)

    async def _initialize_intelligence_services(self) -> None:
        """Initialize LLM and DOM intelligence services."""
        # Initialize DOM service if enabled
        if self.config.dom.enabled:
            try:
                from ghoststorm.core.dom.models import DOMConfig as DOMServiceConfig
                from ghoststorm.core.dom.service import DOMService

                dom_config = DOMServiceConfig(
                    include_hidden=self.config.dom.include_hidden,
                    max_depth=self.config.dom.max_depth,
                    include_styles=self.config.dom.include_styles,
                    include_attributes=self.config.dom.include_attributes,
                )
                self.dom_service = DOMService(dom_config)
                logger.info("DOM service initialized")
            except Exception as e:
                logger.warning("Failed to initialize DOM service", error=str(e))

        # Initialize LLM service if enabled
        if self.config.llm.enabled:
            try:
                from ghoststorm.core.llm.controller import (
                    ControllerConfig,
                    ControllerMode,
                    LLMController,
                )
                from ghoststorm.core.llm.service import LLMService, LLMServiceConfig, ProviderType

                # Build service config from app config
                llm_config = LLMServiceConfig(
                    default_provider=ProviderType(self.config.llm.default_provider),
                    openai_api_key=self.config.llm.openai.api_key,
                    openai_model=self.config.llm.openai.model or "gpt-4o",
                    openai_base_url=self.config.llm.openai.base_url,
                    anthropic_api_key=self.config.llm.anthropic.api_key,
                    anthropic_model=self.config.llm.anthropic.model or "claude-sonnet-4-20250514",
                    anthropic_base_url=self.config.llm.anthropic.base_url,
                    ollama_host=self.config.llm.ollama.base_url
                    or os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                    ollama_model=self.config.llm.ollama.model or "llama3",
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                    timeout=self.config.llm.timeout,
                    max_retries=self.config.llm.max_retries,
                )

                self.llm_service = LLMService(llm_config)
                logger.info(
                    "LLM service initialized",
                    default_provider=self.config.llm.default_provider,
                )

                # Build controller config
                controller_mode = (
                    ControllerMode.AUTONOMOUS
                    if self.config.llm.controller_mode == "autonomous"
                    else ControllerMode.ASSIST
                )
                controller_config = ControllerConfig(
                    mode=controller_mode,
                    max_steps=self.config.llm.max_steps,
                    min_confidence=self.config.llm.min_confidence,
                )

                self.llm_controller = LLMController(
                    llm_service=self.llm_service,
                    dom_service=self.dom_service,
                    config=controller_config,
                )
                logger.info(
                    "LLM controller initialized",
                    mode=controller_mode.value,
                )

            except Exception as e:
                logger.warning("Failed to initialize LLM services", error=str(e))
