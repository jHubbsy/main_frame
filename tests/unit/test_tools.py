"""Tests for tool system."""

from __future__ import annotations

from pathlib import Path

import pytest

from mainframe.tools.base import ToolContext, validate_params
from mainframe.tools.builtins import register_builtins
from mainframe.tools.policy import ToolPolicy
from mainframe.tools.registry import ToolRegistry


@pytest.fixture
def ctx(tmp_path: Path) -> ToolContext:
    return ToolContext(session_id="test", workspace_dir=tmp_path)


@pytest.fixture
def registry() -> ToolRegistry:
    r = ToolRegistry()
    register_builtins(r)
    return r


def test_registry_has_all_builtins(registry: ToolRegistry):
    expected = {"bash", "read_file", "write_file", "edit_file", "glob_search", "grep_search"}
    assert set(registry.names) == expected


def test_policy_from_groups():
    policy = ToolPolicy.from_groups(["readonly"])
    assert policy.is_allowed("read_file")
    assert not policy.is_allowed("bash")


def test_validate_params_missing_required():
    schema = {"required": ["path"], "properties": {"path": {"type": "string"}}}
    errors = validate_params({}, schema)
    assert any("path" in e for e in errors)


@pytest.mark.asyncio
async def test_read_file(registry: ToolRegistry, ctx: ToolContext):
    (ctx.workspace_dir / "test.txt").write_text("hello\nworld\n")
    result = await registry.execute("read_file", {"path": "test.txt"}, ctx)
    assert not result.is_error
    assert "hello" in result.content


@pytest.mark.asyncio
async def test_write_file(registry: ToolRegistry, ctx: ToolContext):
    result = await registry.execute("write_file", {"path": "out.txt", "content": "data"}, ctx)
    assert not result.is_error
    assert (ctx.workspace_dir / "out.txt").read_text() == "data"


@pytest.mark.asyncio
async def test_edit_file(registry: ToolRegistry, ctx: ToolContext):
    (ctx.workspace_dir / "edit.txt").write_text("foo bar baz")
    result = await registry.execute("edit_file", {
        "path": "edit.txt", "old_string": "bar", "new_string": "qux",
    }, ctx)
    assert not result.is_error
    assert (ctx.workspace_dir / "edit.txt").read_text() == "foo qux baz"


@pytest.mark.asyncio
async def test_glob_search(registry: ToolRegistry, ctx: ToolContext):
    (ctx.workspace_dir / "a.py").write_text("")
    (ctx.workspace_dir / "b.txt").write_text("")
    result = await registry.execute("glob_search", {"pattern": "*.py"}, ctx)
    assert not result.is_error
    assert "a.py" in result.content
    assert "b.txt" not in result.content


@pytest.mark.asyncio
async def test_grep_search(registry: ToolRegistry, ctx: ToolContext):
    (ctx.workspace_dir / "code.py").write_text("def hello():\n    pass\n")
    result = await registry.execute("grep_search", {"pattern": "def hello"}, ctx)
    assert not result.is_error
    assert "hello" in result.content


@pytest.mark.asyncio
async def test_bash(registry: ToolRegistry, ctx: ToolContext):
    result = await registry.execute("bash", {"command": "echo test123"}, ctx)
    assert not result.is_error
    assert "test123" in result.content
