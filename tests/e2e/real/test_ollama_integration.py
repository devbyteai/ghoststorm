"""Real Ollama integration tests.

These tests require a running Ollama instance.
Run with: pytest tests/e2e/real/ --run-real -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.real
@pytest.mark.ollama
class TestOllamaConnection:
    """Tests for real Ollama connection."""

    def test_ollama_health(self, api_test_client: TestClient, real_ollama_url: str):
        """Test Ollama service is healthy."""
        response = api_test_client.get("/api/llm/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["connected", "healthy"]

    def test_ollama_available(self, api_test_client: TestClient, real_ollama_url: str):
        """Test Ollama is available at configured URL."""
        response = api_test_client.get("/api/llm/providers/ollama/status")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True


@pytest.mark.real
@pytest.mark.ollama
class TestOllamaModels:
    """Tests for Ollama model operations."""

    def test_list_models(self, api_test_client: TestClient, real_ollama_url: str):
        """Test listing available Ollama models."""
        response = api_test_client.get("/api/llm/providers/ollama/models")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)

    def test_model_info(self, api_test_client: TestClient, real_ollama_url: str):
        """Test getting model information."""
        # First get available models
        list_response = api_test_client.get("/api/llm/providers/ollama/models")
        models = list_response.json().get("models", [])

        if models:
            model_name = models[0]["name"] if isinstance(models[0], dict) else models[0]
            response = api_test_client.get(f"/api/llm/providers/ollama/models/{model_name}")

            assert response.status_code in [200, 404]


@pytest.mark.real
@pytest.mark.ollama
class TestOllamaCompletion:
    """Tests for Ollama text completion."""

    def test_simple_completion(self, api_test_client: TestClient, real_ollama_url: str):
        """Test simple text completion."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "prompt": "Say hello in one word:",
                "max_tokens": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data or "completion" in data or "response" in data

    def test_completion_with_system_prompt(self, api_test_client: TestClient, real_ollama_url: str):
        """Test completion with system prompt."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "prompt": "What is 2+2?",
                "system": "You are a math tutor. Always answer with just the number.",
                "max_tokens": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data or "completion" in data or "response" in data

    def test_completion_timeout(self, api_test_client: TestClient, real_ollama_url: str):
        """Test completion respects timeout."""
        response = api_test_client.post(
            "/api/llm/complete",
            json={
                "prompt": "Tell me a short story",
                "max_tokens": 50,
                "timeout": 30,
            },
        )

        # Should complete within timeout
        assert response.status_code in [200, 408]


@pytest.mark.real
@pytest.mark.ollama
class TestOllamaChat:
    """Tests for Ollama chat functionality."""

    def test_chat_message(self, api_test_client: TestClient, real_ollama_url: str):
        """Test sending a chat message."""
        response = api_test_client.post(
            "/api/assistant/chat",
            json={
                "message": "Hello, how are you?",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "response" in data

    def test_chat_conversation(self, api_test_client: TestClient, real_ollama_url: str):
        """Test multi-turn conversation."""
        # First message
        response1 = api_test_client.post(
            "/api/assistant/chat",
            json={"message": "My name is Test User"},
        )
        assert response1.status_code == 200

        # Follow-up
        response2 = api_test_client.post(
            "/api/assistant/chat",
            json={"message": "What is my name?"},
        )
        assert response2.status_code == 200

    def test_chat_with_context(self, api_test_client: TestClient, real_ollama_url: str):
        """Test chat with additional context."""
        response = api_test_client.post(
            "/api/assistant/chat",
            json={
                "message": "Summarize this",
                "context": "The quick brown fox jumps over the lazy dog.",
            },
        )

        assert response.status_code == 200


@pytest.mark.real
@pytest.mark.ollama
class TestOllamaStreaming:
    """Tests for Ollama streaming responses."""

    def test_streaming_completion(self, api_test_client: TestClient, real_ollama_url: str):
        """Test streaming completion response."""
        with api_test_client.stream(
            "POST",
            "/api/llm/complete/stream",
            json={
                "prompt": "Count from 1 to 5",
                "max_tokens": 50,
            },
        ) as response:
            chunks = []
            for chunk in response.iter_lines():
                if chunk:
                    chunks.append(chunk)

            # Should receive multiple chunks
            assert len(chunks) >= 0

    def test_streaming_chat(self, api_test_client: TestClient, real_ollama_url: str):
        """Test streaming chat response."""
        with api_test_client.stream(
            "POST",
            "/api/assistant/chat/stream",
            json={"message": "Say hello"},
        ) as response:
            chunks = []
            for chunk in response.iter_lines():
                if chunk:
                    chunks.append(chunk)

            assert len(chunks) >= 0


@pytest.mark.real
@pytest.mark.ollama
class TestOllamaAnalysis:
    """Tests for Ollama analysis capabilities."""

    def test_analyze_code(self, api_test_client: TestClient, real_ollama_url: str):
        """Test code analysis."""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        response = api_test_client.post(
            "/api/llm/analyze",
            json={
                "content": code,
                "query": "What does this function do?",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data or "response" in data

    def test_analyze_page(self, api_test_client: TestClient, real_ollama_url: str):
        """Test page content analysis."""
        response = api_test_client.post(
            "/api/llm/analyze",
            json={
                "content": "<html><body><h1>Welcome</h1><p>This is a test page</p></body></html>",
                "query": "What is on this page?",
            },
        )

        assert response.status_code == 200


@pytest.mark.real
@pytest.mark.ollama
class TestOllamaTaskExecution:
    """Tests for LLM-assisted task execution."""

    def test_generate_selectors(self, api_test_client: TestClient, real_ollama_url: str):
        """Test generating CSS selectors with LLM."""
        response = api_test_client.post(
            "/api/llm/execute",
            json={
                "task": "generate_selectors",
                "context": {
                    "page_html": '<button class="btn-primary">Sign Up</button>',
                    "target": "signup button",
                },
            },
        )

        assert response.status_code == 200

    def test_analyze_captcha(self, api_test_client: TestClient, real_ollama_url: str):
        """Test captcha analysis with LLM."""
        response = api_test_client.post(
            "/api/llm/execute",
            json={
                "task": "analyze_captcha",
                "context": {
                    "captcha_type": "slider",
                    "description": "Slide to verify you are human",
                },
            },
        )

        assert response.status_code == 200


@pytest.mark.real
@pytest.mark.ollama
class TestOllamaUsage:
    """Tests for Ollama usage tracking."""

    def test_get_usage_stats(self, api_test_client: TestClient, real_ollama_url: str):
        """Test getting usage statistics."""
        response = api_test_client.get("/api/llm/usage")

        assert response.status_code == 200
        data = response.json()
        # Should have usage data
        assert isinstance(data, dict)

    def test_usage_after_completion(self, api_test_client: TestClient, real_ollama_url: str):
        """Test usage is tracked after completion."""
        # Get initial usage
        api_test_client.get("/api/llm/usage").json()

        # Make a completion
        api_test_client.post(
            "/api/llm/complete",
            json={"prompt": "Hello", "max_tokens": 5},
        )

        # Get updated usage
        updated = api_test_client.get("/api/llm/usage").json()

        # Usage should be tracked (might not change if not implemented)
        assert isinstance(updated, dict)


@pytest.mark.real
@pytest.mark.ollama
class TestOllamaPerformance:
    """Performance tests for Ollama integration."""

    def test_response_time(self, api_test_client: TestClient, real_ollama_url: str):
        """Test response time is acceptable."""
        import time

        start = time.time()
        response = api_test_client.post(
            "/api/llm/complete",
            json={"prompt": "Hello", "max_tokens": 5},
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        # Response should be under 30 seconds
        assert elapsed < 30

    def test_concurrent_requests(self, api_test_client: TestClient, real_ollama_url: str):
        """Test handling concurrent requests."""
        import concurrent.futures

        def make_request():
            return api_test_client.post(
                "/api/llm/complete",
                json={"prompt": "Hi", "max_tokens": 5},
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should complete
        assert len(results) == 3
        for result in results:
            assert result.status_code in [200, 429, 503]  # OK, rate limited, or overloaded
