"""Tests for config system."""

from __future__ import annotations

from pathlib import Path

from mainframe.config.loader import load_config
from mainframe.config.schema import MainframeConfig


def test_default_config():
    config = MainframeConfig()
    assert config.provider.name == "anthropic"
    assert config.provider.max_tokens == 4096
    assert config.security.max_sandbox_tier == 1


def test_load_config_missing_file(tmp_path: Path):
    config = load_config(tmp_path / "nonexistent.toml")
    assert config.provider.name == "anthropic"


def test_load_config_from_toml(tmp_path: Path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_text("""
[provider]
model = "claude-opus-4-20250514"
max_tokens = 8192
""")
    config = load_config(toml_file)
    assert config.provider.model == "claude-opus-4-20250514"
    assert config.provider.max_tokens == 8192


def test_env_overlay(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MAINFRAME_MODEL", "test-model")
    config = load_config(tmp_path / "nonexistent.toml")
    assert config.provider.model == "test-model"
