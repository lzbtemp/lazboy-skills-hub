---
name: lazboy-backend-patterns
description: "Architectural patterns and best practices for scalable backend applications using Node.js, Express, and Next.js. Use this skill when designing APIs, implementing layered architecture, optimizing database queries, adding caching, setting up background jobs, structuring error handling, or building middleware."
version: "1.0.0"
category: Backend
tags: [nodejs, express, api, architecture, caching, database]
---

# Backend Patterns

Patterns for building scalable, maintainable backend applications.

## 1. Layered Architecture

Separate concerns into Controller → Service → Repository layers:

```
Controller  →  Handles HTTP request/response
Service     →  Business logic, orchestration
Repository  →  Data access, queries
```

### Repository Pattern

```typescript
class UserRepository {
  async findById(id: string): Promise<User | null> {
    const { data } = await db
      .from('users')
      .select('id, name, email, role')
      .eq('id', id)
      .single();
    return data;
  }

  async findByEmail(email: string): Promise<User | null> {
    const { data } = await db
      .from('users')
      .select('id, name, email')
      .eq('email', email)
      .single();
    return data;
  }
}
```

### Service Layer

```typescript
class UserService {
  constructor(private repo: UserRepository) {}

  async getUser(id: string): Promise<User> {
    const user = await this.repo.findById(id);
    if (!user) throw new NotFoundError(`User ${id} not found`);
    return user;
  }

  async createUser(input: CreateUserInput): Promise<User> {
    const existing = await this.repo.findByEmail(input.email);
    if (existing) throw new ConflictError('Email already registered');
    return this.repo.create(input);
  }
}
```

## 2. Database Optimization

### Select Only Needed Columns

```typescript
// ❌ Fetches everything
const { data } = await db.from('users').select('*');

// ✅ Select only what's needed
const { data } = await db.from('users').select('id, name, email');
```

### Prevent N+1 Queries

```typescript
// ❌ N+1 — one query per user
for (const user of users) {
  const orders = await db.from('orders').select('*').eq('user_id', user.id);
}

// ✅ Batch fetch
const userIds = users.map(u => u.id);
const { data: orders } = await db
  .from('orders')
  .select('*')
  .in('user_id', userIds);
```

### Transactions

```typescript
async function transferFunds(fromId: string, toId: string, amount: number) {
  await db.rpc('transfer_funds', {
    from_account: fromId,
    to_account: toId,
    transfer_amount: amount,
  });
}
```

## 3. Caching

### Cache-Aside Pattern

```typescript
class CacheLayer {
  constructor(private redis: RedisClient, private defaultTTL = 300) {}

  async get<T>(key: string, fetcher: () => Promise<T>, ttl?: number): Promise<T> {
    const cached = await this.redis.get(key);
    if (cached) return JSON.parse(cached);

    const data = await fetcher();
    await this.redis.set(key, JSON.stringify(data), 'EX', ttl ?? this.defaultTTL);
    return data;
  }

  async invalidate(key: string): Promise<void> {
    await this.redis.del(key);
  }
}

// Usage
const user = await cache.get(`user:${id}`, () => userRepo.findById(id), 600);
```

## 4. Error Handling

### Centralized Error Handler

```typescript
class ApiError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class NotFoundError extends ApiError {
  constructor(message: string) { super(404, message); }
}

class ConflictError extends ApiError {
  constructor(message: string) { super(409, message); }
}

class ValidationError extends ApiError {
  constructor(errors: unknown) { super(400, 'Validation failed', errors); }
}

// Express error middleware
function errorHandler(err: Error, req: Request, res: Response, next: NextFunction) {
  if (err instanceof ApiError) {
    return res.status(err.statusCode).json({
      success: false,
      error: err.message,
      details: err.details,
    });
  }

  logger.error('Unhandled error', { error: err, path: req.path });
  res.status(500).json({ success: false, error: 'Internal server error' });
}
```

## 5. Resilience — Retry with Backoff

```typescript
async function withRetry<T>(
  fn: () => Promise<T>,
  maxAttempts = 3,
  baseDelay = 1000,
): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxAttempts) throw error;
      const delay = baseDelay * Math.pow(2, attempt - 1); // 1s, 2s, 4s
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  throw new Error('Unreachable');
}
```

## 6. Authentication & Authorization

### JWT Verification Middleware

```typescript
function authenticate(req: Request, res: Response, next: NextFunction) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) return res.status(401).json({ error: 'Token required' });

  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET!);
    next();
  } catch {
    res.status(401).json({ error: 'Invalid token' });
  }
}
```

### Role-Based Access Control

```typescript
const ROLE_PERMISSIONS: Record<string, string[]> = {
  admin: ['read', 'write', 'delete', 'manage'],
  editor: ['read', 'write'],
  viewer: ['read'],
};

function requirePermission(permission: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    const userPerms = ROLE_PERMISSIONS[req.user.role] ?? [];
    if (!userPerms.includes(permission)) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }
    next();
  };
}

// Usage
app.delete('/api/users/:id', authenticate, requirePermission('delete'), deleteUser);
```

## 7. Rate Limiting

```typescript
class RateLimiter {
  private requests = new Map<string, { count: number; resetAt: number }>();

  check(identifier: string, maxRequests: number, windowMs: number): boolean {
    const now = Date.now();
    const record = this.requests.get(identifier);

    if (!record || now > record.resetAt) {
      this.requests.set(identifier, { count: 1, resetAt: now + windowMs });
      return true;
    }

    if (record.count >= maxRequests) return false;
    record.count++;
    return true;
  }
}
```

## 8. Background Processing

```typescript
class JobQueue {
  private queue: Array<{ id: string; handler: () => Promise<void> }> = [];
  private processing = false;

  enqueue(id: string, handler: () => Promise<void>) {
    this.queue.push({ id, handler });
    if (!this.processing) this.process();
  }

  private async process() {
    this.processing = true;
    while (this.queue.length > 0) {
      const job = this.queue.shift()!;
      try {
        await job.handler();
        logger.info('Job completed', { jobId: job.id });
      } catch (error) {
        logger.error('Job failed', { jobId: job.id, error });
      }
    }
    this.processing = false;
  }
}
```

## 9. Structured Logging

```typescript
interface LogEntry {
  level: 'info' | 'warn' | 'error';
  message: string;
  timestamp: string;
  requestId?: string;
  [key: string]: unknown;
}

function createLogger(context: Record<string, unknown> = {}) {
  return {
    info: (msg: string, data?: Record<string, unknown>) =>
      console.log(JSON.stringify({ level: 'info', message: msg, timestamp: new Date().toISOString(), ...context, ...data })),
    warn: (msg: string, data?: Record<string, unknown>) =>
      console.warn(JSON.stringify({ level: 'warn', message: msg, timestamp: new Date().toISOString(), ...context, ...data })),
    error: (msg: string, data?: Record<string, unknown>) =>
      console.error(JSON.stringify({ level: 'error', message: msg, timestamp: new Date().toISOString(), ...context, ...data })),
  };
}

// Usage — include request ID for tracing
app.use((req, res, next) => {
  req.logger = createLogger({ requestId: req.headers['x-request-id'] });
  next();
});
```

## 10. What NOT to Do

- **No business logic in controllers** — controllers handle HTTP only
- **No raw SQL string concatenation** — always use parameterized queries
- **No `SELECT *`** — select only needed columns
- **No uncaught promise rejections** — always handle async errors
- **No secrets in code** — use environment variables
- **No blocking operations in request handlers** — offload to background jobs
