"""Worker pool implementation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

if TYPE_CHECKING:
    from ghoststorm.core.models.task import Task, TaskResult

logger = structlog.get_logger(__name__)


class WorkerState(str, Enum):
    """Worker lifecycle states."""

    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerStats:
    """Worker statistics."""

    tasks_completed: int = 0
    tasks_failed: int = 0
    total_duration_ms: float = 0
    last_task_at: datetime | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def avg_task_duration_ms(self) -> float:
        """Calculate average task duration."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0
        return self.total_duration_ms / total


@dataclass
class Worker:
    """Represents a single worker in the pool."""

    id: str
    state: WorkerState = WorkerState.IDLE
    current_task: Task | None = None
    stats: WorkerStats = field(default_factory=WorkerStats)
    created_at: datetime = field(default_factory=datetime.now)


# Type alias for task executor function
TaskExecutor = Callable[["Task"], Coroutine[Any, Any, "TaskResult"]]


class WorkerPool:
    """
    Manages a pool of concurrent workers.

    Provides controlled parallelism for task execution.
    """

    def __init__(
        self,
        max_workers: int = 10,
        task_timeout: float = 120.0,
    ) -> None:
        """
        Initialize worker pool.

        Args:
            max_workers: Maximum concurrent workers
            task_timeout: Default task timeout in seconds
        """
        self._max_workers = max_workers
        self._task_timeout = task_timeout

        # Worker management
        self._workers: dict[str, Worker] = {}
        self._semaphore = asyncio.Semaphore(max_workers)
        self._lock = asyncio.Lock()

        # State
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Stats
        self._stats = {
            "total_tasks_executed": 0,
            "total_tasks_succeeded": 0,
            "total_tasks_failed": 0,
            "total_tasks_timeout": 0,
        }

    @property
    def max_workers(self) -> int:
        """Get maximum worker count."""
        return self._max_workers

    @property
    def active_workers(self) -> int:
        """Get count of active workers."""
        return sum(1 for w in self._workers.values() if w.state == WorkerState.BUSY)

    @property
    def idle_workers(self) -> int:
        """Get count of idle workers."""
        return self._max_workers - self.active_workers

    @property
    def is_running(self) -> bool:
        """Check if pool is running."""
        return self._running

    @property
    def stats(self) -> dict[str, int]:
        """Get pool statistics."""
        return self._stats.copy()

    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()
        logger.info("Worker pool started", max_workers=self._max_workers)

    async def stop(self, timeout: float = 30.0) -> None:
        """
        Stop the worker pool gracefully.

        Args:
            timeout: Maximum time to wait for workers to finish
        """
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # Wait for all workers to finish
        async with self._lock:
            busy_workers = [w for w in self._workers.values() if w.state == WorkerState.BUSY]

        if busy_workers:
            logger.info("Waiting for workers to finish", count=len(busy_workers))

            # Give workers time to finish
            for _ in range(int(timeout)):
                await asyncio.sleep(1)
                async with self._lock:
                    busy_count = sum(
                        1 for w in self._workers.values() if w.state == WorkerState.BUSY
                    )
                if busy_count == 0:
                    break

        logger.info("Worker pool stopped")

    async def execute(
        self,
        task: Task,
        executor: TaskExecutor,
        timeout: float | None = None,
    ) -> TaskResult:
        """
        Execute a task using an available worker.

        Args:
            task: Task to execute
            executor: Function to execute the task
            timeout: Optional timeout override

        Returns:
            TaskResult from execution
        """
        from ghoststorm.core.models.task import TaskResult, TaskStatus

        if not self._running:
            raise RuntimeError("Worker pool is not running")

        timeout = timeout or self._task_timeout

        # Acquire semaphore to limit concurrency
        await self._semaphore.acquire()

        worker = await self._get_or_create_worker()

        try:
            async with self._lock:
                worker.state = WorkerState.BUSY
                worker.current_task = task

            # Execute with timeout
            started_at = datetime.now()
            task.start(worker.id)

            try:
                result = await asyncio.wait_for(executor(task), timeout=timeout)
                self._stats["total_tasks_succeeded"] += 1
                worker.stats.tasks_completed += 1

            except TimeoutError:
                self._stats["total_tasks_timeout"] += 1
                self._stats["total_tasks_failed"] += 1
                worker.stats.tasks_failed += 1
                worker.stats.errors.append(f"Timeout after {timeout}s")

                result = TaskResult(
                    task_id=task.id,
                    success=False,
                    status=TaskStatus.FAILED,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    duration_ms=(datetime.now() - started_at).total_seconds() * 1000,
                    error=f"Task timeout after {timeout}s",
                    error_type="TimeoutError",
                )

            except Exception as e:
                self._stats["total_tasks_failed"] += 1
                worker.stats.tasks_failed += 1
                worker.stats.errors.append(str(e))

                result = TaskResult(
                    task_id=task.id,
                    success=False,
                    status=TaskStatus.FAILED,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    duration_ms=(datetime.now() - started_at).total_seconds() * 1000,
                    error=str(e),
                    error_type=type(e).__name__,
                )

            # Update stats
            self._stats["total_tasks_executed"] += 1
            worker.stats.total_duration_ms += result.duration_ms
            worker.stats.last_task_at = datetime.now()

            return result

        finally:
            async with self._lock:
                worker.state = WorkerState.IDLE
                worker.current_task = None

            self._semaphore.release()

    async def execute_batch(
        self,
        tasks: list[Task],
        executor: TaskExecutor,
        on_complete: Callable[[Task, TaskResult], Coroutine[Any, Any, None]] | None = None,
        on_error: Callable[[Task, Exception], Coroutine[Any, Any, None]] | None = None,
    ) -> list[TaskResult]:
        """
        Execute multiple tasks concurrently.

        Args:
            tasks: Tasks to execute
            executor: Task executor function
            on_complete: Optional callback for each completed task
            on_error: Optional callback for each failed task

        Returns:
            List of TaskResults
        """

        async def execute_with_callback(task: Task) -> TaskResult:
            result = await self.execute(task, executor)

            if on_complete:
                try:
                    await on_complete(task, result)
                except Exception as e:
                    logger.warning("on_complete callback failed", error=str(e))

            if not result.success and on_error:
                try:
                    await on_error(task, Exception(result.error or "Unknown error"))
                except Exception as e:
                    logger.warning("on_error callback failed", error=str(e))

            return result

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[execute_with_callback(task) for task in tasks],
            return_exceptions=True,
        )

        # Convert exceptions to TaskResults
        from ghoststorm.core.models.task import TaskResult, TaskStatus

        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    TaskResult(
                        task_id=tasks[i].id,
                        success=False,
                        status=TaskStatus.FAILED,
                        started_at=datetime.now(),
                        completed_at=datetime.now(),
                        duration_ms=0,
                        error=str(result),
                        error_type=type(result).__name__,
                    )
                )
            else:
                final_results.append(result)

        return final_results

    async def _get_or_create_worker(self) -> Worker:
        """Get an idle worker or create a new one."""
        async with self._lock:
            # Find an idle worker
            for worker in self._workers.values():
                if worker.state == WorkerState.IDLE:
                    return worker

            # Create new worker
            worker_id = str(uuid4())[:8]
            worker = Worker(id=worker_id)
            self._workers[worker_id] = worker

            logger.debug("Worker created", worker_id=worker_id)
            return worker

    def get_worker_stats(self) -> list[dict[str, Any]]:
        """Get statistics for all workers."""
        return [
            {
                "id": w.id,
                "state": w.state.value,
                "tasks_completed": w.stats.tasks_completed,
                "tasks_failed": w.stats.tasks_failed,
                "avg_duration_ms": w.stats.avg_task_duration_ms,
                "current_task": w.current_task.id if w.current_task else None,
            }
            for w in self._workers.values()
        ]

    async def scale(self, new_max_workers: int) -> None:
        """
        Scale the worker pool.

        Args:
            new_max_workers: New maximum worker count
        """
        if new_max_workers < 1:
            raise ValueError("max_workers must be at least 1")

        old_max = self._max_workers
        self._max_workers = new_max_workers

        # Adjust semaphore
        if new_max_workers > old_max:
            # Add permits
            for _ in range(new_max_workers - old_max):
                self._semaphore.release()
        elif new_max_workers < old_max:
            # Remove permits (will block new tasks until workers free up)
            for _ in range(old_max - new_max_workers):
                await self._semaphore.acquire()

        logger.info(
            "Worker pool scaled",
            old_max=old_max,
            new_max=new_max_workers,
        )
