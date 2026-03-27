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
            "description": "A short identifier for the server (e.g. 'github', 'postgres').",
        },
        "command": {
            "type": "string",
            "description": "The executable command to launch a stdio MCP server.",
        },
        "args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Command-line arguments for a stdio server process.",
        },
        "env": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Environment variables to set for a stdio server process.",
        },
        "url": {
            "type": "string",
            "description": "URL for an HTTP-based MCP server. Only use if explicitly provided by the user.",
        },
        "required_env": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Env var names the server needs for auth. User will be prompted for missing values.",
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
