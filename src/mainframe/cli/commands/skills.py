"""Skill management CLI commands."""

from __future__ import annotations

from pathlib import Path

import click

from mainframe.cli.display import console, print_error, print_info
from mainframe.skills.loader import discover_skills, install_skill
from mainframe.skills.manifest import parse_skill_file


@click.group()
def skills() -> None:
    """Manage skills."""


@skills.command(name="list")
def list_skills() -> None:
    """List all discovered skills."""
    found = discover_skills()
    if not found:
        print_info("No skills installed.")
        return

    for skill in found:
        signed = " [signed]" if skill.is_signed else ""
        console.print(
            f"  [bold]{skill.name}[/bold] v{skill.version} "
            f"(tier {skill.sandbox_tier}){signed}"
        )
        if skill.description:
            console.print(f"    {skill.description}")


@skills.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def install(path: Path) -> None:
    """Install a skill from a local directory."""
    try:
        manifest = install_skill(path)
        print_info(f"Installed skill: {manifest.name} v{manifest.version}")
    except Exception as e:
        print_error(str(e))


@skills.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def inspect(path: Path) -> None:
    """Inspect a SKILL.md file."""
    if path.is_dir():
        path = path / "SKILL.md"

    try:
        manifest = parse_skill_file(path)
    except Exception as e:
        print_error(str(e))
        return

    console.print(f"[bold]Name:[/bold] {manifest.name}")
    console.print(f"[bold]Version:[/bold] {manifest.version}")
    console.print(f"[bold]Description:[/bold] {manifest.description}")
    console.print(f"[bold]Sandbox Tier:[/bold] {manifest.sandbox_tier}")
    console.print(f"[bold]Publisher:[/bold] {manifest.publisher or 'unknown'}")
    console.print(f"[bold]Signed:[/bold] {manifest.is_signed}")

    if manifest.permissions.bins:
        console.print(f"[bold]Binaries:[/bold] {', '.join(manifest.permissions.bins)}")
    console.print(f"[bold]Network:[/bold] {manifest.permissions.network}")


@skills.command()
def audit() -> None:
    """Audit installed skills for security issues."""
    found = discover_skills()
    if not found:
        print_info("No skills to audit.")
        return

    issues = 0
    for skill in found:
        skill_issues: list[str] = []

        if not skill.is_signed:
            skill_issues.append("unsigned (no signature verification)")

        if skill.is_signed and not skill.verify_content_hash():
            skill_issues.append("content hash mismatch (possibly tampered)")

        if skill.sandbox_tier < 1:
            skill_issues.append("sandbox tier 0 (runs in-process)")

        if skill.permissions.network:
            skill_issues.append("requests network access")

        if skill.permissions.filesystem.write:
            skill_issues.append(
                f"requests write access: {skill.permissions.filesystem.write}"
            )

        if skill_issues:
            console.print(f"\n[bold yellow]{skill.name}[/bold yellow]:")
            for issue in skill_issues:
                console.print(f"  [yellow]- {issue}[/yellow]")
                issues += 1
        else:
            console.print(f"  [green]{skill.name}: OK[/green]")

    if issues:
        console.print(f"\n[yellow]{issues} issue(s) found.[/yellow]")
    else:
        console.print("\n[green]All skills pass audit.[/green]")
