"""LLM Service - orchestrates LLM providers."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

from ghoststorm.core.llm.base import BaseLLM, LLMConfig, ProviderInfo
from ghoststorm.core.llm.messages import LLMResponse, LLMUsage, Message

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


@dataclass
class LLMServiceConfig:
    """Configuration for LLM service."""

    default_provider: ProviderType = ProviderType.OLLAMA

    # Provider-specific configs
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str | None = None

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_base_url: str | None = None

    ollama_host: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    ollama_model: str = "llama3"

    # Shared settings
    temperature: float = 0.2
    max_tokens: int | None = None
    timeout: float = 60.0
    max_retries: int = 3

    def get_provider_config(self, provider: ProviderType) -> LLMConfig:
        """Get LLMConfig for a specific provider."""
        if provider == ProviderType.OPENAI:
            return LLMConfig(
                api_key=self.openai_api_key,
                model=self.openai_model,
                base_url=self.openai_base_url,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        elif provider == ProviderType.ANTHROPIC:
            return LLMConfig(
                api_key=self.anthropic_api_key,
                model=self.anthropic_model,
                base_url=self.anthropic_base_url,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        elif provider == ProviderType.OLLAMA:
            return LLMConfig(
                api_key="",  # Ollama doesn't need API key
                model=self.ollama_model,
                base_url=self.ollama_host,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")


class LLMService:
    """
    Service that manages LLM providers and provides a unified interface.

    Supports lazy loading of providers and provider switching.
    """

    def __init__(self, config: LLMServiceConfig) -> None:
        """
        Initialize LLM service.

        Args:
            config: Service configuration
        """
        self.config = config
        self._providers: dict[ProviderType, BaseLLM] = {}
        self._current_provider: ProviderType = config.default_provider
        self._total_usage = LLMUsage()

    @property
    def current_provider(self) -> ProviderType:
        """Get current active provider type."""
        return self._current_provider

    @property
    def total_usage(self) -> LLMUsage:
        """Get cumulative usage across all providers."""
        return self._total_usage

    def _get_provider(self, provider_type: ProviderType) -> BaseLLM:
        """Get or create a provider instance."""
        if provider_type not in self._providers:
            self._providers[provider_type] = self._create_provider(provider_type)
        return self._providers[provider_type]

    def _create_provider(self, provider_type: ProviderType) -> BaseLLM:
        """Create a new provider instance."""
        config = self.config.get_provider_config(provider_type)

        if provider_type == ProviderType.OPENAI:
            from ghoststorm.core.llm.providers.openai import OpenAIProvider

            return OpenAIProvider(config)
        elif provider_type == ProviderType.ANTHROPIC:
            from ghoststorm.core.llm.providers.anthropic import AnthropicProvider

            return AnthropicProvider(config)
        elif provider_type == ProviderType.OLLAMA:
            from ghoststorm.core.llm.providers.ollama import OllamaProvider

            return OllamaProvider(config)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def set_provider(self, provider_type: ProviderType) -> None:
        """
        Set the active provider.

        Args:
            provider_type: Provider to activate
        """
        self._current_provider = provider_type
        logger.info("LLM provider changed", provider=provider_type.value)

    def get_provider(self, provider_type: ProviderType | None = None) -> BaseLLM:
        """
        Get a provider instance.

        Args:
            provider_type: Specific provider or None for current

        Returns:
            Provider instance
        """
        ptype = provider_type or self._current_provider
        return self._get_provider(ptype)

    async def complete(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        provider: ProviderType | None = None,
    ) -> LLMResponse:
        """
        Generate completion using the specified or current provider.

        Args:
            messages: Conversation messages
            temperature: Override temperature
            max_tokens: Override max tokens
            stop: Stop sequences
            provider: Specific provider or None for current

        Returns:
            LLM response
        """
        llm = self.get_provider(provider)

        try:
            response = await llm.complete(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
            )

            # Update service-level usage
            self._update_usage(response.usage)

            logger.debug(
                "LLM completion",
                provider=llm.provider,
                model=llm.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            return response

        except Exception as e:
            logger.error(
                "LLM completion error",
                provider=llm.provider,
                model=llm.model,
                error=str(e),
            )
            raise

    async def complete_with_retry(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: ProviderType | None = None,
    ) -> LLMResponse:
        """
        Generate completion with automatic retry.

        Args:
            messages: Conversation messages
            temperature: Override temperature
            max_tokens: Override max tokens
            provider: Specific provider or None for current

        Returns:
            LLM response
        """
        llm = self.get_provider(provider)
        response = await llm.complete_with_retry(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._update_usage(response.usage)
        return response

    async def stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: ProviderType | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream completion tokens.

        Args:
            messages: Conversation messages
            temperature: Override temperature
            max_tokens: Override max tokens
            provider: Specific provider or None for current

        Yields:
            Tokens as they are generated
        """
        llm = self.get_provider(provider)

        try:
            async for token in llm.stream(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield token
        except Exception as e:
            logger.error(
                "LLM streaming error",
                provider=llm.provider,
                model=llm.model,
                error=str(e),
            )
            raise

    async def health_check(self, provider: ProviderType | None = None) -> bool:
        """
        Check if a provider is healthy.

        Args:
            provider: Specific provider or None for current

        Returns:
            True if provider is working
        """
        llm = self.get_provider(provider)
        return await llm.health_check()

    async def health_check_all(self) -> dict[ProviderType, bool]:
        """
        Check health of all configured providers.

        Returns:
            Dict mapping provider to health status
        """
        results = {}

        for provider_type in ProviderType:
            try:
                # Check if provider has required config
                if provider_type == ProviderType.OPENAI and not self.config.openai_api_key:
                    results[provider_type] = False
                    continue
                if provider_type == ProviderType.ANTHROPIC and not self.config.anthropic_api_key:
                    results[provider_type] = False
                    continue

                results[provider_type] = await self.health_check(provider_type)
            except Exception:
                results[provider_type] = False

        return results

    def list_providers(self) -> list[ProviderInfo]:
        """
        List all available providers with their info.

        Returns:
            List of provider info
        """
        from ghoststorm.core.llm.providers.anthropic import AnthropicProvider
        from ghoststorm.core.llm.providers.ollama import OllamaProvider
        from ghoststorm.core.llm.providers.openai import OpenAIProvider

        providers = [
            ProviderInfo(
                name="openai",
                provider_class=OpenAIProvider,
                default_model=OpenAIProvider.DEFAULT_MODEL,
                supported_models=OpenAIProvider.SUPPORTED_MODELS,
                requires_api_key=True,
                supports_streaming=True,
                supports_tools=True,
            ),
            ProviderInfo(
                name="anthropic",
                provider_class=AnthropicProvider,
                default_model=AnthropicProvider.DEFAULT_MODEL,
                supported_models=AnthropicProvider.SUPPORTED_MODELS,
                requires_api_key=True,
                supports_streaming=True,
                supports_tools=True,
            ),
            ProviderInfo(
                name="ollama",
                provider_class=OllamaProvider,
                default_model=OllamaProvider.DEFAULT_MODEL,
                supported_models=OllamaProvider.SUPPORTED_MODELS,
                requires_api_key=False,
                supports_streaming=True,
                supports_tools=False,
            ),
        ]

        return providers

    def get_provider_info(self, provider_type: ProviderType) -> ProviderInfo | None:
        """
        Get info for a specific provider.

        Args:
            provider_type: Provider to get info for

        Returns:
            Provider info or None
        """
        providers = self.list_providers()
        for info in providers:
            if info.name == provider_type.value:
                return info
        return None

    def _update_usage(self, usage: LLMUsage) -> None:
        """Update cumulative usage statistics."""
        self._total_usage.input_tokens += usage.input_tokens
        self._total_usage.output_tokens += usage.output_tokens
        self._total_usage.total_tokens += usage.total_tokens

    def reset_usage(self) -> None:
        """Reset cumulative usage statistics."""
        self._total_usage = LLMUsage()

    def get_usage_summary(self) -> dict[str, Any]:
        """
        Get usage summary including per-provider stats.

        Returns:
            Usage summary dict
        """
        summary = {
            "total": {
                "input_tokens": self._total_usage.input_tokens,
                "output_tokens": self._total_usage.output_tokens,
                "total_tokens": self._total_usage.total_tokens,
            },
            "by_provider": {},
        }

        for provider_type, provider in self._providers.items():
            usage = provider.total_usage
            summary["by_provider"][provider_type.value] = {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
            }

        return summary
