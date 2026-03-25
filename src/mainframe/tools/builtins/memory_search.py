"""Memory search tool — lets the agent query conversation history and facts."""

from __future__ import annotations

from typing import Any

from mainframe.security.sanitize import sanitize_memory_result
from mainframe.tools.base import ToolContext, ToolResult

name = "memory_search"
description = (
    "Search conversation history and stored facts. "
    "Use this to recall previous discussions or find relevant context."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query.",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum results to return (default 5).",
        },
    },
    "required": ["query"],
}

# Will be set by the CLI when memory manager is available
_memory_manager = None


def set_memory_manager(manager: Any) -> None:
    global _memory_manager
    _memory_manager = manager


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    if _memory_manager is None:
        return ToolResult.error("Memory system not initialized.")

    query = params["query"]
    max_results = params.get("max_results", 5)

    results = await _memory_manager.search(query, max_results=max_results)

    if not results:
        return ToolResult.success("No relevant memories found.")

    lines = []
    for i, r in enumerate(results, 1):
        source = r.source
        if r.metadata.get("role"):
            source = f"{r.source}/{r.metadata['role']}"
        lines.append(f"[{i}] ({source}, score={r.score:.3f})")
        lines.append(sanitize_memory_result(r.content).content)
        lines.append("")

    return ToolResult.success("\n".join(lines))
