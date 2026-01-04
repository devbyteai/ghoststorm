"""Browser and Context Pool for High-Volume Operations.

Provides pooling and recycling of browser instances and contexts
for running 1000+ concurrent sessions over extended periods.
"""

from __future__ import annotations

import asyncio
import gc
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import psutil
import structlog

if TYPE_CHECKING:
    from ghoststorm.core.models.fingerprint import Fingerprint
    from ghoststorm.plugins.browsers.base import BrowserPlugin
    from ghoststorm.plugins.proxies.base import Proxy

logger = structlog.get_logger(__name__)


class PoolItemState(str, Enum):
    """State of a pooled item."""
    AVAILABLE = "available"
    IN_USE = "in_use"
    RECYCLING = "recycling"
    DEAD = "dead"


@dataclass
class BrowserInstance:
    """Represents a single browser instance in the pool."""

    id: str
    engine: BrowserPlugin
    state: PoolItemState = PoolItemState.AVAILABLE
    created_at: datetime = field(default_factory=datetime.now)
    tasks_completed: int = 0
    contexts_created: int = 0
    errors: int = 0
    last_used_at: datetime | None = None
    memory_mb: float = 0

    def should_recycle(self, max_tasks: int = 100, max_age_minutes: int = 30) -> bool:
        """Check if browser should be recycled."""
        if self.tasks_completed >= max_tasks:
            return True
        if self.errors >= 10:
            return True
        age = (datetime.now() - self.created_at).total_seconds() / 60
        if age >= max_age_minutes:
            return True
        return False


@dataclass
class ContextInstance:
    """Represents a single browser context in the pool."""

    id: str
    browser_id: str
    context: Any  # BrowserContext
    page: Any | None = None  # Page
    state: PoolItemState = PoolItemState.AVAILABLE
    created_at: datetime = field(default_factory=datetime.now)
    tasks_completed: int = 0
    fingerprint_id: str | None = None
    proxy_id: str | None = None
    last_used_at: datetime | None = None

    def should_recycle(self, max_tasks: int = 50) -> bool:
        """Check if context should be recycled."""
        return self.tasks_completed >= max_tasks


class BrowserPool:
    """
    Manages a pool of browser instances for high-volume operations.

    Features:
    - Multiple concurrent browser instances
    - Automatic browser recycling
    - Memory monitoring
    - Health checks
    """

    def __init__(
        self,
        browser_factory: Any,  # Callable to create browser engine
        max_browsers: int = 10,
        max_contexts_per_browser: int = 10,
        recycle_after_tasks: int = 100,
        recycle_after_minutes: int = 30,
        memory_limit_mb: int = 0,  # 0 = no limit
    ) -> None:
        self._browser_factory = browser_factory
        self._max_browsers = max_browsers
        self._max_contexts_per_browser = max_contexts_per_browser
        self._recycle_after_tasks = recycle_after_tasks
        self._recycle_after_minutes = recycle_after_minutes
        self._memory_limit_mb = memory_limit_mb

        self._browsers: dict[str, BrowserInstance] = {}
        self._lock = asyncio.Lock()
        self._running = False

        # Stats
        self._stats = {
            "browsers_created": 0,
            "browsers_recycled": 0,
            "total_tasks": 0,
            "total_errors": 0,
        }

    @property
    def active_browsers(self) -> int:
        """Count of active browser instances."""
        return sum(1 for b in self._browsers.values() if b.state != PoolItemState.DEAD)

    @property
    def available_browsers(self) -> int:
        """Count of available browser instances."""
        return sum(1 for b in self._browsers.values() if b.state == PoolItemState.AVAILABLE)

    @property
    def stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            **self._stats,
            "active_browsers": self.active_browsers,
            "available_browsers": self.available_browsers,
            "memory_mb": self._get_memory_usage(),
        }

    async def start(self) -> None:
        """Start the browser pool."""
        if self._running:
            return

        self._running = True

        # Pre-warm with some browsers
        initial_browsers = min(3, self._max_browsers)
        logger.info(
            "[BROWSER_POOL] Starting pool",
            max_browsers=self._max_browsers,
            initial_browsers=initial_browsers,
        )

        for _ in range(initial_browsers):
            try:
                await self._create_browser()
            except Exception as e:
                logger.error("[BROWSER_POOL] Failed to create initial browser", error=str(e))

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the browser pool and close all browsers."""
        if not self._running:
            return

        self._running = False

        logger.info("[BROWSER_POOL] Stopping pool", active_browsers=self.active_browsers)

        # Close all browsers
        async with self._lock:
            for browser in list(self._browsers.values()):
                await self._close_browser(browser)

        self._browsers.clear()
        gc.collect()

        logger.info("[BROWSER_POOL] Pool stopped")

    async def acquire(self) -> BrowserInstance:
        """
        Acquire an available browser instance.

        Returns:
            BrowserInstance ready for use
        """
        async with self._lock:
            # Check memory limit
            if self._memory_limit_mb > 0:
                current_mem = self._get_memory_usage()
                if current_mem > self._memory_limit_mb:
                    await self._recycle_oldest_browser()

            # Find available browser
            for browser in self._browsers.values():
                if browser.state == PoolItemState.AVAILABLE:
                    # Check if needs recycling
                    if browser.should_recycle(
                        self._recycle_after_tasks,
                        self._recycle_after_minutes
                    ):
                        await self._recycle_browser(browser)
                        continue

                    browser.state = PoolItemState.IN_USE
                    browser.last_used_at = datetime.now()
                    return browser

            # Create new browser if under limit
            if len(self._browsers) < self._max_browsers:
                browser = await self._create_browser()
                browser.state = PoolItemState.IN_USE
                browser.last_used_at = datetime.now()
                return browser

            # Wait for available browser
            # (This could be improved with a queue/condition variable)
            raise RuntimeError("No browsers available and at max capacity")

    async def release(self, browser: BrowserInstance, had_error: bool = False) -> None:
        """
        Release a browser back to the pool.

        Args:
            browser: The browser instance to release
            had_error: Whether the task had an error
        """
        async with self._lock:
            if browser.id not in self._browsers:
                return

            browser.tasks_completed += 1
            self._stats["total_tasks"] += 1

            if had_error:
                browser.errors += 1
                self._stats["total_errors"] += 1

            # Check if needs recycling
            if browser.should_recycle(
                self._recycle_after_tasks,
                self._recycle_after_minutes
            ):
                await self._recycle_browser(browser)
            else:
                browser.state = PoolItemState.AVAILABLE

    async def _create_browser(self) -> BrowserInstance:
        """Create a new browser instance."""
        browser_id = str(uuid4())[:8]

        try:
            engine = await self._browser_factory()

            browser = BrowserInstance(
                id=browser_id,
                engine=engine,
                state=PoolItemState.AVAILABLE,
            )

            self._browsers[browser_id] = browser
            self._stats["browsers_created"] += 1

            logger.debug(
                "[BROWSER_POOL] Browser created",
                browser_id=browser_id,
                total_browsers=len(self._browsers),
            )

            return browser

        except Exception as e:
            logger.error(
                "[BROWSER_POOL] Failed to create browser",
                error=str(e),
            )
            raise

    async def _close_browser(self, browser: BrowserInstance) -> None:
        """Close a browser instance."""
        try:
            browser.state = PoolItemState.DEAD
            await browser.engine.close()
            logger.debug("[BROWSER_POOL] Browser closed", browser_id=browser.id)
        except Exception as e:
            logger.warning(
                "[BROWSER_POOL] Error closing browser",
                browser_id=browser.id,
                error=str(e),
            )

    async def _recycle_browser(self, browser: BrowserInstance) -> None:
        """Recycle a browser instance (close and create new)."""
        browser.state = PoolItemState.RECYCLING

        logger.info(
            "[BROWSER_POOL] Recycling browser",
            browser_id=browser.id,
            tasks_completed=browser.tasks_completed,
            errors=browser.errors,
        )

        # Close old browser
        await self._close_browser(browser)
        del self._browsers[browser.id]

        self._stats["browsers_recycled"] += 1

        # Create replacement
        try:
            await self._create_browser()
        except Exception as e:
            logger.error("[BROWSER_POOL] Failed to create replacement browser", error=str(e))

        gc.collect()

    async def _recycle_oldest_browser(self) -> None:
        """Recycle the oldest browser to free memory."""
        oldest: BrowserInstance | None = None

        for browser in self._browsers.values():
            if browser.state == PoolItemState.AVAILABLE:
                if oldest is None or browser.created_at < oldest.created_at:
                    oldest = browser

        if oldest:
            await self._recycle_browser(oldest)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)


class ContextPool:
    """
    Manages a pool of browser contexts for high-volume operations.

    Features:
    - Context reuse across tasks
    - Automatic context recycling
    - Fingerprint/proxy association
    """

    def __init__(
        self,
        browser_pool: BrowserPool,
        max_contexts_per_browser: int = 10,
        recycle_after_tasks: int = 50,
    ) -> None:
        self._browser_pool = browser_pool
        self._max_contexts_per_browser = max_contexts_per_browser
        self._recycle_after_tasks = recycle_after_tasks

        self._contexts: dict[str, ContextInstance] = {}
        self._lock = asyncio.Lock()

        # Stats
        self._stats = {
            "contexts_created": 0,
            "contexts_recycled": 0,
            "contexts_reused": 0,
        }

    @property
    def active_contexts(self) -> int:
        """Count of active contexts."""
        return sum(1 for c in self._contexts.values() if c.state != PoolItemState.DEAD)

    @property
    def stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            **self._stats,
            "active_contexts": self.active_contexts,
        }

    async def acquire(
        self,
        fingerprint: Fingerprint | None = None,
        proxy: Proxy | None = None,
    ) -> ContextInstance:
        """
        Acquire a context, creating new or reusing existing.

        Args:
            fingerprint: Optional fingerprint for the context
            proxy: Optional proxy for the context

        Returns:
            ContextInstance ready for use
        """
        async with self._lock:
            # Try to find reusable context with matching fingerprint/proxy
            # (Only if strict reuse is needed)

            # Get a browser
            browser = await self._browser_pool.acquire()

            # Count contexts for this browser
            browser_contexts = sum(
                1 for c in self._contexts.values()
                if c.browser_id == browser.id and c.state != PoolItemState.DEAD
            )

            # Create new context if under limit
            if browser_contexts < self._max_contexts_per_browser:
                context = await self._create_context(browser, fingerprint, proxy)
                return context

            # Find available context for this browser
            for ctx in self._contexts.values():
                if ctx.browser_id == browser.id and ctx.state == PoolItemState.AVAILABLE:
                    if ctx.should_recycle(self._recycle_after_tasks):
                        await self._recycle_context(ctx)
                        continue

                    ctx.state = PoolItemState.IN_USE
                    ctx.last_used_at = datetime.now()
                    self._stats["contexts_reused"] += 1

                    # Release browser back since we're reusing context
                    await self._browser_pool.release(browser)
                    return ctx

            raise RuntimeError("No contexts available for browser")

    async def release(self, context: ContextInstance, had_error: bool = False) -> None:
        """
        Release a context back to the pool.

        Args:
            context: The context to release
            had_error: Whether the task had an error
        """
        async with self._lock:
            if context.id not in self._contexts:
                return

            context.tasks_completed += 1

            # Clear page state for reuse
            if context.page:
                try:
                    # Navigate to blank to clear state
                    await context.page.goto("about:blank")
                except Exception:
                    pass

            if context.should_recycle(self._recycle_after_tasks) or had_error:
                await self._recycle_context(context)
            else:
                context.state = PoolItemState.AVAILABLE

    async def _create_context(
        self,
        browser: BrowserInstance,
        fingerprint: Fingerprint | None = None,
        proxy: Proxy | None = None,
    ) -> ContextInstance:
        """Create a new context on a browser."""
        context_id = str(uuid4())[:8]

        try:
            # Create context with fingerprint/proxy
            ctx = await browser.engine.new_context(
                fingerprint=fingerprint,
                proxy=proxy,
            )

            # Create page
            page = await ctx.new_page()

            context = ContextInstance(
                id=context_id,
                browser_id=browser.id,
                context=ctx,
                page=page,
                state=PoolItemState.IN_USE,
                fingerprint_id=fingerprint.id if fingerprint else None,
                proxy_id=proxy.id if proxy else None,
            )

            self._contexts[context_id] = context
            browser.contexts_created += 1
            self._stats["contexts_created"] += 1

            logger.debug(
                "[CONTEXT_POOL] Context created",
                context_id=context_id,
                browser_id=browser.id,
            )

            return context

        except Exception as e:
            # Release browser on failure
            await self._browser_pool.release(browser, had_error=True)
            logger.error(
                "[CONTEXT_POOL] Failed to create context",
                error=str(e),
            )
            raise

    async def _recycle_context(self, context: ContextInstance) -> None:
        """Recycle a context (close it)."""
        context.state = PoolItemState.RECYCLING

        logger.debug(
            "[CONTEXT_POOL] Recycling context",
            context_id=context.id,
            tasks_completed=context.tasks_completed,
        )

        try:
            if context.page:
                await context.page.close()
            await context.context.close()
        except Exception as e:
            logger.warning(
                "[CONTEXT_POOL] Error closing context",
                context_id=context.id,
                error=str(e),
            )

        context.state = PoolItemState.DEAD
        del self._contexts[context.id]
        self._stats["contexts_recycled"] += 1

    async def cleanup(self) -> None:
        """Clean up all contexts."""
        async with self._lock:
            for context in list(self._contexts.values()):
                await self._recycle_context(context)
            self._contexts.clear()


class HighVolumeExecutor:
    """
    High-volume task executor using browser and context pools.

    Designed for 1000+ concurrent operations over extended periods.
    """

    def __init__(
        self,
        browser_factory: Any,
        max_browsers: int = 10,
        max_contexts_per_browser: int = 10,
        max_concurrent: int = 100,
        memory_limit_mb: int = 0,
    ) -> None:
        self._browser_pool = BrowserPool(
            browser_factory=browser_factory,
            max_browsers=max_browsers,
            max_contexts_per_browser=max_contexts_per_browser,
            memory_limit_mb=memory_limit_mb,
        )

        self._context_pool = ContextPool(
            browser_pool=self._browser_pool,
            max_contexts_per_browser=max_contexts_per_browser,
        )

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False

        # Stats
        self._stats = {
            "tasks_started": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
        }

    @property
    def stats(self) -> dict[str, Any]:
        """Get executor statistics."""
        return {
            **self._stats,
            "browser_pool": self._browser_pool.stats,
            "context_pool": self._context_pool.stats,
        }

    async def start(self) -> None:
        """Start the executor."""
        if self._running:
            return

        self._running = True
        await self._browser_pool.start()

        logger.info("[HIGH_VOLUME] Executor started")

    async def stop(self) -> None:
        """Stop the executor."""
        if not self._running:
            return

        self._running = False
        await self._context_pool.cleanup()
        await self._browser_pool.stop()

        logger.info("[HIGH_VOLUME] Executor stopped", stats=self._stats)

    async def execute(
        self,
        task_func: Any,
        fingerprint: Fingerprint | None = None,
        proxy: Proxy | None = None,
    ) -> Any:
        """
        Execute a task with pooled browser/context.

        Args:
            task_func: Async function that takes (page) as argument
            fingerprint: Optional fingerprint
            proxy: Optional proxy

        Returns:
            Result from task_func
        """
        await self._semaphore.acquire()

        self._stats["tasks_started"] += 1
        context: ContextInstance | None = None
        had_error = False

        try:
            context = await self._context_pool.acquire(fingerprint, proxy)
            result = await task_func(context.page)
            self._stats["tasks_completed"] += 1
            return result

        except Exception:
            self._stats["tasks_failed"] += 1
            had_error = True
            raise

        finally:
            if context:
                await self._context_pool.release(context, had_error)
            self._semaphore.release()
