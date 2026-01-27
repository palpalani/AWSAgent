"""Agentic AWS - AI-powered AWS infrastructure management."""

__version__ = "0.1.0"

from agentic_aws.agent import AWSAgenticAgent
from agentic_aws.cli import run_api, run_chat
from agentic_aws.config import AWSConfig
from agentic_aws.exceptions import AWSAgentError, AWSConnectionError, ToolExecutionError
from agentic_aws.logging import get_logger, setup_logging
from agentic_aws.models import (
    AWSResourceInput,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CloudWatchResult,
    OperationProgress,
    OperationResult,
)
from agentic_aws.processor import get_agent, process_request

__all__ = [
    "AWSAgenticAgent",
    "AWSConfig",
    "AWSAgentError",
    "AWSConnectionError",
    "AWSResourceInput",
    "ToolExecutionError",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "OperationProgress",
    "OperationResult",
    "CloudWatchResult",
    "get_agent",
    "get_logger",
    "process_request",
    "run_api",
    "run_chat",
    "setup_logging",
]
