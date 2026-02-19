"""API key management commands."""

from __future__ import annotations

import getpass

import click

from mainframe.cli.display import print_error, print_info
from mainframe.security.credentials import (
    delete_api_key,
    get_api_key,
    list_stored_providers,
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
    """Show which providers have stored API keys."""
    providers = list_stored_providers()
    if providers:
        for p in providers:
            print_info(f"  {p}: configured")
    else:
        print_info("No API keys stored. Run: mainframe auth login")
