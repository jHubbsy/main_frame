"""Tool permission policy — allow/deny lists and permission groups."""

from __future__ import annotations

from dataclasses import dataclass, field

# Predefined permission groups
GROUPS: dict[str, list[str]] = {
    "builtin": [
        "bash", "read_file", "write_file", "edit_file",
        "glob_search", "grep_search", "memory_search", "create_skill",
        "web_fetch", "web_search", "connect_mcp",
    ],
    "filesystem": ["read_file", "write_file", "edit_file", "glob_search", "grep_search"],
    "shell": ["bash"],
    "memory": ["memory_search"],
    "web": ["web_fetch", "web_search"],
    "readonly": ["read_file", "glob_search", "grep_search", "memory_search"],
}


@dataclass
class ToolPolicy:
    """Controls which tools are allowed to execute."""

    allowed: set[str] = field(default_factory=set)
    denied: set[str] = field(default_factory=set)
    _mcp_servers: set[str] = field(default_factory=set)

    @classmethod
    def from_groups(cls, groups: list[str]) -> ToolPolicy:
        """Create policy from permission group names."""
        allowed: set[str] = set()
        mcp_servers: set[str] = set()
        for group in groups:
            if group in GROUPS:
                allowed.update(GROUPS[group])
            elif group.startswith("mcp:"):
                mcp_servers.add(group[4:])
            else:
                # Treat as individual tool name
                allowed.add(group)
        return cls(allowed=allowed, _mcp_servers=mcp_servers)

    @classmethod
    def allow_all(cls) -> ToolPolicy:
        """Create a policy that allows everything."""
        return cls()

    def is_allowed(self, tool_name: str) -> bool:
        if tool_name in self.denied:
            return False
        if not self.allowed and not self._mcp_servers:
            return True  # empty allowed = allow all
        if tool_name in self.allowed:
            return True
        # Check MCP server prefix matching
        return any(tool_name.startswith(f"{server}__") for server in self._mcp_servers)

    def allow_mcp_server(self, server_name: str) -> None:
        """Allow all tools from an MCP server by prefix."""
        self._mcp_servers.add(server_name)

    def deny(self, tool_name: str) -> None:
        self.denied.add(tool_name)

    def allow(self, tool_name: str) -> None:
        self.allowed.add(tool_name)
        self.denied.discard(tool_name)
