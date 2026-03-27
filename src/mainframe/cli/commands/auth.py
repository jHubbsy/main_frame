"""API key management commands."""

from __future__ import annotations

import getpass

import click

from mainframe.cli.display import print_error, print_info
from mainframe.security.credentials import (
    delete_api_key,
    delete_mcp_env_var,
    delete_mcp_oauth_tokens,
    get_api_key,
    list_mcp_env_vars,
    list_mcp_oauth_servers,
    list_stored_providers,
    store_mcp_env_var,
    update_api_key,
)


@click.group()
def auth() -> None:
    """Manage API keys."""


@auth.command()
@click.option("--provider", default="anthropic", help="Provider name.")
def login(provider: str) -> None:
    """Set or update an API key for a provider."""
    existing = get_api_key(provider)
    if existing:
        print_info(f"A key for '{provider}' already exists. This will replace it.")

    try:
        key = getpass.getpass(f"{provider} API key: ")
    except (EOFError, KeyboardInterrupt):
        print_info("\nCancelled.")
        return

    key = key.strip()
    if not key:
        print_error("No key entered.")
        return

    replaced = update_api_key(provider, key)
    if replaced:
        print_info(f"API key for '{provider}' updated.")
    else:
        print_info(f"API key for '{provider}' saved.")


@auth.command()
@click.option("--provider", default="anthropic", help="Provider name.")
def logout(provider: str) -> None:
    """Remove a stored API key."""
    if delete_api_key(provider):
        print_info(f"API key for '{provider}' removed.")
    else:
        print_info(f"No stored key for '{provider}'.")


@auth.command(name="status")
def auth_status() -> None:
    """Show stored API keys and MCP credentials."""
    providers = list_stored_providers()
    if providers:
        print_info("API keys:")
        for p in providers:
            print_info(f"  {p}: configured")
    else:
        print_info("No API keys stored. Run: mainframe auth login")

    mcp_env_vars = list_mcp_env_vars()
    if mcp_env_vars:
        print_info("MCP credentials:")
        for server, var in mcp_env_vars:
            print_info(f"  {server}: {var}")

    mcp_servers = list_mcp_oauth_servers()
    if mcp_servers:
        print_info("MCP OAuth tokens:")
        for s in mcp_servers:
            print_info(f"  {s}: token stored")


@auth.command(name="logout-mcp")
@click.argument("server")
def logout_mcp(server: str) -> None:
    """Remove stored OAuth tokens for an MCP server."""
    if delete_mcp_oauth_tokens(server):
        print_info(f"OAuth tokens for MCP server '{server}' removed.")
    else:
        print_info(f"No stored OAuth tokens for '{server}'.")


@auth.command(name="mcp-set")
@click.argument("server")
@click.argument("var")
def mcp_set(server: str, var: str) -> None:
    """Store a credential env var for an MCP server.

    Example: mainframe auth mcp-set github GITHUB_PERSONAL_ACCESS_TOKEN
    """
    try:
        value = getpass.getpass(f"{var}: ")
    except (EOFError, KeyboardInterrupt):
        print_info("\nCancelled.")
        return

    value = value.strip()
    if not value:
        print_error("No value entered.")
        return

    store_mcp_env_var(server, var, value)
    print_info(f"Saved {var} for MCP server '{server}'.")


@auth.command(name="mcp-delete")
@click.argument("server")
@click.argument("var")
def mcp_delete(server: str, var: str) -> None:
    """Remove a stored credential env var for an MCP server.

    Example: mainframe auth mcp-delete github GITHUB_PERSONAL_ACCESS_TOKEN
    """
    if delete_mcp_env_var(server, var):
        print_info(f"Removed {var} for MCP server '{server}'.")
    else:
        print_info(f"No stored {var} for '{server}'.")
