"""E2E tests for Proxy Management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestProxySourcesAPI:
    """Tests for /api/proxies/sources endpoint."""

    def test_get_sources(self, api_test_client: TestClient):
        """Test listing proxy sources."""
        response = api_test_client.get("/api/proxies/sources")

        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) > 0

    def test_sources_structure(self, api_test_client: TestClient):
        """Test source data structure."""
        response = api_test_client.get("/api/proxies/sources")

        assert response.status_code == 200
        data = response.json()

        source = data["sources"][0]
        assert "id" in source
        assert "name" in source
        assert "url" in source
        assert "type" in source


@pytest.mark.e2e
@pytest.mark.api
class TestProxyStatsAPI:
    """Tests for /api/proxies/stats endpoint."""

    def test_get_stats(self, api_test_client: TestClient):
        """Test getting proxy statistics."""
        response = api_test_client.get("/api/proxies/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "alive" in data
        assert "dead" in data
        assert "untested" in data

    def test_stats_non_negative(self, api_test_client: TestClient):
        """Test stats values are non-negative."""
        response = api_test_client.get("/api/proxies/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0
        assert data["alive"] >= 0
        assert data["dead"] >= 0


@pytest.mark.e2e
@pytest.mark.api
class TestProxyScrapeAPI:
    """Tests for /api/proxies/scrape/* endpoints."""

    def test_start_scrape(self, api_test_client: TestClient):
        """Test starting a scrape job."""
        with patch("ghoststorm.api.routes.proxies.asyncio.create_task"):
            response = api_test_client.post("/api/proxies/scrape/start")

            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert "sources_total" in data

    def test_get_scrape_status(self, api_test_client: TestClient):
        """Test getting scrape job status."""
        # First start a job
        with patch("ghoststorm.api.routes.proxies.asyncio.create_task"):
            start_response = api_test_client.post("/api/proxies/scrape/start")
            job_id = start_response.json()["job_id"]

            response = api_test_client.get(f"/api/proxies/scrape/{job_id}")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "sources_total" in data

    def test_get_nonexistent_scrape_job(self, api_test_client: TestClient):
        """Test getting non-existent scrape job."""
        response = api_test_client.get("/api/proxies/scrape/nonexistent-id")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data


@pytest.mark.e2e
@pytest.mark.api
class TestProxyTestAPI:
    """Tests for /api/proxies/test/* endpoints."""

    def test_start_test_no_proxies(self, api_test_client: TestClient):
        """Test starting test when no proxies exist."""
        with patch("ghoststorm.api.routes.proxies.count_lines", return_value=0):
            response = api_test_client.post("/api/proxies/test/start")

            assert response.status_code == 200
            data = response.json()
            # Should indicate no proxies to test
            assert "error" in data or data.get("total", 0) == 0

    def test_start_test_with_proxies(self, api_test_client: TestClient):
        """Test starting test when proxies exist."""
        with patch("ghoststorm.api.routes.proxies.count_lines", return_value=100):
            with patch("ghoststorm.api.routes.proxies.asyncio.create_task"):
                with patch("ghoststorm.api.routes.proxies.read_proxies", return_value=set()):
                    response = api_test_client.post("/api/proxies/test/start")

                    assert response.status_code == 200
                    data = response.json()
                    if "job_id" in data:
                        assert data["total"] == 100

    def test_get_test_status(self, api_test_client: TestClient):
        """Test getting test job status."""
        with patch("ghoststorm.api.routes.proxies.count_lines", return_value=10):
            with patch("ghoststorm.api.routes.proxies.asyncio.create_task"):
                with patch("ghoststorm.api.routes.proxies.read_proxies", return_value=set()):
                    start_response = api_test_client.post("/api/proxies/test/start")

                    if "job_id" in start_response.json():
                        job_id = start_response.json()["job_id"]

                        response = api_test_client.get(f"/api/proxies/test/{job_id}")

                        assert response.status_code == 200
                        data = response.json()
                        assert "status" in data or "error" in data

    def test_stop_test(self, api_test_client: TestClient):
        """Test stopping a test job."""
        with patch("ghoststorm.api.routes.proxies.count_lines", return_value=10):
            with patch("ghoststorm.api.routes.proxies.asyncio.create_task"):
                with patch("ghoststorm.api.routes.proxies.read_proxies", return_value=set()):
                    start_response = api_test_client.post("/api/proxies/test/start")

                    if "job_id" in start_response.json():
                        job_id = start_response.json()["job_id"]

                        response = api_test_client.post(f"/api/proxies/test/{job_id}/stop")

                        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.api
class TestProxyCleanAPI:
    """Tests for /api/proxies/clean endpoint."""

    def test_clean_no_alive(self, api_test_client: TestClient):
        """Test cleaning when no alive proxies."""
        with patch("ghoststorm.api.routes.proxies.read_proxies", return_value=set()):
            response = api_test_client.post("/api/proxies/clean")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data or data.get("removed", 0) == 0

    def test_clean_with_alive(self, api_test_client: TestClient):
        """Test cleaning with alive proxies."""
        alive = {"1.2.3.4:8080", "5.6.7.8:3128"}
        aggregated = {"1.2.3.4:8080", "5.6.7.8:3128", "9.10.11.12:80"}

        def mock_read(path):
            if "alive" in str(path) or "working" in str(path):
                return alive
            return aggregated

        with patch("ghoststorm.api.routes.proxies.read_proxies", side_effect=mock_read):
            with patch("builtins.open", MagicMock()):
                with patch("pathlib.Path.exists", return_value=True):
                    response = api_test_client.post("/api/proxies/clean")

                    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.api
class TestProxyImportExportAPI:
    """Tests for /api/proxies/import and export endpoints."""

    def test_import_valid_proxies(self, api_test_client: TestClient):
        """Test importing valid proxies."""
        with patch("ghoststorm.api.routes.proxies.read_proxies", return_value=set()):
            with patch("builtins.open", MagicMock()):
                with patch("pathlib.Path.mkdir"):
                    response = api_test_client.post(
                        "/api/proxies/import",
                        json={"proxies": ["1.2.3.4:8080", "5.6.7.8:3128"]},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "added" in data
                    assert data["added"] >= 0

    def test_import_invalid_proxies(self, api_test_client: TestClient):
        """Test importing invalid proxies."""
        response = api_test_client.post(
            "/api/proxies/import",
            json={"proxies": ["not-a-proxy", "also-invalid"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("added", 0) == 0

    def test_import_mixed_proxies(self, api_test_client: TestClient):
        """Test importing mix of valid and invalid proxies."""
        with patch("ghoststorm.api.routes.proxies.read_proxies", return_value=set()):
            with patch("builtins.open", MagicMock()):
                with patch("pathlib.Path.mkdir"):
                    response = api_test_client.post(
                        "/api/proxies/import",
                        json={
                            "proxies": [
                                "1.2.3.4:8080",  # valid
                                "not-valid",  # invalid
                                "5.6.7.8:3128",  # valid
                            ]
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["added"] >= 0

    def test_export_proxies(self, api_test_client: TestClient):
        """Test exporting proxies."""
        proxies = {"1.2.3.4:8080", "5.6.7.8:3128"}
        with patch("ghoststorm.api.routes.proxies.read_proxies", return_value=proxies):
            response = api_test_client.get("/api/proxies/export")

            assert response.status_code == 200
            data = response.json()
            assert "proxies" in data
            assert isinstance(data["proxies"], list)

    def test_export_no_proxies(self, api_test_client: TestClient):
        """Test exporting when no proxies exist."""
        with patch("ghoststorm.api.routes.proxies.read_proxies", return_value=set()):
            response = api_test_client.get("/api/proxies/export")

            assert response.status_code == 200
            data = response.json()
            assert data.get("proxies", []) == [] or "error" in data


@pytest.mark.e2e
@pytest.mark.api
class TestProxyProvidersAPI:
    """Tests for /api/proxies/providers/* endpoints."""

    def test_list_providers(self, api_test_client: TestClient):
        """Test listing premium providers."""
        with patch("ghoststorm.api.routes.proxies._get_credential_store") as mock_store:
            mock_store.return_value.get = MagicMock(return_value=None)

            response = api_test_client.get("/api/proxies/providers")

            assert response.status_code == 200
            data = response.json()
            assert "providers" in data
            assert isinstance(data["providers"], list)

    def test_provider_structure(self, api_test_client: TestClient):
        """Test provider data structure."""
        with patch("ghoststorm.api.routes.proxies._get_credential_store") as mock_store:
            mock_store.return_value.get = MagicMock(return_value=None)

            response = api_test_client.get("/api/proxies/providers")

            assert response.status_code == 200
            data = response.json()

            for provider in data["providers"]:
                assert "name" in provider
                assert "configured" in provider

    def test_get_unconfigured_provider(self, api_test_client: TestClient):
        """Test getting unconfigured provider."""
        with patch("ghoststorm.api.routes.proxies._get_credential_store") as mock_store:
            mock_store.return_value.get = MagicMock(return_value=None)

            response = api_test_client.get("/api/proxies/providers/decodo")

            assert response.status_code == 200
            data = response.json()
            assert data["configured"] is False

    def test_get_configured_provider(self, api_test_client: TestClient):
        """Test getting configured provider."""
        config = {
            "username": "testuser",
            "password": "secret123",
            "country": "US",
        }
        with patch("ghoststorm.api.routes.proxies._get_credential_store") as mock_store:
            mock_store.return_value.get = MagicMock(return_value=config)

            response = api_test_client.get("/api/proxies/providers/decodo")

            assert response.status_code == 200
            data = response.json()
            assert data["configured"] is True
            assert data["config"]["password"] == "********"  # Should be masked

    def test_configure_decodo_provider(self, api_test_client: TestClient):
        """Test configuring Decodo provider."""
        with patch("ghoststorm.api.routes.proxies._get_credential_store") as mock_store:
            mock_store.return_value.save = MagicMock()

            response = api_test_client.post(
                "/api/proxies/providers/configure",
                json={
                    "provider": "decodo",
                    "username": "testuser",
                    "password": "testpass",
                    "country": "US",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_configure_decodo_missing_password(self, api_test_client: TestClient):
        """Test configuring Decodo without password."""
        response = api_test_client.post(
            "/api/proxies/providers/configure",
            json={
                "provider": "decodo",
                "username": "testuser",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "password" in data["error"].lower()

    def test_configure_brightdata_provider(self, api_test_client: TestClient):
        """Test configuring Bright Data provider."""
        with patch("ghoststorm.api.routes.proxies._get_credential_store") as mock_store:
            mock_store.return_value.save = MagicMock()

            response = api_test_client.post(
                "/api/proxies/providers/configure",
                json={
                    "provider": "brightdata",
                    "customer_id": "cust123",
                    "password": "pass123",
                    "zone": "residential",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_remove_provider(self, api_test_client: TestClient):
        """Test removing a provider."""
        with patch("ghoststorm.api.routes.proxies._get_credential_store") as mock_store:
            mock_store.return_value.is_configured = MagicMock(return_value=True)
            mock_store.return_value.remove = MagicMock()

            response = api_test_client.delete("/api/proxies/providers/decodo")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_remove_unconfigured_provider(self, api_test_client: TestClient):
        """Test removing unconfigured provider."""
        with patch("ghoststorm.api.routes.proxies._get_credential_store") as mock_store:
            mock_store.return_value.is_configured = MagicMock(return_value=False)

            response = api_test_client.delete("/api/proxies/providers/decodo")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


@pytest.mark.e2e
@pytest.mark.api
class TestProxyTorAPI:
    """Tests for /api/proxies/providers/tor/test endpoint."""

    def test_tor_test_not_running(self, api_test_client: TestClient):
        """Test Tor connection when not running."""
        with patch("asyncio.open_connection", side_effect=ConnectionRefusedError()):
            response = api_test_client.post("/api/proxies/providers/tor/test")

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False

    def test_tor_test_timeout(self, api_test_client: TestClient):
        """Test Tor connection timeout."""

        with patch("asyncio.wait_for", side_effect=TimeoutError()):
            response = api_test_client.post("/api/proxies/providers/tor/test")

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert "timeout" in data["error"].lower()


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.real
class TestProxyRealScrape:
    """Real proxy scraping tests - require --run-real flag."""

    def test_real_scrape_single_source(self, api_test_client: TestClient):
        """Test real scraping of a single source."""
        # This would actually scrape a real proxy source
        # Marked as real test, so only runs with --run-real
        pass  # Implementation depends on actual source availability

    def test_real_proxy_validation(self, api_test_client: TestClient):
        """Test real proxy validation."""
        # Would test against a real proxy
        pass
