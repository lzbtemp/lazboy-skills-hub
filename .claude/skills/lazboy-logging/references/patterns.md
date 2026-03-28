# Logging Patterns — Cross-Language Reference

## Structured Log Schema

Every log line from a La-Z-Boy service should include these fields. Consistent field names across all services enable unified queries in the log aggregator.

```json
{
  "timestamp":      "2025-01-15T14:32:11.234Z",   // ISO 8601 UTC — never local time
  "level":          "INFO",                         // DEBUG | INFO | WARNING | ERROR | CRITICAL
  "logger":         "lazboy_orders.service",        // module path (Python: __name__)
  "message":        "Order processing started",     // human-readable summary
  "service":        "orders-api",                   // service name from config
  "environment":    "production",                   // development | staging | production
  "correlation_id": "req-a1b2c3d4",                // see Correlation IDs section
  "version":        "1.4.2",                        // app version (optional but useful)

  // Event-specific context — add relevant fields per log call:
  "order_id":       "ORD-9921",
  "user_id":        4821,
  "duration_ms":    143
}
```

**Never embed context in the message string.** Fields in the `extra` dict (Python) or structured key-value pairs are indexed and searchable; message strings are not.

---

## Correlation ID Lifecycle

A correlation ID connects all log lines — across services, async tasks, and retries — that belong to the same user-initiated request.

```
Client ──► API Gateway ──► orders-api ──► inventory-api ──► database
            generates        propagates     propagates
            X-Correlation-ID → header    → header
```

### Rules

1. **Generate at the edge** (API Gateway or the first service to receive the request)
2. **Extract or generate** in middleware: `X-Correlation-ID` header → if missing, generate `uuid4()`
3. **Store in `ContextVar`** (Python) or async-local storage so it's available everywhere without being passed as a parameter
4. **Inject into all outbound HTTP calls** as the `X-Correlation-ID` request header
5. **Return in HTTP response** so clients can report it in support tickets

```python
import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

def get_or_generate_correlation_id(header_value: str | None) -> str:
    return header_value or f"req-{uuid.uuid4().hex[:12]}"
```

### Propagating to downstream HTTP calls

```python
import httpx

async def call_inventory(sku: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{INVENTORY_API}/products/{sku}",
            headers={"X-Correlation-ID": get_correlation_id()},  # always propagate
        )
    return response.json()
```

---

## What to Log at Each Application Layer

### HTTP layer (middleware)
Log every request and response with timing. This is the outer envelope — it tells you what happened, how long it took, and whether it succeeded.

```json
{
  "message": "HTTP request completed",
  "method": "POST",
  "path": "/api/orders",
  "status_code": 201,
  "duration_ms": 143,
  "correlation_id": "req-a1b2c3d4"
}
```

### Service layer (business logic)
Log significant business events — not every method call, but the decisions and outcomes that matter.

```json
{"message": "Order validated", "order_id": "ORD-9921", "item_count": 3}
{"message": "Inventory reservation failed", "sku": "LZB-001", "requested_qty": 2, "available_qty": 0}
```

### Repository layer (data access)
Log slow queries and failures, not individual queries.

```json
{"message": "Slow query detected", "query": "find_orders_by_customer", "duration_ms": 412, "threshold_ms": 200}
```

### Background jobs / workers
Log job start, completion, and failures with enough context to restart from a checkpoint.

```json
{"message": "Sync job started", "job_id": "sync-20250115", "record_count": 1842}
{"message": "Sync job completed", "job_id": "sync-20250115", "processed": 1840, "failed": 2, "duration_ms": 12300}
```

---

## Sanitizing Payloads Before Logging

When you need to log a request body for debugging, scrub sensitive fields first. Never log the raw body.

```python
_SENSITIVE_KEYS = frozenset({
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "authorization", "auth", "credit_card", "card_number", "cvv",
    "ssn", "social_security", "dob", "date_of_birth",
})

def sanitize_payload(data: dict, redacted: str = "[REDACTED]") -> dict:
    """Recursively replaces sensitive values with [REDACTED]."""
    result = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_KEYS:
            result[key] = redacted
        elif isinstance(value, dict):
            result[key] = sanitize_payload(value, redacted)
        elif isinstance(value, list):
            result[key] = [
                sanitize_payload(v, redacted) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            result[key] = value
    return result
```

Usage:
```python
logger.debug("Request body received", extra={"body": sanitize_payload(request_body)})
```

---

## Error Logging — Always Include Context

When logging errors, include enough information to diagnose the problem without re-running the code.

```python
# Minimal but complete error log
try:
    result = await inventory_client.check_stock(sku)
except ExternalServiceError as err:
    logger.error(
        "Inventory check failed",
        extra={
            "sku": sku,
            "order_id": order_id,
            "service": "inventory-api",
            "error_type": type(err).__name__,
        },
        exc_info=True,  # always include traceback on ERROR and CRITICAL
    )
    raise
```

`exc_info=True` captures the full traceback as a structured field — critical for production debugging.

---

## Log Aggregation and Alerting

Recommended setup for La-Z-Boy:

| Concern | Tool / Pattern |
|---|---|
| Aggregation | CloudWatch Logs / Datadog / Splunk |
| Structured queries | Filter by `service`, `level`, `correlation_id` |
| Error rate alerts | Alert when `ERROR` count > threshold per 5-min window |
| Latency alerts | Alert when `duration_ms` p95 > SLA threshold |
| Security audit | Retain `INFO`+ logs for 90 days minimum |
| Debug retention | Retain `DEBUG` logs for 7 days max (high volume) |

### Useful log queries (pseudocode for any aggregator)

```
# All errors for a specific user request
level = ERROR AND correlation_id = "req-a1b2c3d4"

# Slow requests in the last hour
duration_ms > 500 AND timestamp > now() - 1h

# All logs for an order across services
order_id = "ORD-9921"

# Error rate by service
GROUP BY service WHERE level = ERROR
```
