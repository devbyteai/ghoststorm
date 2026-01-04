"""Anthropic LLM provider."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import structlog

from ghoststorm.core.llm.base import BaseLLM, LLMConfig
from ghoststorm.core.llm.messages import LLMResponse, LLMUsage, Message, MessageRole
from ghoststorm.core.llm.vision import (
    BaseVisionProvider,
    VisionAnalysis,
    VisionDetailLevel,
    encode_screenshot,
    get_image_media_type,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class AnthropicProvider(BaseLLM, BaseVisionProvider):
    """
    Anthropic API provider.

    Supports Claude 3.5 Sonnet, Claude 3 Opus, and other Claude models.
    All Claude 3+ models support vision.
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    SUPPORTED_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    # All Claude 3+ models support vision
    VISION_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, config: LLMConfig) -> None:
        """
        Initialize Anthropic provider.

        Args:
            config: Provider configuration with API key
        """
        super().__init__(config)

        if not config.model:
            config.model = self.DEFAULT_MODEL

        self._client = None

    @property
    def provider(self) -> str:
        """Get provider name."""
        return "anthropic"

    def _get_client(self):
        """Get or create Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ImportError(
                    "Anthropic library not installed. Install with: pip install anthropic"
                )

            self._client = AsyncAnthropic(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=0,
            )

        return self._client

    async def complete(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate completion using Anthropic API."""
        client = self._get_client()

        # Extract system message
        system_content = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_content = msg.content
            else:
                anthropic_messages.append(msg.to_anthropic())

        try:
            kwargs = {
                "model": self.config.model,
                "messages": anthropic_messages,
                "temperature": temperature or self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens or 4096,
            }

            if system_content:
                kwargs["system"] = system_content

            if stop:
                kwargs["stop_sequences"] = stop

            response = await client.messages.create(**kwargs)

            # Extract content
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            # Build usage
            usage = LLMUsage(
                input_tokens=response.usage.input_tokens if response.usage else 0,
                output_tokens=response.usage.output_tokens if response.usage else 0,
                total_tokens=(
                    (response.usage.input_tokens + response.usage.output_tokens)
                    if response.usage
                    else 0
                ),
            )

            self._update_usage(usage)

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=response.stop_reason or "end_turn",
                raw_response=response,
            )

        except Exception as e:
            logger.error("Anthropic API error", error=str(e))
            raise

    async def stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion tokens."""
        client = self._get_client()

        # Extract system message
        system_content = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_content = msg.content
            else:
                anthropic_messages.append(msg.to_anthropic())

        try:
            kwargs = {
                "model": self.config.model,
                "messages": anthropic_messages,
                "temperature": temperature or self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens or 4096,
            }

            if system_content:
                kwargs["system"] = system_content

            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error("Anthropic streaming error", error=str(e))
            raise

    # =========================================================================
    # Vision Provider Implementation
    # =========================================================================

    @property
    def supports_vision(self) -> bool:
        """Check if current model supports vision. All Claude 3+ models do."""
        model = self.config.model.lower()
        return "claude-3" in model or "claude-sonnet-4" in model or "claude-opus-4" in model

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
        Analyze a screenshot using Claude vision.

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
                f"Use a Claude 3+ model."
            )

        client = self._get_client()

        # Encode screenshot
        image_base64 = encode_screenshot(screenshot)
        media_type = get_image_media_type(screenshot)

        try:
            response = await client.messages.create(
                model=self.config.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            analysis = self._parse_vision_response(content)

            logger.debug(
                "Anthropic vision analysis complete",
                model=self.config.model,
                response_length=len(content),
            )

            return analysis

        except Exception as e:
            logger.error("Anthropic vision error", error=str(e))
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
        media_type = get_image_media_type(screenshot)

        # Extract system message and build Anthropic messages
        system_content = None
        anthropic_messages = []

        for i, msg in enumerate(messages):
            if msg.role == MessageRole.SYSTEM:
                system_content = msg.content
            elif i == len(messages) - 1 and msg.role == MessageRole.USER:
                # Add image to last user message
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": msg.content,
                        },
                    ],
                })
            else:
                anthropic_messages.append(msg.to_anthropic())

        try:
            kwargs: dict[str, Any] = {
                "model": self.config.model,
                "messages": anthropic_messages,
                "temperature": temperature or self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens or 1024,
            }

            if system_content:
                kwargs["system"] = system_content

            response = await client.messages.create(**kwargs)

            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            usage = LLMUsage(
                input_tokens=response.usage.input_tokens if response.usage else 0,
                output_tokens=response.usage.output_tokens if response.usage else 0,
                total_tokens=(
                    (response.usage.input_tokens + response.usage.output_tokens)
                    if response.usage
                    else 0
                ),
            )

            self._update_usage(usage)

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=response.stop_reason or "end_turn",
                raw_response=response,
            )

        except Exception as e:
            logger.error("Anthropic vision completion error", error=str(e))
            raise

    def _parse_vision_response(self, content: str) -> VisionAnalysis:
        """Parse vision model response into VisionAnalysis."""
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
            return VisionAnalysis(
                description=content,
                elements=[],
                suggested_action=None,
                coordinates=None,
                confidence=0.5,
                raw_response=content,
            )
