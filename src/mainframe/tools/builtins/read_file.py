"""Read file contents tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult

name = "read_file"
description = "Read the contents of a file. Returns the file content with line numbers."
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Absolute or workspace-relative path to the file.",
        },
        "offset": {
            "type": "integer",
            "description": "Line number to start reading from (1-based).",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of lines to read.",
        },
    },
    "required": ["path"],
}

MAX_LINES = 2000
MAX_LINE_LEN = 2000


def _resolve_path(path_str: str, workspace: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return workspace / p


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    path = _resolve_path(params["path"], ctx.workspace_dir)
    offset = params.get("offset", 1)
    limit = params.get("limit", MAX_LINES)

    if not path.exists():
        return ToolResult.error(f"File not found: {path}")
    if not path.is_file():
        return ToolResult.error(f"Not a file: {path}")

    try:
        text = path.read_text(errors="replace")
    except PermissionError:
        return ToolResult.error(f"Permission denied: {path}")

    lines = text.splitlines()
    start = max(0, offset - 1)
    end = start + limit
    selected = lines[start:end]

    numbered = []
    for i, line in enumerate(selected, start=start + 1):
        if len(line) > MAX_LINE_LEN:
            line = line[:MAX_LINE_LEN] + "..."
        numbered.append(f"{i:>6}\t{line}")

    if not numbered:
        return ToolResult.success("(empty file)")

    result = "\n".join(numbered)
    if end < len(lines):
        result += f"\n... ({len(lines) - end} more lines)"

    return ToolResult.success(result)
