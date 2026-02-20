"""Interactive REPL for multi-turn conversation."""

from __future__ import annotations

import asyncio

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from mainframe.cli.display import (
    console,
    print_assistant_text,
    print_error,
    print_info,
    print_session_info,
    print_tool_call,
    print_tool_result,
    print_usage,
    print_welcome,
)
from mainframe.config.loader import load_config
from mainframe.config.paths import data_dir
from mainframe.core.agent import AgentLoop
from mainframe.core.events import Event, TextDelta
from mainframe.core.session import Session
from mainframe.memory.manager import MemoryManager
from mainframe.providers.registry import create_provider
from mainframe.tools.builtins import register_builtins
from mainframe.tools.builtins.memory_search import set_memory_manager
from mainframe.tools.policy import ToolPolicy
from mainframe.tools.registry import ToolRegistry


def _setup_tools(allowed_groups: list[str]) -> tuple[ToolRegistry, ToolPolicy]:
    registry = ToolRegistry()
    register_builtins(registry)
    policy = ToolPolicy.from_groups(allowed_groups)
    return registry, policy


@click.command()
@click.option("--resume", is_flag=True, help="Resume the most recent session.")
@click.option("--session-id", default=None, help="Resume a specific session.")
@click.option("--model", default=None, help="Override the model.")
@click.option("--no-tools", is_flag=True, help="Disable tool use.")
@click.option("--no-memory", is_flag=True, help="Disable memory indexing.")
def chat(
    resume: bool,
    session_id: str | None,
    model: str | None,
    no_tools: bool,
    no_memory: bool,
) -> None:
    """Start an interactive chat session."""
    asyncio.run(_chat_loop(
        resume=resume, session_id=session_id,
        model_override=model, no_tools=no_tools, no_memory=no_memory,
    ))


async def _chat_loop(
    resume: bool = False,
    session_id: str | None = None,
    model_override: str | None = None,
    no_tools: bool = False,
    no_memory: bool = False,
) -> None:
    config = load_config()
    if model_override:
        config.provider.model = model_override

    try:
        provider = create_provider(config.provider)
    except Exception as e:
        print_error(str(e))
        return

    # Memory setup
    memory_manager: MemoryManager | None = None
    if not no_memory:
        memory_manager = MemoryManager()
        set_memory_manager(memory_manager)

    # Tool setup
    tool_registry = None
    tool_policy = None
    if not no_tools:
        tool_registry, tool_policy = _setup_tools(config.security.allowed_tool_groups)

    # Skills setup — discover and inject into system prompt
    from mainframe.skills.registry import SkillRegistry

    skill_registry = SkillRegistry()
    skill_registry.load()
    system_prompt = config.system_prompt
    skill_section = skill_registry.build_system_prompt_section()
    if skill_section:
        system_prompt = system_prompt + "\n" + skill_section

    # Session setup
    if session_id:
        session = Session(session_id=session_id)
        if not session.load():
            print_error(f"Session '{session_id}' not found.")
            return
        print_info(f"Resumed session: {session_id}")
    elif resume:
        latest_id = Session.latest_session_id()
        if not latest_id:
            print_error("No previous sessions found.")
            return
        session = Session(session_id=latest_id)
        session.load()
        print_info(f"Resumed session: {latest_id}")
    else:
        session = Session()

    agent = AgentLoop(
        provider=provider,
        session=session,
        tool_registry=tool_registry,
        tool_policy=tool_policy,
        system_prompt=system_prompt,
        max_tokens=config.provider.max_tokens,
    )

    # Index messages to memory as they flow through
    if memory_manager:
        collected_response: list[str] = []

        async def _on_text_delta(event: Event) -> None:
            assert isinstance(event, TextDelta)
            collected_response.append(event.text)

        async def _index_user_message(text: str) -> None:
            await memory_manager.index_message(
                session.session_id, "user", text,
            )

        async def _index_assistant_response() -> None:
            if collected_response:
                full_text = "".join(collected_response)
                await memory_manager.index_message(
                    session.session_id, "assistant", full_text,
                )
                collected_response.clear()

        agent.event_bus.on("text_delta", _on_text_delta)

    print_welcome()
    print_session_info(session.session_id, session.meta.turn_count)

    # prompt_toolkit session for input history
    history_file = data_dir() / "chat_history"
    prompt_session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_file))
    )

    while True:
        try:
            user_input = await asyncio.to_thread(
                prompt_session.prompt, "\n> "
            )
        except (EOFError, KeyboardInterrupt):
            print_info("\nGoodbye.")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "/q"):
            print_info("Goodbye.")
            break

        if user_input.lower() == "/session":
            print_session_info(session.session_id, session.meta.turn_count)
            continue

        if user_input.lower() == "/tools":
            if tool_registry:
                print_info(f"Tools: {', '.join(tool_registry.names)}")
            else:
                print_info("Tools disabled.")
            continue

        try:
            # Index user message
            if memory_manager:
                await _index_user_message(user_input)

            await agent.submit(user_input)
            console.print()  # blank line before response

            async for event in agent.run():
                if event.type == "text_delta" and event.text:
                    print_assistant_text(event.text, streaming=True)
                elif event.type == "tool_result" and event.tool_call:
                    print_tool_call(event.tool_call.name, event.tool_call.input)
                    is_error = event.text.startswith(
                        f"[{event.tool_call.name}] ERROR:"
                    )
                    content = (
                        event.text.split("] ", 1)[-1]
                        if "] " in event.text
                        else event.text
                    )
                    print_tool_result(event.tool_call.name, content, is_error)
                elif event.type == "message_stop" and event.usage:
                    print_usage(event.usage.input_tokens, event.usage.output_tokens)

            # Index assistant response
            if memory_manager:
                await _index_assistant_response()

        except Exception as e:
            print_error(str(e))
