"""Write file contents tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult

name = "write_file"
description = "Create or overwrite a file with the given content."
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Absolute or workspace-relative path to the file.",
        },
        "content": {
            "type": "string",
            "description": "The content to write to the file.",
        },
    },
    "required": ["path", "content"],
}


def _resolve_path(path_str: str, workspace: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return workspace / p


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    path = _resolve_path(params["path"], ctx.workspace_dir)
    content = params["content"]

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    except PermissionError:
        return ToolResult.error(f"Permission denied: {path}")
    except Exception as e:
        return ToolResult.error(f"Failed to write file: {e}")

    return ToolResult.success(f"Wrote {len(content)} bytes to {path}")
