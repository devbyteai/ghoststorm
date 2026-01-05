"""Tests for LLM module."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from ghoststorm.core.llm.base import BaseLLM, LLMConfig, ProviderInfo
from ghoststorm.core.llm.controller import (
    ActionType,
    BrowserAction,
    ControllerConfig,
    ControllerMode,
    LLMController,
    PageAnalysis,
    StepResult,
    TaskResult,
)
from ghoststorm.core.llm.messages import (
    AssistantMessage,
    Conversation,
    LLMResponse,
    LLMUsage,
    Message,
    MessageRole,
    SystemMessage,
    UserMessage,
)
from ghoststorm.core.llm.prompts import (
    BROWSER_AGENT_SYSTEM_PROMPT,
    build_analysis_prompt,
    build_captcha_prompt,
    build_element_finder_prompt,
    build_error_recovery_prompt,
    build_extraction_prompt,
)
from ghoststorm.core.llm.service import LLMService, LLMServiceConfig, ProviderType

# ============================================================================
# Message Tests
# ============================================================================


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_role_values(self):
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"


class TestMessage:
    """Tests for Message class."""

    def test_create_message(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"

    def test_to_openai(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        openai_format = msg.to_openai()
        assert openai_format == {"role": "user", "content": "Hello"}

    def test_to_anthropic_user(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        anthropic_format = msg.to_anthropic()
        assert anthropic_format == {"role": "user", "content": "Hello"}

    def test_to_anthropic_assistant(self):
        msg = Message(role=MessageRole.ASSISTANT, content="Hi there")
        anthropic_format = msg.to_anthropic()
        assert anthropic_format == {"role": "assistant", "content": "Hi there"}

    def test_to_ollama(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        ollama_format = msg.to_ollama()
        assert ollama_format == {"role": "user", "content": "Hello"}


class TestMessageHelpers:
    """Tests for message helper classes."""

    def test_system_message(self):
        msg = SystemMessage("You are helpful")
        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "You are helpful"

    def test_user_message(self):
        msg = UserMessage("Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"

    def test_assistant_message(self):
        msg = AssistantMessage("Hi there")
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Hi there"


class TestConversation:
    """Tests for Conversation class."""

    def test_empty_conversation(self):
        conv = Conversation()
        assert len(conv.messages) == 0

    def test_add_system(self):
        conv = Conversation()
        conv.add_system("You are helpful")
        assert len(conv.messages) == 1
        assert conv.messages[0].role == MessageRole.SYSTEM

    def test_add_user(self):
        conv = Conversation()
        conv.add_user("Hello")
        assert len(conv.messages) == 1
        assert conv.messages[0].role == MessageRole.USER

    def test_add_assistant(self):
        conv = Conversation()
        conv.add_assistant("Hi")
        assert len(conv.messages) == 1
        assert conv.messages[0].role == MessageRole.ASSISTANT

    def test_add_multiple_messages(self):
        conv = Conversation()
        conv.add_user("User message")
        conv.add_assistant("Assistant response")
        assert len(conv.messages) == 2
        assert conv.messages[0].role == MessageRole.USER
        assert conv.messages[1].role == MessageRole.ASSISTANT

    def test_clear(self):
        conv = Conversation()
        conv.add_user("Hello")
        conv.add_assistant("Hi")
        conv.clear()
        assert len(conv.messages) == 0

    def test_to_openai(self):
        conv = Conversation()
        conv.add_system("System")
        conv.add_user("User")
        openai_format = conv.to_openai()
        assert len(openai_format) == 2
        assert openai_format[0]["role"] == "system"
        assert openai_format[1]["role"] == "user"


class TestLLMUsage:
    """Tests for LLMUsage class."""

    def test_default_values(self):
        usage = LLMUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0

    def test_custom_values(self):
        usage = LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150


class TestLLMResponse:
    """Tests for LLMResponse class."""

    def test_create_response(self):
        usage = LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30)
        response = LLMResponse(
            content="Hello",
            model="gpt-4o",
            usage=usage,
            finish_reason="stop",
        )
        assert response.content == "Hello"
        assert response.model == "gpt-4o"
        assert response.usage.total_tokens == 30
        assert response.finish_reason == "stop"

    def test_default_values(self):
        usage = LLMUsage()
        response = LLMResponse(content="Test", model="test", usage=usage)
        assert response.finish_reason == "stop"
        assert response.tool_calls == []  # Default is empty list
        assert response.raw_response is None


# ============================================================================
# Base LLM Tests
# ============================================================================


class TestLLMConfig:
    """Tests for LLMConfig class."""

    def test_default_config(self):
        config = LLMConfig()
        assert config.api_key == ""
        assert config.model == ""
        assert config.temperature == 0.2
        assert config.timeout == 60.0
        assert config.max_retries == 3

    def test_custom_config(self):
        config = LLMConfig(
            api_key="test-key",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=1000,
        )
        assert config.api_key == "test-key"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000

    def test_to_dict_excludes_api_key(self):
        config = LLMConfig(api_key="secret", model="gpt-4o")
        d = config.to_dict()
        assert "api_key" not in d
        assert d["model"] == "gpt-4o"


class TestProviderInfo:
    """Tests for ProviderInfo class."""

    def test_create_provider_info(self):
        info = ProviderInfo(
            name="openai",
            provider_class=BaseLLM,
            default_model="gpt-4o",
            supported_models=["gpt-4o", "gpt-4"],
            requires_api_key=True,
            supports_streaming=True,
        )
        assert info.name == "openai"
        assert info.default_model == "gpt-4o"
        assert "gpt-4o" in info.supported_models

    def test_to_dict(self):
        info = ProviderInfo(
            name="test",
            provider_class=BaseLLM,
            default_model="model",
        )
        d = info.to_dict()
        assert d["name"] == "test"
        assert d["default_model"] == "model"
        assert "provider_class" not in d


# ============================================================================
# Service Tests
# ============================================================================


class TestLLMServiceConfig:
    """Tests for LLMServiceConfig class."""

    def test_default_config(self):
        config = LLMServiceConfig()
        assert config.default_provider == ProviderType.OLLAMA
        assert config.openai_model == "gpt-4o"
        assert config.anthropic_model == "claude-sonnet-4-20250514"
        assert config.ollama_model == "llama3"

    def test_get_provider_config_openai(self):
        config = LLMServiceConfig(openai_api_key="test-key", openai_model="gpt-4")
        llm_config = config.get_provider_config(ProviderType.OPENAI)
        assert llm_config.api_key == "test-key"
        assert llm_config.model == "gpt-4"

    def test_get_provider_config_anthropic(self):
        config = LLMServiceConfig(anthropic_api_key="test-key")
        llm_config = config.get_provider_config(ProviderType.ANTHROPIC)
        assert llm_config.api_key == "test-key"

    def test_get_provider_config_ollama(self):
        config = LLMServiceConfig(ollama_host="http://custom:11434")
        llm_config = config.get_provider_config(ProviderType.OLLAMA)
        assert llm_config.base_url == "http://custom:11434"
        assert llm_config.api_key == ""  # Ollama doesn't need API key


class TestLLMService:
    """Tests for LLMService class."""

    def test_create_service(self):
        config = LLMServiceConfig()
        service = LLMService(config)
        assert service.current_provider == ProviderType.OLLAMA

    def test_set_provider(self):
        config = LLMServiceConfig()
        service = LLMService(config)
        service.set_provider(ProviderType.ANTHROPIC)
        assert service.current_provider == ProviderType.ANTHROPIC

    def test_list_providers(self):
        config = LLMServiceConfig()
        service = LLMService(config)
        providers = service.list_providers()
        assert len(providers) == 3
        names = [p.name for p in providers]
        assert "openai" in names
        assert "anthropic" in names
        assert "ollama" in names

    def test_get_provider_info(self):
        config = LLMServiceConfig()
        service = LLMService(config)
        info = service.get_provider_info(ProviderType.OPENAI)
        assert info is not None
        assert info.name == "openai"

    def test_reset_usage(self):
        config = LLMServiceConfig()
        service = LLMService(config)
        service._total_usage.input_tokens = 100
        service.reset_usage()
        assert service.total_usage.input_tokens == 0

    def test_get_usage_summary(self):
        config = LLMServiceConfig()
        service = LLMService(config)
        summary = service.get_usage_summary()
        assert "total" in summary
        assert "by_provider" in summary


# ============================================================================
# Controller Tests
# ============================================================================


class TestBrowserAction:
    """Tests for BrowserAction model."""

    def test_click_action(self):
        action = BrowserAction(
            type=ActionType.CLICK,
            selector="#button",
            reason="Click submit button",
        )
        assert action.type == ActionType.CLICK
        assert action.selector == "#button"

    def test_type_action(self):
        action = BrowserAction(
            type=ActionType.TYPE,
            selector="#input",
            value="hello",
            reason="Type text",
        )
        assert action.type == ActionType.TYPE
        assert action.value == "hello"

    def test_navigate_action(self):
        action = BrowserAction(
            type=ActionType.NAVIGATE,
            url="https://example.com",
            reason="Navigate",
        )
        assert action.type == ActionType.NAVIGATE
        assert action.url == "https://example.com"


class TestPageAnalysis:
    """Tests for PageAnalysis model."""

    def test_complete_analysis(self):
        analysis = PageAnalysis(
            analysis="Task complete",
            is_complete=True,
            next_action=None,
            confidence=1.0,
            extracted_data={"result": "success"},
        )
        assert analysis.is_complete
        assert analysis.extracted_data["result"] == "success"

    def test_analysis_with_action(self):
        action = BrowserAction(type=ActionType.CLICK, selector="#btn", reason="test")
        analysis = PageAnalysis(
            analysis="Click button",
            is_complete=False,
            next_action=action,
            confidence=0.9,
        )
        assert not analysis.is_complete
        assert analysis.next_action.type == ActionType.CLICK


class TestTaskResult:
    """Tests for TaskResult model."""

    def test_success_result(self):
        result = TaskResult(
            success=True,
            steps_taken=5,
            extracted_data={"data": "value"},
            final_url="https://example.com/done",
        )
        assert result.success
        assert result.steps_taken == 5
        assert result.error is None

    def test_failure_result(self):
        result = TaskResult(
            success=False,
            steps_taken=3,
            error="Element not found",
        )
        assert not result.success
        assert result.error == "Element not found"


class TestControllerConfig:
    """Tests for ControllerConfig."""

    def test_default_config(self):
        config = ControllerConfig()
        assert config.mode == ControllerMode.ASSIST
        assert config.max_steps == 20
        assert config.min_confidence == 0.5

    def test_custom_config(self):
        config = ControllerConfig(
            mode=ControllerMode.AUTONOMOUS,
            max_steps=50,
            min_confidence=0.8,
        )
        assert config.mode == ControllerMode.AUTONOMOUS
        assert config.max_steps == 50


class TestLLMController:
    """Tests for LLMController."""

    @pytest.fixture
    def mock_llm_service(self):
        service = MagicMock(spec=LLMService)
        service.complete = AsyncMock()
        return service

    @pytest.fixture
    def controller(self, mock_llm_service):
        return LLMController(llm_service=mock_llm_service)

    def test_create_controller(self, controller):
        assert controller.mode == ControllerMode.ASSIST

    def test_set_mode(self, controller):
        controller.set_mode(ControllerMode.AUTONOMOUS)
        assert controller.mode == ControllerMode.AUTONOMOUS

    def test_reset(self, controller):
        controller._step_history.append(StepResult(step_number=1, action=None, success=True))
        controller.reset()
        assert len(controller._step_history) == 0

    def test_get_step_history(self, controller):
        result = StepResult(step_number=1, action=None, success=True)
        controller._step_history.append(result)
        history = controller.get_step_history()
        assert len(history) == 1
        assert history is not controller._step_history  # Returns list copy

    def test_parse_analysis_valid_json(self, controller):
        content = json.dumps(
            {
                "analysis": "Test page",
                "is_complete": False,
                "next_action": {
                    "type": "click",
                    "selector": "#btn",
                    "reason": "Click button",
                },
                "confidence": 0.9,
            }
        )
        analysis = controller._parse_analysis(content)
        assert analysis.analysis == "Test page"
        assert not analysis.is_complete
        assert analysis.next_action.type == ActionType.CLICK

    def test_parse_analysis_with_markdown(self, controller):
        content = """```json
{
    "analysis": "Test",
    "is_complete": true,
    "confidence": 1.0
}
```"""
        analysis = controller._parse_analysis(content)
        assert analysis.is_complete

    def test_parse_analysis_invalid_json(self, controller):
        content = "This is not JSON"
        analysis = controller._parse_analysis(content)
        assert analysis.confidence == 0.0
        assert "Failed to parse" in analysis.analysis

    @pytest.mark.asyncio
    async def test_execute_task_not_autonomous(self, controller):
        mock_page = MagicMock()
        with pytest.raises(ValueError, match="not in autonomous mode"):
            await controller.execute_task(mock_page, "Test task")


# ============================================================================
# Prompt Tests
# ============================================================================


class TestPrompts:
    """Tests for prompt builders."""

    def test_browser_system_prompt_exists(self):
        assert len(BROWSER_AGENT_SYSTEM_PROMPT) > 0
        assert "web automation" in BROWSER_AGENT_SYSTEM_PROMPT.lower()

    def test_build_analysis_prompt(self):
        prompt = build_analysis_prompt(
            task="Click login button",
            url="https://example.com",
            dom_state="<button>Login</button>",
        )
        assert "Click login button" in prompt
        assert "https://example.com" in prompt
        assert "Login" in prompt

    def test_build_element_finder_prompt(self):
        prompt = build_element_finder_prompt(
            description="submit button",
            elements="[button#submit, button.primary]",
        )
        assert "submit button" in prompt
        assert "button#submit" in prompt

    def test_build_error_recovery_prompt(self):
        prompt = build_error_recovery_prompt(
            error="Element not found",
            action='{"type": "click"}',
            url="https://example.com",
        )
        assert "Element not found" in prompt
        assert "click" in prompt

    def test_build_extraction_prompt(self):
        prompt = build_extraction_prompt(
            target="product prices",
            dom_state="<div class='price'>$99</div>",
        )
        assert "product prices" in prompt
        assert "$99" in prompt

    def test_build_captcha_prompt(self):
        prompt = build_captcha_prompt(
            dom_state="<div class='g-recaptcha'>CAPTCHA</div>",
        )
        assert "recaptcha" in prompt.lower()


# ============================================================================
# Provider Tests (Mock-based)
# ============================================================================


class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    def test_create_provider(self):
        from ghoststorm.core.llm.providers.openai import OpenAIProvider

        config = LLMConfig(api_key="test-key", model="gpt-4o")
        provider = OpenAIProvider(config)
        assert provider.provider == "openai"
        assert provider.model == "gpt-4o"

    def test_default_model(self):
        from ghoststorm.core.llm.providers.openai import OpenAIProvider

        config = LLMConfig(api_key="test-key")
        provider = OpenAIProvider(config)
        assert provider.model == OpenAIProvider.DEFAULT_MODEL


class TestAnthropicProvider:
    """Tests for Anthropic provider."""

    def test_create_provider(self):
        from ghoststorm.core.llm.providers.anthropic import AnthropicProvider

        config = LLMConfig(api_key="test-key", model="claude-sonnet-4-20250514")
        provider = AnthropicProvider(config)
        assert provider.provider == "anthropic"

    def test_default_model(self):
        from ghoststorm.core.llm.providers.anthropic import AnthropicProvider

        config = LLMConfig(api_key="test-key")
        provider = AnthropicProvider(config)
        assert provider.model == AnthropicProvider.DEFAULT_MODEL


class TestOllamaProvider:
    """Tests for Ollama provider."""

    def test_create_provider(self):
        from ghoststorm.core.llm.providers.ollama import OllamaProvider

        config = LLMConfig(model="llama3")
        provider = OllamaProvider(config)
        assert provider.provider == "ollama"
        assert provider.model == "llama3"

    def test_default_host(self):
        from ghoststorm.core.llm.providers.ollama import OllamaProvider

        config = LLMConfig()
        provider = OllamaProvider(config)
        assert provider.config.base_url == OllamaProvider.DEFAULT_HOST


# ============================================================================
# Integration Tests (with mocks)
# ============================================================================


class TestLLMIntegration:
    """Integration tests with mocked providers."""

    @pytest.fixture
    def service_config(self):
        return LLMServiceConfig(
            openai_api_key="test-openai-key",
            anthropic_api_key="test-anthropic-key",
        )

    def test_service_creates_providers_lazily(self, service_config):
        service = LLMService(service_config)
        # Providers should not be created until needed
        assert len(service._providers) == 0

    def test_service_creates_provider_on_access(self, service_config):
        service = LLMService(service_config)
        provider = service.get_provider(ProviderType.OPENAI)
        assert provider is not None
        assert ProviderType.OPENAI in service._providers

    def test_service_caches_providers(self, service_config):
        service = LLMService(service_config)
        provider1 = service.get_provider(ProviderType.OPENAI)
        provider2 = service.get_provider(ProviderType.OPENAI)
        assert provider1 is provider2

    @pytest.mark.asyncio
    async def test_controller_with_mock_service(self):
        # Create mock service
        mock_service = MagicMock(spec=LLMService)
        mock_response = LLMResponse(
            content=json.dumps(
                {
                    "analysis": "Page loaded",
                    "is_complete": True,
                    "confidence": 1.0,
                }
            ),
            model="test",
            usage=LLMUsage(),
        )
        mock_service.complete = AsyncMock(return_value=mock_response)

        # Create controller
        controller = LLMController(llm_service=mock_service)
        controller.set_mode(ControllerMode.AUTONOMOUS)

        # Create mock page
        mock_page = MagicMock()
        mock_page.url = AsyncMock(return_value="https://example.com")
        mock_page.title = AsyncMock(return_value="Test Page")

        # Execute
        result = await controller.execute_task(mock_page, "Test task")

        assert result.success
        assert result.steps_taken == 1
