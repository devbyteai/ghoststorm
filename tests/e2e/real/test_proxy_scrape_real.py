"""Real proxy scraping integration tests.

These tests perform actual network requests to scrape proxies.
Run with: pytest tests/e2e/real/ --run-real -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.real
@pytest.mark.proxy
class TestProxyScraping:
    """Tests for real proxy scraping."""

    def test_scrape_free_proxies(self, api_test_client: TestClient):
        """Test scraping proxies from free sources."""
        response = api_test_client.post(
            "/api/proxies/scrape",
            json={
                "sources": ["free-proxy-list"],
                "limit": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data or "proxies" in data

    def test_scrape_multiple_sources(self, api_test_client: TestClient):
        """Test scraping from multiple sources."""
        response = api_test_client.post(
            "/api/proxies/scrape",
            json={
                "sources": ["free-proxy-list", "spys-one"],
                "limit": 20,
            },
        )

        assert response.status_code == 200

    def test_scrape_with_filters(self, api_test_client: TestClient):
        """Test scraping with protocol filter."""
        response = api_test_client.post(
            "/api/proxies/scrape",
            json={
                "sources": ["free-proxy-list"],
                "protocol": "http",
                "limit": 10,
            },
        )

        assert response.status_code == 200


@pytest.mark.real
@pytest.mark.proxy
class TestProxyValidation:
    """Tests for real proxy validation."""

    def test_validate_proxies(self, api_test_client: TestClient):
        """Test validating scraped proxies."""
        # First scrape some proxies
        scrape_response = api_test_client.post(
            "/api/proxies/scrape",
            json={
                "sources": ["free-proxy-list"],
                "limit": 5,
            },
        )

        if scrape_response.status_code == 200:
            # Wait for scrape to complete or get job status
            import time
            time.sleep(5)

            # Start validation
            validate_response = api_test_client.post("/api/proxies/test")

            assert validate_response.status_code in [200, 202]

    def test_validate_single_proxy(self, api_test_client: TestClient):
        """Test validating a single proxy."""
        response = api_test_client.post(
            "/api/proxies/test/single",
            json={
                "proxy": "1.2.3.4:8080",
                "timeout": 10,
            },
        )

        # May fail if proxy is invalid, but endpoint should work
        assert response.status_code in [200, 400]

    def test_validate_with_target(self, api_test_client: TestClient):
        """Test validating against specific target."""
        response = api_test_client.post(
            "/api/proxies/test",
            json={
                "target_url": "https://httpbin.org/ip",
                "limit": 5,
            },
        )

        assert response.status_code in [200, 202]


@pytest.mark.real
@pytest.mark.proxy
class TestProxyStats:
    """Tests for proxy statistics with real data."""

    def test_get_stats(self, api_test_client: TestClient):
        """Test getting proxy statistics."""
        response = api_test_client.get("/api/proxies/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "healthy" in data
        assert "failed" in data

    def test_stats_after_scrape(self, api_test_client: TestClient):
        """Test stats update after scraping."""
        # Get initial stats
        initial = api_test_client.get("/api/proxies/stats").json()

        # Scrape more
        api_test_client.post(
            "/api/proxies/scrape",
            json={"sources": ["free-proxy-list"], "limit": 5},
        )

        import time
        time.sleep(10)

        # Get updated stats
        updated = api_test_client.get("/api/proxies/stats").json()

        # Stats should be returned
        assert "total" in updated


@pytest.mark.real
@pytest.mark.proxy
class TestProxySources:
    """Tests for proxy source management."""

    def test_get_sources(self, api_test_client: TestClient):
        """Test getting available sources."""
        response = api_test_client.get("/api/proxies/sources")

        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert len(data["sources"]) > 0

    def test_source_health(self, api_test_client: TestClient):
        """Test checking source health."""
        response = api_test_client.get("/api/proxies/sources/health")

        assert response.status_code in [200, 404]

    def test_toggle_source(self, api_test_client: TestClient):
        """Test toggling a source."""
        # Get sources
        sources = api_test_client.get("/api/proxies/sources").json().get("sources", [])

        if sources:
            source_name = sources[0]["name"] if isinstance(sources[0], dict) else sources[0]

            # Toggle
            response = api_test_client.post(
                f"/api/proxies/sources/{source_name}/toggle",
            )

            assert response.status_code in [200, 404]


@pytest.mark.real
@pytest.mark.proxy
class TestProxyExportImport:
    """Tests for proxy export/import with real data."""

    def test_export_proxies(self, api_test_client: TestClient):
        """Test exporting proxies."""
        response = api_test_client.get("/api/proxies/export")

        assert response.status_code == 200
        # Should return proxy list

    def test_export_healthy_only(self, api_test_client: TestClient):
        """Test exporting only healthy proxies."""
        response = api_test_client.get("/api/proxies/export?status=healthy")

        assert response.status_code == 200

    def test_import_proxies(self, api_test_client: TestClient):
        """Test importing proxies."""
        response = api_test_client.post(
            "/api/proxies/import",
            json={
                "proxies": [
                    "192.168.1.1:8080",
                    "192.168.1.2:3128",
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "imported" in data


@pytest.mark.real
@pytest.mark.proxy
class TestPremiumProxyProviders:
    """Tests for premium proxy provider integration."""

    @pytest.mark.skip(reason="Requires API key")
    def test_decodo_connection(self, api_test_client: TestClient):
        """Test Decodo provider connection."""
        response = api_test_client.get("/api/proxies/providers/decodo/status")

        assert response.status_code in [200, 401]

    @pytest.mark.skip(reason="Requires API key")
    def test_brightdata_connection(self, api_test_client: TestClient):
        """Test Bright Data provider connection."""
        response = api_test_client.get("/api/proxies/providers/brightdata/status")

        assert response.status_code in [200, 401]

    @pytest.mark.skip(reason="Requires API key")
    def test_oxylabs_connection(self, api_test_client: TestClient):
        """Test Oxylabs provider connection."""
        response = api_test_client.get("/api/proxies/providers/oxylabs/status")

        assert response.status_code in [200, 401]


@pytest.mark.real
@pytest.mark.proxy
class TestTorIntegration:
    """Tests for Tor integration."""

    def test_tor_status(self, api_test_client: TestClient):
        """Test Tor status check."""
        response = api_test_client.get("/api/proxies/tor/status")

        assert response.status_code in [200, 503]

    def test_tor_new_circuit(self, api_test_client: TestClient):
        """Test requesting new Tor circuit."""
        response = api_test_client.post("/api/proxies/tor/new-circuit")

        # May fail if Tor not available
        assert response.status_code in [200, 400, 503]


@pytest.mark.real
@pytest.mark.proxy
class TestProxyPerformance:
    """Performance tests for proxy operations."""

    def test_scrape_performance(self, api_test_client: TestClient):
        """Test scraping performance."""
        import time

        start = time.time()
        response = api_test_client.post(
            "/api/proxies/scrape",
            json={"sources": ["free-proxy-list"], "limit": 50},
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        # Should start within 5 seconds
        assert elapsed < 5

    def test_validation_performance(self, api_test_client: TestClient):
        """Test validation performance."""
        import time

        # Import some test proxies
        api_test_client.post(
            "/api/proxies/import",
            json={
                "proxies": [f"192.168.1.{i}:8080" for i in range(1, 6)],
            },
        )

        start = time.time()
        response = api_test_client.post(
            "/api/proxies/test",
            json={"limit": 5, "timeout": 5},
        )
        elapsed = time.time() - start

        assert response.status_code in [200, 202]
        # Should start within 5 seconds
        assert elapsed < 5


@pytest.mark.real
@pytest.mark.proxy
class TestProxyJobManagement:
    """Tests for proxy job management."""

    def test_get_active_jobs(self, api_test_client: TestClient):
        """Test getting active jobs."""
        response = api_test_client.get("/api/proxies/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data

    def test_cancel_job(self, api_test_client: TestClient):
        """Test cancelling a job."""
        # Start a scrape job
        scrape_response = api_test_client.post(
            "/api/proxies/scrape",
            json={"sources": ["free-proxy-list"], "limit": 100},
        )

        if scrape_response.status_code == 200:
            job_id = scrape_response.json().get("job_id")

            if job_id:
                # Cancel it
                cancel_response = api_test_client.delete(f"/api/proxies/jobs/{job_id}")

                assert cancel_response.status_code in [200, 404]

    def test_get_job_status(self, api_test_client: TestClient):
        """Test getting job status."""
        # Start a job
        scrape_response = api_test_client.post(
            "/api/proxies/scrape",
            json={"sources": ["free-proxy-list"], "limit": 10},
        )

        if scrape_response.status_code == 200:
            job_id = scrape_response.json().get("job_id")

            if job_id:
                # Get status
                status_response = api_test_client.get(f"/api/proxies/jobs/{job_id}")

                assert status_response.status_code in [200, 404]
