---
name: lazboy-database-optimization
description: "Optimize database queries, indexes, and schema design for La-Z-Boy applications. Covers PostgreSQL performance tuning, query analysis, connection pooling, caching strategies, and migration best practices. Use when diagnosing slow queries or designing database schemas."
version: "1.0.0"
category: Backend
tags: [backend, database, postgresql, performance]
---

# La-Z-Boy Database Optimization Skill

Guide for optimizing database performance across La-Z-Boy applications.

**Reference files — load when needed:**
- `references/query-patterns.md` — optimized query patterns for common operations
- `references/indexing-guide.md` — when and how to create indexes

**Scripts — run when needed:**
- `scripts/analyze_queries.py` — identify slow queries from pg_stat_statements
- `scripts/generate_migration.py` — create an Alembic migration from schema changes

---

## 1. Query Performance Rules

### Always Use EXPLAIN ANALYZE
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT s.name, c.name as category
FROM skills s
JOIN categories c ON s.category_id = c.id
WHERE s.is_published = true
ORDER BY s.created_at DESC
LIMIT 20;
```

### Avoid N+1 Queries
```python
# BAD — N+1 queries
skills = await db.execute(select(Skill))
for skill in skills:
    category = await db.execute(select(Category).where(Category.id == skill.category_id))

# GOOD — eager loading
skills = await db.execute(
    select(Skill).options(selectinload(Skill.category)).where(Skill.is_published == True)
)
```

## 2. Indexing Strategy

### When to Add Indexes
- Columns in `WHERE` clauses queried frequently
- Columns used in `JOIN` conditions
- Columns used in `ORDER BY` with `LIMIT`
- Foreign key columns (always)

### When NOT to Index
- Tables with < 1000 rows
- Columns with very low cardinality (boolean flags)
- Columns that are frequently updated

```sql
-- Composite index for common query pattern
CREATE INDEX CONCURRENTLY idx_skills_category_published
ON skills (category_id, is_published)
WHERE is_published = true;
```

## 3. Connection Pooling

```python
# SQLAlchemy async engine with pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```

## 4. Caching Strategy

- **L1 Cache**: Application-level (LRU cache for reference data)
- **L2 Cache**: Redis for session data and frequently accessed queries
- **Cache invalidation**: TTL-based (5 min for lists, 30 min for reference data)

## 5. Migration Best Practices

- Always use `CONCURRENTLY` for index creation in production
- Never drop columns directly — mark deprecated, remove in next release
- Test migrations on a copy of production data
- Keep migrations reversible (include downgrade)

## 6. Monitoring

Key metrics to track:
- Query execution time (p50, p95, p99)
- Connection pool utilization
- Cache hit ratio (target: > 90%)
- Dead tuple ratio (trigger VACUUM if > 10%)
