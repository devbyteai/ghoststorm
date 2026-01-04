"""LLM API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/llm", tags=["llm"])


# Request/Response Models


class ProviderInfoResponse(BaseModel):
    """Provider information response."""

    name: str
    default_model: str
    supported_models: list[str]
    requires_api_key: bool
    supports_streaming: bool
    supports_tools: bool


class ListProvidersResponse(BaseModel):
    """List providers response."""

    providers: list[ProviderInfoResponse]
    current_provider: str


class SetProviderRequest(BaseModel):
    """Set provider request."""

    provider: str = Field(description="Provider name (openai, anthropic, ollama)")


class CompletionRequest(BaseModel):
    """Completion request."""

    messages: list[dict[str, str]] = Field(description="List of messages with role and content")
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    provider: str | None = Field(default=None, description="Provider to use")


class CompletionResponse(BaseModel):
    """Completion response."""

    content: str
    model: str
    provider: str
    usage: dict[str, int]
    finish_reason: str


class AnalyzePageRequest(BaseModel):
    """Analyze page request."""

    task_id: str = Field(description="Task ID with active browser session")
    task: str = Field(description="Task description (what to accomplish)")
    provider: str | None = Field(default=None)


class AnalysisResponse(BaseModel):
    """Page analysis response."""

    analysis: str
    is_complete: bool
    next_action: dict[str, Any] | None
    confidence: float
    extracted_data: dict[str, Any] | None


class ExecuteTaskRequest(BaseModel):
    """Execute autonomous task request."""

    task_id: str = Field(description="Task ID with active browser session")
    task: str = Field(description="Task to accomplish")
    max_steps: int = Field(default=20, ge=1, le=100)
    provider: str | None = Field(default=None)


class TaskResultResponse(BaseModel):
    """Task execution result."""

    success: bool
    steps_taken: int
    extracted_data: dict[str, Any] | None
    error: str | None
    final_url: str | None


class UsageResponse(BaseModel):
    """Usage statistics response."""

    total: dict[str, int]
    by_provider: dict[str, dict[str, int]]


class HealthCheckResponse(BaseModel):
    """LLM health check response."""

    providers: dict[str, bool]


# Helper functions


def _get_llm_service():
    """Get LLM service from orchestrator."""
    from ghoststorm.api.app import get_orchestrator

    orchestrator = get_orchestrator()
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    if not hasattr(orchestrator, "llm_service") or orchestrator.llm_service is None:
        raise HTTPException(status_code=503, detail="LLM service not initialized")

    return orchestrator.llm_service


def _get_llm_controller():
    """Get LLM controller from orchestrator."""
    from ghoststorm.api.app import get_orchestrator

    orchestrator = get_orchestrator()
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    if not hasattr(orchestrator, "llm_controller") or orchestrator.llm_controller is None:
        raise HTTPException(status_code=503, detail="LLM controller not initialized")

    return orchestrator.llm_controller


# Endpoints


@router.get("/providers", response_model=ListProvidersResponse)
async def list_providers() -> ListProvidersResponse:
    """List available LLM providers."""
    try:
        llm_service = _get_llm_service()
        providers = llm_service.list_providers()

        return ListProvidersResponse(
            providers=[
                ProviderInfoResponse(
                    name=p.name,
                    default_model=p.default_model,
                    supported_models=p.supported_models,
                    requires_api_key=p.requires_api_key,
                    supports_streaming=p.supports_streaming,
                    supports_tools=p.supports_tools,
                )
                for p in providers
            ],
            current_provider=llm_service.current_provider.value,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/set")
async def set_provider(request: SetProviderRequest) -> dict[str, str]:
    """Set the active LLM provider."""
    from ghoststorm.core.llm.service import ProviderType

    try:
        llm_service = _get_llm_service()

        # Validate provider
        try:
            provider_type = ProviderType(request.provider.lower())
        except ValueError:
            valid = [p.value for p in ProviderType]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider: {request.provider}. Valid: {valid}",
            )

        llm_service.set_provider(provider_type)
        return {"status": "ok", "provider": provider_type.value}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete", response_model=CompletionResponse)
async def complete(request: CompletionRequest) -> CompletionResponse:
    """Generate LLM completion."""
    from ghoststorm.core.llm.messages import Message, MessageRole
    from ghoststorm.core.llm.service import ProviderType

    try:
        llm_service = _get_llm_service()

        # Convert messages
        messages = []
        for msg in request.messages:
            role = MessageRole(msg.get("role", "user"))
            content = msg.get("content", "")
            messages.append(Message(role=role, content=content))

        # Parse provider if specified
        provider = None
        if request.provider:
            try:
                provider = ProviderType(request.provider.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {request.provider}")

        # Get completion
        response = await llm_service.complete(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            provider=provider,
        )

        return CompletionResponse(
            content=response.content,
            model=response.model,
            provider=llm_service.current_provider.value if not provider else provider.value,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.finish_reason,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_page(request: AnalyzePageRequest) -> AnalysisResponse:
    """Analyze a page and get suggested action."""
    from ghoststorm.api.app import get_orchestrator
    from ghoststorm.core.llm.service import ProviderType

    try:
        orchestrator = get_orchestrator()
        if orchestrator is None:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        # Get page from task
        page = orchestrator.get_page_for_task(request.task_id)
        if page is None:
            raise HTTPException(
                status_code=404, detail=f"No active page for task {request.task_id}"
            )

        controller = _get_llm_controller()

        # Parse provider
        provider = None
        if request.provider:
            try:
                provider = ProviderType(request.provider.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {request.provider}")

        # Analyze page
        analysis = await controller.analyze_page(page, request.task, provider)

        return AnalysisResponse(
            analysis=analysis.analysis,
            is_complete=analysis.is_complete,
            next_action=analysis.next_action.model_dump() if analysis.next_action else None,
            confidence=analysis.confidence,
            extracted_data=analysis.extracted_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=TaskResultResponse)
async def execute_task(request: ExecuteTaskRequest) -> TaskResultResponse:
    """Execute task autonomously using LLM."""
    from ghoststorm.api.app import get_orchestrator
    from ghoststorm.core.llm.controller import ControllerMode
    from ghoststorm.core.llm.service import ProviderType

    try:
        orchestrator = get_orchestrator()
        if orchestrator is None:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        # Get page from task
        page = orchestrator.get_page_for_task(request.task_id)
        if page is None:
            raise HTTPException(
                status_code=404, detail=f"No active page for task {request.task_id}"
            )

        controller = _get_llm_controller()

        # Set autonomous mode
        controller.set_mode(ControllerMode.AUTONOMOUS)
        controller.config.max_steps = request.max_steps

        # Parse provider
        provider = None
        if request.provider:
            try:
                provider = ProviderType(request.provider.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {request.provider}")

        # Execute task
        result = await controller.execute_task(page, request.task, provider)

        return TaskResultResponse(
            success=result.success,
            steps_taken=result.steps_taken,
            extracted_data=result.extracted_data,
            error=result.error,
            final_url=result.final_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage", response_model=UsageResponse)
async def get_usage() -> UsageResponse:
    """Get LLM usage statistics."""
    try:
        llm_service = _get_llm_service()
        summary = llm_service.get_usage_summary()

        return UsageResponse(
            total=summary["total"],
            by_provider=summary["by_provider"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/usage/reset")
async def reset_usage() -> dict[str, str]:
    """Reset LLM usage statistics."""
    try:
        llm_service = _get_llm_service()
        llm_service.reset_usage()
        return {"status": "ok", "message": "Usage statistics reset"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Check health of all LLM providers."""
    try:
        llm_service = _get_llm_service()
        results = await llm_service.health_check_all()

        return HealthCheckResponse(providers={p.value: healthy for p, healthy in results.items()})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
