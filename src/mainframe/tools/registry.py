"""Tool collection, lookup, and execution dispatch."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mainframe.core.errors import ToolNotFoundError
from mainframe.providers.base import ToolDefinition
from mainframe.tools.base import Tool, ToolContext, ToolResult, validate_params

if TYPE_CHECKING:
    from mainframe.skills.actions import SkillAction


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def register_skill_action(self, action: SkillAction) -> None:
        """Register a SkillAction as a tool (duck-typed, same interface)."""
        self._tools[action.name] = action  # type: ignore[assignment]

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool not found: {name}")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    @property
    def names(self) -> list[str]:
        return list(self._tools.keys())

    def to_definitions(self) -> list[ToolDefinition]:
        """Convert all tools to provider-compatible definitions."""
        return [
            ToolDefinition(
                name=t.name,
                description=t.description,
                input_schema=t.parameters,
            )
            for t in self._tools.values()
        ]

    async def execute(
        self, name: str, params: dict[str, Any], ctx: ToolContext
    ) -> ToolResult:
        tool = self.get(name)

        errors = validate_params(params, tool.parameters)
        if errors:
            return ToolResult.error(f"Parameter validation failed: {'; '.join(errors)}")

        try:
            return await tool.execute(params, ctx)
        except Exception as e:
            return ToolResult.error(f"Tool execution failed: {e}")
