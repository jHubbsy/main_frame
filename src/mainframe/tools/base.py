"""Tool protocol, ToolResult, ToolContext, and parameter validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class ToolContext:
    """Context passed to every tool execution."""

    session_id: str
    workspace_dir: Path
    config: Any = None
    sandbox_tier: int = 0


@dataclass
class ToolResult:
    """Result returned by a tool execution."""

    content: str
    is_error: bool = False

    @classmethod
    def error(cls, message: str) -> ToolResult:
        return cls(content=message, is_error=True)

    @classmethod
    def success(cls, content: str) -> ToolResult:
        return cls(content=content, is_error=False)


@runtime_checkable
class Tool(Protocol):
    """Protocol for tool implementations."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult: ...


def validate_params(params: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Basic JSON Schema validation. Returns list of error messages."""
    errors: list[str] = []
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for req in required:
        if req not in params:
            errors.append(f"Missing required parameter: {req}")

    for key, value in params.items():
        if key not in properties:
            continue
        prop_schema = properties[key]
        expected_type = prop_schema.get("type")
        if expected_type and not _check_type(value, expected_type):
            actual = type(value).__name__
            errors.append(f"Parameter '{key}' expected '{expected_type}', got {actual}")

    return errors


def _check_type(value: Any, expected: str) -> bool:
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    expected_types = type_map.get(expected)
    if expected_types is None:
        return True
    return isinstance(value, expected_types)
