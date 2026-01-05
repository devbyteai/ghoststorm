"""E2E tests for Health/Watchdog API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestHealthAPI:
    """Tests for /api/health endpoints (metrics health check)."""

    def test_get_health(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting overall system health."""
        response = api_test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "orchestrator" in data

    def test_health_status_value(self, api_test_client: TestClient, mock_orchestrator):
        """Test health status is valid."""
        response = api_test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_orchestrator_info(self, api_test_client: TestClient, mock_orchestrator):
        """Test health includes orchestrator info."""
        response = api_test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "running" in data["orchestrator"]
        assert "uptime_seconds" in data["orchestrator"]


@pytest.mark.e2e
@pytest.mark.api
class TestWatchdogsAPI:
    """Tests for /api/watchdog/watchdogs endpoints."""

    def test_get_watchdog_status(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting all watchdog statuses."""
        # Mock the watchdog_manager.get_states() method
        mock_orchestrator.watchdog_manager.get_states = MagicMock(return_value={})
        response = api_test_client.get("/api/watchdog/watchdogs")

        assert response.status_code == 200
        data = response.json()
        assert "watchdogs" in data
        assert "count" in data

    def test_watchdog_count(self, api_test_client: TestClient, mock_orchestrator):
        """Test watchdog count matches."""
        mock_orchestrator.watchdog_manager.get_states = MagicMock(return_value={})
        response = api_test_client.get("/api/watchdog/watchdogs")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == len(data["watchdogs"])

    def test_get_specific_watchdog(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting a specific watchdog."""
        # Setup mock watchdog
        mock_watchdog = MagicMock()
        mock_state = MagicMock()
        mock_state.to_dict = MagicMock(return_value={"status": "healthy"})
        mock_watchdog.state = mock_state

        mock_health = MagicMock()
        mock_health.to_dict = MagicMock(return_value={"level": "healthy"})
        mock_watchdog.check_health = AsyncMock(return_value=mock_health)

        mock_orchestrator.watchdog_manager.get = MagicMock(return_value=mock_watchdog)

        response = api_test_client.get("/api/watchdog/watchdogs/TestWatchdog")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TestWatchdog"

    def test_get_nonexistent_watchdog(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting non-existent watchdog."""
        mock_orchestrator.watchdog_manager.get = MagicMock(return_value=None)

        response = api_test_client.get("/api/watchdog/watchdogs/NonExistentWatchdog")

        assert response.status_code == 404

    def test_watchdogs_without_orchestrator(self, api_test_client: TestClient):
        """Test watchdogs when orchestrator not initialized."""
        with patch("ghoststorm.api.routes.health._get_orchestrator", side_effect=RuntimeError()):
            response = api_test_client.get("/api/watchdog/watchdogs")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
            assert "error" in data


@pytest.mark.e2e
@pytest.mark.api
class TestWatchdogStatsAPI:
    """Tests for /api/watchdog/stats endpoint."""

    def test_get_stats(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting watchdog stats."""
        mock_orchestrator.watchdog_manager.get_stats = MagicMock(
            return_value={"running": True, "total": 0}
        )
        response = api_test_client.get("/api/watchdog/stats")

        assert response.status_code == 200
        data = response.json()
        # Should have stats or error
        assert "running" in data or "error" in data

    def test_stats_without_orchestrator(self, api_test_client: TestClient):
        """Test stats when orchestrator not initialized."""
        with patch("ghoststorm.api.routes.health._get_orchestrator", side_effect=RuntimeError()):
            response = api_test_client.get("/api/watchdog/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["running"] is False


@pytest.mark.e2e
@pytest.mark.api
class TestHealthCheckAPI:
    """Tests for /api/watchdog/check endpoint."""

    def test_trigger_health_check(self, api_test_client: TestClient, mock_orchestrator):
        """Test triggering a health check."""
        mock_health = MagicMock()
        mock_health.to_dict = MagicMock(return_value={"level": "healthy"})
        mock_orchestrator.watchdog_manager.check_health = AsyncMock(return_value=mock_health)

        response = api_test_client.post("/api/watchdog/check")

        assert response.status_code == 200
        data = response.json()
        assert "triggered" in data

    def test_health_check_result(self, api_test_client: TestClient, mock_orchestrator):
        """Test health check returns result."""
        mock_health = MagicMock()
        mock_health.to_dict = MagicMock(return_value={"level": "healthy"})
        mock_orchestrator.watchdog_manager.check_health = AsyncMock(return_value=mock_health)

        response = api_test_client.post("/api/watchdog/check")

        assert response.status_code == 200
        data = response.json()
        if data["triggered"]:
            assert "result" in data

    def test_health_check_without_orchestrator(self, api_test_client: TestClient):
        """Test health check when orchestrator not initialized."""
        with patch("ghoststorm.api.routes.health._get_orchestrator", side_effect=RuntimeError()):
            response = api_test_client.post("/api/watchdog/check")

            assert response.status_code == 200
            data = response.json()
            assert data["triggered"] is False
