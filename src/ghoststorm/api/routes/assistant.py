"""AI Assistant API endpoints."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ghoststorm.core.assistant import Agent, AgentConfig
from ghoststorm.core.assistant.agent import RECOMMENDED_MODELS

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

# Global agent instance (per-session in production)
_agent: Agent | None = None
_pending_actions: dict[str, dict[str, Any]] = {}


def _get_agent() -> Agent:
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        # Get project root (parent of src directory)
        project_root = Path(__file__).parent.parent.parent.parent.parent
        _agent = Agent(
            config=AgentConfig(
                project_root=str(project_root),
                model="llama3.2",
            )
        )
    return _agent


# Request/Response Models


class ChatRequest(BaseModel):
    """Chat message request."""
    message: str = Field(description="User message")
    stream: bool = Field(default=False, description="Stream response")


class ChatResponse(BaseModel):
    """Chat response."""
    content: str
    has_pending_actions: bool = False
    pending_action_id: str | None = None


class FileReadRequest(BaseModel):
    """File read request."""
    path: str = Field(description="File path to read")


class FileReadResponse(BaseModel):
    """File read response."""
    content: str | None
    error: str | None = None


class FileWriteRequest(BaseModel):
    """File write request."""
    path: str = Field(description="File path to write")
    content: str = Field(description="File content")


class FileWriteResponse(BaseModel):
    """File write response."""
    success: bool
    error: str | None = None


class ListFilesRequest(BaseModel):
    """List files request."""
    path: str = Field(default=".", description="Directory path")
    pattern: str = Field(default="*", description="Glob pattern")
    recursive: bool = Field(default=False)


class ListFilesResponse(BaseModel):
    """List files response."""
    files: list[str] | None
    error: str | None = None


class ExecuteRequest(BaseModel):
    """Command execution request."""
    command: str = Field(description="Command to execute")


class ExecuteResponse(BaseModel):
    """Command execution response."""
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    requires_approval: bool = False


class ActionApprovalRequest(BaseModel):
    """Action approval request."""
    action_id: str = Field(description="Action ID to approve/reject")
    approved: bool = Field(description="Whether to approve")


class ContextResponse(BaseModel):
    """Context information response."""
    project_root: str
    model: str
    message_count: int
    has_pyproject: bool = False
    src_dirs: list[str] = []


class SearchRequest(BaseModel):
    """Search request."""
    query: str = Field(description="Search query")
    file_pattern: str = Field(default="*.py", description="File pattern")


class SearchResponse(BaseModel):
    """Search response."""
    matches: list[dict[str, Any]] | None
    error: str | None = None


# Endpoints


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse | StreamingResponse:
    """Chat with the AI assistant."""
    agent = _get_agent()

    if request.stream:
        async def generate():
            response = await agent.chat(request.message, stream=True)
            async for chunk in response:
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/plain",
        )

    try:
        response = await agent.chat(request.message, stream=False)
        return ChatResponse(
            content=response,
            has_pending_actions=len(agent.get_pending_approvals()) > 0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files", response_model=ListFilesResponse)
async def list_files(
    path: str = ".",
    pattern: str = "*",
    recursive: bool = False,
) -> ListFilesResponse:
    """List files in a directory."""
    agent = _get_agent()

    files, error = await agent.file_sandbox.list_files(path, pattern, recursive)
    return ListFilesResponse(files=files, error=error)


@router.get("/file", response_model=FileReadResponse)
async def read_file(path: str) -> FileReadResponse:
    """Read a file."""
    agent = _get_agent()

    content, error = await agent.file_sandbox.read_file(path)
    return FileReadResponse(content=content, error=error)


@router.post("/file", response_model=FileWriteResponse)
async def write_file(request: FileWriteRequest) -> FileWriteResponse:
    """Write a file (requires approval in UI)."""
    agent = _get_agent()

    success, error = await agent.file_sandbox.write_file(
        request.path,
        request.content,
        create_dirs=True,
    )
    return FileWriteResponse(success=success, error=error)


@router.post("/execute", response_model=ExecuteResponse)
async def execute_command(request: ExecuteRequest) -> ExecuteResponse:
    """Execute a command."""
    agent = _get_agent()

    # Check if command requires approval
    is_allowed, blocked_reason, requires_approval = agent.command_sandbox.validate_command(
        request.command
    )

    if not is_allowed:
        return ExecuteResponse(
            status="blocked",
            stdout="",
            stderr=blocked_reason or "Command blocked",
            exit_code=None,
            requires_approval=False,
        )

    if requires_approval:
        # Store pending action
        import uuid
        action_id = str(uuid.uuid4())
        _pending_actions[action_id] = {
            "type": "execute",
            "command": request.command,
        }
        return ExecuteResponse(
            status="pending_approval",
            stdout="",
            stderr="",
            exit_code=None,
            requires_approval=True,
        )

    # Execute command
    result = await agent.command_sandbox.execute(request.command)
    return ExecuteResponse(
        status=result.status.value,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        requires_approval=False,
    )


@router.post("/search", response_model=SearchResponse)
async def search_files(request: SearchRequest) -> SearchResponse:
    """Search for text in files."""
    agent = _get_agent()

    matches, error = await agent.file_sandbox.search_files(
        request.query,
        ".",
        request.file_pattern,
    )
    return SearchResponse(matches=matches, error=error)


@router.get("/context", response_model=ContextResponse)
async def get_context() -> ContextResponse:
    """Get current context information."""
    agent = _get_agent()
    context = await agent.get_context()

    return ContextResponse(
        project_root=context.get("project_root", ""),
        model=context.get("model", ""),
        message_count=context.get("message_count", 0),
        has_pyproject=context.get("has_pyproject", False),
        src_dirs=context.get("src_dirs", []),
    )


@router.post("/reset")
async def reset_conversation() -> dict[str, str]:
    """Reset the conversation history."""
    agent = _get_agent()
    agent.reset()
    return {"status": "ok", "message": "Conversation reset"}


@router.post("/action/approve")
async def approve_action(request: ActionApprovalRequest) -> dict[str, Any]:
    """Approve or reject a pending action."""
    if request.action_id not in _pending_actions:
        raise HTTPException(status_code=404, detail="Action not found")

    action = _pending_actions.pop(request.action_id)

    if not request.approved:
        return {"status": "rejected", "action": action}

    agent = _get_agent()

    # Execute the approved action
    if action["type"] == "execute":
        result = await agent.command_sandbox.execute(action["command"])
        return {
            "status": "executed",
            "result": {
                "status": result.status.value,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
            },
        }
    elif action["type"] == "write_file":
        success, error = await agent.file_sandbox.write_file(
            action["path"],
            action["content"],
            create_dirs=True,
        )
        return {
            "status": "executed",
            "result": {"success": success, "error": error},
        }

    return {"status": "unknown_action"}


@router.get("/pending")
async def get_pending_actions() -> dict[str, Any]:
    """Get list of pending actions awaiting approval."""
    return {"pending": list(_pending_actions.items())}


@router.get("/models")
async def list_models() -> dict[str, Any]:
    """List available Ollama models with recommendations."""
    import httpx

    agent = _get_agent()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{agent.config.ollama_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            available = [m["name"] for m in data.get("models", [])]

            # Find best available model from recommendations
            best_available = None
            for recommended in RECOMMENDED_MODELS:
                # Check exact match or base name match (e.g., "qwen2.5-coder:32b" matches "qwen2.5-coder")
                for model in available:
                    if model == recommended or model.startswith(recommended.split(":")[0]):
                        if best_available is None:
                            best_available = model
                        break

            return {
                "models": available,
                "current": agent.config.model,
                "recommended": RECOMMENDED_MODELS,
                "best_available": best_available,
            }
    except Exception as e:
        return {
            "models": [],
            "error": str(e),
            "current": agent.config.model,
            "recommended": RECOMMENDED_MODELS,
        }


@router.post("/models/set")
async def set_model(model: str) -> dict[str, str]:
    """Set the Ollama model to use."""
    agent = _get_agent()
    agent.config.model = model
    return {"status": "ok", "model": model}


@router.post("/models/pull")
async def pull_model(model: str) -> StreamingResponse:
    """Pull/install a model from Ollama."""
    import httpx

    agent = _get_agent()

    async def stream_pull():
        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{agent.config.ollama_url}/api/pull",
                    json={"name": model, "stream": True},
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            yield line + "\n"
            except Exception as e:
                yield f'{{"error": "{str(e)}"}}\n'

    return StreamingResponse(stream_pull(), media_type="application/x-ndjson")


@router.delete("/models/{model_name}")
async def delete_model(model_name: str) -> dict[str, str]:
    """Delete a model from Ollama."""
    import httpx

    agent = _get_agent()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{agent.config.ollama_url}/api/delete",
                json={"name": model_name},
            )
            if response.status_code == 200:
                return {"status": "ok", "deleted": model_name}
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to delete model")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
async def get_settings() -> dict[str, Any]:
    """Get assistant settings."""
    agent = _get_agent()
    return {
        "model": agent.config.model,
        "temperature": agent.config.temperature,
        "max_tokens": agent.config.max_tokens,
        "ollama_url": agent.config.ollama_url,
        "command_timeout": agent.config.command_timeout,
        "recommended_models": RECOMMENDED_MODELS,
    }


@router.post("/settings")
async def update_settings(
    temperature: float | None = None,
    max_tokens: int | None = None,
    command_timeout: float | None = None,
) -> dict[str, str]:
    """Update assistant settings."""
    agent = _get_agent()

    if temperature is not None:
        agent.config.temperature = max(0.0, min(2.0, temperature))
    if max_tokens is not None:
        agent.config.max_tokens = max(256, min(32768, max_tokens))
    if command_timeout is not None:
        agent.config.command_timeout = max(5.0, min(300.0, command_timeout))

    return {"status": "ok"}


# Docker/Ollama Container Management

DOCKER_CONTAINER_NAME = "ghoststorm-ollama"
DOCKER_IMAGE = "ollama/ollama:latest"


class DockerStatusResponse(BaseModel):
    """Docker container status."""
    docker_available: bool
    container_exists: bool
    container_running: bool
    container_id: str | None = None
    error: str | None = None


async def _run_docker_command(args: list[str]) -> tuple[str, str, int]:
    """Run a docker command and return stdout, stderr, exit_code."""
    proc = await asyncio.create_subprocess_exec(
        "docker", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode(), proc.returncode or 0


@router.get("/docker/status", response_model=DockerStatusResponse)
async def get_docker_status() -> DockerStatusResponse:
    """Get Docker and Ollama container status."""
    # Check if Docker is available
    try:
        _, _, code = await _run_docker_command(["version", "--format", "{{.Server.Version}}"])
        if code != 0:
            return DockerStatusResponse(
                docker_available=False,
                container_exists=False,
                container_running=False,
                error="Docker is not running",
            )
    except FileNotFoundError:
        return DockerStatusResponse(
            docker_available=False,
            container_exists=False,
            container_running=False,
            error="Docker is not installed",
        )

    # Check container status
    stdout, _, code = await _run_docker_command([
        "ps", "-a", "--filter", f"name={DOCKER_CONTAINER_NAME}",
        "--format", "{{.ID}}|{{.Status}}"
    ])

    if not stdout.strip():
        return DockerStatusResponse(
            docker_available=True,
            container_exists=False,
            container_running=False,
        )

    container_id, status = stdout.strip().split("|", 1)
    is_running = status.lower().startswith("up")

    return DockerStatusResponse(
        docker_available=True,
        container_exists=True,
        container_running=is_running,
        container_id=container_id,
    )


@router.post("/docker/start")
async def start_ollama_container() -> dict[str, Any]:
    """Start the Ollama Docker container with GPU support."""
    # Check current status
    status = await get_docker_status()

    if not status.docker_available:
        raise HTTPException(status_code=503, detail=status.error or "Docker not available")

    # If container exists but stopped, start it
    if status.container_exists and not status.container_running:
        _, stderr, code = await _run_docker_command(["start", DOCKER_CONTAINER_NAME])
        if code != 0:
            raise HTTPException(status_code=500, detail=f"Failed to start container: {stderr}")
        return {"status": "started", "container": DOCKER_CONTAINER_NAME}

    # If container already running
    if status.container_running:
        return {"status": "already_running", "container": DOCKER_CONTAINER_NAME}

    # Create and start new container
    # First, pull image if needed
    _, stderr, code = await _run_docker_command(["pull", DOCKER_IMAGE])
    if code != 0:
        raise HTTPException(status_code=500, detail=f"Failed to pull image: {stderr}")

    # Run container with GPU support
    _, stderr, code = await _run_docker_command([
        "run", "-d",
        "--name", DOCKER_CONTAINER_NAME,
        "--gpus", "all",
        "-v", "ollama_data:/root/.ollama",
        "-p", "11434:11434",
        "--restart", "unless-stopped",
        DOCKER_IMAGE,
    ])

    if code != 0:
        # If GPU failed, try without GPU
        if "gpu" in stderr.lower() or "nvidia" in stderr.lower():
            _, stderr2, code2 = await _run_docker_command([
                "run", "-d",
                "--name", DOCKER_CONTAINER_NAME,
                "-v", "ollama_data:/root/.ollama",
                "-p", "11434:11434",
                "--restart", "unless-stopped",
                DOCKER_IMAGE,
            ])
            if code2 != 0:
                raise HTTPException(status_code=500, detail=f"Failed to create container: {stderr2}")
            return {"status": "created", "container": DOCKER_CONTAINER_NAME, "gpu": False}

        raise HTTPException(status_code=500, detail=f"Failed to create container: {stderr}")

    return {"status": "created", "container": DOCKER_CONTAINER_NAME, "gpu": True}


@router.post("/docker/stop")
async def stop_ollama_container() -> dict[str, str]:
    """Stop the Ollama Docker container."""
    status = await get_docker_status()

    if not status.container_exists:
        return {"status": "not_found"}

    if not status.container_running:
        return {"status": "already_stopped"}

    _, stderr, code = await _run_docker_command(["stop", DOCKER_CONTAINER_NAME])
    if code != 0:
        raise HTTPException(status_code=500, detail=f"Failed to stop container: {stderr}")

    return {"status": "stopped"}


@router.delete("/docker/container")
async def remove_ollama_container() -> dict[str, str]:
    """Remove the Ollama Docker container (keeps data volume)."""
    status = await get_docker_status()

    if not status.container_exists:
        return {"status": "not_found"}

    # Stop if running
    if status.container_running:
        await _run_docker_command(["stop", DOCKER_CONTAINER_NAME])

    _, stderr, code = await _run_docker_command(["rm", DOCKER_CONTAINER_NAME])
    if code != 0:
        raise HTTPException(status_code=500, detail=f"Failed to remove container: {stderr}")

    return {"status": "removed"}


@router.get("/docker/logs")
async def get_container_logs(tail: int = 100) -> StreamingResponse:
    """Stream container logs."""
    async def stream_logs():
        proc = await asyncio.create_subprocess_exec(
            "docker", "logs", "-f", "--tail", str(tail), DOCKER_CONTAINER_NAME,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                yield line.decode()
        finally:
            proc.terminate()

    return StreamingResponse(stream_logs(), media_type="text/plain")
