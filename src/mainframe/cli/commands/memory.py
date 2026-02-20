"""Memory management CLI commands."""

from __future__ import annotations

import asyncio

import click

from mainframe.cli.display import console, print_info
from mainframe.memory.manager import MemoryManager


@click.group()
def memory() -> None:
    """Manage the memory system."""


@memory.command()
@click.argument("query")
@click.option("--limit", default=5, help="Max results.")
def search(query: str, limit: int) -> None:
    """Search conversation history and stored facts."""
    asyncio.run(_search(query, limit))


async def _search(query: str, limit: int) -> None:
    manager = MemoryManager()
    results = await manager.search(query, max_results=limit)

    if not results:
        print_info("No results found.")
        return

    for i, r in enumerate(results, 1):
        source = r.source
        if r.metadata.get("role"):
            source = f"{r.source}/{r.metadata['role']}"
        console.print(f"\n[bold][{i}][/bold] [dim]({source}, score={r.score:.3f})[/dim]")
        console.print(f"  {r.content[:200]}")


@memory.command()
def status() -> None:
    """Show memory system statistics."""
    asyncio.run(_status())


async def _status() -> None:
    manager = MemoryManager()
    stats = await manager.get_stats()
    print_info("Memory status:")
    for key, value in stats.items():
        print_info(f"  {key}: {value}")


@memory.command()
@click.argument("text")
@click.option("--source", default="user", help="Source label.")
def add(text: str, source: str) -> None:
    """Add a fact to memory."""
    asyncio.run(_add(text, source))


async def _add(text: str, source: str) -> None:
    manager = MemoryManager()
    fact_id = await manager.add_fact(text, {"source": source})
    print_info(f"Fact added (id={fact_id}).")
