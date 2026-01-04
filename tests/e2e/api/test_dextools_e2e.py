"""E2E tests for DEXTools API endpoints.

Tests the DEXTools configuration and task API endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ============================================================================
# DEXToolsConfigAPI TESTS
# ============================================================================


@pytest.mark.e2e
@pytest.mark.api
class TestDEXToolsConfigAPI:
    """Tests for DEXTools configuration endpoints."""

    def test_get_dextools_platform_config(self, api_test_client: TestClient):
        """GET /api/config/platforms/dextools should return config schema."""
        response = api_test_client.get("/api/config/platforms/dextools")

        assert response.status_code == 200
        data = response.json()

        assert data["platform"] == "dextools"
        assert "config" in data
        assert "schema" in data

        # Check expected config fields are present
        config = data["config"]
        assert "pair_url" in config
        assert "behavior_mode" in config
        assert "dwell_time_min" in config
        assert "dwell_time_max" in config

    def test_get_dextools_selectors(self, api_test_client: TestClient):
        """GET /api/config/dextools/selectors should return selectors."""
        response = api_test_client.get("/api/config/dextools/selectors")

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "social_links" in data
        assert "xpath_fallbacks" in data
        assert "chart" in data
        assert "ui_elements" in data
        assert "update_instructions" in data

        # Check social links
        assert "twitter" in data["social_links"]
        assert "telegram" in data["social_links"]
        assert "discord" in data["social_links"]

        # Check chart selectors
        assert "container" in data["chart"]

    def test_get_dextools_behavior_weights(self, api_test_client: TestClient):
        """GET /api/config/dextools/behavior-weights should return weights."""
        response = api_test_client.get("/api/config/dextools/behavior-weights")

        assert response.status_code == 200
        data = response.json()

        assert data["mode"] == "realistic"
        assert "weights" in data
        assert "explanations" in data

        weights = data["weights"]
        assert "passive" in weights
        assert "light" in weights
        assert "engaged" in weights

        # Verify distribution
        assert weights["passive"] == 60
        assert weights["light"] == 30
        assert weights["engaged"] == 10

    def test_dextools_config_in_all_platforms(self, api_test_client: TestClient):
        """DEXTools should be listed in all platforms endpoint."""
        response = api_test_client.get("/api/config/platforms")

        assert response.status_code == 200
        data = response.json()

        assert "platforms" in data
        assert "dextools" in data["platforms"]

        dextools = data["platforms"]["dextools"]
        assert "defaults" in dextools
        assert "fields" in dextools

    def test_dextools_config_fields(self, api_test_client: TestClient):
        """DEXTools config should have all expected fields."""
        response = api_test_client.get("/api/config/platforms/dextools")

        assert response.status_code == 200
        schema = response.json()["schema"]

        # Check properties exist
        assert "properties" in schema

        props = schema["properties"]
        expected_fields = [
            "pair_url",
            "mode",
            "num_visitors",
            "duration_hours",
            "behavior_mode",
            "dwell_time_min",
            "dwell_time_max",
            "enable_natural_scroll",
            "enable_chart_hover",
            "enable_mouse_movement",
            "enable_social_clicks",
        ]

        for field in expected_fields:
            assert field in props, f"Missing field: {field}"


# ============================================================================
# DEXToolsTaskAPI TESTS
# ============================================================================


@pytest.mark.e2e
@pytest.mark.api
class TestDEXToolsTaskAPI:
    """Tests for DEXTools task creation and management."""

    def test_dextools_platform_detection(self, api_test_client: TestClient):
        """Platform should be auto-detected from DEXTools URL."""
        response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123abc"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["platform"] == "dextools"
        assert data["detected"] is True
        assert "pair_address" in data["metadata"]

    @pytest.mark.parametrize("url", [
        "https://www.dextools.io/app/en/ether/pair-explorer/0xdac17f958d2ee523a2206206994597c13d831ec7",
        "https://www.dextools.io/app/en/solana/pair-explorer/abc123def",
        "https://www.dextools.io/app/en/bsc/pair-explorer/0x456",
    ])
    def test_dextools_url_patterns(self, api_test_client: TestClient, url: str):
        """Various DEXTools URL patterns should be detected."""
        response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": url}
        )

        assert response.status_code == 200
        assert response.json()["platform"] == "dextools"

    def test_create_dextools_task(self, api_test_client: TestClient):
        """Should create a task with DEXTools URL."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 1,
                "repeat": 1,
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert data["platform"] == "dextools"
        assert data["status"] == "pending"

    def test_create_dextools_task_with_config(self, api_test_client: TestClient):
        """Should create task with custom DEXTools config."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 2,
                "repeat": 5,
                "config": {
                    "behavior_mode": "realistic",
                    "dwell_time_min": 45.0,
                    "dwell_time_max": 90.0,
                    "enable_natural_scroll": True,
                    "enable_chart_hover": True,
                    "enable_social_clicks": True,
                }
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["platform"] == "dextools"
        assert data["workers"] == 2

    def test_create_dextools_campaign_task(self, api_test_client: TestClient):
        """Should create campaign-mode task."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 5,
                "repeat": 100,
                "config": {
                    "mode": "campaign",
                    "num_visitors": 100,
                    "duration_hours": 12.0,
                    "behavior_mode": "realistic",
                }
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["platform"] == "dextools"


# ============================================================================
# SELECTOR TEST ENDPOINT TESTS
# ============================================================================


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.browser
class TestDEXToolsSelectorTest:
    """Tests for selector health check endpoint.

    Note: These tests may require browser to be available.
    """

    def test_selector_test_endpoint_exists(self, api_test_client: TestClient):
        """POST /api/config/dextools/test-selectors should exist."""
        # Just test the endpoint exists and returns proper structure
        # Actual browser test may fail without browser installed
        response = api_test_client.post(
            "/api/config/dextools/test-selectors",
            json={
                "pair_url": "https://www.dextools.io/app/en/ether/pair-explorer/0xdac17f958d2ee523a2206206994597c13d831ec7",
                "headless": True,
                "timeout_s": 10.0,
            }
        )

        # Accept 200 (success) or proper error response
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "status" in data
        assert "page_loads" in data
        assert "chart_visible" in data
        assert "social_links_found" in data
        assert "errors" in data
        assert "recommendations" in data


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.e2e
@pytest.mark.api
class TestDEXToolsAPIIntegration:
    """Integration tests for DEXTools API flow."""

    def test_full_task_creation_flow(self, api_test_client: TestClient):
        """Test complete flow: detect -> create -> check status."""
        # Step 1: Detect platform
        detect_response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123"}
        )
        assert detect_response.status_code == 200
        assert detect_response.json()["platform"] == "dextools"

        # Step 2: Get config for platform
        config_response = api_test_client.get("/api/config/platforms/dextools")
        assert config_response.status_code == 200

        # Step 3: Create task
        create_response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 1,
            }
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["task_id"]

        # Step 4: Check task status
        status_response = api_test_client.get(f"/api/tasks/{task_id}")
        assert status_response.status_code == 200
        assert status_response.json()["platform"] == "dextools"

    def test_config_and_behavior_weights_consistency(self, api_test_client: TestClient):
        """Config and behavior weights should be consistent."""
        # Get config
        config_response = api_test_client.get("/api/config/platforms/dextools")
        assert config_response.status_code == 200

        # Get behavior weights
        weights_response = api_test_client.get("/api/config/dextools/behavior-weights")
        assert weights_response.status_code == 200

        weights = weights_response.json()["weights"]
        total = sum(weights.values())
        assert total == 100, "Behavior weights should sum to 100"
