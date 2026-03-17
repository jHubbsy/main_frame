"""Single-shot prompt execution."""

from __future__ import annotations

import anyio
import click

from mainframe.cli.display import (
    console,
    print_assistant_text,
    print_error,
    print_tool_call,
    print_tool_result,
    print_usage,
)
from mainframe.config.loader import load_config
from mainframe.core.agent import AgentLoop
from mainframe.core.session import Session
from mainframe.providers.registry import create_provider
from mainframe.tools.builtins import register_builtins
from mainframe.tools.policy import ToolPolicy
from mainframe.tools.registry import ToolRegistry


@click.command()
@click.argument("prompt")
@click.option("--model", default=None, help="Override the model.")
@click.option("--raw", is_flag=True, help="Output raw text without formatting.")
@click.option("--no-tools", is_flag=True, help="Disable tool use.")
def run(prompt: str, model: str | None, raw: bool, no_tools: bool) -> None:
    """Run a single prompt and exit."""
    async def _execute() -> None:
        await _run(prompt, model_override=model, raw=raw, no_tools=no_tools)
    anyio.run(_execute)


async def _run(
    prompt: str,
    model_override: str | None = None,
    raw: bool = False,
    no_tools: bool = False,
) -> None:
    config = load_config()
    if model_override:
        config.provider.model = model_override

    try:
        provider = create_provider(config.provider)
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1) from e

    tool_registry = None
    tool_policy = None
    if not no_tools:
        tool_registry = ToolRegistry()
        register_builtins(tool_registry)
        tool_policy = ToolPolicy.from_groups(config.security.allowed_tool_groups)

    session = Session()
    agent = AgentLoop(
        provider=provider,
        session=session,
        tool_registry=tool_registry,
        tool_policy=tool_policy,
        system_prompt=config.system_prompt,
        max_tokens=config.provider.max_tokens,
    )

    try:
        if raw:
            response = await agent.complete(prompt)
            click.echo(response)
        else:
            await agent.submit(prompt)
            async for event in agent.run():
                if event.type == "text_delta" and event.text:
                    print_assistant_text(event.text, streaming=True)
                elif event.type == "tool_result" and event.tool_call:
                    print_tool_call(event.tool_call.name, event.tool_call.input)
                    content = event.text.split("] ", 1)[-1] if "] " in event.text else event.text
                    is_error = "ERROR:" in (event.text or "")
                    print_tool_result(event.tool_call.name, content, is_error)
                elif event.type == "message_stop" and event.usage:
                    print_usage(event.usage.input_tokens, event.usage.output_tokens)
            console.print()  # trailing newline
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1) from e
