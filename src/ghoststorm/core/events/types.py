"""Event type definitions."""

from enum import Enum


class EventType(str, Enum):
    """All event types in the system."""

    # Engine lifecycle
    ENGINE_STARTING = "engine.starting"
    ENGINE_STARTED = "engine.started"
    ENGINE_STOPPING = "engine.stopping"
    ENGINE_STOPPED = "engine.stopped"
    ENGINE_ERROR = "engine.error"

    # Browser lifecycle
    BROWSER_LAUNCHING = "browser.launching"
    BROWSER_LAUNCHED = "browser.launched"
    BROWSER_CLOSING = "browser.closing"
    BROWSER_CLOSED = "browser.closed"
    BROWSER_ERROR = "browser.error"

    # Context lifecycle
    CONTEXT_CREATED = "context.created"
    CONTEXT_CLOSED = "context.closed"

    # Page lifecycle
    PAGE_CREATED = "page.created"
    PAGE_NAVIGATING = "page.navigating"
    PAGE_LOADED = "page.loaded"
    PAGE_ERROR = "page.error"
    PAGE_CLOSED = "page.closed"

    # Task lifecycle
    TASK_QUEUED = "task.queued"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_RETRYING = "task.retrying"

    # Batch lifecycle
    BATCH_STARTED = "batch.started"
    BATCH_PROGRESS = "batch.progress"
    BATCH_COMPLETED = "batch.completed"

    # Worker lifecycle
    WORKER_STARTED = "worker.started"
    WORKER_IDLE = "worker.idle"
    WORKER_BUSY = "worker.busy"
    WORKER_STOPPED = "worker.stopped"
    WORKER_ERROR = "worker.error"

    # Detection events
    CAPTCHA_DETECTED = "detection.captcha"
    CAPTCHA_SOLVING = "detection.captcha_solving"
    CAPTCHA_SOLVED = "detection.captcha_solved"
    CAPTCHA_FAILED = "detection.captcha_failed"
    BOT_DETECTED = "detection.bot"
    RATE_LIMITED = "detection.rate_limit"
    BLOCKED = "detection.blocked"

    # Proxy events
    PROXY_ASSIGNED = "proxy.assigned"
    PROXY_SUCCESS = "proxy.success"
    PROXY_FAILED = "proxy.failed"
    PROXY_ROTATED = "proxy.rotated"
    PROXY_EXHAUSTED = "proxy.exhausted"
    PROXY_HEALTH_CHECK = "proxy.health_check"

    # Fingerprint events
    FINGERPRINT_GENERATED = "fingerprint.generated"
    FINGERPRINT_APPLIED = "fingerprint.applied"

    # Network events
    REQUEST_STARTED = "network.request_started"
    REQUEST_COMPLETED = "network.request_completed"
    REQUEST_FAILED = "network.request_failed"
    REQUEST_BLOCKED = "network.request_blocked"
    RESPONSE_RECEIVED = "network.response_received"

    # Data events
    DATA_EXTRACTED = "data.extracted"
    DATA_WRITTEN = "data.written"
    SCREENSHOT_CAPTURED = "data.screenshot"

    # Plugin events
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_ERROR = "plugin.error"

    # Metrics events
    METRICS_COLLECTED = "metrics.collected"
    METRICS_EXPORTED = "metrics.exported"

    # LLM/AI events
    LLM_ANALYZING = "llm.analyzing"
    LLM_ANALYSIS_READY = "llm.analysis_ready"
    LLM_ACTION_SUGGESTED = "llm.action_suggested"
    LLM_ACTION_APPROVED = "llm.action_approved"
    LLM_ACTION_REJECTED = "llm.action_rejected"
    LLM_ACTION_EXECUTING = "llm.action_executing"
    LLM_ACTION_COMPLETED = "llm.action_completed"
    LLM_TASK_COMPLETE = "llm.task_complete"
    LLM_VISION_FALLBACK = "llm.vision_fallback"
    LLM_ERROR = "llm.error"

    # DOM intelligence events
    DOM_EXTRACTING = "dom.extracting"
    DOM_EXTRACTED = "dom.extracted"
    DOM_ELEMENT_FOUND = "dom.element_found"
    DOM_ELEMENT_CLICKED = "dom.element_clicked"
    DOM_ELEMENT_TYPED = "dom.element_typed"
    DOM_ELEMENT_HIGHLIGHTED = "dom.element_highlighted"

    # Visual feedback events
    SCREENSHOT_LIVE = "visual.screenshot_live"
    ELEMENT_ACTION = "visual.element_action"

    # Flow recording events
    FLOW_RECORDING_STARTED = "flow.recording_started"
    FLOW_RECORDING_PAUSED = "flow.recording_paused"
    FLOW_RECORDING_RESUMED = "flow.recording_resumed"
    FLOW_RECORDING_STOPPED = "flow.recording_stopped"
    FLOW_RECORDING_CANCELLED = "flow.recording_cancelled"
    FLOW_CHECKPOINT_ADDED = "flow.checkpoint_added"

    # Flow execution events
    FLOW_EXECUTION_STARTED = "flow.execution_started"
    FLOW_EXECUTION_PROGRESS = "flow.execution_progress"
    FLOW_EXECUTION_COMPLETED = "flow.execution_completed"
    FLOW_EXECUTION_FAILED = "flow.execution_failed"
    FLOW_EXECUTION_CANCELLED = "flow.execution_cancelled"
    FLOW_CHECKPOINT_STARTED = "flow.checkpoint_started"
    FLOW_CHECKPOINT_COMPLETED = "flow.checkpoint_completed"
    FLOW_CHECKPOINT_FAILED = "flow.checkpoint_failed"
