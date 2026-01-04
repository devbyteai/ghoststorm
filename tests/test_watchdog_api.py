"""Tests for watchdog health API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthAPIEndpoints:
    """Tests for /api/health endpoints."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator with watchdog manager."""
        from ghoststorm.core.watchdog.models import HealthLevel, HealthStatus, WatchdogState

        orchestrator = MagicMock()

        # Mock get_health
        async def mock_get_health():
            return {
                "level": "healthy",
                "message": "All systems operational",
                "details": {},
                "score": 1.0,
            }

        orchestrator.get_health = mock_get_health

        # Mock watchdog_manager
        mock_manager = MagicMock()

        # Mock get_states
        mock_state = WatchdogState(
            name="BrowserWatchdog",
            enabled=True,
            running=True,
            total_events=100,
            failures_detected=5,
        )
        mock_manager.get_states.return_value = {"BrowserWatchdog": mock_state}

        # Mock get
        mock_watchdog = MagicMock()
        mock_watchdog.state = mock_state

        async def mock_check_health():
            return HealthStatus(
                level=HealthLevel.HEALTHY,
                message="Browser running",
            )

        mock_watchdog.check_health = mock_check_health
        mock_manager.get.return_value = mock_watchdog

        # Mock get_stats
        mock_manager.get_stats.return_value = {
            "running": True,
            "watchdog_count": 4,
            "total_events_processed": 500,
        }

        # Mock check_health
        async def manager_check_health():
            return HealthStatus(
                level=HealthLevel.HEALTHY,
                message="All watchdogs healthy",
            )

        mock_manager.check_health = manager_check_health

        orchestrator.watchdog_manager = mock_manager
        return orchestrator

    @pytest.fixture
    def client(self, mock_orchestrator):
        """Create test client with mocked orchestrator."""
        from ghoststorm.api.app import create_app

        with patch(
            "ghoststorm.api.routes.health._get_orchestrator", return_value=mock_orchestrator
        ):
            app = create_app(mock_orchestrator)
            yield TestClient(app)

    def test_get_watchdog_health(self, client):
        """Test GET /api/watchdog endpoint."""
        response = client.get("/api/watchdog")
        assert response.status_code == 200

        data = response.json()
        assert "level" in data
        assert data["level"] == "healthy"

    def test_get_watchdog_status(self, client):
        """Test GET /api/watchdog/watchdogs endpoint."""
        response = client.get("/api/watchdog/watchdogs")
        assert response.status_code == 200

        data = response.json()
        assert "watchdogs" in data
        assert "count" in data
        assert data["count"] >= 0

    def test_get_watchdog_detail(self, client):
        """Test GET /api/watchdog/watchdogs/{name} endpoint."""
        response = client.get("/api/watchdog/watchdogs/BrowserWatchdog")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert data["name"] == "BrowserWatchdog"
        assert "state" in data
        assert "health" in data

    def test_get_watchdog_stats(self, client):
        """Test GET /api/watchdog/stats endpoint."""
        response = client.get("/api/watchdog/stats")
        assert response.status_code == 200

        data = response.json()
        assert "running" in data
        assert data["running"] is True

    def test_trigger_health_check(self, client):
        """Test POST /api/watchdog/check endpoint."""
        response = client.post("/api/watchdog/check")
        assert response.status_code == 200

        data = response.json()
        assert "triggered" in data
        assert "result" in data


class TestHealthAPIWithoutOrchestrator:
    """Test API behavior when orchestrator is not initialized."""

    @pytest.fixture
    def client_no_orchestrator(self):
        """Create test client without orchestrator."""
        from ghoststorm.api.app import create_app

        def raise_runtime_error():
            raise RuntimeError("Orchestrator not initialized")

        with patch(
            "ghoststorm.api.routes.health._get_orchestrator", side_effect=raise_runtime_error
        ):
            app = create_app(None)
            yield TestClient(app)

    def test_get_watchdog_health_no_orchestrator(self, client_no_orchestrator):
        """Test watchdog health endpoint when orchestrator not initialized."""
        response = client_no_orchestrator.get("/api/watchdog")
        assert response.status_code == 200

        data = response.json()
        assert data["level"] == "unknown"

    def test_get_stats_no_orchestrator(self, client_no_orchestrator):
        """Test stats endpoint when orchestrator not initialized."""
        response = client_no_orchestrator.get("/api/watchdog/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["running"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
