"""Typed event bus for decoupled component communication."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    """Base event class."""

    type: str


@dataclass
class AgentThinking(Event):
    type: str = field(default="agent_thinking", init=False)


@dataclass
class TextDelta(Event):
    text: str = ""
    type: str = field(default="text_delta", init=False)


@dataclass
class TokenUsage(Event):
    input_tokens: int = 0
    output_tokens: int = 0
    type: str = field(default="token_usage", init=False)


@dataclass
class BeforeToolCall(Event):
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)
    call_id: str = ""
    type: str = field(default="before_tool_call", init=False)


@dataclass
class AfterToolCall(Event):
    tool_name: str = ""
    call_id: str = ""
    result_content: str = ""
    is_error: bool = False
    type: str = field(default="after_tool_call", init=False)


@dataclass
class TurnComplete(Event):
    turn_number: int = 0
    type: str = field(default="turn_complete", init=False)


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Simple async event bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].remove(handler)

    async def emit(self, event: Event) -> None:
        for handler in self._handlers.get(event.type, []):
            await handler(event)
        # Also fire wildcard handlers
        for handler in self._handlers.get("*", []):
            await handler(event)
