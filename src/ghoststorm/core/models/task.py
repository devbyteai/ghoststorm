"""Task data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskType(str, Enum):
    """Type of task to execute."""

    VISIT = "visit"
    SCRAPE = "scrape"
    LOAD_TEST = "load_test"
    CLICK = "click"
    SCREENSHOT = "screenshot"
    CUSTOM = "custom"
    RECORDED_FLOW = "recorded_flow"  # Execute a recorded goal-based flow


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(int, Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class LLMMode(str, Enum):
    """LLM control mode for task execution."""

    OFF = "off"  # No LLM involvement
    ASSIST = "assist"  # LLM suggests, human approves
    AUTONOMOUS = "autonomous"  # LLM executes automatically


@dataclass
class TaskConfig:
    """Task-specific configuration."""

    # Navigation
    wait_until: str = "load"  # load, domcontentloaded, networkidle
    timeout: float = 30.0

    # Behavior
    human_simulation: bool = True
    scroll_page: bool = True
    dwell_time: tuple[float, float] = (5.0, 15.0)  # min, max seconds

    # Screenshots
    take_screenshot: bool = False
    screenshot_full_page: bool = False

    # Extraction
    extract_selectors: dict[str, str] = field(default_factory=dict)

    # Clicks
    click_selectors: list[str] = field(default_factory=list)
    click_strategy: str = "sequential"  # sequential, random, all

    # Retry
    max_retries: int = 3
    retry_delay: float = 2.0

    # Custom script
    custom_script: str | None = None

    # LLM integration
    llm_mode: LLMMode = LLMMode.OFF
    llm_provider: str | None = None  # openai, anthropic, ollama (None = use default)
    llm_task: str | None = None  # Natural language task description

    # DOM intelligence
    extract_dom: bool = False  # Extract DOM state for LLM analysis

    # Recorded flow execution
    flow_id: str | None = None  # ID of recorded flow to execute
    flow_variation_level: str = "medium"  # low, medium, high - how much to deviate from recording
    flow_browser_engine: str = "camoufox"  # Browser engine for flow replay


@dataclass
class Task:
    """Represents a task to be executed."""

    url: str
    task_type: TaskType = TaskType.VISIT
    id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    config: TaskConfig = field(default_factory=TaskConfig)

    # Scheduling
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    scheduled_at: datetime | None = None

    # Execution tracking
    attempt: int = 0
    worker_id: str | None = None
    proxy_id: str | None = None
    fingerprint_id: str | None = None

    # Metadata
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Parent task (for subtasks)
    parent_id: str | None = None

    def start(self, worker_id: str) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        self.worker_id = worker_id
        self.attempt += 1

    def complete(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def fail(self) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()

    def retry(self) -> bool:
        """Attempt to retry the task."""
        if self.attempt < self.config.max_retries:
            self.status = TaskStatus.RETRYING
            return True
        self.fail()
        return False

    def cancel(self) -> None:
        """Cancel the task."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()

    @property
    def duration(self) -> float | None:
        """Get task duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    @property
    def is_finished(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "attempt": self.attempt,
            "worker_id": self.worker_id,
            "proxy_id": self.proxy_id,
            "fingerprint_id": self.fingerprint_id,
            "duration": self.duration,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class TaskResult:
    """Result of task execution."""

    task_id: str
    success: bool
    status: TaskStatus

    # Timing
    started_at: datetime
    completed_at: datetime
    duration_ms: float

    # Response data
    final_url: str | None = None
    status_code: int | None = None
    page_title: str | None = None

    # Extracted data
    extracted_data: dict[str, Any] = field(default_factory=dict)

    # Screenshots
    screenshot_path: str | None = None

    # Error info
    error: str | None = None
    error_type: str | None = None
    traceback: str | None = None

    # Resource usage
    proxy_used: str | None = None
    fingerprint_used: str | None = None
    bytes_downloaded: int = 0
    requests_made: int = 0

    # Detection info
    captcha_detected: bool = False
    captcha_solved: bool = False
    bot_detected: bool = False

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_ms": self.duration_ms,
            "final_url": self.final_url,
            "status_code": self.status_code,
            "page_title": self.page_title,
            "extracted_data": self.extracted_data,
            "screenshot_path": self.screenshot_path,
            "error": self.error,
            "error_type": self.error_type,
            "proxy_used": self.proxy_used,
            "fingerprint_used": self.fingerprint_used,
            "bytes_downloaded": self.bytes_downloaded,
            "requests_made": self.requests_made,
            "captcha_detected": self.captcha_detected,
            "captcha_solved": self.captcha_solved,
            "bot_detected": self.bot_detected,
            "metadata": self.metadata,
        }


@dataclass
class BatchResult:
    """Result of batch task execution."""

    batch_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int

    started_at: datetime
    completed_at: datetime | None = None

    results: list[TaskResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    @property
    def duration(self) -> float | None:
        """Get batch duration in seconds."""
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def is_finished(self) -> bool:
        """Check if all tasks are finished."""
        return (self.completed_tasks + self.failed_tasks + self.cancelled_tasks) == self.total_tasks

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "cancelled_tasks": self.cancelled_tasks,
            "success_rate": self.success_rate,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "is_finished": self.is_finished,
        }
