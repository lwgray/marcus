# PM Agent Scaling Guide

This guide provides step-by-step instructions for scaling PM Agent from a single-connection system to handling thousands of concurrent agents.

## Quick Start

### Running Scaled Version Locally

1. **Install scaling dependencies:**
   ```bash
   pip install -r requirements-scaling.txt
   ```

2. **Start infrastructure with Docker Compose:**
   ```bash
   cd deployment/docker
   docker-compose up -d
   ```

3. **Run the scaled server:**
   ```bash
   python -m pm_agent.server.scaled_server
   ```

4. **Test with benchmark:**
   ```bash
   python tests/performance/benchmark_scaling.py --agents 10 --duration 60
   ```

## Scaling Tiers

### Tier 1: 10-20 Agents (Development)

**Changes Required:**
- Replace STDIO server with HTTP/WebSocket server
- Add Redis for state caching
- Implement connection pooling

**Quick Implementation:**
```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Set environment variables
export REDIS_URL=redis://localhost:6379

# Run scaled server
python -m pm_agent.server.scaled_server
```

### Tier 2: 100 Agents (Small Team)

**Additional Requirements:**
- PostgreSQL for persistence
- Nginx for load balancing
- Background task processing

**Docker Compose Setup:**
```bash
cd deployment/docker
docker-compose up -d

# View logs
docker-compose logs -f pm-agent

# Access monitoring
# Grafana: http://localhost:3000 (admin/admin)
# pgAdmin: http://localhost:8082
```

### Tier 3: 1000 Agents (Enterprise)

**Kubernetes Deployment:**
```bash
# Create namespace and deploy
kubectl apply -f deployment/kubernetes/pm-agent-deployment.yaml

# Check status
kubectl get pods -n pm-agent

# Scale up
kubectl scale deployment pm-agent-server --replicas=10 -n pm-agent
```

### Tier 4: 10,000+ Agents (Cloud Scale)

**Multi-Region Setup:**
- Deploy to multiple cloud regions
- Use managed services (RDS, ElastiCache, EKS)
- Implement global load balancing

## Configuration

### Environment Variables

```bash
# Server Configuration
export PM_AGENT_HOST=0.0.0.0
export PM_AGENT_PORT=8000
export PM_AGENT_WORKERS=4

# Redis Configuration
export REDIS_URL=redis://localhost:6379
export REDIS_POOL_SIZE=10

# Database Configuration
export DATABASE_URL=postgresql://user:pass@localhost/pmagent
export DB_POOL_SIZE=20

# Performance Tuning
export MAX_CONNECTIONS=1000
export CONNECTION_TIMEOUT=60
export TASK_QUEUE_SIZE=10000
```

### Configuration File

Create `config/scaling.json`:
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 4,
    "max_connections": 1000
  },
  "redis": {
    "url": "redis://localhost:6379",
    "pool_size": 10,
    "ttl": 300
  },
  "database": {
    "url": "postgresql://localhost/pmagent",
    "pool_size": 20
  },
  "performance": {
    "connection_pool_size": 100,
    "task_batch_size": 50,
    "cache_ttl": 300
  }
}
```

## Monitoring

### Metrics Endpoints

- Health Check: `http://localhost:8000/health`
- Prometheus Metrics: `http://localhost:8000/metrics`
- Connection Stats: `http://localhost:8000/api/v1/stats`

### Key Metrics to Monitor

1. **Connection Metrics:**
   - `pm_agent_active_connections` - Current active connections
   - `pm_agent_connection_errors` - Connection failures
   - `pm_agent_connection_duration` - Connection lifespan

2. **Performance Metrics:**
   - `pm_agent_request_duration` - Request latency
   - `pm_agent_requests_per_second` - Throughput
   - `pm_agent_task_queue_size` - Pending tasks

3. **Resource Metrics:**
   - CPU utilization
   - Memory usage
   - Database connection pool status
   - Redis memory usage

### Grafana Dashboards

Import the provided dashboards:
```bash
# Copy dashboard files
cp deployment/docker/grafana-dashboards/*.json /path/to/grafana/dashboards/

# Or import via UI
# Dashboard IDs: 15000 (Overview), 15001 (Connections), 15002 (Performance)
```

## Performance Tuning

### Connection Optimization

1. **Enable Connection Pooling:**
   ```python
   # In your client code
   from pm_agent.client import PooledClient
   
   client = PooledClient(
       server_url="http://localhost:8000",
       pool_size=10,
       max_overflow=20
   )
   ```

2. **Use WebSockets for Long-Running Agents:**
   ```python
   # WebSocket client example
   import websockets
   
   async with websockets.connect("ws://localhost:8000/ws/agent/123") as ws:
       await ws.send(json.dumps({"type": "register"}))
       # Keep connection alive
   ```

### Database Optimization

1. **Create Indexes:**
   ```sql
   CREATE INDEX idx_agent_heartbeat ON agents(last_heartbeat);
   CREATE INDEX idx_task_priority ON tasks(priority, status);
   CREATE INDEX idx_task_assignment ON tasks(assigned_agent_id, status);
   ```

2. **Enable Query Caching:**
   ```python
   # Redis caching for frequent queries
   @cache(ttl=60)
   async def get_pending_tasks():
       return await db.query("SELECT * FROM tasks WHERE status='pending'")
   ```

### Redis Optimization

1. **Configure Memory Policy:**
   ```redis
   CONFIG SET maxmemory 2gb
   CONFIG SET maxmemory-policy allkeys-lru
   ```

2. **Use Pipeline for Batch Operations:**
   ```python
   async with redis.pipeline() as pipe:
       for agent_id in agent_ids:
           pipe.hget(f"agent:{agent_id}", "status")
       results = await pipe.execute()
   ```

## Troubleshooting

### Common Issues

1. **Connection Limit Reached:**
   ```bash
   # Check current connections
   curl http://localhost:8000/api/v1/stats | jq .connections
   
   # Increase limit
   export MAX_CONNECTIONS=2000
   ```

2. **High Memory Usage:**
   ```bash
   # Check memory stats
   docker stats pm-agent-server
   
   # Adjust cache TTL
   export CACHE_TTL=60  # Reduce from default 300
   ```

3. **Slow Response Times:**
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   
   # Check slow queries
   docker logs postgres | grep "duration:"
   ```

### Performance Debugging

1. **Run Benchmark:**
   ```bash
   python tests/performance/benchmark_scaling.py \
     --server http://localhost:8000 \
     --agents 100 \
     --duration 300
   ```

2. **Analyze Results:**
   ```bash
   # View benchmark report
   cat benchmark_results.json | jq .
   
   # Check for bottlenecks
   grep "p95" benchmark_results.json
   ```

3. **Profile Server:**
   ```bash
   # CPU profiling
   py-spy record -o profile.svg -- python -m pm_agent.server.scaled_server
   
   # Memory profiling
   memray run pm_agent.server.scaled_server
   ```

## Migration Guide

### From STDIO to HTTP/WebSocket

1. **Update Agent Code:**
   ```python
   # Old (STDIO)
   from pm_agent.client import StdioClient
   client = StdioClient()
   
   # New (HTTP)
   from pm_agent.client import HTTPClient
   client = HTTPClient("http://localhost:8000")
   ```

2. **Update Configuration:**
   ```json
   {
     "server_type": "http",
     "endpoint": "http://localhost:8000"
   }
   ```

### Database Migration

1. **Export Current State:**
   ```bash
   python -m pm_agent.tools.export_state > state_backup.json
   ```

2. **Initialize Database:**
   ```bash
   alembic upgrade head
   ```

3. **Import State:**
   ```bash
   python -m pm_agent.tools.import_state < state_backup.json
   ```

## Best Practices

1. **Use Connection Pooling:** Reuse connections instead of creating new ones
2. **Implement Retry Logic:** Handle transient failures gracefully
3. **Monitor Resource Usage:** Set up alerts for high CPU/memory
4. **Regular Maintenance:** Clean up old data, update indexes
5. **Test at Scale:** Run load tests before production deployment

## Security Considerations

1. **Enable TLS:**
   ```nginx
   server {
       listen 443 ssl;
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
   }
   ```

2. **Implement Rate Limiting:**
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/api/v1/tasks/request")
   @limiter.limit("100/minute")
   async def request_task():
       pass
   ```

3. **Add Authentication:**
   ```python
   from fastapi.security import HTTPBearer
   security = HTTPBearer()
   
   @app.post("/api/v1/agents/register")
   async def register(token: HTTPAuthorizationCredentials = Depends(security)):
       # Verify token
       pass
   ```

## Conclusion

PM Agent can scale from a simple development tool to an enterprise-grade system handling thousands of concurrent agents. Start with the appropriate tier for your needs and scale up as demand grows. Regular monitoring and performance testing ensure smooth operation at any scale.