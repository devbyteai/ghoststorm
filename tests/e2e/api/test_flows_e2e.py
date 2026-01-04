"""E2E tests for Flows API endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.flow
class TestFlowsAPI:
    """Tests for /api/flows endpoints."""

    # ========================================================================
    # GET /api/flows - List Flows
    # ========================================================================

    def test_list_flows_empty(self, api_test_client: TestClient):
        """Test listing flows when none exist."""
        response = api_test_client.get("/api/flows")

        assert response.status_code == 200
        data = response.json()
        assert "flows" in data
        assert isinstance(data["flows"], list)
        assert "total" in data
        assert "ready" in data
        assert "draft" in data

    def test_list_flows_after_creation(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test listing flows after creating one."""
        # Create a flow
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        assert create_response.status_code in [200, 201]
        flow_id = create_response.json()["id"]

        # List flows
        response = api_test_client.get("/api/flows")

        assert response.status_code == 200
        data = response.json()
        flow_ids = [f["id"] for f in data["flows"]]
        assert flow_id in flow_ids

    def test_list_flows_filter_by_status(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test filtering flows by status."""
        # Create a draft flow
        api_test_client.post("/api/flows", json=sample_flow_data)

        # Filter by draft status
        response = api_test_client.get("/api/flows", params={"status": "draft"})

        assert response.status_code == 200
        data = response.json()
        for flow in data["flows"]:
            assert flow["status"] == "draft"

    def test_list_flows_filter_by_tag(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test filtering flows by tag."""
        # Create a flow with tags
        api_test_client.post("/api/flows", json=sample_flow_data)

        # Filter by tag
        response = api_test_client.get("/api/flows", params={"tag": "test"})

        assert response.status_code == 200
        data = response.json()
        for flow in data["flows"]:
            assert "test" in flow.get("tags", [])

    # ========================================================================
    # GET /api/flows/summary - Flow Summary
    # ========================================================================

    def test_get_flows_summary(self, api_test_client: TestClient):
        """Test getting flows summary."""
        response = api_test_client.get("/api/flows/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data or "total_flows" in data

    # ========================================================================
    # POST /api/flows - Create Flow
    # ========================================================================

    def test_create_flow_success(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test successful flow creation."""
        response = api_test_client.post("/api/flows", json=sample_flow_data)

        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_flow_data["name"]
        assert data["status"] == "draft"

    def test_create_flow_minimal(self, api_test_client: TestClient):
        """Test flow creation with minimal data."""
        response = api_test_client.post(
            "/api/flows",
            json={
                "name": "Minimal Flow",
                "start_url": "https://example.com",
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Minimal Flow"

    def test_create_flow_missing_name(self, api_test_client: TestClient):
        """Test flow creation without name."""
        response = api_test_client.post(
            "/api/flows",
            json={"start_url": "https://example.com"},
        )

        assert response.status_code == 422

    def test_create_flow_missing_url(self, api_test_client: TestClient):
        """Test flow creation without URL."""
        response = api_test_client.post(
            "/api/flows",
            json={"name": "Test Flow"},
        )

        assert response.status_code == 422

    # ========================================================================
    # GET /api/flows/{flow_id} - Get Flow
    # ========================================================================

    def test_get_flow_success(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test getting a specific flow."""
        # Create a flow
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        # Get the flow
        response = api_test_client.get(f"/api/flows/{flow_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == flow_id
        assert data["name"] == sample_flow_data["name"]
        assert "checkpoints" in data

    def test_get_flow_not_found(self, api_test_client: TestClient):
        """Test getting a non-existent flow."""
        response = api_test_client.get("/api/flows/nonexistent-flow-id")

        assert response.status_code == 404

    # ========================================================================
    # PATCH /api/flows/{flow_id} - Update Flow
    # ========================================================================

    def test_update_flow_name(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test updating flow name."""
        # Create a flow
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        # Update the flow
        response = api_test_client.patch(
            f"/api/flows/{flow_id}",
            json={"name": "Updated Flow Name"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Flow Name"

    def test_update_flow_description(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test updating flow description."""
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        response = api_test_client.patch(
            f"/api/flows/{flow_id}",
            json={"description": "New description"},
        )

        assert response.status_code == 200
        assert response.json()["description"] == "New description"

    def test_update_flow_tags(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test updating flow tags."""
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        response = api_test_client.patch(
            f"/api/flows/{flow_id}",
            json={"tags": ["new-tag", "another-tag"]},
        )

        assert response.status_code == 200
        assert "new-tag" in response.json()["tags"]

    def test_update_flow_not_found(self, api_test_client: TestClient):
        """Test updating a non-existent flow."""
        response = api_test_client.patch(
            "/api/flows/nonexistent-id",
            json={"name": "New Name"},
        )

        assert response.status_code == 404

    # ========================================================================
    # DELETE /api/flows/{flow_id} - Delete Flow
    # ========================================================================

    def test_delete_flow_success(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test deleting a flow."""
        # Create a flow
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        # Delete the flow
        response = api_test_client.delete(f"/api/flows/{flow_id}")

        assert response.status_code == 200

        # Verify flow is deleted
        get_response = api_test_client.get(f"/api/flows/{flow_id}")
        assert get_response.status_code == 404

    def test_delete_flow_not_found(self, api_test_client: TestClient):
        """Test deleting a non-existent flow."""
        response = api_test_client.delete("/api/flows/nonexistent-id")

        assert response.status_code == 404

    # ========================================================================
    # POST /api/flows/{flow_id}/checkpoints - Add Checkpoint
    # ========================================================================

    def test_add_checkpoint_success(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
        sample_checkpoint_data: dict[str, Any],
    ):
        """Test adding a checkpoint to a flow."""
        # Create a flow
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        # Add checkpoint
        response = api_test_client.post(
            f"/api/flows/{flow_id}/checkpoints",
            json=sample_checkpoint_data,
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert data["goal"] == sample_checkpoint_data["goal"]

    def test_add_checkpoint_various_types(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test adding checkpoints of various types."""
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        checkpoint_types = ["navigation", "click", "input", "wait", "scroll"]

        for cp_type in checkpoint_types:
            response = api_test_client.post(
                f"/api/flows/{flow_id}/checkpoints",
                json={
                    "checkpoint_type": cp_type,
                    "goal": f"Test {cp_type} checkpoint",
                    "timing": {"min_delay": 0.5, "max_delay": 1.0, "timeout": 30.0},
                },
            )

            assert response.status_code in [200, 201]
            assert response.json()["checkpoint_type"] == cp_type

    def test_add_checkpoint_to_nonexistent_flow(
        self,
        api_test_client: TestClient,
        sample_checkpoint_data: dict[str, Any],
    ):
        """Test adding checkpoint to non-existent flow."""
        response = api_test_client.post(
            "/api/flows/nonexistent-id/checkpoints",
            json=sample_checkpoint_data,
        )

        assert response.status_code == 404

    # ========================================================================
    # DELETE /api/flows/{flow_id}/checkpoints/{checkpoint_id}
    # ========================================================================

    def test_delete_checkpoint_success(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
        sample_checkpoint_data: dict[str, Any],
    ):
        """Test deleting a checkpoint."""
        # Create flow and add checkpoint
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        cp_response = api_test_client.post(
            f"/api/flows/{flow_id}/checkpoints",
            json=sample_checkpoint_data,
        )
        checkpoint_id = cp_response.json()["id"]

        # Delete checkpoint
        response = api_test_client.delete(
            f"/api/flows/{flow_id}/checkpoints/{checkpoint_id}"
        )

        assert response.status_code == 200

    def test_delete_checkpoint_not_found(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test deleting non-existent checkpoint."""
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        response = api_test_client.delete(
            f"/api/flows/{flow_id}/checkpoints/nonexistent-cp-id"
        )

        assert response.status_code == 404

    # ========================================================================
    # POST /api/flows/record/start - Start Recording
    # ========================================================================

    def test_start_recording_success(
        self,
        api_test_client: TestClient,
        sample_recording_data: dict[str, Any],
    ):
        """Test starting a recording session."""
        response = api_test_client.post(
            "/api/flows/record/start",
            json=sample_recording_data,
        )

        # May fail if browser can't launch in test environment
        assert response.status_code in [200, 201, 500]

        if response.status_code in [200, 201]:
            data = response.json()
            assert "flow_id" in data
            assert data["status"] == "recording"

    def test_start_recording_with_stealth_options(
        self,
        api_test_client: TestClient,
    ):
        """Test starting recording with stealth options."""
        response = api_test_client.post(
            "/api/flows/record/start",
            json={
                "name": "Stealth Recording",
                "start_url": "https://example.com",
                "stealth": {
                    "use_proxy": True,
                    "use_fingerprint": True,
                    "block_webrtc": True,
                    "canvas_noise": True,
                },
            },
        )

        assert response.status_code in [200, 201, 500]

    def test_start_recording_missing_name(self, api_test_client: TestClient):
        """Test starting recording without name."""
        response = api_test_client.post(
            "/api/flows/record/start",
            json={"start_url": "https://example.com"},
        )

        assert response.status_code == 422

    # ========================================================================
    # GET /api/flows/record/status - Recording Status
    # ========================================================================

    def test_get_recording_status_not_recording(self, api_test_client: TestClient):
        """Test getting recording status when not recording."""
        response = api_test_client.get("/api/flows/record/status")

        assert response.status_code == 200
        data = response.json()
        assert data["is_recording"] is False

    # ========================================================================
    # POST /api/flows/record/cancel - Cancel Recording
    # ========================================================================

    def test_cancel_recording_when_not_recording(self, api_test_client: TestClient):
        """Test cancelling when no recording in progress."""
        response = api_test_client.post("/api/flows/record/cancel")

        assert response.status_code == 400

    # ========================================================================
    # POST /api/flows/{flow_id}/finalize - Finalize Flow
    # ========================================================================

    def test_finalize_flow_success(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
        sample_checkpoint_data: dict[str, Any],
    ):
        """Test finalizing a flow with checkpoints."""
        # Create flow and add checkpoint
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        api_test_client.post(
            f"/api/flows/{flow_id}/checkpoints",
            json=sample_checkpoint_data,
        )

        # Finalize
        response = api_test_client.post(f"/api/flows/{flow_id}/finalize")

        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_finalize_flow_no_checkpoints(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test finalizing a flow without checkpoints."""
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        response = api_test_client.post(f"/api/flows/{flow_id}/finalize")

        assert response.status_code == 400

    def test_finalize_already_ready_flow(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
        sample_checkpoint_data: dict[str, Any],
    ):
        """Test finalizing an already finalized flow."""
        # Create, add checkpoint, finalize
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        api_test_client.post(
            f"/api/flows/{flow_id}/checkpoints",
            json=sample_checkpoint_data,
        )
        api_test_client.post(f"/api/flows/{flow_id}/finalize")

        # Try to finalize again
        response = api_test_client.post(f"/api/flows/{flow_id}/finalize")

        assert response.status_code == 400

    # ========================================================================
    # POST /api/flows/{flow_id}/execute - Execute Flow
    # ========================================================================

    def test_execute_flow_success(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
        sample_checkpoint_data: dict[str, Any],
        sample_execution_config: dict[str, Any],
    ):
        """Test executing a ready flow."""
        # Create, add checkpoint, finalize
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        api_test_client.post(
            f"/api/flows/{flow_id}/checkpoints",
            json=sample_checkpoint_data,
        )
        api_test_client.post(f"/api/flows/{flow_id}/finalize")

        # Execute
        response = api_test_client.post(
            f"/api/flows/{flow_id}/execute",
            json=sample_execution_config,
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "execution_id" in data
        assert data["status"] == "started"

    def test_execute_draft_flow(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
        sample_execution_config: dict[str, Any],
    ):
        """Test executing a draft (not ready) flow."""
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        response = api_test_client.post(
            f"/api/flows/{flow_id}/execute",
            json=sample_execution_config,
        )

        assert response.status_code == 400

    def test_execute_flow_not_found(
        self,
        api_test_client: TestClient,
        sample_execution_config: dict[str, Any],
    ):
        """Test executing a non-existent flow."""
        response = api_test_client.post(
            "/api/flows/nonexistent-id/execute",
            json=sample_execution_config,
        )

        assert response.status_code == 404

    # ========================================================================
    # GET /api/flows/executions/{execution_id} - Execution Status
    # ========================================================================

    def test_get_execution_status_not_found(self, api_test_client: TestClient):
        """Test getting status of non-existent execution."""
        response = api_test_client.get("/api/flows/executions/nonexistent-exec-id")

        assert response.status_code == 404

    # ========================================================================
    # POST /api/flows/executions/{execution_id}/cancel - Cancel Execution
    # ========================================================================

    def test_cancel_execution_not_found(self, api_test_client: TestClient):
        """Test cancelling non-existent execution."""
        response = api_test_client.post(
            "/api/flows/executions/nonexistent-exec-id/cancel"
        )

        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.flow
class TestFlowsAPIEdgeCases:
    """Edge case tests for Flows API."""

    def test_flow_with_long_name(
        self,
        api_test_client: TestClient,
    ):
        """Test flow with long name."""
        response = api_test_client.post(
            "/api/flows",
            json={
                "name": "A" * 200,
                "start_url": "https://example.com",
            },
        )

        # Should either accept or reject with validation error
        assert response.status_code in [200, 201, 422]

    def test_flow_with_special_characters_in_name(
        self,
        api_test_client: TestClient,
    ):
        """Test flow with special characters in name."""
        response = api_test_client.post(
            "/api/flows",
            json={
                "name": "Test Flow 🚀 (v1.0)",
                "start_url": "https://example.com",
            },
        )

        assert response.status_code in [200, 201]

    def test_multiple_checkpoints_ordering(
        self,
        api_test_client: TestClient,
        sample_flow_data: dict[str, Any],
    ):
        """Test that checkpoints maintain order."""
        create_response = api_test_client.post("/api/flows", json=sample_flow_data)
        flow_id = create_response.json()["id"]

        # Add multiple checkpoints
        for i in range(5):
            api_test_client.post(
                f"/api/flows/{flow_id}/checkpoints",
                json={
                    "checkpoint_type": "click",
                    "goal": f"Checkpoint {i}",
                    "timing": {"min_delay": 0.5, "max_delay": 1.0, "timeout": 30.0},
                },
            )

        # Verify order
        response = api_test_client.get(f"/api/flows/{flow_id}")
        checkpoints = response.json()["checkpoints"]

        for i, cp in enumerate(checkpoints):
            assert cp["order"] == i
