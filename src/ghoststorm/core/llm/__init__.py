"""LLM integration module for AI-powered browser control."""

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
from ghoststorm.core.llm.service import LLMService, LLMServiceConfig, ProviderType
from ghoststorm.core.llm.vision import (
    BaseVisionProvider,
    VisionAnalysis,
    VisionConfig,
    VisionDetailLevel,
    VisionMode,
)

__all__ = [
    # Base
    "BaseLLM",
    "LLMConfig",
    "ProviderInfo",
    # Messages
    "Message",
    "MessageRole",
    "SystemMessage",
    "UserMessage",
    "AssistantMessage",
    "LLMResponse",
    "LLMUsage",
    "Conversation",
    # Service
    "LLMService",
    "LLMServiceConfig",
    "ProviderType",
    # Controller
    "LLMController",
    "ControllerConfig",
    "ControllerMode",
    "ActionType",
    "BrowserAction",
    "PageAnalysis",
    "TaskResult",
    "StepResult",
    # Vision
    "BaseVisionProvider",
    "VisionAnalysis",
    "VisionConfig",
    "VisionDetailLevel",
    "VisionMode",
]
