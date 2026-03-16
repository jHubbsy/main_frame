"""Connect MCP tool — agent proposes MCP server connections for user approval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult

name = "connect_mcp"
description = (
    "Propose connecting to an MCP (Model Context Protocol) server. "
    "The connection requires user approval before it is established. "
    "Provide the server name and the command to launch it."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "server_name": {
            "type": "string",
            "description": "A short identifier for the server (e.g. 'github', 'postgres').",
        },
        "command": {
            "type": "string",
            "description": "The executable command to launch the MCP server.",
        },
        "args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Command-line arguments for the server process.",
        },
        "env": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Environment variables to set for the server process.",
        },
    },
    "required": ["server_name", "command"],
}


@dataclass
class MCPPendingRequest:
    """A pending MCP server connection awaiting user approval."""

    server_name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


_pending_requests: list[MCPPendingRequest] = []


def get_pending_requests() -> list[MCPPendingRequest]:
    """Return the current list of pending MCP connection requests."""
    return list(_pending_requests)


def clear_pending_requests() -> None:
    """Clear all pending requests."""
    _pending_requests.clear()


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    server_name = params["server_name"]
    command = params["command"]
    args = params.get("args", [])
    env = params.get("env", {})

    _pending_requests.append(MCPPendingRequest(
        server_name=server_name,
        command=command,
        args=args,
        env=env,
    ))

    cmd_display = f"{command} {' '.join(args)}".strip()
    return ToolResult.success(
        f"Connection request for MCP server '{server_name}' ({cmd_display}) "
        f"has been queued for user approval. The result will be provided after the user responds."
    )
