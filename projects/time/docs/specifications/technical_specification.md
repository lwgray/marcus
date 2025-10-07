# Technical Specification - Task Management System

## 1. Implementation Patterns and Best Practices

### 1.1 Repository Pattern Implementation

The repository pattern abstracts data access logic and provides a clean interface for business logic.

```python
# repositories/task_repository.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from models.task import Task
from schemas.task_schema import TaskFilter

class TaskRepository:
    """
    Data access layer for Task entity.

    Handles all database operations for tasks including CRUD operations,
    filtering, and complex queries.
    """

    def __init__(self, db_session: Session):
        """
        Initialize repository with database session.

        Parameters
        ----------
        db_session : Session
            SQLAlchemy database session
        """
        self.db = db_session

    async def create(self, task_data: dict) -> Task:
        """
        Create a new task.

        Parameters
        ----------
        task_data : dict
            Task attributes including title, description, priority, etc.

        Returns
        -------
        Task
            Created task instance
        """
        task = Task(**task_data)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID, user_id: UUID) -> Optional[Task]:
        """
        Retrieve task by ID ensuring user owns it.

        Parameters
        ----------
        task_id : UUID
            Task identifier
        user_id : UUID
            User identifier for authorization check

        Returns
        -------
        Optional[Task]
            Task if found and owned by user, None otherwise
        """
        return await self.db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == user_id
        ).first()

    async def list_tasks(self, user_id: UUID, filters: TaskFilter) -> List[Task]:
        """
        List tasks with filtering and pagination.

        Parameters
        ----------
        user_id : UUID
            User identifier
        filters : TaskFilter
            Filter criteria including status, priority, dates, pagination

        Returns
        -------
        List[Task]
            Filtered and paginated task list
        """
        query = self.db.query(Task).filter(Task.user_id == user_id)

        # Apply filters
        if filters.status:
            query = query.filter(Task.status == filters.status)
        if filters.priority:
            query = query.filter(Task.priority == filters.priority)
        if filters.tags:
            query = query.filter(Task.tags.overlap(filters.tags))
        if filters.due_date_from:
            query = query.filter(Task.due_date >= filters.due_date_from)
        if filters.due_date_to:
            query = query.filter(Task.due_date <= filters.due_date_to)
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                (Task.title.ilike(search_term)) |
                (Task.description.ilike(search_term))
            )

        # Apply sorting
        sort_field = getattr(Task, filters.sort)
        if filters.order == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())

        # Apply pagination
        offset = (filters.page - 1) * filters.limit
        query = query.offset(offset).limit(filters.limit)

        return await query.all()

    async def update(self, task_id: UUID, user_id: UUID, update_data: dict) -> Optional[Task]:
        """
        Update task attributes.

        Parameters
        ----------
        task_id : UUID
            Task identifier
        user_id : UUID
            User identifier for authorization check
        update_data : dict
            Fields to update

        Returns
        -------
        Optional[Task]
            Updated task if found, None otherwise
        """
        task = await self.get_by_id(task_id, user_id)
        if not task:
            return None

        for key, value in update_data.items():
            setattr(task, key, value)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task_id: UUID, user_id: UUID) -> bool:
        """
        Delete a task.

        Parameters
        ----------
        task_id : UUID
            Task identifier
        user_id : UUID
            User identifier for authorization check

        Returns
        -------
        bool
            True if deleted, False if not found
        """
        task = await self.get_by_id(task_id, user_id)
        if not task:
            return False

        await self.db.delete(task)
        await self.db.commit()
        return True
```

### 1.2 Service Layer Pattern

Business logic is encapsulated in service classes, separating concerns from data access.

```python
# services/task_service.py
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from repositories.task_repository import TaskRepository
from schemas.task_schema import TaskCreate, TaskUpdate, TaskFilter
from models.task import Task

class TaskService:
    """
    Business logic layer for task management.

    Handles task operations including creation, updates, validation,
    and coordination with notification services.
    """

    def __init__(self, task_repository: TaskRepository):
        """
        Initialize service with repository.

        Parameters
        ----------
        task_repository : TaskRepository
            Data access layer for tasks
        """
        self.repository = task_repository

    async def create_task(self, user_id: UUID, task_data: TaskCreate) -> Task:
        """
        Create a new task with validation.

        Parameters
        ----------
        user_id : UUID
            Task owner identifier
        task_data : TaskCreate
            Task creation data

        Returns
        -------
        Task
            Created task instance

        Raises
        ------
        ValidationError
            If task data is invalid
        """
        # Validate due date is in future
        if task_data.due_date and task_data.due_date < datetime.now():
            raise ValidationError("Due date must be in the future")

        # Prepare task data
        task_dict = task_data.dict()
        task_dict['user_id'] = user_id
        task_dict['status'] = 'todo'

        # Create task
        task = await self.repository.create(task_dict)

        # Schedule reminder if due date exists
        if task.due_date:
            await self._schedule_reminder(task)

        return task

    async def update_task(
        self,
        task_id: UUID,
        user_id: UUID,
        update_data: TaskUpdate
    ) -> Optional[Task]:
        """
        Update task with validation and side effects.

        Parameters
        ----------
        task_id : UUID
            Task identifier
        user_id : UUID
            User identifier for authorization
        update_data : TaskUpdate
            Fields to update

        Returns
        -------
        Optional[Task]
            Updated task if found, None otherwise
        """
        # Get existing task
        task = await self.repository.get_by_id(task_id, user_id)
        if not task:
            return None

        # Prepare update dictionary
        update_dict = update_data.dict(exclude_unset=True)

        # Handle status change to completed
        if update_dict.get('status') == 'completed' and task.status != 'completed':
            update_dict['completed_at'] = datetime.now()

        # Update task
        updated_task = await self.repository.update(task_id, user_id, update_dict)

        # Trigger webhook if status changed
        if 'status' in update_dict and update_dict['status'] != task.status:
            await self._trigger_webhook('task.updated', updated_task)

        return updated_task

    async def list_tasks(self, user_id: UUID, filters: TaskFilter) -> dict:
        """
        List tasks with pagination metadata.

        Parameters
        ----------
        user_id : UUID
            User identifier
        filters : TaskFilter
            Filter and pagination criteria

        Returns
        -------
        dict
            Dictionary with 'items' and 'pagination' keys
        """
        tasks = await self.repository.list_tasks(user_id, filters)
        total = await self.repository.count_tasks(user_id, filters)

        return {
            'items': tasks,
            'pagination': {
                'page': filters.page,
                'limit': filters.limit,
                'total': total,
                'total_pages': (total + filters.limit - 1) // filters.limit
            }
        }

    async def _schedule_reminder(self, task: Task):
        """Schedule reminder notification for task."""
        # Implementation would use background job queue
        pass

    async def _trigger_webhook(self, event: str, task: Task):
        """Trigger webhook for task event."""
        # Implementation would call webhook service
        pass
```

### 1.3 API Route Handlers

Routes handle HTTP requests and responses, delegating to service layer.

```python
# api/routes/tasks.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from services.task_service import TaskService
from schemas.task_schema import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from api.dependencies import get_current_user, get_task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Create a new task.

    Parameters
    ----------
    task_data : TaskCreate
        Task creation data
    current_user : dict
        Authenticated user from JWT token
    task_service : TaskService
        Injected task service

    Returns
    -------
    TaskResponse
        Created task wrapped in success response
    """
    try:
        task = await task_service.create_task(current_user['id'], task_data)
        return TaskResponse(success=True, data=task)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        )

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """
    List tasks with filtering and pagination.

    Parameters
    ----------
    status : Optional[str]
        Filter by status
    priority : Optional[str]
        Filter by priority
    page : int
        Page number (default: 1)
    limit : int
        Items per page (default: 20)
    current_user : dict
        Authenticated user
    task_service : TaskService
        Injected task service

    Returns
    -------
    TaskListResponse
        Paginated task list with metadata
    """
    filters = TaskFilter(
        status=status,
        priority=priority,
        page=page,
        limit=min(limit, 100)  # Cap at 100
    )

    result = await task_service.list_tasks(current_user['id'], filters)
    return TaskListResponse(success=True, data=result)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Get a specific task by ID.

    Parameters
    ----------
    task_id : UUID
        Task identifier
    current_user : dict
        Authenticated user
    task_service : TaskService
        Injected task service

    Returns
    -------
    TaskResponse
        Task data wrapped in success response

    Raises
    ------
    HTTPException
        404 if task not found
    """
    task = await task_service.get_task(task_id, current_user['id'])
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": f"Task with id '{task_id}' not found"
            }
        )

    return TaskResponse(success=True, data=task)

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    update_data: TaskUpdate,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Update a task.

    Parameters
    ----------
    task_id : UUID
        Task identifier
    update_data : TaskUpdate
        Fields to update
    current_user : dict
        Authenticated user
    task_service : TaskService
        Injected task service

    Returns
    -------
    TaskResponse
        Updated task data

    Raises
    ------
    HTTPException
        404 if task not found
    """
    task = await task_service.update_task(task_id, current_user['id'], update_data)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": f"Task with id '{task_id}' not found"
            }
        )

    return TaskResponse(success=True, data=task)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Delete a task.

    Parameters
    ----------
    task_id : UUID
        Task identifier
    current_user : dict
        Authenticated user
    task_service : TaskService
        Injected task service

    Raises
    ------
    HTTPException
        404 if task not found
    """
    deleted = await task_service.delete_task(task_id, current_user['id'])
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": f"Task with id '{task_id}' not found"
            }
        )
```

### 1.4 Data Validation with Pydantic

```python
# schemas/task_schema.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(str, Enum):
    """Task status values."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class TaskCreate(BaseModel):
    """
    Schema for creating a new task.

    Attributes
    ----------
    title : str
        Task title (required, max 200 chars)
    description : Optional[str]
        Task description (max 5000 chars)
    due_date : Optional[datetime]
        Task due date
    priority : TaskPriority
        Task priority (default: medium)
    tags : List[str]
        Task tags for categorization
    project_id : Optional[UUID]
        Associated project identifier
    """
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    tags: List[str] = Field(default_factory=list)
    project_id: Optional[UUID] = None

    @validator('title')
    def title_not_empty(cls, v):
        """Validate title is not just whitespace."""
        if not v or not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        return v.strip()

    @validator('due_date')
    def due_date_in_future(cls, v):
        """Validate due date is in the future."""
        if v and v < datetime.now():
            raise ValueError('Due date must be in the future')
        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags are non-empty and unique."""
        if not v:
            return v
        # Remove empty tags and duplicates
        tags = [tag.strip() for tag in v if tag.strip()]
        return list(set(tags))

class TaskUpdate(BaseModel):
    """
    Schema for updating a task.

    All fields are optional for partial updates.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None
    project_id: Optional[UUID] = None

class TaskResponse(BaseModel):
    """
    Schema for task in API responses.

    Includes all task fields plus metadata.
    """
    id: UUID
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: TaskPriority
    status: TaskStatus
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    user_id: UUID
    project_id: Optional[UUID]

    class Config:
        """Pydantic configuration."""
        from_attributes = True  # Enable ORM mode
```

## 2. Database Optimization Strategies

### 2.1 Index Strategy

```sql
-- Primary indexes for foreign keys and common queries
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_project_id ON tasks(project_id);

-- Indexes for filtering
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);

-- Composite index for common query patterns
CREATE INDEX idx_tasks_user_status_priority ON tasks(user_id, status, priority);
CREATE INDEX idx_tasks_user_due_date ON tasks(user_id, due_date) WHERE due_date IS NOT NULL;

-- GIN index for array operations (tags)
CREATE INDEX idx_tasks_tags ON tasks USING GIN(tags);

-- Full-text search index
CREATE INDEX idx_tasks_search ON tasks USING GIN(to_tsvector('english', title || ' ' || COALESCE(description, '')));
```

### 2.2 Query Optimization

```python
# Use select_related for foreign keys to avoid N+1 queries
tasks = await session.query(Task)\
    .options(selectinload(Task.project))\
    .filter(Task.user_id == user_id)\
    .all()

# Use pagination to limit result sets
query = query.offset(offset).limit(limit)

# Use count query separately for better performance
total_count = await session.query(func.count(Task.id))\
    .filter(Task.user_id == user_id)\
    .scalar()
```

## 3. Error Handling Strategy

### 3.1 Custom Exception Classes

```python
# utils/exceptions.py
class TaskManagerException(Exception):
    """Base exception for task manager."""
    pass

class ValidationError(TaskManagerException):
    """Raised when input validation fails."""
    pass

class NotFoundError(TaskManagerException):
    """Raised when resource is not found."""
    pass

class UnauthorizedError(TaskManagerException):
    """Raised when user is not authorized."""
    pass
```

### 3.2 Global Exception Handler

```python
# api/middleware/error_handler.py
from fastapi import Request, status
from fastapi.responses import JSONResponse

async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for consistent error responses.

    Parameters
    ----------
    request : Request
        FastAPI request object
    exc : Exception
        Raised exception

    Returns
    -------
    JSONResponse
        Standardized error response
    """
    if isinstance(exc, ValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

    if isinstance(exc, NotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": str(exc),
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

    # Generic server error
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        }
    )
```

## 4. Testing Strategy

### 4.1 Unit Test Example

```python
# tests/unit/services/test_task_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime, timedelta
from services.task_service import TaskService
from schemas.task_schema import TaskCreate

class TestTaskService:
    """Unit tests for TaskService."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock task repository."""
        mock = Mock()
        mock.create = AsyncMock()
        mock.get_by_id = AsyncMock()
        mock.update = AsyncMock()
        mock.delete = AsyncMock()
        return mock

    @pytest.fixture
    def task_service(self, mock_repository):
        """Create task service with mock repository."""
        return TaskService(mock_repository)

    @pytest.mark.asyncio
    async def test_create_task_success(self, task_service, mock_repository):
        """Test successful task creation."""
        # Arrange
        user_id = uuid4()
        task_data = TaskCreate(
            title="Test Task",
            description="Test Description",
            priority="high"
        )
        expected_task = Mock(
            id=uuid4(),
            title="Test Task",
            user_id=user_id
        )
        mock_repository.create.return_value = expected_task

        # Act
        result = await task_service.create_task(user_id, task_data)

        # Assert
        assert result == expected_task
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_past_due_date_fails(self, task_service):
        """Test task creation fails with past due date."""
        # Arrange
        user_id = uuid4()
        past_date = datetime.now() - timedelta(days=1)
        task_data = TaskCreate(
            title="Test Task",
            due_date=past_date
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Due date must be in the future"):
            await task_service.create_task(user_id, task_data)
```

### 4.2 Integration Test Example

```python
# tests/integration/api/test_tasks_api.py
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

class TestTasksAPI:
    """Integration tests for tasks API."""

    @pytest.fixture
    def auth_headers(self, test_user):
        """Get authorization headers for test user."""
        token = create_test_token(test_user['id'])
        return {"Authorization": f"Bearer {token}"}

    def test_create_task_success(self, client, auth_headers):
        """Test successful task creation via API."""
        # Arrange
        task_data = {
            "title": "Integration Test Task",
            "description": "Test Description",
            "priority": "high"
        }

        # Act
        response = client.post(
            "/v1/tasks",
            json=task_data,
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == task_data["title"]
        assert "id" in data["data"]

    def test_create_task_without_auth_fails(self, client):
        """Test task creation fails without authentication."""
        # Arrange
        task_data = {"title": "Test Task"}

        # Act
        response = client.post("/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 401
```

## 5. Performance Considerations

### 5.1 Caching Strategy

```python
# Use Redis for caching frequently accessed data
from redis import asyncio as aioredis
import json

class CachedTaskService:
    """Task service with caching layer."""

    def __init__(self, task_service: TaskService, redis_client: aioredis.Redis):
        self.task_service = task_service
        self.redis = redis_client

    async def get_task(self, task_id: UUID, user_id: UUID) -> Optional[Task]:
        """Get task with caching."""
        cache_key = f"task:{task_id}:{user_id}"

        # Try cache first
        cached = await self.redis.get(cache_key)
        if cached:
            return Task(**json.loads(cached))

        # Fetch from database
        task = await self.task_service.get_task(task_id, user_id)
        if task:
            # Cache for 5 minutes
            await self.redis.setex(
                cache_key,
                300,
                json.dumps(task.dict())
            )

        return task
```

### 5.2 Background Job Processing

```python
# Use Celery for background tasks
from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task
def send_task_reminder(task_id: str, user_email: str):
    """Send reminder email for task."""
    # Email sending logic
    pass

@celery_app.task
def cleanup_completed_tasks():
    """Archive old completed tasks."""
    # Cleanup logic
    pass
```

## 6. Security Implementation

### 6.1 JWT Authentication

```python
# api/middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()

def create_access_token(user_id: str) -> str:
    """
    Create JWT access token.

    Parameters
    ----------
    user_id : str
        User identifier

    Returns
    -------
    str
        Encoded JWT token
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Validate JWT token and extract user.

    Parameters
    ----------
    credentials : HTTPAuthorizationCredentials
        Bearer token credentials

    Returns
    -------
    dict
        User information from token

    Raises
    ------
    HTTPException
        401 if token is invalid or expired
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=['HS256']
        )
        return {'id': payload['user_id']}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
```

### 6.2 Input Sanitization

```python
# utils/validators.py
import re
from typing import str

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent XSS attacks.

    Parameters
    ----------
    text : str
        User input text

    Returns
    -------
    str
        Sanitized text
    """
    if not text:
        return text

    # Remove potentially dangerous HTML tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)

    return text.strip()
```

## 7. Deployment Configuration

### 7.1 Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
```

### 7.2 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/taskmanager
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=taskmanager
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## 8. Monitoring and Observability

### 8.1 Logging Configuration

```python
# config/logging.py
import logging
import sys

def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/app.log')
        ]
    )

    # Set specific log levels
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
```

### 8.2 Metrics Collection

```python
# api/middleware/metrics.py
from prometheus_client import Counter, Histogram
import time

request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

async def metrics_middleware(request: Request, call_next):
    """Collect metrics for each request."""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    return response
```

---

**Document Version**: 1.0
**Last Updated**: October 6, 2025
**Author**: Time Agent 3
**Status**: Ready for Implementation
