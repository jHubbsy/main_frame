"""Click CLI entrypoint for Mainframe."""

from __future__ import annotations

import click

from mainframe.cli.commands.auth import auth
from mainframe.cli.commands.chat import chat
from mainframe.cli.commands.mcp import mcp
from mainframe.cli.commands.memory import memory
from mainframe.cli.commands.run import run
from mainframe.cli.commands.skills import skills


@click.group()
@click.version_option(package_name="mainframe")
def cli() -> None:
    """Mainframe — AI Agent Framework."""


cli.add_command(auth)
cli.add_command(chat)
cli.add_command(mcp)
cli.add_command(memory)
cli.add_command(run)
cli.add_command(skills)


def quick_chat() -> None:
    """Shortcut entrypoint: `computer` launches chat directly."""
    chat(standalone_mode=True)


if __name__ == "__main__":
    cli()
