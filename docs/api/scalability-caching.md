# Scalability & Caching Strategy

## Architecture Overview

### Microservices Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  API Gateway │────▶│ Load Balancer│
└─────────────┘     └─────────────┘     └─────────────┘
                           │                     │
                    ┌──────┴──────┬──────────────┤
                    ▼             ▼              ▼
              ┌─────────┐   ┌─────────┐   ┌─────────┐
              │ API     │   │ API     │   │ API     │
              │ Server  │   │ Server  │   │ Server  │
              └─────────┘   └─────────┘   └─────────┘
                    │             │              │
         ┌──────────┴─────────────┴──────────────┘
         ▼                   ▼                ▼
   ┌─────────┐         ┌─────────┐     ┌─────────┐
   │  Redis  │         │PostgreSQL│     │   S3    │
   │  Cache  │         │ Primary  │     │ Storage │
   └─────────┘         └─────────┘     └─────────┘
                             │
                       ┌─────▼─────┐
                       │PostgreSQL │
                       │ Replica   │
                       └───────────┘
```

## Horizontal Scaling Strategy

### 1. API Servers
- **Auto-scaling**: Based on CPU usage and request rate
- **Target metrics**: 70% CPU, 1000 req/s per instance
- **Scaling policy**: Add 2 instances when threshold reached
- **Cooldown**: 5 minutes between scaling events

### 2. Database Scaling

#### Read Replicas
- **Primary**: Write operations only
- **Read replicas**: 3 replicas for read operations
- **Load distribution**: Round-robin for read queries
- **Replication lag monitoring**: Alert if > 1 second

#### Database Sharding (Future)
```python
# Sharding strategy for user data
def get_shard_key(user_id: str) -> int:
    return hash(user_id) % NUM_SHARDS

# Recipe sharding by creation date
def get_recipe_shard(created_at: datetime) -> str:
    return f"recipes_{created_at.year}_{created_at.month}"
```

### 3. Service Mesh
- **Technology**: Istio or Linkerd
- **Features**: Circuit breaking, retries, load balancing
- **Observability**: Distributed tracing with Jaeger

## Caching Strategy

### 1. Cache Layers

#### CDN Cache (CloudFront/Cloudflare)
- **Content**: Static assets, images, videos
- **TTL**: 30 days for images, 1 year for versioned assets
- **Invalidation**: On recipe image update

#### Application Cache (Redis)
```python
# Cache configuration
CACHE_CONFIG = {
    "recipe_detail": {"ttl": 3600, "pattern": "recipe:{id}"},
    "user_profile": {"ttl": 1800, "pattern": "user:{id}"},
    "search_results": {"ttl": 300, "pattern": "search:{hash}"},
    "trending": {"ttl": 600, "pattern": "trending:{period}"},
    "recommendations": {"ttl": 1800, "pattern": "recommend:{user_id}"}
}
```

#### Database Query Cache
- **Technology**: PostgreSQL query cache
- **Cache size**: 25% of available RAM
- **Eviction**: LRU (Least Recently Used)

### 2. Cache Implementation

#### Cache-Aside Pattern
```python
async def get_recipe(recipe_id: str) -> Recipe:
    # Try cache first
    cache_key = f"recipe:{recipe_id}"
    cached = await redis.get(cache_key)

    if cached:
        return Recipe.parse_raw(cached)

    # Cache miss - fetch from DB
    recipe = await db.fetch_recipe(recipe_id)

    # Update cache
    await redis.setex(
        cache_key,
        CACHE_CONFIG["recipe_detail"]["ttl"],
        recipe.json()
    )

    return recipe
```

#### Cache Invalidation
```python
async def update_recipe(recipe_id: str, data: dict):
    # Update database
    await db.update_recipe(recipe_id, data)

    # Invalidate caches
    await redis.delete(f"recipe:{recipe_id}")
    await redis.delete(f"search:*")  # Pattern delete

    # Publish invalidation event
    await pubsub.publish("cache_invalidation", {
        "type": "recipe",
        "id": recipe_id
    })
```

### 3. Cache Warming
```python
# Scheduled job to warm popular content
async def warm_cache():
    # Top 100 recipes
    popular_recipes = await db.get_popular_recipes(limit=100)
    for recipe in popular_recipes:
        await get_recipe(recipe.id)  # Triggers cache

    # Trending searches
    trending_searches = await analytics.get_trending_searches()
    for search in trending_searches:
        await search_recipes(search.query)
```

## Performance Optimization

### 1. Database Optimization

#### Indexes
```sql
-- Primary indexes
CREATE INDEX idx_recipes_author_created ON recipes(author_id, created_at DESC);
CREATE INDEX idx_recipes_cuisine_rating ON recipes(cuisine, rating DESC);
CREATE INDEX idx_ingredients_name ON ingredients(name);

-- Full-text search
CREATE INDEX idx_recipes_search ON recipes USING GIN(to_tsvector('english', title || ' ' || description));

-- Composite indexes for common queries
CREATE INDEX idx_recipe_ingredients ON recipe_ingredients(recipe_id, ingredient_id);
```

#### Query Optimization
```python
# Use select_related for joined queries
recipes = await Recipe.objects.select_related(
    'author', 'nutrition'
).prefetch_related(
    'ingredients', 'tags'
).filter(cuisine='italian').limit(20)

# Pagination with cursor
async def get_recipes_cursor(cursor: str = None, limit: int = 20):
    query = Recipe.objects.filter(is_public=True)
    if cursor:
        query = query.filter(created_at__lt=cursor)
    return await query.order_by('-created_at').limit(limit)
```

### 2. API Response Optimization

#### Field Selection
```python
# Allow clients to specify fields
GET /recipes?fields=id,title,image_url,rating

# GraphQL-like field selection
{
  "fields": {
    "recipe": ["id", "title", "author.username"],
    "include": ["ingredients", "nutrition"]
  }
}
```

#### Response Compression
- **Gzip**: For JSON responses > 1KB
- **Brotli**: For static assets
- **Image optimization**: WebP format, responsive sizes

### 3. Asynchronous Processing

#### Task Queue (Celery + Redis)
```python
# Async tasks
@celery.task
def generate_recommendations(user_id: str):
    # Heavy computation moved to background
    recommendations = ml_model.predict(user_id)
    cache.set(f"recommend:{user_id}", recommendations)

@celery.task
def update_recipe_stats(recipe_id: str):
    # Update view counts, ratings asynchronously
    stats = calculate_stats(recipe_id)
    db.update_stats(recipe_id, stats)
```

#### Event-Driven Architecture
```python
# Event publishing
async def create_recipe(data: RecipeCreate):
    recipe = await db.create_recipe(data)

    # Publish events
    await events.publish("recipe.created", {
        "recipe_id": recipe.id,
        "author_id": recipe.author_id
    })

    return recipe

# Event consumers
@events.subscribe("recipe.created")
async def on_recipe_created(event):
    await index_recipe_search(event["recipe_id"])
    await notify_followers(event["author_id"])
    await warm_cache(event["recipe_id"])
```

## Load Testing & Capacity Planning

### 1. Performance Targets
- **Response time**: p50 < 100ms, p95 < 500ms, p99 < 1s
- **Throughput**: 10,000 requests/second
- **Concurrent users**: 100,000
- **Availability**: 99.9% uptime

### 2. Load Testing Strategy
```yaml
# k6 load test configuration
scenarios:
  constant_load:
    executor: constant-arrival-rate
    rate: 1000
    timeUnit: 1s
    duration: 30m
    preAllocatedVUs: 100

  spike_test:
    executor: ramping-arrival-rate
    startRate: 100
    timeUnit: 1s
    stages:
      - duration: 5m, target: 1000
      - duration: 10m, target: 5000
      - duration: 5m, target: 100
```

### 3. Monitoring & Alerting

#### Key Metrics
- **Application**: Request rate, error rate, latency
- **Infrastructure**: CPU, memory, disk I/O, network
- **Database**: Query time, connection pool, replication lag
- **Cache**: Hit rate, eviction rate, memory usage

#### Alert Thresholds
```yaml
alerts:
  - name: high_error_rate
    condition: error_rate > 1%
    duration: 5m
    severity: critical

  - name: high_latency
    condition: p95_latency > 1s
    duration: 10m
    severity: warning

  - name: cache_hit_rate_low
    condition: cache_hit_rate < 80%
    duration: 15m
    severity: warning
```

## Disaster Recovery

### 1. Backup Strategy
- **Database**: Daily full backup, hourly incremental
- **Redis**: AOF persistence, snapshots every 5 minutes
- **S3**: Cross-region replication

### 2. Failover Plan
- **Database**: Automatic failover to read replica
- **Redis**: Redis Sentinel for HA
- **API**: Multi-region deployment with Route53

### 3. Recovery Time Objectives
- **RTO**: 15 minutes
- **RPO**: 5 minutes
- **Testing**: Monthly DR drills
