"""mainframe extras — show declared optional integrations vs installed state."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

import click
from rich.table import Table

from mainframe.cli.display import console


def _find_pyproject() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            return candidate
    return None


def _load_extras() -> list[dict]:
    path = _find_pyproject()
    if path is None:
        return []

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return []

    with path.open("rb") as f:
        data = tomllib.load(f)

    opt_deps = data.get("project", {}).get("optional-dependencies", {})
    extras_meta = data.get("tool", {}).get("mainframe", {}).get("extras", {})

    result = []
    for name, pkgs in opt_deps.items():
        if name == "dev":
            continue
        meta = extras_meta.get(name, {})
        result.append({
            "name": name,
            "description": meta.get("description", ""),
            "check_package": meta.get("check_package", ""),
            "packages": pkgs,
            "has_meta": name in extras_meta,
        })
    return result


def _is_installed(check_package: str) -> bool:
    if not check_package:
        return False
    try:
        importlib.metadata.version(check_package)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


@click.command(name="extras")
def extras() -> None:
    """Show optional integrations and their install status."""
    items = _load_extras()

    if not items:
        console.print("[yellow]No optional integrations declared in pyproject.toml.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False, min_width=60)
    table.add_column("Extra", style="bold cyan", min_width=12)
    table.add_column("Description", min_width=40)
    table.add_column("Status", min_width=12)

    missing = []
    no_meta = []

    for item in items:
        name = item["name"]
        desc = item["description"] or "—"
        installed = _is_installed(item["check_package"])

        if not item["has_meta"]:
            status = "[yellow]? no metadata[/yellow]"
            no_meta.append(name)
        elif installed:
            status = "[green]✓ installed[/green]"
        else:
            status = "[red]✗ missing[/red]"
            missing.append(name)

        table.add_row(name, desc, status)

    console.print(table)

    if missing:
        console.print()
        console.print("[bold]To install missing extras:[/bold]")
        in_pipx = ".local/pipx/venvs" in sys.prefix
        for name in missing:
            if in_pipx:
                cmd = f"pipx runpip mainframe install -e '.\\[{name}]'"
            else:
                cmd = f"pip install -e '.\\[{name}]'"
            console.print(f"  {cmd}")

    if no_meta:
        console.print()
        console.print(
            "[yellow]Warning:[/yellow] The following extras are missing "
            "[tool.mainframe.extras.<name>] metadata in pyproject.toml:"
        )
        for name in no_meta:
            console.print(f"  {name}")
        console.print(
            "  Contributors should add a description and check_package "
            "so install.sh and this command work correctly."
        )
