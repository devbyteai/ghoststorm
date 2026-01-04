"""Comprehensive tests for Task, TaskConfig, TaskResult, and BatchResult classes."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from uuid import UUID

from ghoststorm.core.models.task import (
    BatchResult,
    Task,
    TaskConfig,
    TaskPriority,
    TaskResult,
    TaskStatus,
    TaskType,
)

# ============================================================================
# TASKTYPE ENUM TESTS
# ============================================================================


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_values(self):
        """Test all TaskType enum values exist with correct string values."""
        assert TaskType.VISIT.value == "visit"
        assert TaskType.SCRAPE.value == "scrape"
        assert TaskType.LOAD_TEST.value == "load_test"
        assert TaskType.CLICK.value == "click"
        assert TaskType.SCREENSHOT.value == "screenshot"
        assert TaskType.CUSTOM.value == "custom"

    def test_task_type_count(self):
        """Test that TaskType has exactly 7 values."""
        assert len(TaskType) == 7

    def test_task_type_is_str_enum(self):
        """Test that TaskType inherits from str for easy serialization."""
        assert isinstance(TaskType.VISIT, str)
        # StrEnum.value gives the string value for serialization
        assert TaskType.VISIT.value == "visit"

    def test_task_type_from_value(self):
        """Test creating TaskType from string value."""
        assert TaskType("visit") == TaskType.VISIT
        assert TaskType("scrape") == TaskType.SCRAPE


# ============================================================================
# TASKSTATUS ENUM TESTS
# ============================================================================


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self):
        """Test all TaskStatus enum values exist with correct string values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.RETRYING.value == "retrying"

    def test_task_status_count(self):
        """Test that TaskStatus has exactly 7 values."""
        assert len(TaskStatus) == 7

    def test_task_status_is_str_enum(self):
        """Test that TaskStatus inherits from str for easy serialization."""
        assert isinstance(TaskStatus.PENDING, str)
        # StrEnum.value gives the string value for serialization
        assert TaskStatus.RUNNING.value == "running"

    def test_task_status_from_value(self):
        """Test creating TaskStatus from string value."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("completed") == TaskStatus.COMPLETED


# ============================================================================
# TASKPRIORITY ENUM TESTS
# ============================================================================


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_task_priority_values(self):
        """Test all TaskPriority enum values with correct integer values."""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 5
        assert TaskPriority.HIGH.value == 10
        assert TaskPriority.CRITICAL.value == 20

    def test_task_priority_count(self):
        """Test that TaskPriority has exactly 4 values."""
        assert len(TaskPriority) == 4

    def test_task_priority_is_int_enum(self):
        """Test that TaskPriority inherits from int for comparison."""
        assert isinstance(TaskPriority.LOW, int)
        assert TaskPriority.HIGH > TaskPriority.NORMAL
        assert TaskPriority.CRITICAL > TaskPriority.HIGH

    def test_task_priority_ordering(self):
        """Test that priorities are correctly ordered."""
        assert TaskPriority.LOW < TaskPriority.NORMAL < TaskPriority.HIGH < TaskPriority.CRITICAL

    def test_task_priority_arithmetic(self):
        """Test that TaskPriority supports int arithmetic."""
        assert TaskPriority.LOW + TaskPriority.NORMAL == 6
        assert TaskPriority.CRITICAL - TaskPriority.HIGH == 10


# ============================================================================
# TASKCONFIG TESTS
# ============================================================================


class TestTaskConfig:
    """Tests for TaskConfig dataclass."""

    def test_task_config_defaults(self):
        """Test TaskConfig default values."""
        config = TaskConfig()

        assert config.wait_until == "load"
        assert config.timeout == 30.0
        assert config.human_simulation is True
        assert config.scroll_page is True
        assert config.dwell_time == (5.0, 15.0)
        assert config.take_screenshot is False
        assert config.screenshot_full_page is False
        assert config.extract_selectors == {}
        assert config.click_selectors == []
        assert config.click_strategy == "sequential"
        assert config.max_retries == 3
        assert config.retry_delay == 2.0
        assert config.custom_script is None

    def test_task_config_dwell_time_tuple(self):
        """Test dwell_time is a proper tuple with min/max seconds."""
        config = TaskConfig()
        min_dwell, max_dwell = config.dwell_time

        assert min_dwell == 5.0
        assert max_dwell == 15.0
        assert min_dwell < max_dwell

    def test_task_config_custom_dwell_time(self):
        """Test setting custom dwell_time values."""
        config = TaskConfig(dwell_time=(1.0, 3.0))

        assert config.dwell_time == (1.0, 3.0)

    def test_task_config_click_strategy_values(self):
        """Test different click_strategy values."""
        sequential = TaskConfig(click_strategy="sequential")
        random_config = TaskConfig(click_strategy="random")
        all_config = TaskConfig(click_strategy="all")

        assert sequential.click_strategy == "sequential"
        assert random_config.click_strategy == "random"
        assert all_config.click_strategy == "all"

    def test_task_config_max_retries(self):
        """Test max_retries configuration."""
        config = TaskConfig(max_retries=5)
        assert config.max_retries == 5

    def test_task_config_extract_selectors(self):
        """Test extract_selectors as mutable default."""
        config1 = TaskConfig()
        config2 = TaskConfig()

        config1.extract_selectors["title"] = "h1"

        # Ensure mutable default is not shared
        assert config1.extract_selectors != config2.extract_selectors

    def test_task_config_click_selectors(self):
        """Test click_selectors as mutable default."""
        config1 = TaskConfig()
        config2 = TaskConfig()

        config1.click_selectors.append("button.submit")

        # Ensure mutable default is not shared
        assert config1.click_selectors != config2.click_selectors

    def test_task_config_custom_script(self):
        """Test custom_script configuration."""
        script = "document.querySelector('button').click()"
        config = TaskConfig(custom_script=script)

        assert config.custom_script == script


# ============================================================================
# TASK TESTS - CREATION
# ============================================================================


class TestTaskCreation:
    """Tests for Task creation and defaults."""

    def test_task_creation_minimal(self):
        """Test creating a Task with only required URL."""
        task = Task(url="https://example.com")

        assert task.url == "https://example.com"
        assert task.task_type == TaskType.VISIT
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL

    def test_task_creation_with_type(self):
        """Test creating Tasks with different types."""
        scrape_task = Task(url="https://example.com", task_type=TaskType.SCRAPE)
        click_task = Task(url="https://example.com", task_type=TaskType.CLICK)

        assert scrape_task.task_type == TaskType.SCRAPE
        assert click_task.task_type == TaskType.CLICK

    def test_task_id_generation(self):
        """Test that task ID is auto-generated as valid UUID."""
        task = Task(url="https://example.com")

        # Should be valid UUID format
        UUID(task.id)
        assert len(task.id) == 36  # UUID string length

    def test_task_unique_ids(self):
        """Test that each task gets a unique ID."""
        task1 = Task(url="https://example.com")
        task2 = Task(url="https://example.com")

        assert task1.id != task2.id

    def test_task_custom_id(self):
        """Test setting a custom task ID."""
        task = Task(url="https://example.com", id="custom-task-id")
        assert task.id == "custom-task-id"

    def test_task_created_at_auto(self):
        """Test that created_at is automatically set."""
        before = datetime.now()
        task = Task(url="https://example.com")
        after = datetime.now()

        assert before <= task.created_at <= after

    def test_task_default_timestamps(self):
        """Test that execution timestamps start as None."""
        task = Task(url="https://example.com")

        assert task.started_at is None
        assert task.completed_at is None
        assert task.scheduled_at is None

    def test_task_default_tracking(self):
        """Test default execution tracking values."""
        task = Task(url="https://example.com")

        assert task.attempt == 0
        assert task.worker_id is None
        assert task.proxy_id is None
        assert task.fingerprint_id is None

    def test_task_default_metadata(self):
        """Test default metadata values."""
        task = Task(url="https://example.com")

        assert task.tags == []
        assert task.metadata == {}
        assert task.parent_id is None

    def test_task_config_default(self):
        """Test that Task gets a default TaskConfig."""
        task = Task(url="https://example.com")

        assert isinstance(task.config, TaskConfig)
        assert task.config.max_retries == 3


# ============================================================================
# TASK TESTS - START METHOD
# ============================================================================


class TestTaskStart:
    """Tests for Task.start() method."""

    def test_task_start_sets_running_status(self):
        """Test that start() sets status to RUNNING."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")

        assert task.status == TaskStatus.RUNNING

    def test_task_start_sets_started_at(self):
        """Test that start() sets started_at timestamp."""
        task = Task(url="https://example.com")
        before = datetime.now()
        task.start(worker_id="worker-1")
        after = datetime.now()

        assert task.started_at is not None
        assert before <= task.started_at <= after

    def test_task_start_sets_worker_id(self):
        """Test that start() sets worker_id."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-123")

        assert task.worker_id == "worker-123"

    def test_task_start_increments_attempt(self):
        """Test that start() increments attempt counter."""
        task = Task(url="https://example.com")
        assert task.attempt == 0

        task.start(worker_id="worker-1")
        assert task.attempt == 1

        # Simulate retry scenario
        task.status = TaskStatus.RETRYING
        task.start(worker_id="worker-2")
        assert task.attempt == 2

    def test_task_start_multiple_times(self):
        """Test starting a task multiple times (retry scenario)."""
        task = Task(url="https://example.com")

        task.start(worker_id="worker-1")
        first_start = task.started_at

        # Simulate retry
        time.sleep(0.01)
        task.start(worker_id="worker-2")

        assert task.started_at > first_start
        assert task.worker_id == "worker-2"
        assert task.attempt == 2


# ============================================================================
# TASK TESTS - COMPLETE METHOD
# ============================================================================


class TestTaskComplete:
    """Tests for Task.complete() method."""

    def test_task_complete_sets_completed_status(self):
        """Test that complete() sets status to COMPLETED."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        task.complete()

        assert task.status == TaskStatus.COMPLETED

    def test_task_complete_sets_completed_at(self):
        """Test that complete() sets completed_at timestamp."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        before = datetime.now()
        task.complete()
        after = datetime.now()

        assert task.completed_at is not None
        assert before <= task.completed_at <= after


# ============================================================================
# TASK TESTS - FAIL METHOD
# ============================================================================


class TestTaskFail:
    """Tests for Task.fail() method."""

    def test_task_fail_sets_failed_status(self):
        """Test that fail() sets status to FAILED."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        task.fail()

        assert task.status == TaskStatus.FAILED

    def test_task_fail_sets_completed_at(self):
        """Test that fail() sets completed_at timestamp."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        before = datetime.now()
        task.fail()
        after = datetime.now()

        assert task.completed_at is not None
        assert before <= task.completed_at <= after


# ============================================================================
# TASK TESTS - RETRY METHOD
# ============================================================================


class TestTaskRetry:
    """Tests for Task.retry() method."""

    def test_task_retry_returns_true_when_retries_available(self):
        """Test retry() returns True when attempts < max_retries."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")  # attempt = 1

        result = task.retry()

        assert result is True
        assert task.status == TaskStatus.RETRYING

    def test_task_retry_returns_false_when_exhausted(self):
        """Test retry() returns False when attempts >= max_retries."""
        task = Task(url="https://example.com")
        task.config.max_retries = 3

        # Simulate 3 attempts
        for _ in range(3):
            task.start(worker_id="worker-1")

        result = task.retry()

        assert result is False
        assert task.status == TaskStatus.FAILED

    def test_task_retry_at_boundary(self):
        """Test retry() behavior at exactly max_retries."""
        task = Task(url="https://example.com")
        task.config.max_retries = 2

        task.start(worker_id="worker-1")  # attempt = 1
        assert task.retry() is True

        task.start(worker_id="worker-1")  # attempt = 2
        assert task.retry() is False
        assert task.status == TaskStatus.FAILED

    def test_task_retry_with_zero_max_retries(self):
        """Test retry() with max_retries=0 fails immediately."""
        task = Task(url="https://example.com")
        task.config.max_retries = 0
        task.start(worker_id="worker-1")

        result = task.retry()

        assert result is False
        assert task.status == TaskStatus.FAILED


# ============================================================================
# TASK TESTS - CANCEL METHOD
# ============================================================================


class TestTaskCancel:
    """Tests for Task.cancel() method."""

    def test_task_cancel_sets_cancelled_status(self):
        """Test that cancel() sets status to CANCELLED."""
        task = Task(url="https://example.com")
        task.cancel()

        assert task.status == TaskStatus.CANCELLED

    def test_task_cancel_sets_completed_at(self):
        """Test that cancel() sets completed_at timestamp."""
        task = Task(url="https://example.com")
        before = datetime.now()
        task.cancel()
        after = datetime.now()

        assert task.completed_at is not None
        assert before <= task.completed_at <= after

    def test_task_cancel_pending_task(self):
        """Test cancelling a task that hasn't started."""
        task = Task(url="https://example.com")
        assert task.status == TaskStatus.PENDING

        task.cancel()

        assert task.status == TaskStatus.CANCELLED
        assert task.started_at is None

    def test_task_cancel_running_task(self):
        """Test cancelling a task that is currently running."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        task.cancel()

        assert task.status == TaskStatus.CANCELLED


# ============================================================================
# TASK TESTS - DURATION PROPERTY
# ============================================================================


class TestTaskDuration:
    """Tests for Task.duration property."""

    def test_task_duration_none_when_not_started(self):
        """Test duration is None when task hasn't started."""
        task = Task(url="https://example.com")

        assert task.duration is None

    def test_task_duration_calculates_when_running(self):
        """Test duration calculates from started_at to now when running."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        time.sleep(0.05)

        duration = task.duration

        assert duration is not None
        assert duration >= 0.05

    def test_task_duration_calculates_when_completed(self):
        """Test duration calculates from started_at to completed_at."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        time.sleep(0.05)
        task.complete()

        duration = task.duration

        assert duration is not None
        assert duration >= 0.05

    def test_task_duration_fixed_after_completion(self):
        """Test duration doesn't change after task completes."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        task.complete()

        duration1 = task.duration
        time.sleep(0.02)
        duration2 = task.duration

        assert duration1 == duration2


# ============================================================================
# TASK TESTS - IS_FINISHED PROPERTY
# ============================================================================


class TestTaskIsFinished:
    """Tests for Task.is_finished property."""

    def test_task_is_finished_pending(self):
        """Test is_finished is False for PENDING."""
        task = Task(url="https://example.com")
        assert task.is_finished is False

    def test_task_is_finished_queued(self):
        """Test is_finished is False for QUEUED."""
        task = Task(url="https://example.com")
        task.status = TaskStatus.QUEUED
        assert task.is_finished is False

    def test_task_is_finished_running(self):
        """Test is_finished is False for RUNNING."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        assert task.is_finished is False

    def test_task_is_finished_retrying(self):
        """Test is_finished is False for RETRYING."""
        task = Task(url="https://example.com")
        task.status = TaskStatus.RETRYING
        assert task.is_finished is False

    def test_task_is_finished_completed(self):
        """Test is_finished is True for COMPLETED."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        task.complete()
        assert task.is_finished is True

    def test_task_is_finished_failed(self):
        """Test is_finished is True for FAILED."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        task.fail()
        assert task.is_finished is True

    def test_task_is_finished_cancelled(self):
        """Test is_finished is True for CANCELLED."""
        task = Task(url="https://example.com")
        task.cancel()
        assert task.is_finished is True


# ============================================================================
# TASK TESTS - TO_DICT METHOD
# ============================================================================


class TestTaskToDict:
    """Tests for Task.to_dict() serialization."""

    def test_task_to_dict_basic_fields(self):
        """Test to_dict includes basic fields."""
        task = Task(url="https://example.com", id="test-id")
        result = task.to_dict()

        assert result["id"] == "test-id"
        assert result["url"] == "https://example.com"
        assert result["task_type"] == "visit"
        assert result["status"] == "pending"
        assert result["priority"] == 5

    def test_task_to_dict_timestamps(self):
        """Test to_dict includes timestamp fields."""
        task = Task(url="https://example.com")
        result = task.to_dict()

        assert "created_at" in result
        assert result["started_at"] is None
        assert result["completed_at"] is None

    def test_task_to_dict_timestamps_after_start(self):
        """Test to_dict includes started_at after starting."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-1")
        result = task.to_dict()

        assert result["started_at"] is not None
        # Should be ISO format string
        assert isinstance(result["started_at"], str)

    def test_task_to_dict_execution_tracking(self):
        """Test to_dict includes execution tracking fields."""
        task = Task(url="https://example.com")
        task.start(worker_id="worker-123")
        task.proxy_id = "proxy-1"
        task.fingerprint_id = "fp-1"

        result = task.to_dict()

        assert result["attempt"] == 1
        assert result["worker_id"] == "worker-123"
        assert result["proxy_id"] == "proxy-1"
        assert result["fingerprint_id"] == "fp-1"

    def test_task_to_dict_metadata(self):
        """Test to_dict includes metadata fields."""
        task = Task(url="https://example.com")
        task.tags = ["test", "important"]
        task.metadata = {"key": "value"}

        result = task.to_dict()

        assert result["tags"] == ["test", "important"]
        assert result["metadata"] == {"key": "value"}

    def test_task_to_dict_duration(self):
        """Test to_dict includes duration."""
        task = Task(url="https://example.com")
        result = task.to_dict()
        assert result["duration"] is None

        task.start(worker_id="worker-1")
        result = task.to_dict()
        assert result["duration"] is not None


# ============================================================================
# TASKRESULT TESTS
# ============================================================================


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_task_result_creation(self):
        """Test creating a TaskResult with required fields."""
        now = datetime.now()
        result = TaskResult(
            task_id="task-123",
            success=True,
            status=TaskStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_ms=1500.0,
        )

        assert result.task_id == "task-123"
        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert result.duration_ms == 1500.0

    def test_task_result_defaults(self):
        """Test TaskResult default values."""
        now = datetime.now()
        result = TaskResult(
            task_id="task-123",
            success=True,
            status=TaskStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_ms=1000.0,
        )

        assert result.final_url is None
        assert result.status_code is None
        assert result.page_title is None
        assert result.extracted_data == {}
        assert result.screenshot_path is None
        assert result.error is None
        assert result.error_type is None
        assert result.traceback is None
        assert result.proxy_used is None
        assert result.fingerprint_used is None
        assert result.bytes_downloaded == 0
        assert result.requests_made == 0
        assert result.captcha_detected is False
        assert result.captcha_solved is False
        assert result.bot_detected is False
        assert result.metadata == {}

    def test_task_result_success_case(self):
        """Test TaskResult for successful execution."""
        now = datetime.now()
        result = TaskResult(
            task_id="task-123",
            success=True,
            status=TaskStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_ms=2500.0,
            final_url="https://example.com/page",
            status_code=200,
            page_title="Example Page",
            bytes_downloaded=51200,
            requests_made=15,
        )

        assert result.success is True
        assert result.error is None
        assert result.status_code == 200

    def test_task_result_failure_case(self):
        """Test TaskResult for failed execution."""
        now = datetime.now()
        result = TaskResult(
            task_id="task-123",
            success=False,
            status=TaskStatus.FAILED,
            started_at=now,
            completed_at=now,
            duration_ms=500.0,
            error="Connection timeout",
            error_type="TimeoutError",
        )

        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.error_type == "TimeoutError"

    def test_task_result_detection_info(self):
        """Test TaskResult detection fields."""
        now = datetime.now()
        result = TaskResult(
            task_id="task-123",
            success=True,
            status=TaskStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_ms=3000.0,
            captcha_detected=True,
            captcha_solved=True,
            bot_detected=False,
        )

        assert result.captcha_detected is True
        assert result.captcha_solved is True
        assert result.bot_detected is False

    def test_task_result_to_dict(self):
        """Test TaskResult.to_dict() serialization."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=2)
        result = TaskResult(
            task_id="task-123",
            success=True,
            status=TaskStatus.COMPLETED,
            started_at=start_time,
            completed_at=end_time,
            duration_ms=2000.0,
            final_url="https://example.com",
            status_code=200,
        )

        data = result.to_dict()

        assert data["task_id"] == "task-123"
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["duration_ms"] == 2000.0
        assert data["final_url"] == "https://example.com"
        assert data["status_code"] == 200
        assert isinstance(data["started_at"], str)
        assert isinstance(data["completed_at"], str)

    def test_task_result_to_dict_all_fields(self):
        """Test TaskResult.to_dict() includes all fields."""
        now = datetime.now()
        result = TaskResult(
            task_id="task-123",
            success=True,
            status=TaskStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_ms=1000.0,
        )

        data = result.to_dict()

        expected_keys = {
            "task_id",
            "success",
            "status",
            "started_at",
            "completed_at",
            "duration_ms",
            "final_url",
            "status_code",
            "page_title",
            "extracted_data",
            "screenshot_path",
            "error",
            "error_type",
            "proxy_used",
            "fingerprint_used",
            "bytes_downloaded",
            "requests_made",
            "captcha_detected",
            "captcha_solved",
            "bot_detected",
            "metadata",
        }
        assert set(data.keys()) == expected_keys


# ============================================================================
# BATCHRESULT TESTS
# ============================================================================


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_batch_result_creation(self):
        """Test creating a BatchResult."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=8,
            failed_tasks=1,
            cancelled_tasks=1,
            started_at=now,
        )

        assert batch.batch_id == "batch-123"
        assert batch.total_tasks == 10
        assert batch.completed_tasks == 8
        assert batch.failed_tasks == 1
        assert batch.cancelled_tasks == 1

    def test_batch_result_defaults(self):
        """Test BatchResult default values."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=5,
            completed_tasks=0,
            failed_tasks=0,
            cancelled_tasks=0,
            started_at=now,
        )

        assert batch.completed_at is None
        assert batch.results == []

    def test_batch_result_success_rate_all_completed(self):
        """Test success_rate when all tasks completed."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=10,
            failed_tasks=0,
            cancelled_tasks=0,
            started_at=now,
        )

        assert batch.success_rate == 1.0

    def test_batch_result_success_rate_partial(self):
        """Test success_rate with mixed results."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=7,
            failed_tasks=2,
            cancelled_tasks=1,
            started_at=now,
        )

        assert batch.success_rate == 0.7

    def test_batch_result_success_rate_none_completed(self):
        """Test success_rate when no tasks completed."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=0,
            failed_tasks=10,
            cancelled_tasks=0,
            started_at=now,
        )

        assert batch.success_rate == 0.0

    def test_batch_result_success_rate_zero_tasks(self):
        """Test success_rate with zero total tasks."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            cancelled_tasks=0,
            started_at=now,
        )

        assert batch.success_rate == 0.0

    def test_batch_result_duration_not_completed(self):
        """Test duration is None when batch not completed."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=5,
            failed_tasks=0,
            cancelled_tasks=0,
            started_at=now,
        )

        assert batch.duration is None

    def test_batch_result_duration_completed(self):
        """Test duration calculation when completed."""
        start = datetime.now()
        end = start + timedelta(seconds=30)
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=10,
            failed_tasks=0,
            cancelled_tasks=0,
            started_at=start,
            completed_at=end,
        )

        assert batch.duration == 30.0

    def test_batch_result_is_finished_incomplete(self):
        """Test is_finished when tasks still pending."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=5,
            failed_tasks=2,
            cancelled_tasks=1,
            started_at=now,
        )

        # 5 + 2 + 1 = 8, not 10
        assert batch.is_finished is False

    def test_batch_result_is_finished_complete(self):
        """Test is_finished when all tasks done."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=7,
            failed_tasks=2,
            cancelled_tasks=1,
            started_at=now,
        )

        # 7 + 2 + 1 = 10
        assert batch.is_finished is True

    def test_batch_result_is_finished_all_failed(self):
        """Test is_finished when all tasks failed."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=5,
            completed_tasks=0,
            failed_tasks=5,
            cancelled_tasks=0,
            started_at=now,
        )

        assert batch.is_finished is True

    def test_batch_result_to_dict(self):
        """Test BatchResult.to_dict() serialization."""
        start = datetime.now()
        end = start + timedelta(seconds=60)
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=8,
            failed_tasks=1,
            cancelled_tasks=1,
            started_at=start,
            completed_at=end,
        )

        data = batch.to_dict()

        assert data["batch_id"] == "batch-123"
        assert data["total_tasks"] == 10
        assert data["completed_tasks"] == 8
        assert data["failed_tasks"] == 1
        assert data["cancelled_tasks"] == 1
        assert data["success_rate"] == 0.8
        assert data["duration"] == 60.0
        assert data["is_finished"] is True
        assert isinstance(data["started_at"], str)
        assert isinstance(data["completed_at"], str)

    def test_batch_result_to_dict_not_completed(self):
        """Test BatchResult.to_dict() when not completed."""
        now = datetime.now()
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=10,
            completed_tasks=3,
            failed_tasks=0,
            cancelled_tasks=0,
            started_at=now,
        )

        data = batch.to_dict()

        assert data["completed_at"] is None
        assert data["duration"] is None
        assert data["is_finished"] is False

    def test_batch_result_with_task_results(self):
        """Test BatchResult containing TaskResult objects."""
        now = datetime.now()
        task_result = TaskResult(
            task_id="task-1",
            success=True,
            status=TaskStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_ms=1000.0,
        )
        batch = BatchResult(
            batch_id="batch-123",
            total_tasks=1,
            completed_tasks=1,
            failed_tasks=0,
            cancelled_tasks=0,
            started_at=now,
            results=[task_result],
        )

        assert len(batch.results) == 1
        assert batch.results[0].task_id == "task-1"
