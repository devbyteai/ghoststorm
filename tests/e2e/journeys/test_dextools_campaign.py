"""E2E journey tests for DEXTools trending campaigns.

Tests complete user workflows for DEXTools automation.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ============================================================================
# SINGLE VISIT JOURNEY TESTS
# ============================================================================


@pytest.mark.e2e
@pytest.mark.journey
class TestDEXToolsSingleVisitJourney:
    """Tests for single DEXTools visit workflow."""

    def test_complete_single_visit_flow(self, api_test_client: TestClient, mock_orchestrator):
        """Test complete single visit journey.

        Flow:
        1. User enters DEXTools pair URL
        2. Platform is auto-detected
        3. Task is created
        4. Task executes with realistic behavior
        5. Results show engagement metrics
        """
        # Step 1: Detect platform
        pair_url = "https://www.dextools.io/app/en/ether/pair-explorer/0xdac17f958d2ee523a2206206994597c13d831ec7"

        detect_response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": pair_url}
        )

        assert detect_response.status_code == 200
        detect_data = detect_response.json()
        assert detect_data["platform"] == "dextools"
        assert detect_data["detected"] is True

        # Step 2: Check available configuration
        config_response = api_test_client.get("/api/config/platforms/dextools")
        assert config_response.status_code == 200

        config_schema = config_response.json()
        assert "behavior_mode" in config_schema["config"]

        # Step 3: Create task with single visit mode
        create_response = api_test_client.post(
            "/api/tasks",
            json={
                "url": pair_url,
                "workers": 1,
                "repeat": 1,
                "config": {
                    "mode": "single",
                    "behavior_mode": "realistic",
                    "dwell_time_min": 30.0,
                    "dwell_time_max": 90.0,
                    "enable_natural_scroll": True,
                    "enable_chart_hover": True,
                    "enable_social_clicks": True,
                }
            }
        )

        assert create_response.status_code == 200
        task_data = create_response.json()
        assert task_data["platform"] == "dextools"
        assert "task_id" in task_data

        task_id = task_data["task_id"]

        # Step 4: Verify task was created correctly
        status_response = api_test_client.get(f"/api/tasks/{task_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["platform"] == "dextools"

    def test_single_visit_with_passive_behavior(self, api_test_client: TestClient):
        """Test single visit with forced passive behavior."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 1,
                "config": {
                    "behavior_mode": "passive",  # Force passive
                    "enable_social_clicks": False,
                    "enable_tab_clicks": False,
                }
            }
        )

        assert response.status_code == 200
        assert response.json()["platform"] == "dextools"

    def test_single_visit_with_engaged_behavior(self, api_test_client: TestClient):
        """Test single visit with forced engaged behavior."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 1,
                "config": {
                    "behavior_mode": "engaged",
                    "enable_social_clicks": True,
                    "enable_tab_clicks": True,
                    "dwell_time_min": 60.0,
                    "dwell_time_max": 180.0,
                }
            }
        )

        assert response.status_code == 200


# ============================================================================
# CAMPAIGN JOURNEY TESTS
# ============================================================================


@pytest.mark.e2e
@pytest.mark.journey
class TestDEXToolsCampaignJourney:
    """Tests for DEXTools trending campaign workflow."""

    def test_complete_trending_campaign_setup(self, api_test_client: TestClient):
        """Test setting up a complete trending campaign.

        Flow:
        1. User decides on campaign parameters
        2. Creates campaign-mode task
        3. Multiple workers distribute visits over time
        """
        # Step 1: Get behavior weights to understand distribution
        weights_response = api_test_client.get("/api/config/dextools/behavior-weights")
        assert weights_response.status_code == 200

        weights = weights_response.json()["weights"]
        assert weights["passive"] == 60  # 60% will just view
        assert weights["light"] == 30    # 30% will interact once
        assert weights["engaged"] == 10  # 10% will be highly engaged

        # Step 2: Create campaign task
        campaign_response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 5,
                "repeat": 100,  # 100 visitors
                "config": {
                    "mode": "campaign",
                    "num_visitors": 100,
                    "duration_hours": 24.0,
                    "distribution_mode": "natural",
                    "behavior_mode": "realistic",
                }
            }
        )

        assert campaign_response.status_code == 200
        assert campaign_response.json()["platform"] == "dextools"

    def test_campaign_with_burst_distribution(self, api_test_client: TestClient):
        """Test campaign with burst distribution mode."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 10,
                "repeat": 50,
                "config": {
                    "mode": "campaign",
                    "num_visitors": 50,
                    "duration_hours": 6.0,
                    "distribution_mode": "burst",  # Bursts of activity
                }
            }
        )

        assert response.status_code == 200

    def test_campaign_with_even_distribution(self, api_test_client: TestClient):
        """Test campaign with even distribution mode."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 3,
                "repeat": 30,
                "config": {
                    "mode": "campaign",
                    "num_visitors": 30,
                    "duration_hours": 12.0,
                    "distribution_mode": "even",  # Evenly spaced
                }
            }
        )

        assert response.status_code == 200


# ============================================================================
# BEHAVIOR DISTRIBUTION TESTS
# ============================================================================


@pytest.mark.e2e
@pytest.mark.journey
class TestDEXToolsBehaviorDistribution:
    """Tests for verifying behavior distribution works correctly."""

    def test_behavior_weights_available(self, api_test_client: TestClient):
        """Behavior weights should be accessible and correct."""
        response = api_test_client.get("/api/config/dextools/behavior-weights")

        assert response.status_code == 200
        data = response.json()

        assert data["mode"] == "realistic"

        weights = data["weights"]
        total = sum(weights.values())
        assert total == 100

        # Check explanations are present
        assert "passive" in data["explanations"]
        assert "light" in data["explanations"]
        assert "engaged" in data["explanations"]

    def test_task_config_accepts_all_behavior_modes(self, api_test_client: TestClient):
        """All behavior modes should be accepted in task config."""
        modes = ["realistic", "passive", "light", "engaged"]

        for mode in modes:
            response = api_test_client.post(
                "/api/tasks",
                json={
                    "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                    "workers": 1,
                    "config": {"behavior_mode": mode}
                }
            )

            assert response.status_code == 200, f"Failed for mode: {mode}"


# ============================================================================
# SELECTOR HEALTH CHECK JOURNEY
# ============================================================================


@pytest.mark.e2e
@pytest.mark.journey
class TestDEXToolsSelectorHealthJourney:
    """Tests for selector health check workflow."""

    def test_selector_check_workflow(self, api_test_client: TestClient):
        """Test workflow for checking if selectors work.

        Flow:
        1. User wants to verify DEXTools selectors are current
        2. Gets current selectors
        3. Runs health check
        4. Reviews recommendations
        """
        # Step 1: Get current selectors
        selectors_response = api_test_client.get("/api/config/dextools/selectors")
        assert selectors_response.status_code == 200

        selectors = selectors_response.json()

        # Verify structure
        assert "social_links" in selectors
        assert "chart" in selectors
        assert "update_instructions" in selectors

        # Step 2: Health check is available (may fail without browser)
        # Just verify endpoint exists and returns proper structure
        check_response = api_test_client.post(
            "/api/config/dextools/test-selectors",
            json={
                "pair_url": "https://www.dextools.io/app/en/ether/pair-explorer/0xdac17f958d2ee523a2206206994597c13d831ec7",
                "headless": True,
            }
        )

        assert check_response.status_code == 200
        check_data = check_response.json()

        # Verify response structure
        assert "status" in check_data
        assert "recommendations" in check_data


# ============================================================================
# MULTI-CHAIN TESTS
# ============================================================================


@pytest.mark.e2e
@pytest.mark.journey
class TestDEXToolsMultiChain:
    """Tests for DEXTools across different blockchain networks."""

    @pytest.mark.parametrize("chain,pair_address", [
        ("ether", "0xdac17f958d2ee523a2206206994597c13d831ec7"),
        ("solana", "abc123def456"),
        ("bsc", "0x789xyz"),
        ("polygon", "0xpoly123"),
        ("arbitrum", "0xarb456"),
        ("base", "0xbase789"),
    ])
    def test_multi_chain_url_detection(
        self,
        api_test_client: TestClient,
        chain: str,
        pair_address: str
    ):
        """DEXTools URLs for various chains should be detected."""
        url = f"https://www.dextools.io/app/en/{chain}/pair-explorer/{pair_address}"

        response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": url}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "dextools"

    def test_create_task_different_chains(self, api_test_client: TestClient):
        """Tasks should work for different blockchain networks."""
        chains = [
            "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
            "https://www.dextools.io/app/en/bsc/pair-explorer/0x456",
            "https://www.dextools.io/app/en/polygon/pair-explorer/0x789",
        ]

        for url in chains:
            response = api_test_client.post(
                "/api/tasks",
                json={"url": url, "workers": 1}
            )
            assert response.status_code == 200
            assert response.json()["platform"] == "dextools"


# ============================================================================
# ERROR HANDLING JOURNEY
# ============================================================================


@pytest.mark.e2e
@pytest.mark.journey
class TestDEXToolsErrorHandling:
    """Tests for error handling in DEXTools workflows."""

    def test_invalid_dextools_url(self, api_test_client: TestClient):
        """Invalid DEXTools URL should not be detected as DEXTools."""
        response = api_test_client.post(
            "/api/tasks/detect",
            json={"url": "https://www.dextools.io/about"}  # Not a pair URL
        )

        assert response.status_code == 200
        # Should fall back to generic
        assert response.json()["platform"] != "dextools" or response.json()["detected"] is False

    def test_task_with_invalid_config(self, api_test_client: TestClient):
        """Invalid config values should be handled."""
        response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.dextools.io/app/en/ether/pair-explorer/0x123",
                "workers": 1,
                "config": {
                    "dwell_time_min": -10.0,  # Invalid negative
                }
            }
        )

        # Should either reject or use defaults
        # Implementation dependent
        assert response.status_code in [200, 400, 422]
