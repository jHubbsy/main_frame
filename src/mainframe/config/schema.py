"""Pydantic settings model for Mainframe configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    name: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7


class SecurityConfig(BaseModel):
    max_sandbox_tier: int = Field(default=1, ge=0, le=2)
    require_skill_signatures: bool = False
    allowed_tool_groups: list[str] = Field(default_factory=lambda: ["builtin"])


class SessionConfig(BaseModel):
    max_turns: int = 100
    auto_compact: bool = True
    compact_threshold: int = 50


class MainframeConfig(BaseModel):
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    system_prompt: str = (
        "You are Mainframe, a capable AI assistant. "
        "You help users with software engineering tasks. "
        "Be concise, accurate, and helpful."
    )
