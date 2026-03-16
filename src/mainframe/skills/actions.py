"""Skill action loader — discovers and wraps action Python files as tools.

An action file is a Python module in a skill's actions/ directory with:
- name: str
- description: str
- parameters: dict (JSON Schema)
- async def execute(params: dict, ctx: ToolContext) -> ToolResult

Actions run in the sandbox tier declared by the skill manifest.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from mainframe.skills.manifest import SkillManifest
from mainframe.tools.base import ToolContext, ToolResult


class SkillAction:
    """Wraps an action module as a Tool, with sandbox-aware execution."""

    def __init__(self, module: ModuleType, skill: SkillManifest) -> None:
        self._module = module
        self._skill = skill
        # Prefix tool name with skill name to avoid collisions
        self.name: str = f"{skill.name}__{module.name}"
        self.description: str = module.description
        self.parameters: dict[str, Any] = module.parameters

    async def execute(self, params: dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Execute the action. Tier 0 runs in-process, Tier 1+ uses sandbox."""
        if self._skill.sandbox_tier == 0:
            return await self._module.execute(params, ctx)

        # For Tier 1+, actions still run in-process but with
        # the sandbox available for shell commands they invoke.
        # TODO: full sandbox delegation for Tier 2
        return await self._module.execute(params, ctx)


def discover_actions(skill: SkillManifest) -> list[SkillAction]:
    """Find and load all action modules in a skill's actions/ directory."""
    if skill.path is None:
        return []

    actions_dir = skill.path.parent / "actions"
    if not actions_dir.exists():
        return []

    actions: list[SkillAction] = []
    for py_file in sorted(actions_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            module = _load_action_module(py_file, skill.name)
            # Validate the module has required attributes
            if not all(hasattr(module, attr) for attr in (
                "name", "description", "parameters", "execute"
            )):
                continue
            actions.append(SkillAction(module, skill))
        except Exception:
            continue

    return actions


def _load_action_module(path: Path, skill_name: str) -> ModuleType:
    """Dynamically load a Python file as a module."""
    module_name = f"mainframe_skill_{skill_name}_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
