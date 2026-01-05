"""End-to-end journey test for flow recording and playback.

This test simulates a complete user journey:
1. Record a browser flow
2. Add checkpoints
3. Finalize and save
4. Execute the saved flow
5. Verify execution results
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghoststorm.core.models.flow import (
    Checkpoint,
    CheckpointType,
    FlowExecutionConfig,
    FlowExecutionResult,
    FlowStatus,
    RecordedFlow,
    TimingConfig,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def create_mock_flow(
    flow_id: str = "test-flow-id",
    name: str = "Test Flow",
    status: FlowStatus = FlowStatus.DRAFT,
    checkpoints: list[Checkpoint] | None = None,
) -> RecordedFlow:
    """Create a mock RecordedFlow for testing."""
    flow = RecordedFlow(
        name=name,
        description="A test flow",
        start_url="https://example.com",
        status=status,
    )
    # Override the auto-generated ID
    flow.id = flow_id
    if checkpoints:
        for cp in checkpoints:
            flow.add_checkpoint(cp)
    return flow


def create_mock_checkpoint(
    checkpoint_id: str = "checkpoint-1",
    goal: str = "Click the button",
    checkpoint_type: CheckpointType = CheckpointType.CLICK,
) -> Checkpoint:
    """Create a mock Checkpoint for testing."""
    cp = Checkpoint(
        checkpoint_type=checkpoint_type,
        goal=goal,
        url_pattern="https://example.com/*",
        element_description="The submit button",
        timing=TimingConfig(min_delay=0.5, max_delay=2.0, timeout=30.0),
    )
    cp.id = checkpoint_id
    return cp


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.flow
class TestFlowRecordPlaybackJourney:
    """Complete flow recording and playback workflow."""

    def test_complete_flow_workflow(
        self,
        api_test_client: TestClient,
        mock_orchestrator,
    ):
        """Test complete flow from recording to execution."""
        # Create mock objects
        mock_flow = create_mock_flow(flow_id="session-123", status=FlowStatus.DRAFT)
        mock_recorder = MagicMock()
        mock_recorder.is_recording = False
        mock_recorder.current_flow = None
        mock_recorder.start_recording = AsyncMock(return_value=mock_flow)
        mock_recorder.add_checkpoint = AsyncMock(return_value=create_mock_checkpoint())
        mock_recorder.stop_recording = AsyncMock(return_value=mock_flow)

        mock_storage = MagicMock()
        mock_storage.list_flows = AsyncMock(return_value=[])
        mock_storage.load = AsyncMock(return_value=None)
        mock_storage.save = AsyncMock(return_value=True)
        mock_storage.exists = AsyncMock(return_value=False)
        mock_storage.delete = AsyncMock(return_value=True)

        # Step 1: Start recording a flow
        with patch(
            "ghoststorm.api.routes.flows.get_flow_recorder", return_value=mock_recorder
        ):
            with patch(
                "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
            ):
                record_response = api_test_client.post(
                    "/api/flows/record/start",
                    json={
                        "name": "Test Recording",
                        "start_url": "https://example.com",
                        "description": "Test recording session",
                        "stealth": {
                            "use_proxy": False,
                            "use_fingerprint": True,
                            "block_webrtc": True,
                            "canvas_noise": True,
                        },
                    },
                )

                assert record_response.status_code == 200
                data = record_response.json()
                assert data["status"] == "recording"
                assert data["flow_id"] == "session-123"
                session_id = data["flow_id"]

        # Step 2: Add checkpoints during recording
        mock_recorder.is_recording = True
        mock_recorder.current_flow = mock_flow
        mock_checkpoint = create_mock_checkpoint(goal="Page Loaded")

        with patch(
            "ghoststorm.api.routes.flows.get_flow_recorder", return_value=mock_recorder
        ):
            mock_recorder.add_checkpoint = AsyncMock(return_value=mock_checkpoint)

            checkpoint_response = api_test_client.post(
                f"/api/flows/record/{session_id}/checkpoint",
                json={
                    "checkpoint_type": "navigation",
                    "goal": "Page Loaded",
                    "timing": {"min_delay": 0.5, "max_delay": 3.0, "timeout": 30.0},
                },
            )

            assert checkpoint_response.status_code == 200
            cp_data = checkpoint_response.json()
            assert cp_data["goal"] == "Page Loaded"

        # Step 3: Stop recording and finalize flow
        mock_flow.checkpoints.append(mock_checkpoint)
        mock_recorder.stop_recording = AsyncMock(return_value=mock_flow)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_recorder", return_value=mock_recorder
        ):
            stop_response = api_test_client.post(f"/api/flows/record/{session_id}/stop")

            assert stop_response.status_code == 200
            stop_data = stop_response.json()
            assert stop_data["flow_id"] == session_id
            assert stop_data["checkpoint_count"] >= 0

        # Step 4: Create a new flow via POST /api/flows
        new_flow = create_mock_flow(flow_id="new-flow-id", status=FlowStatus.DRAFT)
        mock_storage.save = AsyncMock(return_value=True)
        mock_storage.load = AsyncMock(return_value=new_flow)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            save_response = api_test_client.post(
                "/api/flows",
                json={
                    "name": "Test Flow",
                    "description": "A test automation flow",
                    "start_url": "https://example.com",
                    "tags": ["test", "automation"],
                },
            )

            assert save_response.status_code == 200
            flow_data = save_response.json()
            flow_id = flow_data.get("id")
            assert flow_id is not None

        # Step 5: Verify flow can be retrieved
        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            mock_storage.load = AsyncMock(return_value=new_flow)
            get_response = api_test_client.get(f"/api/flows/{flow_id}")
            assert get_response.status_code == 200

        # Step 6: Execute the saved flow
        ready_flow = create_mock_flow(
            flow_id=flow_id, status=FlowStatus.READY, checkpoints=[mock_checkpoint]
        )
        mock_storage.load = AsyncMock(return_value=ready_flow)

        mock_executor = MagicMock()
        mock_result = FlowExecutionResult(
            flow_id=flow_id,
            total_checkpoints=1,
            browser_engine="patchright",
        )
        mock_result.success = True
        mock_executor.execute = AsyncMock(return_value=mock_result)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            with patch(
                "ghoststorm.api.routes.flows.get_flow_executor", return_value=mock_executor
            ):
                execute_response = api_test_client.post(
                    f"/api/flows/{flow_id}/execute",
                    json={
                        "browser_engine": "patchright",
                        "variation_level": "medium",
                        "workers": 1,
                        "use_proxy": False,
                    },
                )

                assert execute_response.status_code == 200
                exec_data = execute_response.json()
                assert exec_data["status"] == "started"


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.flow
class TestFlowWithStealthOptions:
    """Test flow recording with various stealth configurations."""

    def test_flow_with_minimal_stealth(self, api_test_client: TestClient):
        """Test recording with minimal stealth preset."""
        mock_flow = create_mock_flow(flow_id="stealth-flow-1")
        mock_recorder = MagicMock()
        mock_recorder.is_recording = False
        mock_recorder.start_recording = AsyncMock(return_value=mock_flow)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_recorder", return_value=mock_recorder
        ):
            response = api_test_client.post(
                "/api/flows/record/start",
                json={
                    "name": "Minimal Stealth Flow",
                    "start_url": "https://example.com",
                    "stealth": {
                        "use_proxy": False,
                        "use_fingerprint": False,
                        "block_webrtc": True,
                        "canvas_noise": False,
                    },
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "recording"
            assert data["flow_id"] == "stealth-flow-1"

    def test_flow_with_aggressive_stealth(self, api_test_client: TestClient):
        """Test recording with aggressive stealth preset."""
        mock_flow = create_mock_flow(flow_id="stealth-flow-2")
        mock_recorder = MagicMock()
        mock_recorder.is_recording = False
        mock_recorder.start_recording = AsyncMock(return_value=mock_flow)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_recorder", return_value=mock_recorder
        ):
            response = api_test_client.post(
                "/api/flows/record/start",
                json={
                    "name": "Aggressive Stealth Flow",
                    "start_url": "https://example.com",
                    "stealth": {
                        "use_proxy": True,
                        "use_fingerprint": True,
                        "block_webrtc": True,
                        "canvas_noise": True,
                    },
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "recording"

    def test_flow_with_cloud_stealth(self, api_test_client: TestClient):
        """Test recording with cloud-optimized stealth."""
        mock_flow = create_mock_flow(flow_id="stealth-flow-3")
        mock_recorder = MagicMock()
        mock_recorder.is_recording = False
        mock_recorder.start_recording = AsyncMock(return_value=mock_flow)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_recorder", return_value=mock_recorder
        ):
            response = api_test_client.post(
                "/api/flows/record/start",
                json={
                    "name": "Cloud Stealth Flow",
                    "start_url": "https://example.com",
                    "stealth": {
                        "use_proxy": True,
                        "use_fingerprint": True,
                        "block_webrtc": True,
                        "canvas_noise": True,
                    },
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "recording"


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.flow
class TestFlowCheckpoints:
    """Test flow checkpoint functionality."""

    def test_checkpoint_with_assertions(self, api_test_client: TestClient):
        """Test checkpoints with element assertions."""
        mock_flow = create_mock_flow(flow_id="test-session")
        mock_checkpoint = create_mock_checkpoint(goal="Login Form Visible")

        mock_recorder = MagicMock()
        mock_recorder.is_recording = True
        mock_recorder.current_flow = mock_flow
        mock_recorder.add_checkpoint = AsyncMock(return_value=mock_checkpoint)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_recorder", return_value=mock_recorder
        ):
            response = api_test_client.post(
                "/api/flows/record/test-session/checkpoint",
                json={
                    "checkpoint_type": "click",
                    "goal": "Login Form Visible",
                    "element_description": "The login form container",
                    "selector_hints": ["#login-form", ".login-container"],
                    "timing": {"min_delay": 0.5, "max_delay": 3.0, "timeout": 30.0},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["goal"] == "Login Form Visible"

    def test_checkpoint_with_screenshot(self, api_test_client: TestClient):
        """Test checkpoint with screenshot capture."""
        mock_flow = create_mock_flow(flow_id="test-session")
        mock_checkpoint = create_mock_checkpoint(goal="Before Submit")
        mock_checkpoint.reference_screenshot = "base64encodeddata..."

        mock_recorder = MagicMock()
        mock_recorder.is_recording = True
        mock_recorder.current_flow = mock_flow
        mock_recorder.add_checkpoint = AsyncMock(return_value=mock_checkpoint)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_recorder", return_value=mock_recorder
        ):
            response = api_test_client.post(
                "/api/flows/record/test-session/checkpoint",
                json={
                    "checkpoint_type": "custom",
                    "goal": "Before Submit",
                    "reference_screenshot": "base64encodeddata...",
                    "timing": {"min_delay": 0.5, "max_delay": 3.0, "timeout": 30.0},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_screenshot"] is True


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.flow
class TestFlowManagement:
    """Test flow library management."""

    def test_list_saved_flows(self, api_test_client: TestClient):
        """Test listing all saved flows."""
        mock_flows = [
            create_mock_flow(flow_id="flow-1", name="Flow 1", status=FlowStatus.READY),
            create_mock_flow(flow_id="flow-2", name="Flow 2", status=FlowStatus.DRAFT),
        ]

        mock_storage = MagicMock()
        mock_storage.list_flows = AsyncMock(return_value=mock_flows)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            response = api_test_client.get("/api/flows")

            assert response.status_code == 200
            data = response.json()
            assert "flows" in data
            assert data["total"] == 2
            assert data["ready"] == 1
            assert data["draft"] == 1

    def test_duplicate_flow(self, api_test_client: TestClient):
        """Test duplicating a flow (via create with same data)."""
        # The API doesn't have a /duplicate endpoint, so we test creating a similar flow
        mock_flow = create_mock_flow(flow_id="duplicated-flow")
        mock_storage = MagicMock()
        mock_storage.save = AsyncMock(return_value=True)
        mock_storage.load = AsyncMock(return_value=mock_flow)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            response = api_test_client.post(
                "/api/flows",
                json={
                    "name": "Duplicated Flow",
                    "description": "A copy of another flow",
                    "start_url": "https://example.com",
                    "tags": ["duplicate"],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Flow"  # From mock

    def test_export_flow(self, api_test_client: TestClient):
        """Test exporting a flow (get full flow data)."""
        mock_flow = create_mock_flow(
            flow_id="test-flow",
            name="Test Flow",
            status=FlowStatus.READY,
        )

        mock_storage = MagicMock()
        mock_storage.load = AsyncMock(return_value=mock_flow)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            response = api_test_client.get("/api/flows/test-flow")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-flow"
            assert data["name"] == "Test Flow"

    def test_import_flow(self, api_test_client: TestClient):
        """Test importing a flow (create new flow)."""
        mock_flow = create_mock_flow(flow_id="imported-flow")
        mock_storage = MagicMock()
        mock_storage.save = AsyncMock(return_value=True)
        mock_storage.load = AsyncMock(return_value=mock_flow)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            response = api_test_client.post(
                "/api/flows",
                json={
                    "name": "Imported Flow",
                    "description": "An imported flow",
                    "start_url": "https://example.com",
                    "tags": ["imported"],
                },
            )

            assert response.status_code == 200

    def test_delete_flow(self, api_test_client: TestClient):
        """Test deleting a flow."""
        mock_storage = MagicMock()
        mock_storage.exists = AsyncMock(return_value=True)
        mock_storage.delete = AsyncMock(return_value=True)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            response = api_test_client.delete("/api/flows/test-flow")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "deleted"


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.flow
class TestFlowExecution:
    """Test flow execution scenarios."""

    def test_execute_with_variation(self, api_test_client: TestClient):
        """Test executing flow with variation settings."""
        mock_checkpoint = create_mock_checkpoint()
        mock_flow = create_mock_flow(
            flow_id="test-flow",
            status=FlowStatus.READY,
            checkpoints=[mock_checkpoint],
        )

        mock_storage = MagicMock()
        mock_storage.load = AsyncMock(return_value=mock_flow)

        mock_executor = MagicMock()
        mock_result = FlowExecutionResult(
            flow_id="test-flow",
            total_checkpoints=1,
            browser_engine="patchright",
        )
        mock_executor.execute = AsyncMock(return_value=mock_result)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            with patch(
                "ghoststorm.api.routes.flows.get_flow_executor", return_value=mock_executor
            ):
                response = api_test_client.post(
                    "/api/flows/test-flow/execute",
                    json={
                        "browser_engine": "patchright",
                        "variation_level": "high",
                        "workers": 3,
                        "use_proxy": True,
                        "checkpoint_timeout": 120.0,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "started"
                assert data["workers"] == 3

    def test_execute_with_proxy(self, api_test_client: TestClient):
        """Test executing flow with proxy rotation."""
        mock_checkpoint = create_mock_checkpoint()
        mock_flow = create_mock_flow(
            flow_id="test-flow",
            status=FlowStatus.READY,
            checkpoints=[mock_checkpoint],
        )

        mock_storage = MagicMock()
        mock_storage.load = AsyncMock(return_value=mock_flow)

        mock_executor = MagicMock()
        mock_result = FlowExecutionResult(
            flow_id="test-flow",
            total_checkpoints=1,
            browser_engine="camoufox",
        )
        mock_executor.execute = AsyncMock(return_value=mock_result)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_storage", return_value=mock_storage
        ):
            with patch(
                "ghoststorm.api.routes.flows.get_flow_executor", return_value=mock_executor
            ):
                response = api_test_client.post(
                    "/api/flows/test-flow/execute",
                    json={
                        "browser_engine": "camoufox",
                        "variation_level": "medium",
                        "workers": 1,
                        "use_proxy": True,
                        "proxy_pool": "rotating",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "started"

    def test_execution_status(self, api_test_client: TestClient):
        """Test getting flow execution status."""
        mock_result = FlowExecutionResult(
            flow_id="test-flow",
            total_checkpoints=5,
            browser_engine="patchright",
        )
        mock_result.checkpoints_completed = 3
        mock_result.success = False

        mock_executor = MagicMock()
        mock_executor.get_execution_status.return_value = mock_result

        with patch(
            "ghoststorm.api.routes.flows.get_flow_executor", return_value=mock_executor
        ):
            # Note: The route expects the execution to be tracked
            # We need to add it to _active_executions
            with patch(
                "ghoststorm.api.routes.flows._active_executions",
                {mock_result.execution_id: mock_result},
            ):
                response = api_test_client.get(
                    f"/api/flows/executions/{mock_result.execution_id}"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["checkpoints_completed"] == 3
                assert data["total_checkpoints"] == 5

    def test_cancel_execution(self, api_test_client: TestClient):
        """Test cancelling a flow execution."""
        mock_executor = MagicMock()
        mock_executor.cancel_execution = AsyncMock(return_value=True)

        with patch(
            "ghoststorm.api.routes.flows.get_flow_executor", return_value=mock_executor
        ):
            response = api_test_client.post("/api/flows/executions/exec-123/cancel")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cancelled"
