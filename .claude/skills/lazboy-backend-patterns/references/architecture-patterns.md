# Architecture Patterns for Node.js/Express Backend Applications

Comprehensive guide to layered architecture, dependency injection, middleware patterns,
and error handling strategies for building scalable, maintainable backend services.

---

## 1. Layered Architecture

### Overview

Layered architecture separates application concerns into distinct tiers. Each layer has
a single responsibility and communicates only with the layer directly below it.

```
HTTP Request
    │
    ▼
┌─────────────┐
│  Controller  │   Handles HTTP request/response, input validation
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Service    │   Business logic, orchestration, authorization
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Repository   │   Data access, queries, database abstraction
└─────────────┘
```

### Layer Responsibilities

| Layer        | Responsibilities                                      | Does NOT Do                      |
|------------- |-------------------------------------------------------|----------------------------------|
| Controller   | Parse request, validate input, format response         | Business logic, DB queries       |
| Service      | Business rules, orchestration, transaction management  | HTTP concerns, raw SQL           |
| Repository   | Data access, query building, ORM interactions          | Business rules, HTTP handling    |

### Controller Layer

Controllers are thin. They parse the HTTP request, delegate to a service, and format
the HTTP response. No business logic belongs here.

```typescript
// controllers/userController.ts
import { Request, Response, NextFunction } from 'express';
import { UserService } from '../services/userService';
import { createUserSchema, updateUserSchema } from '../validators/userSchemas';

export class UserController {
  constructor(private userService: UserService) {}

  getById = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const user = await this.userService.getUser(req.params.id);
      res.json({ success: true, data: user });
    } catch (error) {
      next(error);
    }
  };

  create = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const input = createUserSchema.parse(req.body);
      const user = await this.userService.createUser(input);
      res.status(201).json({ success: true, data: user });
    } catch (error) {
      next(error);
    }
  };

  update = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const input = updateUserSchema.parse(req.body);
      const user = await this.userService.updateUser(req.params.id, input);
      res.json({ success: true, data: user });
    } catch (error) {
      next(error);
    }
  };

  delete = async (req: Request, res: Response, next: NextFunction) => {
    try {
      await this.userService.deleteUser(req.params.id);
      res.status(204).send();
    } catch (error) {
      next(error);
    }
  };
}
```

### Service Layer

Services contain business logic and orchestrate calls across multiple repositories.
They enforce business rules and manage transactions.

```typescript
// services/userService.ts
import { UserRepository } from '../repositories/userRepository';
import { AuditLogRepository } from '../repositories/auditLogRepository';
import { NotFoundError, ConflictError, ForbiddenError } from '../errors';
import { CreateUserInput, UpdateUserInput, User } from '../types';

export class UserService {
  constructor(
    private userRepo: UserRepository,
    private auditRepo: AuditLogRepository,
  ) {}

  async getUser(id: string): Promise<User> {
    const user = await this.userRepo.findById(id);
    if (!user) throw new NotFoundError(`User ${id} not found`);
    return user;
  }

  async createUser(input: CreateUserInput): Promise<User> {
    // Business rule: no duplicate emails
    const existing = await this.userRepo.findByEmail(input.email);
    if (existing) throw new ConflictError('Email already registered');

    // Business rule: normalize email
    const normalized = { ...input, email: input.email.toLowerCase().trim() };

    const user = await this.userRepo.create(normalized);
    await this.auditRepo.log('user.created', { userId: user.id });
    return user;
  }

  async updateUser(id: string, input: UpdateUserInput): Promise<User> {
    const user = await this.getUser(id);

    // Business rule: cannot change role to admin without approval
    if (input.role === 'admin' && user.role !== 'admin') {
      throw new ForbiddenError('Admin role requires approval workflow');
    }

    const updated = await this.userRepo.update(id, input);
    await this.auditRepo.log('user.updated', { userId: id, changes: input });
    return updated;
  }

  async deleteUser(id: string): Promise<void> {
    await this.getUser(id); // Ensure exists
    await this.userRepo.softDelete(id);
    await this.auditRepo.log('user.deleted', { userId: id });
  }
}
```

### Repository Layer

Repositories abstract data access. The rest of the application never knows whether
data comes from PostgreSQL, MongoDB, or an external API.

```typescript
// repositories/userRepository.ts
import { db } from '../lib/database';
import { User, CreateUserInput, UpdateUserInput } from '../types';

export class UserRepository {
  private table = 'users';

  async findById(id: string): Promise<User | null> {
    const { data } = await db
      .from(this.table)
      .select('id, name, email, role, created_at')
      .eq('id', id)
      .eq('deleted_at', null)
      .single();
    return data;
  }

  async findByEmail(email: string): Promise<User | null> {
    const { data } = await db
      .from(this.table)
      .select('id, name, email, role')
      .eq('email', email.toLowerCase())
      .eq('deleted_at', null)
      .single();
    return data;
  }

  async findAll(options: { page: number; limit: number }): Promise<User[]> {
    const offset = (options.page - 1) * options.limit;
    const { data } = await db
      .from(this.table)
      .select('id, name, email, role, created_at')
      .eq('deleted_at', null)
      .range(offset, offset + options.limit - 1)
      .order('created_at', { ascending: false });
    return data ?? [];
  }

  async create(input: CreateUserInput): Promise<User> {
    const { data } = await db
      .from(this.table)
      .insert(input)
      .select('id, name, email, role, created_at')
      .single();
    return data!;
  }

  async update(id: string, input: UpdateUserInput): Promise<User> {
    const { data } = await db
      .from(this.table)
      .update({ ...input, updated_at: new Date().toISOString() })
      .eq('id', id)
      .select('id, name, email, role, created_at, updated_at')
      .single();
    return data!;
  }

  async softDelete(id: string): Promise<void> {
    await db
      .from(this.table)
      .update({ deleted_at: new Date().toISOString() })
      .eq('id', id);
  }
}
```

---

## 2. Dependency Injection

Dependency injection decouples components and makes code testable by passing
dependencies as constructor parameters instead of importing them directly.

### Manual DI with a Composition Root

```typescript
// container.ts — the composition root
import { UserRepository } from './repositories/userRepository';
import { AuditLogRepository } from './repositories/auditLogRepository';
import { UserService } from './services/userService';
import { UserController } from './controllers/userController';
import { CacheLayer } from './lib/cache';
import { createRedisClient } from './lib/redis';

// Infrastructure
const redis = createRedisClient();
const cache = new CacheLayer(redis);

// Repositories
const userRepo = new UserRepository();
const auditRepo = new AuditLogRepository();

// Services
const userService = new UserService(userRepo, auditRepo);

// Controllers
export const userController = new UserController(userService);
```

### Route Registration

```typescript
// routes/userRoutes.ts
import { Router } from 'express';
import { userController } from '../container';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';

const router = Router();

router.get('/:id', authenticate, userController.getById);
router.post('/', authenticate, requirePermission('write'), userController.create);
router.patch('/:id', authenticate, requirePermission('write'), userController.update);
router.delete('/:id', authenticate, requirePermission('delete'), userController.delete);

export default router;
```

### Benefits of DI for Testing

```typescript
// __tests__/userService.test.ts
describe('UserService', () => {
  let service: UserService;
  let mockUserRepo: jest.Mocked<UserRepository>;
  let mockAuditRepo: jest.Mocked<AuditLogRepository>;

  beforeEach(() => {
    mockUserRepo = {
      findById: jest.fn(),
      findByEmail: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
      softDelete: jest.fn(),
    } as any;
    mockAuditRepo = { log: jest.fn() } as any;
    service = new UserService(mockUserRepo, mockAuditRepo);
  });

  it('should throw NotFoundError when user does not exist', async () => {
    mockUserRepo.findById.mockResolvedValue(null);
    await expect(service.getUser('nonexistent')).rejects.toThrow(NotFoundError);
  });

  it('should throw ConflictError on duplicate email', async () => {
    mockUserRepo.findByEmail.mockResolvedValue({ id: '1', email: 'a@b.com' } as User);
    await expect(
      service.createUser({ name: 'Test', email: 'a@b.com', role: 'user' }),
    ).rejects.toThrow(ConflictError);
  });
});
```

---

## 3. Middleware Patterns

### Middleware Execution Order

```
Request  →  Logger  →  Auth  →  RBAC  →  Validate  →  Controller  →  Response
                                                            │
                                                     Error Handler ← (on throw)
```

### Request Logging Middleware

```typescript
function requestLogger(req: Request, res: Response, next: NextFunction) {
  const start = Date.now();
  const requestId = req.headers['x-request-id'] || crypto.randomUUID();
  req.headers['x-request-id'] = requestId;

  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(JSON.stringify({
      requestId,
      method: req.method,
      path: req.path,
      status: res.statusCode,
      durationMs: duration,
      timestamp: new Date().toISOString(),
    }));
  });

  next();
}
```

### Input Validation Middleware (Zod)

```typescript
import { ZodSchema } from 'zod';

function validate(schema: ZodSchema) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return next(new ValidationError(result.error.flatten()));
    }
    req.body = result.data;
    next();
  };
}

// Usage
router.post('/users', validate(createUserSchema), userController.create);
```

### Async Handler Wrapper

Eliminates repetitive try/catch in every controller method:

```typescript
function asyncHandler(fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) {
  return (req: Request, res: Response, next: NextFunction) => {
    fn(req, res, next).catch(next);
  };
}

// Usage — no try/catch needed in the controller
router.get('/users/:id', asyncHandler(async (req, res) => {
  const user = await userService.getUser(req.params.id);
  res.json({ success: true, data: user });
}));
```

---

## 4. Error Handling Strategies

### Custom Error Hierarchy

```typescript
// errors/index.ts
export class AppError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public code: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class NotFoundError extends AppError {
  constructor(message: string) {
    super(404, message, 'NOT_FOUND');
  }
}

export class ConflictError extends AppError {
  constructor(message: string) {
    super(409, message, 'CONFLICT');
  }
}

export class ValidationError extends AppError {
  constructor(details: unknown) {
    super(400, 'Validation failed', 'VALIDATION_ERROR', details);
  }
}

export class ForbiddenError extends AppError {
  constructor(message: string) {
    super(403, message, 'FORBIDDEN');
  }
}

export class UnauthorizedError extends AppError {
  constructor(message = 'Authentication required') {
    super(401, message, 'UNAUTHORIZED');
  }
}

export class RateLimitError extends AppError {
  constructor(retryAfter: number) {
    super(429, 'Too many requests', 'RATE_LIMIT_EXCEEDED', { retryAfter });
  }
}
```

### Centralized Error Handler Middleware

```typescript
function errorHandler(err: Error, req: Request, res: Response, _next: NextFunction) {
  // Zod validation errors
  if (err.name === 'ZodError') {
    return res.status(400).json({
      success: false,
      error: 'Validation failed',
      code: 'VALIDATION_ERROR',
      details: (err as any).flatten(),
    });
  }

  // Known application errors
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      success: false,
      error: err.message,
      code: err.code,
      details: err.details,
    });
  }

  // Unknown errors — log full details, return generic message
  console.error('Unhandled error:', {
    error: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
    requestId: req.headers['x-request-id'],
  });

  res.status(500).json({
    success: false,
    error: 'Internal server error',
    code: 'INTERNAL_ERROR',
  });
}
```

### Consistent API Response Format

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  code?: string;
  details?: unknown;
  meta?: {
    total: number;
    page: number;
    limit: number;
    hasMore: boolean;
  };
}

// Helper functions
function successResponse<T>(data: T, meta?: ApiResponse<T>['meta']): ApiResponse<T> {
  return { success: true, data, meta };
}

function errorResponse(message: string, code: string, details?: unknown): ApiResponse<never> {
  return { success: false, error: message, code, details };
}
```

---

## 5. Anti-Patterns to Avoid

### Business Logic in Controllers

```typescript
// BAD — controller doing business logic
app.post('/api/orders', async (req, res) => {
  const user = await db.from('users').select('*').eq('id', req.body.userId).single();
  if (user.data.balance < req.body.total) {
    return res.status(400).json({ error: 'Insufficient balance' });
  }
  // 50 more lines of business logic...
});

// GOOD — controller delegates to service
app.post('/api/orders', asyncHandler(async (req, res) => {
  const order = await orderService.createOrder(req.body);
  res.status(201).json({ success: true, data: order });
}));
```

### God Service (Service Doing Everything)

```typescript
// BAD — one service with 30+ methods across unrelated domains
class AppService {
  createUser() { /* ... */ }
  processPayment() { /* ... */ }
  sendEmail() { /* ... */ }
  generateReport() { /* ... */ }
}

// GOOD — separate services by domain
class UserService { /* user-related methods */ }
class PaymentService { /* payment-related methods */ }
class NotificationService { /* notification-related methods */ }
class ReportService { /* report-related methods */ }
```

### Direct Database Access from Controllers

```typescript
// BAD — controller queries the database directly
app.get('/api/users', async (req, res) => {
  const { data } = await db.from('users').select('*');
  res.json(data);
});

// GOOD — go through repository and service layers
app.get('/api/users', asyncHandler(async (req, res) => {
  const users = await userService.listUsers({ page: 1, limit: 20 });
  res.json({ success: true, data: users });
}));
```

---

## 6. Project Structure Reference

```
src/
├── controllers/        # HTTP request handlers (thin)
│   ├── userController.ts
│   └── orderController.ts
├── services/           # Business logic
│   ├── userService.ts
│   └── orderService.ts
├── repositories/       # Data access
│   ├── userRepository.ts
│   └── orderRepository.ts
├── middleware/          # Express middleware
│   ├── auth.ts
│   ├── errorHandler.ts
│   ├── rateLimiter.ts
│   └── validate.ts
├── errors/             # Custom error classes
│   └── index.ts
├── validators/         # Zod schemas
│   └── userSchemas.ts
├── types/              # TypeScript interfaces
│   └── index.ts
├── lib/                # Shared utilities
│   ├── database.ts
│   ├── cache.ts
│   └── logger.ts
├── routes/             # Route definitions
│   └── index.ts
├── container.ts        # Dependency injection composition root
└── app.ts              # Express app setup
```

---

*Reference for lazboy-backend-patterns skill v1.0.0*
