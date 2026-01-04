"""E2E tests for Automation Engine API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestEngineStatsAPI:
    """Tests for /api/engine/stats endpoint."""

    def test_get_stats(self, api_test_client: TestClient):
        """Test getting engine statistics."""
        response = api_test_client.get("/api/engine/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "successful" in data
        assert "failed" in data
        assert "running" in data

    def test_stats_initial_values(self, api_test_client: TestClient):
        """Test initial stats values."""
        response = api_test_client.get("/api/engine/stats")

        assert response.status_code == 200
        data = response.json()
        # Values should be non-negative
        assert data["total"] >= 0
        assert data["successful"] >= 0
        assert data["failed"] >= 0
        assert data["running"] >= 0


@pytest.mark.e2e
@pytest.mark.api
class TestEnginePresetsAPI:
    """Tests for /api/engine/presets endpoints."""

    def test_list_presets(self, api_test_client: TestClient):
        """Test listing all presets."""
        response = api_test_client.get("/api/engine/presets")

        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert isinstance(data["presets"], dict)

    def test_list_presets_by_category(self, api_test_client: TestClient):
        """Test filtering presets by category."""
        response = api_test_client.get(
            "/api/engine/presets",
            params={"category": "crypto"},
        )

        assert response.status_code == 200
        data = response.json()
        # All returned presets should be in the category
        for preset in data["presets"].values():
            assert preset.get("category") == "crypto"

    def test_get_preset_categories(self, api_test_client: TestClient):
        """Test getting preset categories."""
        response = api_test_client.get("/api/engine/presets/categories")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)

    def test_get_specific_preset(self, api_test_client: TestClient):
        """Test getting a specific preset."""
        # First list to get an ID
        list_response = api_test_client.get("/api/engine/presets")

        if list_response.json()["presets"]:
            preset_id = next(iter(list_response.json()["presets"].keys()))

            response = api_test_client.get(f"/api/engine/presets/{preset_id}")

            assert response.status_code == 200
            data = response.json()
            assert data.get("id") == preset_id

    def test_get_nonexistent_preset(self, api_test_client: TestClient):
        """Test getting non-existent preset."""
        response = api_test_client.get("/api/engine/presets/nonexistent-preset-id")

        assert response.status_code == 404

    def test_save_custom_preset(self, api_test_client: TestClient):
        """Test saving a custom preset."""
        response = api_test_client.post(
            "/api/engine/presets",
            json={
                "id": "test-custom-preset",
                "name": "Test Custom Preset",
                "description": "A test preset",
                "category": "test",
                "url": "https://example.com",
                "goal_keywords": ["success", "complete"],
                "captcha_selectors": {"iframe": "iframe[src*='captcha']"},
                "actions": [{"type": "wait", "seconds": 2}],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"
        assert data["id"] == "test-custom-preset"

    def test_delete_custom_preset(self, api_test_client: TestClient):
        """Test deleting a custom preset."""
        # First create one
        api_test_client.post(
            "/api/engine/presets",
            json={
                "id": "test-to-delete",
                "name": "To Delete",
                "category": "test",
            },
        )

        response = api_test_client.delete("/api/engine/presets/test-to-delete")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

    def test_delete_builtin_preset_fails(self, api_test_client: TestClient):
        """Test that built-in presets cannot be deleted."""
        # Get a built-in preset
        list_response = api_test_client.get("/api/engine/presets")
        presets = list_response.json()["presets"]

        builtin_id = None
        for pid, preset in presets.items():
            if preset.get("builtin"):
                builtin_id = pid
                break

        if builtin_id:
            response = api_test_client.delete(f"/api/engine/presets/{builtin_id}")
            assert response.status_code == 400

    def test_reload_presets(self, api_test_client: TestClient):
        """Test reloading presets from disk."""
        response = api_test_client.post("/api/engine/presets/reload")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reloaded"
        assert "count" in data


@pytest.mark.e2e
@pytest.mark.api
class TestEngineJobsAPI:
    """Tests for /api/engine/jobs endpoints."""

    def test_list_jobs_empty(self, api_test_client: TestClient):
        """Test listing jobs when none exist."""
        response = api_test_client.get("/api/engine/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_get_nonexistent_job(self, api_test_client: TestClient):
        """Test getting non-existent job."""
        response = api_test_client.get("/api/engine/jobs/nonexistent-id")

        assert response.status_code == 404

    def test_cancel_job(self, api_test_client: TestClient):
        """Test cancelling a job."""
        # First we need a job to cancel
        # Create one via start endpoint
        with patch("ghoststorm.api.routes.engine._run_engine_job"):
            start_response = api_test_client.post(
                "/api/engine/start",
                json={
                    "url": "https://example.com",
                    "name": "Test Job",
                },
            )

            if start_response.status_code == 200:
                job_id = start_response.json()["job_id"]

                response = api_test_client.delete(f"/api/engine/jobs/{job_id}")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "cancelled"

    def test_cancel_nonexistent_job(self, api_test_client: TestClient):
        """Test cancelling non-existent job."""
        response = api_test_client.delete("/api/engine/jobs/nonexistent")

        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.api
class TestEngineTestAPI:
    """Tests for /api/engine/test endpoint."""

    def test_quick_test_mock(self, api_test_client: TestClient):
        """Test quick test with mocked browser."""
        with patch("ghoststorm.api.routes.engine.AutomationEngine") as MockEngine:
            mock_engine = MagicMock()
            mock_engine._init_browser = AsyncMock()
            mock_engine._page = MagicMock()
            mock_engine._page.goto = AsyncMock()
            mock_engine._page.title = AsyncMock(return_value="Test Page")
            mock_engine._page.url = "https://example.com"
            mock_engine._page.inner_text = AsyncMock(return_value="Page content")
            mock_engine._page.screenshot = AsyncMock()
            mock_engine._cleanup = AsyncMock()
            MockEngine.return_value = mock_engine

            response = api_test_client.post(
                "/api/engine/test",
                json={
                    "url": "https://example.com",
                    "headless": True,
                    "screenshot": True,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "title" in data
            assert "url" in data

    def test_quick_test_failure(self, api_test_client: TestClient):
        """Test quick test with browser failure."""
        with patch("ghoststorm.api.routes.engine.AutomationEngine") as MockEngine:
            mock_engine = MagicMock()
            mock_engine._init_browser = AsyncMock(side_effect=Exception("Browser failed"))
            mock_engine._cleanup = AsyncMock()
            MockEngine.return_value = mock_engine

            response = api_test_client.post(
                "/api/engine/test",
                json={
                    "url": "https://example.com",
                    "headless": True,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "error" in data


@pytest.mark.e2e
@pytest.mark.api
class TestEngineAnalyzeAPI:
    """Tests for /api/engine/analyze endpoint."""

    def test_analyze_page_mock(self, api_test_client: TestClient):
        """Test page analysis with mocked components."""
        with patch("ghoststorm.api.routes.engine.AutomationEngine") as MockEngine:
            with patch("ghoststorm.api.routes.engine.PageDetector") as MockDetector:
                mock_engine = MagicMock()
                mock_engine._init_browser = AsyncMock()
                mock_engine._page = MagicMock()
                mock_engine._page.goto = AsyncMock()
                mock_engine._page.title = AsyncMock(return_value="Login Page")
                mock_engine._page.url = "https://example.com/login"
                mock_engine._page.inner_text = AsyncMock(return_value="Login Form")
                mock_engine._page.screenshot = AsyncMock()
                mock_engine._cleanup = AsyncMock()
                MockEngine.return_value = mock_engine

                mock_detection = MagicMock()
                mock_detection.page_type = "login_form"
                mock_detection.confidence = 0.9
                mock_detection.detected_elements = []
                mock_detection.suggested_goal_keywords = ["login", "success"]
                mock_detection.suggested_captcha_selectors = {}
                mock_detection.suggested_actions = [{"type": "click", "selector": "#submit"}]

                mock_detector = MagicMock()
                mock_detector.analyze_page = AsyncMock(return_value=mock_detection)
                MockDetector.return_value = mock_detector

                response = api_test_client.post(
                    "/api/engine/analyze",
                    json={
                        "url": "https://example.com/login",
                        "headless": True,
                        "screenshot": True,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "detection" in data
                assert data["detection"]["page_type"] == "login_form"


@pytest.mark.e2e
@pytest.mark.api
class TestEngineStartAPI:
    """Tests for /api/engine/start endpoint."""

    def test_start_job_success(self, api_test_client: TestClient):
        """Test starting an engine job."""
        with patch("ghoststorm.api.routes.engine.asyncio.create_task"):
            response = api_test_client.post(
                "/api/engine/start",
                json={
                    "url": "https://example.com",
                    "name": "Test Automation",
                    "goal_keywords": ["success", "complete"],
                    "headless": True,
                    "max_iterations": 10,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "started"

    def test_start_job_with_preset(self, api_test_client: TestClient):
        """Test starting job with preset."""
        with patch("ghoststorm.api.routes.engine.asyncio.create_task"):
            response = api_test_client.post(
                "/api/engine/start",
                json={
                    "url": "https://example.com",
                    "preset": "some-preset",  # May or may not exist
                    "headless": True,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data

    def test_start_job_with_actions(self, api_test_client: TestClient):
        """Test starting job with custom actions."""
        with patch("ghoststorm.api.routes.engine.asyncio.create_task"):
            response = api_test_client.post(
                "/api/engine/start",
                json={
                    "url": "https://example.com",
                    "actions": [
                        {"type": "wait", "seconds": 2},
                        {"type": "click", "selector": "#button"},
                    ],
                    "headless": True,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data

    def test_start_job_with_proxy(self, api_test_client: TestClient):
        """Test starting job with proxy."""
        with patch("ghoststorm.api.routes.engine.asyncio.create_task"):
            response = api_test_client.post(
                "/api/engine/start",
                json={
                    "url": "https://example.com",
                    "proxy": "http://proxy.example.com:8080",
                    "headless": True,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data

    def test_start_job_with_captcha(self, api_test_client: TestClient):
        """Test starting job with captcha solving enabled."""
        with patch("ghoststorm.api.routes.engine.asyncio.create_task"):
            response = api_test_client.post(
                "/api/engine/start",
                json={
                    "url": "https://example.com",
                    "solve_captcha": True,
                    "captcha_selectors": {
                        "iframe": "iframe[src*='recaptcha']",
                        "checkbox": ".recaptcha-checkbox",
                    },
                    "headless": True,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data

    def test_start_job_missing_url(self, api_test_client: TestClient):
        """Test starting job without URL."""
        response = api_test_client.post(
            "/api/engine/start",
            json={
                "name": "No URL Job",
            },
        )

        # Should fail validation or return error
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            assert "error" in response.json()


@pytest.mark.e2e
@pytest.mark.api
class TestEngineJobLifecycle:
    """Tests for full job lifecycle."""

    def test_job_creation_and_retrieval(self, api_test_client: TestClient):
        """Test creating and retrieving a job."""
        with patch("ghoststorm.api.routes.engine.asyncio.create_task"):
            # Create job
            start_response = api_test_client.post(
                "/api/engine/start",
                json={
                    "url": "https://example.com",
                    "name": "Lifecycle Test",
                },
            )

            assert start_response.status_code == 200
            job_id = start_response.json()["job_id"]

            # Retrieve job
            get_response = api_test_client.get(f"/api/engine/jobs/{job_id}")

            assert get_response.status_code == 200
            job = get_response.json()
            assert job["job_id"] == job_id
            assert job["url"] == "https://example.com"

    def test_job_appears_in_list(self, api_test_client: TestClient):
        """Test that created job appears in job list."""
        with patch("ghoststorm.api.routes.engine.asyncio.create_task"):
            # Create job
            start_response = api_test_client.post(
                "/api/engine/start",
                json={
                    "url": "https://example.com",
                    "name": "List Test",
                },
            )

            job_id = start_response.json()["job_id"]

            # List jobs
            list_response = api_test_client.get("/api/engine/jobs")

            assert list_response.status_code == 200
            jobs = list_response.json()["jobs"]
            job_ids = [j["job_id"] for j in jobs]
            assert job_id in job_ids

    def test_job_updates_stats(self, api_test_client: TestClient):
        """Test that job creation updates stats."""
        # Get initial stats
        initial_stats = api_test_client.get("/api/engine/stats").json()
        initial_total = initial_stats["total"]

        with patch("ghoststorm.api.routes.engine.asyncio.create_task"):
            # Create job
            api_test_client.post(
                "/api/engine/start",
                json={
                    "url": "https://example.com",
                    "name": "Stats Test",
                },
            )

            # Check stats
            new_stats = api_test_client.get("/api/engine/stats").json()
            assert new_stats["total"] == initial_total + 1


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.real
@pytest.mark.browser
class TestEngineRealBrowser:
    """Real browser tests - require --run-real flag."""

    def test_real_quick_test(self, api_test_client: TestClient):
        """Test quick test with real browser."""
        response = api_test_client.post(
            "/api/engine/test",
            json={
                "url": "https://example.com",
                "headless": True,
                "screenshot": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Example Domain" in data["title"]

    def test_real_page_analysis(self, api_test_client: TestClient):
        """Test page analysis with real browser."""
        response = api_test_client.post(
            "/api/engine/analyze",
            json={
                "url": "https://example.com",
                "headless": True,
                "screenshot": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "detection" in data
