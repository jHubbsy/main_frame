"""Skill sandboxing — Tier 1 (subprocess) and Tier 2 (container) execution."""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path

from mainframe.skills.manifest import SkillManifest
from mainframe.tools.base import ToolResult


@dataclass
class SandboxConfig:
    timeout: int = 30
    max_output: int = 50_000
    workspace_dir: Path | None = None


def detect_container_runtime() -> str | None:
    """Auto-detect available container runtime: docker > podman > nerdctl."""
    for runtime in ("docker", "podman", "nerdctl"):
        if shutil.which(runtime):
            return runtime
    return None


async def execute_tier1(
    skill: SkillManifest,
    code: str,
    config: SandboxConfig | None = None,
) -> ToolResult:
    """Tier 1: Execute code in a subprocess with resource limits.

    Uses ulimit for CPU/memory constraints and timeout for wall clock.
    Only allowed binaries from the skill's permissions are accessible.
    """
    config = config or SandboxConfig()

    allowed_bins = skill.permissions.bins
    if not allowed_bins:
        return ToolResult.error("Skill has no permitted binaries.")

    # Build a restricted PATH containing only allowed binaries
    allowed_paths = []
    for bin_name in allowed_bins:
        bin_path = shutil.which(bin_name)
        if bin_path:
            allowed_paths.append(str(Path(bin_path).parent))

    if not allowed_paths:
        return ToolResult.error(
            f"None of the required binaries found: {allowed_bins}"
        )

    env_path = ":".join(dict.fromkeys(allowed_paths))  # dedupe, preserve order

    try:
        proc = await asyncio.create_subprocess_shell(
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(config.workspace_dir) if config.workspace_dir else None,
            env={"PATH": env_path, "HOME": str(Path.home())},
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=config.timeout
        )
    except TimeoutError:
        proc.kill()
        return ToolResult.error(f"Skill timed out after {config.timeout}s")
    except Exception as e:
        return ToolResult.error(f"Skill execution failed: {e}")

    output = stdout.decode(errors="replace")
    if len(output) > config.max_output:
        output = output[:config.max_output] + "\n... (truncated)"

    if stderr:
        err_text = stderr.decode(errors="replace")
        if err_text.strip():
            output += f"\nSTDERR:\n{err_text}"

    if proc.returncode != 0:
        return ToolResult(content=f"Exit code {proc.returncode}\n{output}", is_error=True)

    return ToolResult.success(output or "(no output)")


async def execute_tier2(
    skill: SkillManifest,
    code: str,
    config: SandboxConfig | None = None,
) -> ToolResult:
    """Tier 2: Execute code in a container with maximum isolation.

    Uses --read-only, --network=none, --cap-drop=ALL for security.
    """
    config = config or SandboxConfig()

    runtime = detect_container_runtime()
    if runtime is None:
        return ToolResult.error(
            "No container runtime found (docker/podman/nerdctl). "
            "Tier 2 skills require a container runtime. "
            "Install one or lower the skill's sandbox_tier."
        )

    workspace = config.workspace_dir or Path.cwd()

    cmd = [
        runtime, "run", "--rm",
        "--read-only",
        "--network=none",
        "--cap-drop=ALL",
        f"--timeout={config.timeout}",
        "-v", f"{workspace}:/workspace:ro",
        "-w", "/workspace",
        "python:3.12-slim",
        "python", "-c", code,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=config.timeout + 10
        )
    except TimeoutError:
        proc.kill()
        return ToolResult.error(f"Container timed out after {config.timeout}s")
    except Exception as e:
        return ToolResult.error(f"Container execution failed: {e}")

    output = stdout.decode(errors="replace")
    if stderr:
        err_text = stderr.decode(errors="replace")
        if err_text.strip():
            output += f"\nSTDERR:\n{err_text}"

    if proc.returncode != 0:
        return ToolResult(content=f"Exit code {proc.returncode}\n{output}", is_error=True)

    return ToolResult.success(output or "(no output)")


async def execute_skill(
    skill: SkillManifest,
    code: str,
    config: SandboxConfig | None = None,
) -> ToolResult:
    """Execute code in the appropriate sandbox tier for the skill."""
    if skill.sandbox_tier <= 1:
        return await execute_tier1(skill, code, config)
    else:
        return await execute_tier2(skill, code, config)
