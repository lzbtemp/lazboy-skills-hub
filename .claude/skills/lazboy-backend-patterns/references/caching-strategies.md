# Caching Strategies for Backend Applications

Comprehensive guide to Redis caching, in-memory caching, cache invalidation patterns,
and HTTP caching headers for Node.js/Express applications.

---

## 1. Caching Fundamentals

### Why Cache?

| Problem                    | Caching Solution                          |
|----------------------------|-------------------------------------------|
| Slow database queries      | Cache query results in Redis or memory    |
| Repeated API calls         | HTTP cache headers, response caching      |
| Expensive computations     | Memoize results with TTL                  |
| High read-to-write ratio   | Cache-aside pattern with invalidation     |

### Cache Hit/Miss Flow

```
Client Request
     │
     ▼
┌──────────┐     hit     ┌───────┐
│  Check   │────────────►│ Return│
│  Cache   │             │ Cached│
└────┬─────┘             └───────┘
     │ miss
     ▼
┌──────────┐
│  Query   │
│ Database │
└────┬─────┘
     │
     ▼
┌──────────┐
│  Store   │
│ in Cache │
└────┬─────┘
     │
     ▼
  Return Data
```

---

## 2. Redis Caching

### Redis Client Setup

```typescript
// lib/redis.ts
import { createClient, RedisClientType } from 'redis';

let client: RedisClientType;

export async function getRedisClient(): Promise<RedisClientType> {
  if (!client) {
    client = createClient({
      url: process.env.REDIS_URL || 'redis://localhost:6379',
      socket: {
        reconnectStrategy: (retries: number) => {
          if (retries > 10) return new Error('Max reconnect attempts reached');
          return Math.min(retries * 100, 3000);
        },
      },
    });

    client.on('error', (err) => console.error('Redis error:', err));
    client.on('connect', () => console.log('Redis connected'));

    await client.connect();
  }
  return client;
}
```

### Cache-Aside Pattern (Lazy Loading)

The most common caching pattern. Data is loaded into the cache only when requested.

```typescript
// lib/cache.ts
import { RedisClientType } from 'redis';

export class CacheLayer {
  constructor(
    private redis: RedisClientType,
    private defaultTTL: number = 300, // 5 minutes
    private keyPrefix: string = 'app:',
  ) {}

  private prefixKey(key: string): string {
    return `${this.keyPrefix}${key}`;
  }

  async get<T>(key: string): Promise<T | null> {
    const cached = await this.redis.get(this.prefixKey(key));
    if (!cached) return null;
    return JSON.parse(cached) as T;
  }

  async set<T>(key: string, value: T, ttl?: number): Promise<void> {
    await this.redis.set(
      this.prefixKey(key),
      JSON.stringify(value),
      { EX: ttl ?? this.defaultTTL },
    );
  }

  async getOrFetch<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl?: number,
  ): Promise<T> {
    const cached = await this.get<T>(key);
    if (cached !== null) return cached;

    const data = await fetcher();
    await this.set(key, data, ttl);
    return data;
  }

  async invalidate(key: string): Promise<void> {
    await this.redis.del(this.prefixKey(key));
  }

  async invalidatePattern(pattern: string): Promise<void> {
    const keys = await this.redis.keys(this.prefixKey(pattern));
    if (keys.length > 0) {
      await this.redis.del(keys);
    }
  }
}
```

### Usage in a Service

```typescript
class ProductService {
  constructor(
    private productRepo: ProductRepository,
    private cache: CacheLayer,
  ) {}

  async getProduct(id: string): Promise<Product> {
    return this.cache.getOrFetch(
      `product:${id}`,
      () => this.productRepo.findById(id),
      600, // 10 minutes
    );
  }

  async listProducts(category: string, page: number): Promise<Product[]> {
    return this.cache.getOrFetch(
      `products:${category}:page:${page}`,
      () => this.productRepo.findByCategory(category, page),
      120, // 2 minutes — list caches are shorter
    );
  }

  async updateProduct(id: string, input: UpdateProductInput): Promise<Product> {
    const product = await this.productRepo.update(id, input);

    // Invalidate the specific product and all list caches for its category
    await this.cache.invalidate(`product:${id}`);
    await this.cache.invalidatePattern(`products:${product.category}:*`);

    return product;
  }
}
```

### Redis Data Structures for Caching

```typescript
// Sorted sets for leaderboards and ranked data
async function cacheLeaderboard(entries: LeaderboardEntry[]): Promise<void> {
  const multi = redis.multi();
  for (const entry of entries) {
    multi.zAdd('leaderboard', { score: entry.score, value: entry.userId });
  }
  multi.expire('leaderboard', 3600);
  await multi.exec();
}

async function getTopUsers(count: number): Promise<string[]> {
  return redis.zRange('leaderboard', 0, count - 1, { REV: true });
}

// Hash maps for structured objects
async function cacheUserSession(userId: string, session: SessionData): Promise<void> {
  await redis.hSet(`session:${userId}`, {
    token: session.token,
    role: session.role,
    loginAt: session.loginAt.toISOString(),
  });
  await redis.expire(`session:${userId}`, 86400); // 24 hours
}

// Sets for unique collections
async function trackActiveUsers(userId: string): Promise<void> {
  const today = new Date().toISOString().split('T')[0];
  await redis.sAdd(`active_users:${today}`, userId);
  await redis.expire(`active_users:${today}`, 172800); // 48 hours
}
```

---

## 3. In-Memory Caching

Best for small, frequently accessed, rarely changing data such as configuration
or feature flags.

### Simple LRU Cache

```typescript
// lib/memoryCache.ts
export class MemoryCache<T> {
  private cache = new Map<string, { value: T; expiresAt: number }>();
  private maxSize: number;

  constructor(maxSize: number = 1000) {
    this.maxSize = maxSize;
  }

  get(key: string): T | undefined {
    const entry = this.cache.get(key);
    if (!entry) return undefined;

    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      return undefined;
    }

    // Move to end (most recently used)
    this.cache.delete(key);
    this.cache.set(key, entry);
    return entry.value;
  }

  set(key: string, value: T, ttlMs: number = 60000): void {
    // Evict oldest if at capacity
    if (this.cache.size >= this.maxSize) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey) this.cache.delete(oldestKey);
    }

    this.cache.set(key, {
      value,
      expiresAt: Date.now() + ttlMs,
    });
  }

  invalidate(key: string): void {
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  get size(): number {
    return this.cache.size;
  }
}
```

### Usage: Feature Flags

```typescript
const featureFlagCache = new MemoryCache<boolean>(100);

async function isFeatureEnabled(flag: string): Promise<boolean> {
  const cached = featureFlagCache.get(`flag:${flag}`);
  if (cached !== undefined) return cached;

  const result = await db
    .from('feature_flags')
    .select('enabled')
    .eq('name', flag)
    .single();

  const enabled = result.data?.enabled ?? false;
  featureFlagCache.set(`flag:${flag}`, enabled, 30000); // 30 seconds
  return enabled;
}
```

### Multi-Layer Caching

Combine in-memory (L1) and Redis (L2) for the best performance:

```typescript
class MultiLayerCache {
  constructor(
    private l1: MemoryCache<unknown>,
    private l2: CacheLayer,
  ) {}

  async get<T>(key: string, fetcher: () => Promise<T>, ttl: number): Promise<T> {
    // L1 — in-memory (fastest)
    const memCached = this.l1.get(key) as T | undefined;
    if (memCached !== undefined) return memCached;

    // L2 — Redis
    const redisCached = await this.l2.get<T>(key);
    if (redisCached !== null) {
      this.l1.set(key, redisCached, ttl * 1000);
      return redisCached;
    }

    // Database — slowest
    const data = await fetcher();
    this.l1.set(key, data, ttl * 1000);
    await this.l2.set(key, data, ttl);
    return data;
  }

  async invalidate(key: string): Promise<void> {
    this.l1.invalidate(key);
    await this.l2.invalidate(key);
  }
}
```

---

## 4. Cache Invalidation Patterns

### Time-Based (TTL)

The simplest approach. Data expires after a fixed duration.

```typescript
// Short TTL for frequently changing data
await cache.set('dashboard:stats', stats, 30);     // 30 seconds

// Longer TTL for stable reference data
await cache.set('config:pricing', pricing, 3600);   // 1 hour

// Very long TTL for rarely changing data
await cache.set('static:countries', countries, 86400); // 24 hours
```

### Event-Based Invalidation

Invalidate cache entries when the underlying data changes.

```typescript
class OrderService {
  constructor(
    private orderRepo: OrderRepository,
    private cache: CacheLayer,
    private eventBus: EventEmitter,
  ) {
    // Listen for events that should trigger cache invalidation
    this.eventBus.on('order.created', (order: Order) => this.onOrderCreated(order));
    this.eventBus.on('order.updated', (order: Order) => this.onOrderUpdated(order));
  }

  async createOrder(input: CreateOrderInput): Promise<Order> {
    const order = await this.orderRepo.create(input);
    this.eventBus.emit('order.created', order);
    return order;
  }

  private async onOrderCreated(order: Order): Promise<void> {
    await this.cache.invalidate(`user:${order.userId}:orders`);
    await this.cache.invalidatePattern(`orders:list:*`);
  }

  private async onOrderUpdated(order: Order): Promise<void> {
    await this.cache.invalidate(`order:${order.id}`);
    await this.cache.invalidate(`user:${order.userId}:orders`);
  }
}
```

### Write-Through Cache

Update cache and database simultaneously on every write.

```typescript
async function updateProductWithWriteThrough(
  id: string,
  input: UpdateProductInput,
): Promise<Product> {
  // Update database
  const product = await productRepo.update(id, input);

  // Update cache immediately (no stale data window)
  await cache.set(`product:${id}`, product, 600);

  return product;
}
```

### Write-Behind (Write-Back) Cache

Write to cache first, then asynchronously persist to database. Useful for
high-write scenarios like counters or analytics.

```typescript
class ViewCounter {
  private buffer = new Map<string, number>();
  private flushInterval: NodeJS.Timeout;

  constructor(
    private redis: RedisClientType,
    private db: Database,
    flushIntervalMs: number = 10000,
  ) {
    this.flushInterval = setInterval(() => this.flush(), flushIntervalMs);
  }

  async increment(articleId: string): Promise<void> {
    // Immediate update in Redis
    await this.redis.incr(`views:${articleId}`);

    // Buffer for batch database write
    const current = this.buffer.get(articleId) ?? 0;
    this.buffer.set(articleId, current + 1);
  }

  private async flush(): Promise<void> {
    if (this.buffer.size === 0) return;

    const entries = Array.from(this.buffer.entries());
    this.buffer.clear();

    // Batch update database
    for (const [articleId, count] of entries) {
      await this.db
        .from('articles')
        .update({ view_count: this.db.raw(`view_count + ${count}`) })
        .eq('id', articleId);
    }
  }

  destroy(): void {
    clearInterval(this.flushInterval);
    this.flush(); // Final flush
  }
}
```

### Cache Stampede Prevention

When a popular cache key expires, many concurrent requests hit the database.
Use a mutex/lock to prevent this.

```typescript
class StampedeProtectedCache {
  constructor(private redis: RedisClientType, private cache: CacheLayer) {}

  async getOrFetchWithLock<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl: number,
  ): Promise<T> {
    // Try cache first
    const cached = await this.cache.get<T>(key);
    if (cached !== null) return cached;

    const lockKey = `lock:${key}`;
    const lockAcquired = await this.redis.set(lockKey, '1', {
      NX: true,  // Only set if not exists
      EX: 10,    // Lock expires in 10 seconds
    });

    if (lockAcquired) {
      try {
        const data = await fetcher();
        await this.cache.set(key, data, ttl);
        return data;
      } finally {
        await this.redis.del(lockKey);
      }
    }

    // Another process holds the lock — wait and retry from cache
    await new Promise((resolve) => setTimeout(resolve, 200));
    const retried = await this.cache.get<T>(key);
    if (retried !== null) return retried;

    // Fallback: fetch directly (lock holder may have failed)
    return fetcher();
  }
}
```

---

## 5. HTTP Caching Headers

### Cache-Control Header

```typescript
// Middleware to set cache headers

// Public, static assets — cached by CDN and browser
function staticCacheHeaders(req: Request, res: Response, next: NextFunction) {
  res.set('Cache-Control', 'public, max-age=31536000, immutable');
  next();
}

// API responses — private, short cache, must revalidate
function apiCacheHeaders(maxAge: number = 60) {
  return (req: Request, res: Response, next: NextFunction) => {
    res.set('Cache-Control', `private, max-age=${maxAge}, must-revalidate`);
    next();
  };
}

// No cache — for dynamic/sensitive data
function noCacheHeaders(req: Request, res: Response, next: NextFunction) {
  res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
  res.set('Pragma', 'no-cache');
  res.set('Expires', '0');
  next();
}
```

### Cache-Control Directives Reference

| Directive         | Meaning                                                 |
|-------------------|---------------------------------------------------------|
| `public`          | Any cache (CDN, browser) can store the response         |
| `private`         | Only the browser can cache (not CDN)                    |
| `max-age=N`       | Response is fresh for N seconds                         |
| `s-maxage=N`      | Override max-age for shared caches (CDNs)               |
| `no-cache`        | Cache but revalidate with server before using           |
| `no-store`        | Do not cache at all                                     |
| `must-revalidate` | Once stale, must revalidate before reusing              |
| `immutable`       | Content will never change (use with hashed file names)  |
| `stale-while-revalidate=N` | Serve stale while fetching fresh in background |

### ETag-Based Conditional Requests

```typescript
import crypto from 'crypto';

function withETag(req: Request, res: Response, data: unknown): void {
  const json = JSON.stringify(data);
  const etag = `"${crypto.createHash('md5').update(json).digest('hex')}"`;

  res.set('ETag', etag);

  // If client sent If-None-Match and it matches, return 304
  if (req.headers['if-none-match'] === etag) {
    res.status(304).end();
    return;
  }

  res.json(data);
}

// Usage
app.get('/api/products/:id', async (req, res) => {
  const product = await productService.getProduct(req.params.id);
  withETag(req, res, { success: true, data: product });
});
```

### Route-Level Cache Configuration

```typescript
// routes/index.ts
const router = Router();

// Static reference data — cache 1 hour
router.get('/api/categories', apiCacheHeaders(3600), categoryController.list);

// User-specific data — no shared caching
router.get('/api/me/profile', noCacheHeaders, profileController.get);

// Product listings — cache 2 minutes
router.get('/api/products', apiCacheHeaders(120), productController.list);

// Static assets — cache forever (use hashed filenames)
app.use('/static', staticCacheHeaders, express.static('public'));
```

---

## 6. Caching Best Practices

### Key Naming Convention

Use a consistent, hierarchical key naming scheme:

```
{service}:{entity}:{identifier}:{variant}
```

Examples:
```
app:user:abc123              — single user
app:user:abc123:orders       — user's orders
app:products:electronics:p1  — product list, page 1
app:config:feature_flags     — configuration
app:rate:ip:192.168.1.1      — rate limit counter
```

### TTL Guidelines

| Data Type                | Suggested TTL | Reason                            |
|--------------------------|---------------|-----------------------------------|
| User session             | 24 hours      | Security balanced with UX         |
| Product details          | 10 minutes    | Moderate change frequency         |
| Product listings         | 2 minutes     | Lists change more often           |
| Feature flags            | 30 seconds    | Need quick propagation            |
| Static config            | 1 hour        | Rarely changes                    |
| Analytics/counters       | 5 minutes     | Approximate is acceptable         |
| Search results           | 1 minute      | Balance freshness with speed      |

### Common Pitfalls

1. **Caching null/empty results** -- always cache "not found" with a short TTL to
   prevent repeated database queries for missing data.

2. **Unbounded cache growth** -- always set TTLs and max-size limits on in-memory
   caches.

3. **Cache key collisions** -- use prefixes and include all relevant parameters in
   the key.

4. **Serialization overhead** -- for very large objects, consider caching only
   essential fields or using MessagePack instead of JSON.

5. **Cache warming on deploy** -- pre-populate critical caches after deployment to
   avoid cold-start latency spikes.

```typescript
// Cache warming on application start
async function warmCaches(): Promise<void> {
  console.log('Warming caches...');

  const [categories, config] = await Promise.all([
    categoryRepo.findAll(),
    configRepo.getAll(),
  ]);

  await Promise.all([
    cache.set('categories:all', categories, 3600),
    cache.set('config:all', config, 3600),
  ]);

  console.log('Cache warming complete');
}
```

---

*Reference for lazboy-backend-patterns skill v1.0.0*
