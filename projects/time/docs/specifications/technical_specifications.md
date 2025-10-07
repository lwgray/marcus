# Technical Specifications - Time Tracking Platform

## Document Overview

This document provides detailed technical specifications for implementing the Time Tracking and Data Analytics Platform, including database schemas, business logic, security requirements, and integration specifications.

## Table of Contents
1. [Database Schema](#database-schema)
2. [Data Models](#data-models)
3. [Business Logic](#business-logic)
4. [Security Specifications](#security-specifications)
5. [Performance Requirements](#performance-requirements)
6. [Integration Specifications](#integration-specifications)
7. [Error Handling](#error-handling)
8. [Testing Requirements](#testing-requirements)

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐
│     Users       │
│─────────────────│
│ id (PK)         │
│ email           │
│ password_hash   │
│ full_name       │
│ created_at      │
│ updated_at      │
│ is_active       │
│ last_login      │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────┴────────────────┐
│       Tasks             │
│─────────────────────────│
│ id (PK)                 │
│ user_id (FK)            │
│ title                   │
│ description             │
│ status                  │
│ priority                │
│ due_date                │
│ created_at              │
│ updated_at              │
│ tags (JSONB)            │
│ estimated_hours         │
└────────┬────────────────┘
         │ 1
         │
         │ N
┌────────┴────────────────┐
│    Time Entries         │
│─────────────────────────│
│ id (PK)                 │
│ user_id (FK)            │
│ task_id (FK, nullable)  │
│ start_time              │
│ end_time                │
│ duration_seconds        │
│ description             │
│ created_at              │
│ updated_at              │
│ is_active               │
└─────────────────────────┘
```

### PostgreSQL Schema Definitions

#### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,

    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### Tasks Table
```sql
CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done', 'archived');
CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'urgent');

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status task_status NOT NULL DEFAULT 'todo',
    priority task_priority NOT NULL DEFAULT 'medium',
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tags JSONB DEFAULT '[]'::jsonb,
    estimated_hours DECIMAL(10, 2),

    CONSTRAINT title_length CHECK (LENGTH(title) >= 1),
    CONSTRAINT estimated_hours_positive CHECK (estimated_hours IS NULL OR estimated_hours > 0)
);

-- Indexes
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_tags ON tasks USING GIN(tags);

-- Full-text search index
CREATE INDEX idx_tasks_search ON tasks USING GIN(
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))
);

-- Trigger for updated_at
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### Time Entries Table
```sql
CREATE TABLE time_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE,

    CONSTRAINT end_after_start CHECK (end_time IS NULL OR end_time > start_time),
    CONSTRAINT duration_non_negative CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    CONSTRAINT active_has_no_end CHECK (
        (is_active = TRUE AND end_time IS NULL AND duration_seconds IS NULL) OR
        (is_active = FALSE AND end_time IS NOT NULL)
    )
);

-- Indexes
CREATE INDEX idx_time_entries_user_id ON time_entries(user_id);
CREATE INDEX idx_time_entries_task_id ON time_entries(task_id);
CREATE INDEX idx_time_entries_start_time ON time_entries(start_time);
CREATE INDEX idx_time_entries_is_active ON time_entries(is_active);
CREATE INDEX idx_time_entries_created_at ON time_entries(created_at);

-- Unique constraint: only one active entry per user
CREATE UNIQUE INDEX idx_one_active_per_user ON time_entries(user_id)
    WHERE is_active = TRUE;

-- Trigger for updated_at
CREATE TRIGGER update_time_entries_updated_at
    BEFORE UPDATE ON time_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to calculate duration on end_time update
CREATE OR REPLACE FUNCTION calculate_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.end_time IS NOT NULL AND NEW.start_time IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.end_time - NEW.start_time))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER calculate_time_entry_duration
    BEFORE INSERT OR UPDATE ON time_entries
    FOR EACH ROW
    EXECUTE FUNCTION calculate_duration();
```

### Views for Analytics

#### User Productivity Summary View
```sql
CREATE OR REPLACE VIEW user_productivity_summary AS
SELECT
    u.id as user_id,
    u.email,
    u.full_name,
    COUNT(DISTINCT t.id) as total_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as completed_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) as in_progress_tasks,
    COALESCE(SUM(te.duration_seconds) / 3600.0, 0) as total_hours_tracked,
    COALESCE(AVG(te.duration_seconds) / 3600.0, 0) as avg_hours_per_entry,
    COUNT(DISTINCT te.id) as total_time_entries
FROM users u
LEFT JOIN tasks t ON u.id = t.user_id
LEFT JOIN time_entries te ON u.id = te.user_id
GROUP BY u.id, u.email, u.full_name;
```

#### Task Time Summary View
```sql
CREATE OR REPLACE VIEW task_time_summary AS
SELECT
    t.id as task_id,
    t.user_id,
    t.title,
    t.status,
    t.priority,
    t.estimated_hours,
    COUNT(te.id) as time_entry_count,
    COALESCE(SUM(te.duration_seconds) / 3600.0, 0) as actual_hours,
    CASE
        WHEN t.estimated_hours IS NOT NULL THEN
            COALESCE(SUM(te.duration_seconds) / 3600.0, 0) - t.estimated_hours
        ELSE NULL
    END as hours_variance
FROM tasks t
LEFT JOIN time_entries te ON t.id = te.task_id
GROUP BY t.id, t.user_id, t.title, t.status, t.priority, t.estimated_hours;
```

---

## Data Models

### Python/Pydantic Models

#### User Models
```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    """Base user model with common fields."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)

class UserCreate(UserBase):
    """Model for user registration."""
    password: str = Field(..., min_length=8, max_length=100)

    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain special character')
        return v

class UserLogin(BaseModel):
    """Model for user login."""
    email: EmailStr
    password: str

class UserResponse(UserBase):
    """Model for user data in responses."""
    id: UUID
    created_at: datetime
    is_active: bool
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class UserInDB(UserResponse):
    """Internal model including password hash."""
    password_hash: str
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

class TokenResponse(BaseModel):
    """Model for authentication token response."""
    token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
```

#### Task Models
```python
from enum import Enum
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator

class TaskStatus(str, Enum):
    """Task status enumeration."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"

class TaskPriority(str, Enum):
    """Task priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskBase(BaseModel):
    """Base task model."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    estimated_hours: Optional[float] = Field(None, gt=0)

class TaskCreate(TaskBase):
    """Model for task creation."""
    pass

class TaskUpdate(TaskBase):
    """Model for task updates (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None

class TaskStatusUpdate(BaseModel):
    """Model for updating only task status."""
    status: TaskStatus

class TaskResponse(TaskBase):
    """Model for task data in responses."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    time_tracked_hours: float = 0.0

    class Config:
        from_attributes = True

class TaskDetailResponse(TaskResponse):
    """Detailed task response including time entries."""
    time_entries: List['TimeEntryResponse'] = []
```

#### Time Entry Models
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class TimeEntryBase(BaseModel):
    """Base time entry model."""
    task_id: Optional[UUID] = None
    description: Optional[str] = Field(None, max_length=500)

class TimeEntryStart(TimeEntryBase):
    """Model for starting time tracking."""
    pass

class TimeEntryCreate(TimeEntryBase):
    """Model for creating manual time entry."""
    start_time: datetime
    end_time: datetime

    @validator('end_time')
    def end_after_start(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

class TimeEntryUpdate(BaseModel):
    """Model for updating time entry."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=500)

    @validator('end_time')
    def end_after_start(cls, v, values):
        if 'start_time' in values and v and values['start_time'] and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

class TimeEntryResponse(TimeEntryBase):
    """Model for time entry in responses."""
    id: UUID
    user_id: UUID
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    duration_hours: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    task_title: Optional[str] = None

    class Config:
        from_attributes = True

    @property
    def duration_hours(self) -> Optional[float]:
        if self.duration_seconds:
            return self.duration_seconds / 3600.0
        return None
```

#### Analytics Models
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import date, datetime

class DateRange(BaseModel):
    """Date range for analytics queries."""
    start: date
    end: date

class DailyMetrics(BaseModel):
    """Daily productivity metrics."""
    date: date
    tasks_completed: int
    time_tracked_hours: float

class ProductivityTrend(BaseModel):
    """Productivity trend for a period."""
    period_start: date
    period_end: date
    tasks_completed: int
    time_tracked_hours: float
    productivity_score: float
    comparison_previous_period: Dict[str, float]

class TaskStatistics(BaseModel):
    """Task completion statistics."""
    total_tasks: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    completion_rate: float
    on_time_completion_rate: float

class TimeDistribution(BaseModel):
    """Time distribution across categories."""
    total_hours: float
    distribution: List[Dict[str, Any]]
    top_productive_hours: List[int]

class DashboardMetrics(BaseModel):
    """Complete dashboard metrics."""
    date_range: DateRange
    total_tasks_completed: int
    total_tasks_in_progress: int
    total_tasks_todo: int
    total_time_tracked_hours: float
    average_task_completion_time_hours: float
    tasks_completed_on_time: int
    tasks_completed_late: int
    productivity_score: float
    daily_breakdown: List[DailyMetrics]
```

---

## Business Logic

### Authentication Logic

#### Password Security
```python
import bcrypt
from datetime import datetime, timedelta

class PasswordService:
    """Service for password operations."""

    BCRYPT_COST_FACTOR = 12
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt(rounds=PasswordService.BCRYPT_COST_FACTOR)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    @staticmethod
    def is_account_locked(user: UserInDB) -> bool:
        """Check if account is locked due to failed attempts."""
        if user.locked_until and user.locked_until > datetime.utcnow():
            return True
        return False

    @staticmethod
    def handle_failed_login(user: UserInDB) -> UserInDB:
        """Handle failed login attempt."""
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= PasswordService.MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=PasswordService.LOCKOUT_DURATION_MINUTES
            )
        return user

    @staticmethod
    def reset_failed_attempts(user: UserInDB) -> UserInDB:
        """Reset failed login attempts after successful login."""
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        return user
```

#### JWT Token Management
```python
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

class TokenService:
    """Service for JWT token operations."""

    SECRET_KEY = "your-secret-key-here"  # Should be in env var
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    @classmethod
    def create_access_token(cls, user_id: str, email: str) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)

    @classmethod
    def create_refresh_token(cls, user_id: str) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        return jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)

    @classmethod
    def decode_token(cls, token: str) -> Optional[dict]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except JWTError:
            return None
```

### Time Tracking Logic

#### Time Entry Management
```python
from datetime import datetime
from typing import Optional

class TimeTrackingService:
    """Service for time tracking operations."""

    @staticmethod
    async def start_tracking(
        user_id: str,
        task_id: Optional[str],
        description: Optional[str]
    ) -> TimeEntry:
        """Start time tracking for a task."""
        # Check for existing active entry
        active_entry = await get_active_entry(user_id)
        if active_entry:
            raise ValueError("Already have active time entry")

        # Create new entry
        entry = TimeEntry(
            user_id=user_id,
            task_id=task_id,
            start_time=datetime.utcnow(),
            description=description,
            is_active=True
        )
        return await save_entry(entry)

    @staticmethod
    async def stop_tracking(user_id: str) -> TimeEntry:
        """Stop active time tracking."""
        active_entry = await get_active_entry(user_id)
        if not active_entry:
            raise ValueError("No active time entry")

        active_entry.end_time = datetime.utcnow()
        active_entry.is_active = False
        # duration_seconds calculated by database trigger
        return await update_entry(active_entry)

    @staticmethod
    def calculate_productivity_score(
        tasks_completed: int,
        tasks_on_time: int,
        hours_tracked: float,
        period_days: int
    ) -> float:
        """Calculate productivity score (0-100)."""
        # Base score from completion rate
        completion_score = (tasks_completed / max(period_days, 1)) * 20

        # On-time completion bonus
        on_time_rate = tasks_on_time / max(tasks_completed, 1)
        on_time_score = on_time_rate * 30

        # Time tracking consistency
        avg_hours_per_day = hours_tracked / max(period_days, 1)
        time_score = min(avg_hours_per_day / 8.0, 1.0) * 30

        # Task variety bonus
        variety_score = min(tasks_completed / 5.0, 1.0) * 20

        return min(completion_score + on_time_score + time_score + variety_score, 100.0)
```

---

## Security Specifications

### Authentication Requirements
- Passwords hashed with bcrypt (cost factor: 12)
- JWT tokens with short expiration (15 minutes)
- Refresh tokens stored securely (httpOnly cookies)
- Account lockout after 5 failed login attempts (15-minute lockout)
- Rate limiting on authentication endpoints (5 req/min)

### Authorization Requirements
- Role-based access control (future: admin, user roles)
- Resource ownership validation (users can only access their data)
- Token validation on every protected endpoint
- Automatic token refresh mechanism

### Data Protection
- TLS 1.3 for all communications
- Database encryption at rest
- Sensitive data (passwords) never logged
- PII data anonymization in analytics aggregates
- GDPR compliance (data export, right to be forgotten)

### Input Validation
- All inputs validated using Pydantic models
- SQL injection prevention via parameterized queries
- XSS prevention via Content Security Policy
- CSRF protection for state-changing operations
- File upload validation (future feature)

---

## Performance Requirements

### Response Time Targets
- API endpoints: < 200ms (p95)
- Database queries: < 100ms (p95)
- Analytics endpoints: < 500ms (p95)
- Dashboard load: < 1 second

### Scalability Targets
- Support 10,000 concurrent users
- Handle 1,000 requests per second
- Store 10 million time entries
- Process analytics for 100,000 tasks

### Optimization Strategies
- Database connection pooling (50 connections)
- Redis caching for frequent queries (TTL: 5 minutes)
- Query result pagination (max 100 items per page)
- Database indexes on all foreign keys and frequent filters
- Lazy loading for related data

---

## Integration Specifications

### External Service Integration

#### Email Service (Future)
```python
class EmailService:
    """Email notification service."""

    async def send_welcome_email(user: User) -> bool:
        """Send welcome email to new user."""
        pass

    async def send_task_reminder(user: User, task: Task) -> bool:
        """Send task deadline reminder."""
        pass

    async def send_weekly_report(user: User, metrics: DashboardMetrics) -> bool:
        """Send weekly productivity report."""
        pass
```

#### Calendar Integration (Future)
- Google Calendar API integration
- Task deadlines sync to calendar
- Time entries create calendar events

#### Slack Integration (Future)
- Task completion notifications
- Daily standup summaries
- Time tracking reminders

---

## Error Handling

### Error Response Structure
```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ErrorCode(str, Enum):
    """Standard error codes."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: ErrorDetail
    meta: Dict[str, Any]
```

### Exception Hierarchy
```python
class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: ErrorCode, status_code: int):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class ValidationError(AppException):
    """Validation error."""
    def __init__(self, message: str, details: dict):
        super().__init__(message, ErrorCode.VALIDATION_ERROR, 422)
        self.details = details

class AuthenticationError(AppException):
    """Authentication error."""
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, ErrorCode.AUTHENTICATION_ERROR, 401)

class AuthorizationError(AppException):
    """Authorization error."""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, ErrorCode.AUTHORIZATION_ERROR, 403)

class NotFoundError(AppException):
    """Resource not found error."""
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} with id {identifier} not found"
        super().__init__(message, ErrorCode.NOT_FOUND, 404)

class ConflictError(AppException):
    """Resource conflict error."""
    def __init__(self, message: str):
        super().__init__(message, ErrorCode.CONFLICT, 409)
```

---

## Testing Requirements

### Unit Testing
- Test coverage: minimum 80%
- Mock all external dependencies
- Test all business logic functions
- Test all validation rules
- Test error handling paths

### Integration Testing
- Test all API endpoints
- Test database operations
- Test authentication flow
- Test authorization checks
- Test pagination and filtering

### Performance Testing
- Load testing: 1,000 concurrent users
- Stress testing: Peak load scenarios
- Endurance testing: 24-hour sustained load
- Spike testing: Sudden traffic increases

### Security Testing
- OWASP Top 10 vulnerabilities
- SQL injection attempts
- XSS attack prevention
- CSRF protection validation
- Rate limiting effectiveness

---

## Deployment Specifications

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/timetracker
DATABASE_POOL_SIZE=50

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=300

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=false

# CORS
CORS_ORIGINS=https://app.timetracker.com,https://admin.timetracker.com

# Rate Limiting
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_READ=100/minute
RATE_LIMIT_WRITE=50/minute

# Monitoring
SENTRY_DSN=https://...
LOG_LEVEL=INFO
```

### Docker Configuration
```dockerfile
# Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## Monitoring & Logging

### Metrics to Track
- Request count by endpoint
- Request duration (p50, p95, p99)
- Error rate by error type
- Active users count
- Database connection pool usage
- Cache hit/miss ratio
- Task completion rate
- Average time tracking session duration

### Logging Standards
```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON log formatter."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        return json.dumps(log_data)
```

---

## Appendix

### Technology Stack Summary
- **Backend**: FastAPI, Python 3.11+
- **Database**: PostgreSQL 15+, Redis 7+
- **ORM**: SQLAlchemy 2.0+
- **Validation**: Pydantic v2
- **Authentication**: python-jose, bcrypt
- **Testing**: pytest, pytest-asyncio, httpx
- **Monitoring**: Prometheus, Grafana
- **Logging**: structlog, ELK Stack

### References
- FastAPI Documentation: https://fastapi.tiangolo.com/
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Pydantic Documentation: https://docs.pydantic.dev/
- OWASP Security Guidelines: https://owasp.org/

---

**Document Version**: 1.0
**Last Updated**: 2025-10-06
**Author**: Time Agent 1
