"""E2E tests for Health/Watchdog API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestHealthAPI:
    """Tests for /api/health endpoints."""

    def test_get_health(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting overall system health."""
        response = api_test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "level" in data

    def test_health_levels(self, api_test_client: TestClient, mock_orchestrator):
        """Test health level values."""
        response = api_test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        # Level should be one of known values
        assert data["level"] in ["healthy", "degraded", "unhealthy", "critical", "unknown"]

    def test_health_without_orchestrator(self, api_test_client: TestClient):
        """Test health when orchestrator not initialized."""
        with patch(
            "ghoststorm.api.routes.health._get_orchestrator",
            side_effect=RuntimeError("Not initialized"),
        ):
            response = api_test_client.get("/api/health")

            assert response.status_code == 200
            data = response.json()
            assert data["level"] == "unknown"


@pytest.mark.e2e
@pytest.mark.api
class TestWatchdogsAPI:
    """Tests for /api/health/watchdogs endpoints."""

    def test_get_watchdog_status(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting all watchdog statuses."""
        response = api_test_client.get("/api/health/watchdogs")

        assert response.status_code == 200
        data = response.json()
        assert "watchdogs" in data
        assert "count" in data

    def test_watchdog_count(self, api_test_client: TestClient, mock_orchestrator):
        """Test watchdog count matches."""
        response = api_test_client.get("/api/health/watchdogs")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == len(data["watchdogs"])

    def test_get_specific_watchdog(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting a specific watchdog."""
        # First get list of watchdogs
        list_response = api_test_client.get("/api/health/watchdogs")

        if list_response.json()["watchdogs"]:
            watchdog_name = next(iter(list_response.json()["watchdogs"].keys()))

            response = api_test_client.get(f"/api/health/watchdogs/{watchdog_name}")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == watchdog_name

    def test_get_nonexistent_watchdog(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting non-existent watchdog."""
        with patch("ghoststorm.api.routes.health._get_orchestrator") as mock_get:
            mock_get.return_value = mock_orchestrator
            mock_orchestrator.watchdog_manager.get = MagicMock(return_value=None)

            response = api_test_client.get("/api/health/watchdogs/NonExistentWatchdog")

            assert response.status_code == 404

    def test_watchdogs_without_orchestrator(self, api_test_client: TestClient):
        """Test watchdogs when orchestrator not initialized."""
        with patch("ghoststorm.api.routes.health._get_orchestrator", side_effect=RuntimeError()):
            response = api_test_client.get("/api/health/watchdogs")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
            assert "error" in data


@pytest.mark.e2e
@pytest.mark.api
class TestWatchdogStatsAPI:
    """Tests for /api/health/stats endpoint."""

    def test_get_stats(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting watchdog stats."""
        response = api_test_client.get("/api/health/stats")

        assert response.status_code == 200
        data = response.json()
        # Should have stats or error
        assert "running" in data or "error" in data

    def test_stats_without_orchestrator(self, api_test_client: TestClient):
        """Test stats when orchestrator not initialized."""
        with patch("ghoststorm.api.routes.health._get_orchestrator", side_effect=RuntimeError()):
            response = api_test_client.get("/api/health/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["running"] is False


@pytest.mark.e2e
@pytest.mark.api
class TestHealthCheckAPI:
    """Tests for /api/health/check endpoint."""

    def test_trigger_health_check(self, api_test_client: TestClient, mock_orchestrator):
        """Test triggering a health check."""
        response = api_test_client.post("/api/health/check")

        assert response.status_code == 200
        data = response.json()
        assert "triggered" in data

    def test_health_check_result(self, api_test_client: TestClient, mock_orchestrator):
        """Test health check returns result."""
        response = api_test_client.post("/api/health/check")

        assert response.status_code == 200
        data = response.json()
        if data["triggered"]:
            assert "result" in data

    def test_health_check_without_orchestrator(self, api_test_client: TestClient):
        """Test health check when orchestrator not initialized."""
        with patch("ghoststorm.api.routes.health._get_orchestrator", side_effect=RuntimeError()):
            response = api_test_client.post("/api/health/check")

            assert response.status_code == 200
            data = response.json()
            assert data["triggered"] is False
