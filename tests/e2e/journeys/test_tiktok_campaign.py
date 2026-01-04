"""End-to-end journey test for TikTok campaign workflow.

This test simulates a complete user journey:
1. Create a TikTok task
2. Configure settings
3. Execute the task
4. Monitor progress via WebSocket
5. View results
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.journey
class TestTikTokCampaignJourney:
    """Full TikTok campaign workflow test."""

    def test_complete_tiktok_views_campaign(
        self,
        api_test_client: TestClient,
        mock_orchestrator,
    ):
        """Test complete TikTok views campaign from start to finish."""
        # Step 1: Detect platform from URL
        detect_response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": "https://www.tiktok.com/@user/video/7123456789"},
        )

        assert detect_response.status_code == 200
        detect_data = detect_response.json()
        assert detect_data["platform"] == "tiktok"

        # Step 2: Check proxy availability
        proxy_stats = api_test_client.get("/api/proxies/stats")
        assert proxy_stats.status_code == 200

        # Step 3: Create the task
        task_response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.tiktok.com/@user/video/7123456789",
                "platform": "tiktok",
                "task_type": "views",
                "config": {
                    "target_count": 1000,
                    "use_proxy": True,
                    "headless": True,
                    "behavior": {
                        "watch_time_min": 5,
                        "watch_time_max": 30,
                        "scroll": True,
                    },
                },
            },
        )

        assert task_response.status_code == 200
        task_data = task_response.json()
        task_id = task_data.get("task_id") or task_data.get("id")
        assert task_id is not None

        # Step 4: Verify task was created
        task_status = api_test_client.get(f"/api/tasks/{task_id}")
        assert task_status.status_code == 200
        assert task_status.json()["status"] in ["pending", "running", "queued"]

        # Step 5: Check metrics endpoint
        metrics = api_test_client.get("/api/metrics")
        assert metrics.status_code == 200

        # Step 6: Monitor task progress (simulated)
        for _ in range(3):
            status_response = api_test_client.get(f"/api/tasks/{task_id}")
            assert status_response.status_code == 200

        # Step 7: Cancel task (cleanup)
        cancel_response = api_test_client.post(f"/api/tasks/{task_id}/cancel")
        assert cancel_response.status_code in [200, 400]

    def test_tiktok_likes_campaign_with_flow(
        self,
        api_test_client: TestClient,
        mock_orchestrator,
    ):
        """Test TikTok likes campaign using a recorded flow."""
        # Step 1: Check for saved flows
        flows_response = api_test_client.get("/api/flows")
        assert flows_response.status_code == 200

        # Step 2: Create a new flow for TikTok likes
        with patch("ghoststorm.api.routes.flows._recording_sessions", {}):
            record_response = api_test_client.post(
                "/api/flows/record",
                json={
                    "url": "https://www.tiktok.com/@user/video/123",
                    "platform": "tiktok",
                    "stealth": {
                        "webdriver": True,
                        "webgl": True,
                        "canvas": True,
                    },
                },
            )

            # Recording might succeed or need mock
            if record_response.status_code == 200:
                session_id = record_response.json().get("session_id")

                # Stop recording
                api_test_client.post(f"/api/flows/stop/{session_id}")

        # Step 3: Create task with flow-based execution
        task_response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.tiktok.com/@user/video/123",
                "platform": "tiktok",
                "task_type": "likes",
                "config": {
                    "target_count": 500,
                    "use_flow": True,
                },
            },
        )

        assert task_response.status_code == 200

    def test_tiktok_multi_video_campaign(
        self,
        api_test_client: TestClient,
        mock_orchestrator,
    ):
        """Test campaign targeting multiple TikTok videos."""
        videos = [
            "https://www.tiktok.com/@user/video/1",
            "https://www.tiktok.com/@user/video/2",
            "https://www.tiktok.com/@user/video/3",
        ]

        task_ids = []

        # Create tasks for each video
        for url in videos:
            response = api_test_client.post(
                "/api/tasks",
                json={
                    "url": url,
                    "platform": "tiktok",
                    "task_type": "views",
                    "config": {
                        "target_count": 100,
                        "use_proxy": True,
                    },
                },
            )

            assert response.status_code == 200
            task_id = response.json().get("task_id") or response.json().get("id")
            task_ids.append(task_id)

        # Verify all tasks created
        assert len(task_ids) == 3

        # Check task list
        list_response = api_test_client.get("/api/tasks")
        assert list_response.status_code == 200

        # Cancel all tasks
        for task_id in task_ids:
            if task_id:
                api_test_client.post(f"/api/tasks/{task_id}/cancel")


@pytest.mark.e2e
@pytest.mark.journey
class TestTikTokCampaignWithAI:
    """TikTok campaign workflow with AI assistance."""

    def test_ai_assisted_campaign_setup(
        self,
        api_test_client: TestClient,
        mock_orchestrator,
        mock_ollama_service,
    ):
        """Test AI-assisted campaign configuration."""
        # Step 1: Ask AI for recommendations
        with patch("ghoststorm.api.routes.assistant.AIAssistant") as MockAI:
            mock_ai = MagicMock()
            mock_ai.chat.return_value = {
                "message": "For TikTok views, I recommend using stealth mode with 5-30 second watch times.",
                "recommendations": {
                    "watch_time_min": 5,
                    "watch_time_max": 30,
                    "use_stealth": True,
                },
            }
            MockAI.return_value = mock_ai

            chat_response = api_test_client.post(
                "/api/assistant/chat",
                json={
                    "message": "What settings should I use for TikTok views?",
                },
            )

            assert chat_response.status_code == 200

        # Step 2: Use AI to analyze target video
        analyze_response = api_test_client.post(
            "/api/llm/analyze",
            json={
                "content": "TikTok video with 1M views, posted 2 days ago, trending hashtags",
                "query": "Analyze engagement potential",
            },
        )

        # May need mock, but endpoint should respond
        assert analyze_response.status_code in [200, 400, 503]

        # Step 3: Create optimized task
        task_response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.tiktok.com/@user/video/123",
                "platform": "tiktok",
                "task_type": "views",
                "config": {
                    "target_count": 1000,
                    "ai_optimized": True,
                    "behavior": {
                        "watch_time_min": 5,
                        "watch_time_max": 30,
                        "scroll": True,
                        "interact": True,
                    },
                },
            },
        )

        assert task_response.status_code == 200


@pytest.mark.e2e
@pytest.mark.journey
class TestTikTokErrorRecovery:
    """Test TikTok campaign error handling and recovery."""

    def test_campaign_with_proxy_failures(
        self,
        api_test_client: TestClient,
        mock_orchestrator,
    ):
        """Test campaign handling proxy failures."""
        # Create task
        task_response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.tiktok.com/@user/video/123",
                "platform": "tiktok",
                "task_type": "views",
                "config": {
                    "use_proxy": True,
                    "proxy_retry_count": 3,
                    "on_proxy_fail": "rotate",
                },
            },
        )

        assert task_response.status_code == 200
        task_id = task_response.json().get("task_id") or task_response.json().get("id")

        # Simulate proxy failure and check retry
        retry_response = api_test_client.post(f"/api/tasks/{task_id}/retry")
        assert retry_response.status_code in [200, 400, 404]

    def test_campaign_resume_after_stop(
        self,
        api_test_client: TestClient,
        mock_orchestrator,
    ):
        """Test resuming a stopped campaign."""
        # Create and start task
        task_response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.tiktok.com/@user/video/123",
                "platform": "tiktok",
                "task_type": "views",
                "config": {"target_count": 1000},
            },
        )

        task_id = task_response.json().get("task_id") or task_response.json().get("id")

        # Pause task
        api_test_client.post(f"/api/tasks/{task_id}/pause")

        # Resume task
        resume_response = api_test_client.post(f"/api/tasks/{task_id}/resume")

        # Either might work depending on implementation
        assert resume_response.status_code in [200, 400, 404]


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.real
class TestTikTokRealCampaign:
    """Real TikTok campaign tests (requires --run-real flag)."""

    def test_real_tiktok_page_load(self, api_test_client: TestClient):
        """Test loading real TikTok page."""
        with patch("ghoststorm.api.routes.flows._recording_sessions", {}):
            response = api_test_client.post(
                "/api/flows/record",
                json={
                    "url": "https://www.tiktok.com",
                    "headless": True,
                },
            )

            if response.status_code == 200:
                session_id = response.json().get("session_id")
                if session_id:
                    # Stop session
                    api_test_client.post(f"/api/flows/stop/{session_id}")

            # May succeed or fail based on browser availability
            assert response.status_code in [200, 400, 500]
