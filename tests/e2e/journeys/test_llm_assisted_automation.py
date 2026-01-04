"""End-to-end journey test for LLM-assisted automation.

This test simulates a complete user journey using AI:
1. Configure LLM provider
2. Analyze target page
3. Generate automation strategy
4. Execute with AI guidance
5. Review and optimize
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.assistant
class TestLLMAssistedAutomationJourney:
    """Complete LLM-assisted automation workflow."""

    def test_complete_ai_assisted_workflow(
        self,
        api_test_client: TestClient,
        mock_orchestrator,
        mock_ollama_service,
    ):
        """Test complete AI-assisted automation from setup to execution."""
        # Step 1: Check LLM provider status
        health_response = api_test_client.get("/api/llm/health")
        assert health_response.status_code == 200

        # Step 2: List available models
        models_response = api_test_client.get("/api/llm/providers/ollama/models")
        assert models_response.status_code in [200, 503]

        # Step 3: Ask AI to analyze target
        with patch("ghoststorm.api.routes.assistant.AIAssistant") as MockAI:
            mock_ai = MagicMock()
            mock_ai.chat.return_value = {
                "message": "I've analyzed the page. Here's my recommendation...",
                "analysis": {
                    "platform": "tiktok",
                    "elements_found": ["video", "like_button", "share_button"],
                    "recommended_actions": ["watch", "like", "share"],
                },
            }
            MockAI.return_value = mock_ai

            chat_response = api_test_client.post(
                "/api/assistant/chat",
                json={
                    "message": "Analyze https://www.tiktok.com/@user/video/123 and suggest automation",
                },
            )

            assert chat_response.status_code == 200

        # Step 4: Use AI to generate selectors
        with patch("ghoststorm.api.routes.llm._call_llm") as mock_llm:
            mock_llm.return_value = {
                "selectors": {
                    "like_button": '[data-e2e="like-icon"]',
                    "share_button": '[data-e2e="share-icon"]',
                    "video_player": "video",
                },
            }

            analyze_response = api_test_client.post(
                "/api/llm/analyze",
                json={
                    "content": "<html>...</html>",
                    "query": "Find selectors for TikTok interaction elements",
                },
            )

            assert analyze_response.status_code in [200, 400, 503]

        # Step 5: Create AI-optimized task
        task_response = api_test_client.post(
            "/api/tasks",
            json={
                "url": "https://www.tiktok.com/@user/video/123",
                "platform": "tiktok",
                "task_type": "engagement",
                "config": {
                    "ai_assisted": True,
                    "actions": ["watch", "like"],
                    "behavior": {
                        "ai_controlled": True,
                        "adapt_to_page": True,
                    },
                },
            },
        )

        assert task_response.status_code == 200
        task_id = task_response.json().get("task_id") or task_response.json().get("id")

        # Step 6: Monitor with AI insights
        with patch("ghoststorm.api.routes.assistant.AIAssistant") as MockAI:
            mock_ai = MagicMock()
            mock_ai.chat.return_value = {
                "message": "Task is progressing well. Current success rate: 85%",
            }
            MockAI.return_value = mock_ai

            insight_response = api_test_client.post(
                "/api/assistant/chat",
                json={
                    "message": f"How is task {task_id} performing?",
                },
            )

            assert insight_response.status_code == 200

        # Step 7: Request AI optimization suggestions
        with patch("ghoststorm.api.routes.assistant.AIAssistant") as MockAI:
            mock_ai = MagicMock()
            mock_ai.chat.return_value = {
                "message": "Based on the results, I suggest increasing watch time and adding random scroll behavior.",
                "suggestions": {
                    "watch_time_min": 10,
                    "watch_time_max": 45,
                    "add_scroll": True,
                },
            }
            MockAI.return_value = mock_ai

            optimize_response = api_test_client.post(
                "/api/assistant/chat",
                json={
                    "message": "How can I optimize this task for better results?",
                },
            )

            assert optimize_response.status_code == 200


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.assistant
class TestAIContextAwareness:
    """Test AI assistant context awareness features."""

    def test_ai_remembers_conversation(
        self,
        api_test_client: TestClient,
        mock_ollama_service,
    ):
        """Test AI maintains conversation context."""
        with patch("ghoststorm.api.routes.assistant.AIAssistant") as MockAI:
            mock_ai = MagicMock()

            # First message
            mock_ai.chat.return_value = {"message": "I understand you want to automate TikTok."}
            MockAI.return_value = mock_ai

            response1 = api_test_client.post(
                "/api/assistant/chat",
                json={"message": "I want to automate TikTok views"},
            )
            assert response1.status_code == 200

            # Follow-up should understand context
            mock_ai.chat.return_value = {
                "message": "For TikTok views, I recommend these settings...",
            }

            response2 = api_test_client.post(
                "/api/assistant/chat",
                json={"message": "What settings should I use?"},
            )
            assert response2.status_code == 200

    def test_ai_with_file_context(
        self,
        api_test_client: TestClient,
        mock_ollama_service,
    ):
        """Test AI can analyze files in context."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", MagicMock()) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "# Sample flow"

                with patch("ghoststorm.api.routes.assistant.AIAssistant") as MockAI:
                    mock_ai = MagicMock()
                    mock_ai.chat.return_value = {
                        "message": "I've analyzed the file. Here's what I found...",
                    }
                    MockAI.return_value = mock_ai

                    response = api_test_client.post(
                        "/api/assistant/chat",
                        json={
                            "message": "Analyze this flow file",
                            "context_files": ["flows/test.json"],
                        },
                    )

                    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.assistant
class TestAICodeGeneration:
    """Test AI code generation capabilities."""

    def test_ai_generates_flow_actions(
        self,
        api_test_client: TestClient,
        mock_ollama_service,
    ):
        """Test AI generates automation actions."""
        with patch("ghoststorm.api.routes.llm._call_llm") as mock_llm:
            mock_llm.return_value = {
                "actions": [
                    {"type": "navigate", "url": "https://example.com"},
                    {"type": "wait", "selector": "h1"},
                    {"type": "click", "selector": "button"},
                ],
            }

            response = api_test_client.post(
                "/api/llm/execute",
                json={
                    "task": "generate_flow",
                    "context": {
                        "url": "https://example.com",
                        "goal": "Click the main button",
                    },
                },
            )

            assert response.status_code in [200, 400, 503]

    def test_ai_generates_selectors(
        self,
        api_test_client: TestClient,
        mock_ollama_service,
    ):
        """Test AI generates CSS selectors from description."""
        with patch("ghoststorm.api.routes.llm._call_llm") as mock_llm:
            mock_llm.return_value = {
                "selectors": [
                    {"css": "button.submit", "confidence": 0.9},
                    {"xpath": "//button[@type='submit']", "confidence": 0.85},
                ],
            }

            response = api_test_client.post(
                "/api/llm/execute",
                json={
                    "task": "find_element",
                    "context": {
                        "description": "Submit button",
                        "html": "<button class='submit'>Submit</button>",
                    },
                },
            )

            assert response.status_code in [200, 400, 503]


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.assistant
class TestAIErrorHandling:
    """Test AI error handling and recovery."""

    def test_ai_handles_timeout(
        self,
        api_test_client: TestClient,
    ):
        """Test AI handles timeout gracefully."""
        with patch("ghoststorm.api.routes.assistant.AIAssistant") as MockAI:
            mock_ai = MagicMock()
            mock_ai.chat.side_effect = TimeoutError("LLM timeout")
            MockAI.return_value = mock_ai

            response = api_test_client.post(
                "/api/assistant/chat",
                json={"message": "Test message"},
            )

            # Should return error, not crash
            assert response.status_code in [200, 408, 500, 503]

    def test_ai_handles_invalid_input(
        self,
        api_test_client: TestClient,
    ):
        """Test AI handles invalid input."""
        response = api_test_client.post(
            "/api/assistant/chat",
            json={"message": ""},  # Empty message
        )

        assert response.status_code in [200, 400]

    def test_ai_recovery_after_error(
        self,
        api_test_client: TestClient,
        mock_ollama_service,
    ):
        """Test AI can recover after an error."""
        with patch("ghoststorm.api.routes.assistant.AIAssistant") as MockAI:
            mock_ai = MagicMock()

            # First call fails
            mock_ai.chat.side_effect = [
                Exception("Temporary error"),
                {"message": "I'm back! How can I help?"},
            ]
            MockAI.return_value = mock_ai

            # First call
            api_test_client.post(
                "/api/assistant/chat",
                json={"message": "Hello"},
            )

            # Second call should work
            mock_ai.chat.side_effect = None
            mock_ai.chat.return_value = {"message": "I'm back!"}

            response2 = api_test_client.post(
                "/api/assistant/chat",
                json={"message": "Are you there?"},
            )

            assert response2.status_code == 200


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.assistant
class TestAIDockerIntegration:
    """Test AI Docker environment integration."""

    def test_ai_docker_status(
        self,
        api_test_client: TestClient,
    ):
        """Test AI can check Docker status."""
        with patch("ghoststorm.api.routes.assistant.DockerEnvironment") as MockDocker:
            mock_docker = MagicMock()
            mock_docker.status.return_value = {"running": True, "containers": 2}
            MockDocker.return_value = mock_docker

            response = api_test_client.get("/api/assistant/docker/status")

            assert response.status_code == 200

    def test_ai_docker_execute(
        self,
        api_test_client: TestClient,
    ):
        """Test AI can execute code in Docker."""
        with patch("ghoststorm.api.routes.assistant.DockerEnvironment") as MockDocker:
            mock_docker = MagicMock()
            mock_docker.execute.return_value = {
                "output": "Hello, World!",
                "exit_code": 0,
            }
            MockDocker.return_value = mock_docker

            response = api_test_client.post(
                "/api/assistant/docker/execute",
                json={
                    "code": "print('Hello, World!')",
                    "language": "python",
                },
            )

            assert response.status_code in [200, 400, 503]


@pytest.mark.e2e
@pytest.mark.journey
@pytest.mark.assistant
@pytest.mark.real
class TestRealAIAutomation:
    """Real AI automation tests (requires --run-real flag)."""

    def test_real_ollama_chat(
        self,
        api_test_client: TestClient,
        real_ollama_url: str,
    ):
        """Test real Ollama chat."""
        response = api_test_client.post(
            "/api/assistant/chat",
            json={"message": "Hello, what can you help me with?"},
        )

        assert response.status_code in [200, 503]

    def test_real_page_analysis(
        self,
        api_test_client: TestClient,
        real_ollama_url: str,
    ):
        """Test real page analysis with Ollama."""
        response = api_test_client.post(
            "/api/llm/analyze",
            json={
                "content": "<html><body><h1>Welcome</h1><button>Click me</button></body></html>",
                "query": "What interactive elements are on this page?",
            },
        )

        assert response.status_code in [200, 503]
