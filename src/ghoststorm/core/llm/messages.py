"""Message types for LLM communication."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    """Message roles in conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """Base message class."""

    role: MessageRole
    content: str
    name: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_openai(self) -> dict[str, Any]:
        """Convert to OpenAI API format."""
        msg = {"role": self.role.value, "content": self.content}
        if self.name:
            msg["name"] = self.name
        return msg

    def to_anthropic(self) -> dict[str, Any]:
        """Convert to Anthropic API format."""
        return {"role": self.role.value, "content": self.content}

    def to_ollama(self) -> dict[str, Any]:
        """Convert to Ollama API format."""
        return {"role": self.role.value, "content": self.content}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role.value,
            "content": self.content,
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SystemMessage(Message):
    """System message for setting context."""

    def __init__(self, content: str, name: str | None = None) -> None:
        super().__init__(role=MessageRole.SYSTEM, content=content, name=name)


@dataclass
class UserMessage(Message):
    """User message."""

    def __init__(self, content: str, name: str | None = None) -> None:
        super().__init__(role=MessageRole.USER, content=content, name=name)


@dataclass
class AssistantMessage(Message):
    """Assistant response message."""

    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def __init__(
        self,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(role=MessageRole.ASSISTANT, content=content, name=name)
        self.tool_calls = tool_calls or []


@dataclass
class ToolMessage(Message):
    """Tool/function result message."""

    tool_call_id: str = ""

    def __init__(
        self,
        content: str,
        tool_call_id: str,
        name: str | None = None,
    ) -> None:
        super().__init__(role=MessageRole.TOOL, content=content, name=name)
        self.tool_call_id = tool_call_id

    def to_openai(self) -> dict[str, Any]:
        """Convert to OpenAI API format."""
        return {
            "role": "tool",
            "content": self.content,
            "tool_call_id": self.tool_call_id,
        }


@dataclass
class LLMUsage:
    """Token usage information."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    @property
    def estimated_cost(self) -> float:
        """Estimate cost in USD (rough approximation)."""
        # Rough estimate: $0.002 per 1K input, $0.006 per 1K output
        input_cost = (self.input_tokens / 1000) * 0.002
        output_cost = (self.output_tokens / 1000) * 0.006
        return input_cost + output_cost

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost,
        }


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    finish_reason: str = "stop"
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw_response: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage.to_dict(),
            "finish_reason": self.finish_reason,
            "tool_calls": self.tool_calls,
        }


@dataclass
class Conversation:
    """Conversation history manager."""

    messages: list[Message] = field(default_factory=list)
    max_messages: int = 100

    def add(self, message: Message) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)

        # Trim if over limit (keep system messages)
        if len(self.messages) > self.max_messages:
            system_msgs = [m for m in self.messages if m.role == MessageRole.SYSTEM]
            other_msgs = [m for m in self.messages if m.role != MessageRole.SYSTEM]

            # Keep system messages and last N non-system messages
            keep_count = self.max_messages - len(system_msgs)
            self.messages = system_msgs + other_msgs[-keep_count:]

    def add_user(self, content: str) -> None:
        """Add a user message."""
        self.add(UserMessage(content))

    def add_assistant(self, content: str) -> None:
        """Add an assistant message."""
        self.add(AssistantMessage(content))

    def add_system(self, content: str) -> None:
        """Add a system message."""
        self.add(SystemMessage(content))

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def to_openai(self) -> list[dict[str, Any]]:
        """Convert to OpenAI format."""
        return [m.to_openai() for m in self.messages]

    def to_anthropic(self) -> list[dict[str, Any]]:
        """Convert to Anthropic format (excludes system)."""
        return [m.to_anthropic() for m in self.messages if m.role != MessageRole.SYSTEM]

    def get_system_prompt(self) -> str | None:
        """Get combined system prompt."""
        system_msgs = [m for m in self.messages if m.role == MessageRole.SYSTEM]
        if system_msgs:
            return "\n\n".join(m.content for m in system_msgs)
        return None

    def to_dict(self) -> list[dict[str, Any]]:
        """Convert to list of dictionaries."""
        return [m.to_dict() for m in self.messages]
