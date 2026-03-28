"""
La-Z-Boy FastAPI request logging middleware.

Injects a correlation ID into every request, stores it in a ContextVar
(so it appears in all log lines for that request), propagates it in the
response header, and logs each request with method, path, status, and duration.

Usage:
    from lazboy_myservice.logging_middleware import RequestLoggingMiddleware
    app.add_middleware(RequestLoggingMiddleware)
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from lazboy_myservice.logging_config import set_correlation_id

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    For every HTTP request:
    1. Extract or generate a correlation ID
    2. Store it in the ContextVar (all log calls in this request inherit it)
    3. Log the completed request with method, path, status, and duration
    4. Return the correlation ID in the response header
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Step 1: resolve correlation ID
        correlation_id = (
            request.headers.get(CORRELATION_ID_HEADER)
            or f"req-{uuid.uuid4().hex[:12]}"
        )

        # Step 2: store in ContextVar — every logger.* call in this request sees it
        set_correlation_id(correlation_id)

        # Step 3: time the request
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        # Step 4: log the completed request
        logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Step 5: propagate correlation ID in response so clients can report it
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
