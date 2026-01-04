"""DOM API endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter()


class FindElementRequest(BaseModel):
    """Request to find an element by description."""

    description: str
    element_type: str | None = None
    max_results: int = 5


class ElementResponse(BaseModel):
    """Response containing element info."""

    selector: str
    xpath: str
    description: str
    element_type: str
    text: str | None = None
    index: int


# In-memory DOM state cache (per task)
_dom_states: dict[str, dict[str, Any]] = {}


@router.get("")
async def get_dom_info() -> dict[str, Any]:
    """
    Get DOM service information.

    Returns information about the DOM service configuration.
    """
    return {
        "service": "DOMService",
        "version": "1.0.0",
        "features": [
            "DOM extraction",
            "Interactive element detection",
            "Smart selector generation",
            "Natural language element matching",
        ],
        "cached_states": len(_dom_states),
    }


@router.get("/state/{task_id}")
async def get_dom_state(task_id: str) -> dict[str, Any]:
    """
    Get cached DOM state for a task.

    Args:
        task_id: ID of the task

    Returns:
        Cached DOM state or 404
    """
    if task_id not in _dom_states:
        raise HTTPException(
            status_code=404,
            detail=f"No DOM state cached for task: {task_id}",
        )

    return _dom_states[task_id]


@router.delete("/state/{task_id}")
async def clear_dom_state(task_id: str) -> dict[str, str]:
    """
    Clear cached DOM state for a task.

    Args:
        task_id: ID of the task

    Returns:
        Confirmation message
    """
    if task_id in _dom_states:
        del _dom_states[task_id]
        return {"status": "cleared", "task_id": task_id}

    return {"status": "not_found", "task_id": task_id}


@router.post("/state/{task_id}")
async def store_dom_state(task_id: str, state: dict[str, Any]) -> dict[str, str]:
    """
    Store DOM state for a task.

    This is typically called internally after DOM extraction.

    Args:
        task_id: ID of the task
        state: DOM state to cache
    """
    _dom_states[task_id] = state
    return {"status": "stored", "task_id": task_id}


@router.get("/elements/{task_id}")
async def get_interactive_elements(task_id: str) -> dict[str, Any]:
    """
    Get interactive elements from cached DOM state.

    Args:
        task_id: ID of the task

    Returns:
        List of interactive elements
    """
    if task_id not in _dom_states:
        raise HTTPException(
            status_code=404,
            detail=f"No DOM state cached for task: {task_id}",
        )

    state = _dom_states[task_id]

    return {
        "task_id": task_id,
        "clickables": state.get("clickables", []),
        "inputs": state.get("inputs", []),
        "links": state.get("links", []),
        "counts": state.get("counts", {}),
    }


@router.post("/analyze")
async def analyze_dom(request: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze DOM state with a query.

    Finds elements matching a natural language description
    from a provided DOM state.

    Args:
        request: Contains 'dom_state' and 'query'

    Returns:
        Matching elements
    """
    from ghoststorm.core.dom import BoundingBox, DOMAnalyzer, DOMNode, DOMState, ElementInfo

    dom_data = request.get("dom_state")
    query = request.get("query", "")

    if not dom_data:
        raise HTTPException(
            status_code=400,
            detail="Missing 'dom_state' in request",
        )

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Missing 'query' in request",
        )

    try:
        # Reconstruct DOMState from data
        # This is a simplified reconstruction
        clickables = []
        for idx, elem_data in enumerate(dom_data.get("clickables", [])):
            node_data = elem_data.get("node", {})
            bbox_data = node_data.get("bounding_box")

            node = DOMNode(
                tag=node_data.get("tag", "unknown"),
                node_id=node_data.get("node_id", ""),
                text=node_data.get("text", ""),
                attributes=node_data.get("attributes", {}),
            )

            if bbox_data:
                node.bounding_box = BoundingBox.from_dict(bbox_data)

            clickables.append(
                ElementInfo(
                    node=node,
                    selector=elem_data.get("selector", ""),
                    xpath=elem_data.get("xpath", ""),
                    description=elem_data.get("description", ""),
                    index=idx,
                )
            )

        dom_state = DOMState(
            url=dom_data.get("url", ""),
            title=dom_data.get("title", ""),
            clickables=clickables,
        )

        # Run analysis
        analyzer = DOMAnalyzer()
        matches = analyzer.find_matches(dom_state, query, max_results=5)

        return {
            "query": query,
            "matches": [m.to_dict() for m in matches],
            "count": len(matches),
        }

    except Exception as e:
        logger.exception("DOM analysis failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {e!s}",
        )


@router.get("/config")
async def get_dom_config() -> dict[str, Any]:
    """Get current DOM extraction configuration."""
    from ghoststorm.core.dom import DOMConfig

    config = DOMConfig()
    return config.to_dict()
