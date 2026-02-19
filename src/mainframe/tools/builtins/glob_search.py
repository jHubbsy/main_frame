"""Glob-based file pattern search tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult

name = "glob_search"
description = (
    "Find files matching a glob pattern. "
    "Returns matching file paths sorted by modification time."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.ts').",
        },
        "path": {
            "type": "string",
            "description": "Directory to search in (default: workspace root).",
        },
    },
    "required": ["pattern"],
}

MAX_RESULTS = 200


def _resolve_path(path_str: str | None, workspace: Path) -> Path:
    if path_str is None:
        return workspace
    p = Path(path_str)
    if p.is_absolute():
        return p
    return workspace / p


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    pattern = params["pattern"]
    search_dir = _resolve_path(params.get("path"), ctx.workspace_dir)

    if not search_dir.exists():
        return ToolResult.error(f"Directory not found: {search_dir}")

    try:
        matches = sorted(search_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception as e:
        return ToolResult.error(f"Glob failed: {e}")

    # Filter out directories, only return files
    files = [str(m) for m in matches if m.is_file()]

    if not files:
        return ToolResult.success("No files matched.")

    result = "\n".join(files[:MAX_RESULTS])
    if len(files) > MAX_RESULTS:
        result += f"\n... ({len(files) - MAX_RESULTS} more files)"

    return ToolResult.success(result)
