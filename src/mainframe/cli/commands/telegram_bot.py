"""Telegram bot interface for Mainframe."""

from __future__ import annotations

import os
import sys

import click

from mainframe.cli.commands.chat import _ensure_mcp_credentials, _setup_tools
from mainframe.cli.display import (
    console,
    print_assistant_text,
    print_error,
    print_info,
    print_tool_call,
    print_tool_result,
    print_usage,
)
from mainframe.config.loader import load_config
from mainframe.core.agent import AgentLoop
from mainframe.core.mcp_client import MCPClientManager
from mainframe.core.session import Session
from mainframe.providers.registry import create_provider
from mainframe.tools.builtins.memory_search import set_memory_manager
from mainframe.tools.mcp_adapter import discover_and_register


@click.command(name="telegram")
@click.option("--model", default=None, help="Override the model.")
@click.option("--no-tools", is_flag=True, help="Disable tool use.")
@click.option("--no-memory", is_flag=True, help="Disable memory indexing.")
def telegram(
    model: str | None,
    no_tools: bool,
    no_memory: bool,
) -> None:
    """Start the Telegram bot interface."""
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    except ImportError:
        print_error("Telegram integration is not installed.")
        print_info(
            "Install it with: pipx inject mainframe '.[telegram]' or pip install -e '.[telegram]'"
        )
        sys.exit(1)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        try:
            from mainframe.security.credentials import _get_credential_store
            store = _get_credential_store()
            token = store.get("telegram_bot_token")
        except Exception:
            token = None

    if not token:
        print_info("TELEGRAM_BOT_TOKEN environment variable is not set.")
        print_info("To use this feature, you need the Telegram app: https://telegram.org/apps")
        print_info("If you don't have a bot token, you can get one from https://t.me/BotFather")
        try:
            import getpass
            token = getpass.getpass("  Enter Telegram Bot Token: ").strip()
        except (EOFError, KeyboardInterrupt):
            print_error("\nCancelled.")
            sys.exit(1)
            
        if not token:
            print_error("Token was not provided.")
            sys.exit(1)
            
        try:
            save = click.confirm("  Save Telegram Bot Token for future sessions?", default=True)
            if save:
                from mainframe.security.credentials import _get_credential_store
                _get_credential_store().set("telegram_bot_token", token)
        except Exception as e:
            print_error(f"Failed to save token: {e}")

    async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "Hello! I am Mainframe. Send me a message, "
                "and I'll respond using my tools and memory."
            )

    async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_message or not update.effective_message.text:
            return

        chat_id = update.effective_chat.id if update.effective_chat else 0
        user_text = update.effective_message.text

        msg = await update.effective_message.reply_text("🤔 Thinking...")

        session_id = f"tg-{chat_id}"
        config = load_config()
        if model:
            config.provider.model = model

        try:
            provider = create_provider(config.provider)
        except Exception as e:
            await msg.edit_text(f"Error initializing provider: {e}")
            return

        memory_manager = None
        if not no_memory:
            from mainframe.memory.manager import MemoryManager
            memory_manager = MemoryManager()
            set_memory_manager(memory_manager)

        tool_registry = None
        tool_policy = None
        if not no_tools:
            tool_registry, tool_policy = _setup_tools(config.security.allowed_tool_groups)

        mcp_manager = None
        if not no_tools and config.mcp.enabled and config.mcp.servers and tool_registry:
            mcp_manager = MCPClientManager()
            for server_name, server_config in config.mcp.servers.items():
                if server_config.required_env:
                    resolved = await _ensure_mcp_credentials(
                        server_name, server_config.required_env
                    )
                    server_config.env.update(resolved)
            # pass items since it expects dict of config objects
            connected = await mcp_manager.connect_all(config.mcp.servers)
            for server_name, sess in connected.items():
                await discover_and_register(server_name, sess, tool_registry)
                if tool_policy:
                    tool_policy.allow_mcp_server(server_name)

        from mainframe.skills.registry import SkillRegistry
        skill_registry = SkillRegistry()
        skill_registry.load(skill_configs=config.skills)
        system_prompt = config.system_prompt
        skill_section = skill_registry.build_system_prompt_section()
        if skill_section:
            system_prompt = system_prompt + "\n" + skill_section

        if tool_registry and skill_registry.actions:
            skill_registry.register_tools(tool_registry)
            if tool_policy:
                for action in skill_registry.actions:
                    tool_policy.allow(action.name)

        main_session = Session(session_id=session_id)
        # Session.load() is synchronous, safe to call here even if blocking slightly,
        # but better to handle it properly if needed. It's fast enough.
        main_session.load()

        agent = AgentLoop(
            provider=provider,
            session=main_session,
            tool_registry=tool_registry,
            tool_policy=tool_policy,
            system_prompt=system_prompt,
            max_tokens=config.provider.max_tokens,
        )

        try:
            if memory_manager:
                await memory_manager.index_message(session_id, "user", user_text)

            print_info(f"Message from {chat_id}: {user_text}")
            await agent.submit(user_text)
            
            text_parts = []
            async for event in agent.run():
                if event.type == "text_delta" and event.text:
                    print_assistant_text(event.text, streaming=True)
                    text_parts.append(event.text)
                elif event.type == "tool_result" and event.tool_call:
                    print_tool_call(event.tool_call.name, event.tool_call.input)
                    is_error = event.text.startswith(f"[{event.tool_call.name}] ERROR:")
                    content = event.text.split("] ", 1)[-1] if "] " in event.text else event.text
                    print_tool_result(event.tool_call.name, content, is_error)
                elif event.type == "message_stop" and event.usage:
                    print_usage(event.usage.input_tokens, event.usage.output_tokens)
            console.print()

            response_text = "".join(text_parts)

            if memory_manager:
                await memory_manager.index_message(session_id, "assistant", response_text)

            if not response_text:
                response_text = "Done."

            # Safe chunking for Telegram limits (4096 is max length)
            MAX_LENGTH = 4000
            chunks = [
                response_text[i : i + MAX_LENGTH]
                for i in range(0, len(response_text), MAX_LENGTH)
            ]
            await msg.edit_text(chunks[0])
            for chunk in chunks[1:]:
                # Sleep briefly to avoid hitting rate limits
                import asyncio
                await asyncio.sleep(0.5)
                await update.effective_message.reply_text(chunk)

        except Exception as e:
            await msg.edit_text(f"Error during agent loop: {e}")
        finally:
            if mcp_manager:
                await mcp_manager.cleanup()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", _start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

    print_info("Telegram bot is polling. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
