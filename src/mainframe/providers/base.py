"""Provider protocol and shared types for LLM abstraction."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ContentBlock:
    """A single content block within a message."""

    type: str  # "text", "tool_use", "tool_result", "image"
    text: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    is_error: bool = False
    # Image fields
    image_data: str | None = None  # base64 encoded image data
    image_mime_type: str | None = None  # MIME type (e.g., "image/png")


@dataclass
class Message:
    role: Role
    content: str | list[ContentBlock]
    tool_call_id: str | None = None

    @property
    def text(self) -> str:
        if isinstance(self.content, str):
            return self.content
        parts = [b.text for b in self.content if b.text]
        return "\n".join(parts)


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


class StopReason(StrEnum):
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"


@dataclass
class CompletionResult:
    message: Message
    usage: Usage
    stop_reason: StopReason
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class StreamEvent:
    """A single event from a streaming response."""

    type: str  # "text_delta", "tool_call_start", "tool_call_delta", "message_stop", etc.
    text: str | None = None
    tool_call: ToolCall | None = None
    stop_reason: StopReason | None = None
    usage: Usage | None = None


@dataclass
class ToolDefinition:
    """Tool definition passed to the provider."""

    name: str
    description: str
    input_schema: dict[str, Any]


@runtime_checkable
class Provider(Protocol):
    """Protocol for LLM providers."""

    name: str

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> CompletionResult: ...

    async def stream(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]: ...
