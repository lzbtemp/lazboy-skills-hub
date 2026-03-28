# API Design Patterns

Comprehensive reference for API gateway patterns, conventions, and implementation examples in TypeScript/Express.

---

## RESTful Conventions

### Resource Naming

| Pattern | Example | Notes |
|---|---|---|
| Collection | `GET /users` | Plural nouns |
| Document | `GET /users/123` | Specific resource |
| Sub-collection | `GET /users/123/orders` | Nested resource |
| Controller | `POST /users/123/activate` | Action (verb, exception to noun rule) |

### HTTP Method Mapping

| Method | Action | Idempotent | Safe | Success Code |
|---|---|---|---|---|
| `GET` | Read | Yes | Yes | `200 OK` |
| `POST` | Create | No | No | `201 Created` |
| `PUT` | Full replace | Yes | No | `200 OK` |
| `PATCH` | Partial update | No* | No | `200 OK` |
| `DELETE` | Remove | Yes | No | `204 No Content` |

### Standard Response Envelope

```typescript
// types/api-response.ts
interface ApiResponse<T> {
  data: T;
  meta?: {
    requestId: string;
    timestamp: string;
    pagination?: PaginationMeta;
  };
}

interface ApiErrorResponse {
  error: {
    type: string;         // URI reference (RFC 7807)
    title: string;        // Short summary
    status: number;       // HTTP status code
    detail: string;       // Human-readable explanation
    instance?: string;    // URI of the specific occurrence
    errors?: FieldError[];// Validation errors
  };
}

interface FieldError {
  field: string;
  message: string;
  code: string;
}
```

---

## Versioning Strategies

### URI Versioning (Recommended for Public APIs)

```typescript
// routes/index.ts
import { Router } from 'express';
import v1Routes from './v1';
import v2Routes from './v2';

const router = Router();
router.use('/api/v1', v1Routes);
router.use('/api/v2', v2Routes);

export default router;
```

### Header Versioning (Recommended for Internal APIs)

```typescript
// middleware/api-version.ts
import { Request, Response, NextFunction } from 'express';

export function apiVersion(req: Request, _res: Response, next: NextFunction): void {
  const version = req.headers['api-version'] || req.headers['accept']?.match(/version=(\d+)/)?.[1] || '1';
  req.apiVersion = parseInt(version as string, 10);
  next();
}

// Usage in route handler
app.get('/api/users', apiVersion, (req, res) => {
  if (req.apiVersion >= 2) {
    return res.json(formatV2(users));
  }
  return res.json(formatV1(users));
});
```

### Sunset Header for Deprecation

```typescript
// middleware/sunset.ts
export function sunsetHeader(date: string) {
  return (_req: Request, res: Response, next: NextFunction) => {
    res.set('Sunset', new Date(date).toUTCString());
    res.set('Deprecation', 'true');
    res.set('Link', '</api/v2/users>; rel="successor-version"');
    next();
  };
}

// Apply to deprecated routes
router.use('/api/v1', sunsetHeader('2025-06-01'), v1Routes);
```

---

## Pagination

### Cursor-Based Pagination (Recommended)

Best for real-time data, infinite scrolling, large datasets.

```typescript
// middleware/pagination.ts
interface CursorPaginationParams {
  cursor?: string;
  limit: number;
}

interface CursorPaginationMeta {
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  startCursor: string | null;
  endCursor: string | null;
}

// services/user.service.ts
async function listUsers(params: CursorPaginationParams): Promise<{
  data: User[];
  pagination: CursorPaginationMeta;
}> {
  const { cursor, limit } = params;

  const where = cursor
    ? { id: { gt: decodeCursor(cursor) } }
    : {};

  // Fetch one extra to determine if there's a next page
  const items = await prisma.user.findMany({
    where,
    take: limit + 1,
    orderBy: { id: 'asc' },
  });

  const hasNextPage = items.length > limit;
  const data = hasNextPage ? items.slice(0, limit) : items;

  return {
    data,
    pagination: {
      hasNextPage,
      hasPreviousPage: !!cursor,
      startCursor: data.length > 0 ? encodeCursor(data[0].id) : null,
      endCursor: data.length > 0 ? encodeCursor(data[data.length - 1].id) : null,
    },
  };
}

function encodeCursor(id: string | number): string {
  return Buffer.from(String(id)).toString('base64url');
}

function decodeCursor(cursor: string): string {
  return Buffer.from(cursor, 'base64url').toString('utf8');
}

// Controller response
// GET /api/users?cursor=MTIz&limit=20
// Response:
// {
//   "data": [...],
//   "meta": {
//     "pagination": {
//       "hasNextPage": true,
//       "endCursor": "MTQ0",
//     }
//   }
// }
```

### Offset-Based Pagination

Simpler, allows jumping to arbitrary pages. Degrades on large datasets.

```typescript
// middleware/pagination.ts
interface OffsetPaginationParams {
  page: number;   // 1-indexed
  limit: number;
}

interface OffsetPaginationMeta {
  page: number;
  limit: number;
  totalItems: number;
  totalPages: number;
}

function parsePagination(query: Record<string, unknown>): OffsetPaginationParams {
  const page = Math.max(1, Number(query.page) || 1);
  const limit = Math.min(100, Math.max(1, Number(query.limit) || 20));
  return { page, limit };
}

async function listUsers(params: OffsetPaginationParams) {
  const { page, limit } = params;
  const offset = (page - 1) * limit;

  const [data, totalItems] = await Promise.all([
    prisma.user.findMany({ skip: offset, take: limit, orderBy: { createdAt: 'desc' } }),
    prisma.user.count(),
  ]);

  return {
    data,
    pagination: {
      page,
      limit,
      totalItems,
      totalPages: Math.ceil(totalItems / limit),
    },
  };
}
```

---

## Filtering & Sorting

```typescript
// middleware/query-parser.ts
interface QueryParams {
  filter: Record<string, string | string[]>;
  sort: { field: string; order: 'asc' | 'desc' }[];
  fields: string[];  // Sparse fieldsets
}

function parseQuery(query: Record<string, unknown>): QueryParams {
  // GET /api/users?filter[status]=active&filter[role]=admin,editor&sort=-createdAt,name&fields=id,name,email

  const filter: Record<string, string | string[]> = {};
  for (const [key, value] of Object.entries(query)) {
    const match = key.match(/^filter\[(\w+)]$/);
    if (match && typeof value === 'string') {
      const vals = value.split(',');
      filter[match[1]] = vals.length === 1 ? vals[0] : vals;
    }
  }

  const sort: QueryParams['sort'] = [];
  if (typeof query.sort === 'string') {
    for (const field of query.sort.split(',')) {
      if (field.startsWith('-')) {
        sort.push({ field: field.slice(1), order: 'desc' });
      } else {
        sort.push({ field, order: 'asc' });
      }
    }
  }

  const fields = typeof query.fields === 'string'
    ? query.fields.split(',').map(f => f.trim())
    : [];

  return { filter, sort, fields };
}

// Allowlist-based Prisma where builder
const ALLOWED_FILTERS: Record<string, (value: string | string[]) => object> = {
  status: (v) => ({ status: Array.isArray(v) ? { in: v } : v }),
  role: (v) => ({ role: Array.isArray(v) ? { in: v } : v }),
  search: (v) => ({
    OR: [
      { name: { contains: String(v), mode: 'insensitive' } },
      { email: { contains: String(v), mode: 'insensitive' } },
    ],
  }),
  createdAfter: (v) => ({ createdAt: { gte: new Date(String(v)) } }),
};
```

---

## Rate Limiting

### Token Bucket Implementation

```typescript
// middleware/rate-limiter.ts
import { Request, Response, NextFunction } from 'express';
import Redis from 'ioredis';

const redis = new Redis(process.env.REDIS_URL);

interface RateLimitConfig {
  windowMs: number;      // Time window in milliseconds
  maxRequests: number;   // Max requests per window
  keyPrefix?: string;
}

export function rateLimit(config: RateLimitConfig) {
  const { windowMs, maxRequests, keyPrefix = 'rl' } = config;

  return async (req: Request, res: Response, next: NextFunction) => {
    const identifier = req.user?.id || req.ip;
    const key = `${keyPrefix}:${identifier}`;
    const windowSeconds = Math.ceil(windowMs / 1000);

    const results = await redis
      .multi()
      .incr(key)
      .expire(key, windowSeconds)
      .exec();

    const currentCount = results?.[0]?.[1] as number;

    // Set standard rate limit headers (RFC 6585 / draft-ietf-httpapi-ratelimit-headers)
    res.set('RateLimit-Limit', String(maxRequests));
    res.set('RateLimit-Remaining', String(Math.max(0, maxRequests - currentCount)));
    res.set('RateLimit-Reset', String(Math.ceil(Date.now() / 1000) + windowSeconds));

    if (currentCount > maxRequests) {
      res.set('Retry-After', String(windowSeconds));
      return res.status(429).json({
        error: {
          type: 'https://api.example.com/errors/rate-limit-exceeded',
          title: 'Rate Limit Exceeded',
          status: 429,
          detail: `You have exceeded the rate limit of ${maxRequests} requests per ${windowSeconds}s.`,
        },
      });
    }

    next();
  };
}

// Usage
app.use('/api', rateLimit({ windowMs: 60_000, maxRequests: 100 }));
app.use('/api/auth/login', rateLimit({ windowMs: 900_000, maxRequests: 5, keyPrefix: 'rl:login' }));
```

### Tiered Rate Limits

```typescript
const RATE_LIMIT_TIERS: Record<string, RateLimitConfig> = {
  free:       { windowMs: 3600_000, maxRequests: 100 },
  basic:      { windowMs: 3600_000, maxRequests: 1_000 },
  pro:        { windowMs: 3600_000, maxRequests: 10_000 },
  enterprise: { windowMs: 3600_000, maxRequests: 100_000 },
};

export function tieredRateLimit(req: Request, res: Response, next: NextFunction) {
  const tier = req.user?.plan || 'free';
  const config = RATE_LIMIT_TIERS[tier] || RATE_LIMIT_TIERS.free;
  return rateLimit(config)(req, res, next);
}
```

---

## Circuit Breaker

Prevent cascading failures when downstream services are unhealthy.

```typescript
// lib/circuit-breaker.ts
enum CircuitState {
  CLOSED = 'CLOSED',       // Normal operation
  OPEN = 'OPEN',           // Failing, reject requests
  HALF_OPEN = 'HALF_OPEN', // Testing if service recovered
}

interface CircuitBreakerOptions {
  failureThreshold: number;    // Failures before opening
  resetTimeoutMs: number;      // Time before trying half-open
  monitorWindowMs: number;     // Window to count failures
}

class CircuitBreaker {
  private state = CircuitState.CLOSED;
  private failureCount = 0;
  private lastFailureTime = 0;
  private successCount = 0;

  constructor(
    private readonly name: string,
    private readonly options: CircuitBreakerOptions = {
      failureThreshold: 5,
      resetTimeoutMs: 30_000,
      monitorWindowMs: 60_000,
    },
  ) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() - this.lastFailureTime >= this.options.resetTimeoutMs) {
        this.state = CircuitState.HALF_OPEN;
        this.successCount = 0;
      } else {
        throw new CircuitBreakerError(
          `Circuit breaker '${this.name}' is OPEN. Request rejected.`,
        );
      }
    }

    try {
      const result = await fn();

      if (this.state === CircuitState.HALF_OPEN) {
        this.successCount++;
        if (this.successCount >= 3) {
          this.reset();
        }
      }

      return result;
    } catch (error) {
      this.recordFailure();
      throw error;
    }
  }

  private recordFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.failureCount >= this.options.failureThreshold) {
      this.state = CircuitState.OPEN;
      console.error(`Circuit breaker '${this.name}' OPENED after ${this.failureCount} failures`);
    }
  }

  private reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    console.info(`Circuit breaker '${this.name}' CLOSED (recovered)`);
  }
}

class CircuitBreakerError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CircuitBreakerError';
  }
}

// Usage
const paymentBreaker = new CircuitBreaker('payment-service', {
  failureThreshold: 3,
  resetTimeoutMs: 30_000,
  monitorWindowMs: 60_000,
});

async function processPayment(orderId: string) {
  return paymentBreaker.execute(() =>
    fetch(`${PAYMENT_SERVICE_URL}/charge`, {
      method: 'POST',
      body: JSON.stringify({ orderId }),
    }).then(r => {
      if (!r.ok) throw new Error(`Payment service returned ${r.status}`);
      return r.json();
    }),
  );
}
```

---

## API Composition (Aggregation Gateway)

Combine multiple microservice calls into a single API response.

```typescript
// services/order-aggregator.ts
interface OrderDetail {
  order: Order;
  customer: Customer;
  items: OrderItem[];
  shipping: ShippingInfo;
}

async function getOrderDetail(orderId: string): Promise<OrderDetail> {
  const order = await orderService.getById(orderId);

  // Parallel fan-out to downstream services
  const [customer, items, shipping] = await Promise.allSettled([
    customerService.getById(order.customerId),
    catalogService.getOrderItems(orderId),
    shippingService.getTracking(orderId),
  ]);

  return {
    order,
    customer: customer.status === 'fulfilled' ? customer.value : null,
    items: items.status === 'fulfilled' ? items.value : [],
    shipping: shipping.status === 'fulfilled' ? shipping.value : null,
  };
}
```

---

## Backend for Frontend (BFF) Pattern

Tailor API responses to specific client needs.

```typescript
// bff/mobile/routes/home.ts
// Mobile BFF: optimized payload, fewer round-trips

router.get('/home', async (req, res) => {
  const userId = req.user.id;

  const [profile, recentOrders, recommendations] = await Promise.all([
    userService.getProfile(userId),
    orderService.getRecent(userId, { limit: 3, fields: ['id', 'status', 'total', 'date'] }),
    recommendationService.getForUser(userId, { limit: 5 }),
  ]);

  // Mobile-optimized: smaller images, fewer fields
  res.json({
    data: {
      greeting: `Welcome back, ${profile.firstName}`,
      avatar: profile.avatarUrl ? `${profile.avatarUrl}?w=100&h=100` : null,
      recentOrders: recentOrders.map(o => ({
        id: o.id,
        status: o.status,
        total: o.total,
        date: o.date,
      })),
      recommendations: recommendations.map(r => ({
        id: r.id,
        name: r.name,
        price: r.price,
        image: `${r.imageUrl}?w=200&h=200`,
      })),
    },
  });
});

// bff/web/routes/home.ts
// Web BFF: richer payload, more detail

router.get('/home', async (req, res) => {
  const userId = req.user.id;

  const [profile, orders, recommendations, notifications, stats] = await Promise.all([
    userService.getFullProfile(userId),
    orderService.getRecent(userId, { limit: 10 }),
    recommendationService.getForUser(userId, { limit: 12 }),
    notificationService.getUnread(userId),
    analyticsService.getUserStats(userId),
  ]);

  res.json({
    data: { profile, orders, recommendations, notifications, stats },
  });
});
```

---

## Request Validation Middleware

```typescript
// middleware/validate.ts
import { z, ZodSchema } from 'zod';
import { Request, Response, NextFunction } from 'express';

interface ValidationSchemas {
  body?: ZodSchema;
  query?: ZodSchema;
  params?: ZodSchema;
}

export function validate(schemas: ValidationSchemas) {
  return (req: Request, res: Response, next: NextFunction) => {
    const errors: FieldError[] = [];

    for (const [source, schema] of Object.entries(schemas)) {
      if (!schema) continue;
      const result = schema.safeParse(req[source as keyof Request]);
      if (!result.success) {
        for (const issue of result.error.issues) {
          errors.push({
            field: `${source}.${issue.path.join('.')}`,
            message: issue.message,
            code: issue.code,
          });
        }
      }
    }

    if (errors.length > 0) {
      return res.status(400).json({
        error: {
          type: 'https://api.example.com/errors/validation-error',
          title: 'Validation Error',
          status: 400,
          detail: 'One or more fields failed validation.',
          errors,
        },
      });
    }

    next();
  };
}

// Usage
const createUserSchema = {
  body: z.object({
    email: z.string().email(),
    name: z.string().min(1).max(100),
    role: z.enum(['user', 'admin']).default('user'),
  }),
};

router.post('/users', validate(createUserSchema), userController.create);
```

---

## Health Check Endpoint

```typescript
// routes/health.ts
interface HealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  checks: Record<string, { status: string; latencyMs: number; message?: string }>;
}

router.get('/health', async (_req, res) => {
  const checks: HealthCheck['checks'] = {};

  // Database check
  const dbStart = Date.now();
  try {
    await prisma.$queryRaw`SELECT 1`;
    checks.database = { status: 'pass', latencyMs: Date.now() - dbStart };
  } catch (e) {
    checks.database = { status: 'fail', latencyMs: Date.now() - dbStart, message: String(e) };
  }

  // Redis check
  const redisStart = Date.now();
  try {
    await redis.ping();
    checks.redis = { status: 'pass', latencyMs: Date.now() - redisStart };
  } catch (e) {
    checks.redis = { status: 'fail', latencyMs: Date.now() - redisStart, message: String(e) };
  }

  const allPass = Object.values(checks).every(c => c.status === 'pass');
  const anyFail = Object.values(checks).some(c => c.status === 'fail');

  const health: HealthCheck = {
    status: allPass ? 'healthy' : anyFail ? 'unhealthy' : 'degraded',
    version: process.env.APP_VERSION || '0.0.0',
    uptime: process.uptime(),
    checks,
  };

  const statusCode = health.status === 'healthy' ? 200 : 503;
  res.status(statusCode).json(health);
});
```
