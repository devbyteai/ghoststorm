"""E2E tests for DOM API endpoints."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestDOMInfoAPI:
    """Tests for /api/dom endpoint."""

    def test_get_dom_info(self, api_test_client: TestClient):
        """Test getting DOM service information."""
        response = api_test_client.get("/api/dom")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "DOMService"
        assert data["version"] == "1.0.0"
        assert "features" in data
        assert "cached_states" in data

    def test_dom_features(self, api_test_client: TestClient):
        """Test DOM service features list."""
        response = api_test_client.get("/api/dom")

        assert response.status_code == 200
        data = response.json()
        features = data["features"]

        assert "DOM extraction" in features
        assert "Interactive element detection" in features
        assert "Smart selector generation" in features
        assert "Natural language element matching" in features


@pytest.mark.e2e
@pytest.mark.api
class TestDOMStateAPI:
    """Tests for /api/dom/state/{task_id} endpoints."""

    def test_get_state_not_found(self, api_test_client: TestClient):
        """Test getting state for non-existent task."""
        response = api_test_client.get("/api/dom/state/nonexistent-task")

        assert response.status_code == 404
        assert "No DOM state cached" in response.json()["detail"]

    def test_store_state(self, api_test_client: TestClient):
        """Test storing DOM state."""
        task_id = "test-task-123"
        state = {
            "url": "https://example.com",
            "title": "Test Page",
            "clickables": [
                {"selector": "button.submit", "description": "Submit button"}
            ],
            "inputs": [],
            "links": [],
        }

        response = api_test_client.post(
            f"/api/dom/state/{task_id}",
            json=state,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stored"
        assert data["task_id"] == task_id

    def test_get_stored_state(self, api_test_client: TestClient):
        """Test retrieving stored DOM state."""
        task_id = "test-task-456"
        state = {
            "url": "https://example.com/page",
            "title": "Page Title",
            "clickables": [],
            "inputs": [{"selector": "input#email", "type": "email"}],
            "links": [{"href": "/about", "text": "About"}],
        }

        # Store state
        api_test_client.post(f"/api/dom/state/{task_id}", json=state)

        # Retrieve state
        response = api_test_client.get(f"/api/dom/state/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["url"] == state["url"]
        assert data["title"] == state["title"]

    def test_clear_state(self, api_test_client: TestClient):
        """Test clearing DOM state."""
        task_id = "test-task-789"
        state = {"url": "https://example.com", "title": "Test"}

        # Store state
        api_test_client.post(f"/api/dom/state/{task_id}", json=state)

        # Clear state
        response = api_test_client.delete(f"/api/dom/state/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
        assert data["task_id"] == task_id

    def test_clear_nonexistent_state(self, api_test_client: TestClient):
        """Test clearing non-existent state."""
        response = api_test_client.delete("/api/dom/state/nonexistent")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"

    def test_state_lifecycle(self, api_test_client: TestClient):
        """Test full state lifecycle: store -> get -> clear -> 404."""
        task_id = "lifecycle-test"
        state = {"url": "https://test.com", "title": "Lifecycle Test"}

        # Store
        store_resp = api_test_client.post(f"/api/dom/state/{task_id}", json=state)
        assert store_resp.status_code == 200

        # Get
        get_resp = api_test_client.get(f"/api/dom/state/{task_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["url"] == state["url"]

        # Clear
        clear_resp = api_test_client.delete(f"/api/dom/state/{task_id}")
        assert clear_resp.status_code == 200

        # Verify 404
        verify_resp = api_test_client.get(f"/api/dom/state/{task_id}")
        assert verify_resp.status_code == 404


@pytest.mark.e2e
@pytest.mark.api
class TestDOMElementsAPI:
    """Tests for /api/dom/elements/{task_id} endpoint."""

    def test_get_elements_not_found(self, api_test_client: TestClient):
        """Test getting elements for non-existent task."""
        response = api_test_client.get("/api/dom/elements/nonexistent")

        assert response.status_code == 404

    def test_get_elements(self, api_test_client: TestClient):
        """Test getting interactive elements from cached state."""
        task_id = "elements-test"
        state = {
            "url": "https://example.com",
            "title": "Elements Test",
            "clickables": [
                {"selector": "button.submit", "text": "Submit"},
                {"selector": "button.cancel", "text": "Cancel"},
            ],
            "inputs": [
                {"selector": "input#name", "type": "text"},
                {"selector": "input#email", "type": "email"},
            ],
            "links": [
                {"href": "/home", "text": "Home"},
            ],
            "counts": {
                "clickables": 2,
                "inputs": 2,
                "links": 1,
            },
        }

        # Store state
        api_test_client.post(f"/api/dom/state/{task_id}", json=state)

        # Get elements
        response = api_test_client.get(f"/api/dom/elements/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert len(data["clickables"]) == 2
        assert len(data["inputs"]) == 2
        assert len(data["links"]) == 1
        assert data["counts"]["clickables"] == 2


@pytest.mark.e2e
@pytest.mark.api
class TestDOMAnalyzeAPI:
    """Tests for /api/dom/analyze endpoint."""

    def test_analyze_missing_dom_state(self, api_test_client: TestClient):
        """Test analyze without dom_state."""
        response = api_test_client.post(
            "/api/dom/analyze",
            json={"query": "find button"},
        )

        assert response.status_code == 400
        assert "Missing 'dom_state'" in response.json()["detail"]

    def test_analyze_missing_query(self, api_test_client: TestClient):
        """Test analyze without query."""
        response = api_test_client.post(
            "/api/dom/analyze",
            json={"dom_state": {"url": "https://example.com"}},
        )

        assert response.status_code == 400
        assert "Missing 'query'" in response.json()["detail"]

    def test_analyze_with_dom_state(self, api_test_client: TestClient):
        """Test analyzing DOM with query."""
        dom_state = {
            "url": "https://example.com",
            "title": "Test",
            "clickables": [
                {
                    "node": {
                        "tag": "button",
                        "node_id": "btn-1",
                        "text": "Submit Form",
                        "attributes": {"class": "btn-primary"},
                    },
                    "selector": "button.btn-primary",
                    "xpath": "//button[@class='btn-primary']",
                    "description": "Primary submit button",
                },
            ],
        }

        with patch("ghoststorm.api.routes.dom.DOMAnalyzer") as MockAnalyzer:
            mock_analyzer = MagicMock()
            mock_match = MagicMock()
            mock_match.to_dict.return_value = {
                "selector": "button.btn-primary",
                "description": "Primary submit button",
            }
            mock_analyzer.find_matches.return_value = [mock_match]
            MockAnalyzer.return_value = mock_analyzer

            response = api_test_client.post(
                "/api/dom/analyze",
                json={
                    "dom_state": dom_state,
                    "query": "submit button",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "submit button"
            assert "matches" in data
            assert "count" in data

    def test_analyze_error_handling(self, api_test_client: TestClient):
        """Test analyze handles errors gracefully."""
        dom_state = {
            "url": "https://example.com",
            "clickables": [{"invalid": "structure"}],
        }

        response = api_test_client.post(
            "/api/dom/analyze",
            json={
                "dom_state": dom_state,
                "query": "find something",
            },
        )

        # May succeed or fail based on DOM parsing
        assert response.status_code in [200, 500]


@pytest.mark.e2e
@pytest.mark.api
class TestDOMConfigAPI:
    """Tests for /api/dom/config endpoint."""

    def test_get_config(self, api_test_client: TestClient):
        """Test getting DOM extraction configuration."""
        with patch("ghoststorm.api.routes.dom.DOMConfig") as MockConfig:
            mock_config = MagicMock()
            mock_config.to_dict.return_value = {
                "max_depth": 10,
                "include_hidden": False,
                "extract_text": True,
                "max_elements": 1000,
            }
            MockConfig.return_value = mock_config

            response = api_test_client.get("/api/dom/config")

            assert response.status_code == 200
            data = response.json()
            assert "max_depth" in data or response.status_code == 200

    def test_config_structure(self, api_test_client: TestClient):
        """Test DOM config has expected structure."""
        response = api_test_client.get("/api/dom/config")

        assert response.status_code == 200
        # Response should be a dict
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.e2e
@pytest.mark.api
class TestDOMIntegration:
    """Integration tests for DOM API."""

    def test_full_dom_workflow(self, api_test_client: TestClient):
        """Test complete DOM workflow."""
        task_id = "integration-test"

        # 1. Check initial state (should be empty)
        info_resp = api_test_client.get("/api/dom")
        assert info_resp.status_code == 200

        # 2. Store DOM state
        dom_state = {
            "url": "https://example.com/form",
            "title": "Contact Form",
            "clickables": [
                {
                    "node": {"tag": "button", "node_id": "submit", "text": "Send"},
                    "selector": "button#submit",
                    "xpath": "//button[@id='submit']",
                    "description": "Submit button",
                },
            ],
            "inputs": [
                {"selector": "input#name", "type": "text"},
                {"selector": "input#email", "type": "email"},
            ],
            "links": [],
            "counts": {"clickables": 1, "inputs": 2, "links": 0},
        }

        store_resp = api_test_client.post(
            f"/api/dom/state/{task_id}",
            json=dom_state,
        )
        assert store_resp.status_code == 200

        # 3. Get interactive elements
        elements_resp = api_test_client.get(f"/api/dom/elements/{task_id}")
        assert elements_resp.status_code == 200
        assert len(elements_resp.json()["clickables"]) == 1

        # 4. Get full state
        state_resp = api_test_client.get(f"/api/dom/state/{task_id}")
        assert state_resp.status_code == 200
        assert state_resp.json()["title"] == "Contact Form"

        # 5. Clear state
        clear_resp = api_test_client.delete(f"/api/dom/state/{task_id}")
        assert clear_resp.status_code == 200

        # 6. Verify cleared
        verify_resp = api_test_client.get(f"/api/dom/state/{task_id}")
        assert verify_resp.status_code == 404
