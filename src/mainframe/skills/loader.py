"""Skill discovery — scans directories for SKILL.md files."""

from __future__ import annotations

from pathlib import Path

from mainframe.config.paths import skills_dir
from mainframe.skills.manifest import SkillManifest, parse_skill_file

SKILL_FILENAME = "SKILL.md"


def discover_skills(
    extra_dirs: list[Path] | None = None,
) -> list[SkillManifest]:
    """Scan standard and extra directories for SKILL.md files.

    Searches:
    - ~/.local/share/mainframe/skills/*/SKILL.md (user-installed)
    - ./skills/*/SKILL.md (project-local)
    - any extra_dirs passed in
    """
    search_dirs = [
        skills_dir(),
        Path.cwd() / "skills",
    ]
    if extra_dirs:
        search_dirs.extend(extra_dirs)

    skills: list[SkillManifest] = []
    seen_names: set[str] = set()

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue

        for skill_file in sorted(base_dir.glob(f"*/{SKILL_FILENAME}")):
            try:
                manifest = parse_skill_file(skill_file)
                if manifest.name not in seen_names:
                    skills.append(manifest)
                    seen_names.add(manifest.name)
            except Exception:
                # Skip malformed skills silently
                continue

    return skills


def install_skill(source: Path, target_dir: Path | None = None) -> SkillManifest:
    """Install a skill from a source directory to the skills directory.

    The source should be a directory containing a SKILL.md file.
    """
    target_dir = target_dir or skills_dir()

    if source.is_file() and source.name == SKILL_FILENAME:
        source = source.parent

    skill_file = source / SKILL_FILENAME
    if not skill_file.exists():
        raise FileNotFoundError(f"No {SKILL_FILENAME} found in {source}")

    manifest = parse_skill_file(skill_file)
    dest = target_dir / manifest.name
    dest.mkdir(parents=True, exist_ok=True)

    # Copy all files from source to destination
    for item in source.iterdir():
        target = dest / item.name
        if item.is_file():
            target.write_bytes(item.read_bytes())
        elif item.is_dir():
            _copy_dir(item, target)

    # Re-parse from installed location
    return parse_skill_file(dest / SKILL_FILENAME)


def _copy_dir(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_file():
            target.write_bytes(item.read_bytes())
        elif item.is_dir():
            _copy_dir(item, target)
