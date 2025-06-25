# PM Agent Scaling Architecture

## Overview

This document outlines the architectural changes required to scale PM Agent from its current single-connection design to support 10, 100, 1000, and 10000+ concurrent connections.

## Current Architecture Analysis

### Limitations
1. **Single-Process STDIO Server**: Current implementation uses MCP's stdio_server which handles one connection at a time
2. **In-Memory State Management**: All state stored in dictionaries, lost on restart
3. **No Connection Pooling**: Each kanban operation spawns new subprocess
4. **Synchronous Operations**: AI analysis blocks other operations
5. **No Horizontal Scaling**: Cannot run multiple instances

### Components Requiring Changes
- `pm_agent_mcp_server_v2.py`: Main server (STDIO-based)
- `PMAgentState`: In-memory state management
- `SimpleMCPKanbanClient`: Creates new connection per operation
- Configuration: JSON-based, no dynamic scaling

## Scaling Tiers

### Tier 1: 10-20 Concurrent Connections

**Architecture Changes:**
```
┌─────────────┐     ┌──────────────┐     ┌─────────┐
│   Agents    │────▶│  HTTP/WS     │────▶│  Redis  │
└─────────────┘     │   Server     │     └─────────┘
                    └──────────────┘
```

**Implementation:**
1. **Replace STDIO with HTTP/WebSocket Server**
   ```python
   # Use FastAPI or aiohttp
   from fastapi import FastAPI, WebSocket
   app = FastAPI()
   
   @app.websocket("/agent/{agent_id}")
   async def agent_connection(websocket: WebSocket, agent_id: str):
       await websocket.accept()
       # Handle agent operations
   ```

2. **Add Redis for State Management**
   ```python
   import redis.asyncio as redis
   
   class RedisStateManager:
       async def set_agent_status(self, agent_id: str, status: dict):
           await self.redis.hset(f"agent:{agent_id}", mapping=status)
   ```

3. **Connection Pooling for Kanban**
   ```python
   class KanbanConnectionPool:
       def __init__(self, pool_size=10):
           self.pool = asyncio.Queue(maxsize=pool_size)
           # Pre-create connections
   ```

### Tier 2: 100 Concurrent Connections

**Architecture Changes:**
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Agents    │────▶│    Nginx     │────▶│  PM Agent   │
└─────────────┘     └──────────────┘     │   Cluster   │
                                          └─────────────┘
                                                 │
                    ┌──────────────┬──────────────┼──────────────┐
                    ▼              ▼              ▼              ▼
              ┌─────────┐    ┌─────────┐   ┌──────────┐   ┌─────────┐
              │  Redis  │    │   PG    │   │  Celery  │   │   AI    │
              └─────────┘    └─────────┘   └──────────┘   │ Workers │
                                                           └─────────┘
```

**Implementation:**
1. **PostgreSQL for Persistent Storage**
   ```python
   # Using SQLAlchemy
   class Agent(Base):
       __tablename__ = 'agents'
       id = Column(String, primary_key=True)
       name = Column(String)
       status = Column(JSON)
       created_at = Column(DateTime)
   ```

2. **Background Task Queue**
   ```python
   from celery import Celery
   
   celery_app = Celery('pm_agent', broker='redis://localhost:6379')
   
   @celery_app.task
   def analyze_project_async(project_id: str):
       # Long-running AI analysis
   ```

3. **Nginx Configuration**
   ```nginx
   upstream pm_agent {
       server pm-agent-1:8000;
       server pm-agent-2:8000;
   }
   ```

### Tier 3: 1000 Concurrent Connections

**Architecture Changes:**
```
                    ┌──────────────┐
                    │Load Balancer │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  ┌───────────┐      ┌───────────┐     ┌───────────┐
  │ PM Agent  │      │ PM Agent  │     │ PM Agent  │
  │ Instance 1│      │ Instance 2│     │ Instance N│
  └───────────┘      └───────────┘     └───────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
    ┌─────────┬────────────┼────────────┬─────────┐
    ▼         ▼            ▼            ▼         ▼
┌────────┐ ┌──────┐ ┌──────────┐ ┌─────────┐ ┌──────┐
│ Redis  │ │  PG  │ │ RabbitMQ │ │ Workers │ │ S3   │
│Cluster │ │ Pool │ └──────────┘ │  Pool   │ │Cache │
└────────┘ └──────┘               └─────────┘ └──────┘
```

**Implementation:**
1. **Kubernetes Deployment**
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: pm-agent
   spec:
     replicas: 10
     template:
       spec:
         containers:
         - name: pm-agent
           image: pm-agent:latest
           env:
           - name: REDIS_CLUSTER
             value: "redis-cluster:6379"
   ```

2. **Message Queue for Task Distribution**
   ```python
   import aio_pika
   
   async def distribute_task(task: dict):
       channel = await connection.channel()
       await channel.default_exchange.publish(
           aio_pika.Message(body=json.dumps(task).encode()),
           routing_key="tasks"
       )
   ```

3. **Service Discovery**
   ```python
   from consul import Consul
   
   consul = Consul()
   consul.agent.service.register(
       name="pm-agent",
       service_id=f"pm-agent-{instance_id}",
       port=8000,
       check=Check.http("http://localhost:8000/health", interval="10s")
   )
   ```

### Tier 4: 10,000+ Concurrent Connections

**Architecture Changes:**
```
                        ┌─────────────────┐
                        │  Global Load    │
                        │   Balancer      │
                        └────────┬────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
   ┌─────────┐             ┌─────────┐             ┌─────────┐
   │Region 1 │             │Region 2 │             │Region N │
   └────┬────┘             └────┬────┘             └────┬────┘
        │                       │                       │
   ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
   │   API   │             │   API   │             │   API   │
   │ Gateway │             │ Gateway │             │ Gateway │
   └────┬────┘             └────┬────┘             └────┬────┘
        │                       │                       │
   ┌────▼─────────────────────────────────────────────▼────┐
   │                    Microservices                       │
   ├──────────┬──────────┬──────────┬──────────┬──────────┤
   │Connection│   Task   │    AI    │  Notify  │  Kanban  │
   │ Service │ Service  │ Service  │ Service  │ Service  │
   └──────────┴──────────┴──────────┴──────────┴──────────┘
                              │
   ┌──────────────────────────┼──────────────────────────┐
   │                    Data Layer                        │
   ├────────┬────────┬────────┬────────┬────────┬───────┤
   │Cassandra│  Kafka │ Redis │  PG   │  S3   │Elastic│
   └────────┴────────┴────────┴────────┴────────┴───────┘
```

**Implementation:**
1. **Microservices Architecture**
   ```python
   # Connection Service
   @app.post("/api/v1/agents/connect")
   async def connect_agent(agent_id: str):
       # Register with service mesh
       # Assign to least loaded instance
   
   # Task Service
   @app.post("/api/v1/tasks/request")
   async def request_task(agent_id: str):
       # Check agent authorization
       # Query task queue
       # Record assignment
   ```

2. **Event-Driven Architecture**
   ```python
   from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
   
   producer = AIOKafkaProducer(bootstrap_servers='kafka:9092')
   
   async def publish_event(event_type: str, data: dict):
       await producer.send(
           f"pm-agent.{event_type}",
           value=json.dumps(data).encode()
       )
   ```

3. **API Gateway with Rate Limiting**
   ```yaml
   # Kong configuration
   services:
   - name: pm-agent-api
     url: http://pm-agent-service
     plugins:
     - name: rate-limiting
       config:
         minute: 1000
         policy: redis
   ```

## Performance Optimizations

### Connection Management
1. **WebSocket Connection Pooling**
   ```python
   class WebSocketManager:
       def __init__(self):
           self.connections: Dict[str, WebSocket] = {}
           self.connection_limit = 1000
       
       async def add_connection(self, agent_id: str, websocket: WebSocket):
           if len(self.connections) >= self.connection_limit:
               raise ConnectionLimitExceeded()
           self.connections[agent_id] = websocket
   ```

2. **Circuit Breaker Pattern**
   ```python
   from pybreaker import CircuitBreaker
   
   kanban_breaker = CircuitBreaker(fail_max=5, reset_timeout=60)
   
   @kanban_breaker
   async def call_kanban_service(operation: str, **kwargs):
       # Protected service call
   ```

### Caching Strategy
1. **Multi-Level Cache**
   ```python
   class CacheManager:
       def __init__(self):
           self.local_cache = TTLCache(maxsize=1000, ttl=60)
           self.redis_cache = redis.Redis()
           self.cdn_cache = CloudFrontCache()
       
       async def get(self, key: str):
           # Check local first
           # Then Redis
           # Then origin
   ```

2. **Cache Warming**
   ```python
   @celery_app.task
   def warm_cache():
       # Pre-load frequently accessed data
       # Refresh before TTL expires
   ```

## Monitoring and Observability

### Metrics Collection
```python
from prometheus_client import Counter, Histogram, Gauge

agent_connections = Gauge('pm_agent_connections', 'Active agent connections')
task_assignments = Counter('pm_agent_task_assignments', 'Total task assignments')
request_duration = Histogram('pm_agent_request_duration', 'Request duration')

@request_duration.time()
async def handle_request(request):
    # Process request
```

### Distributed Tracing
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)

@app.post("/api/v1/tasks")
async def create_task(task: TaskCreate):
    with tracer.start_as_current_span("create_task"):
        # Trace task creation
```

## Migration Strategy

### Phase 1: Foundation (10-20 connections)
1. Implement HTTP/WebSocket server alongside STDIO
2. Add Redis for state management
3. Create connection pooling
4. Test with small agent pool

### Phase 2: Reliability (100 connections)
1. Add PostgreSQL migration scripts
2. Implement Celery workers
3. Deploy behind Nginx
4. Add monitoring

### Phase 3: Scale (1000 connections)
1. Containerize application
2. Deploy to Kubernetes
3. Implement service mesh
4. Add auto-scaling

### Phase 4: Global Scale (10000+ connections)
1. Split into microservices
2. Deploy across regions
3. Implement event streaming
4. Add edge caching

## Testing Strategy

### Load Testing
```python
# Using Locust
from locust import HttpUser, task, between

class PMAgentUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def request_task(self):
        self.client.post("/api/v1/tasks/request", 
                        json={"agent_id": self.agent_id})
```

### Chaos Engineering
```yaml
# Chaos Mesh experiment
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: pm-agent-network-delay
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - pm-agent
  delay:
    latency: "100ms"
    jitter: "10ms"
```

## Cost Considerations

### Resource Requirements by Scale

| Connections | CPU Cores | Memory | Storage | Monthly Cost |
|------------|-----------|---------|---------|--------------|
| 10-20      | 2-4       | 8GB     | 50GB    | ~$100        |
| 100        | 8-16      | 32GB    | 200GB   | ~$500        |
| 1000       | 32-64     | 128GB   | 1TB     | ~$2,500      |
| 10000+     | 200+      | 512GB+  | 10TB+   | ~$15,000+    |

### Optimization Opportunities
1. Spot instances for workers
2. Reserved instances for core services
3. Auto-scaling based on demand
4. Geographic distribution for latency
5. CDN for static content

## Security Considerations

### Authentication & Authorization
```python
from fastapi_jwt_auth import AuthJWT

@app.post("/api/v1/agents/auth")
async def authenticate_agent(credentials: AgentCredentials, 
                           Authorize: AuthJWT = Depends()):
    # Verify credentials
    access_token = Authorize.create_access_token(subject=agent_id)
    return {"access_token": access_token}
```

### Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/tasks/request")
@limiter.limit("100/minute")
async def request_task(request: Request):
    # Handle request
```

### Encryption
- TLS for all connections
- Encrypted data at rest
- Secure key management (Vault)

## Conclusion

Scaling PM Agent requires progressive architectural changes:
1. Start with connection handling improvements
2. Add persistence and caching
3. Implement horizontal scaling
4. Evolve to microservices for massive scale

Each tier builds on the previous, allowing gradual migration based on actual demand.