"""
La-Z-Boy standard logging configuration.

Usage:
    from lazboy_myservice.logging_config import setup_logging
    setup_logging(service_name="orders-api")

Copy this file into your service's src/lazboy_<service>/ directory.
"""

import json
import logging
import os
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Correlation ID — module-level ContextVar (safe for asyncio and threads)
# ---------------------------------------------------------------------------

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


# ---------------------------------------------------------------------------
# Filter — injects correlation_id into every log record automatically
# ---------------------------------------------------------------------------

class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get()
        return True


# ---------------------------------------------------------------------------
# Formatter — emits single-line JSON
# ---------------------------------------------------------------------------

_RESERVED = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
})


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
        }

        correlation_id = getattr(record, "correlation_id", "")
        if correlation_id:
            payload["correlation_id"] = correlation_id

        # Include caller-supplied extra= fields
        for key, val in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = val

        # Structured exception — traceback as a field, not embedded in message
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            payload["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value),
                "traceback": traceback.format_exception(*record.exc_info),
            }
            record.exc_info = None  # prevent double-rendering by StreamHandler

        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Setup function — call once at application startup
# ---------------------------------------------------------------------------

def setup_logging(
    service_name: str,
    level: str | None = None,
    environment: str | None = None,
) -> None:
    """
    Configure root logger with JSON output and correlation ID injection.

    Args:
        service_name: Identifies your service in every log line (e.g. "orders-api").
        level: Override log level. Defaults to LOG_LEVEL env var, or INFO in production
               and DEBUG in development.
        environment: Defaults to ENVIRONMENT env var, or "development".
    """
    env = environment or os.getenv("ENVIRONMENT", "development")
    default_level = "DEBUG" if env == "development" else "INFO"
    resolved_level = (level or os.getenv("LOG_LEVEL", default_level)).upper()
    numeric_level = getattr(logging, resolved_level, logging.INFO)

    formatter = JsonFormatter(service_name=service_name, environment=env)
    filter_ = CorrelationIdFilter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(filter_)
    handler.setLevel(numeric_level)

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
