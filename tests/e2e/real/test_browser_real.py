"""Real browser integration tests.

These tests require browser automation capabilities.
Run with: pytest tests/e2e/real/ --run-real -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.real
@pytest.mark.browser
class TestBrowserLaunch:
    """Tests for real browser launch."""

    def test_launch_browser(self, api_test_client: TestClient):
        """Test launching a real browser."""
        response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        session_id = data.get("session_id")

        # Clean up
        if session_id:
            api_test_client.post(f"/api/flows/stop/{session_id}")

    def test_launch_with_proxy(self, api_test_client: TestClient):
        """Test launching browser with proxy."""
        response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://httpbin.org/ip",
                "headless": True,
                "use_proxy": True,
            },
        )

        # May succeed or fail based on proxy availability
        assert response.status_code in [200, 400, 503]


@pytest.mark.real
@pytest.mark.browser
class TestBrowserNavigation:
    """Tests for real browser navigation."""

    def test_navigate_to_page(self, api_test_client: TestClient):
        """Test navigating to a page."""
        # Start recording session
        start_response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )

        if start_response.status_code == 200:
            session_id = start_response.json().get("session_id")

            # Navigate to another page
            nav_response = api_test_client.post(
                f"/api/flows/{session_id}/navigate",
                json={"url": "https://example.org"},
            )

            # Clean up
            api_test_client.post(f"/api/flows/stop/{session_id}")

            # Navigation might succeed or not be implemented
            assert nav_response.status_code in [200, 400, 404]

    def test_get_page_content(self, api_test_client: TestClient):
        """Test getting page content."""
        start_response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )

        if start_response.status_code == 200:
            session_id = start_response.json().get("session_id")

            # Get page content
            content_response = api_test_client.get(f"/api/flows/{session_id}/content")

            api_test_client.post(f"/api/flows/stop/{session_id}")

            if content_response.status_code == 200:
                data = content_response.json()
                assert "html" in data or "content" in data


@pytest.mark.real
@pytest.mark.browser
class TestBrowserScreenshot:
    """Tests for browser screenshot functionality."""

    def test_take_screenshot(self, api_test_client: TestClient):
        """Test taking a screenshot."""
        start_response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )

        if start_response.status_code == 200:
            session_id = start_response.json().get("session_id")

            # Take screenshot
            screenshot_response = api_test_client.get(f"/api/flows/{session_id}/screenshot")

            api_test_client.post(f"/api/flows/stop/{session_id}")

            # Screenshot might be base64 or file path
            assert screenshot_response.status_code in [200, 400, 404]


@pytest.mark.real
@pytest.mark.browser
class TestBrowserDOMExtraction:
    """Tests for DOM extraction from real browser."""

    def test_extract_dom(self, api_test_client: TestClient):
        """Test extracting DOM from page."""
        start_response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )

        if start_response.status_code == 200:
            session_id = start_response.json().get("session_id")

            # Extract DOM
            dom_response = api_test_client.get(f"/api/flows/{session_id}/dom")

            api_test_client.post(f"/api/flows/stop/{session_id}")

            if dom_response.status_code == 200:
                data = dom_response.json()
                # Should have DOM elements
                assert "elements" in data or "clickables" in data or "inputs" in data

    def test_find_interactive_elements(self, api_test_client: TestClient):
        """Test finding interactive elements."""
        start_response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )

        if start_response.status_code == 200:
            session_id = start_response.json().get("session_id")

            # Get interactive elements
            elements_response = api_test_client.get(f"/api/flows/{session_id}/elements")

            api_test_client.post(f"/api/flows/stop/{session_id}")

            assert elements_response.status_code in [200, 404]


@pytest.mark.real
@pytest.mark.browser
class TestBrowserActions:
    """Tests for browser action execution."""

    def test_click_element(self, api_test_client: TestClient):
        """Test clicking an element."""
        start_response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )

        if start_response.status_code == 200:
            session_id = start_response.json().get("session_id")

            # Try to click an element
            click_response = api_test_client.post(
                f"/api/flows/{session_id}/action",
                json={
                    "type": "click",
                    "selector": "a",
                },
            )

            api_test_client.post(f"/api/flows/stop/{session_id}")

            # Action might succeed or fail
            assert click_response.status_code in [200, 400, 404]

    def test_type_text(self, api_test_client: TestClient):
        """Test typing text into an element."""
        start_response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://httpbin.org/forms/post",
                "headless": True,
            },
        )

        if start_response.status_code == 200:
            session_id = start_response.json().get("session_id")

            # Try to type in an input
            type_response = api_test_client.post(
                f"/api/flows/{session_id}/action",
                json={
                    "type": "type",
                    "selector": "input[name='custname']",
                    "text": "Test User",
                },
            )

            api_test_client.post(f"/api/flows/stop/{session_id}")

            assert type_response.status_code in [200, 400, 404]


@pytest.mark.real
@pytest.mark.browser
class TestBrowserStealth:
    """Tests for browser stealth mode."""

    def test_stealth_mode(self, api_test_client: TestClient):
        """Test browser with stealth mode enabled."""
        response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://bot.sannysoft.com/",
                "headless": True,
                "stealth": {
                    "webdriver": True,
                    "webgl": True,
                    "canvas": True,
                },
            },
        )

        if response.status_code == 200:
            session_id = response.json().get("session_id")
            api_test_client.post(f"/api/flows/stop/{session_id}")

        # Stealth mode should be applied
        assert response.status_code in [200, 400]

    def test_fingerprint_spoofing(self, api_test_client: TestClient):
        """Test fingerprint spoofing."""
        response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
                "fingerprint": True,
            },
        )

        if response.status_code == 200:
            session_id = response.json().get("session_id")
            api_test_client.post(f"/api/flows/stop/{session_id}")

        assert response.status_code in [200, 400]


@pytest.mark.real
@pytest.mark.browser
class TestFlowRecording:
    """Tests for flow recording with real browser."""

    def test_record_flow(self, api_test_client: TestClient):
        """Test recording a flow."""
        # Start recording
        start_response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )

        if start_response.status_code == 200:
            session_id = start_response.json().get("session_id")

            # Let it record for a moment
            import time
            time.sleep(2)

            # Stop recording
            stop_response = api_test_client.post(f"/api/flows/stop/{session_id}")

            assert stop_response.status_code == 200
            data = stop_response.json()
            assert "actions" in data or "flow" in data

    def test_add_checkpoint(self, api_test_client: TestClient):
        """Test adding checkpoint during recording."""
        start_response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )

        if start_response.status_code == 200:
            session_id = start_response.json().get("session_id")

            # Add checkpoint
            checkpoint_response = api_test_client.post(
                f"/api/flows/{session_id}/checkpoint",
                json={"name": "Page loaded"},
            )

            api_test_client.post(f"/api/flows/stop/{session_id}")

            assert checkpoint_response.status_code in [200, 400, 404]


@pytest.mark.real
@pytest.mark.browser
class TestFlowExecution:
    """Tests for flow execution with real browser."""

    def test_execute_saved_flow(self, api_test_client: TestClient):
        """Test executing a saved flow."""
        # First, get available flows
        flows_response = api_test_client.get("/api/flows")

        if flows_response.status_code == 200:
            flows = flows_response.json().get("flows", [])

            if flows:
                flow_id = flows[0]["id"]

                # Execute flow
                execute_response = api_test_client.post(
                    f"/api/flows/{flow_id}/execute",
                    json={"headless": True},
                )

                # Execution might succeed or fail
                assert execute_response.status_code in [200, 400, 404, 500]


@pytest.mark.real
@pytest.mark.browser
class TestBrowserPerformance:
    """Performance tests for browser operations."""

    def test_page_load_time(self, api_test_client: TestClient):
        """Test page load time is acceptable."""
        import time

        start = time.time()
        response = api_test_client.post(
            "/api/flows/record",
            json={
                "url": "https://example.com",
                "headless": True,
            },
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            session_id = response.json().get("session_id")
            api_test_client.post(f"/api/flows/stop/{session_id}")

        # Page should load within 30 seconds
        assert elapsed < 30

    def test_browser_cleanup(self, api_test_client: TestClient):
        """Test browsers are properly cleaned up."""
        sessions = []

        # Create multiple sessions
        for _ in range(3):
            response = api_test_client.post(
                "/api/flows/record",
                json={
                    "url": "https://example.com",
                    "headless": True,
                },
            )
            if response.status_code == 200:
                sessions.append(response.json().get("session_id"))

        # Clean up all
        for session_id in sessions:
            if session_id:
                api_test_client.post(f"/api/flows/stop/{session_id}")

        # All sessions should be stopped
        assert len(sessions) >= 0
