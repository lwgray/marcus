# Todo Application Architecture Design

## System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  (Web Browser / Mobile App / Third-party Integration)           │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS/REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway / Load Balancer                 │
│                    (NGINX / AWS ALB / CloudFlare)               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Routers    │  │  Middleware  │  │ Dependencies │         │
│  │ (Endpoints)  │  │  (Auth/CORS) │  │   (DI)       │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                 │
│                             │                                     │
│  ┌──────────────────────────▼─────────────────────────┐         │
│  │              Service Layer                         │         │
│  │  (Business Logic / Validation / Orchestration)    │         │
│  └──────────────────────────┬─────────────────────────┘         │
│                             │                                     │
│  ┌──────────────────────────▼─────────────────────────┐         │
│  │         Data Access Layer (SQLAlchemy ORM)        │         │
│  └──────────────────────────┬─────────────────────────┘         │
└─────────────────────────────┼─────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL Database                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Users   │  │  Todos   │  │   Tags   │  │ Todo_Tags│       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Supporting Services                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    Redis     │  │   Logging    │  │  Monitoring  │         │
│  │   (Cache)    │  │  (ELK Stack) │  │ (Prometheus) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. API Layer (FastAPI)

**Responsibilities:**
- HTTP request/response handling
- Input validation via Pydantic
- Authentication/authorization
- Rate limiting
- CORS handling
- Request routing
- Auto-generated API documentation

**Key Components:**

#### Routers
```
app/routers/
├── auth.py         # Authentication endpoints
├── users.py        # User management endpoints
├── todos.py        # Todo CRUD endpoints
├── tags.py         # Tag management endpoints
└── stats.py        # Statistics endpoints
```

#### Middleware Stack
```python
# Order matters - middleware executes in order
1. CORS Middleware (handle cross-origin requests)
2. Rate Limiting Middleware (prevent abuse)
3. Authentication Middleware (verify JWT tokens)
4. Logging Middleware (request/response logging)
5. Error Handling Middleware (standardize errors)
6. Request ID Middleware (tracing)
```

---

### 2. Service Layer

**Responsibilities:**
- Business logic implementation
- Transaction management
- Data validation and transformation
- Cross-cutting concerns
- Orchestration of multiple operations

**Key Services:**

```python
# app/services/auth_service.py
class AuthService:
    """
    Handles authentication and authorization logic
    """
    async def register_user(username, email, password) -> User
    async def authenticate_user(email, password) -> User | None
    async def create_access_token(user_id) -> str
    async def create_refresh_token(user_id) -> str
    async def verify_token(token) -> dict
    async def blacklist_token(token) -> None

# app/services/todo_service.py
class TodoService:
    """
    Manages todo business logic
    """
    async def create_todo(user_id, todo_data) -> Todo
    async def get_user_todos(user_id, filters, pagination) -> List[Todo]
    async def update_todo(user_id, todo_id, updates) -> Todo
    async def delete_todo(user_id, todo_id) -> None
    async def bulk_update_todos(user_id, todo_ids, updates) -> List[Todo]
    async def reorder_todos(user_id, ordered_ids) -> None
    async def calculate_stats(user_id) -> Stats

# app/services/user_service.py
class UserService:
    """
    Manages user operations
    """
    async def get_user_by_id(user_id) -> User
    async def get_user_by_email(email) -> User | None
    async def update_user(user_id, updates) -> User
    async def change_password(user_id, old_pass, new_pass) -> None
    async def deactivate_user(user_id) -> None
```

---

### 3. Data Access Layer

**Responsibilities:**
- Database interactions via SQLAlchemy ORM
- Query optimization
- Connection pooling
- Transaction management
- Database migrations

**Models:**

```python
# app/models/user.py
class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    avatar_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owned_todos = relationship("Todo", back_populates="owner", foreign_keys="Todo.owner_id")
    assigned_todos = relationship("Todo", back_populates="assigned_to", foreign_keys="Todo.assigned_to_id")
    tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")

# app/models/todo.py
class Todo(Base):
    __tablename__ = "todos"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum(TodoStatus), default=TodoStatus.PENDING)
    priority = Column(Enum(TodoPriority), default=TodoPriority.MEDIUM)
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    owner_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to_id = Column(UUID, ForeignKey("users.id", ondelete="SET NULL"))
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="owned_todos", foreign_keys=[owner_id])
    assigned_to = relationship("User", back_populates="assigned_todos", foreign_keys=[assigned_to_id])
    tags = relationship("Tag", secondary="todo_tags", back_populates="todos")

# app/models/tag.py
class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False)
    color = Column(String(7))  # Hex color code
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tags")
    todos = relationship("Todo", secondary="todo_tags", back_populates="tags")

    # Constraints
    __table_args__ = (
        UniqueConstraint('name', 'user_id', name='uq_tag_name_user'),
    )

# app/models/todo_tags.py (Association Table)
todo_tags = Table(
    'todo_tags',
    Base.metadata,
    Column('todo_id', UUID, ForeignKey('todos.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', UUID, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)
```

---

## Database Design

### Entity-Relationship Diagram

```
┌─────────────────────────────────────┐
│              Users                  │
├─────────────────────────────────────┤
│ PK id (UUID)                        │
│ UK email (VARCHAR 255)              │
│ UK username (VARCHAR 50)            │
│    password_hash (VARCHAR 255)      │
│    first_name (VARCHAR 100)         │
│    last_name (VARCHAR 100)          │
│    avatar_url (TEXT)                │
│    is_active (BOOLEAN)              │
│    created_at (TIMESTAMP)           │
│    updated_at (TIMESTAMP)           │
└──────────────┬──────────────────────┘
               │
               │ 1:N (owner)
               │
               ▼
┌─────────────────────────────────────┐
│              Todos                  │
├─────────────────────────────────────┤
│ PK id (UUID)                        │
│    title (VARCHAR 200)              │
│    description (TEXT)               │
│    status (ENUM)                    │
│    priority (ENUM)                  │
│    due_date (TIMESTAMP)             │
│    completed_at (TIMESTAMP)         │
│ FK owner_id (UUID)                  │────┐
│ FK assigned_to_id (UUID)            │    │
│    position (INTEGER)               │    │
│    created_at (TIMESTAMP)           │    │
│    updated_at (TIMESTAMP)           │    │
└──────────────┬──────────────────────┘    │
               │                            │
               │ N:M                        │
               │                            │
               ▼                            │
┌─────────────────────────────────────┐    │
│           Todo_Tags                 │    │
│       (Junction Table)              │    │
├─────────────────────────────────────┤    │
│ PK,FK todo_id (UUID)                │    │
│ PK,FK tag_id (UUID)                 │    │
└──────────────┬──────────────────────┘    │
               │                            │
               │ N:M                        │
               │                            │
               ▼                            │
┌─────────────────────────────────────┐    │
│              Tags                   │    │
├─────────────────────────────────────┤    │
│ PK id (UUID)                        │    │
│    name (VARCHAR 50)                │    │
│    color (VARCHAR 7)                │    │
│ FK user_id (UUID)                   │◄───┘
│    created_at (TIMESTAMP)           │
│ UK (name, user_id)                  │
└─────────────────────────────────────┘
```

### Indexes Strategy

```sql
-- Primary Keys (automatic indexes)
users.id, todos.id, tags.id

-- Unique Constraints (automatic indexes)
users.email, users.username
tags.(name, user_id)

-- Foreign Keys (for join performance)
CREATE INDEX idx_todos_owner_id ON todos(owner_id);
CREATE INDEX idx_todos_assigned_to_id ON todos(assigned_to_id);
CREATE INDEX idx_tags_user_id ON tags(user_id);

-- Query Optimization Indexes
CREATE INDEX idx_todos_status ON todos(status);
CREATE INDEX idx_todos_priority ON todos(priority);
CREATE INDEX idx_todos_due_date ON todos(due_date);
CREATE INDEX idx_todos_created_at ON todos(created_at);

-- Composite Indexes for common queries
CREATE INDEX idx_todos_owner_status ON todos(owner_id, status);
CREATE INDEX idx_todos_owner_priority ON todos(owner_id, priority);
CREATE INDEX idx_todos_owner_created ON todos(owner_id, created_at DESC);

-- Full-text search (for search functionality)
CREATE INDEX idx_todos_title_gin ON todos USING gin(to_tsvector('english', title));
CREATE INDEX idx_todos_description_gin ON todos USING gin(to_tsvector('english', description));
```

---

## Authentication Flow

### Registration Flow
```
Client                  API                 Service              Database
  │                      │                     │                    │
  │  POST /auth/register │                     │                    │
  ├─────────────────────►│                     │                    │
  │                      │ validate input      │                    │
  │                      ├─────────────────────►                    │
  │                      │                     │ check email exists │
  │                      │                     ├───────────────────►│
  │                      │                     │◄───────────────────┤
  │                      │                     │ hash password      │
  │                      │                     │ create user        │
  │                      │                     ├───────────────────►│
  │                      │                     │◄───────────────────┤
  │                      │                     │ generate JWT       │
  │◄─────────────────────┼─────────────────────┤                    │
  │ {user, tokens}       │                     │                    │
```

### Login Flow
```
Client                  API                 Service              Database
  │                      │                     │                    │
  │  POST /auth/login    │                     │                    │
  ├─────────────────────►│                     │                    │
  │                      │ validate input      │                    │
  │                      ├─────────────────────►                    │
  │                      │                     │ get user by email  │
  │                      │                     ├───────────────────►│
  │                      │                     │◄───────────────────┤
  │                      │                     │ verify password    │
  │                      │                     │ generate JWT       │
  │◄─────────────────────┼─────────────────────┤                    │
  │ {user, tokens}       │                     │                    │
```

### Protected Request Flow
```
Client                  Middleware          Service              Database
  │                      │                     │                    │
  │  GET /todos          │                     │                    │
  │  Authorization:      │                     │                    │
  │  Bearer <token>      │                     │                    │
  ├─────────────────────►│                     │                    │
  │                      │ verify JWT          │                    │
  │                      │ extract user_id     │                    │
  │                      │ check blacklist     │                    │
  │                      ├─────────────────────►                    │
  │                      │                     │ get user todos     │
  │                      │                     ├───────────────────►│
  │                      │                     │◄───────────────────┤
  │◄─────────────────────┼─────────────────────┤                    │
  │ {todos}              │                     │                    │
```

---

## Security Architecture

### 1. Authentication Security

**Password Security:**
- Bcrypt hashing with cost factor 12
- Minimum 8 characters
- Never logged or returned in responses
- Password reset via email (future feature)

**JWT Security:**
- HS256 algorithm (or RS256 for distributed systems)
- Short-lived access tokens (1 hour)
- Longer-lived refresh tokens (7 days)
- Token blacklisting on logout
- Tokens include: user_id, exp, iat, jti (unique token ID)

### 2. Authorization Security

**Resource Access Control:**
```python
def verify_todo_access(user_id: UUID, todo: Todo) -> bool:
    """
    User can access todo if they are:
    - The owner
    - Assigned to it
    """
    return todo.owner_id == user_id or todo.assigned_to_id == user_id

def verify_todo_modification(user_id: UUID, todo: Todo) -> bool:
    """
    User can modify todo only if they are the owner
    """
    return todo.owner_id == user_id
```

### 3. Input Validation

**Pydantic Schemas:**
```python
class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: TodoStatus = TodoStatus.PENDING
    priority: TodoPriority = TodoPriority.MEDIUM
    due_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)

    @validator('title')
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

    @validator('due_date')
    def due_date_not_past(cls, v):
        if v and v < datetime.utcnow():
            raise ValueError('Due date cannot be in the past')
        return v
```

### 4. Rate Limiting

**Strategy:**
```python
RATE_LIMITS = {
    "anonymous": "100/hour",
    "authenticated": "1000/hour",
    "burst": "20/minute"
}
```

**Implementation:**
- Token bucket algorithm
- Redis-based for distributed systems
- Per-IP for anonymous requests
- Per-user for authenticated requests
- Different limits per endpoint tier

### 5. CORS Configuration

```python
CORS_CONFIG = {
    "allow_origins": [
        "http://localhost:3000",  # Development
        "https://app.example.com"  # Production
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
    "allow_headers": ["Authorization", "Content-Type"],
    "max_age": 3600  # Preflight cache
}
```

---

## Performance Optimization

### 1. Database Optimization

**Connection Pooling:**
```python
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600
}
```

**Query Optimization:**
- Use eager loading for relationships
- Implement pagination for list endpoints
- Use database-level aggregations
- Add indexes on frequently queried columns

**Example Optimized Query:**
```python
# Bad: N+1 query problem
todos = session.query(Todo).filter_by(owner_id=user_id).all()
for todo in todos:
    print(todo.tags)  # Separate query for each todo

# Good: Eager loading
todos = session.query(Todo)\
    .options(joinedload(Todo.tags))\
    .filter_by(owner_id=user_id)\
    .all()
```

### 2. Caching Strategy

**Redis Cache:**
```python
# User statistics (expensive calculation)
@cache(expire=300)  # 5 minutes
async def get_user_stats(user_id: UUID) -> Stats:
    ...

# User profile (changes infrequently)
@cache(expire=3600)  # 1 hour
async def get_user_profile(user_id: UUID) -> User:
    ...

# Invalidate cache on update
@cache_invalidate("user_stats:{user_id}")
async def update_todo(user_id: UUID, todo_id: UUID, updates):
    ...
```

### 3. Response Optimization

**Selective Field Loading:**
```python
# List endpoint - minimal fields
GET /todos?fields=id,title,status,due_date

# Detail endpoint - all fields
GET /todos/{id}
```

**Compression:**
- Enable gzip compression for responses > 1KB
- Reduces bandwidth by 60-80%

---

## Scalability Considerations

### Horizontal Scaling

**Stateless Design:**
- No server-side sessions
- JWT tokens contain all necessary data
- Any API server can handle any request

**Database Scaling:**
- Read replicas for read-heavy workloads
- Connection pooling
- Sharding by user_id if needed

**Caching Layer:**
- Redis cluster for distributed caching
- Cache invalidation strategies
- Session storage for blacklisted tokens

### Deployment Architecture

```
                    ┌─────────────┐
                    │   CDN       │
                    │ (Static)    │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │Load Balancer│
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                  ▼
    ┌─────────┐      ┌─────────┐       ┌─────────┐
    │ API     │      │ API     │       │ API     │
    │ Server 1│      │ Server 2│       │ Server 3│
    └────┬────┘      └────┬────┘       └────┬────┘
         │                │                   │
         └────────────────┼───────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐   ┌──────────┐
    │PostgreSQL│    │  Redis   │   │  Logger  │
    │ Primary  │    │  Cache   │   │  (ELK)   │
    └─────┬────┘    └──────────┘   └──────────┘
          │
          ▼
    ┌──────────┐
    │PostgreSQL│
    │ Replica  │
    └──────────┘
```

---

## Monitoring and Observability

### Metrics to Track

**Application Metrics:**
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Active users
- Endpoint usage distribution

**Database Metrics:**
- Query execution time
- Connection pool usage
- Slow query log
- Database size growth

**Business Metrics:**
- New user registrations
- Active users (DAU, MAU)
- Todos created/completed
- API usage patterns

### Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@app.get("/health/detailed")
async def detailed_health():
    return {
        "api": "healthy",
        "database": await check_database(),
        "redis": await check_redis(),
        "disk_space": check_disk_space()
    }
```

---

## Development Workflow

### Local Development Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd todo-api

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# 4. Set up environment variables
cp .env.example .env
# Edit .env with local configuration

# 5. Start PostgreSQL (Docker)
docker-compose up -d postgres

# 6. Run database migrations
alembic upgrade head

# 7. Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 8. Access API documentation
# http://localhost:8000/docs
```

### Testing Strategy

```
tests/
├── unit/
│   ├── test_auth_service.py
│   ├── test_todo_service.py
│   └── test_user_service.py
├── integration/
│   ├── test_auth_endpoints.py
│   ├── test_todo_endpoints.py
│   └── test_database.py
└── performance/
    └── test_load.py
```

**Run Tests:**
```bash
# All tests with coverage
pytest --cov=app --cov-report=html

# Unit tests only (fast)
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# Specific test file
pytest tests/unit/test_auth_service.py -v
```

---

## API Versioning Strategy

### Version Management

**URL Versioning:**
- `/api/v1/todos` - Current version
- `/api/v2/todos` - Future version with breaking changes

**Deprecation Process:**
1. Announce deprecation 6 months in advance
2. Add deprecation warning headers
3. Support old version for 6 months minimum
4. Remove old version after transition period

**Example Deprecation Header:**
```
Deprecation: Sun, 01 Apr 2026 00:00:00 GMT
Link: </api/v2/todos>; rel="successor-version"
```

---

## Conclusion

This architecture provides:
- **Scalability**: Stateless design, horizontal scaling
- **Performance**: Caching, query optimization, indexes
- **Security**: JWT auth, input validation, rate limiting
- **Maintainability**: Clean architecture, separation of concerns
- **Observability**: Comprehensive logging and monitoring
- **Developer Experience**: Auto-documentation, type safety
- **Reliability**: Error handling, health checks, graceful degradation

The design follows industry best practices and is production-ready for deployment.
