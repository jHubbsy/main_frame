"""Edit file via exact string replacement."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult

name = "edit_file"
description = (
    "Edit a file by replacing an exact string match with new content. "
    "The old_string must uniquely match within the file."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Absolute or workspace-relative path to the file.",
        },
        "old_string": {
            "type": "string",
            "description": "The exact text to find and replace.",
        },
        "new_string": {
            "type": "string",
            "description": "The replacement text.",
        },
        "replace_all": {
            "type": "boolean",
            "description": "Replace all occurrences (default false).",
        },
    },
    "required": ["path", "old_string", "new_string"],
}


def _resolve_path(path_str: str, workspace: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return workspace / p


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    path = _resolve_path(params["path"], ctx.workspace_dir)
    old_string = params["old_string"]
    new_string = params["new_string"]
    replace_all = params.get("replace_all", False)

    if not path.exists():
        return ToolResult.error(f"File not found: {path}")
    if not path.is_file():
        return ToolResult.error(f"Not a file: {path}")

    try:
        content = path.read_text()
    except PermissionError:
        return ToolResult.error(f"Permission denied: {path}")

    count = content.count(old_string)
    if count == 0:
        return ToolResult.error("old_string not found in file.")
    if count > 1 and not replace_all:
        return ToolResult.error(
            f"old_string found {count} times. Set replace_all=true or provide more context."
        )

    if replace_all:
        new_content = content.replace(old_string, new_string)
    else:
        new_content = content.replace(old_string, new_string, 1)

    path.write_text(new_content)
    return ToolResult.success(f"Replaced {count if replace_all else 1} occurrence(s) in {path}")
