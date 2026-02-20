"""Installed skills catalog and system prompt injection."""

from __future__ import annotations

from pathlib import Path

from mainframe.skills.loader import discover_skills
from mainframe.skills.manifest import SkillManifest


class SkillRegistry:
    """Manages discovered skills and generates system prompt context."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillManifest] = {}

    def load(self, extra_dirs: list[Path] | None = None) -> None:
        """Discover and load all available skills."""
        for skill in discover_skills(extra_dirs):
            self._skills[skill.name] = skill

    def register(self, skill: SkillManifest) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillManifest | None:
        return self._skills.get(name)

    @property
    def names(self) -> list[str]:
        return list(self._skills.keys())

    @property
    def skills(self) -> list[SkillManifest]:
        return list(self._skills.values())

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

    def get_skill_context(self, name: str) -> str | None:
        """Get the full body content of a skill for injection into context."""
        skill = self._skills.get(name)
        if skill is None:
            return None
        return skill.body
