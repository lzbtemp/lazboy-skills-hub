# SQL Query Optimization Patterns

A practical reference for writing performant SQL queries, interpreting execution plans, and avoiding common anti-patterns. Examples are PostgreSQL-focused but principles apply broadly.

---

## Index Types and When to Use Them

### B-tree (Default)

The default index type. Best for equality and range queries.

```sql
-- Equality lookups
CREATE INDEX idx_users_email ON users (email);
SELECT * FROM users WHERE email = 'user@example.com';

-- Range queries
CREATE INDEX idx_orders_created ON orders (created_at);
SELECT * FROM orders WHERE created_at >= '2025-01-01' AND created_at < '2025-02-01';

-- Sorting
SELECT * FROM orders ORDER BY created_at DESC LIMIT 20;
```

### GIN (Generalized Inverted Index)

Best for full-text search, JSONB, arrays, and multi-valued columns.

```sql
-- Full-text search
CREATE INDEX idx_products_search ON products USING gin(to_tsvector('english', name || ' ' || description));
SELECT * FROM products WHERE to_tsvector('english', name || ' ' || description) @@ to_tsquery('recliner & leather');

-- JSONB containment
CREATE INDEX idx_products_attrs ON products USING gin(attributes jsonb_path_ops);
SELECT * FROM products WHERE attributes @> '{"color": "charcoal"}';

-- Array contains
CREATE INDEX idx_tags ON articles USING gin(tags);
SELECT * FROM articles WHERE tags @> ARRAY['postgresql', 'optimization'];
```

### GiST (Generalized Search Tree)

Best for geometric data, ranges, and nearest-neighbor queries.

```sql
-- Range types (e.g., date ranges for reservations)
CREATE INDEX idx_reservations_period ON reservations USING gist(date_range);
SELECT * FROM reservations WHERE date_range && daterange('2025-03-01', '2025-03-15');

-- Geometric / PostGIS
CREATE INDEX idx_stores_location ON stores USING gist(location);
SELECT * FROM stores WHERE ST_DWithin(location, ST_MakePoint(-73.99, 40.73)::geography, 5000);
```

### Partial Indexes

Index only a subset of rows. Reduces index size and maintenance cost.

```sql
-- Only index active users (skip soft-deleted rows)
CREATE INDEX idx_active_users_email ON users (email) WHERE deleted_at IS NULL;

-- Only index pending orders
CREATE INDEX idx_pending_orders ON orders (created_at) WHERE status = 'pending';

-- Only index non-null values
CREATE INDEX idx_users_phone ON users (phone) WHERE phone IS NOT NULL;
```

### Covering Indexes (INCLUDE)

Include non-indexed columns to enable index-only scans.

```sql
-- Avoid heap lookups by including commonly selected columns
CREATE INDEX idx_orders_user_date ON orders (user_id, created_at)
  INCLUDE (total_amount, status);

-- This query can be answered entirely from the index
SELECT created_at, total_amount, status
FROM orders
WHERE user_id = 42
ORDER BY created_at DESC;
```

---

## EXPLAIN ANALYZE Interpretation

### Reading Execution Plans

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.id, o.total_amount, u.name
FROM orders o
JOIN users u ON u.id = o.user_id
WHERE o.created_at >= '2025-01-01'
  AND o.status = 'completed'
ORDER BY o.created_at DESC
LIMIT 20;
```

### Key Metrics to Watch

| Metric | What It Means | Action If High |
|--------|---------------|----------------|
| **Seq Scan** | Full table scan | Add an index on the filter columns |
| **actual time** | Time in ms (startup..total) | Focus on highest total time nodes |
| **rows** vs **Rows Removed by Filter** | How selective the filter is | Poor selectivity = wrong index or missing index |
| **Buffers: shared hit** | Pages read from cache | Good if high relative to read |
| **Buffers: shared read** | Pages read from disk | Bad if high; need more memory or better index |
| **Sort Method: external merge** | Sort spilled to disk | Increase `work_mem` or add index for ordering |
| **Hash Batch** > 1 | Hash join spilled to disk | Increase `work_mem` |
| **Loops** | Number of times a node executes | High loop count with nested loop = possible N+1 |

### Plan Node Types

| Node | Meaning | Performance Notes |
|------|---------|-------------------|
| **Seq Scan** | Full table scan | Fine for small tables; bad for large filtered queries |
| **Index Scan** | Index lookup + heap fetch | Good for selective queries returning few rows |
| **Index Only Scan** | Answered entirely from index | Best case; no heap access needed |
| **Bitmap Index Scan** | Build bitmap from index, then scan heap | Good for moderate selectivity |
| **Nested Loop** | For each outer row, scan inner | Fast with index on inner; bad with sequential inner |
| **Hash Join** | Build hash table from one side | Good for equi-joins; watch for spilling |
| **Merge Join** | Both sides pre-sorted, merge | Great when both inputs are pre-sorted |
| **Sort** | In-memory or on-disk sort | Check if an index could eliminate it |
| **Aggregate** | GROUP BY / COUNT / SUM | Consider partial aggregation or materialized views |

---

## Common Anti-Patterns

### 1. SELECT * (Fetching All Columns)

```sql
-- BAD: Fetches all columns, prevents index-only scans, wastes I/O
SELECT * FROM orders WHERE user_id = 42;

-- GOOD: Select only needed columns
SELECT id, total_amount, status, created_at FROM orders WHERE user_id = 42;
```

### 2. N+1 Query Problem

```sql
-- BAD: One query per user to get their orders (N+1)
-- Application code:
--   users = query("SELECT * FROM users LIMIT 100")
--   for user in users:
--       orders = query("SELECT * FROM orders WHERE user_id = ?", user.id)

-- GOOD: Single JOIN query
SELECT u.id, u.name, o.id AS order_id, o.total_amount
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE u.id IN (SELECT id FROM users LIMIT 100);

-- GOOD: Or use a lateral join for top-N per group
SELECT u.id, u.name, recent.*
FROM users u
CROSS JOIN LATERAL (
  SELECT id, total_amount, created_at
  FROM orders
  WHERE user_id = u.id
  ORDER BY created_at DESC
  LIMIT 5
) recent;
```

### 3. Missing Indexes on Foreign Keys

```sql
-- Foreign keys do NOT automatically create indexes in PostgreSQL
ALTER TABLE orders ADD CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id);

-- You MUST create the index yourself
CREATE INDEX idx_orders_user_id ON orders (user_id);
```

### 4. Implicit Type Casts (Index Bypass)

```sql
-- BAD: Comparing varchar column with integer bypasses index
SELECT * FROM users WHERE phone = 5551234567;
-- PostgreSQL will cast: WHERE phone::bigint = 5551234567 (no index used)

-- GOOD: Match the column type
SELECT * FROM users WHERE phone = '5551234567';
```

### 5. Functions on Indexed Columns

```sql
-- BAD: Function on column prevents index usage
SELECT * FROM orders WHERE EXTRACT(YEAR FROM created_at) = 2025;
SELECT * FROM users WHERE LOWER(email) = 'user@example.com';

-- GOOD: Rewrite to use range (index-friendly)
SELECT * FROM orders WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01';

-- GOOD: Create an expression index
CREATE INDEX idx_users_email_lower ON users (LOWER(email));
SELECT * FROM users WHERE LOWER(email) = 'user@example.com';
```

### 6. LIKE with Leading Wildcard

```sql
-- BAD: Leading wildcard cannot use B-tree index
SELECT * FROM products WHERE name LIKE '%recliner%';

-- GOOD: Use GIN trigram index for pattern matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_products_name_trgm ON products USING gin(name gin_trgm_ops);
SELECT * FROM products WHERE name LIKE '%recliner%';

-- GOOD: Or use full-text search
SELECT * FROM products WHERE to_tsvector('english', name) @@ to_tsquery('recliner');
```

### 7. Missing LIMIT on Large Result Sets

```sql
-- BAD: Fetching potentially millions of rows
SELECT * FROM audit_log WHERE action = 'page_view';

-- GOOD: Always paginate
SELECT id, user_id, action, created_at
FROM audit_log
WHERE action = 'page_view'
ORDER BY created_at DESC
LIMIT 50 OFFSET 0;

-- BETTER: Keyset pagination (avoids OFFSET performance degradation)
SELECT id, user_id, action, created_at
FROM audit_log
WHERE action = 'page_view'
  AND created_at < '2025-03-15T10:30:00Z'  -- last seen timestamp
ORDER BY created_at DESC
LIMIT 50;
```

---

## Query Rewriting Techniques

### CTEs vs Subqueries

PostgreSQL 12+ inlines CTEs when possible, but `MATERIALIZED` / `NOT MATERIALIZED` give you control.

```sql
-- CTE (may be inlined by optimizer in PG 12+)
WITH active_users AS (
  SELECT id, name FROM users WHERE status = 'active'
)
SELECT au.name, COUNT(o.id) AS order_count
FROM active_users au
JOIN orders o ON o.user_id = au.id
GROUP BY au.name;

-- Force materialization (useful when CTE is referenced multiple times)
WITH active_users AS MATERIALIZED (
  SELECT id, name FROM users WHERE status = 'active'
)
SELECT au.name, COUNT(o.id) AS order_count
FROM active_users au
JOIN orders o ON o.user_id = au.id
GROUP BY au.name;

-- Equivalent subquery (always inlined)
SELECT u.name, COUNT(o.id) AS order_count
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE u.status = 'active'
GROUP BY u.name;
```

### EXISTS vs IN vs JOIN

```sql
-- EXISTS: Best for correlated subqueries (stops at first match)
SELECT u.id, u.name
FROM users u
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.status = 'completed');

-- IN: Fine for small subquery results
SELECT u.id, u.name
FROM users u
WHERE u.id IN (SELECT DISTINCT user_id FROM orders WHERE status = 'completed');

-- JOIN: Be careful of duplicates if relationship is one-to-many
SELECT DISTINCT u.id, u.name
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE o.status = 'completed';
```

### Window Functions (Avoid Self-Joins)

```sql
-- BAD: Self-join to get previous order
SELECT o.id, o.total_amount,
       prev.total_amount AS prev_amount
FROM orders o
LEFT JOIN orders prev ON prev.user_id = o.user_id
  AND prev.created_at = (
    SELECT MAX(created_at) FROM orders
    WHERE user_id = o.user_id AND created_at < o.created_at
  );

-- GOOD: Window function
SELECT id, total_amount,
       LAG(total_amount) OVER (PARTITION BY user_id ORDER BY created_at) AS prev_amount
FROM orders;

-- Running totals
SELECT id, total_amount,
       SUM(total_amount) OVER (PARTITION BY user_id ORDER BY created_at) AS running_total
FROM orders;

-- Rank / deduplicate
SELECT * FROM (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rn
  FROM orders
) sub
WHERE rn = 1;  -- Latest order per user
```

---

## Materialized Views

Use materialized views for expensive aggregations that don't need real-time data.

```sql
-- Create materialized view for dashboard stats
CREATE MATERIALIZED VIEW mv_daily_sales AS
SELECT
  DATE(created_at) AS sale_date,
  COUNT(*) AS order_count,
  SUM(total_amount) AS total_revenue,
  AVG(total_amount) AS avg_order_value,
  COUNT(DISTINCT user_id) AS unique_customers
FROM orders
WHERE status = 'completed'
GROUP BY DATE(created_at);

-- Create index on the materialized view
CREATE UNIQUE INDEX idx_mv_daily_sales_date ON mv_daily_sales (sale_date);

-- Refresh (blocks reads during refresh)
REFRESH MATERIALIZED VIEW mv_daily_sales;

-- Refresh concurrently (requires unique index; doesn't block reads)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales;

-- Query the view (instant, no complex aggregation)
SELECT * FROM mv_daily_sales
WHERE sale_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY sale_date DESC;
```

---

## Batch Operations

```sql
-- BAD: Inserting rows one at a time
INSERT INTO products (name, price) VALUES ('A', 10);
INSERT INTO products (name, price) VALUES ('B', 20);
INSERT INTO products (name, price) VALUES ('C', 30);

-- GOOD: Batch insert
INSERT INTO products (name, price) VALUES
  ('A', 10),
  ('B', 20),
  ('C', 30);

-- GOOD: Batch update with FROM
UPDATE products p
SET price = v.new_price
FROM (VALUES (1, 15.99), (2, 25.99), (3, 35.99)) AS v(id, new_price)
WHERE p.id = v.id;

-- GOOD: Batch delete with chunking (avoid locking huge tables)
DELETE FROM audit_log
WHERE id IN (
  SELECT id FROM audit_log
  WHERE created_at < '2024-01-01'
  LIMIT 10000
);
```

---

## Connection and Query Tuning Parameters

```sql
-- Per-query memory for sorts and hashes
SET work_mem = '256MB';  -- Default is 4MB; increase for complex queries

-- Parallelism
SET max_parallel_workers_per_gather = 4;

-- Statistics target for better plans on skewed data
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 1000;
ANALYZE orders;

-- Disable seq scan temporarily to test if index is used (debugging only)
SET enable_seqscan = off;
EXPLAIN ANALYZE SELECT ...;
SET enable_seqscan = on;  -- Always re-enable
```

---

*Reference: [PostgreSQL Documentation](https://www.postgresql.org/docs/current/) | [Use The Index, Luke](https://use-the-index-luke.com/) | [pganalyze](https://pganalyze.com/docs)*
