# Todo Management Application - Technical Specifications

## Technology Stack

### Frontend Technologies

#### Core Framework
- **Framework**: React 18.2+ with TypeScript 5.0+
- **Build Tool**: Vite 5.0+ for fast development and optimized production builds
- **State Management**: Zustand 4.4+ for lightweight state management
- **Routing**: React Router 6.20+ for client-side routing

#### UI/UX Libraries
- **Component Library**: Material-UI (MUI) 5.15+ for consistent design
- **Styling**: Emotion CSS-in-JS for component styling
- **Forms**: React Hook Form 7.48+ with Yup validation
- **Date Handling**: date-fns 3.0+ for date manipulation
- **Icons**: Material Icons and React Icons

#### Development Tools
- **Type Checking**: TypeScript with strict mode
- **Linting**: ESLint 8.50+ with TypeScript plugin
- **Formatting**: Prettier 3.0+ with consistent code style
- **Testing**: Vitest + React Testing Library
- **E2E Testing**: Playwright 1.40+

### Backend Technologies

#### Core Framework
- **Framework**: FastAPI 0.109+ (Python 3.11+)
- **ASGI Server**: Uvicorn 0.25+ with Gunicorn workers
- **Dependency Injection**: FastAPI's built-in DI system

#### Database & ORM
- **Database**: PostgreSQL 15+ for primary data storage
- **ORM**: SQLAlchemy 2.0+ with async support
- **Migrations**: Alembic 1.13+ for database versioning
- **Query Builder**: SQLAlchemy Core for complex queries

#### Caching & Queue
- **Cache**: Redis 7.0+ for session storage and caching
- **Task Queue**: Celery 5.3+ with Redis as broker
- **Rate Limiting**: slowapi with Redis backend

#### Authentication & Security
- **JWT**: python-jose[cryptography] for token generation
- **Password Hashing**: passlib[bcrypt] for secure hashing
- **CORS**: FastAPI CORS middleware
- **Security Headers**: secure-headers middleware

### Infrastructure Technologies

#### Containerization
- **Containers**: Docker 24+ with multi-stage builds
- **Orchestration**: Docker Compose for development
- **Production**: Kubernetes 1.28+ or AWS ECS

#### Cloud Services (AWS)
- **Compute**: ECS Fargate for serverless containers
- **Database**: RDS PostgreSQL with Multi-AZ
- **Cache**: ElastiCache for Redis
- **Storage**: S3 for file attachments
- **CDN**: CloudFront for static assets
- **Load Balancer**: Application Load Balancer

#### Monitoring & Logging
- **APM**: OpenTelemetry with Datadog/New Relic
- **Logging**: Structured JSON logs with CloudWatch
- **Metrics**: Prometheus + Grafana
- **Error Tracking**: Sentry for error monitoring

## Development Environment Setup

### Prerequisites
```yaml
Required Software:
  - Node.js: 20.0+ LTS
  - Python: 3.11+
  - Docker: 24.0+
  - PostgreSQL: 15+ (or Docker)
  - Redis: 7.0+ (or Docker)
  - Git: 2.40+
```

### Local Development Setup

#### 1. Clone Repository
```bash
git clone https://github.com/marcus/todo-app.git
cd todo-app
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

#### 3. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
```

#### 4. Database Setup
```bash
# Using Docker
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Seed data (optional)
python scripts/seed_data.py
```

#### 5. Start Services
```bash
# Terminal 1: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery Worker
celery -A app.worker worker --loglevel=info

# Terminal 3: Frontend (already running)
# http://localhost:3000
```

### Docker Development Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/todos
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: celery -A app.worker worker --loglevel=info
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/todos
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=todos
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## API Implementation Details

### FastAPI Application Structure
```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

app = FastAPI(
    title="Todo Management API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### Database Configuration
```python
# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### Authentication Implementation
```python
# app/core/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

## Deployment Specifications

### Production Build Process

#### Frontend Build
```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Backend Build
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Build and push Docker images
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY

          docker build -t $ECR_REGISTRY/todo-frontend:$GITHUB_SHA ./frontend
          docker build -t $ECR_REGISTRY/todo-backend:$GITHUB_SHA ./backend

          docker push $ECR_REGISTRY/todo-frontend:$GITHUB_SHA
          docker push $ECR_REGISTRY/todo-backend:$GITHUB_SHA

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster todo-cluster \
            --service todo-frontend \
            --force-new-deployment

          aws ecs update-service \
            --cluster todo-cluster \
            --service todo-backend \
            --force-new-deployment
```

### Infrastructure as Code (Terraform)

```hcl
# infrastructure/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# VPC Configuration
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "todo-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = true
}

# RDS PostgreSQL
resource "aws_db_instance" "postgres" {
  identifier = "todo-db"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"

  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_encrypted     = true

  db_name  = "todos"
  username = "postgres"
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.postgres.name

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  deletion_protection = true
  skip_final_snapshot = false
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "todo-cache"
  engine              = "redis"
  node_type           = "cache.t3.micro"
  num_cache_nodes     = 1
  parameter_group_name = "default.redis7"
  port                = 6379

  subnet_group_name = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "todo-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "todo-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = module.vpc.public_subnets
}
```

## Performance Optimization

### Frontend Optimizations

#### Code Splitting
```typescript
// Lazy load routes
const TodoList = lazy(() => import('./pages/TodoList'));
const TodoDetail = lazy(() => import('./pages/TodoDetail'));
const Settings = lazy(() => import('./pages/Settings'));

// Route configuration
<Suspense fallback={<LoadingSpinner />}>
  <Routes>
    <Route path="/" element={<TodoList />} />
    <Route path="/todo/:id" element={<TodoDetail />} />
    <Route path="/settings" element={<Settings />} />
  </Routes>
</Suspense>
```

#### Virtual Scrolling
```typescript
// Use react-window for large lists
import { FixedSizeList } from 'react-window';

const TodoVirtualList = ({ todos }: { todos: Todo[] }) => {
  const Row = ({ index, style }) => (
    <div style={style}>
      <TodoItem todo={todos[index]} />
    </div>
  );

  return (
    <FixedSizeList
      height={600}
      itemCount={todos.length}
      itemSize={80}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
};
```

### Backend Optimizations

#### Database Query Optimization
```python
# Use select_related and prefetch_related
async def get_todos_optimized(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20
) -> List[Todo]:
    query = (
        select(Todo)
        .options(
            selectinload(Todo.categories),
            selectinload(Todo.comments),
            selectinload(Todo.attachments)
        )
        .where(Todo.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()
```

#### Redis Caching
```python
# Cache decorator
from functools import wraps
import json
from app.core.redis import redis_client

def cache_result(expiration: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await redis_client.setex(
                cache_key,
                expiration,
                json.dumps(result, default=str)
            )
            return result
        return wrapper
    return decorator
```

## Security Implementation

### Input Validation
```python
# Strict input validation with Pydantic
from pydantic import BaseModel, validator, constr
import bleach

class TodoCreateSchema(BaseModel):
    title: constr(min_length=1, max_length=500, strip_whitespace=True)
    description: Optional[str] = None
    priority: TodoPriority
    due_date: Optional[datetime] = None

    @validator('description')
    def sanitize_description(cls, v):
        if v:
            # Remove dangerous HTML
            return bleach.clean(v, tags=[], strip=True)
        return v

    @validator('due_date')
    def validate_future_date(cls, v):
        if v and v < datetime.utcnow():
            raise ValueError('Due date must be in the future')
        return v
```

### Rate Limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/todos")
@limiter.limit("10/minute")
async def create_todo(
    todo: TodoCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Implementation
    pass
```

## Testing Strategy

### Unit Testing
```python
# tests/unit/test_todo_service.py
import pytest
from app.services.todo import TodoService
from app.schemas.todo import TodoCreate

@pytest.mark.asyncio
async def test_create_todo(db_session, test_user):
    todo_service = TodoService(db_session)
    todo_data = TodoCreate(
        title="Test Todo",
        description="Test Description",
        priority="high"
    )

    todo = await todo_service.create(test_user.id, todo_data)

    assert todo.title == "Test Todo"
    assert todo.user_id == test_user.id
    assert todo.status == "pending"
```

### Integration Testing
```python
# tests/integration/test_api_todos.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_todo_workflow(async_client: AsyncClient, auth_headers):
    # Create todo
    response = await async_client.post(
        "/api/v1/todos",
        json={
            "title": "Integration Test Todo",
            "priority": "medium"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    todo_id = response.json()["data"]["id"]

    # Update todo
    response = await async_client.patch(
        f"/api/v1/todos/{todo_id}",
        json={"status": "in_progress"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "in_progress"
```

## Monitoring and Observability

### Application Metrics
```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
todo_created_total = Counter(
    'todo_created_total',
    'Total number of todos created',
    ['user_id', 'priority']
)

todo_operation_duration = Histogram(
    'todo_operation_duration_seconds',
    'Time spent processing todo operations',
    ['operation']
)

active_todos_gauge = Gauge(
    'active_todos_total',
    'Current number of active todos',
    ['status']
)

# Usage in service
@todo_operation_duration.labels(operation='create').time()
async def create_todo(self, user_id: UUID, todo_data: TodoCreate):
    todo = await self._create_todo_in_db(user_id, todo_data)
    todo_created_total.labels(
        user_id=str(user_id),
        priority=todo.priority
    ).inc()
    return todo
```

### Structured Logging
```python
# app/core/logging.py
import structlog
from structlog.processors import JSONRenderer

structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage
logger.info(
    "todo_created",
    user_id=user_id,
    todo_id=todo.id,
    priority=todo.priority,
    has_due_date=bool(todo.due_date)
)
```

## Marcus Integration Configuration

### MCP Client Setup
```python
# app/integrations/marcus.py
from src.mcp.client import MCPClient
from app.core.config import settings

class MarcusIntegration:
    def __init__(self):
        self.client = MCPClient(
            server_url=settings.MARCUS_MCP_URL,
            api_key=settings.MARCUS_API_KEY
        )

    async def create_task_from_todo(
        self,
        todo: Todo,
        project_id: str
    ) -> str:
        """Convert todo to Marcus task"""
        task_data = {
            "name": todo.title,
            "description": todo.description or "",
            "priority": self._map_priority(todo.priority),
            "due_date": todo.due_date.isoformat() if todo.due_date else None,
            "labels": todo.tags,
            "metadata": {
                "source": "todo_app",
                "todo_id": str(todo.id)
            }
        }

        response = await self.client.call_tool(
            "create_task",
            project_id=project_id,
            task_data=task_data
        )

        return response["task_id"]

    def _map_priority(self, todo_priority: str) -> str:
        """Map todo priority to Marcus priority"""
        mapping = {
            "urgent": "high",
            "high": "medium",
            "medium": "low",
            "low": "low"
        }
        return mapping.get(todo_priority, "medium")
```

This technical specification provides a comprehensive guide for implementing the Todo Management application with all necessary technologies, configurations, and best practices for a production-ready system integrated with Marcus.
