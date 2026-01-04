"""E2E tests for Zefoy API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestZefoyStatsAPI:
    """Tests for /api/zefoy/stats endpoint."""

    def test_get_stats(self, api_test_client: TestClient):
        """Test getting Zefoy statistics."""
        response = api_test_client.get("/api/zefoy/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "successful" in data
        assert "failed" in data
        assert "running" in data

    def test_stats_non_negative(self, api_test_client: TestClient):
        """Test stats values are non-negative."""
        response = api_test_client.get("/api/zefoy/stats")

        assert response.status_code == 200
        data = response.json()

        for key in ["total", "successful", "failed", "running"]:
            assert data[key] >= 0, f"{key} should be non-negative"


@pytest.mark.e2e
@pytest.mark.api
class TestZefoyJobsAPI:
    """Tests for /api/zefoy/jobs endpoints."""

    def test_list_jobs(self, api_test_client: TestClient):
        """Test listing all Zefoy jobs."""
        response = api_test_client.get("/api/zefoy/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_get_nonexistent_job(self, api_test_client: TestClient):
        """Test getting non-existent job."""
        response = api_test_client.get("/api/zefoy/jobs/nonexistent")

        assert response.status_code == 404

    def test_cancel_nonexistent_job(self, api_test_client: TestClient):
        """Test cancelling non-existent job."""
        response = api_test_client.delete("/api/zefoy/jobs/nonexistent")

        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.api
class TestZefoyStartAPI:
    """Tests for /api/zefoy/start endpoint."""

    def test_start_job_invalid_url(self, api_test_client: TestClient):
        """Test starting job with invalid URL."""
        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            response = api_test_client.post(
                "/api/zefoy/start",
                json={
                    "url": "https://example.com/video",
                    "services": ["views"],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert "Invalid TikTok URL" in data["error"]

    def test_start_job_invalid_service(self, api_test_client: TestClient):
        """Test starting job with invalid service."""
        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            response = api_test_client.post(
                "/api/zefoy/start",
                json={
                    "url": "https://www.tiktok.com/@user/video/123",
                    "services": ["invalid_service"],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert "Invalid services" in data["error"]

    def test_start_job_success(self, api_test_client: TestClient):
        """Test starting job successfully."""
        with patch(
            "ghoststorm.api.routes.zefoy.ZEFOY_SERVICES",
            {"views": ".btn-views", "likes": ".btn-likes"},
        ):
            with patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock):
                with patch("asyncio.create_task"):
                    response = api_test_client.post(
                        "/api/zefoy/start",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "services": ["views"],
                            "repeat": 1,
                            "delay": 60,
                            "workers": 1,
                            "use_proxy": True,
                            "headless": True,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "job_id" in data
                    assert data["status"] == "running"
                    assert data["url"] == "https://www.tiktok.com/@user/video/123"

    def test_start_job_multiple_services(self, api_test_client: TestClient):
        """Test starting job with multiple services."""
        with (
            patch(
                "ghoststorm.api.routes.zefoy.ZEFOY_SERVICES",
                {
                    "views": ".btn-views",
                    "likes": ".btn-likes",
                    "shares": ".btn-shares",
                },
            ),
            patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock),
        ):
            with patch("asyncio.create_task"):
                response = api_test_client.post(
                    "/api/zefoy/start",
                    json={
                        "url": "https://www.tiktok.com/@user/video/123",
                        "services": ["views", "likes"],
                        "repeat": 2,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["services"] == ["views", "likes"]
                assert data["total_runs"] == 4  # 2 services * 2 repeats

    def test_start_job_config_stored(self, api_test_client: TestClient):
        """Test job config is stored correctly."""
        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            with patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock):
                with patch("asyncio.create_task"):
                    response = api_test_client.post(
                        "/api/zefoy/start",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "services": ["views"],
                            "repeat": 5,
                            "delay": 120,
                            "workers": 3,
                            "use_proxy": False,
                            "headless": False,
                            "rotate_proxy": False,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    config = data["config"]
                    assert config["repeat"] == 5
                    assert config["delay"] == 120
                    assert config["workers"] == 3
                    assert config["use_proxy"] is False
                    assert config["headless"] is False
                    assert config["rotate_proxy"] is False


@pytest.mark.e2e
@pytest.mark.api
class TestZefoyServicesAPI:
    """Tests for /api/zefoy/services endpoints."""

    def test_get_services(self, api_test_client: TestClient):
        """Test getting available Zefoy services."""
        with patch(
            "ghoststorm.api.routes.zefoy.ZEFOY_SERVICES",
            {
                "views": ".btn-views",
                "likes": ".btn-likes",
                "shares": ".btn-shares",
                "favorites": ".btn-favorites",
            },
        ):
            response = api_test_client.get("/api/zefoy/services")

            assert response.status_code == 200
            data = response.json()
            assert "services" in data
            assert "selectors" in data
            assert "views" in data["services"]
            assert "likes" in data["services"]

    def test_get_services_status(self, api_test_client: TestClient):
        """Test getting Zefoy services status."""
        response = api_test_client.get("/api/zefoy/services/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "last_check" in data
        assert "checking" in data

    def test_check_services_already_checking(self, api_test_client: TestClient):
        """Test check when already checking."""
        with patch(
            "ghoststorm.api.routes.zefoy._service_status_cache",
            {
                "status": {},
                "last_check": None,
                "checking": True,
            },
        ):
            response = api_test_client.post("/api/zefoy/services/check")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert "already in progress" in data["error"]

    def test_check_services_success(self, api_test_client: TestClient):
        """Test checking services successfully."""
        with (
            patch(
                "ghoststorm.api.routes.zefoy._service_status_cache",
                {
                    "status": {},
                    "last_check": None,
                    "checking": False,
                },
            ),
            patch("ghoststorm.api.routes.zefoy.check_zefoy_services") as mock_check,
        ):
            mock_check.return_value = {
                "views": "available",
                "likes": "cooldown",
                "shares": "offline",
            }

            response = api_test_client.post("/api/zefoy/services/check")

            assert response.status_code == 200
            data = response.json()
            if "status" in data:
                assert "views" in data["status"]

    def test_check_services_error(self, api_test_client: TestClient):
        """Test check services handles errors."""
        with (
            patch(
                "ghoststorm.api.routes.zefoy._service_status_cache",
                {
                    "status": {},
                    "last_check": None,
                    "checking": False,
                },
            ),
            patch("ghoststorm.api.routes.zefoy.check_zefoy_services") as mock_check,
        ):
            mock_check.side_effect = Exception("Network error")

            response = api_test_client.post("/api/zefoy/services/check")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data


@pytest.mark.e2e
@pytest.mark.api
class TestZefoyJobLifecycle:
    """Tests for Zefoy job lifecycle."""

    def test_create_and_get_job(self, api_test_client: TestClient):
        """Test creating and retrieving a job."""
        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            with patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock):
                with patch("asyncio.create_task"):
                    # Create job
                    create_resp = api_test_client.post(
                        "/api/zefoy/start",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "services": ["views"],
                        },
                    )

                    assert create_resp.status_code == 200
                    job_id = create_resp.json()["job_id"]

                    # Get job
                    get_resp = api_test_client.get(f"/api/zefoy/jobs/{job_id}")
                    assert get_resp.status_code == 200
                    assert get_resp.json()["job_id"] == job_id

    def test_create_and_cancel_job(self, api_test_client: TestClient):
        """Test creating and cancelling a job."""
        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            with patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock):
                with patch("asyncio.create_task"):
                    # Create job
                    create_resp = api_test_client.post(
                        "/api/zefoy/start",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "services": ["views"],
                        },
                    )

                    job_id = create_resp.json()["job_id"]

                    # Cancel job
                    cancel_resp = api_test_client.delete(f"/api/zefoy/jobs/{job_id}")
                    assert cancel_resp.status_code == 200
                    assert cancel_resp.json()["status"] == "cancelled"

                    # Verify cancelled
                    get_resp = api_test_client.get(f"/api/zefoy/jobs/{job_id}")
                    assert get_resp.json()["status"] == "cancelled"

    def test_job_appears_in_list(self, api_test_client: TestClient):
        """Test created job appears in job list."""
        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            with patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock):
                with patch("asyncio.create_task"):
                    # Create job
                    create_resp = api_test_client.post(
                        "/api/zefoy/start",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "services": ["views"],
                        },
                    )

                    job_id = create_resp.json()["job_id"]

                    # List jobs
                    list_resp = api_test_client.get("/api/zefoy/jobs")
                    jobs = list_resp.json()["jobs"]
                    job_ids = [j["job_id"] for j in jobs]
                    assert job_id in job_ids


@pytest.mark.e2e
@pytest.mark.api
class TestZefoyJobStructure:
    """Tests for Zefoy job data structure."""

    def test_job_has_required_fields(self, api_test_client: TestClient):
        """Test job response has all required fields."""
        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            with patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock):
                with patch("asyncio.create_task"):
                    response = api_test_client.post(
                        "/api/zefoy/start",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "services": ["views"],
                        },
                    )

                    data = response.json()

                    # Required fields
                    assert "job_id" in data
                    assert "status" in data
                    assert "url" in data
                    assert "services" in data
                    assert "total_runs" in data
                    assert "current_run" in data
                    assert "successful_runs" in data
                    assert "failed_runs" in data
                    assert "captchas_solved" in data
                    assert "current_service" in data
                    assert "config" in data
                    assert "created_at" in data
                    assert "logs" in data

    def test_job_initial_values(self, api_test_client: TestClient):
        """Test job has correct initial values."""
        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            with patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock):
                with patch("asyncio.create_task"):
                    response = api_test_client.post(
                        "/api/zefoy/start",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "services": ["views"],
                        },
                    )

                    data = response.json()

                    assert data["status"] == "running"
                    assert data["current_run"] == 0
                    assert data["successful_runs"] == 0
                    assert data["failed_runs"] == 0
                    assert data["captchas_solved"] == 0
                    assert data["current_service"] is None
                    assert data["logs"] == []

    def test_job_config_defaults(self, api_test_client: TestClient):
        """Test job config has defaults when not specified."""
        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            with patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock):
                with patch("asyncio.create_task"):
                    response = api_test_client.post(
                        "/api/zefoy/start",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "services": ["views"],
                            # No other config specified
                        },
                    )

                    config = response.json()["config"]

                    # Check defaults
                    assert config["repeat"] == 1
                    assert config["delay"] == 60
                    assert config["workers"] == 1
                    assert config["use_proxy"] is True
                    assert config["headless"] is True
                    assert config["rotate_proxy"] is True


@pytest.mark.e2e
@pytest.mark.api
class TestZefoyStatsTracking:
    """Tests for Zefoy stats tracking."""

    def test_stats_increment_on_job_start(self, api_test_client: TestClient):
        """Test stats total increments when job starts."""
        # Get initial stats
        initial_resp = api_test_client.get("/api/zefoy/stats")
        initial_total = initial_resp.json()["total"]

        with patch("ghoststorm.api.routes.zefoy.ZEFOY_SERVICES", {"views": ".btn-views"}):
            with patch("ghoststorm.api.routes.zefoy._run_zefoy_job", new_callable=AsyncMock):
                with patch("asyncio.create_task"):
                    api_test_client.post(
                        "/api/zefoy/start",
                        json={
                            "url": "https://www.tiktok.com/@user/video/123",
                            "services": ["views"],
                        },
                    )

        # Check stats increased
        final_resp = api_test_client.get("/api/zefoy/stats")
        assert final_resp.json()["total"] == initial_total + 1
