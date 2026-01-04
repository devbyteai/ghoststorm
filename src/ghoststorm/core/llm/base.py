"""Base LLM protocol and types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, TypeVar

from ghoststorm.core.llm.messages import LLMResponse, LLMUsage, Message


T = TypeVar("T")


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    api_key: str = ""
    model: str = ""
    base_url: str | None = None
    timeout: float = 60.0
    max_retries: int = 3
    temperature: float = 0.2
    max_tokens: int | None = None
    top_p: float = 1.0

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (excludes API key)."""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }


class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers must implement this interface.
    """

    def __init__(self, config: LLMConfig) -> None:
        """
        Initialize LLM provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self._total_usage = LLMUsage()

    @property
    @abstractmethod
    def provider(self) -> str:
        """Get provider name (e.g., 'openai', 'anthropic')."""
        pass

    @property
    def model(self) -> str:
        """Get model name."""
        return self.config.model

    @property
    def total_usage(self) -> LLMUsage:
        """Get cumulative usage across all requests."""
        return self._total_usage

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """
        Generate a completion for the given messages.

        Args:
            messages: List of messages in the conversation
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Stop sequences

        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream a completion token by token.

        Args:
            messages: List of messages in the conversation
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Yields:
            String tokens as they are generated
        """
        pass

    async def complete_with_retry(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Complete with automatic retry on failure.

        Args:
            messages: List of messages
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            LLMResponse
        """
        import asyncio

        last_error: Exception | None = None

        for attempt in range(self.config.max_retries):
            try:
                return await self.complete(messages, temperature, max_tokens)
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2**attempt)

        raise last_error or RuntimeError("Max retries exceeded")

    def _update_usage(self, usage: LLMUsage) -> None:
        """Update cumulative usage statistics."""
        self._total_usage.input_tokens += usage.input_tokens
        self._total_usage.output_tokens += usage.output_tokens
        self._total_usage.total_tokens += usage.total_tokens

    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible.

        Returns:
            True if provider is working
        """
        try:
            from ghoststorm.core.llm.messages import UserMessage

            # Simple test message
            response = await self.complete(
                [UserMessage("Say 'ok'")],
                max_tokens=10,
            )
            return len(response.content) > 0
        except Exception:
            return False

    def reset_usage(self) -> None:
        """Reset cumulative usage statistics."""
        self._total_usage = LLMUsage()


@dataclass
class ProviderInfo:
    """Information about an LLM provider."""

    name: str
    provider_class: type[BaseLLM]
    default_model: str
    supported_models: list[str] = field(default_factory=list)
    requires_api_key: bool = True
    supports_streaming: bool = True
    supports_tools: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "default_model": self.default_model,
            "supported_models": self.supported_models,
            "requires_api_key": self.requires_api_key,
            "supports_streaming": self.supports_streaming,
            "supports_tools": self.supports_tools,
        }
