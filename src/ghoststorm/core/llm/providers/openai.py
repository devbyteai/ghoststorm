"""OpenAI LLM provider."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import structlog

from ghoststorm.core.llm.base import BaseLLM, LLMConfig
from ghoststorm.core.llm.messages import LLMResponse, LLMUsage, Message
from ghoststorm.core.llm.vision import (
    BaseVisionProvider,
    VisionAnalysis,
    VisionDetailLevel,
    encode_screenshot,
    get_image_media_type,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    pass

logger = structlog.get_logger(__name__)


class OpenAIProvider(BaseLLM, BaseVisionProvider):
    """
    OpenAI API provider.

    Supports GPT-4, GPT-4o, GPT-3.5-turbo, and other OpenAI models.
    Includes vision support for GPT-4o and GPT-4-turbo.
    """

    DEFAULT_MODEL = "gpt-4o"

    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ]

    # Vision-capable models
    VISION_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4-vision-preview",
    ]

    def __init__(self, config: LLMConfig) -> None:
        """
        Initialize OpenAI provider.

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
        return "openai"

    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError("OpenAI library not installed. Install with: pip install openai")

            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=0,  # We handle retries ourselves
            )

        return self._client

    async def complete(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate completion using OpenAI API."""
        client = self._get_client()

        # Convert messages to OpenAI format
        openai_messages = [m.to_openai() for m in messages]

        try:
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=openai_messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                top_p=self.config.top_p,
                stop=stop,
            )

            # Extract content
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason or "stop"

            # Extract tool calls if present
            tool_calls = []
            if response.choices[0].message.tool_calls:
                for tc in response.choices[0].message.tool_calls:
                    tool_calls.append(
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                    )

            # Build usage
            usage = LLMUsage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )

            self._update_usage(usage)

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=finish_reason,
                tool_calls=tool_calls,
                raw_response=response,
            )

        except Exception as e:
            logger.error("OpenAI API error", error=str(e))
            raise

    async def stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion tokens."""
        client = self._get_client()

        openai_messages = [m.to_openai() for m in messages]

        try:
            stream = await client.chat.completions.create(
                model=self.config.model,
                messages=openai_messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error("OpenAI streaming error", error=str(e))
            raise

    # =========================================================================
    # Vision Provider Implementation
    # =========================================================================

    @property
    def supports_vision(self) -> bool:
        """Check if current model supports vision."""
        model = self.config.model.lower()
        return any(vm in model for vm in ["gpt-4o", "gpt-4-turbo", "gpt-4-vision"])

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
        Analyze a screenshot using OpenAI vision model.

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
                f"Use one of: {', '.join(self.VISION_MODELS)}"
            )

        client = self._get_client()

        # Encode screenshot
        image_base64 = encode_screenshot(screenshot)
        media_type = get_image_media_type(screenshot)

        # Map detail level
        detail = "auto"
        if detail_level == VisionDetailLevel.LOW:
            detail = "low"
        elif detail_level == VisionDetailLevel.HIGH:
            detail = "high"

        try:
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_base64}",
                                    "detail": detail,
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=1024,
            )

            content = response.choices[0].message.content or ""
            analysis = self._parse_vision_response(content)

            logger.debug(
                "OpenAI vision analysis complete",
                model=self.config.model,
                response_length=len(content),
            )

            return analysis

        except Exception as e:
            logger.error("OpenAI vision error", error=str(e))
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

        # Convert messages, adding image to last user message
        openai_messages = []
        for i, msg in enumerate(messages):
            if i == len(messages) - 1 and msg.role.value == "user":
                # Add image to last user message
                openai_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": msg.content},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_base64}",
                                    "detail": "auto",
                                },
                            },
                        ],
                    }
                )
            else:
                openai_messages.append(msg.to_openai())

        try:
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=openai_messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens or 1024,
            )

            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason or "stop"

            usage = LLMUsage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )

            self._update_usage(usage)

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=finish_reason,
                raw_response=response,
            )

        except Exception as e:
            logger.error("OpenAI vision completion error", error=str(e))
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
            if data.get("coordinates"):
                coords = tuple(data["coordinates"][:2])
            elif data.get("suggested_action"):
                action = data["suggested_action"]
                if action.get("coordinates"):
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
