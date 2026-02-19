"""Tool permission policy — allow/deny lists and permission groups."""

from __future__ import annotations

from dataclasses import dataclass, field

# Predefined permission groups
GROUPS: dict[str, list[str]] = {
    "builtin": [
        "bash", "read_file", "write_file", "edit_file",
        "glob_search", "grep_search",
    ],
    "filesystem": ["read_file", "write_file", "edit_file", "glob_search", "grep_search"],
    "shell": ["bash"],
    "readonly": ["read_file", "glob_search", "grep_search"],
}


@dataclass
class ToolPolicy:
    """Controls which tools are allowed to execute."""

    allowed: set[str] = field(default_factory=set)
    denied: set[str] = field(default_factory=set)

    @classmethod
    def from_groups(cls, groups: list[str]) -> ToolPolicy:
        """Create policy from permission group names."""
        allowed: set[str] = set()
        for group in groups:
            if group in GROUPS:
                allowed.update(GROUPS[group])
            else:
                # Treat as individual tool name
                allowed.add(group)
        return cls(allowed=allowed)

    @classmethod
    def allow_all(cls) -> ToolPolicy:
        """Create a policy that allows everything."""
        return cls()

    def is_allowed(self, tool_name: str) -> bool:
        if tool_name in self.denied:
            return False
        if not self.allowed:
            return True  # empty allowed = allow all
        return tool_name in self.allowed

    def deny(self, tool_name: str) -> None:
        self.denied.add(tool_name)

    def allow(self, tool_name: str) -> None:
        self.allowed.add(tool_name)
        self.denied.discard(tool_name)
