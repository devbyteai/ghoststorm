"""Task scheduler implementation."""

from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ghoststorm.core.models.task import Task

logger = structlog.get_logger(__name__)


@dataclass(order=True)
class PriorityTask:
    """Wrapper for priority queue ordering."""

    priority: int
    timestamp: float
    task: Any = field(compare=False)

    @classmethod
    def from_task(cls, task: Task) -> PriorityTask:
        """Create from a Task."""
        # Negate priority so higher priority comes first
        return cls(
            priority=-task.priority.value,
            timestamp=task.created_at.timestamp(),
            task=task,
        )


class TaskScheduler:
    """
    Priority-based task scheduler.

    Manages task queue with priority ordering and rate limiting.
    """

    def __init__(
        self,
        max_queue_size: int = 10000,
        rate_limit_per_minute: int | None = None,
    ) -> None:
        """
        Initialize scheduler.

        Args:
            max_queue_size: Maximum queue size
            rate_limit_per_minute: Optional rate limit
        """
        self._queue: list[PriorityTask] = []
        self._queue_lock = asyncio.Lock()
        self._max_size = max_queue_size
        self._rate_limit = rate_limit_per_minute

        # Rate limiting state
        self._request_times: list[float] = []
        self._rate_lock = asyncio.Lock()

        # Stats
        self._stats = {
            "tasks_queued": 0,
            "tasks_dequeued": 0,
            "tasks_cancelled": 0,
            "rate_limit_waits": 0,
        }

        # Task lookup for cancellation
        self._task_ids: set[str] = set()

        # Condition for waiting on empty queue
        self._not_empty = asyncio.Condition()

    @property
    def size(self) -> int:
        """Get current queue size."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    @property
    def is_full(self) -> bool:
        """Check if queue is full."""
        return len(self._queue) >= self._max_size

    @property
    def stats(self) -> dict[str, int]:
        """Get scheduler statistics."""
        return self._stats.copy()

    async def enqueue(self, task: Task) -> bool:
        """
        Add a task to the queue.

        Args:
            task: Task to enqueue

        Returns:
            True if enqueued, False if queue full or duplicate
        """
        async with self._queue_lock:
            if len(self._queue) >= self._max_size:
                logger.warning("Queue full, rejecting task", task_id=task.id)
                return False

            if task.id in self._task_ids:
                logger.warning("Duplicate task rejected", task_id=task.id)
                return False

            priority_task = PriorityTask.from_task(task)
            heapq.heappush(self._queue, priority_task)
            self._task_ids.add(task.id)
            self._stats["tasks_queued"] += 1

            logger.debug(
                "Task enqueued",
                task_id=task.id,
                priority=task.priority.value,
                queue_size=len(self._queue),
            )

        # Notify waiters
        async with self._not_empty:
            self._not_empty.notify()

        return True

    async def enqueue_many(self, tasks: list[Task]) -> int:
        """
        Add multiple tasks to the queue.

        Args:
            tasks: Tasks to enqueue

        Returns:
            Number of tasks successfully enqueued
        """
        count = 0
        for task in tasks:
            if await self.enqueue(task):
                count += 1
        return count

    async def dequeue(self, timeout: float | None = None) -> Task | None:
        """
        Get the highest priority task from the queue.

        Args:
            timeout: Maximum time to wait for a task

        Returns:
            Task or None if timeout
        """
        # Wait for rate limit if configured
        if self._rate_limit:
            await self._wait_for_rate_limit()

        async with self._not_empty:
            # Wait for a task to be available
            while self.is_empty:
                try:
                    await asyncio.wait_for(self._not_empty.wait(), timeout=timeout)
                except TimeoutError:
                    return None

        async with self._queue_lock:
            if self._queue:
                priority_task = heapq.heappop(self._queue)
                self._task_ids.discard(priority_task.task.id)
                self._stats["tasks_dequeued"] += 1

                logger.debug(
                    "Task dequeued",
                    task_id=priority_task.task.id,
                    queue_size=len(self._queue),
                )

                return priority_task.task

        return None

    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a queued task.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if task was found and cancelled
        """
        async with self._queue_lock:
            if task_id not in self._task_ids:
                return False

            # Find and remove the task
            self._queue = [pt for pt in self._queue if pt.task.id != task_id]
            heapq.heapify(self._queue)
            self._task_ids.discard(task_id)
            self._stats["tasks_cancelled"] += 1

            logger.debug("Task cancelled", task_id=task_id)
            return True

    async def clear(self) -> int:
        """
        Clear all tasks from the queue.

        Returns:
            Number of tasks cleared
        """
        async with self._queue_lock:
            count = len(self._queue)
            self._queue.clear()
            self._task_ids.clear()
            return count

    async def peek(self) -> Task | None:
        """
        Peek at the highest priority task without removing it.

        Returns:
            Task or None if queue empty
        """
        async with self._queue_lock:
            if self._queue:
                return self._queue[0].task
            return None

    async def _wait_for_rate_limit(self) -> None:
        """Wait if rate limit is exceeded."""
        if not self._rate_limit:
            return

        async with self._rate_lock:
            now = asyncio.get_event_loop().time()

            # Remove old request times
            cutoff = now - 60.0
            self._request_times = [t for t in self._request_times if t > cutoff]

            # Check if at limit
            if len(self._request_times) >= self._rate_limit:
                # Wait until oldest request expires
                wait_time = self._request_times[0] - cutoff
                if wait_time > 0:
                    self._stats["rate_limit_waits"] += 1
                    logger.debug("Rate limit wait", wait_time=wait_time)
                    await asyncio.sleep(wait_time)

            # Record this request
            self._request_times.append(now)

    def contains(self, task_id: str) -> bool:
        """Check if a task is in the queue."""
        return task_id in self._task_ids

    def get_pending_tasks(self, limit: int = 100) -> list[Task]:
        """Get a list of pending tasks (for inspection)."""
        sorted_queue = sorted(self._queue)
        return [pt.task for pt in sorted_queue[:limit]]
