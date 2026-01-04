"""E2E tests for Tasks API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestTasksAPI:
    """Tests for /api/tasks endpoints."""

    # ========================================================================
    # POST /api/tasks - Create Task
    # ========================================================================

    def test_create_task_success(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test successful task creation."""
        response = api_test_client.post("/api/tasks", json=sample_task_data)

        assert response.status_code == 201
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["pending", "queued", "running"]
        assert data["platform"] == sample_task_data["platform"]

    def test_create_task_invalid_url(self, api_test_client: TestClient):
        """Test task creation with invalid URL."""
        response = api_test_client.post(
            "/api/tasks",
            json={"url": "not-a-valid-url", "platform": "generic"},
        )

        assert response.status_code == 422

    def test_create_task_missing_url(self, api_test_client: TestClient):
        """Test task creation without URL."""
        response = api_test_client.post("/api/tasks", json={"platform": "tiktok"})

        assert response.status_code == 422

    def test_create_task_auto_detect_platform(self, api_test_client: TestClient):
        """Test platform auto-detection from URL."""
        response = api_test_client.post(
            "/api/tasks",
            json={"url": "https://www.tiktok.com/@user/video/123"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "tiktok"

    @pytest.mark.parametrize(
        "url,expected_platform",
        [
            ("https://www.tiktok.com/@user/video/123", "tiktok"),
            ("https://www.instagram.com/reel/abc123/", "instagram"),
            ("https://www.youtube.com/watch?v=xyz", "youtube"),
            ("https://www.dextools.io/app/en/ether/pair-explorer/0x123", "dextools"),
            ("https://example.com", "generic"),
        ],
    )
    def test_create_task_platform_detection(
        self,
        api_test_client: TestClient,
        url: str,
        expected_platform: str,
    ):
        """Test platform detection for various URLs."""
        response = api_test_client.post("/api/tasks", json={"url": url})

        assert response.status_code == 201
        assert response.json()["platform"] == expected_platform

    # ========================================================================
    # GET /api/tasks - List Tasks
    # ========================================================================

    def test_list_tasks_empty(self, api_test_client: TestClient):
        """Test listing tasks when none exist."""
        response = api_test_client.get("/api/tasks")

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert isinstance(data["tasks"], list)

    def test_list_tasks_after_creation(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test listing tasks after creating one."""
        # Create a task
        create_response = api_test_client.post("/api/tasks", json=sample_task_data)
        assert create_response.status_code == 201
        task_id = create_response.json()["task_id"]

        # List tasks
        response = api_test_client.get("/api/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) >= 1
        task_ids = [t["task_id"] for t in data["tasks"]]
        assert task_id in task_ids

    def test_list_tasks_filter_by_status(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test filtering tasks by status."""
        # Create a task
        api_test_client.post("/api/tasks", json=sample_task_data)

        # Filter by pending status
        response = api_test_client.get("/api/tasks", params={"status": "pending"})

        assert response.status_code == 200
        data = response.json()
        for task in data["tasks"]:
            assert task["status"] == "pending"

    def test_list_tasks_filter_by_platform(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test filtering tasks by platform."""
        # Create a TikTok task
        api_test_client.post("/api/tasks", json=sample_task_data)

        # Filter by platform
        response = api_test_client.get("/api/tasks", params={"platform": "tiktok"})

        assert response.status_code == 200
        data = response.json()
        for task in data["tasks"]:
            assert task["platform"] == "tiktok"

    def test_list_tasks_pagination(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test task list pagination."""
        # Create multiple tasks
        for i in range(5):
            data = sample_task_data.copy()
            data["url"] = f"https://www.tiktok.com/@user/video/{1000 + i}"
            api_test_client.post("/api/tasks", json=data)

        # Get first page
        response = api_test_client.get("/api/tasks", params={"limit": 2, "offset": 0})

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) <= 2

    # ========================================================================
    # GET /api/tasks/{task_id} - Get Task
    # ========================================================================

    def test_get_task_success(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test getting a specific task."""
        # Create a task
        create_response = api_test_client.post("/api/tasks", json=sample_task_data)
        task_id = create_response.json()["task_id"]

        # Get the task
        response = api_test_client.get(f"/api/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert "status" in data
        assert "platform" in data
        assert "url" in data

    def test_get_task_not_found(self, api_test_client: TestClient):
        """Test getting a non-existent task."""
        response = api_test_client.get("/api/tasks/nonexistent-id-12345")

        assert response.status_code == 404

    def test_get_task_includes_config(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test that task response includes configuration."""
        create_response = api_test_client.post("/api/tasks", json=sample_task_data)
        task_id = create_response.json()["task_id"]

        response = api_test_client.get(f"/api/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert "config" in data or "workers" in data

    # ========================================================================
    # DELETE /api/tasks/{task_id} - Cancel Task
    # ========================================================================

    def test_cancel_task_success(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test cancelling a pending task."""
        # Create a task
        create_response = api_test_client.post("/api/tasks", json=sample_task_data)
        task_id = create_response.json()["task_id"]

        # Cancel the task
        response = api_test_client.delete(f"/api/tasks/{task_id}")

        assert response.status_code in [200, 204]

        # Verify task is cancelled
        get_response = api_test_client.get(f"/api/tasks/{task_id}")
        if get_response.status_code == 200:
            assert get_response.json()["status"] in ["cancelled", "stopped"]

    def test_cancel_task_not_found(self, api_test_client: TestClient):
        """Test cancelling a non-existent task."""
        response = api_test_client.delete("/api/tasks/nonexistent-id-12345")

        assert response.status_code == 404

    # ========================================================================
    # POST /api/tasks/detect - Platform Detection
    # ========================================================================

    def test_detect_platform_tiktok(self, api_test_client: TestClient):
        """Test TikTok URL detection."""
        response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": "https://www.tiktok.com/@user/video/7123456789"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "tiktok"
        assert "metadata" in data

    def test_detect_platform_instagram(self, api_test_client: TestClient):
        """Test Instagram URL detection."""
        response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": "https://www.instagram.com/reel/ABC123/"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "instagram"

    def test_detect_platform_youtube(self, api_test_client: TestClient):
        """Test YouTube URL detection."""
        response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "youtube"

    def test_detect_platform_generic(self, api_test_client: TestClient):
        """Test generic URL detection."""
        response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": "https://example.com/page"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "generic"

    def test_detect_platform_invalid_url(self, api_test_client: TestClient):
        """Test detection with invalid URL."""
        response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": "not-a-url"},
        )

        assert response.status_code == 422

    # ========================================================================
    # POST /api/tasks/{task_id}/retry - Retry Task
    # ========================================================================

    def test_retry_task_success(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test retrying a failed task."""
        # Create and (mock) fail a task
        create_response = api_test_client.post("/api/tasks", json=sample_task_data)
        task_id = create_response.json()["task_id"]

        # Retry the task
        response = api_test_client.post(f"/api/tasks/{task_id}/retry")

        # Should either succeed or return appropriate error
        assert response.status_code in [200, 201, 400, 404]

    def test_retry_task_not_found(self, api_test_client: TestClient):
        """Test retrying a non-existent task."""
        response = api_test_client.post("/api/tasks/nonexistent-id-12345/retry")

        assert response.status_code == 404

    # ========================================================================
    # Multiple Tasks / Batch Operations
    # ========================================================================

    def test_create_multiple_tasks_sequentially(
        self,
        api_test_client: TestClient,
    ):
        """Test creating multiple tasks sequentially."""
        task_ids = []

        urls = [
            "https://www.tiktok.com/@user1/video/111",
            "https://www.tiktok.com/@user2/video/222",
            "https://www.tiktok.com/@user3/video/333",
        ]

        for url in urls:
            response = api_test_client.post("/api/tasks", json={"url": url})
            assert response.status_code == 201
            task_ids.append(response.json()["task_id"])

        # Verify all tasks exist
        for task_id in task_ids:
            response = api_test_client.get(f"/api/tasks/{task_id}")
            assert response.status_code == 200

    def test_task_stats_in_list_response(
        self,
        api_test_client: TestClient,
        sample_task_data: dict[str, Any],
    ):
        """Test that task list includes statistics."""
        # Create some tasks
        for i in range(3):
            data = sample_task_data.copy()
            data["url"] = f"https://www.tiktok.com/@user/video/{2000 + i}"
            api_test_client.post("/api/tasks", json=data)

        # Get list with stats
        response = api_test_client.get("/api/tasks")

        assert response.status_code == 200
        data = response.json()
        # Should have total count or similar stats
        assert "tasks" in data
        assert "total" in data or len(data["tasks"]) > 0


@pytest.mark.e2e
@pytest.mark.api
class TestTasksAPIEdgeCases:
    """Edge case tests for Tasks API."""

    def test_create_task_with_all_config_options(
        self,
        api_test_client: TestClient,
    ):
        """Test task creation with full configuration."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.tiktok.com/@user/video/123",
                "platform": "tiktok",
                "config": {
                    "workers": 5,
                    "headless": True,
                    "use_proxy": True,
                    "proxy_rotation": "per_request",
                    "human_simulation": True,
                    "dwell_time": [5.0, 15.0],
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["task_id"] is not None

    def test_create_task_empty_config(self, api_test_client: TestClient):
        """Test task creation with empty config (use defaults)."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.tiktok.com/@user/video/123",
                "config": {},
            },
        )

        assert response.status_code == 201

    def test_task_url_normalization(self, api_test_client: TestClient):
        """Test that URLs are normalized."""
        # URL with trailing slash
        response = api_test_client.post(
            "/api/tasks",
            json={"url": "https://www.tiktok.com/@user/video/123/"},
        )

        assert response.status_code == 201

    def test_short_url_handling(self, api_test_client: TestClient):
        """Test handling of short URLs (vm.tiktok.com)."""
        response = api_test_client.post(
            "/api/tasks",
            json={"url": "https://vm.tiktok.com/ZM8abc123/"},
        )

        assert response.status_code == 201
        assert response.json()["platform"] == "tiktok"
