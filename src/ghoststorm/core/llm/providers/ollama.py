"""Ollama LLM provider for local models."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import structlog

from ghoststorm.core.llm.base import BaseLLM, LLMConfig
from ghoststorm.core.llm.messages import LLMResponse, LLMUsage, Message
from ghoststorm.core.llm.vision import (
    BaseVisionProvider,
    VisionAnalysis,
    VisionDetailLevel,
    encode_screenshot,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class OllamaProvider(BaseLLM, BaseVisionProvider):
    """
    Ollama provider for local LLM models.

    Supports various open-source models running locally via Ollama.
    Includes vision support for multimodal models like LLaVA and Qwen-VL.
    """

    DEFAULT_MODEL = "llama3"
    DEFAULT_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    SUPPORTED_MODELS = [
        "llama3",
        "llama3:70b",
        "mistral",
        "mixtral",
        "codellama",
        "phi3",
        "gemma",
        "qwen",
    ]

    # Vision-capable models
    VISION_MODELS = [
        "qwen3-vl",
        "qwen3-vl:2b",
        "qwen3-vl:8b",
        "qwen3-vl:32b",
        "qwen2.5vl",
        "qwen2.5vl:7b",
        "qwen2.5vl:32b",
        "llava",
        "llava:7b",
        "llava:13b",
        "llava:34b",
        "llava-phi3",
        "llava-llama3",
        "moondream",
        "minicpm-v",
        "llama3.2-vision",
        "llama3.2-vision:11b",
        "bakllava",
        "gemma3",
    ]

    def __init__(self, config: LLMConfig) -> None:
        """
        Initialize Ollama provider.

        Args:
            config: Provider configuration (base_url is the Ollama host)
        """
        super().__init__(config)

        if not config.model:
            config.model = self.DEFAULT_MODEL

        if not config.base_url:
            config.base_url = self.DEFAULT_HOST

        self._http_client = None

    @property
    def provider(self) -> str:
        """Get provider name."""
        return "ollama"

    def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            try:
                import httpx
            except ImportError:
                raise ImportError(
                    "httpx library not installed. Install with: pip install httpx"
                )

            self._http_client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )

        return self._http_client

    async def complete(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate completion using Ollama API."""
        client = self._get_client()

        # Convert messages to Ollama format
        ollama_messages = [m.to_ollama() for m in messages]

        try:
            payload: dict[str, Any] = {
                "model": self.config.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": temperature or self.config.temperature,
                },
            }

            if max_tokens or self.config.max_tokens:
                payload["options"]["num_predict"] = max_tokens or self.config.max_tokens

            if stop:
                payload["options"]["stop"] = stop

            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()

            data = response.json()

            # Extract content
            content = data.get("message", {}).get("content", "")

            # Build usage (Ollama provides eval_count and prompt_eval_count)
            usage = LLMUsage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            )

            self._update_usage(usage)

            return LLMResponse(
                content=content,
                model=data.get("model", self.config.model),
                usage=usage,
                finish_reason=data.get("done_reason", "stop"),
                raw_response=data,
            )

        except Exception as e:
            logger.error("Ollama API error", error=str(e))
            raise

    async def stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion tokens."""
        client = self._get_client()

        ollama_messages = [m.to_ollama() for m in messages]

        try:
            payload: dict[str, Any] = {
                "model": self.config.model,
                "messages": ollama_messages,
                "stream": True,
                "options": {
                    "temperature": temperature or self.config.temperature,
                },
            }

            if max_tokens or self.config.max_tokens:
                payload["options"]["num_predict"] = max_tokens or self.config.max_tokens

            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        import json

                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]

        except Exception as e:
            logger.error("Ollama streaming error", error=str(e))
            raise

    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        client = self._get_client()

        try:
            response = await client.get("/api/tags")
            response.raise_for_status()

            data = response.json()
            return [m["name"] for m in data.get("models", [])]

        except Exception as e:
            logger.error("Failed to list Ollama models", error=str(e))
            return []

    async def health_check(self) -> bool:
        """Check if Ollama server is running."""
        client = self._get_client()

        try:
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    # =========================================================================
    # Vision Provider Implementation
    # =========================================================================

    @property
    def supports_vision(self) -> bool:
        """Check if current model supports vision."""
        model = self.config.model.lower()
        return any(vm in model for vm in [
            "llava", "qwen3-vl", "qwen2.5vl", "moondream",
            "minicpm-v", "vision", "bakllava", "gemma3"
        ])

    @property
    def vision_models(self) -> list[str]:
        """List of vision-capable models."""
        return self.VISION_MODELS

    async def analyze_screenshot(
        self,
        screenshot: bytes,
        prompt: str,
        detail_level: VisionDetailLevel = VisionDetailLevel.AUTO,
    ) -> VisionAnalysis:
        """
        Analyze a screenshot using Ollama vision model.

        Args:
            screenshot: PNG/JPEG screenshot bytes
            prompt: What to analyze/look for
            detail_level: Level of detail for analysis

        Returns:
            Vision analysis result
        """
        if not self.supports_vision:
            raise ValueError(
                f"Model {self.config.model} does not support vision. "
                f"Use one of: {', '.join(self.VISION_MODELS[:5])}..."
            )

        client = self._get_client()

        # Encode screenshot to base64
        image_base64 = encode_screenshot(screenshot)

        try:
            # Ollama vision API format
            payload: dict[str, Any] = {
                "model": self.config.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_base64],
                    }
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temp for accurate analysis
                },
            }

            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()

            data = response.json()
            content = data.get("message", {}).get("content", "")

            # Try to parse JSON response
            analysis = self._parse_vision_response(content)

            logger.debug(
                "Vision analysis complete",
                model=self.config.model,
                response_length=len(content),
            )

            return analysis

        except Exception as e:
            logger.error("Ollama vision error", error=str(e))
            raise

    async def complete_with_vision(
        self,
        messages: list[Message],
        screenshot: bytes,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Generate completion with screenshot context.

        Args:
            messages: Conversation messages
            screenshot: Screenshot to include
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            LLM response
        """
        if not self.supports_vision:
            raise ValueError(f"Model {self.config.model} does not support vision")

        client = self._get_client()

        # Encode screenshot
        image_base64 = encode_screenshot(screenshot)

        # Convert messages, adding image to last user message
        ollama_messages = []
        for i, msg in enumerate(messages):
            msg_dict = msg.to_ollama()

            # Add image to last user message
            if i == len(messages) - 1 and msg_dict["role"] == "user":
                msg_dict["images"] = [image_base64]

            ollama_messages.append(msg_dict)

        try:
            payload: dict[str, Any] = {
                "model": self.config.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": temperature or self.config.temperature,
                },
            }

            if max_tokens or self.config.max_tokens:
                payload["options"]["num_predict"] = max_tokens or self.config.max_tokens

            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()

            data = response.json()
            content = data.get("message", {}).get("content", "")

            usage = LLMUsage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            )

            self._update_usage(usage)

            return LLMResponse(
                content=content,
                model=data.get("model", self.config.model),
                usage=usage,
                finish_reason=data.get("done_reason", "stop"),
                raw_response=data,
            )

        except Exception as e:
            logger.error("Ollama vision completion error", error=str(e))
            raise

    def _parse_vision_response(self, content: str) -> VisionAnalysis:
        """Parse vision model response into VisionAnalysis."""
        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            data = json.loads(content)

            # Parse coordinates if present
            coords = None
            if "coordinates" in data and data["coordinates"]:
                coords = tuple(data["coordinates"][:2])
            elif "suggested_action" in data and data["suggested_action"]:
                action = data["suggested_action"]
                if "coordinates" in action and action["coordinates"]:
                    coords = tuple(action["coordinates"][:2])

            return VisionAnalysis(
                description=data.get("description", content),
                elements=data.get("elements", []),
                suggested_action=data.get("suggested_action"),
                coordinates=coords,
                confidence=data.get("confidence", 0.5),
                raw_response=content,
            )

        except (json.JSONDecodeError, KeyError, TypeError):
            # Return raw description if not JSON
            return VisionAnalysis(
                description=content,
                elements=[],
                suggested_action=None,
                coordinates=None,
                confidence=0.5,
                raw_response=content,
            )
