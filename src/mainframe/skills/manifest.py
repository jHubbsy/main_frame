"""SkillManifest dataclass and SKILL.md parser.

A skill is a SKILL.md file with YAML frontmatter and markdown body:

---
name: github
version: "1.0.0"
description: "GitHub operations via gh CLI"
sandbox_tier: 1
permissions:
  bins: ["gh"]
  network: false
  filesystem:
    read: ["$WORKSPACE"]
    write: []
signature: "base64-ed25519-sig"
content_hash: "sha256:abc..."
publisher: "mainframe-official"
---
# GitHub Skill
Use the `gh` CLI to interact with GitHub...
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FilesystemPermissions:
    read: list[str] = field(default_factory=list)
    write: list[str] = field(default_factory=list)


@dataclass
class SkillPermissions:
    bins: list[str] = field(default_factory=list)
    network: bool = False
    filesystem: FilesystemPermissions = field(default_factory=FilesystemPermissions)


@dataclass
class SkillManifest:
    name: str
    version: str = "0.0.0"
    description: str = ""
    sandbox_tier: int = 1
    permissions: SkillPermissions = field(default_factory=SkillPermissions)
    signature: str | None = None
    content_hash: str | None = None
    publisher: str | None = None
    body: str = ""  # the markdown content below the frontmatter
    path: Path | None = None  # path to the SKILL.md file
    config: dict[str, Any] = field(default_factory=dict)  # skill-specific config defaults
    requires: list[str] = field(default_factory=list)  # tool groups or skill names

    @property
    def is_signed(self) -> bool:
        return self.signature is not None and self.content_hash is not None

    def compute_content_hash(self) -> str:
        """Compute sha256 hash of the body content."""
        digest = hashlib.sha256(self.body.encode()).hexdigest()
        return f"sha256:{digest}"

    def verify_content_hash(self) -> bool:
        """Check if the stored content_hash matches the actual body."""
        if not self.content_hash:
            return False
        return self.compute_content_hash() == self.content_hash


def parse_skill_file(path: Path) -> SkillManifest:
    """Parse a SKILL.md file into a SkillManifest."""
    text = path.read_text()
    frontmatter, body = _split_frontmatter(text)

    if frontmatter is None:
        raise ValueError(f"No YAML frontmatter found in {path}")

    data = yaml.safe_load(frontmatter)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid frontmatter in {path}: expected a mapping")

    # Parse permissions
    perms_data = data.get("permissions", {})
    fs_data = perms_data.get("filesystem", {})
    permissions = SkillPermissions(
        bins=perms_data.get("bins", []),
        network=perms_data.get("network", False),
        filesystem=FilesystemPermissions(
            read=fs_data.get("read", []),
            write=fs_data.get("write", []),
        ),
    )

    return SkillManifest(
        name=data.get("name", path.parent.name),
        version=str(data.get("version", "0.0.0")),
        description=data.get("description", ""),
        sandbox_tier=data.get("sandbox_tier", 1),
        permissions=permissions,
        signature=data.get("signature"),
        content_hash=data.get("content_hash"),
        publisher=data.get("publisher"),
        body=body.strip(),
        path=path,
        config=data.get("config", {}),
        requires=data.get("requires", []),
    )


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    """Split YAML frontmatter from markdown body."""
    text = text.strip()
    if not text.startswith("---"):
        return None, text

    # Find the closing ---
    end = text.find("---", 3)
    if end == -1:
        return None, text

    frontmatter = text[3:end].strip()
    body = text[end + 3:]
    return frontmatter, body
