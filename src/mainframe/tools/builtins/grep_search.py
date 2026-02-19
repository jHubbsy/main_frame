"""Content search tool using regex pattern matching."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult

name = "grep_search"
description = (
    "Search file contents for a regex pattern. "
    "Returns matching lines with file paths and line numbers."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Regex pattern to search for.",
        },
        "path": {
            "type": "string",
            "description": "File or directory to search in (default: workspace root).",
        },
        "glob": {
            "type": "string",
            "description": "File glob filter (e.g., '*.py').",
        },
        "case_insensitive": {
            "type": "boolean",
            "description": "Case-insensitive search (default false).",
        },
    },
    "required": ["pattern"],
}

MAX_MATCHES = 100
BINARY_EXTENSIONS = {
    ".pyc", ".so", ".o", ".a", ".dll", ".exe", ".bin",
    ".png", ".jpg", ".gif", ".zip", ".gz", ".tar",
}


def _resolve_path(path_str: str | None, workspace: Path) -> Path:
    if path_str is None:
        return workspace
    p = Path(path_str)
    if p.is_absolute():
        return p
    return workspace / p


def _should_skip(path: Path) -> bool:
    return (
        path.suffix in BINARY_EXTENSIONS
        or any(part.startswith(".") for part in path.parts)
        or "__pycache__" in path.parts
        or "node_modules" in path.parts
        or ".venv" in path.parts
    )


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    pattern_str = params["pattern"]
    search_path = _resolve_path(params.get("path"), ctx.workspace_dir)
    glob_filter = params.get("glob", "**/*")
    case_insensitive = params.get("case_insensitive", False)

    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern_str, flags)
    except re.error as e:
        return ToolResult.error(f"Invalid regex: {e}")

    matches: list[str] = []

    if search_path.is_file():
        files = [search_path]
    elif search_path.is_dir():
        files = [f for f in search_path.glob(glob_filter) if f.is_file() and not _should_skip(f)]
    else:
        return ToolResult.error(f"Path not found: {search_path}")

    for file_path in sorted(files):
        try:
            content = file_path.read_text(errors="replace")
        except (PermissionError, OSError):
            continue

        for line_num, line in enumerate(content.splitlines(), 1):
            if regex.search(line):
                matches.append(f"{file_path}:{line_num}: {line.strip()}")
                if len(matches) >= MAX_MATCHES:
                    break
        if len(matches) >= MAX_MATCHES:
            break

    if not matches:
        return ToolResult.success("No matches found.")

    result = "\n".join(matches)
    if len(matches) >= MAX_MATCHES:
        result += f"\n... (truncated at {MAX_MATCHES} matches)"

    return ToolResult.success(result)
