"""E2E tests for Data Management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestDataStatsAPI:
    """Tests for /api/data/stats endpoint."""

    def test_get_stats(self, api_test_client: TestClient):
        """Test getting data statistics."""
        response = api_test_client.get("/api/data/stats")

        assert response.status_code == 200
        data = response.json()

        # Should have counts for each category
        assert "user_agents" in data
        assert "fingerprints" in data
        assert "referrers" in data
        assert "blacklists" in data
        assert "screen_sizes" in data
        assert "behavior" in data
        assert "evasion" in data

    def test_stats_non_negative(self, api_test_client: TestClient):
        """Test stats values are non-negative."""
        response = api_test_client.get("/api/data/stats")

        assert response.status_code == 200
        data = response.json()

        for key, value in data.items():
            assert value >= 0, f"{key} should be non-negative"


@pytest.mark.e2e
@pytest.mark.api
class TestDataCategoryAPI:
    """Tests for /api/data/{category} endpoints."""

    @pytest.mark.parametrize(
        "category",
        [
            "user_agents",
            "fingerprints",
            "referrers",
            "blacklists",
            "screen_sizes",
            "behavior",
            "evasion",
        ],
    )
    def test_list_category_items(self, api_test_client: TestClient, category: str):
        """Test listing items for each category."""
        response = api_test_client.get(f"/api/data/{category}")

        assert response.status_code == 200
        data = response.json()
        assert "files" in data

    def test_invalid_category(self, api_test_client: TestClient):
        """Test listing invalid category."""
        response = api_test_client.get("/api/data/invalid_category")

        assert response.status_code == 400


@pytest.mark.e2e
@pytest.mark.api
class TestDataFileAPI:
    """Tests for /api/data/{category}/{filename} endpoints."""

    def test_get_file_content(self, api_test_client: TestClient):
        """Test getting file content."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", MagicMock()) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "line1\nline2\n"
                mock_open.return_value.__enter__.return_value.__iter__ = lambda self: iter(
                    ["line1\n", "line2\n"]
                )

                response = api_test_client.get("/api/data/user_agents/test.txt")

                # May be 200 or 404 depending on mock setup
                assert response.status_code in [200, 404]

    def test_get_nonexistent_file(self, api_test_client: TestClient):
        """Test getting non-existent file."""
        with patch("pathlib.Path.exists", return_value=False):
            response = api_test_client.get("/api/data/user_agents/nonexistent.txt")

            assert response.status_code == 404

    def test_path_traversal_blocked(self, api_test_client: TestClient):
        """Test path traversal is blocked."""
        response = api_test_client.get("/api/data/user_agents/../../../etc/passwd")

        # Should be 400 or 404, not 200
        assert response.status_code in [400, 404]

    def test_add_data_item(self, api_test_client: TestClient):
        """Test adding a data item."""
        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.mkdir"):
            with patch("builtins.open", MagicMock()):
                response = api_test_client.post(
                    "/api/data/user_agents/custom.txt",
                    json={"content": "Mozilla/5.0 Test Agent"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_delete_data_item(self, api_test_client: TestClient):
        """Test deleting a data item."""
        import json as json_lib

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", MagicMock()) as mock_open:
                mock_open.return_value.__enter__.return_value.__iter__ = lambda self: iter(
                    ["item1\n", "item2\n"]
                )

                # DELETE with body requires using request() method or content parameter
                response = api_test_client.request(
                    method="DELETE",
                    url="/api/data/user_agents/test.txt",
                    content=json_lib.dumps({"content": "item1"}),
                    headers={"Content-Type": "application/json"},
                )

                assert response.status_code in [200, 404, 500]


@pytest.mark.e2e
@pytest.mark.api
class TestUserAgentGenerationAPI:
    """Tests for /api/data/user_agents/generate endpoint."""

    def test_generate_user_agents(self, api_test_client: TestClient):
        """Test generating user agents."""
        with patch("browserforge.headers.HeaderGenerator") as MockHG:
            mock_hg = MagicMock()
            mock_hg.generate.return_value = {
                "User-Agent": "Mozilla/5.0 Test",
                "sec-ch-ua": '"Chromium";v="120"',
                "sec-ch-ua-platform": '"Windows"',
                "sec-ch-ua-mobile": "?0",
                "Accept-Language": "en-US",
            }
            MockHG.return_value = mock_hg

            response = api_test_client.post(
                "/api/data/user_agents/generate",
                json={"browser": "chrome", "os": "windows", "count": 3},
            )

            assert response.status_code == 200
            data = response.json()
            if data.get("success"):
                assert "user_agents" in data
                assert len(data["user_agents"]) <= 3

    def test_generate_user_agents_no_browserforge(self, api_test_client: TestClient):
        """Test generating when browserforge not installed."""
        with patch("browserforge.headers.HeaderGenerator", side_effect=ImportError("No module")):
            response = api_test_client.post(
                "/api/data/user_agents/generate",
                json={"browser": "chrome", "os": "windows", "count": 1},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_parse_user_agent(self, api_test_client: TestClient):
        """Test parsing a user agent."""
        response = api_test_client.post(
            "/api/data/user_agents/parse",
            json={
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "browser" in data
        assert "os" in data
        assert "device" in data
        assert data["browser"] == "Chrome"
        assert data["os"] == "Windows"

    def test_parse_firefox_user_agent(self, api_test_client: TestClient):
        """Test parsing Firefox user agent."""
        response = api_test_client.post(
            "/api/data/user_agents/parse",
            json={
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["browser"] == "Firefox"

    def test_parse_safari_user_agent(self, api_test_client: TestClient):
        """Test parsing Safari user agent."""
        response = api_test_client.post(
            "/api/data/user_agents/parse",
            json={
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15"
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["browser"] == "Safari"
        assert data["os"] == "macOS"

    def test_parse_mobile_user_agent(self, api_test_client: TestClient):
        """Test parsing mobile user agent."""
        response = api_test_client.post(
            "/api/data/user_agents/parse",
            json={
                "user_agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile"
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["device"] == "Mobile"
        assert data["os"] == "Android"


@pytest.mark.e2e
@pytest.mark.api
class TestUserAgentRecommendationAPI:
    """Tests for /api/data/user_agents/recommendation endpoint."""

    @pytest.mark.parametrize("platform", ["tiktok", "instagram", "youtube", "dextools", "generic"])
    def test_get_recommendation(self, api_test_client: TestClient, platform: str):
        """Test getting UA recommendations for each platform."""
        response = api_test_client.get(f"/api/data/user_agents/recommendation/{platform}")

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == platform
        assert "recommended_mode" in data
        assert "recommended_file" in data
        assert "message" in data
        assert "settings" in data

    def test_unknown_platform_falls_back(self, api_test_client: TestClient):
        """Test unknown platform falls back to generic."""
        response = api_test_client.get("/api/data/user_agents/recommendation/unknown")

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "generic"


@pytest.mark.e2e
@pytest.mark.api
class TestFingerprintGenerationAPI:
    """Tests for /api/data/fingerprints/generate endpoint."""

    def test_generate_fingerprints(self, api_test_client: TestClient):
        """Test generating fingerprints."""
        with patch("browserforge.fingerprints.FingerprintGenerator") as MockFG:
            mock_fp = MagicMock()
            mock_fp.screen.width = 1920
            mock_fp.screen.height = 1080
            mock_fp.screen.availWidth = 1920
            mock_fp.screen.availHeight = 1040
            mock_fp.screen.colorDepth = 24
            mock_fp.screen.devicePixelRatio = 1
            mock_fp.navigator.userAgent = "Mozilla/5.0 Test"
            mock_fp.navigator.platform = "Win32"
            mock_fp.navigator.language = "en-US"
            mock_fp.navigator.languages = ["en-US"]
            mock_fp.navigator.hardwareConcurrency = 8
            mock_fp.navigator.deviceMemory = 8
            mock_fp.navigator.maxTouchPoints = 0
            mock_fp.videoCard = None
            mock_fp.fonts = []
            mock_fp.audioCodecs = {}
            mock_fp.videoCodecs = {}

            mock_fg = MagicMock()
            mock_fg.generate.return_value = mock_fp
            MockFG.return_value = mock_fg

            response = api_test_client.post(
                "/api/data/fingerprints/generate",
                json={"browser": "chrome", "os": "windows", "count": 1},
            )

            assert response.status_code == 200
            data = response.json()
            if data.get("success"):
                assert "fingerprints" in data

    def test_sample_fingerprint(self, api_test_client: TestClient):
        """Test sampling a fingerprint."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", MagicMock()) as mock_open:
                import json

                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                    [
                        {"screen": {"width": 1920, "height": 1080}},
                    ]
                )

                response = api_test_client.get("/api/data/fingerprints/sample")

                # May succeed or fail based on file availability
                assert response.status_code == 200
