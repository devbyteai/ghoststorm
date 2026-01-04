"""E2E tests for Metrics API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestMetricsAPI:
    """Tests for /api/metrics endpoint."""

    def test_get_metrics(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting dashboard metrics."""
        response = api_test_client.get("/api/metrics")

        assert response.status_code == 200
        data = response.json()

        # Should have all metric fields
        assert "timestamp" in data
        assert "tasks_pending" in data
        assert "tasks_running" in data
        assert "tasks_completed" in data
        assert "tasks_failed" in data
        assert "proxies_total" in data
        assert "proxies_healthy" in data
        assert "proxies_failed" in data
        assert "workers_active" in data
        assert "workers_total" in data

    def test_metrics_non_negative(self, api_test_client: TestClient, mock_orchestrator):
        """Test metrics values are non-negative."""
        response = api_test_client.get("/api/metrics")

        assert response.status_code == 200
        data = response.json()

        # All count fields should be non-negative
        for key in [
            "tasks_pending",
            "tasks_running",
            "tasks_completed",
            "tasks_failed",
            "proxies_total",
            "proxies_healthy",
            "proxies_failed",
            "workers_active",
            "workers_total",
        ]:
            assert data[key] >= 0, f"{key} should be non-negative"


@pytest.mark.e2e
@pytest.mark.api
class TestMetricsHealthAPI:
    """Tests for /api/health endpoint (metrics module)."""

    def test_health_check(self, api_test_client: TestClient, mock_orchestrator):
        """Test health check endpoint."""
        response = api_test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"

    def test_health_check_contains_orchestrator_info(
        self, api_test_client: TestClient, mock_orchestrator
    ):
        """Test health check includes orchestrator info."""
        response = api_test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        if "orchestrator" in data:
            assert "running" in data["orchestrator"]


@pytest.mark.e2e
@pytest.mark.api
class TestSummaryStatsAPI:
    """Tests for /api/stats/summary endpoint."""

    def test_get_summary_stats(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting summary statistics."""
        response = api_test_client.get("/api/stats/summary")

        assert response.status_code == 200
        data = response.json()

        # Should have all sections
        assert "timestamp" in data
        assert "uptime" in data
        assert "tasks" in data
        assert "proxies" in data
        assert "workers" in data

    def test_summary_tasks_structure(self, api_test_client: TestClient, mock_orchestrator):
        """Test tasks section structure."""
        response = api_test_client.get("/api/stats/summary")

        assert response.status_code == 200
        data = response.json()
        tasks = data["tasks"]

        assert "total" in tasks
        assert "pending" in tasks
        assert "running" in tasks
        assert "completed" in tasks
        assert "failed" in tasks
        assert "success_rate_percent" in tasks

    def test_summary_proxies_structure(self, api_test_client: TestClient, mock_orchestrator):
        """Test proxies section structure."""
        response = api_test_client.get("/api/stats/summary")

        assert response.status_code == 200
        data = response.json()
        proxies = data["proxies"]

        assert "total" in proxies
        assert "healthy" in proxies
        assert "failed" in proxies

    def test_summary_workers_structure(self, api_test_client: TestClient, mock_orchestrator):
        """Test workers section structure."""
        response = api_test_client.get("/api/stats/summary")

        assert response.status_code == 200
        data = response.json()
        workers = data["workers"]

        assert "active" in workers
        assert "total" in workers

    def test_summary_uptime_structure(self, api_test_client: TestClient, mock_orchestrator):
        """Test uptime section structure."""
        response = api_test_client.get("/api/stats/summary")

        assert response.status_code == 200
        data = response.json()
        uptime = data["uptime"]

        assert "seconds" in uptime
        assert "formatted" in uptime

    def test_success_rate_calculation(self, api_test_client: TestClient, mock_orchestrator):
        """Test success rate is calculated correctly."""
        response = api_test_client.get("/api/stats/summary")

        assert response.status_code == 200
        data = response.json()
        tasks = data["tasks"]

        # Success rate should be between 0 and 100
        assert 0 <= tasks["success_rate_percent"] <= 100


@pytest.mark.e2e
@pytest.mark.api
class TestMetricsWithoutOrchestrator:
    """Tests for metrics when orchestrator is not initialized."""

    def test_metrics_without_orchestrator(self, api_test_client: TestClient):
        """Test metrics when orchestrator not available."""
        with patch("ghoststorm.api.routes.metrics._get_orchestrator_stats") as mock_stats:
            mock_stats.return_value = {
                "uptime_seconds": None,
                "is_running": False,
                "workers_active": 0,
                "workers_total": 0,
            }

            response = api_test_client.get("/api/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data["workers_active"] == 0

    def test_health_without_orchestrator(self, api_test_client: TestClient):
        """Test health check without orchestrator."""
        with patch("ghoststorm.api.routes.metrics._get_orchestrator_stats") as mock_stats:
            mock_stats.return_value = {
                "uptime_seconds": None,
                "is_running": False,
                "workers_active": 0,
                "workers_total": 0,
            }

            response = api_test_client.get("/api/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"  # API is still healthy
