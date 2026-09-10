import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.config import settings

# Correlation Context Variables
request_id_var: ContextVar[str] = ContextVar("request_id_var", default="")
analysis_id_var: ContextVar[str] = ContextVar("analysis_id_var", default="")

# Sensitive data sanitization patterns
SENSITIVE_PATTERNS = [
    (re.compile(r"(?i)(password|secret|token|api_key|access_token)\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?"), r"\1: [REDACTED]"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"), "Bearer [REDACTED]"),
    (re.compile(r"([a-zA-Z0-9+.-]+://[^:]+):([^@]+)@"), r"\1:[REDACTED]@"),
]


def sanitize_sensitive_data(text: str) -> str:
    """Sanitizes tokens, passwords, and sensitive keys from log strings."""
    if not isinstance(text, str):
        return text
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class SensitiveDataFilter(logging.Filter):
    """Logging filter that scrubs sensitive credentials from record messages and arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_sensitive_data(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize_sensitive_data(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    sanitize_sensitive_data(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON documents."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_var.get("")
        analysis_id = analysis_id_var.get("")

        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        if req_id:
            log_data["request_id"] = req_id
        if analysis_id:
            log_data["analysis_id"] = analysis_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ContextAwareTextFormatter(logging.Formatter):
    """Text log formatter that embeds correlation IDs when present."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_var.get("")
        prefix = f"[{req_id}] " if req_id else ""
        record.request_prefix = prefix
        return super().format(record)


def setup_logging() -> None:
    """Configures application-wide logging with the appropriate formatter and filters."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.addFilter(SensitiveDataFilter())

    if settings.LOG_FORMAT == "json":
        stream_handler.setFormatter(StructuredJsonFormatter())
    else:
        stream_handler.setFormatter(
            ContextAwareTextFormatter(
                "%(asctime)s | %(levelname)-8s | %(request_prefix)s%(name)s:%(funcName)s:%(lineno)d - %(message)s"
            )
        )

    root_logger.addHandler(stream_handler)

    # Silence verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
