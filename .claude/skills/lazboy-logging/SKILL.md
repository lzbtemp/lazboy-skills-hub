---
name: lazboy-logging
description: "La-Z-Boy application logging best practices — structured JSON logging, log levels, correlation IDs, security (no PII/secrets), Python logging setup, and observability patterns. Apply this skill whenever writing, reviewing, or debugging logging code for any La-Z-Boy service. Trigger on: logging, logger, log level, structured logs, JSON logs, correlation ID, request ID, tracing, observability, audit trail, log aggregation, python logging, loguru, structlog, or any request to add or improve application logging."
version: "1.0.0"
category: DevOps
tags: [devops, logging, observability, monitoring, structured-logs]
---

# La-Z-Boy Application Logging

Well-designed logging is the difference between a 5-minute and a 5-hour debugging session in production. These standards ensure La-Z-Boy services emit logs that are structured, searchable, safe, and meaningful.

**Reference files — load when needed:**
- `references/python-logging.md` — Python logging module, JSON formatters, contextvars, structlog
- `references/patterns.md` — Structured log schema, correlation IDs, log aggregation, alerting
- `assets/logging_config.py` — Production-ready Python logging setup (copy into new services)
- `assets/logging_middleware.py` — FastAPI request logging middleware with correlation ID injection

---

## 1. Log Levels — Match Severity to Event

Use the right level every time. Misleveling is the #1 cause of noisy, useless logs.

| Level | When to use | Example |
|---|---|---|
| `DEBUG` | Developer diagnostics — disabled in production | SQL query params, internal state |
| `INFO` | Significant business events — enabled in production | Order created, user authenticated |
| `WARNING` | Something unexpected but recoverable | Config fallback used, retry attempt |
| `ERROR` | A specific operation failed — needs investigation | Payment API returned 500 |
| `CRITICAL` | The application cannot continue | DB connection pool exhausted |

```python
logger.debug("Cache miss for key", extra={"key": cache_key})
logger.info("Order placed", extra={"order_id": order.id, "customer_id": customer.id})
logger.warning("Config value missing, using default", extra={"key": "MAX_RETRIES", "default": 3})
logger.error("Payment gateway error", extra={"order_id": order.id, "status": response.status_code}, exc_info=True)
logger.critical("Database connection pool exhausted", extra={"pool_size": config.pool_size})
```

**Rule**: Never log at `ERROR` for expected business flows (e.g., "product not found" is a `WARNING`, not an `ERROR`).

---

## 2. Structured Logging — Always JSON in Production

Unstructured log lines like `"Processing order 12345 for user jane"` are unqueryable. Structured logs with consistent fields let your log aggregator (Datadog, CloudWatch, Splunk) filter, group, and alert.

```python
# Wrong — unstructured, impossible to filter by order_id
logger.info(f"Processing order {order_id} for user {user_id}")

# Correct — structured fields, fully queryable
logger.info("Order processing started", extra={
    "order_id": order_id,
    "user_id": user_id,
    "sku_count": len(order.items),
})
```

### Minimum required fields (every log line)

```json
{
  "timestamp": "2025-01-15T14:32:11.234Z",
  "level": "INFO",
  "logger": "lazboy_orders.service",
  "message": "Order processing started",
  "correlation_id": "req-a1b2c3d4",
  "service": "orders-api",
  "environment": "production"
}
```

Configure once at startup — see `assets/logging_config.py`.

---

## 3. Correlation IDs — Connect the Dots

Without correlation IDs, debugging a request that touches 4 services means grepping 4 separate log streams and mentally joining them. With a correlation ID propagated through every log line and HTTP header, you grep once.

```python
# In the FastAPI middleware (see assets/logging_middleware.py):
# 1. Extract X-Correlation-ID from the incoming request (or generate one)
# 2. Store it in a ContextVar
# 3. The logging filter reads it and injects into every log record automatically

# Result: every log from this request carries the same correlation_id
logger.info("Product fetched from cache", extra={"sku": sku})
# → {"correlation_id": "req-a1b2c3d4", "message": "Product fetched from cache", ...}
```

**Propagation rule**: Pass `X-Correlation-ID` in all outbound HTTP requests to downstream services. Never generate a new one mid-request.

See `references/patterns.md` for the full correlation ID lifecycle.

---

## 4. Security — What NEVER to Log

Logging sensitive data is a security incident waiting to happen. Log files end up in aggregators, S3 buckets, and CI artifacts — all with broader access than production databases.

```python
# NEVER log these
logger.info("User login", extra={
    "password": request.password,     # ❌ credential
    "api_key": config.api_key,        # ❌ secret
    "credit_card": order.card_number, # ❌ PII/PCI
    "ssn": customer.ssn,              # ❌ PII
    "token": auth_token,              # ❌ secret
})

# Log identifiers, not values
logger.info("User login", extra={
    "user_id": user.id,               # ✅ identifier
    "email_domain": email.split("@")[1],  # ✅ non-identifying fragment
    "auth_method": "oauth2",          # ✅ metadata, not credential
})
```

**If you need to log a request body for debugging**: scrub sensitive fields first using a sanitizer utility. See `references/patterns.md` for a `sanitize_payload()` pattern.

---

## 5. Python Setup — One Config, All Services

Configure logging once at application startup. Every `logging.getLogger(__name__)` call across the codebase inherits from it automatically.

```python
# Copy assets/logging_config.py into your service and call setup_logging() at startup
from lazboy_myservice.logging_config import setup_logging

# In your main.py / app factory:
setup_logging(service_name="orders-api", level="INFO")
```

Acquire loggers by module name — never pass loggers as arguments or use a global `logger` shared across modules:

```python
# Each module gets its own logger — correct hierarchy, filterable by module path
import logging
logger = logging.getLogger(__name__)
```

For more: see `references/python-logging.md` — JSON formatters, handler configuration, contextvars integration.

---

## 6. What NOT to Do

- **Never use `print()` for logging** — no levels, no timestamps, no context, no aggregation
- **Never log passwords, tokens, API keys, PII, or card numbers** — security incident risk
- **Never use f-strings in logger calls** — defeats lazy evaluation; use `extra={}` instead
- **Never log at `INFO` for every function call** — noise drowns signal; use `DEBUG`
- **Never catch-and-log-only without re-raising or handling** — silently swallowed errors are worse than crashes
- **Never create unbounded log files without rotation** — disk exhaustion in production
- **Never log to stdout in production without a formatter** — raw stdout is unstructured noise
- **Never skip `exc_info=True` on error logs** — traceback is the most valuable part
