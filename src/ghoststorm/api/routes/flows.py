"""API routes for flow recording and execution."""

from __future__ import annotations

import contextlib
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException

from ghoststorm.api.schemas import (
    CheckpointCreate,
    CheckpointResponse,
    FlowCreate,
    FlowExecuteRequest,
    FlowExecutionResponse,
    FlowExecutionStatus,
    FlowListItem,
    FlowListResponse,
    FlowResponse,
    FlowSummaryResponse,
    FlowUpdate,
    RecordingStartRequest,
    RecordingStartResponse,
    RecordingStopResponse,
)
from ghoststorm.core.flow import (
    get_flow_executor,
    get_flow_recorder,
    get_flow_storage,
)
from ghoststorm.core.models.flow import (
    Checkpoint,
    CheckpointType,
    FlowExecutionConfig,
    FlowStatus,
    RecordedFlow,
    TimingConfig,
    VariationLevel,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/flows", tags=["flows"])

# Active executions tracking
_active_executions: dict[str, Any] = {}


# --- Flow CRUD ---


@router.get("", response_model=FlowListResponse)
async def list_flows(
    status: str | None = None,
    tag: str | None = None,
) -> FlowListResponse:
    """List all recorded flows."""
    storage = get_flow_storage()

    # Parse status filter
    status_filter = None
    if status:
        with contextlib.suppress(ValueError):
            status_filter = FlowStatus(status)

    # Parse tags filter
    tags = [tag] if tag else None

    flows = await storage.list_flows(status=status_filter, tags=tags)

    items = [
        FlowListItem(
            id=f.id,
            name=f.name,
            description=f.description,
            status=f.status.value,
            start_url=f.start_url,
            checkpoint_count=f.checkpoint_count,
            success_rate=f.success_rate,
            times_executed=f.times_executed,
            updated_at=f.updated_at,
            tags=f.tags,
        )
        for f in flows
    ]

    ready_count = sum(1 for f in flows if f.status == FlowStatus.READY)
    draft_count = sum(1 for f in flows if f.status == FlowStatus.DRAFT)

    return FlowListResponse(
        flows=items,
        total=len(items),
        ready=ready_count,
        draft=draft_count,
    )


@router.get("/summary", response_model=FlowSummaryResponse)
async def get_flows_summary() -> FlowSummaryResponse:
    """Get summary statistics for all flows."""
    storage = get_flow_storage()
    summary = await storage.get_flow_summary()
    return FlowSummaryResponse(**summary)


@router.get("/{flow_id}", response_model=FlowResponse)
async def get_flow(flow_id: str) -> FlowResponse:
    """Get a specific flow by ID."""
    storage = get_flow_storage()
    flow = await storage.load(flow_id)

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    checkpoints = [
        CheckpointResponse(
            id=cp.id,
            checkpoint_type=cp.checkpoint_type.value,
            goal=cp.goal,
            url_pattern=cp.url_pattern,
            element_description=cp.element_description,
            selector_hints=cp.selector_hints,
            input_value=cp.input_value,
            timing={
                "min_delay": cp.timing.min_delay,
                "max_delay": cp.timing.max_delay,
                "timeout": cp.timing.timeout,
            },
            order=cp.order,
            created_at=cp.created_at,
            has_screenshot=cp.reference_screenshot is not None,
        )
        for cp in flow.checkpoints
    ]

    return FlowResponse(
        id=flow.id,
        name=flow.name,
        description=flow.description,
        status=flow.status.value,
        start_url=flow.start_url,
        checkpoints=checkpoints,
        summary_goal=flow.summary_goal,
        recorded_with_browser=flow.recorded_with_browser,
        created_at=flow.created_at,
        updated_at=flow.updated_at,
        times_executed=flow.times_executed,
        successful_executions=flow.successful_executions,
        success_rate=flow.success_rate,
        checkpoint_count=flow.checkpoint_count,
        tags=flow.tags,
    )


@router.post("", response_model=FlowResponse)
async def create_flow(request: FlowCreate) -> FlowResponse:
    """Create a new flow manually (without recording)."""
    storage = get_flow_storage()

    flow = RecordedFlow(
        name=request.name,
        description=request.description,
        start_url=request.start_url,
        tags=request.tags,
        status=FlowStatus.DRAFT,
    )

    await storage.save(flow)
    logger.info("Flow created", flow_id=flow.id, name=flow.name)

    return await get_flow(flow.id)


@router.patch("/{flow_id}", response_model=FlowResponse)
async def update_flow(flow_id: str, request: FlowUpdate) -> FlowResponse:
    """Update a flow."""
    storage = get_flow_storage()
    flow = await storage.load(flow_id)

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    if request.name is not None:
        flow.name = request.name
    if request.description is not None:
        flow.description = request.description
    if request.summary_goal is not None:
        flow.summary_goal = request.summary_goal
    if request.tags is not None:
        flow.tags = request.tags
    if request.status is not None:
        flow.status = FlowStatus(request.status)

    await storage.save(flow)
    logger.info("Flow updated", flow_id=flow_id)

    return await get_flow(flow_id)


@router.delete("/{flow_id}")
async def delete_flow(flow_id: str) -> dict[str, str]:
    """Delete a flow."""
    storage = get_flow_storage()

    if not await storage.exists(flow_id):
        raise HTTPException(status_code=404, detail="Flow not found")

    await storage.delete(flow_id)
    logger.info("Flow deleted", flow_id=flow_id)

    return {"status": "deleted", "flow_id": flow_id}


# --- Checkpoints ---


@router.post("/{flow_id}/checkpoints", response_model=CheckpointResponse)
async def add_checkpoint(flow_id: str, request: CheckpointCreate) -> CheckpointResponse:
    """Add a checkpoint to a flow."""
    storage = get_flow_storage()
    flow = await storage.load(flow_id)

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    checkpoint = Checkpoint(
        checkpoint_type=CheckpointType(request.checkpoint_type),
        goal=request.goal,
        url_pattern=request.url_pattern,
        element_description=request.element_description,
        selector_hints=request.selector_hints,
        input_value=request.input_value,
        timing=TimingConfig(
            min_delay=request.timing.min_delay,
            max_delay=request.timing.max_delay,
            timeout=request.timing.timeout,
        ),
        reference_screenshot=request.reference_screenshot,
    )

    flow.add_checkpoint(checkpoint)
    await storage.save(flow)

    logger.info("Checkpoint added", flow_id=flow_id, checkpoint_id=checkpoint.id)

    return CheckpointResponse(
        id=checkpoint.id,
        checkpoint_type=checkpoint.checkpoint_type.value,
        goal=checkpoint.goal,
        url_pattern=checkpoint.url_pattern,
        element_description=checkpoint.element_description,
        selector_hints=checkpoint.selector_hints,
        input_value=checkpoint.input_value,
        timing={
            "min_delay": checkpoint.timing.min_delay,
            "max_delay": checkpoint.timing.max_delay,
            "timeout": checkpoint.timing.timeout,
        },
        order=checkpoint.order,
        created_at=checkpoint.created_at,
        has_screenshot=checkpoint.reference_screenshot is not None,
    )


@router.delete("/{flow_id}/checkpoints/{checkpoint_id}")
async def delete_checkpoint(flow_id: str, checkpoint_id: str) -> dict[str, str]:
    """Delete a checkpoint from a flow."""
    storage = get_flow_storage()
    flow = await storage.load(flow_id)

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    if not flow.remove_checkpoint(checkpoint_id):
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    await storage.save(flow)
    logger.info("Checkpoint deleted", flow_id=flow_id, checkpoint_id=checkpoint_id)

    return {"status": "deleted", "checkpoint_id": checkpoint_id}


# --- Recording ---


@router.post("/record/start", response_model=RecordingStartResponse)
async def start_recording(request: RecordingStartRequest) -> RecordingStartResponse:
    """Start recording a new flow.

    This launches a browser in headed mode with the recording toolbar.
    """
    recorder = get_flow_recorder()

    if recorder.is_recording:
        raise HTTPException(status_code=400, detail="Recording already in progress")

    # Build stealth config dict
    stealth_config = None
    if request.stealth:
        stealth_config = {
            "use_proxy": request.stealth.use_proxy,
            "use_fingerprint": request.stealth.use_fingerprint,
            "block_webrtc": request.stealth.block_webrtc,
            "canvas_noise": request.stealth.canvas_noise,
        }

    try:
        flow = await recorder.start_recording(
            name=request.name,
            start_url=request.start_url,
            description=request.description,
            stealth=stealth_config,
        )

        stealth_msg = ""
        if stealth_config and (
            stealth_config.get("use_proxy") or stealth_config.get("use_fingerprint")
        ):
            stealth_msg = " with stealth mode"

        return RecordingStartResponse(
            flow_id=flow.id,
            status="recording",
            message=f"Recording started{stealth_msg}. Browser opened at {request.start_url}",
            browser_launched=True,
        )

    except Exception as e:
        logger.error("Failed to start recording", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record/{flow_id}/checkpoint", response_model=CheckpointResponse)
async def add_recording_checkpoint(
    flow_id: str,
    request: CheckpointCreate,
) -> CheckpointResponse:
    """Add a checkpoint during recording."""
    recorder = get_flow_recorder()

    if not recorder.is_recording:
        raise HTTPException(status_code=400, detail="No recording in progress")

    if recorder.current_flow and recorder.current_flow.id != flow_id:
        raise HTTPException(status_code=400, detail="Flow ID mismatch")

    checkpoint = await recorder.add_checkpoint(
        checkpoint_type=CheckpointType(request.checkpoint_type),
        goal=request.goal,
        element_description=request.element_description,
        input_value=request.input_value,
        timing=TimingConfig(
            min_delay=request.timing.min_delay,
            max_delay=request.timing.max_delay,
            timeout=request.timing.timeout,
        ),
    )

    if not checkpoint:
        raise HTTPException(status_code=500, detail="Failed to add checkpoint")

    return CheckpointResponse(
        id=checkpoint.id,
        checkpoint_type=checkpoint.checkpoint_type.value,
        goal=checkpoint.goal,
        url_pattern=checkpoint.url_pattern,
        element_description=checkpoint.element_description,
        selector_hints=checkpoint.selector_hints,
        input_value=checkpoint.input_value,
        timing={
            "min_delay": checkpoint.timing.min_delay,
            "max_delay": checkpoint.timing.max_delay,
            "timeout": checkpoint.timing.timeout,
        },
        order=checkpoint.order,
        created_at=checkpoint.created_at,
        has_screenshot=checkpoint.reference_screenshot is not None,
    )


@router.post("/record/{flow_id}/stop", response_model=RecordingStopResponse)
async def stop_recording(flow_id: str) -> RecordingStopResponse:
    """Stop the current recording."""
    recorder = get_flow_recorder()

    if not recorder.is_recording:
        raise HTTPException(status_code=400, detail="No recording in progress")

    if recorder.current_flow and recorder.current_flow.id != flow_id:
        raise HTTPException(status_code=400, detail="Flow ID mismatch")

    flow = await recorder.stop_recording()

    if not flow:
        raise HTTPException(status_code=500, detail="Failed to stop recording")

    return RecordingStopResponse(
        flow_id=flow.id,
        status=flow.status.value,
        checkpoint_count=flow.checkpoint_count,
        message=f"Recording stopped. {flow.checkpoint_count} checkpoints saved.",
    )


@router.post("/record/cancel")
async def cancel_recording() -> dict[str, str]:
    """Cancel the current recording without saving."""
    recorder = get_flow_recorder()

    if not recorder.is_recording:
        raise HTTPException(status_code=400, detail="No recording in progress")

    await recorder.cancel_recording()

    return {"status": "cancelled", "message": "Recording cancelled"}


@router.get("/record/status")
async def get_recording_status() -> dict[str, Any]:
    """Get current recording status."""
    recorder = get_flow_recorder()

    if not recorder.is_recording:
        return {"is_recording": False}

    flow = recorder.current_flow
    return {
        "is_recording": True,
        "flow_id": flow.id if flow else None,
        "flow_name": flow.name if flow else None,
        "checkpoint_count": len(flow.checkpoints) if flow else 0,
    }


# --- Execution ---


@router.post("/{flow_id}/execute", response_model=FlowExecutionResponse)
async def execute_flow(
    flow_id: str,
    request: FlowExecuteRequest,
    background_tasks: BackgroundTasks,
) -> FlowExecutionResponse:
    """Execute a recorded flow.

    This runs the flow in the background and returns immediately.
    Use /executions/{execution_id} to check status.
    """
    storage = get_flow_storage()
    flow = await storage.load(flow_id)

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    if flow.status != FlowStatus.READY:
        raise HTTPException(
            status_code=400, detail=f"Flow is not ready (status: {flow.status.value})"
        )

    # Create execution config
    config = FlowExecutionConfig(
        flow_id=flow_id,
        browser_engine=request.browser_engine,
        variation_level=VariationLevel(request.variation_level),
        workers=request.workers,
        use_proxy=request.use_proxy,
        proxy_pool=request.proxy_pool,
        substitutions=request.substitutions,
        checkpoint_timeout=request.checkpoint_timeout,
        capture_screenshots=request.capture_screenshots,
    )

    # Start execution in background
    executor = get_flow_executor()

    async def run_execution() -> None:
        result = await executor.execute(flow_id, config)
        _active_executions[result.execution_id] = result

    background_tasks.add_task(run_execution)

    # Generate execution ID (we don't have it yet since it's async)
    from uuid import uuid4

    execution_id = str(uuid4())

    return FlowExecutionResponse(
        execution_id=execution_id,
        flow_id=flow_id,
        status="started",
        browser_engine=request.browser_engine,
        workers=request.workers,
        message=f"Flow execution started with {request.workers} worker(s)",
    )


@router.get("/executions/{execution_id}", response_model=FlowExecutionStatus)
async def get_execution_status(execution_id: str) -> FlowExecutionStatus:
    """Get status of a flow execution."""
    result = _active_executions.get(execution_id)

    if not result:
        # Check if it's still running
        executor = get_flow_executor()
        result = executor.get_execution_status(execution_id)

        if not result:
            raise HTTPException(status_code=404, detail="Execution not found")

    return FlowExecutionStatus(
        execution_id=result.execution_id,
        flow_id=result.flow_id,
        success=result.success,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration=result.duration,
        checkpoints_completed=result.checkpoints_completed,
        total_checkpoints=result.total_checkpoints,
        progress=result.progress,
        failed_at_checkpoint=result.failed_at_checkpoint,
        error=result.error,
        browser_engine=result.browser_engine,
        proxy_used=result.proxy_used,
    )


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str) -> dict[str, str]:
    """Cancel a running execution."""
    executor = get_flow_executor()

    if await executor.cancel_execution(execution_id):
        return {"status": "cancelled", "execution_id": execution_id}
    else:
        raise HTTPException(status_code=404, detail="Execution not found or already completed")


# --- Flow Finalization ---


@router.post("/{flow_id}/finalize", response_model=FlowResponse)
async def finalize_flow(flow_id: str) -> FlowResponse:
    """Finalize a draft flow and mark it as ready."""
    storage = get_flow_storage()
    flow = await storage.load(flow_id)

    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    if flow.status == FlowStatus.READY:
        raise HTTPException(status_code=400, detail="Flow is already finalized")

    if not flow.checkpoints:
        raise HTTPException(status_code=400, detail="Cannot finalize flow with no checkpoints")

    flow.finalize()
    await storage.save(flow)

    logger.info("Flow finalized", flow_id=flow_id)
    return await get_flow(flow_id)
