"""Tests for create_skill action validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from mainframe.tools.builtins.create_skill import _validate_action_code
from mainframe.tools.base import ToolContext, ToolResult


VALID_CODE = """\
from typing import Any
from mainframe.tools.base import ToolContext, ToolResult

name = "my_action"
description = "Does something."
parameters = {"type": "object", "properties": {}, "required": []}

async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    return ToolResult.success("ok")
"""

# --- _validate_action_code ---

def test_valid_action_passes():
    assert _validate_action_code("my_action", VALID_CODE) == []


def test_missing_name_attr():
    code = VALID_CODE.replace('name = "my_action"\n', "")
    errors = _validate_action_code("my_action", code)
    assert any("name" in e for e in errors)


def test_missing_description_attr():
    code = VALID_CODE.replace('description = "Does something."\n', "")
    errors = _validate_action_code("my_action", code)
    assert any("description" in e for e in errors)


def test_missing_parameters_attr():
    code = VALID_CODE.replace(
        'parameters = {"type": "object", "properties": {}, "required": []}\n', ""
    )
    errors = _validate_action_code("my_action", code)
    assert any("parameters" in e for e in errors)


def test_missing_execute():
    code = "\n".join(
        line for line in VALID_CODE.splitlines()
        if not line.startswith("async def execute") and not line.startswith("    return")
    )
    errors = _validate_action_code("my_action", code)
    assert any("execute" in e for e in errors)


def test_sync_execute_rejected():
    code = VALID_CODE.replace("async def execute", "def execute")
    errors = _validate_action_code("my_action", code)
    assert any("async" in e for e in errors)


def test_syntax_error_caught():
    errors = _validate_action_code("bad", "def (((broken syntax")
    assert len(errors) == 1
    assert "import" in errors[0] or "failed" in errors[0]


def test_wrong_name_type():
    code = VALID_CODE.replace('name = "my_action"', "name = 123")
    errors = _validate_action_code("my_action", code)
    assert any("name" in e and "str" in e for e in errors)


def test_wrong_parameters_type():
    code = VALID_CODE.replace(
        'parameters = {"type": "object", "properties": {}, "required": []}',
        'parameters = "not a dict"',
    )
    errors = _validate_action_code("my_action", code)
    assert any("parameters" in e and "dict" in e for e in errors)


# --- execute() integration ---

@pytest.fixture
def ctx(tmp_path: Path) -> ToolContext:
    return ToolContext(session_id="test", workspace_dir=tmp_path)


@pytest.mark.asyncio
async def test_create_skill_rejects_invalid_action(ctx: ToolContext, tmp_path: Path):
    from mainframe.tools.builtins.create_skill import execute as create_skill

    bad_code = "def check_timezone(tz):\n    return {}\n"

    with patch("mainframe.tools.builtins.create_skill.skills_dir", return_value=tmp_path):
        result = await create_skill(
            {
                "skill_name": "bad-skill",
                "description": "test",
                "body": "# test",
                "actions": [{"name": "bad_action", "description": "bad", "code": bad_code}],
            },
            ctx,
        )

    assert result.is_error
    assert "validation failed" in result.content.lower()
    assert not (tmp_path / "bad-skill").exists()


@pytest.mark.asyncio
async def test_create_skill_accepts_valid_action(ctx: ToolContext, tmp_path: Path):
    from mainframe.tools.builtins.create_skill import execute as create_skill

    with patch("mainframe.tools.builtins.create_skill.skills_dir", return_value=tmp_path):
        result = await create_skill(
            {
                "skill_name": "good-skill",
                "description": "test",
                "body": "# test",
                "actions": [
                    {"name": "my_action", "description": "does it", "code": VALID_CODE}
                ],
            },
            ctx,
        )

    assert not result.is_error
    assert (tmp_path / "good-skill" / "actions" / "my_action.py").exists()


@pytest.mark.asyncio
async def test_create_skill_cleans_up_on_write_error(ctx: ToolContext, tmp_path: Path):
    from mainframe.tools.builtins.create_skill import execute as create_skill

    with patch("mainframe.tools.builtins.create_skill.skills_dir", return_value=tmp_path):
        with patch("pathlib.Path.mkdir", side_effect=[None, OSError("disk full")]):
            result = await create_skill(
                {"skill_name": "fail-skill", "description": "x", "body": "# x"},
                ctx,
            )

    assert result.is_error
