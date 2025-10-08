# Performance Optimization Guide

## Overview
This document describes the performance optimizations implemented to achieve <100ms response times for CRUD operations in the Task Management API. All optimizations are validated by comprehensive performance tests.

## Performance Requirements

### Response Time Targets
| Operation Type | Target | Acceptable | Notes |
|---------------|--------|------------|-------|
| Single Read | <50ms | <100ms | Fastest operation |
| Single Create | <100ms | <150ms | Includes validation |
| Single Update | <100ms | <150ms | Includes index updates |
| Single Delete | <100ms | <150ms | Includes cascades |
| Paginated List (20) | <200ms | <300ms | Bulk read operation |
| Concurrent (10 reads) | <500ms total | <1000ms | Connection pool test |

## Architecture Overview

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│   FastAPI Application       │
│   - Request validation      │
│   - Performance monitoring  │
└──────┬──────────────────────┘
       │
       ├──────────┐
       │          │
       ▼          ▼
┌──────────┐  ┌──────────────┐
│  Cache   │  │   Database   │
│  (Redis) │  │ (PostgreSQL) │
│  - 300s  │  │ - Pool: 20   │
│    TTL   │  │ - Overflow:10│
└──────────┘  └──────────────┘
```

## 1. Database Connection Pooling

### Configuration

**File**: `app/core/database.py`

```python
# Connection pool settings
POOL_SIZE = 20              # Persistent connections
MAX_OVERFLOW = 10           # Extra connections during spikes
POOL_TIMEOUT = 30           # Seconds to wait for connection
POOL_RECYCLE = 3600         # Recycle connections after 1 hour
POOL_PRE_PING = True        # Health check before use
```

### Benefits

- **Reduced Latency**: Eliminates 50-100ms connection overhead
- **Scalability**: Handles up to 30 concurrent requests
- **Reliability**: Auto-recovers from database disconnections
- **Resource Efficiency**: Reuses connections instead of creating new ones

### Implementation Details

#### SQLAlchemy Async Engine

```python
engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    execution_options={
        "isolation_level": "READ COMMITTED",
    },
)
```

#### Session Management

```python
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading after commit
    autocommit=False,
    autoflush=False,
)
```

### Monitoring

Check pool status:
```python
from app.core.database import DatabaseHealthCheck

status = DatabaseHealthCheck.get_pool_status()
print(f"Active connections: {status['checked_out']}/{status['size']}")
```

## 2. Query Optimization

### Indexing Strategy

All frequently queried columns are indexed for O(log n) lookup performance:

```sql
-- User table indexes (from design docs)
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_is_verified ON users(is_verified);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
```

### Query Patterns

#### Efficient Pagination

```python
from app.core.performance import QueryOptimizer

# Calculate pagination with max limit enforcement
offset, limit = QueryOptimizer.build_pagination(page=2, limit=20)

query = select(User).offset(offset).limit(limit)
result = await db.execute(query)
```

#### Eager Loading

```python
from sqlalchemy.orm import joinedload

# Load user with preferences in single query
query = select(User).options(
    joinedload(User.preferences)
).where(User.id == user_id)

user = await db.scalar(query)
```

### Query Performance Analysis

Use `QueryAnalyzer` to identify slow queries:

```python
from app.core.performance import QueryAnalyzer

query = select(User).where(User.email == email)
plan = await QueryAnalyzer.explain_query(db, query)

print(f"Execution time: {plan['execution_time_ms']}ms")
```

## 3. Caching Strategy

### Redis Cache Configuration

**File**: `app/core/cache.py`

```python
# Cache settings
CACHE_ENABLED = True
CACHE_DEFAULT_TTL = 300     # 5 minutes
REDIS_URL = "redis://localhost:6379/0"
```

### Cache TTL Strategy

Different data types have different cache lifetimes:

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| User Profile | 600s (10m) | Updates occasionally |
| Auth Session | 300s (5m) | Security-sensitive |
| User Preferences | 3600s (1h) | Rarely changes |
| List Results | 60s (1m) | Data changes frequently |
| Static/Reference | 86400s (24h) | Never changes |

### Usage Examples

#### Manual Caching

```python
from app.core.cache import cache, CacheStrategy

# Get user from cache or database
cache_key = CacheStrategy.get_user_cache_key(user_id)
user = await cache.get(cache_key)

if user is None:
    # Cache miss - fetch from database
    user = await db.query(User).filter(User.id == user_id).first()
    await cache.set(cache_key, user.dict(), ttl=CacheStrategy.USER_PROFILE_TTL)
```

#### Automatic Caching with Decorator

```python
from app.core.cache import cached, CacheStrategy

@cached(ttl=CacheStrategy.USER_PROFILE_TTL, key_prefix="user:")
async def get_user(user_id: str):
    """Get user with automatic caching."""
    return await db.query(User).filter(User.id == user_id).first()

# First call - fetches from database and caches
user = await get_user("123")

# Second call - returns from cache (much faster)
user = await get_user("123")
```

#### Cache Invalidation

```python
from app.core.cache import invalidate_user_cache

# After updating user profile
user.full_name = "New Name"
await db.commit()

# Invalidate cache
await invalidate_user_cache(user.id)
```

### Cache Performance

**Expected Performance Improvement**:
- Uncached read: 50-100ms
- Cached read: 5-20ms
- **Speedup**: 5-10x faster

## 4. Performance Monitoring

### Request Timing

**File**: `app/core/performance.py`

#### Context Manager

```python
from app.core.performance import async_performance_timer

async def get_user(user_id: str):
    async with async_performance_timer("get_user") as timer:
        user = await db.query(User).filter(User.id == user_id).first()

    print(f"Query took {timer['elapsed_ms']:.2f}ms")
```

#### Decorator

```python
from app.core.performance import monitor_performance

@monitor_performance(threshold_ms=100)
async def create_user(user_data: dict):
    """Automatically logs warning if >100ms."""
    user = User(**user_data)
    db.add(user)
    await db.commit()
    return user
```

### Performance Metrics

```python
from app.core.performance import metrics

# Record query
metrics.record_query(elapsed_ms=45)

# Record cache events
metrics.record_cache_hit()
metrics.record_cache_miss()

# Get summary
summary = metrics.get_summary()
print(f"P95 latency: {summary['p95_ms']}ms")
print(f"Cache hit rate: {summary['cache_hit_rate']}%")
```

### Performance Budgets

```python
from app.core.performance import PerformanceBudget

# Check if operation meets budget
elapsed_ms = 75
is_ok = PerformanceBudget.check_budget("read", elapsed_ms)

if not is_ok:
    logger.warning(f"Read operation exceeded budget: {elapsed_ms}ms")
```

## 5. Best Practices

### DO's

✅ **Use connection pooling** - Reuse database connections
✅ **Cache frequently accessed data** - Reduce database load
✅ **Add indexes on query columns** - Ensure O(log n) lookups
✅ **Use pagination** - Limit result set size
✅ **Eager load relationships** - Avoid N+1 queries
✅ **Monitor query performance** - Identify slow queries early
✅ **Set appropriate cache TTLs** - Balance freshness vs performance
✅ **Invalidate cache on updates** - Ensure data consistency

### DON'Ts

❌ **Don't create connections per request** - Use the pool
❌ **Don't fetch all results** - Always paginate
❌ **Don't perform N+1 queries** - Use eager loading
❌ **Don't cache forever** - Set appropriate TTLs
❌ **Don't ignore slow query warnings** - Investigate and optimize
❌ **Don't skip indexes** - Add indexes for all query columns
❌ **Don't forget to close connections** - Use context managers

## 6. Performance Testing

### Running Performance Tests

```bash
# Run all performance tests
pytest tests/performance/ -v

# Run specific test class
pytest tests/performance/test_crud_performance.py::TestUserCRUDPerformance -v

# Run with performance markers only
pytest -m performance -v

# Generate performance report
pytest tests/performance/ --html=reports/performance.html
```

### Test Coverage

Performance tests cover:

1. **Single Operations**
   - Create user (<100ms)
   - Read user by ID (<50ms)
   - Read user by email (<100ms)
   - Update user (<100ms)
   - Delete user (<100ms)

2. **Bulk Operations**
   - List 20 users (<200ms)
   - Bulk create 100 users (<500ms)

3. **Concurrent Operations**
   - 10 concurrent reads (<500ms total, <100ms average)
   - 5 concurrent creates (<500ms total)

4. **Caching**
   - Cached reads are 5x faster than uncached
   - Cached read <20ms

5. **Index Effectiveness**
   - Email lookup in 1000 users (<100ms)
   - Username lookup in 1000 users (<100ms)

### Test Example

```python
@pytest.mark.performance
async def test_create_user_performance(db_session, user_factory):
    """Test user creation meets <100ms budget."""
    # Arrange
    user_data = {"username": "testuser", "email": "test@example.com"}

    # Act - Measure time
    start = perf_counter()
    user = await user_factory.create(**user_data)
    elapsed_ms = (perf_counter() - start) * 1000

    # Assert
    assert elapsed_ms < 100, f"User creation took {elapsed_ms:.2f}ms"
```

## 7. Troubleshooting

### Slow Queries

If queries exceed 100ms:

1. **Check Indexes**
   ```sql
   -- Verify indexes exist
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'users';
   ```

2. **Analyze Query Plan**
   ```python
   from app.core.performance import QueryAnalyzer
   plan = await QueryAnalyzer.explain_query(db, query)
   # Look for sequential scans instead of index scans
   ```

3. **Check Connection Pool**
   ```python
   from app.core.database import DatabaseHealthCheck
   status = DatabaseHealthCheck.get_pool_status()
   # Ensure pool isn't exhausted
   ```

### Cache Misses

If cache hit rate is low:

1. **Check Redis Connection**
   ```python
   from app.core.cache import cache
   is_healthy = await cache._client.ping()
   ```

2. **Verify TTL Settings**
   ```python
   # Check if TTL is too short
   ttl = await cache._client.ttl("user:123")
   ```

3. **Monitor Cache Patterns**
   ```python
   from app.core.performance import metrics
   summary = metrics.get_summary()
   print(f"Cache hit rate: {summary['cache_hit_rate']}%")
   ```

## 8. Production Deployment

### Environment Variables

```bash
# Database connection pool
export DB_POOL_SIZE=20
export DB_MAX_OVERFLOW=10
export DB_POOL_TIMEOUT=30
export DB_POOL_RECYCLE=3600
export DB_POOL_PRE_PING=true

# Cache settings
export CACHE_ENABLED=true
export CACHE_DEFAULT_TTL=300
export REDIS_URL=redis://production-redis:6379/0

# Performance monitoring
export DB_ECHO_SQL=false  # Disable SQL logging in production
export DB_QUERY_TIMEOUT=10000  # 10 seconds
```

### Monitoring Checklist

- [ ] Set up query performance monitoring
- [ ] Configure slow query logging
- [ ] Monitor connection pool usage
- [ ] Track cache hit rates
- [ ] Set up alerting for >100ms queries
- [ ] Monitor database CPU and memory
- [ ] Monitor Redis memory usage

### Scaling Guidelines

**Connection Pool Sizing**:
- Formula: `pool_size = (num_workers * 2) + overflow`
- For 4 workers: `pool_size=8`, `max_overflow=4`
- For 10 workers: `pool_size=20`, `max_overflow=10`

**Cache Sizing**:
- Average user cache: ~2KB
- For 10,000 active users: ~20MB Redis memory
- For 100,000 active users: ~200MB Redis memory

## Summary

The performance optimizations achieve the <100ms target through:

1. **Connection Pooling**: Eliminates connection overhead (50-100ms saved)
2. **Caching**: 5-10x speedup for frequently accessed data
3. **Indexing**: O(log n) instead of O(n) lookups
4. **Query Optimization**: Efficient pagination and eager loading
5. **Monitoring**: Real-time performance tracking and alerting

All optimizations are validated by comprehensive performance tests that run in CI/CD to prevent performance regressions.

## References

- SQLAlchemy Async Documentation: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Redis Caching Best Practices: https://redis.io/docs/manual/patterns/
- PostgreSQL Performance Tuning: https://www.postgresql.org/docs/current/performance-tips.html
- FastAPI Performance: https://fastapi.tiangolo.com/advanced/performance/
