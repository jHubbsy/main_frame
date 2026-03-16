"""Builtin tool loader — registers all built-in tools as module-level tool objects."""

from __future__ import annotations

from types import ModuleType
from typing import Any

from mainframe.tools.base import ToolContext, ToolResult
from mainframe.tools.builtins import (
    bash,
    create_skill,
    edit_file,
    glob_search,
    grep_search,
    memory_search,
    read_file,
    web_fetch,
    web_search,
    write_file,
)
from mainframe.tools.registry import ToolRegistry


class ModuleTool:
    """Adapts a tool module (with name, description, parameters, execute) to the Tool protocol."""

    def __init__(self, module: ModuleType) -> None:
        self.name: str = module.name
        self.description: str = module.description
        self.parameters: dict[str, Any] = module.parameters
        self._execute = module.execute

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        return await self._execute(params, ctx)


_BUILTIN_MODULES = [
    bash, read_file, write_file, edit_file,
    glob_search, grep_search, memory_search, create_skill,
    web_fetch, web_search,
]


def register_builtins(registry: ToolRegistry) -> None:
    """Register all builtin tools with the given registry."""
    for mod in _BUILTIN_MODULES:
        registry.register(ModuleTool(mod))
