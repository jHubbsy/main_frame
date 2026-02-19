"""Anthropic Claude provider implementation."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import anthropic

from mainframe.core.errors import AuthenticationError, ProviderError, RateLimitError
from mainframe.providers.base import (
    CompletionResult,
    ContentBlock,
    Message,
    Role,
    StopReason,
    StreamEvent,
    ToolCall,
    ToolDefinition,
    Usage,
)


def _to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert internal messages to Anthropic API format."""
    result = []
    for msg in messages:
        if msg.role == Role.SYSTEM:
            continue  # system goes in a separate param

        if isinstance(msg.content, str):
            result.append({"role": msg.role.value, "content": msg.content})
        else:
            blocks = []
            for block in msg.content:
                if block.type == "text" and block.text:
                    blocks.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    blocks.append({
                        "type": "tool_use",
                        "id": block.tool_call_id,
                        "name": block.tool_name,
                        "input": block.tool_input or {},
                    })
                elif block.type == "tool_result":
                    blocks.append({
                        "type": "tool_result",
                        "tool_use_id": block.tool_call_id,
                        "content": block.text or "",
                        "is_error": block.is_error,
                    })
            if blocks:
                result.append({"role": msg.role.value, "content": blocks})

    return result


def _to_anthropic_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Convert tool definitions to Anthropic format."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in tools
    ]


def _parse_stop_reason(reason: str) -> StopReason:
    mapping = {
        "end_turn": StopReason.END_TURN,
        "tool_use": StopReason.TOOL_USE,
        "max_tokens": StopReason.MAX_TOKENS,
        "stop_sequence": StopReason.STOP_SEQUENCE,
    }
    return mapping.get(reason, StopReason.END_TURN)


class AnthropicProvider:
    """Claude provider via the Anthropic SDK."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> CompletionResult:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": _to_anthropic_messages(messages),
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = _to_anthropic_tools(tools)

        try:
            response = await self._client.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise AuthenticationError(str(e)) from e
        except anthropic.RateLimitError as e:
            raise RateLimitError(str(e)) from e
        except anthropic.APIError as e:
            raise ProviderError(str(e)) from e

        # Parse response
        content_blocks: list[ContentBlock] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                content_blocks.append(ContentBlock(type="text", text=block.text))
            elif block.type == "tool_use":
                content_blocks.append(ContentBlock(
                    type="tool_use",
                    tool_call_id=block.id,
                    tool_name=block.name,
                    tool_input=block.input,
                ))
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))

        return CompletionResult(
            message=Message(role=Role.ASSISTANT, content=content_blocks),
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            stop_reason=_parse_stop_reason(response.stop_reason),
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": _to_anthropic_messages(messages),
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = _to_anthropic_tools(tools)

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield StreamEvent(type="text_delta", text=event.delta.text)
                        elif event.delta.type == "input_json_delta":
                            yield StreamEvent(
                                type="tool_call_delta",
                                text=event.delta.partial_json,
                            )
                    elif event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            yield StreamEvent(
                                type="tool_call_start",
                                tool_call=ToolCall(
                                    id=event.content_block.id,
                                    name=event.content_block.name,
                                    input={},
                                ),
                            )
                    elif event.type == "message_stop":
                        final = stream.get_final_message()
                        yield StreamEvent(
                            type="message_stop",
                            stop_reason=_parse_stop_reason(final.stop_reason),
                            usage=Usage(
                                input_tokens=final.usage.input_tokens,
                                output_tokens=final.usage.output_tokens,
                            ),
                        )
        except anthropic.AuthenticationError as e:
            raise AuthenticationError(str(e)) from e
        except anthropic.RateLimitError as e:
            raise RateLimitError(str(e)) from e
        except anthropic.APIError as e:
            raise ProviderError(str(e)) from e
