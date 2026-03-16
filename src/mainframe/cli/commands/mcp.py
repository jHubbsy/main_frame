"""MCP server management CLI commands."""

from __future__ import annotations

import asyncio

import click
from rich.table import Table

from mainframe.cli.display import console, print_error, print_info
from mainframe.config.loader import load_config
from mainframe.core.mcp_client import MCPClientManager


@click.group()
def mcp() -> None:
    """Manage MCP server connections."""


@mcp.command(name="list")
def list_servers() -> None:
    """List configured MCP servers and their tools."""
    asyncio.run(_list_servers())


async def _list_servers() -> None:
    config = load_config()
    if not config.mcp.servers:
        print_info("No MCP servers configured.")
        return

    manager = MCPClientManager()
    try:
        table = Table(title="MCP Servers")
        table.add_column("Server", style="bold")
        table.add_column("Status")
        table.add_column("Tools")

        for name, server_config in config.mcp.servers.items():
            try:
                session = await manager.connect_server(name, server_config)
                if session:
                    result = await session.list_tools()
                    tool_names = [t.name for t in result.tools]
                    table.add_row(
                        name,
                        "[green]connected[/green]",
                        f"{len(tool_names)}: {', '.join(tool_names)}",
                    )
                else:
                    table.add_row(name, "[red]failed[/red]", "-")
            except Exception as e:
                table.add_row(name, f"[red]error: {e}[/red]", "-")

        console.print(table)
    finally:
        await manager.cleanup()


@mcp.command()
@click.argument("server_name")
def test(server_name: str) -> None:
    """Test connection to a specific MCP server and list its tools."""
    asyncio.run(_test_server(server_name))


async def _test_server(server_name: str) -> None:
    config = load_config()
    if server_name not in config.mcp.servers:
        print_error(f"Server '{server_name}' not found in configuration.")
        return

    manager = MCPClientManager()
    try:
        server_config = config.mcp.servers[server_name]
        print_info(f"Connecting to '{server_name}' ({server_config.command})...")

        session = await manager.connect_server(server_name, server_config)
        if not session:
            print_error("Connection failed.")
            return

        result = await session.list_tools()
        print_info(f"Connected. Found {len(result.tools)} tool(s):\n")

        for tool in result.tools:
            console.print(f"  [bold]{tool.name}[/bold]")
            if tool.description:
                console.print(f"    {tool.description}")
    except Exception as e:
        print_error(str(e))
    finally:
        await manager.cleanup()
