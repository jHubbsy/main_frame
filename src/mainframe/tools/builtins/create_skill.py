"""Create skill tool — lets the agent draft new skills on disk."""

from __future__ import annotations

from typing import Any

from mainframe.config.paths import skills_dir
from mainframe.tools.base import ToolContext, ToolResult

name = "create_skill"
description = (
    "Create a new skill with a SKILL.md manifest and optional action files. "
    "The skill is written to the user skills directory but NOT activated until "
    "the user restarts or explicitly loads it. Returns the path to the created skill."
)
parameters: dict[str, Any] = {
    "type": "object",
    "properties": {
        "skill_name": {
            "type": "string",
            "description": "Name for the skill (lowercase, hyphens ok).",
        },
        "description": {
            "type": "string",
            "description": "Short description of what the skill does.",
        },
        "version": {
            "type": "string",
            "description": "Semantic version string.",
            "default": "0.1.0",
        },
        "sandbox_tier": {
            "type": "integer",
            "description": "Sandbox tier (0=in-process, 1=restricted, 2=container).",
            "default": 1,
        },
        "bins": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Allowed binary names for this skill.",
            "default": [],
        },
        "body": {
            "type": "string",
            "description": "Markdown body content for the skill (instructions, examples).",
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Action name."},
                    "description": {"type": "string", "description": "Action description."},
                    "code": {
                        "type": "string",
                        "description": (
                            "Python source for the action module. "
                            "MUST follow the mainframe action protocol exactly:\n"
                            "  1. Module-level: name: str\n"
                            "  2. Module-level: description: str\n"
                            "  3. Module-level: parameters: dict (JSON Schema object)\n"
                            "  4. async def execute("
                            "params: dict[str, Any], ctx: ToolContext"
                            ") -> ToolResult\n"
                            "     - Return ToolResult.success(str) or"
                            " ToolResult.error(str).\n"
                            "     - Import: from mainframe.tools.base"
                            " import ToolContext, ToolResult\n"
                            "Example skeleton:\n"
                            "  from typing import Any\n"
                            "  from mainframe.tools.base import"
                            " ToolContext, ToolResult\n"
                            "  name = 'my_action'\n"
                            "  description = 'What this action does.'\n"
                            "  parameters = {'type': 'object',"
                            " 'properties': {'arg': {'type': 'string'}},"
                            " 'required': ['arg']}\n"
                            "  async def execute("
                            "params: dict[str, Any], ctx: ToolContext"
                            ") -> ToolResult:\n"
                            "      return ToolResult.success(params['arg'])"
                        ),
                    },
                },
                "required": ["name", "description", "code"],
            },
            "description": "Optional action modules to create in actions/ directory.",
            "default": [],
        },
    },
    "required": ["skill_name", "description", "body"],
}


def _build_skill_md(
    skill_name: str,
    description: str,
    version: str,
    sandbox_tier: int,
    bins: list[str],
    body: str,
) -> str:
    bins_yaml = ", ".join(f'"{b}"' for b in bins)
    return f"""\
---
name: {skill_name}
version: "{version}"
description: "{description}"
sandbox_tier: {sandbox_tier}
permissions:
  bins: [{bins_yaml}]
  network: false
---
{body}
"""


async def execute(params: dict[str, Any], ctx: ToolContext) -> ToolResult:
    skill_name = params["skill_name"]
    description = params["description"]
    version = params.get("version", "0.1.0")
    sandbox_tier = params.get("sandbox_tier", 1)
    bins: list[str] = params.get("bins", [])
    body = params["body"]
    actions: list[dict[str, str]] = params.get("actions", [])

    # Write to user skills dir
    target = skills_dir() / skill_name
    if target.exists():
        return ToolResult.error(
            f"Skill '{skill_name}' already exists at {target}. "
            "Remove it first or choose a different name."
        )

    try:
        target.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        skill_md = _build_skill_md(skill_name, description, version, sandbox_tier, bins, body)
        (target / "SKILL.md").write_text(skill_md)

        # Write action files
        if actions:
            actions_dir = target / "actions"
            actions_dir.mkdir(exist_ok=True)
            for action in actions:
                action_file = actions_dir / f"{action['name']}.py"
                action_file.write_text(action["code"])

    except Exception as e:
        return ToolResult.error(f"Failed to create skill: {e}")

    parts = [f"Created skill '{skill_name}' at {target}"]
    if actions:
        parts.append(f"with {len(actions)} action(s)")
    parts.append("Restart or reload to activate.")
    return ToolResult.success(" ".join(parts))
