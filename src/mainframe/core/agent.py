"""Agent loop — the core turn-based execution engine."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from mainframe.core.events import (
    AfterToolCall,
    AgentThinking,
    BeforeToolCall,
    EventBus,
    TextDelta,
    TokenUsage,
    TurnComplete,
)
from mainframe.core.session import Session
from mainframe.providers.base import (
    ContentBlock,
    Message,
    Provider,
    Role,
    StopReason,
    StreamEvent,
)
from mainframe.tools.base import ToolContext
from mainframe.tools.policy import ToolPolicy
from mainframe.tools.registry import ToolRegistry


class AgentLoop:
    """Drives the conversation loop between user input and provider responses.

    Supports multi-turn tool execution: the agent calls tools, feeds results
    back to the provider, and continues until it produces a final text response.
    """

    def __init__(
        self,
        provider: Provider,
        session: Session,
        tool_registry: ToolRegistry | None = None,
        tool_policy: ToolPolicy | None = None,
        system_prompt: str = "",
        max_tokens: int = 4096,
        max_iterations: int = 20,
        workspace_dir: Path | None = None,
        event_bus: EventBus | None = None,
    ):
        self._provider = provider
        self._session = session
        self._tool_registry = tool_registry
        self._tool_policy = tool_policy or ToolPolicy.allow_all()
        self._system_prompt = system_prompt
        self._max_tokens = max_tokens
        self._max_iterations = max_iterations
        self._workspace_dir = workspace_dir or Path.cwd()
        self._event_bus = event_bus or EventBus()

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def session(self) -> Session:
        return self._session

    def _make_tool_context(self) -> ToolContext:
        return ToolContext(
            session_id=self._session.session_id,
            workspace_dir=self._workspace_dir,
            provider=self._provider,
        )

    async def submit(self, user_input: str) -> None:
        """Add user message to the session."""
        self._session.add_message(Message(role=Role.USER, content=user_input))

    async def submit_message(self, message: Message) -> None:
        """Add a pre-built message to the session (supports multimodal content)."""
        self._session.add_message(message)

    async def run(self) -> AsyncIterator[StreamEvent]:
        """Execute the agent loop, yielding stream events.

        Uses streaming for text output. When tool calls are needed,
        falls back to non-streaming complete() for reliable tool call parsing,
        then switches back to streaming for the next text response.
        """
        tool_defs = self._tool_registry.to_definitions() if self._tool_registry else None

        for _iteration in range(self._max_iterations):
            await self._event_bus.emit(AgentThinking())

            # Use complete() to get structured tool calls reliably
            result = await self._provider.complete(
                messages=self._session.messages,
                tools=tool_defs,
                system=self._system_prompt,
                max_tokens=self._max_tokens,
            )

            # Persist the assistant message
            self._session.add_message(result.message)

            # Emit text content as deltas
            if isinstance(result.message.content, list):
                for block in result.message.content:
                    if block.type == "text" and block.text:
                        await self._event_bus.emit(TextDelta(text=block.text))
                        yield StreamEvent(type="text_delta", text=block.text)
            elif isinstance(result.message.content, str) and result.message.content:
                await self._event_bus.emit(TextDelta(text=result.message.content))
                yield StreamEvent(type="text_delta", text=result.message.content)

            # Emit usage
            if result.usage:
                yield StreamEvent(
                    type="message_stop",
                    stop_reason=result.stop_reason,
                    usage=result.usage,
                )
                await self._event_bus.emit(TokenUsage(
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                ))

            # If no tool calls, we're done
            if result.stop_reason != StopReason.TOOL_USE or not result.tool_calls:
                break

            # Execute tool calls
            tool_result_blocks: list[ContentBlock] = []
            ctx = self._make_tool_context()

            for call in result.tool_calls:
                await self._event_bus.emit(BeforeToolCall(
                    tool_name=call.name,
                    tool_input=call.input,
                    call_id=call.id,
                ))

                if not self._tool_policy.is_allowed(call.name):
                    content = f"Tool '{call.name}' is not permitted by current policy."
                    is_error = True
                elif self._tool_registry is None:
                    content = "No tool registry configured."
                    is_error = True
                else:
                    tool_result = await self._tool_registry.execute(
                        call.name, call.input, ctx
                    )
                    content = tool_result.content
                    is_error = tool_result.is_error

                tool_result_blocks.append(ContentBlock(
                    type="tool_result",
                    tool_call_id=call.id,
                    text=content,
                    is_error=is_error,
                ))

                await self._event_bus.emit(AfterToolCall(
                    tool_name=call.name,
                    call_id=call.id,
                    result_content=content,
                    is_error=is_error,
                ))

                # Yield tool events so CLI can display them
                yield StreamEvent(
                    type="tool_result",
                    text=f"[{call.name}] {'ERROR: ' if is_error else ''}{content}",
                    tool_call=call,
                )

            # Add tool results as a user message (Anthropic format)
            self._session.add_message(Message(
                role=Role.USER,
                content=tool_result_blocks,
            ))

        await self._event_bus.emit(TurnComplete(
            turn_number=self._session.meta.turn_count,
        ))

    async def complete(self, user_input: str) -> str:
        """Convenience: submit + run, return full text response."""
        await self.submit(user_input)
        text_parts = []
        async for event in self.run():
            if event.type == "text_delta" and event.text:
                text_parts.append(event.text)
        return "".join(text_parts)
