# Performance Requirements Implementation Guide

## Overview

This document defines the performance requirements and implementation strategies for the Time project to ensure the application can handle a large number of users and tasks simultaneously without performance degradation.

**Status**: Requirements defined, awaiting implementation

## Performance Goals

### Response Time Targets

| Operation Type | Target Response Time | Maximum Acceptable |
|---------------|---------------------|-------------------|
| Task Creation | < 100ms | 200ms |
| Task List (< 100 items) | < 50ms | 100ms |
| Task Update | < 100ms | 200ms |
| Time Tracking Start/Stop | < 50ms | 100ms |
| Calendar Sync | < 500ms | 1000ms |
| Database Queries | < 50ms | 100ms |
| API Health Check | < 10ms | 50ms |

### Throughput Targets

- **Concurrent Users**: Support 1,000+ simultaneous active users
- **Requests per Second**: Handle 500+ requests/second
- **Database Connections**: Efficiently manage connection pool
- **API Endpoint Capacity**:
  - Task CRUD: 200 req/sec
  - Time tracking: 150 req/sec
  - Calendar operations: 100 req/sec

### Resource Utilization

- **CPU Usage**: < 70% average under normal load
- **Memory Usage**: < 2GB per application instance
- **Database Connections**: < 50 per instance (pooled)
- **Network Bandwidth**: < 10MB/sec per instance

## Implementation Strategies

### 1. Database Optimization

#### Connection Pooling

```python
# config/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,              # Base pool size
    max_overflow=30,           # Extra connections when pool exhausted
    pool_timeout=30,           # Wait time for connection
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Verify connections before use
    echo=False                 # Disable SQL logging in production
)

# Connection pool monitoring
def get_pool_stats():
    return {
        "size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow()
    }
```

#### Query Optimization

```python
# models/task.py - Optimized queries

# BAD: N+1 Query Problem
tasks = session.query(Task).all()
for task in tasks:
    print(task.project.name)  # Each access hits database

# GOOD: Eager Loading
from sqlalchemy.orm import joinedload

tasks = session.query(Task)\
    .options(joinedload(Task.project))\
    .options(joinedload(Task.assigned_to))\
    .all()

# BETTER: Select specific columns
from sqlalchemy.orm import load_only

tasks = session.query(Task)\
    .options(load_only(Task.id, Task.title, Task.status))\
    .all()

# BEST: Use indexes
class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), index=True)
    assigned_to = Column(Integer, ForeignKey('users.id'), index=True)
    status = Column(String, index=True)  # Frequently filtered
    created_at = Column(DateTime, index=True)  # Frequently sorted
```

#### Database Indexing Strategy

```sql
-- Primary indexes (automatically created)
CREATE INDEX idx_tasks_id ON tasks(id);
CREATE INDEX idx_projects_id ON projects(id);
CREATE INDEX idx_users_id ON users(id);

-- Foreign key indexes
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX idx_time_entries_task_id ON time_entries(task_id);

-- Query optimization indexes
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);

-- Composite indexes for common queries
CREATE INDEX idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX idx_tasks_assigned_status ON tasks(assigned_to, status);
CREATE INDEX idx_time_entries_user_date ON time_entries(user_id, date);

-- Full-text search indexes
CREATE INDEX idx_tasks_title_search ON tasks USING gin(to_tsvector('english', title));
CREATE INDEX idx_tasks_description_search ON tasks USING gin(to_tsvector('english', description));

-- Analyze tables after index creation
ANALYZE tasks;
ANALYZE projects;
ANALYZE time_entries;
```

#### Pagination for Large Result Sets

```python
# api/routes/tasks.py

@router.get("/tasks")
async def list_tasks(
    skip: int = 0,
    limit: int = 50,  # Default page size
    max_limit: int = 100,  # Maximum allowed
    db: Session = Depends(get_db)
):
    # Validate pagination parameters
    limit = min(limit, max_limit)

    # Count total (cached)
    total = db.query(Task).count()

    # Fetch page with offset
    tasks = db.query(Task)\
        .order_by(Task.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

    return {
        "items": tasks,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total
    }
```

### 2. Caching Strategy

#### Redis Cache Implementation

```python
# config/cache.py
import redis
from functools import wraps
import json
import hashlib

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    max_connections=50
)

def cache_result(ttl=300):
    """Cache function results with TTL in seconds"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = f"{func.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Execute function and cache result
            result = await func(*args, **kwargs)
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )
            return result
        return wrapper
    return decorator

# Usage example
@cache_result(ttl=600)  # Cache for 10 minutes
async def get_project_stats(project_id: int):
    return db.query(Task)\
        .filter(Task.project_id == project_id)\
        .group_by(Task.status)\
        .all()
```

#### Cache Invalidation Strategy

```python
# utils/cache_invalidation.py

class CacheManager:
    """Manage cache invalidation patterns"""

    @staticmethod
    def invalidate_task_cache(task_id: int):
        """Invalidate all caches related to a task"""
        patterns = [
            f"task:{task_id}:*",
            f"project:*:tasks",
            f"user:*:assigned_tasks"
        ]
        for pattern in patterns:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)

    @staticmethod
    def invalidate_project_cache(project_id: int):
        """Invalidate all caches related to a project"""
        patterns = [
            f"project:{project_id}:*",
            f"project_list:*"
        ]
        for pattern in patterns:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)

# Usage in API routes
@router.put("/tasks/{task_id}")
async def update_task(task_id: int, task_data: TaskUpdate):
    # Update task
    task = update_task_in_db(task_id, task_data)

    # Invalidate related caches
    CacheManager.invalidate_task_cache(task_id)

    return task
```

### 3. Asynchronous Processing

#### Background Task Queue

```python
# config/celery_app.py
from celery import Celery

celery_app = Celery(
    'time_app',
    broker='redis://localhost:6379/1',
    backend='redis://localhost:6379/2'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000
)

# tasks/calendar_sync.py
@celery_app.task(bind=True, max_retries=3)
def sync_calendar_events(self, user_id: int):
    """Background task for calendar synchronization"""
    try:
        # Perform expensive calendar sync
        sync_user_calendar(user_id)
        return {"status": "success", "user_id": user_id}
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

# API endpoint triggers background task
@router.post("/calendar/sync")
async def trigger_calendar_sync(user_id: int):
    task = sync_calendar_events.delay(user_id)
    return {
        "task_id": task.id,
        "status": "processing"
    }
```

### 4. API Performance Optimizations

#### Response Compression

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()

# Enable GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

#### Request Rate Limiting

```python
# middleware/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply rate limits to endpoints
@router.post("/tasks")
@limiter.limit("100/minute")  # 100 requests per minute per IP
async def create_task(request: Request, task_data: TaskCreate):
    return create_new_task(task_data)

@router.get("/tasks")
@limiter.limit("200/minute")  # Higher limit for reads
async def list_tasks(request: Request):
    return get_all_tasks()
```

#### HTTP Caching Headers

```python
# api/routes/tasks.py
from fastapi import Response
from datetime import datetime, timedelta

@router.get("/tasks/{task_id}")
async def get_task(task_id: int, response: Response):
    task = fetch_task(task_id)

    # Set cache headers
    response.headers["Cache-Control"] = "private, max-age=60"
    response.headers["ETag"] = f'"{task.updated_at.timestamp()}"'
    response.headers["Last-Modified"] = task.updated_at.strftime('%a, %d %b %Y %H:%M:%S GMT')

    return task
```

### 5. Load Balancing & Scalability

#### Horizontal Scaling Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app1
      - app2
      - app3

  app1:
    build: .
    environment:
      - WORKER_ID=1
      - DATABASE_URL=postgresql://user:pass@db:5432/time_app
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  app2:
    build: .
    environment:
      - WORKER_ID=2
      - DATABASE_URL=postgresql://user:pass@db:5432/time_app
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  app3:
    build: .
    environment:
      - WORKER_ID=3
      - DATABASE_URL=postgresql://user:pass@db:5432/time_app
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=time_app
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

volumes:
  postgres_data:
```

#### Nginx Load Balancer Configuration

```nginx
# nginx.conf
upstream time_app {
    least_conn;  # Route to server with least connections

    server app1:8000 max_fails=3 fail_timeout=30s;
    server app2:8000 max_fails=3 fail_timeout=30s;
    server app3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;

    location / {
        proxy_pass http://time_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Connection pooling
        proxy_http_version 1.1;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 30s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Static file caching
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Performance Testing

### Load Testing with Locust

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random

class TimeAppUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login before starting tasks"""
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)  # Weight: 3x more likely than other tasks
    def list_tasks(self):
        self.client.get("/api/tasks", headers=self.headers)

    @task(2)
    def get_task(self):
        task_id = random.randint(1, 1000)
        self.client.get(f"/api/tasks/{task_id}", headers=self.headers)

    @task(1)
    def create_task(self):
        self.client.post("/api/tasks",
            headers=self.headers,
            json={
                "title": "Performance Test Task",
                "description": "Testing load",
                "priority": "medium"
            })

    @task(1)
    def start_time_tracking(self):
        task_id = random.randint(1, 1000)
        self.client.post(f"/api/tasks/{task_id}/time/start",
            headers=self.headers)
```

Run load tests:
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --users 1000 \
    --spawn-rate 50 \
    --run-time 10m \
    --html=load_test_report.html

# View results in browser
# Open http://localhost:8089
```

### Database Performance Testing

```python
# tests/performance/test_database_performance.py
import pytest
import time
from sqlalchemy import text

def test_query_performance(db_session):
    """Ensure queries meet performance targets"""

    # Test 1: Simple query < 50ms
    start = time.time()
    result = db_session.query(Task).filter(Task.status == 'open').all()
    duration = (time.time() - start) * 1000
    assert duration < 50, f"Query took {duration}ms, expected < 50ms"

    # Test 2: Join query < 100ms
    start = time.time()
    result = db_session.query(Task)\
        .join(Project)\
        .filter(Project.owner_id == 1)\
        .all()
    duration = (time.time() - start) * 1000
    assert duration < 100, f"Join query took {duration}ms, expected < 100ms"

    # Test 3: Paginated query < 50ms
    start = time.time()
    result = db_session.query(Task)\
        .order_by(Task.created_at.desc())\
        .limit(50)\
        .all()
    duration = (time.time() - start) * 1000
    assert duration < 50, f"Paginated query took {duration}ms, expected < 50ms"

def test_connection_pool_efficiency(engine):
    """Verify connection pool is properly configured"""
    pool = engine.pool

    # Check pool size
    assert pool.size() >= 20, "Pool size should be at least 20"

    # Test concurrent connections
    connections = []
    for _ in range(30):
        conn = engine.connect()
        connections.append(conn)

    # Verify overflow handling
    assert pool.overflow() <= 30, "Overflow connections should be limited"

    # Clean up
    for conn in connections:
        conn.close()
```

### API Endpoint Performance Testing

```python
# tests/performance/test_api_performance.py
import pytest
from fastapi.testclient import TestClient

def test_task_creation_performance(client: TestClient, auth_token):
    """Ensure task creation < 100ms"""
    import time

    start = time.time()
    response = client.post("/api/tasks",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "title": "Test Task",
            "description": "Performance test",
            "priority": "medium"
        })
    duration = (time.time() - start) * 1000

    assert response.status_code == 201
    assert duration < 100, f"Task creation took {duration}ms, expected < 100ms"

def test_task_list_performance(client: TestClient, auth_token):
    """Ensure task listing < 50ms"""
    import time

    start = time.time()
    response = client.get("/api/tasks?limit=50",
        headers={"Authorization": f"Bearer {auth_token}"})
    duration = (time.time() - start) * 1000

    assert response.status_code == 200
    assert duration < 50, f"Task listing took {duration}ms, expected < 50ms"
```

## Monitoring & Metrics

### Performance Monitoring Setup

```python
# middleware/performance_monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
active_connections = Gauge('active_database_connections', 'Active database connections')
cache_hit_rate = Counter('cache_hits_total', 'Cache hits', ['cache_type'])

@app.middleware("http")
async def performance_monitoring_middleware(request: Request, call_next):
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    # Add performance headers
    response.headers["X-Response-Time"] = f"{duration*1000:.2f}ms"

    return response

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")
```

### Database Query Logging

```python
# config/database.py
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Log slow queries
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.1:  # Log queries > 100ms
        logging.warning(f"Slow query ({total*1000:.2f}ms): {statement}")
```

## Performance Checklist

### Pre-Deployment Checklist

- [ ] Database indexes created for all foreign keys
- [ ] Composite indexes created for common query patterns
- [ ] Connection pooling configured (size: 20, overflow: 30)
- [ ] Redis caching implemented for expensive operations
- [ ] Cache invalidation strategy in place
- [ ] Query pagination implemented for large result sets
- [ ] Eager loading used to prevent N+1 queries
- [ ] Background jobs configured for long-running tasks
- [ ] Rate limiting enabled on all API endpoints
- [ ] Response compression (GZip) enabled
- [ ] Static file caching configured
- [ ] Load balancer configured (if multiple instances)
- [ ] Monitoring and metrics collection enabled
- [ ] Slow query logging enabled
- [ ] Load testing performed and passed
- [ ] Performance regression tests added to CI/CD

### Ongoing Monitoring

- [ ] Monitor response times daily
- [ ] Review slow query logs weekly
- [ ] Check cache hit rates weekly
- [ ] Monitor connection pool utilization
- [ ] Review error rates and timeouts
- [ ] Analyze traffic patterns for optimization opportunities
- [ ] Perform monthly load testing
- [ ] Update indexes based on query patterns

## Expected Performance Results

After implementing these strategies, the application should achieve:

- **99th percentile response time**: < 200ms for all CRUD operations
- **Average response time**: < 50ms for read operations
- **Throughput**: 500+ requests/second
- **Concurrent users**: 1,000+ without degradation
- **Database query time**: < 50ms average
- **Cache hit rate**: > 80% for frequently accessed data
- **Error rate**: < 0.1% under normal load
- **CPU utilization**: < 60% under normal load
- **Memory usage**: < 1.5GB per instance

## Next Steps

1. **Implement Core Optimizations** (Week 1-2)
   - Database connection pooling
   - Query optimization and indexing
   - Basic caching layer

2. **Add Monitoring** (Week 2)
   - Prometheus metrics
   - Query performance logging
   - Response time tracking

3. **Performance Testing** (Week 3)
   - Write load tests
   - Execute baseline tests
   - Identify bottlenecks

4. **Advanced Optimizations** (Week 4+)
   - Implement background job processing
   - Add Redis caching
   - Configure load balancing
   - Fine-tune based on metrics

5. **Continuous Improvement**
   - Monitor production metrics
   - Optimize based on real usage patterns
   - Regular performance regression testing
   - Update indexes as query patterns evolve

---

**Document Version**: 1.0
**Last Updated**: 2025-10-06
**Status**: Requirements defined - awaiting implementation
**Owner**: Time Agent 2
