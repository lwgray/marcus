# Todo Management Data Models

## Overview

This document defines the complete data model specifications for the Todo Management application. All models follow strict typing and validation rules to ensure data integrity.

## Core Data Models

### 1. User Model

Represents a user of the todo application.

```python
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=100)

class User(UserBase):
    id: UUID
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True
```

### 2. Todo Model

The main todo item model with all properties.

```python
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator

class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TodoPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def weight(self) -> int:
        """Return numeric weight for sorting"""
        weights = {
            TodoPriority.LOW: 1,
            TodoPriority.MEDIUM: 2,
            TodoPriority.HIGH: 3,
            TodoPriority.URGENT: 4
        }
        return weights[self]

class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    priority: TodoPriority = TodoPriority.MEDIUM
    due_date: Optional[datetime] = None

    @validator('due_date')
    def validate_due_date(cls, v):
        if v and v < datetime.utcnow():
            raise ValueError('Due date must be in the future')
        return v

class TodoCreate(TodoBase):
    category_ids: List[UUID] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list, max_items=10)

    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        # Normalize tags
        return [tag.lower().strip() for tag in v if tag.strip()]

class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[TodoStatus] = None
    priority: Optional[TodoPriority] = None
    due_date: Optional[datetime] = None
    category_ids: Optional[List[UUID]] = None
    tags: Optional[List[str]] = Field(None, max_items=10)

    @validator('tags')
    def validate_tags(cls, v):
        if v is not None:
            if len(v) > 10:
                raise ValueError('Maximum 10 tags allowed')
            return [tag.lower().strip() for tag in v if tag.strip()]
        return v

class Todo(TodoBase):
    id: UUID
    user_id: UUID
    status: TodoStatus = TodoStatus.PENDING
    completed_at: Optional[datetime] = None
    category_ids: List[UUID] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

    # Computed properties
    is_overdue: bool = False
    days_until_due: Optional[int] = None

    class Config:
        orm_mode = True

    def __init__(self, **data):
        super().__init__(**data)
        self._compute_properties()

    def _compute_properties(self):
        """Compute dynamic properties"""
        now = datetime.utcnow()
        if self.due_date:
            self.is_overdue = self.due_date < now and self.status != TodoStatus.COMPLETED
            self.days_until_due = (self.due_date - now).days
```

### 3. Category Model

Categories for organizing todos.

```python
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    description: Optional[str] = Field(None, max_length=500)

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, regex="^#[0-9A-Fa-f]{6}$")
    description: Optional[str] = Field(None, max_length=500)

class Category(CategoryBase):
    id: UUID
    user_id: UUID
    todo_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
```

### 4. Comment Model

Comments on todo items.

```python
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CommentCreate(CommentBase):
    pass

class Comment(CommentBase):
    id: UUID
    todo_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    edited: bool = False

    class Config:
        orm_mode = True
```

### 5. Attachment Model

File attachments for todos.

```python
class AttachmentBase(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0, le=10485760)  # Max 10MB
    mime_type: str = Field(..., min_length=1, max_length=100)

class AttachmentCreate(AttachmentBase):
    file_data: bytes

class Attachment(AttachmentBase):
    id: UUID
    todo_id: UUID
    user_id: UUID
    storage_path: str
    created_at: datetime

    class Config:
        orm_mode = True
```

## Aggregate Models

### 6. Todo with Relations

Complete todo model with all related data.

```python
class TodoWithRelations(Todo):
    categories: List[Category] = Field(default_factory=list)
    comments: List[Comment] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)
    created_by: Optional[User] = None

    class Config:
        orm_mode = True
```

### 7. Todo Statistics

Aggregated statistics model.

```python
class TodoStatistics(BaseModel):
    total_todos: int = 0
    by_status: Dict[TodoStatus, int] = Field(default_factory=dict)
    by_priority: Dict[TodoPriority, int] = Field(default_factory=dict)
    completion_rate: float = 0.0
    average_completion_time: Optional[float] = None  # in hours
    overdue_count: int = 0
    due_today: int = 0
    due_this_week: int = 0
    due_this_month: int = 0

    # Category breakdown
    by_category: Dict[str, int] = Field(default_factory=dict)

    # Time-based stats
    created_today: int = 0
    created_this_week: int = 0
    created_this_month: int = 0
    completed_today: int = 0
    completed_this_week: int = 0
    completed_this_month: int = 0

    class Config:
        orm_mode = True
```

## Request/Response Models

### 8. Pagination Models

```python
from typing import Generic, TypeVar, List

T = TypeVar('T')

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @validator('total_pages', pre=True, always=True)
    def calculate_total_pages(cls, v, values):
        total = values.get('total', 0)
        per_page = values.get('per_page', 1)
        return (total + per_page - 1) // per_page

    @validator('has_next', pre=True, always=True)
    def calculate_has_next(cls, v, values):
        page = values.get('page', 1)
        total_pages = values.get('total_pages', 1)
        return page < total_pages

    @validator('has_prev', pre=True, always=True)
    def calculate_has_prev(cls, v, values):
        page = values.get('page', 1)
        return page > 1
```

### 9. Filter Models

```python
class TodoFilters(BaseModel):
    status: Optional[TodoStatus] = None
    priority: Optional[TodoPriority] = None
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = Field(None, min_length=1, max_length=100)
    due_before: Optional[datetime] = None
    due_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    created_after: Optional[datetime] = None

class TodoSort(str, Enum):
    CREATED_AT_ASC = "created_at:asc"
    CREATED_AT_DESC = "created_at:desc"
    UPDATED_AT_ASC = "updated_at:asc"
    UPDATED_AT_DESC = "updated_at:desc"
    DUE_DATE_ASC = "due_date:asc"
    DUE_DATE_DESC = "due_date:desc"
    PRIORITY_ASC = "priority:asc"
    PRIORITY_DESC = "priority:desc"
    TITLE_ASC = "title:asc"
    TITLE_DESC = "title:desc"
```

### 10. Bulk Operation Models

```python
class BulkUpdateRequest(BaseModel):
    todo_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    updates: TodoUpdate

class BulkUpdateResponse(BaseModel):
    updated: int
    failed: int
    results: List[Dict[str, Any]]

class BulkDeleteRequest(BaseModel):
    todo_ids: List[UUID] = Field(..., min_items=1, max_items=100)

class BulkDeleteResponse(BaseModel):
    deleted: int
    failed: int
    results: List[Dict[str, Any]]
```

## Marcus Integration Models

### 11. Marcus Task Conversion

```python
class MarcusTaskConversion(BaseModel):
    project_id: UUID
    assign_to_agent: bool = True
    priority_mapping: Dict[TodoPriority, str] = Field(
        default_factory=lambda: {
            TodoPriority.URGENT: "high",
            TodoPriority.HIGH: "medium",
            TodoPriority.MEDIUM: "low",
            TodoPriority.LOW: "low"
        }
    )
    include_description: bool = True
    include_attachments: bool = False

class MarcusTaskConversionResult(BaseModel):
    todo_id: UUID
    marcus_task_id: str
    project_id: UUID
    status: str
    created_at: datetime
```

### 12. Marcus Sync Status

```python
class MarcusSyncStatus(BaseModel):
    todo_id: UUID
    marcus_task_id: Optional[str] = None
    todo_status: TodoStatus
    marcus_task_status: Optional[str] = None
    last_synced: Optional[datetime] = None
    sync_enabled: bool = False
    sync_errors: List[str] = Field(default_factory=list)
```

## WebSocket Event Models

### 13. WebSocket Events

```python
class WebSocketEventType(str, Enum):
    TODO_CREATED = "todo.created"
    TODO_UPDATED = "todo.updated"
    TODO_DELETED = "todo.deleted"
    TODO_COMPLETED = "todo.completed"
    CATEGORY_CREATED = "category.created"
    CATEGORY_UPDATED = "category.updated"
    CATEGORY_DELETED = "category.deleted"

class WebSocketEvent(BaseModel):
    type: WebSocketEventType
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[UUID] = None

class TodoCreatedEvent(BaseModel):
    id: UUID
    title: str
    created_by: UUID

class TodoUpdatedEvent(BaseModel):
    id: UUID
    changes: Dict[str, Any]
    updated_by: UUID

class TodoDeletedEvent(BaseModel):
    id: UUID
    deleted_by: UUID
```

## Database Schema

### SQL Schema Definition

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- Todos table
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    CONSTRAINT valid_priority CHECK (priority IN ('low', 'medium', 'high', 'urgent'))
);

-- Categories table
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7),
    description VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Todo categories junction table
CREATE TABLE todo_categories (
    todo_id UUID NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (todo_id, category_id)
);

-- Tags table (normalized)
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Todo tags junction table
CREATE TABLE todo_tags (
    todo_id UUID NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (todo_id, tag_id)
);

-- Comments table
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    todo_id UUID NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Attachments table
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    todo_id UUID NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Marcus integration table
CREATE TABLE marcus_todo_sync (
    todo_id UUID PRIMARY KEY REFERENCES todos(id) ON DELETE CASCADE,
    marcus_task_id VARCHAR(255),
    marcus_project_id UUID,
    sync_enabled BOOLEAN DEFAULT FALSE,
    last_synced TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_todos_user_id ON todos(user_id);
CREATE INDEX idx_todos_status ON todos(status);
CREATE INDEX idx_todos_priority ON todos(priority);
CREATE INDEX idx_todos_due_date ON todos(due_date);
CREATE INDEX idx_todos_created_at ON todos(created_at);
CREATE INDEX idx_todos_is_deleted ON todos(is_deleted);
CREATE INDEX idx_categories_user_id ON categories(user_id);
CREATE INDEX idx_comments_todo_id ON comments(todo_id);
CREATE INDEX idx_attachments_todo_id ON attachments(todo_id);

-- Full text search index
CREATE INDEX idx_todos_search ON todos USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_todos_updated_at BEFORE UPDATE ON todos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Validation Rules Summary

### Field Validation Rules

1. **Title**: 1-500 characters, required
2. **Description**: Max 5000 characters, optional
3. **Priority**: One of: low, medium, high, urgent
4. **Status**: One of: pending, in_progress, completed, cancelled
5. **Due Date**: Must be future date when creating
6. **Tags**: Max 10 tags per todo, normalized to lowercase
7. **Color**: Hex color format (#RRGGBB)
8. **Email**: Valid email format
9. **Password**: Min 8 characters, max 100 characters
10. **File Size**: Max 10MB for attachments

### Business Logic Rules

1. **Status Transitions**:
   - pending → in_progress, cancelled
   - in_progress → completed, blocked, cancelled
   - blocked → in_progress, cancelled
   - completed → (terminal state)
   - cancelled → (terminal state)

2. **Completion Rules**:
   - When status changes to completed, set completed_at timestamp
   - Cannot set due_date in the past for non-completed todos
   - Overdue calculation excludes completed todos

3. **Category Rules**:
   - Category names must be unique per user
   - Deleting a category removes it from all todos

4. **Sync Rules**:
   - Only todos with marcus_task_id can sync
   - Sync errors don't affect todo operations
   - Sync is one-way by default (todo → marcus)

This comprehensive data model provides a robust foundation for the todo management application with full Marcus integration support.
