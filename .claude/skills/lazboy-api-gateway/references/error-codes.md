# Standardized API Error Codes and Responses

Comprehensive error code registry, response formats, and handling patterns.

---

## Error Response Format (RFC 7807)

All error responses follow the [RFC 7807 Problem Details](https://datatracker.ietf.org/doc/html/rfc7807) format.

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "The 'email' field must be a valid email address.",
  "instance": "/api/v1/users",
  "traceId": "abc-123-def-456",
  "errors": [
    {
      "field": "email",
      "code": "INVALID_FORMAT",
      "message": "Must be a valid email address."
    }
  ]
}
```

### TypeScript Type Definition

```typescript
// types/error.ts
interface ProblemDetail {
  type: string;            // URI identifying the error type
  title: string;           // Short, human-readable summary
  status: number;          // HTTP status code
  detail: string;          // Human-readable explanation specific to this occurrence
  instance?: string;       // URI of the request that caused the error
  traceId?: string;        // Distributed tracing correlation ID
  errors?: FieldError[];   // Validation sub-errors (for 400/422)
}

interface FieldError {
  field: string;           // JSON path to the field (e.g., "body.email")
  code: string;            // Machine-readable error code
  message: string;         // Human-readable explanation
}
```

---

## HTTP Status Code Reference

### 4xx Client Errors

| Code | Name | When to Use |
|---|---|---|
| `400` | Bad Request | Malformed request syntax, invalid JSON, missing required fields |
| `401` | Unauthorized | Missing or invalid authentication credentials |
| `403` | Forbidden | Authenticated but insufficient permissions for this action |
| `404` | Not Found | Resource does not exist at the given URI |
| `405` | Method Not Allowed | HTTP method not supported on this endpoint |
| `406` | Not Acceptable | Cannot produce response in requested format (Accept header) |
| `408` | Request Timeout | Client took too long to complete the request |
| `409` | Conflict | Request conflicts with current state (duplicate, version mismatch) |
| `410` | Gone | Resource has been permanently deleted (useful for deprecated endpoints) |
| `413` | Payload Too Large | Request body exceeds the size limit |
| `415` | Unsupported Media Type | Content-Type not supported |
| `422` | Unprocessable Entity | Syntactically valid but semantically invalid (business rule violation) |
| `429` | Too Many Requests | Rate limit exceeded |

### 5xx Server Errors

| Code | Name | When to Use |
|---|---|---|
| `500` | Internal Server Error | Unexpected server-side error (catch-all) |
| `502` | Bad Gateway | Upstream service returned an invalid response |
| `503` | Service Unavailable | Server temporarily overloaded or in maintenance |
| `504` | Gateway Timeout | Upstream service did not respond in time |

---

## Custom Error Code Registry

Application-level error codes that provide more granular context than HTTP status codes alone.

### Authentication & Authorization

| Code | HTTP Status | Description |
|---|---|---|
| `AUTH_TOKEN_EXPIRED` | 401 | Access token has expired |
| `AUTH_TOKEN_INVALID` | 401 | Token is malformed or signature is invalid |
| `AUTH_TOKEN_MISSING` | 401 | No Authorization header provided |
| `AUTH_REFRESH_EXPIRED` | 401 | Refresh token has expired; re-authentication required |
| `AUTH_INSUFFICIENT_SCOPE` | 403 | Token does not have the required scope |
| `AUTH_ACCOUNT_DISABLED` | 403 | User account is suspended or disabled |
| `AUTH_IP_BLOCKED` | 403 | Request originates from a blocked IP address |
| `AUTH_MFA_REQUIRED` | 403 | Multi-factor authentication step is required |

### Validation

| Code | HTTP Status | Description |
|---|---|---|
| `VALIDATION_REQUIRED` | 400 | A required field is missing |
| `VALIDATION_INVALID_FORMAT` | 400 | Field value does not match expected format |
| `VALIDATION_OUT_OF_RANGE` | 400 | Numeric value is outside the allowed range |
| `VALIDATION_STRING_TOO_LONG` | 400 | String exceeds maximum length |
| `VALIDATION_STRING_TOO_SHORT` | 400 | String is below minimum length |
| `VALIDATION_INVALID_ENUM` | 400 | Value is not in the allowed set of values |
| `VALIDATION_INVALID_JSON` | 400 | Request body is not valid JSON |

### Resource

| Code | HTTP Status | Description |
|---|---|---|
| `RESOURCE_NOT_FOUND` | 404 | The requested resource does not exist |
| `RESOURCE_ALREADY_EXISTS` | 409 | A resource with the same unique key already exists |
| `RESOURCE_VERSION_CONFLICT` | 409 | Optimistic locking conflict (stale ETag or version) |
| `RESOURCE_GONE` | 410 | Resource was deleted and is no longer available |
| `RESOURCE_LOCKED` | 423 | Resource is locked and cannot be modified |

### Rate Limiting

| Code | HTTP Status | Description |
|---|---|---|
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests in the time window |
| `RATE_LIMIT_QUOTA_EXCEEDED` | 429 | Monthly/daily API quota is exhausted |

### Business Logic

| Code | HTTP Status | Description |
|---|---|---|
| `BUSINESS_INSUFFICIENT_FUNDS` | 422 | Not enough balance to complete the transaction |
| `BUSINESS_ORDER_NOT_CANCELLABLE` | 422 | Order has shipped and cannot be cancelled |
| `BUSINESS_INVENTORY_UNAVAILABLE` | 422 | Requested item is out of stock |
| `BUSINESS_PAYMENT_DECLINED` | 422 | Payment processor declined the transaction |
| `BUSINESS_ADDRESS_UNVERIFIABLE` | 422 | Shipping address could not be verified |

### Server / Infrastructure

| Code | HTTP Status | Description |
|---|---|---|
| `SERVER_INTERNAL_ERROR` | 500 | Unexpected internal error |
| `SERVER_DATABASE_ERROR` | 500 | Database query failed |
| `SERVER_UPSTREAM_ERROR` | 502 | Upstream dependency returned an error |
| `SERVER_UNAVAILABLE` | 503 | Service is temporarily unavailable |
| `SERVER_UPSTREAM_TIMEOUT` | 504 | Upstream dependency timed out |

---

## Error Factory

```typescript
// lib/errors.ts
export class AppError extends Error {
  constructor(
    public readonly type: string,
    public readonly title: string,
    public readonly status: number,
    public readonly detail: string,
    public readonly code: string,
    public readonly errors?: FieldError[],
  ) {
    super(detail);
    this.name = 'AppError';
  }

  toJSON(): ProblemDetail {
    return {
      type: `https://api.example.com/errors/${this.type}`,
      title: this.title,
      status: this.status,
      detail: this.detail,
      errors: this.errors,
    };
  }
}

// Pre-built error factories
export const Errors = {
  notFound(resource: string, id: string): AppError {
    return new AppError(
      'resource-not-found',
      'Resource Not Found',
      404,
      `${resource} with id '${id}' was not found.`,
      'RESOURCE_NOT_FOUND',
    );
  },

  validationFailed(errors: FieldError[]): AppError {
    return new AppError(
      'validation-error',
      'Validation Error',
      400,
      'One or more fields failed validation.',
      'VALIDATION_FAILED',
      errors,
    );
  },

  unauthorized(detail = 'Authentication is required.'): AppError {
    return new AppError(
      'unauthorized',
      'Unauthorized',
      401,
      detail,
      'AUTH_TOKEN_MISSING',
    );
  },

  forbidden(detail = 'You do not have permission to perform this action.'): AppError {
    return new AppError(
      'forbidden',
      'Forbidden',
      403,
      detail,
      'AUTH_INSUFFICIENT_SCOPE',
    );
  },

  conflict(detail: string): AppError {
    return new AppError(
      'conflict',
      'Conflict',
      409,
      detail,
      'RESOURCE_ALREADY_EXISTS',
    );
  },

  rateLimited(retryAfterSeconds: number): AppError {
    return new AppError(
      'rate-limit-exceeded',
      'Rate Limit Exceeded',
      429,
      `Too many requests. Retry after ${retryAfterSeconds} seconds.`,
      'RATE_LIMIT_EXCEEDED',
    );
  },

  internal(detail = 'An unexpected error occurred.'): AppError {
    return new AppError(
      'internal-error',
      'Internal Server Error',
      500,
      detail,
      'SERVER_INTERNAL_ERROR',
    );
  },

  badGateway(service: string): AppError {
    return new AppError(
      'bad-gateway',
      'Bad Gateway',
      502,
      `Upstream service '${service}' returned an invalid response.`,
      'SERVER_UPSTREAM_ERROR',
    );
  },

  gatewayTimeout(service: string): AppError {
    return new AppError(
      'gateway-timeout',
      'Gateway Timeout',
      504,
      `Upstream service '${service}' did not respond in time.`,
      'SERVER_UPSTREAM_TIMEOUT',
    );
  },
} as const;
```

---

## Error Handling Middleware

```typescript
// middleware/error-handler.ts
import { Request, Response, NextFunction } from 'express';
import { AppError } from '../lib/errors';
import { ZodError } from 'zod';
import { logger } from '../lib/logger';
import { v4 as uuid } from 'uuid';

export function errorHandler(
  err: Error,
  req: Request,
  res: Response,
  _next: NextFunction,
): void {
  const traceId = (req.headers['x-trace-id'] as string) || uuid();

  // Known application error
  if (err instanceof AppError) {
    const body = err.toJSON();
    body.instance = req.originalUrl;
    body.traceId = traceId;

    if (err.status >= 500) {
      logger.error({ err, traceId, path: req.originalUrl }, err.detail);
    } else {
      logger.warn({ traceId, path: req.originalUrl, status: err.status }, err.detail);
    }

    res.status(err.status).json({ error: body });
    return;
  }

  // Zod validation error
  if (err instanceof ZodError) {
    const errors = err.issues.map(issue => ({
      field: issue.path.join('.'),
      code: issue.code,
      message: issue.message,
    }));

    res.status(400).json({
      error: {
        type: 'https://api.example.com/errors/validation-error',
        title: 'Validation Error',
        status: 400,
        detail: 'Request validation failed.',
        instance: req.originalUrl,
        traceId,
        errors,
      },
    });
    return;
  }

  // SyntaxError from JSON parse
  if (err instanceof SyntaxError && 'body' in err) {
    res.status(400).json({
      error: {
        type: 'https://api.example.com/errors/invalid-json',
        title: 'Invalid JSON',
        status: 400,
        detail: 'The request body contains invalid JSON.',
        instance: req.originalUrl,
        traceId,
      },
    });
    return;
  }

  // Unexpected error - never leak internal details
  logger.error({ err, traceId, path: req.originalUrl, stack: err.stack }, 'Unhandled error');

  res.status(500).json({
    error: {
      type: 'https://api.example.com/errors/internal-error',
      title: 'Internal Server Error',
      status: 500,
      detail: 'An unexpected error occurred. Please try again later.',
      instance: req.originalUrl,
      traceId,
    },
  });
}

// Register as the last middleware
// app.use(errorHandler);
```

---

## Common Error Scenarios

### Scenario: Creating a User with Invalid Input

```
POST /api/v1/users
Content-Type: application/json

{ "email": "not-an-email", "name": "" }
```

```json
HTTP/1.1 400 Bad Request
Content-Type: application/problem+json

{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "One or more fields failed validation.",
  "instance": "/api/v1/users",
  "traceId": "a1b2c3d4",
  "errors": [
    { "field": "email", "code": "VALIDATION_INVALID_FORMAT", "message": "Must be a valid email address." },
    { "field": "name", "code": "VALIDATION_STRING_TOO_SHORT", "message": "Must be at least 1 character." }
  ]
}
```

### Scenario: Accessing a Deleted Resource

```
GET /api/v1/products/789
```

```json
HTTP/1.1 404 Not Found
Content-Type: application/problem+json

{
  "type": "https://api.example.com/errors/resource-not-found",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Product with id '789' was not found.",
  "instance": "/api/v1/products/789",
  "traceId": "e5f6a7b8"
}
```

### Scenario: Optimistic Locking Conflict

```
PUT /api/v1/products/123
If-Match: "v5"
Content-Type: application/json

{ "name": "Updated Name", "price": 29.99 }
```

```json
HTTP/1.1 409 Conflict
Content-Type: application/problem+json

{
  "type": "https://api.example.com/errors/version-conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "The resource has been modified since you last fetched it (expected version 5, current version 7). Fetch the latest version and retry.",
  "instance": "/api/v1/products/123",
  "traceId": "c9d0e1f2"
}
```

### Scenario: Rate Limit Exceeded

```
GET /api/v1/search?q=test
```

```json
HTTP/1.1 429 Too Many Requests
Content-Type: application/problem+json
RateLimit-Limit: 100
RateLimit-Remaining: 0
RateLimit-Reset: 1700000060
Retry-After: 45

{
  "type": "https://api.example.com/errors/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "You have exceeded the rate limit of 100 requests per 60s. Retry after 45 seconds.",
  "instance": "/api/v1/search",
  "traceId": "g3h4i5j6"
}
```

### Scenario: Upstream Service Failure

```
POST /api/v1/orders
```

```json
HTTP/1.1 502 Bad Gateway
Content-Type: application/problem+json

{
  "type": "https://api.example.com/errors/bad-gateway",
  "title": "Bad Gateway",
  "status": 502,
  "detail": "Upstream service 'payment-service' returned an invalid response.",
  "instance": "/api/v1/orders",
  "traceId": "k7l8m9n0"
}
```

---

## Client-Side Error Handling Pattern

```typescript
// client/api-client.ts
async function apiRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const problem: ProblemDetail = error?.error || {
      type: 'https://api.example.com/errors/unknown',
      title: 'Request Failed',
      status: response.status,
      detail: response.statusText,
    };

    switch (problem.status) {
      case 401:
        // Redirect to login or refresh token
        await refreshTokenAndRetry();
        break;
      case 429:
        // Respect Retry-After header
        const retryAfter = parseInt(response.headers.get('Retry-After') || '60', 10);
        await delay(retryAfter * 1000);
        return apiRequest<T>(url, options);
      default:
        throw new ApiError(problem);
    }
  }

  const body = await response.json();
  return body.data as T;
}
```
