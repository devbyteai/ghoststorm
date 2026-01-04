"""E2E tests for Configuration API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestPlatformConfigAPI:
    """Tests for /api/config/platforms endpoints."""

    def test_list_platforms(self, api_test_client: TestClient):
        """Test listing all platforms."""
        response = api_test_client.get("/api/config/platforms")

        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data

    def test_list_platforms_contains_all(self, api_test_client: TestClient):
        """Test all expected platforms are listed."""
        response = api_test_client.get("/api/config/platforms")

        assert response.status_code == 200
        data = response.json()
        platforms = data["platforms"]

        # Should have all platform types
        for platform in ["tiktok", "instagram", "youtube", "dextools", "generic"]:
            assert platform in platforms

    def test_platform_structure(self, api_test_client: TestClient):
        """Test platform data structure."""
        response = api_test_client.get("/api/config/platforms")

        assert response.status_code == 200
        data = response.json()

        for _platform_name, platform_data in data["platforms"].items():
            assert "defaults" in platform_data
            assert "fields" in platform_data
            assert "description" in platform_data

    def test_get_tiktok_config(self, api_test_client: TestClient):
        """Test getting TikTok platform config."""
        response = api_test_client.get("/api/config/platforms/tiktok")

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "tiktok"
        assert "config" in data
        assert "schema" in data

    def test_get_instagram_config(self, api_test_client: TestClient):
        """Test getting Instagram platform config."""
        response = api_test_client.get("/api/config/platforms/instagram")

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "instagram"

    def test_get_youtube_config(self, api_test_client: TestClient):
        """Test getting YouTube platform config."""
        response = api_test_client.get("/api/config/platforms/youtube")

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "youtube"

    def test_get_dextools_config(self, api_test_client: TestClient):
        """Test getting DEXTools platform config."""
        response = api_test_client.get("/api/config/platforms/dextools")

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "dextools"

    def test_get_generic_config(self, api_test_client: TestClient):
        """Test getting generic platform config."""
        response = api_test_client.get("/api/config/platforms/generic")

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "generic"

    def test_get_invalid_platform(self, api_test_client: TestClient):
        """Test getting invalid platform config."""
        response = api_test_client.get("/api/config/platforms/invalid")

        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.api
class TestEngineConfigAPI:
    """Tests for /api/config/engine endpoint."""

    def test_get_engine_config(self, api_test_client: TestClient):
        """Test getting engine configuration."""
        response = api_test_client.get("/api/config/engine")

        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "schema" in data
        assert "description" in data


@pytest.mark.e2e
@pytest.mark.api
class TestBehaviorConfigAPI:
    """Tests for /api/config/behavior endpoint."""

    def test_get_behavior_config(self, api_test_client: TestClient):
        """Test getting behavior configuration."""
        response = api_test_client.get("/api/config/behavior")

        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "schema" in data
        assert "description" in data


@pytest.mark.e2e
@pytest.mark.api
class TestPresetsAPI:
    """Tests for /api/config/presets endpoints."""

    def test_list_presets(self, api_test_client: TestClient):
        """Test listing presets."""
        response = api_test_client.get("/api/config/presets")

        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert isinstance(data["presets"], list)

    def test_preset_structure(self, api_test_client: TestClient):
        """Test preset data structure."""
        response = api_test_client.get("/api/config/presets")

        assert response.status_code == 200
        data = response.json()

        if data["presets"]:
            preset = data["presets"][0]
            assert "id" in preset
            assert "name" in preset
            assert "description" in preset
            assert "config" in preset

    def test_get_specific_preset(self, api_test_client: TestClient):
        """Test getting a specific preset."""
        # First list presets
        list_response = api_test_client.get("/api/config/presets")

        if list_response.json()["presets"]:
            preset_id = list_response.json()["presets"][0]["id"]

            response = api_test_client.get(f"/api/config/presets/{preset_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == preset_id

    def test_get_nonexistent_preset(self, api_test_client: TestClient):
        """Test getting non-existent preset."""
        response = api_test_client.get("/api/config/presets/nonexistent-preset")

        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.api
class TestAllConfigAPI:
    """Tests for /api/config/all endpoint."""

    def test_get_all_config(self, api_test_client: TestClient):
        """Test getting all configuration."""
        response = api_test_client.get("/api/config/all")

        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        assert "engine" in data
        assert "behavior" in data
        assert "presets" in data


@pytest.mark.e2e
@pytest.mark.api
class TestUserConfigAPI:
    """Tests for /api/config/current, save, reset endpoints."""

    def test_get_current_config(self, api_test_client: TestClient):
        """Test getting current user configuration."""
        response = api_test_client.get("/api/config/current")

        assert response.status_code == 200
        # Should return a dict with config values

    def test_save_config(self, api_test_client: TestClient):
        """Test saving configuration."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", MagicMock()):
                with patch("ghoststorm.core.models.config.Config.to_yaml"):
                    response = api_test_client.post(
                        "/api/config/save",
                        json={"workers": 5, "headless": True},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "saved"

    def test_reset_config(self, api_test_client: TestClient):
        """Test resetting configuration."""
        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.unlink"):
            response = api_test_client.post("/api/config/reset")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "reset"

    def test_reset_config_not_exists(self, api_test_client: TestClient):
        """Test resetting when config doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            response = api_test_client.post("/api/config/reset")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "reset"
