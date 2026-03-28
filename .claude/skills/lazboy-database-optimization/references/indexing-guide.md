# Database Indexing Guide

A practical guide to creating, maintaining, and monitoring indexes in PostgreSQL. Covers when to index, composite index strategies, specialized index types, and monitoring tools.

---

## When to Add an Index

### Add an Index When

1. **A column appears in WHERE clauses frequently** with good selectivity (filters out most rows)
2. **A column is used in JOIN conditions** (especially foreign keys)
3. **A column is used in ORDER BY** and the query has a LIMIT
4. **A column is used in GROUP BY** with aggregation
5. **EXPLAIN ANALYZE shows Seq Scan** on a large table with low rows returned
6. **Query response time exceeds acceptable thresholds** and the plan shows table scans

### Do NOT Add an Index When

1. **The table is small** (< 10,000 rows) -- sequential scan is often faster
2. **The column has very low selectivity** (e.g., boolean column with 50/50 distribution)
3. **The table is write-heavy with rare reads** -- indexes slow down INSERT/UPDATE/DELETE
4. **The query already returns most rows** in the table (planner will choose seq scan anyway)
5. **An existing index already covers the query** -- adding duplicates wastes space

### Decision Framework

```
Is the table > 10,000 rows?
  No  -> Skip indexing (seq scan is fine)
  Yes -> Does the query filter/join/sort on this column?
    No  -> No index needed
    Yes -> Does the filter have good selectivity (< 10-15% of rows)?
      No  -> Consider partial index or skip
      Yes -> Add index. Use composite if query filters on multiple columns.
```

---

## Composite Index Column Ordering

The order of columns in a composite index is critical for performance.

### Rules of Thumb

1. **Equality columns first**, range columns last
2. **Most selective column first** (when all are equality)
3. **Columns used in ORDER BY** should follow the filter columns

### Examples

```sql
-- Query: WHERE status = 'active' AND created_at > '2025-01-01' ORDER BY created_at
-- status is equality, created_at is range + sort
CREATE INDEX idx_orders_status_created ON orders (status, created_at);

-- Query: WHERE user_id = 42 AND status = 'completed' ORDER BY created_at DESC
-- Two equality columns + sort column
CREATE INDEX idx_orders_user_status_created ON orders (user_id, status, created_at DESC);

-- Query: WHERE category_id = 5 AND price BETWEEN 100 AND 500
-- category_id is equality, price is range
CREATE INDEX idx_products_category_price ON products (category_id, price);
```

### How Composite Indexes Work

A composite index on `(A, B, C)` can be used for:

| Query Filter | Uses Index? | Notes |
|-------------|-------------|-------|
| `WHERE A = 1` | Yes | Leftmost prefix |
| `WHERE A = 1 AND B = 2` | Yes | Two-column prefix |
| `WHERE A = 1 AND B = 2 AND C = 3` | Yes | Full index |
| `WHERE B = 2` | No | Skips leading column |
| `WHERE A = 1 AND C = 3` | Partial | Uses A only; C requires filter |
| `WHERE B = 2 AND C = 3` | No | Missing leading column |
| `ORDER BY A, B` | Yes | Matches index order |
| `ORDER BY B, A` | No | Wrong order |

---

## Partial Indexes

Index only the rows you actually query.

```sql
-- Only 5% of orders are 'pending', but you query them constantly
CREATE INDEX idx_pending_orders ON orders (created_at)
  WHERE status = 'pending';

-- Query MUST include the matching WHERE clause
SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at;  -- Uses index
SELECT * FROM orders WHERE status = 'shipped' ORDER BY created_at;  -- Does NOT use this index

-- Soft-delete pattern: only index non-deleted rows
CREATE INDEX idx_active_products ON products (category_id, name)
  WHERE deleted_at IS NULL;

-- Unique constraint on active records only
CREATE UNIQUE INDEX idx_unique_active_email ON users (email)
  WHERE deleted_at IS NULL;
```

**Benefits:**
- Smaller index size (less storage, faster to scan)
- Lower maintenance cost on INSERT/UPDATE
- Better cache utilization

---

## Covering Indexes (INCLUDE)

PostgreSQL 11+ supports covering indexes with `INCLUDE` to enable index-only scans.

```sql
-- Without INCLUDE: index scan + heap lookup for total_amount and status
CREATE INDEX idx_orders_user_date ON orders (user_id, created_at);
-- Plan: Index Scan -> Heap fetch for total_amount, status

-- With INCLUDE: index-only scan (no heap access)
CREATE INDEX idx_orders_user_date_covering ON orders (user_id, created_at)
  INCLUDE (total_amount, status);
-- Plan: Index Only Scan (much faster)

-- Query that benefits
SELECT created_at, total_amount, status
FROM orders
WHERE user_id = 42
ORDER BY created_at DESC
LIMIT 10;
```

**When to Use INCLUDE:**
- The query SELECTs columns not in the WHERE/ORDER BY
- The table is large and heap lookups are expensive
- The included columns are small (avoid including large text/jsonb columns)

**INCLUDE vs Adding to Index Key:**
- `INCLUDE` columns are stored in leaf pages only (not used for sorting/filtering)
- Key columns are stored at all tree levels and used for sorting
- Use `INCLUDE` for columns that are only SELECTed, not filtered or sorted

---

## Index-Only Scans

An index-only scan reads data entirely from the index without visiting the table heap.

### Requirements

1. All columns in SELECT, WHERE, ORDER BY must be in the index (key + INCLUDE)
2. The visibility map must indicate that pages are all-visible (run VACUUM regularly)

### Checking Visibility Map Coverage

```sql
-- Check how many heap fetches are needed
EXPLAIN (ANALYZE, BUFFERS) SELECT user_id, created_at FROM orders WHERE user_id = 42;

-- In the output, look for:
--   Index Only Scan
--   Heap Fetches: 0        <-- ideal
--   Heap Fetches: 1523     <-- VACUUM needed

-- Run VACUUM to update visibility map
VACUUM orders;
-- or
VACUUM (VERBOSE) orders;
```

---

## Full-Text Search Indexes

### GIN Index for tsvector

```sql
-- Option 1: Index a generated tsvector column
ALTER TABLE products ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B')
  ) STORED;

CREATE INDEX idx_products_fts ON products USING gin(search_vector);

-- Query
SELECT name, ts_rank(search_vector, query) AS rank
FROM products, to_tsquery('english', 'leather & recliner') query
WHERE search_vector @@ query
ORDER BY rank DESC
LIMIT 20;

-- Option 2: GIN index on expression (no stored column)
CREATE INDEX idx_products_fts_expr ON products
  USING gin(to_tsvector('english', name || ' ' || description));
```

### GIN Trigram Index for Pattern Matching

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_products_name_trgm ON products USING gin(name gin_trgm_ops);

-- Now LIKE/ILIKE with leading wildcards can use the index
SELECT * FROM products WHERE name ILIKE '%reclin%';

-- Similarity search
SELECT name, similarity(name, 'reclienr') AS sim
FROM products
WHERE similarity(name, 'reclienr') > 0.3
ORDER BY sim DESC;
```

---

## GiST Indexes

Best for range types, geometric data, and nearest-neighbor queries.

```sql
-- Range type: find overlapping date ranges
CREATE INDEX idx_bookings_dates ON bookings USING gist(date_range);
SELECT * FROM bookings WHERE date_range && daterange('2025-06-01', '2025-06-15');

-- Exclusion constraint: prevent overlapping bookings for the same room
ALTER TABLE bookings ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (room_id WITH =, date_range WITH &&);

-- PostGIS: spatial index
CREATE INDEX idx_stores_geom ON stores USING gist(geom);
SELECT name FROM stores
WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(-73.99, 40.73), 4326)::geography, 5000);
```

---

## BRIN Indexes (Block Range Index)

Very compact index for naturally ordered data (e.g., time-series tables where rows are inserted in order).

```sql
-- Time-series data where created_at is roughly in insertion order
CREATE INDEX idx_events_created_brin ON events USING brin(created_at);

-- Much smaller than B-tree for large tables (often 1000x smaller)
-- Best when physical row order correlates with column value
```

**When to Use BRIN:**
- Very large tables (millions of rows)
- Data is physically ordered by the indexed column (append-only or time-series)
- Exact lookups are not needed (BRIN is lossy; it narrows to block ranges)

---

## Index Maintenance

### Index Bloat

Indexes accumulate dead tuples over time. VACUUM removes dead rows from the table but does not reclaim space within B-tree index pages.

```sql
-- Check index bloat estimate
SELECT
  schemaname || '.' || indexrelname AS index_name,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
  idx_scan AS times_used,
  idx_tup_read AS tuples_read,
  idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check estimated bloat using pgstattuple extension
CREATE EXTENSION IF NOT EXISTS pgstattuple;
SELECT * FROM pgstattuple('idx_orders_user_id');
-- avg_leaf_density < 50% suggests significant bloat
```

### REINDEX

```sql
-- Rebuild a single index (locks the table)
REINDEX INDEX idx_orders_user_id;

-- Rebuild all indexes on a table
REINDEX TABLE orders;

-- Rebuild concurrently (PostgreSQL 12+; no lock)
REINDEX INDEX CONCURRENTLY idx_orders_user_id;

-- Rebuild all indexes on a table concurrently
REINDEX TABLE CONCURRENTLY orders;
```

### Automated Maintenance Schedule

```sql
-- Option 1: Use pg_cron for scheduled reindex
SELECT cron.schedule('reindex-orders', '0 3 * * 0',
  'REINDEX TABLE CONCURRENTLY orders');

-- Option 2: Regular VACUUM ANALYZE keeps stats fresh
VACUUM ANALYZE orders;
```

---

## Monitoring Index Usage

### pg_stat_user_indexes

```sql
-- Find unused indexes (candidates for removal)
SELECT
  schemaname,
  relname AS table_name,
  indexrelname AS index_name,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
  idx_scan AS times_used
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname NOT IN ('pg_catalog', 'pg_toast')
ORDER BY pg_relation_size(indexrelid) DESC;

-- Find the most-used indexes
SELECT
  relname AS table_name,
  indexrelname AS index_name,
  idx_scan AS scans,
  idx_tup_read AS tuples_read,
  idx_tup_fetch AS tuples_fetched,
  pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC
LIMIT 20;
```

### Table Scan Ratio

```sql
-- Tables with high sequential scan ratio (may need indexes)
SELECT
  relname AS table_name,
  seq_scan,
  idx_scan,
  CASE WHEN (seq_scan + idx_scan) > 0
    THEN round(100.0 * seq_scan / (seq_scan + idx_scan), 1)
    ELSE 0
  END AS seq_scan_pct,
  seq_tup_read,
  idx_tup_fetch,
  pg_size_pretty(pg_relation_size(relid)) AS table_size
FROM pg_stat_user_tables
WHERE (seq_scan + idx_scan) > 100  -- At least some activity
ORDER BY seq_scan_pct DESC;
```

### Cache Hit Ratio

```sql
-- Index cache hit ratio (should be > 99%)
SELECT
  sum(idx_blks_hit) AS cache_hits,
  sum(idx_blks_read) AS disk_reads,
  CASE WHEN sum(idx_blks_hit + idx_blks_read) > 0
    THEN round(100.0 * sum(idx_blks_hit) / sum(idx_blks_hit + idx_blks_read), 2)
    ELSE 100
  END AS cache_hit_ratio
FROM pg_statio_user_indexes;
```

### Duplicate and Overlapping Indexes

```sql
-- Find potentially duplicate indexes
SELECT
  a.indexrelid::regclass AS index_a,
  b.indexrelid::regclass AS index_b,
  pg_size_pretty(pg_relation_size(a.indexrelid)) AS size_a,
  pg_size_pretty(pg_relation_size(b.indexrelid)) AS size_b
FROM pg_index a
JOIN pg_index b ON a.indrelid = b.indrelid
  AND a.indexrelid < b.indexrelid
  AND a.indkey::text = b.indkey::text
WHERE a.indrelid::regclass::text NOT LIKE 'pg_%';
```

---

## Index Impact on Write Performance

Every index adds overhead to INSERT, UPDATE, and DELETE operations.

| Operation | Index Overhead | Notes |
|-----------|---------------|-------|
| INSERT | Medium | Each index must be updated with new entry |
| UPDATE (indexed col) | High | Old entry removed, new entry inserted in each affected index |
| UPDATE (non-indexed col) | Low | HOT update possible if no indexed column changes |
| DELETE | Medium | Index entries marked for cleanup |
| VACUUM | Varies | Must scan all indexes to remove dead pointers |

### Guidelines

- Aim for **5-7 indexes** per table as a starting point
- More than **10 indexes** on a write-heavy table deserves scrutiny
- Use `pg_stat_user_indexes` to drop unused indexes
- Consider partial indexes to reduce write amplification

---

## Quick Reference: Index Selection

| Query Pattern | Index Type | Example |
|--------------|-----------|---------|
| `WHERE col = value` | B-tree | `CREATE INDEX ON t (col)` |
| `WHERE col BETWEEN a AND b` | B-tree | `CREATE INDEX ON t (col)` |
| `WHERE col IN (...)` | B-tree | `CREATE INDEX ON t (col)` |
| `ORDER BY col LIMIT N` | B-tree | `CREATE INDEX ON t (col)` |
| `WHERE col LIKE 'abc%'` | B-tree | `CREATE INDEX ON t (col)` |
| `WHERE col LIKE '%abc%'` | GIN (trigram) | `CREATE INDEX ON t USING gin(col gin_trgm_ops)` |
| `WHERE col @@ tsquery` | GIN | `CREATE INDEX ON t USING gin(col)` |
| `WHERE jsonb @> '{}'` | GIN | `CREATE INDEX ON t USING gin(col jsonb_path_ops)` |
| `WHERE array @> ARRAY[...]` | GIN | `CREATE INDEX ON t USING gin(col)` |
| `WHERE range && range` | GiST | `CREATE INDEX ON t USING gist(col)` |
| `WHERE ST_DWithin(...)` | GiST | `CREATE INDEX ON t USING gist(col)` |
| Time-series, append-only | BRIN | `CREATE INDEX ON t USING brin(col)` |
| `WHERE active = true` (5%) | Partial B-tree | `CREATE INDEX ON t (col) WHERE active` |
| SELECT cols without heap | Covering | `CREATE INDEX ON t (a) INCLUDE (b, c)` |

---

*Reference: [PostgreSQL Index Documentation](https://www.postgresql.org/docs/current/indexes.html) | [Use The Index, Luke](https://use-the-index-luke.com/) | [PostgreSQL Wiki - Index Maintenance](https://wiki.postgresql.org/wiki/Index_Maintenance)*
