"""List open pull requests for the current repository."""

from __future__ import annotations

import asyncio
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult

name = "list_prs"
description = "List open pull requests in the current GitHub repository."
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "limit": {
            "type": "integer",
            "description": "Maximum number of PRs to list.",
            "default": 10,
        },
        "state": {
            "type": "string",
            "description": "PR state filter: open, closed, merged, all.",
            "default": "open",
        },
    },
    "required": [],
}


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    limit = params.get("limit", 10)
    state = params.get("state", "open")

    try:
        proc = await asyncio.create_subprocess_exec(
            "gh", "pr", "list",
            "--limit", str(limit),
            "--state", state,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(ctx.workspace_dir),
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return ToolResult.error(
                f"gh pr list failed: {stderr.decode().strip()}"
            )

        output = stdout.decode().strip()
        if not output:
            return ToolResult.success(f"No {state} pull requests found.")
        return ToolResult.success(output)

    except FileNotFoundError:
        return ToolResult.error(
            "gh CLI not found. Install it: https://cli.github.com"
        )
