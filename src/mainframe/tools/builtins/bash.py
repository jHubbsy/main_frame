"""Bash command execution tool."""

from __future__ import annotations

import asyncio
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult

name = "bash"
description = (
    "Execute a bash command and return its output. "
    "Use for system commands, git, package managers, etc."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "The bash command to execute.",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default 120, max 600).",
        },
    },
    "required": ["command"],
}

MAX_OUTPUT = 50_000


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    command = params["command"]
    timeout = min(params.get("timeout", 120), 600)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(ctx.workspace_dir),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        return ToolResult.error(f"Command timed out after {timeout}s")
    except Exception as e:
        return ToolResult.error(f"Failed to execute command: {e}")

    output_parts = []
    if stdout:
        text = stdout.decode(errors="replace")
        if len(text) > MAX_OUTPUT:
            text = text[:MAX_OUTPUT] + f"\n... (truncated, {len(stdout)} bytes total)"
        output_parts.append(text)
    if stderr:
        text = stderr.decode(errors="replace")
        if len(text) > MAX_OUTPUT:
            text = text[:MAX_OUTPUT] + f"\n... (truncated, {len(stderr)} bytes total)"
        output_parts.append(f"STDERR:\n{text}")

    output = "\n".join(output_parts) if output_parts else "(no output)"

    if proc.returncode != 0:
        return ToolResult(
            content=f"Exit code {proc.returncode}\n{output}",
            is_error=True,
        )

    return ToolResult.success(output)
