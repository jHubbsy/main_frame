"""Interactive REPL for multi-turn conversation."""

from __future__ import annotations

import asyncio

import anyio
import click

from mainframe.cli.display import (
    console,
    print_assistant_text,
    print_error,
    print_help,
    print_info,
    print_input_separator,
    print_response_header,
    print_session_info,
    print_tool_call,
    print_tool_result,
    print_usage,
    print_welcome,
    rerender_as_markdown,
    thinking_status,
)
from mainframe.cli.rich_input import RichInputHandler
from mainframe.config.loader import load_config
from mainframe.config.paths import data_dir
from mainframe.core.agent import AgentLoop
from mainframe.core.events import BeforeToolCall, Event, TextDelta
from mainframe.core.mcp_client import MCPClientManager
from mainframe.core.session import Session
from mainframe.memory.manager import MemoryManager
from mainframe.providers.base import ContentBlock, Message, Role
from mainframe.providers.registry import create_provider
from mainframe.security.credentials import get_mcp_env_var, store_mcp_env_var
from mainframe.security.sanitize import sanitize_user_input
from mainframe.tools.builtins import register_builtins
from mainframe.tools.builtins.connect_mcp import clear_pending_requests, get_pending_requests
from mainframe.tools.builtins.memory_search import set_memory_manager
from mainframe.tools.mcp_adapter import discover_and_register
from mainframe.tools.policy import ToolPolicy
from mainframe.tools.registry import ToolRegistry


async def _process_mcp_requests(
    agent: AgentLoop,
    session: Session,
    registry: ToolRegistry | None,
    policy: ToolPolicy | None,
    mcp_manager: MCPClientManager | None,
) -> MCPClientManager | None:
    """Check for pending MCP connection requests and prompt the user.

    Returns the (possibly newly-created) MCPClientManager so the caller
    can track it for cleanup.
    """
    from mainframe.config.schema import MCPOAuthConfig, MCPServerConfig
    from mainframe.providers.base import Message, Role

    pending = get_pending_requests()
    if not pending:
        return mcp_manager

    results: list[str] = []
    for req in pending:
        display = req.url if req.url else f"{req.command} {' '.join(req.args)}".strip()
        approved = await asyncio.to_thread(
            click.confirm,
            f"\nConnect to MCP server '{req.server_name}' ({display})?",
            default=False,
        )

        if not approved:
            print_info(f"Denied connection to '{req.server_name}'.")
            results.append(
                f"[MCP] User denied connection to server '{req.server_name}'."
            )
            continue

        # Lazily create the MCPClientManager if needed
        if mcp_manager is None:
            mcp_manager = MCPClientManager()

        # Resolve any required credentials before connecting
        resolved_env = dict(req.env)
        if req.required_env:
            resolved = await _ensure_mcp_credentials(req.server_name, req.required_env)
            resolved_env.update(resolved)

        config = MCPServerConfig(
            transport=req.transport,
            command=req.command or None,
            args=req.args,
            env=resolved_env,
            required_env=req.required_env,
            url=req.url or None,
            oauth=MCPOAuthConfig() if req.transport == "streamable_http" else None,
        )
        try:
            mcp_session = await mcp_manager.connect_server(req.server_name, config)
            if mcp_session and registry:
                tool_names = await discover_and_register(
                    req.server_name, mcp_session, registry,
                )
                if policy:
                    policy.allow_mcp_server(req.server_name)
                print_info(
                    f"MCP [{req.server_name}]: connected, {len(tool_names)} tool(s) registered."
                )
                results.append(
                    f"[MCP] Connected to '{req.server_name}'. "
                    f"Tools available: {', '.join(tool_names)}"
                )
        except Exception as e:
            print_error(f"Failed to connect to '{req.server_name}': {e}")
            results.append(
                f"[MCP] Failed to connect to '{req.server_name}': {e}"
            )

    clear_pending_requests()

    # Inject outcome as a user message so the agent knows what happened
    if results:
        outcome = "\n".join(results)
        session.add_message(Message(role=Role.USER, content=outcome))

    return mcp_manager


async def _ensure_mcp_credentials(server_name: str, required_env: list[str]) -> dict[str, str]:
    """Resolve required env vars from store or prompt the user. Returns resolved vars."""
    resolved: dict[str, str] = {}
    for var in required_env:
        value = get_mcp_env_var(server_name, var)
        if value:
            resolved[var] = value
            continue

        print_info(f"MCP server '{server_name}' requires {var}.")
        try:
            import getpass
            value = await asyncio.to_thread(getpass.getpass, f"  Enter {var}: ")
        except (EOFError, KeyboardInterrupt):
            print_info("\nSkipped.")
            continue

        value = value.strip()
        if not value:
            continue

        save = await asyncio.to_thread(
            click.confirm, f"  Save {var} for future connections?", default=True
        )
        if save:
            store_mcp_env_var(server_name, var, value)

        resolved[var] = value
    return resolved


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
    async def _run() -> None:
        await _chat_loop(
            resume=resume, session_id=session_id,
            model_override=model, no_tools=no_tools, no_memory=no_memory,
        )
    anyio.run(_run)


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
        if tool_policy and not config.mcp.enabled:
            tool_policy.deny("connect_mcp")

    # MCP setup
    mcp_manager: MCPClientManager | None = None
    if not no_tools and config.mcp.enabled and config.mcp.servers and tool_registry:
        mcp_manager = MCPClientManager()
        # Resolve credentials for all configured servers before connecting
        for server_name, server_config in config.mcp.servers.items():
            if server_config.required_env:
                resolved = await _ensure_mcp_credentials(server_name, server_config.required_env)
                server_config.env.update(resolved)
        connected = await mcp_manager.connect_all(config.mcp.servers)
        for server_name, session in connected.items():
            tool_names = await discover_and_register(server_name, session, tool_registry)
            if tool_policy:
                tool_policy.allow_mcp_server(server_name)
            print_info(f"MCP [{server_name}]: {len(tool_names)} tool(s)")

    # Skills setup — discover, inject into system prompt, register action tools
    from mainframe.skills.registry import SkillRegistry

    skill_registry = SkillRegistry()
    skill_registry.load(skill_configs=config.skills)
    for warning in skill_registry.warnings:
        print_info(f"Warning: {warning}")
    system_prompt = config.system_prompt
    skill_section = skill_registry.build_system_prompt_section()
    if skill_section:
        system_prompt = system_prompt + "\n" + skill_section

    # Register skill actions as tools and allow them in policy
    if tool_registry and skill_registry.actions:
        skill_registry.register_tools(tool_registry)
        if tool_policy:
            for action in skill_registry.actions:
                tool_policy.allow(action.name)

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

    history_file = data_dir() / "chat_history"
    rich_handler = RichInputHandler(history_file=str(history_file))

    try:
        while True:
            try:
                print_input_separator()
                rich_message = await rich_handler.get_input()
            except (EOFError, KeyboardInterrupt):
                print_info("\nGoodbye.")
                break

            user_input = rich_message.text.strip()
            if not user_input and not rich_message.has_images:
                continue

            if user_input:
                scan = sanitize_user_input(user_input)
                if scan.flagged:
                    print_info(f"[security] Suspicious input patterns: {scan.patterns_found}")

            cmd = user_input.lower().strip()

            if cmd in ("/quit", "/exit", "/q"):
                print_info("Goodbye.")
                break

            if cmd == "/help":
                print_help()
                continue

            if cmd == "/clear":
                console.clear()
                print_welcome()
                print_session_info(session.session_id, session.meta.turn_count)
                continue

            if cmd == "/compact":
                if len(session.messages) < 2:
                    print_info("Nothing to compact.")
                    continue
                compact_status = thinking_status()
                compact_status.update("[dim]compacting conversation…[/dim]")
                compact_status.start()
                try:
                    compact_prompt = (
                        "Summarize this conversation concisely but completely. "
                        "Preserve: key topics, decisions, important technical details, "
                        "and any context needed to continue the conversation coherently. "
                        "This summary will replace the full history to reduce token usage."
                    )
                    summary_result = await provider.complete(
                        messages=list(session.messages) + [
                            Message(role=Role.USER, content=compact_prompt)
                        ],
                        tools=None,
                        system=config.system_prompt,
                        max_tokens=2048,
                    )
                    summary = (
                        summary_result.message.content
                        if isinstance(summary_result.message.content, str)
                        else ""
                    )
                    if not summary:
                        print_info("Compact failed: no summary generated.")
                        continue
                    old_count = len(session.messages)
                    session.compact(summary)
                    compact_status.stop()
                    print_info(f"Compacted {old_count} messages → 1 summary. Token usage reduced.")
                except Exception as e:
                    print_error(f"Compact failed: {e}")
                finally:
                    compact_status.stop()
                continue

            if cmd == "/session":
                print_session_info(session.session_id, session.meta.turn_count)
                continue

            if cmd == "/tools":
                if tool_registry:
                    print_info(f"Tools: {', '.join(tool_registry.names)}")
                else:
                    print_info("Tools disabled.")
                continue

            try:
                # Index user message (text portion only)
                if memory_manager and user_input:
                    await _index_user_message(user_input)

                if rich_message.has_images:
                    blocks: list[ContentBlock] = []
                    if user_input:
                        blocks.append(ContentBlock(type="text", text=user_input))
                    for img in rich_message.images:
                        blocks.append(ContentBlock(
                            type="image",
                            image_data=img.base64_data,
                            image_mime_type=img.mime_type,
                        ))
                    await agent.submit_message(Message(role=Role.USER, content=blocks))
                else:
                    await agent.submit(user_input)

                console.print()  # blank line before response

                status = thinking_status()
                spinner_stopped = False
                response_header_printed = False
                streamed_parts: list[str] = []

                async def _on_before_tool(event: Event) -> None:
                    assert isinstance(event, BeforeToolCall)
                    status.update(f"[dim]running [bold]{event.tool_name}[/bold]…[/dim]")

                agent.event_bus.on("before_tool_call", _on_before_tool)
                status.start()

                try:
                    async for event in agent.run():
                        if event.type == "text_delta" and event.text:
                            if not spinner_stopped:
                                status.stop()
                                spinner_stopped = True
                            if not response_header_printed:
                                print_response_header()
                                response_header_printed = True
                            streamed_parts.append(event.text)
                            print_assistant_text(event.text, streaming=True)
                        elif event.type == "tool_result" and event.tool_call:
                            if not spinner_stopped:
                                status.stop()
                                spinner_stopped = True
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
                            if streamed_parts:
                                console.print()  # end the raw stream line
                                rerender_as_markdown("".join(streamed_parts))
                            print_usage(event.usage.input_tokens, event.usage.output_tokens)
                finally:
                    status.stop()
                    agent.event_bus.off("before_tool_call", _on_before_tool)

                # Index assistant response
                if memory_manager:
                    await _index_assistant_response()

                # Process any pending MCP connection requests
                mcp_manager = await _process_mcp_requests(
                    agent, session, tool_registry, tool_policy, mcp_manager,
                )

            except Exception as e:
                print_error(str(e))
    finally:
        if mcp_manager:
            await mcp_manager.cleanup()
