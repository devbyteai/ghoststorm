"""Flow storage for persisting recorded flows to JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from ghoststorm.core.models.flow import RecordedFlow, FlowStatus

logger = structlog.get_logger(__name__)


class FlowStorage:
    """Storage for recorded flows using JSON files."""

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        """Initialize flow storage.

        Args:
            storage_dir: Directory to store flow JSON files.
                        Defaults to data/flows/
        """
        if storage_dir is None:
            # Default to project root/data/flows/
            self.storage_dir = Path(__file__).parents[4] / "data" / "flows"
        else:
            self.storage_dir = Path(storage_dir)

        # Ensure directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Flow storage initialized", path=str(self.storage_dir))

    def _get_flow_path(self, flow_id: str) -> Path:
        """Get the file path for a flow."""
        return self.storage_dir / f"{flow_id}.json"

    async def save(self, flow: RecordedFlow) -> bool:
        """Save a flow to storage.

        Args:
            flow: The flow to save.

        Returns:
            True if saved successfully.
        """
        try:
            flow_path = self._get_flow_path(flow.id)
            flow_data = flow.to_dict()

            with open(flow_path, "w", encoding="utf-8") as f:
                json.dump(flow_data, f, indent=2, ensure_ascii=False)

            logger.debug("Flow saved", flow_id=flow.id, path=str(flow_path))
            return True

        except Exception as e:
            logger.error("Failed to save flow", flow_id=flow.id, error=str(e))
            return False

    async def load(self, flow_id: str) -> RecordedFlow | None:
        """Load a flow from storage.

        Args:
            flow_id: ID of the flow to load.

        Returns:
            The loaded flow, or None if not found.
        """
        try:
            flow_path = self._get_flow_path(flow_id)

            if not flow_path.exists():
                logger.warning("Flow not found", flow_id=flow_id)
                return None

            with open(flow_path, "r", encoding="utf-8") as f:
                flow_data = json.load(f)

            flow = RecordedFlow.from_dict(flow_data)
            logger.debug("Flow loaded", flow_id=flow_id)
            return flow

        except Exception as e:
            logger.error("Failed to load flow", flow_id=flow_id, error=str(e))
            return None

    async def delete(self, flow_id: str) -> bool:
        """Delete a flow from storage.

        Args:
            flow_id: ID of the flow to delete.

        Returns:
            True if deleted successfully.
        """
        try:
            flow_path = self._get_flow_path(flow_id)

            if not flow_path.exists():
                logger.warning("Flow not found for deletion", flow_id=flow_id)
                return False

            flow_path.unlink()
            logger.info("Flow deleted", flow_id=flow_id)
            return True

        except Exception as e:
            logger.error("Failed to delete flow", flow_id=flow_id, error=str(e))
            return False

    async def list_flows(
        self,
        status: FlowStatus | None = None,
        tags: list[str] | None = None,
    ) -> list[RecordedFlow]:
        """List all flows in storage.

        Args:
            status: Filter by flow status.
            tags: Filter by tags (any match).

        Returns:
            List of flows matching criteria.
        """
        flows: list[RecordedFlow] = []

        try:
            for flow_file in self.storage_dir.glob("*.json"):
                try:
                    with open(flow_file, "r", encoding="utf-8") as f:
                        flow_data = json.load(f)

                    flow = RecordedFlow.from_dict(flow_data)

                    # Apply filters
                    if status is not None and flow.status != status:
                        continue

                    if tags is not None:
                        if not any(tag in flow.tags for tag in tags):
                            continue

                    flows.append(flow)

                except Exception as e:
                    logger.warning(
                        "Failed to load flow file",
                        file=str(flow_file),
                        error=str(e),
                    )
                    continue

            # Sort by updated_at descending (most recent first)
            flows.sort(key=lambda f: f.updated_at, reverse=True)

            logger.debug("Listed flows", count=len(flows))
            return flows

        except Exception as e:
            logger.error("Failed to list flows", error=str(e))
            return []

    async def get_flow_summary(self) -> dict[str, Any]:
        """Get summary statistics for all flows.

        Returns:
            Dictionary with flow statistics.
        """
        flows = await self.list_flows()

        total = len(flows)
        ready = sum(1 for f in flows if f.status == FlowStatus.READY)
        draft = sum(1 for f in flows if f.status == FlowStatus.DRAFT)
        disabled = sum(1 for f in flows if f.status == FlowStatus.DISABLED)

        total_executions = sum(f.times_executed for f in flows)
        total_successful = sum(f.successful_executions for f in flows)

        return {
            "total_flows": total,
            "ready": ready,
            "draft": draft,
            "disabled": disabled,
            "total_executions": total_executions,
            "total_successful": total_successful,
            "overall_success_rate": (
                total_successful / total_executions if total_executions > 0 else 0.0
            ),
        }

    async def exists(self, flow_id: str) -> bool:
        """Check if a flow exists.

        Args:
            flow_id: ID of the flow to check.

        Returns:
            True if flow exists.
        """
        return self._get_flow_path(flow_id).exists()

    async def update_execution_stats(
        self,
        flow_id: str,
        success: bool,
    ) -> bool:
        """Update execution statistics for a flow.

        Args:
            flow_id: ID of the flow.
            success: Whether the execution was successful.

        Returns:
            True if updated successfully.
        """
        flow = await self.load(flow_id)
        if flow is None:
            return False

        flow.record_execution(success)
        return await self.save(flow)


# Global storage instance
_storage: FlowStorage | None = None


def get_flow_storage() -> FlowStorage:
    """Get the global flow storage instance."""
    global _storage
    if _storage is None:
        _storage = FlowStorage()
    return _storage
