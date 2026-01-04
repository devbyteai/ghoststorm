"""Flow data models for goal-based flow recording and replay."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class CheckpointType(str, Enum):
    """Type of checkpoint in a recorded flow."""

    NAVIGATION = "navigation"  # Navigate to URL/page
    CLICK = "click"  # Click on element
    INPUT = "input"  # Enter text into field
    WAIT = "wait"  # Wait for condition
    SCROLL = "scroll"  # Scroll to element/position
    EXTERNAL = "external"  # External action (e.g., solve captcha)
    CUSTOM = "custom"  # Custom goal description


class FlowStatus(str, Enum):
    """Status of a recorded flow."""

    DRAFT = "draft"  # Currently being recorded
    READY = "ready"  # Recording complete, ready for replay
    DISABLED = "disabled"  # Temporarily disabled


class VariationLevel(str, Enum):
    """How much the LLM should deviate from recorded behavior."""

    LOW = "low"  # Minimal variation, stick close to recording
    MEDIUM = "medium"  # Balanced variation
    HIGH = "high"  # Maximum variation, very different paths


@dataclass
class TimingConfig:
    """Timing configuration for a checkpoint."""

    min_delay: float = 0.5  # Minimum wait before checkpoint (seconds)
    max_delay: float = 3.0  # Maximum wait before checkpoint (seconds)
    timeout: float = 30.0  # Max time to achieve checkpoint


@dataclass
class Checkpoint:
    """A goal/checkpoint in a recorded flow."""

    id: str = field(default_factory=lambda: str(uuid4()))
    checkpoint_type: CheckpointType = CheckpointType.CUSTOM
    goal: str = ""  # Natural language description of the goal

    # URL context
    url_pattern: str | None = None  # Regex pattern for expected URL

    # Element context (hints for LLM, not exact selectors)
    element_description: str | None = None  # "the login button", "email input field"
    selector_hints: list[str] = field(default_factory=list)  # CSS/XPath hints

    # For INPUT type
    input_value: str | None = None  # Value to input (can have placeholders like {email})

    # Timing
    timing: TimingConfig = field(default_factory=TimingConfig)

    # Reference screenshot (base64)
    reference_screenshot: str | None = None

    # Order in flow
    order: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "checkpoint_type": self.checkpoint_type.value,
            "goal": self.goal,
            "url_pattern": self.url_pattern,
            "element_description": self.element_description,
            "selector_hints": self.selector_hints,
            "input_value": self.input_value,
            "timing": {
                "min_delay": self.timing.min_delay,
                "max_delay": self.timing.max_delay,
                "timeout": self.timing.timeout,
            },
            "reference_screenshot": self.reference_screenshot,
            "order": self.order,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        """Create from dictionary."""
        timing_data = data.get("timing", {})
        timing = TimingConfig(
            min_delay=timing_data.get("min_delay", 0.5),
            max_delay=timing_data.get("max_delay", 3.0),
            timeout=timing_data.get("timeout", 30.0),
        )

        return cls(
            id=data.get("id", str(uuid4())),
            checkpoint_type=CheckpointType(data.get("checkpoint_type", "custom")),
            goal=data.get("goal", ""),
            url_pattern=data.get("url_pattern"),
            element_description=data.get("element_description"),
            selector_hints=data.get("selector_hints", []),
            input_value=data.get("input_value"),
            timing=timing,
            reference_screenshot=data.get("reference_screenshot"),
            order=data.get("order", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RecordedFlow:
    """A recorded flow consisting of goal-based checkpoints."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: FlowStatus = FlowStatus.DRAFT

    # Starting point
    start_url: str = ""

    # Checkpoints (goals)
    checkpoints: list[Checkpoint] = field(default_factory=list)

    # Summary goal (overall objective)
    summary_goal: str = ""  # "Login to the website and navigate to settings"

    # Recording metadata
    recorded_with_browser: str = "patchright"  # Always patchright for recording

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Execution stats
    times_executed: int = 0
    successful_executions: int = 0

    # Tags for organization
    tags: list[str] = field(default_factory=list)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.times_executed == 0:
            return 0.0
        return self.successful_executions / self.times_executed

    @property
    def checkpoint_count(self) -> int:
        """Get number of checkpoints."""
        return len(self.checkpoints)

    def add_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Add a checkpoint to the flow."""
        checkpoint.order = len(self.checkpoints)
        self.checkpoints.append(checkpoint)
        self.updated_at = datetime.now()

    def remove_checkpoint(self, checkpoint_id: str) -> bool:
        """Remove a checkpoint by ID."""
        for i, cp in enumerate(self.checkpoints):
            if cp.id == checkpoint_id:
                self.checkpoints.pop(i)
                # Reorder remaining checkpoints
                for j, remaining in enumerate(self.checkpoints):
                    remaining.order = j
                self.updated_at = datetime.now()
                return True
        return False

    def finalize(self) -> None:
        """Mark flow as ready for replay."""
        self.status = FlowStatus.READY
        self.updated_at = datetime.now()

    def record_execution(self, success: bool) -> None:
        """Record an execution result."""
        self.times_executed += 1
        if success:
            self.successful_executions += 1
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "start_url": self.start_url,
            "checkpoints": [cp.to_dict() for cp in self.checkpoints],
            "summary_goal": self.summary_goal,
            "recorded_with_browser": self.recorded_with_browser,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "times_executed": self.times_executed,
            "successful_executions": self.successful_executions,
            "success_rate": self.success_rate,
            "checkpoint_count": self.checkpoint_count,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecordedFlow:
        """Create from dictionary."""
        checkpoints = [
            Checkpoint.from_dict(cp_data)
            for cp_data in data.get("checkpoints", [])
        ]

        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=FlowStatus(data.get("status", "draft")),
            start_url=data.get("start_url", ""),
            checkpoints=checkpoints,
            summary_goal=data.get("summary_goal", ""),
            recorded_with_browser=data.get("recorded_with_browser", "patchright"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            times_executed=data.get("times_executed", 0),
            successful_executions=data.get("successful_executions", 0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FlowExecutionConfig:
    """Configuration for executing a recorded flow."""

    flow_id: str = ""

    # Browser choice for replay (can differ from recording)
    browser_engine: str = "camoufox"  # Default to highest stealth for replay

    # Variation level
    variation_level: VariationLevel = VariationLevel.MEDIUM

    # Proxy settings
    use_proxy: bool = True
    proxy_pool: str | None = None  # Proxy pool ID

    # Concurrency
    workers: int = 1

    # Input substitutions (for placeholders in checkpoints)
    substitutions: dict[str, str] = field(default_factory=dict)  # {email: "test@example.com"}

    # Timeout per checkpoint
    checkpoint_timeout: float = 60.0

    # Retry settings
    max_retries: int = 2
    retry_delay: float = 5.0

    # Screenshots
    capture_screenshots: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "flow_id": self.flow_id,
            "browser_engine": self.browser_engine,
            "variation_level": self.variation_level.value,
            "use_proxy": self.use_proxy,
            "proxy_pool": self.proxy_pool,
            "workers": self.workers,
            "substitutions": self.substitutions,
            "checkpoint_timeout": self.checkpoint_timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "capture_screenshots": self.capture_screenshots,
        }


@dataclass
class FlowExecutionResult:
    """Result of a flow execution."""

    flow_id: str
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    success: bool = False

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    # Checkpoint progress
    checkpoints_completed: int = 0
    total_checkpoints: int = 0

    # Failed checkpoint info
    failed_at_checkpoint: str | None = None  # Checkpoint ID where it failed
    error: str | None = None

    # Browser/proxy used
    browser_engine: str = ""
    proxy_used: str | None = None

    # Screenshots captured
    screenshots: list[str] = field(default_factory=list)  # Paths to screenshots

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float | None:
        """Get execution duration in seconds."""
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def progress(self) -> float:
        """Get completion progress (0.0 to 1.0)."""
        if self.total_checkpoints == 0:
            return 0.0
        return self.checkpoints_completed / self.total_checkpoints

    def complete(self, success: bool, error: str | None = None) -> None:
        """Mark execution as complete."""
        self.success = success
        self.completed_at = datetime.now()
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "flow_id": self.flow_id,
            "execution_id": self.execution_id,
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "checkpoints_completed": self.checkpoints_completed,
            "total_checkpoints": self.total_checkpoints,
            "progress": self.progress,
            "failed_at_checkpoint": self.failed_at_checkpoint,
            "error": self.error,
            "browser_engine": self.browser_engine,
            "proxy_used": self.proxy_used,
            "screenshots": self.screenshots,
            "metadata": self.metadata,
        }
