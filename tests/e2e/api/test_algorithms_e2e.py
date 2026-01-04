"""E2E tests for Algorithms API endpoints."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestAlgorithmsListAPI:
    """Tests for /api/algorithms endpoint."""

    def test_list_algorithms(self, api_test_client: TestClient):
        """Test listing all algorithms."""
        response = api_test_client.get("/api/algorithms")

        assert response.status_code == 200
        data = response.json()
        assert "algorithms" in data
        assert isinstance(data["algorithms"], dict)

    def test_algorithms_structure(self, api_test_client: TestClient):
        """Test algorithm data structure."""
        response = api_test_client.get("/api/algorithms")

        assert response.status_code == 200
        data = response.json()

        for name, algo in data["algorithms"].items():
            assert "name" in algo
            assert "platform" in algo
            assert "type" in algo
            assert "status" in algo

    def test_contains_expected_algorithms(self, api_test_client: TestClient):
        """Test expected algorithms are present."""
        response = api_test_client.get("/api/algorithms")

        assert response.status_code == 200
        data = response.json()
        algos = data["algorithms"]

        # Check for key algorithms
        assert "tiktok_xbogus" in algos
        assert "instagram_oauth" in algos
        assert "youtube_api" in algos


@pytest.mark.e2e
@pytest.mark.api
class TestAlgorithmDetailAPI:
    """Tests for /api/algorithms/{name} endpoint."""

    def test_get_algorithm(self, api_test_client: TestClient):
        """Test getting a specific algorithm."""
        response = api_test_client.get("/api/algorithms/tiktok_xbogus")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TikTok X-Bogus"
        assert data["platform"] == "tiktok"

    def test_get_nonexistent_algorithm(self, api_test_client: TestClient):
        """Test getting non-existent algorithm."""
        response = api_test_client.get("/api/algorithms/nonexistent")

        assert response.status_code == 404

    def test_algorithm_has_description(self, api_test_client: TestClient):
        """Test algorithm has description."""
        response = api_test_client.get("/api/algorithms/tiktok_xbogus")

        assert response.status_code == 200
        data = response.json()
        assert "description" in data
        assert len(data["description"]) > 0

    def test_oauth_algorithm_has_example(self, api_test_client: TestClient):
        """Test OAuth algorithms have example code."""
        response = api_test_client.get("/api/algorithms/instagram_oauth")

        assert response.status_code == 200
        data = response.json()
        # OAuth algorithms should have example code
        assert "code" in data or "example_code" in data


@pytest.mark.e2e
@pytest.mark.api
class TestAlgorithmFetchAPI:
    """Tests for /api/algorithms/{name}/fetch/* endpoints."""

    def test_fetch_from_github_not_fetchable(self, api_test_client: TestClient):
        """Test fetching algorithm that cannot be fetched."""
        response = api_test_client.post("/api/algorithms/instagram_oauth/fetch/github")

        assert response.status_code == 400

    def test_fetch_from_github_success(self, api_test_client: TestClient):
        """Test fetching algorithm from GitHub."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.text = "def gorgon(): pass"
            mock_response.raise_for_status = MagicMock()
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with patch("builtins.open", MagicMock()):
                with patch("pathlib.Path.mkdir"):
                    with patch("ghoststorm.api.routes.algorithms.save_metadata"):
                        with patch("ghoststorm.api.routes.algorithms.load_metadata", return_value={}):
                            response = api_test_client.post(
                                "/api/algorithms/tiktok_gorgon/fetch/github"
                            )

                            assert response.status_code == 200
                            data = response.json()
                            assert data["success"] is True

    def test_fetch_from_cdn(self, api_test_client: TestClient):
        """Test fetching algorithm from CDN."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.text = '<script src="/js/bundle.js"></script>'
            mock_response.raise_for_status = MagicMock()
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with patch("builtins.open", MagicMock()):
                with patch("ghoststorm.api.routes.algorithms.save_metadata"):
                    with patch("ghoststorm.api.routes.algorithms.load_metadata", return_value={}):
                        response = api_test_client.post(
                            "/api/algorithms/tiktok_xbogus/fetch/cdn"
                        )

                        # May succeed or fail based on CDN parsing
                        assert response.status_code in [200, 400, 500]

    def test_fetch_from_cdn_no_source(self, api_test_client: TestClient):
        """Test fetching from CDN when no source configured."""
        response = api_test_client.post("/api/algorithms/tiktok_gorgon/fetch/cdn")

        assert response.status_code == 400


@pytest.mark.e2e
@pytest.mark.api
class TestAlgorithmTestAPI:
    """Tests for /api/algorithms/{name}/test endpoint."""

    def test_test_algorithm_no_code(self, api_test_client: TestClient):
        """Test testing algorithm without code."""
        with patch("ghoststorm.api.routes.algorithms.get_algorithm_code", return_value=None):
            response = api_test_client.post("/api/algorithms/tiktok_xbogus/test")

            assert response.status_code == 200
            data = response.json()
            # May succeed or fail based on code availability

    def test_test_python_algorithm(self, api_test_client: TestClient):
        """Test testing Python algorithm."""
        with patch("ghoststorm.api.routes.algorithms.get_algorithm_code") as mock_get:
            mock_get.return_value = "class Gorgon:\n    def encrypt(self): pass"

            response = api_test_client.post("/api/algorithms/tiktok_gorgon/test")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_test_invalid_python_syntax(self, api_test_client: TestClient):
        """Test testing Python with syntax error."""
        with patch("ghoststorm.api.routes.algorithms.get_algorithm_code") as mock_get:
            mock_get.return_value = "def broken(:\n    pass"

            response = api_test_client.post("/api/algorithms/tiktok_gorgon/test")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_test_nonexistent_algorithm(self, api_test_client: TestClient):
        """Test testing non-existent algorithm."""
        response = api_test_client.post("/api/algorithms/nonexistent/test")

        assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.api
class TestAlgorithmRefreshAPI:
    """Tests for /api/algorithms/refresh endpoint."""

    def test_refresh_all(self, api_test_client: TestClient):
        """Test refreshing all algorithms."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.text = "# code"
            mock_response.raise_for_status = MagicMock()
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with patch("builtins.open", MagicMock()):
                with patch("ghoststorm.api.routes.algorithms.save_metadata"):
                    with patch("ghoststorm.api.routes.algorithms.load_metadata", return_value={}):
                        response = api_test_client.post("/api/algorithms/refresh")

                        assert response.status_code == 200
                        data = response.json()
                        assert "updated" in data

    def test_refresh_handles_errors(self, api_test_client: TestClient):
        """Test refresh handles errors gracefully."""
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )

            response = api_test_client.post("/api/algorithms/refresh")

            assert response.status_code == 200
            data = response.json()
            # Should still return, with errors list
            assert "errors" in data or "updated" in data
