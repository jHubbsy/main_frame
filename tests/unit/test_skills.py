"""Tests for skill system."""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from mainframe.skills.loader import discover_skills, install_skill
from mainframe.skills.manifest import SkillManifest, parse_skill_file
from mainframe.skills.registry import SkillRegistry
from mainframe.skills.verifier import SkillVerifier, sign_skill


def _make_skill_md(name: str) -> str:
    return f"""\
---
name: {name}
version: "1.0.0"
description: "A test skill called {name}"
sandbox_tier: 1
permissions:
  bins: ["echo"]
  network: false
---
# {name}
This is the {name} skill body.
"""


def _write_skill(base: Path, name: str) -> Path:
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(_make_skill_md(name))
    return skill_dir


def test_parse_skill_file(tmp_path: Path):
    skill_dir = _write_skill(tmp_path, "my-skill")
    manifest = parse_skill_file(skill_dir / "SKILL.md")
    assert manifest.name == "my-skill"
    assert manifest.version == "1.0.0"
    assert manifest.sandbox_tier == 1
    assert "echo" in manifest.permissions.bins


def test_discover_skills(tmp_path: Path):
    _write_skill(tmp_path, "skill-a")
    _write_skill(tmp_path, "skill-b")
    found = discover_skills(extra_dirs=[tmp_path])
    names = [s.name for s in found]
    assert "skill-a" in names
    assert "skill-b" in names


def test_install_skill(tmp_path: Path):
    source = _write_skill(tmp_path / "source", "installable")
    target = tmp_path / "installed"
    target.mkdir()
    manifest = install_skill(source, target_dir=target)
    assert manifest.name == "installable"
    assert (target / "installable" / "SKILL.md").exists()


def test_skill_registry(tmp_path: Path):
    _write_skill(tmp_path, "reg-skill")
    registry = SkillRegistry()
    registry.load(extra_dirs=[tmp_path])
    assert "reg-skill" in registry.names
    section = registry.build_system_prompt_section()
    assert "reg-skill" in section


def test_sign_and_verify():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    manifest = SkillManifest(name="signed-skill", body="skill content here")
    signature, content_hash = sign_skill(manifest, private_key)
    manifest.signature = signature
    manifest.content_hash = content_hash
    manifest.publisher = "test-pub"

    verifier = SkillVerifier()
    verifier.add_trusted_key("test-pub", public_key)
    assert verifier.verify(manifest) is True


def test_verify_fails_on_tamper():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    manifest = SkillManifest(name="signed-skill", body="original content")
    signature, content_hash = sign_skill(manifest, private_key)
    manifest.signature = signature
    manifest.content_hash = content_hash
    manifest.publisher = "test-pub"

    manifest.body = "tampered content"

    verifier = SkillVerifier()
    verifier.add_trusted_key("test-pub", public_key)
    assert verifier.verify(manifest) is False


def test_content_hash():
    m = SkillManifest(name="test", body="hello world")
    h = m.compute_content_hash()
    assert h.startswith("sha256:")
    m.content_hash = h
    assert m.verify_content_hash() is True
