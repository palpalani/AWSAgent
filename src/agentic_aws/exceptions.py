"""Custom exceptions for the Agentic AWS package."""


class AWSAgentError(Exception):
    """Base exception for all AWS Agent errors."""


class AWSConnectionError(AWSAgentError):
    """Raised when AWS connection fails."""


class ToolExecutionError(AWSAgentError):
    """Raised when a tool execution fails."""
