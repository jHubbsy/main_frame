"""Rich-based terminal output for Mainframe CLI."""

from __future__ import annotations

import math

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def print_welcome() -> None:
    logo = """[bold bright_cyan]███╗░░░███╗░█████╗░██╗███╗░░██╗███████╗██████╗░░█████╗░███╗░░░███╗███████╗
████╗░████║██╔══██╗██║████╗░██║██╔════╝██╔══██╗██╔══██╗████╗░████║██╔════╝
██╔████╔██║███████║██║██╔██╗██║█████╗░░██████╔╝███████║██╔████╔██║█████╗░░
██║╚██╔╝██║██╔══██║██║██║╚████║██╔══╝░░██╔══██╗██╔══██║██║╚██╔╝██║██╔══╝░░
██║░╚═╝░██║██║░░██║██║██║░╚███║██║░░░░░██║░░██║██║░░██║██║░╚═╝░██║███████╗
╚═╝░░░░░╚═╝╚═╝░░╚═╝╚═╝╚═╝░░╚══╝╚═╝░░░░░╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░░░░╚═╝╚══════╝[/bold bright_cyan]

[bright_yellow]▶[/bright_yellow] [bright_green]ARTIFICIAL INTELLIGENCE[/bright_green] [bright_cyan]•[/bright_cyan] [bright_magenta]AGENT FRAMEWORK[/bright_magenta] [bright_cyan]•[/bright_cyan] [bright_red]SYSTEM ONLINE[/bright_red] [bright_yellow]◀[/bright_yellow]
[dim bright_blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim bright_blue]"""

    console.print(
        Panel(
            logo + "\n\n"
            "Press [bold]Enter[/bold] to send  •  "
            "[bold]Option+Enter[/bold] or [bold]Ctrl+J[/bold] for newline  •  "
            "[bold]Ctrl+D[/bold] to exit  •  "
            "[bold]/help[/bold] for commands",
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )


def thinking_status() -> Status:
    """Return a pre-configured thinking spinner. Caller must start/stop it."""
    return Status("[dim]thinking…[/dim]", console=console, spinner="dots")


def print_response_header() -> None:
    """Print the agent response label before streamed output."""
    console.print("[cyan]╭─ Mainframe[/cyan]")


def print_input_separator() -> None:
    """Print the top border of the user input box."""
    console.print("\n[green]╭─ You[/green]")


def print_assistant_text(text: str, *, streaming: bool = False) -> None:
    """Print assistant response. If streaming, print raw text; otherwise render markdown."""
    if streaming:
        console.print(text, end="", highlight=False)
    else:
        console.print(Markdown(text))


def rerender_as_markdown(text: str) -> None:
    """Erase the raw streamed text on-screen and re-render it as Rich Markdown.

    Caller must have just printed a bare newline (console.print()) to end the
    streaming line before calling this — that newline is accounted for in the
    cursor math below.
    """
    if not text.strip():
        return

    width = console.width
    # Count terminal rows the raw text occupied (accounts for line-wrap).
    line_count = sum(
        max(1, math.ceil(len(seg) / width)) if seg else 1
        for seg in text.split("\n")
    )

    # Cursor is on the blank line added after streaming ended.
    # Move up line_count rows to the start of the raw text, go to column 0,
    # then erase from cursor to end of screen.
    console.file.write(f"\x1b[{line_count}A\r\x1b[0J")
    console.file.flush()

    console.print(Markdown(text))


def print_error(message: str) -> None:
    err_console.print(f"[bold red]Error:[/bold red] {message}")


def print_info(message: str) -> None:
    console.print(f"[dim]{message}[/dim]")


def print_usage(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> None:
    parts = [f"tokens: {input_tokens} in / {output_tokens} out"]
    if cache_read_tokens:
        parts.append(f"{cache_read_tokens} cache hit")
    if cache_creation_tokens:
        parts.append(f"{cache_creation_tokens} cache write")
    console.print(f"\n[dim]{' · '.join(parts)}[/dim]")


def print_session_info(session_id: str, turn_count: int) -> None:
    console.print(f"[dim]session: {session_id} ({turn_count} turns)[/dim]")


def print_tool_call(tool_name: str, tool_input: dict) -> None:
    """Display a tool invocation."""
    # Compact display of input params
    params_str = ", ".join(f"{k}={_truncate(str(v), 80)}" for k, v in tool_input.items())
    console.print(f"\n[yellow]> {tool_name}[/yellow]({params_str})")


def print_tool_result(tool_name: str, content: str, is_error: bool = False) -> None:
    """Display tool execution result."""
    style = "red" if is_error else "dim"
    truncated = _truncate(content, 500)
    console.print(f"[{style}]{truncated}[/{style}]")


SLASH_COMMANDS: list[tuple[str, str]] = [
    ("/help", "Show available commands"),
    ("/clear", "Clear the screen"),
    ("/compact", "Summarize conversation history to reduce token usage"),
    ("/session", "Show session ID and turn count"),
    ("/tools", "List available tools"),
    ("/quit", "Exit (also /exit or /q)"),
]


def print_help() -> None:
    """Print available slash commands."""
    table = Table(show_header=False, box=None, pad_edge=False, padding=(0, 2, 0, 0))
    table.add_column(style="bold cyan", min_width=12)
    table.add_column(style="dim")

    for cmd, desc in SLASH_COMMANDS:
        table.add_row(cmd, desc)

    console.print(table)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
