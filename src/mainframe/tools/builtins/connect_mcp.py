"""Connect MCP tool — agent proposes MCP server connections for user approval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult

name = "connect_mcp"
description = (
    "Propose connecting to an MCP server (requires user approval). "
    "Use 'command' for stdio servers (npx, uvx, local binary) or 'url' for HTTP endpoints."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "server_name": {
            "type": "string",
            "description": "Short server identifier (e.g. 'github').",
        },
        "command": {
            "type": "string",
            "description": "Command to launch a stdio server.",
        },
        "args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Arguments for the server command.",
        },
        "env": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Environment variables for the server process.",
        },
        "url": {
            "type": "string",
            "description": "HTTP server URL (user-provided only).",
        },
        "required_env": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Auth env var names; user prompted if missing.",
        },
    },
    "required": ["server_name"],
}


@dataclass
class MCPPendingRequest:
    """A pending MCP server connection awaiting user approval."""

    server_name: str
    # stdio fields
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    required_env: list[str] = field(default_factory=list)
    # HTTP fields
    url: str = ""

    @property
    def transport(self) -> str:
        return "streamable_http" if self.url else "stdio"


_pending_requests: list[MCPPendingRequest] = []


def get_pending_requests() -> list[MCPPendingRequest]:
    return list(_pending_requests)


def clear_pending_requests() -> None:
    _pending_requests.clear()


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    server_name = params["server_name"]
    command = params.get("command", "")
    args = params.get("args", [])
    env = params.get("env", {})
    required_env = params.get("required_env", [])
    url = params.get("url", "")

    if not command and not url:
        return ToolResult.error("Provide either 'command' (stdio) or 'url' (HTTP).")

    _pending_requests.append(MCPPendingRequest(
        server_name=server_name,
        command=command,
        args=args,
        env=env,
        required_env=required_env,
        url=url,
    ))

    display = url or f"{command} {' '.join(args)}".strip()

    return ToolResult.success(
        f"Connection request for MCP server '{server_name}' ({display}) "
        f"has been queued for user approval. The result will be provided after the user responds."
    )
