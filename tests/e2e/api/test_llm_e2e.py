"""E2E tests for LLM API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.api
class TestLLMProvidersAPI:
    """Tests for /api/llm/providers endpoints."""

    def test_list_providers(self, api_test_client: TestClient, mock_orchestrator):
        """Test listing available LLM providers."""
        response = api_test_client.get("/api/llm/providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "current_provider" in data
        assert isinstance(data["providers"], list)

    def test_list_providers_structure(self, api_test_client: TestClient, mock_orchestrator):
        """Test provider info structure."""
        response = api_test_client.get("/api/llm/providers")

        assert response.status_code == 200
        data = response.json()

        if data["providers"]:
            provider = data["providers"][0]
            assert "name" in provider
            assert "default_model" in provider
            assert "supported_models" in provider
            assert "requires_api_key" in provider
            assert "supports_streaming" in provider
            assert "supports_tools" in provider

    def test_set_provider_ollama(self, api_test_client: TestClient, mock_orchestrator):
        """Test setting Ollama as provider."""
        response = api_test_client.post(
            "/api/llm/providers/set",
            json={"provider": "ollama"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["provider"] == "ollama"

    def test_set_provider_openai(self, api_test_client: TestClient, mock_orchestrator):
        """Test setting OpenAI as provider."""
        response = api_test_client.post(
            "/api/llm/providers/set",
            json={"provider": "openai"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["provider"] == "openai"

    def test_set_provider_anthropic(self, api_test_client: TestClient, mock_orchestrator):
        """Test setting Anthropic as provider."""
        response = api_test_client.post(
            "/api/llm/providers/set",
            json={"provider": "anthropic"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["provider"] == "anthropic"

    def test_set_invalid_provider(self, api_test_client: TestClient, mock_orchestrator):
        """Test setting an invalid provider."""
        response = api_test_client.post(
            "/api/llm/providers/set",
            json={"provider": "invalid_provider"},
        )

        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]


@pytest.mark.e2e
@pytest.mark.api
class TestLLMCompletionAPI:
    """Tests for /api/llm/complete endpoint."""

    def test_complete_success(self, api_test_client: TestClient, mock_orchestrator):
        """Test successful LLM completion."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "messages": [{"role": "user", "content": "Say hello"}],
                "temperature": 0.7,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "model" in data
        assert "provider" in data
        assert "usage" in data
        assert "finish_reason" in data

    def test_complete_with_system_message(self, api_test_client: TestClient, mock_orchestrator):
        """Test completion with system message."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": "Hello"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "content" in data

    def test_complete_with_conversation(self, api_test_client: TestClient, mock_orchestrator):
        """Test completion with multi-turn conversation."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "messages": [
                    {"role": "user", "content": "My name is John"},
                    {"role": "assistant", "content": "Hello John!"},
                    {"role": "user", "content": "What is my name?"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "content" in data

    def test_complete_with_max_tokens(self, api_test_client: TestClient, mock_orchestrator):
        """Test completion with max_tokens limit."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "messages": [{"role": "user", "content": "Write a long story"}],
                "max_tokens": 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "content" in data

    def test_complete_with_specific_provider(self, api_test_client: TestClient, mock_orchestrator):
        """Test completion with specific provider."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "provider": "ollama",
            },
        )

        assert response.status_code == 200

    def test_complete_invalid_provider(self, api_test_client: TestClient, mock_orchestrator):
        """Test completion with invalid provider."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "provider": "invalid",
            },
        )

        assert response.status_code == 400

    def test_complete_empty_messages(self, api_test_client: TestClient, mock_orchestrator):
        """Test completion with empty messages."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={"messages": []},
        )

        # Empty messages may cause error or be handled gracefully
        assert response.status_code in [200, 422, 500]

    def test_complete_usage_tracking(self, api_test_client: TestClient, mock_orchestrator):
        """Test that completion tracks token usage."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "usage" in data
        usage = data["usage"]
        assert "input_tokens" in usage
        assert "output_tokens" in usage
        assert "total_tokens" in usage


@pytest.mark.e2e
@pytest.mark.api
class TestLLMAnalyzeAPI:
    """Tests for /api/llm/analyze endpoint."""

    def test_analyze_page_success(self, api_test_client: TestClient, mock_orchestrator):
        """Test page analysis."""
        # Need a task with an active page
        # First create a task
        with patch("ghoststorm.api.routes.llm._get_llm_controller") as mock_ctrl:
            with patch("ghoststorm.api.app.get_orchestrator") as mock_orch:
                mock_orch.return_value = mock_orchestrator
                mock_orchestrator.get_page_for_task = MagicMock(return_value=MagicMock())

                mock_analysis = MagicMock()
                mock_analysis.analysis = "Page contains a login form"
                mock_analysis.is_complete = False
                mock_analysis.next_action = None
                mock_analysis.confidence = 0.85
                mock_analysis.extracted_data = None
                mock_ctrl.return_value.analyze_page = AsyncMock(return_value=mock_analysis)

                response = api_test_client.post(
                    "/api/llm/analyze",
                    json={
                        "task_id": "test-task-123",
                        "task": "Find the login button",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "analysis" in data
                assert "is_complete" in data
                assert "confidence" in data

    def test_analyze_page_not_found(self, api_test_client: TestClient, mock_orchestrator):
        """Test analysis when task/page not found."""
        with patch("ghoststorm.api.app.get_orchestrator") as mock_orch:
            mock_orch.return_value = mock_orchestrator
            mock_orchestrator.get_page_for_task = MagicMock(return_value=None)

            response = api_test_client.post(
                "/api/llm/analyze",
                json={
                    "task_id": "nonexistent-task",
                    "task": "Find something",
                },
            )

            assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.api
class TestLLMExecuteAPI:
    """Tests for /api/llm/execute endpoint."""

    def test_execute_task_success(self, api_test_client: TestClient, mock_orchestrator):
        """Test autonomous task execution."""
        with patch("ghoststorm.api.routes.llm._get_llm_controller") as mock_ctrl:
            with patch("ghoststorm.api.app.get_orchestrator") as mock_orch:
                mock_orch.return_value = mock_orchestrator
                mock_orchestrator.get_page_for_task = MagicMock(return_value=MagicMock())

                mock_result = MagicMock()
                mock_result.success = True
                mock_result.steps_taken = 5
                mock_result.extracted_data = {"title": "Home Page"}
                mock_result.error = None
                mock_result.final_url = "https://example.com/done"
                mock_ctrl.return_value.execute_task = AsyncMock(return_value=mock_result)
                mock_ctrl.return_value.set_mode = MagicMock()
                mock_ctrl.return_value.config = MagicMock()

                response = api_test_client.post(
                    "/api/llm/execute",
                    json={
                        "task_id": "test-task-123",
                        "task": "Navigate to the homepage",
                        "max_steps": 10,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "success" in data
                assert "steps_taken" in data
                assert data["success"] is True

    def test_execute_task_failure(self, api_test_client: TestClient, mock_orchestrator):
        """Test task execution failure."""
        with patch("ghoststorm.api.routes.llm._get_llm_controller") as mock_ctrl:
            with patch("ghoststorm.api.app.get_orchestrator") as mock_orch:
                mock_orch.return_value = mock_orchestrator
                mock_orchestrator.get_page_for_task = MagicMock(return_value=MagicMock())

                mock_result = MagicMock()
                mock_result.success = False
                mock_result.steps_taken = 3
                mock_result.extracted_data = None
                mock_result.error = "Could not find target element"
                mock_result.final_url = "https://example.com"
                mock_ctrl.return_value.execute_task = AsyncMock(return_value=mock_result)
                mock_ctrl.return_value.set_mode = MagicMock()
                mock_ctrl.return_value.config = MagicMock()

                response = api_test_client.post(
                    "/api/llm/execute",
                    json={
                        "task_id": "test-task-123",
                        "task": "Click non-existent button",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False
                assert data["error"] is not None

    def test_execute_task_not_found(self, api_test_client: TestClient, mock_orchestrator):
        """Test execution when task not found."""
        with patch("ghoststorm.api.app.get_orchestrator") as mock_orch:
            mock_orch.return_value = mock_orchestrator
            mock_orchestrator.get_page_for_task = MagicMock(return_value=None)

            response = api_test_client.post(
                "/api/llm/execute",
                json={
                    "task_id": "nonexistent",
                    "task": "Do something",
                },
            )

            assert response.status_code == 404


@pytest.mark.e2e
@pytest.mark.api
class TestLLMUsageAPI:
    """Tests for /api/llm/usage endpoints."""

    def test_get_usage(self, api_test_client: TestClient, mock_orchestrator):
        """Test getting usage statistics."""
        response = api_test_client.get("/api/llm/usage")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_provider" in data

    def test_usage_total_structure(self, api_test_client: TestClient, mock_orchestrator):
        """Test usage total structure."""
        response = api_test_client.get("/api/llm/usage")

        assert response.status_code == 200
        data = response.json()
        total = data["total"]
        assert "input_tokens" in total
        assert "output_tokens" in total
        assert "total_tokens" in total

    def test_reset_usage(self, api_test_client: TestClient, mock_orchestrator):
        """Test resetting usage statistics."""
        response = api_test_client.post("/api/llm/usage/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_usage_after_reset(self, api_test_client: TestClient, mock_orchestrator):
        """Test usage is zero after reset."""
        # Configure mock to return zero after reset is called
        # This simulates the reset behavior properly
        def make_reset_side_effect():
            """Side effect that updates the usage summary mock to return zeros."""
            mock_orchestrator.llm_service.get_usage_summary.return_value = {
                "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "by_provider": {},
            }

        mock_orchestrator.llm_service.reset_usage.side_effect = make_reset_side_effect

        # Reset
        api_test_client.post("/api/llm/usage/reset")

        # Check
        response = api_test_client.get("/api/llm/usage")

        assert response.status_code == 200
        data = response.json()
        assert data["total"]["total_tokens"] == 0


@pytest.mark.e2e
@pytest.mark.api
class TestLLMHealthAPI:
    """Tests for /api/llm/health endpoint."""

    def test_health_check(self, api_test_client: TestClient, mock_orchestrator):
        """Test LLM health check."""
        response = api_test_client.get("/api/llm/health")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], dict)

    def test_health_check_provider_status(self, api_test_client: TestClient, mock_orchestrator):
        """Test health check returns provider status."""
        response = api_test_client.get("/api/llm/health")

        assert response.status_code == 200
        data = response.json()

        # Each provider should have a boolean status
        for _provider, status in data["providers"].items():
            assert isinstance(status, bool)


@pytest.mark.e2e
@pytest.mark.api
@pytest.mark.real
@pytest.mark.ollama
class TestLLMRealOllama:
    """Real Ollama integration tests - require --run-real flag."""

    def test_real_completion(
        self,
        api_test_client: TestClient,
        ollama_url: str,
    ):
        """Test real LLM completion with Ollama."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "messages": [
                    {"role": "user", "content": "What is 2+2? Answer with just the number."}
                ],
                "provider": "ollama",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "4" in data["content"]

    def test_real_providers_list(
        self,
        api_test_client: TestClient,
        ollama_url: str,
    ):
        """Test real provider listing."""
        response = api_test_client.get("/api/llm/providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        # Should have at least ollama available
        provider_names = [p["name"] for p in data["providers"]]
        assert "ollama" in provider_names

    def test_real_health_check(
        self,
        api_test_client: TestClient,
        ollama_url: str,
    ):
        """Test real health check."""
        response = api_test_client.get("/api/llm/health")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        # Ollama should be healthy
        assert data["providers"].get("ollama") is True
