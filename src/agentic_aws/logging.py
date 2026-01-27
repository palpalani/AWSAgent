"""Structured logging configuration for the Agentic AWS package."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import MutableMapping


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_record["data"] = record.extra_data

        return json.dumps(log_record)


class ContextLogger(logging.LoggerAdapter[logging.Logger]):
    """Logger adapter that adds context to log messages."""

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        extra = dict(kwargs.get("extra", {}))
        context_data = dict(self.extra) if self.extra else {}
        existing_extra = extra.get("extra_data", {})
        if isinstance(existing_extra, dict):
            extra["extra_data"] = {**context_data, **existing_extra}
        else:
            extra["extra_data"] = context_data
        kwargs["extra"] = extra

        return msg, kwargs


def get_logger(name: str, context: dict[str, Any] | None = None) -> ContextLogger:
    """Get a logger with optional context.

    Args:
        name: Logger name, typically __name__
        context: Optional context dict to include in all log messages

    Returns:
        A ContextLogger instance
    """
    logger = logging.getLogger(name)
    return ContextLogger(logger, context or {})


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
) -> None:
    """Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    root_logger.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
