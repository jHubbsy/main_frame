"""Pydantic settings model for Mainframe configuration."""

from __future__ import annotations

from typing import Literal

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
    sanitize_level: Literal["off", "warn", "isolate"] = "isolate"


class SessionConfig(BaseModel):
    max_turns: int = 100
    auto_compact: bool = True
    compact_threshold: int = 50


class MCPOAuthConfig(BaseModel):
    redirect_port: int = 8765
    scopes: list[str] = Field(default_factory=list)


class MCPServerConfig(BaseModel):
    transport: Literal["stdio", "streamable_http"] = "stdio"
    # stdio fields
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    required_env: list[str] = Field(default_factory=list)
    # HTTP fields
    url: str | None = None
    oauth: MCPOAuthConfig | None = None


class MCPConfig(BaseModel):
    enabled: bool = True
    servers: dict[str, MCPServerConfig] = Field(default_factory=dict)


class MainframeConfig(BaseModel):
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    system_prompt: str = (
        "You are Mainframe, a capable AI assistant. "
        "You help users with software engineering tasks. "
        "Be concise, accurate, and helpful."
    )
    # Per-skill config overrides: {"skill_name": {"key": "value"}}
    skills: dict[str, dict[str, object]] = Field(default_factory=dict)
