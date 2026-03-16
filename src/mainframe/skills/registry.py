"""Installed skills catalog and system prompt injection."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from mainframe.skills.actions import SkillAction, discover_actions
from mainframe.skills.loader import discover_skills
from mainframe.skills.manifest import SkillManifest
from mainframe.tools.registry import ToolRegistry

log = logging.getLogger(__name__)


class SkillRegistry:
    """Manages discovered skills and generates system prompt context."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillManifest] = {}
        self._actions: dict[str, SkillAction] = {}
        self._warnings: list[str] = []

    def load(
        self,
        extra_dirs: list[Path] | None = None,
        skill_configs: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Discover and load all available skills and their actions."""
        for skill in discover_skills(extra_dirs):
            # Apply user config overrides
            if skill_configs and skill.name in skill_configs:
                skill.config.update(skill_configs[skill.name])
            self._skills[skill.name] = skill
            for action in discover_actions(skill):
                self._actions[action.name] = action

        self._validate_requires()

    def register(self, skill: SkillManifest) -> None:
        self._skills[skill.name] = skill
        for action in discover_actions(skill):
            self._actions[action.name] = action

    def get(self, name: str) -> SkillManifest | None:
        return self._skills.get(name)

    @property
    def names(self) -> list[str]:
        return list(self._skills.keys())

    @property
    def skills(self) -> list[SkillManifest]:
        return list(self._skills.values())

    @property
    def actions(self) -> list[SkillAction]:
        return list(self._actions.values())

    def register_tools(self, tool_registry: ToolRegistry) -> None:
        """Register all skill actions as tools in a ToolRegistry."""
        for action in self._actions.values():
            tool_registry.register_skill_action(action)

    def build_system_prompt_section(self) -> str:
        """Generate a system prompt section describing available skills."""
        if not self._skills:
            return ""

        lines = ["\n## Available Skills\n"]
        for skill in self._skills.values():
            lines.append(f"### {skill.name} (v{skill.version})")
            if skill.description:
                lines.append(skill.description)
            if skill.body:
                lines.append(skill.body)
            lines.append("")

        return "\n".join(lines)

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)

    def _validate_requires(self) -> None:
        """Check that all skill dependencies are satisfied."""
        from mainframe.tools.policy import GROUPS

        available = set(self._skills.keys()) | set(GROUPS.keys())
        for skill in self._skills.values():
            for req in skill.requires:
                if req not in available:
                    msg = f"Skill '{skill.name}' requires '{req}' which is not available"
                    self._warnings.append(msg)
                    log.warning(msg)

    def get_skill_context(self, name: str) -> str | None:
        """Get the full body content of a skill for injection into context."""
        skill = self._skills.get(name)
        if skill is None:
            return None
        return skill.body
