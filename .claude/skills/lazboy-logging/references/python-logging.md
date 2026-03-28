# Python Logging — Deep Dive

## JSON Formatter

Python's default `logging` module emits plaintext. In production, override the formatter to emit JSON so log aggregators can parse fields without brittle regex.

```python
import json
import logging
import traceback
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for log aggregators."""

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

        # Inject correlation_id from record (set by CorrelationIdFilter)
        if hasattr(record, "correlation_id"):
            payload["correlation_id"] = record.correlation_id

        # Include any extra= fields passed by the caller
        for key, val in record.__dict__.items():
            if key not in _LOGGING_RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = val

        # Include exception traceback as a structured field, not embedded in message
        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }
            record.exc_info = None  # prevent duplicate in default formatting

        return json.dumps(payload, default=str)


_LOGGING_RESERVED_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message",
})
```

---

## CorrelationId Filter (contextvars integration)

```python
import logging
from contextvars import ContextVar

# Module-level ContextVar — safe for async code (each request/task has its own copy)
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


class CorrelationIdFilter(logging.Filter):
    """Injects correlation_id from ContextVar into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get()
        return True
```

**Why `ContextVar` instead of `threading.local`**: `ContextVar` is safe in both sync and async code. In async frameworks (FastAPI, asyncio), each `asyncio.Task` inherits a copy of the context — correlation IDs don't bleed between concurrent requests.

---

## Handler Configuration

```python
import logging
import sys


def configure_handlers(
    formatter: logging.Formatter,
    level: int,
) -> list[logging.Handler]:
    """Returns production handler list. Swap stdout for a file/socket handler if needed."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return [handler]
```

**Handler types and when to use them:**

| Handler | Use case |
|---|---|
| `StreamHandler(sys.stdout)` | Containerized apps — let the platform collect stdout |
| `RotatingFileHandler` | Non-containerized; set `maxBytes=50MB, backupCount=5` |
| `TimedRotatingFileHandler` | Legacy apps needing daily log files |
| Custom / socket handler | Shipping directly to Logstash, Fluentd, or a SIEM |

---

## structlog (optional — recommended for complex services)

`structlog` adds a processing pipeline on top of Python's `logging`, making it easier to add context processors (like auto-injecting service metadata) without writing a custom `Formatter`.

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # pulls in bound context
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),  # final step: emit JSON
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

# Bind request-scoped context (survives across awaits in the same task)
structlog.contextvars.bind_contextvars(
    correlation_id="req-a1b2c3d4",
    user_id=user.id,
)

log = structlog.get_logger()
log.info("Order placed", order_id=order.id)
# → {"correlation_id": "req-a1b2c3d4", "user_id": 42, "order_id": 99, ...}
```

Use `structlog` when: your service has many layers (middleware → service → repo) and you want to bind context once at the request level rather than passing `extra={}` everywhere.

---

## Log Level by Environment

```python
import os
import logging

def resolve_log_level() -> int:
    env = os.getenv("ENVIRONMENT", "development").lower()
    level_name = os.getenv("LOG_LEVEL", "DEBUG" if env == "development" else "INFO").upper()
    return getattr(logging, level_name, logging.INFO)
```

| Environment | Recommended level | Why |
|---|---|---|
| Development | `DEBUG` | Full visibility for local debugging |
| Staging | `INFO` | Production-like, but retain info logs |
| Production | `INFO` | Signal without noise; `DEBUG` only via env override |

---

## Log Rotation for Non-Container Deployments

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    filename="/var/log/lazboy/service.log",
    maxBytes=50 * 1024 * 1024,   # 50 MB per file
    backupCount=5,                # keep 5 rotated files → max 300 MB total
    encoding="utf-8",
)
```

For containerized services (Docker / Kubernetes), skip file handlers entirely — write to stdout and let the platform's log driver (Fluentd, CloudWatch, Datadog agent) handle collection and rotation.
