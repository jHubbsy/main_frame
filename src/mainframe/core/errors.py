"""Exception hierarchy for Mainframe."""

from __future__ import annotations


class MainframeError(Exception):
    """Base exception for all Mainframe errors."""


class ConfigError(MainframeError):
    """Configuration-related errors."""


class ProviderError(MainframeError):
    """LLM provider errors."""


class AuthenticationError(ProviderError):
    """Invalid or missing API credentials."""


class RateLimitError(ProviderError):
    """Provider rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ToolError(MainframeError):
    """Tool execution errors."""


class ToolNotFoundError(ToolError):
    """Requested tool does not exist."""


class ToolPermissionError(ToolError):
    """Tool execution denied by policy."""


class SessionError(MainframeError):
    """Session management errors."""


class SecurityError(MainframeError):
    """Security-related errors."""


class CredentialError(SecurityError):
    """Credential storage/retrieval errors."""


class SkillError(MainframeError):
    """Skill system errors."""


class SandboxError(SkillError):
    """Sandbox execution errors."""
