"""Rich-based terminal output for Mainframe CLI."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status

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
            "[bold]Ctrl+I[/bold] add image  •  "
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


def print_error(message: str) -> None:
    err_console.print(f"[bold red]Error:[/bold red] {message}")


def print_info(message: str) -> None:
    console.print(f"[dim]{message}[/dim]")


def print_usage(input_tokens: int, output_tokens: int) -> None:
    console.print(
        f"\n[dim]tokens: {input_tokens} in / {output_tokens} out[/dim]"
    )


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


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
