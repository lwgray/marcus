# TODO CRUD Implementation Design

## Version: 1.0.0
## Author: Backend Agent 2
## Date: 2025-10-07

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Models (SQLAlchemy)](#data-models-sqlalchemy)
4. [Schemas (Pydantic)](#schemas-pydantic)
5. [Service Layer](#service-layer)
6. [API Routes](#api-routes)
7. [Database Migrations](#database-migrations)
8. [Testing Strategy](#testing-strategy)
9. [Implementation Checklist](#implementation-checklist)

---

## Overview

This document provides the detailed implementation design for CRUD operations on TODO items, building upon the existing API specification at `/docs/specifications/todo-api-specification.md`.

### Design Principles
- **Separation of Concerns**: Models, Schemas, Services, and Routes are separate
- **Dependency Injection**: FastAPI's dependency system for authentication and database sessions
- **Type Safety**: Full type hints throughout the codebase
- **Error Handling**: Use Marcus Error Framework for all user-facing errors
- **Testing**: 80%+ test coverage with unit and integration tests

### Technology Stack
- **Framework**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+
- **Validation**: Pydantic 2.0+
- **Database**: PostgreSQL 14+
- **Authentication**: JWT (PyJWT)
- **Testing**: pytest, pytest-asyncio

---

## Architecture

### Layer Structure
```
┌─────────────────────────────────────┐
│         API Layer (Routers)         │
│  - Request validation               │
│  - Response serialization           │
│  - Authentication                   │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│       Service Layer (Business)      │
│  - Business logic                   │
│  - Data transformations             │
│  - Complex queries                  │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│      Data Layer (Models + DB)       │
│  - SQLAlchemy models                │
│  - Database sessions                │
│  - Transactions                     │
└─────────────────────────────────────┘
```

### Project Structure
```
todo-api/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py           # Base model with TimestampMixin
│   │   ├── user.py           # User SQLAlchemy model
│   │   ├── todo.py           # Todo SQLAlchemy model
│   │   └── tag.py            # Tag SQLAlchemy model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py           # User Pydantic schemas
│   │   ├── todo.py           # Todo Pydantic schemas
│   │   ├── tag.py            # Tag Pydantic schemas
│   │   └── common.py         # Common schemas (pagination, etc.)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── todo_service.py   # Todo business logic
│   │   └── tag_service.py    # Tag business logic
│   ├── routers/
│   │   ├── __init__.py
│   │   └── todos.py          # Todo API endpoints
│   ├── core/
│   │   ├── database.py       # Database configuration
│   │   ├── dependencies.py   # Dependency injection
│   │   └── config.py         # Application config
│   └── utils/
│       └── error_handling.py # Error handling utilities
├── tests/
│   ├── unit/
│   │   ├── test_todo_service.py
│   │   └── test_todo_models.py
│   └── integration/
│       └── test_todo_api.py
└── migrations/
    └── versions/
```

---

## Data Models (SQLAlchemy)

### Base Model (`src/models/base.py`)

```python
"""
Base model and database configuration.

This module provides the declarative base for all SQLAlchemy models
and common functionality shared across models.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Declarative base for all models
Base = declarative_base()


class TimestampMixin:
    """
    Mixin for created_at and updated_at timestamps.

    Automatically tracks creation and modification times for all models.

    Attributes
    ----------
    created_at : datetime
        When the record was created (auto-set)
    updated_at : datetime
        When the record was last updated (auto-updated)
    """

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="When this record was created",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="When this record was last updated",
    )


class UUIDMixin:
    """
    Mixin for UUID primary key.

    Attributes
    ----------
    id : uuid
        UUID primary key
    """

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for this record",
    )
```

### User Model (`src/models/user.py`)

```python
"""
User SQLAlchemy model.

Represents users in the todo application with authentication and profile data.
"""

from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model for authentication and profile management.

    Attributes
    ----------
    id : uuid
        Unique identifier
    email : str
        User's email address (unique)
    username : str
        User's username (unique)
    password_hash : str
        Bcrypt hashed password
    first_name : str, optional
        User's first name
    last_name : str, optional
        User's last name
    avatar_url : str, optional
        URL to user's avatar image
    is_active : bool
        Whether the account is active
    created_at : datetime
        When the user registered
    updated_at : datetime
        When the user last updated their profile
    """

    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    owned_todos = relationship(
        "Todo",
        back_populates="owner",
        foreign_keys="Todo.owner_id",
        cascade="all, delete-orphan",
    )
    assigned_todos = relationship(
        "Todo",
        back_populates="assigned_to",
        foreign_keys="Todo.assigned_to_id",
    )
    tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
```

### Todo Model (`src/models/todo.py`)

```python
"""
Todo SQLAlchemy model.

Represents todo items with status, priority, and relationships.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin


class Todo(Base, UUIDMixin, TimestampMixin):
    """
    Todo model representing a task or todo item.

    Attributes
    ----------
    id : uuid
        Unique identifier
    title : str
        Todo title (1-200 characters)
    description : str, optional
        Detailed description (max 2000 characters)
    status : str
        Current status: pending, in_progress, completed
    priority : str
        Priority level: low, medium, high, urgent
    due_date : datetime, optional
        When the todo is due
    completed_at : datetime, optional
        When the todo was completed (auto-set)
    owner_id : uuid
        ID of the user who owns this todo
    assigned_to_id : uuid, optional
        ID of the user assigned to this todo
    position : int
        Position for custom ordering (default: 0)
    created_at : datetime
        When the todo was created
    updated_at : datetime
        When the todo was last modified
    """

    __tablename__ = "todos"

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    priority = Column(String(20), default="medium", nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    position = Column(Integer, default=0, nullable=False)

    # Foreign keys
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_to_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    owner = relationship("User", back_populates="owned_todos", foreign_keys=[owner_id])
    assigned_to = relationship(
        "User", back_populates="assigned_todos", foreign_keys=[assigned_to_id]
    )
    tags = relationship("Tag", secondary="todo_tags", back_populates="todos")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')",
            name="valid_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="valid_priority",
        ),
        Index("idx_todos_owner_id", "owner_id"),
        Index("idx_todos_status", "status"),
        Index("idx_todos_due_date", "due_date"),
        Index("idx_todos_owner_status", "owner_id", "status"),
    )

    def __repr__(self):
        return f"<Todo(id={self.id}, title={self.title}, status={self.status})>"
```

### Tag Model (`src/models/tag.py`)

```python
"""
Tag SQLAlchemy model.

Represents tags for organizing todos.
"""

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Index, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin


# Association table for many-to-many relationship between todos and tags
todo_tags = Table(
    "todo_tags",
    Base.metadata,
    Column("todo_id", UUID(as_uuid=True), ForeignKey("todos.id", ondelete="CASCADE")),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE")),
)


class Tag(Base, UUIDMixin, TimestampMixin):
    """
    Tag model for organizing and categorizing todos.

    Attributes
    ----------
    id : uuid
        Unique identifier
    name : str
        Tag name (1-50 characters)
    color : str, optional
        Hex color code for the tag
    user_id : uuid
        ID of the user who owns this tag
    created_at : datetime
        When the tag was created
    updated_at : datetime
        When the tag was last modified
    """

    __tablename__ = "tags"

    name = Column(String(50), nullable=False)
    color = Column(String(7), nullable=True)  # Hex color code (#RRGGBB)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="tags")
    todos = relationship("Todo", secondary=todo_tags, back_populates="tags")

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="unique_tag_per_user"),
        Index("idx_tags_user_id", "user_id"),
    )

    def __repr__(self):
        return f"<Tag(id={self.id}, name={self.name}, user_id={self.user_id})>"
```

---

## Schemas (Pydantic)

### Common Schemas (`src/schemas/common.py`)

```python
"""
Common Pydantic schemas for API requests and responses.

Provides reusable schemas for pagination, filtering, and sorting.
"""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Query parameters for pagination.

    Attributes
    ----------
    page : int
        Page number (1-indexed)
    page_size : int
        Number of items per page (max 100)
    """

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response wrapper.

    Attributes
    ----------
    items : List[T]
        List of items for current page
    total : int
        Total number of items across all pages
    page : int
        Current page number
    page_size : int
        Number of items per page
    pages : int
        Total number of pages
    """

    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)
```

### Todo Schemas (`src/schemas/todo.py`)

```python
"""
Todo Pydantic schemas for API requests and responses.

Defines validation models for todo CRUD operations.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


class TodoStatus(str, Enum):
    """Valid todo status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TodoPriority(str, Enum):
    """Valid todo priority values."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TodoBase(BaseModel):
    """
    Base schema for todo with common fields.

    Attributes
    ----------
    title : str
        Todo title (1-200 characters)
    description : str, optional
        Detailed description (max 2000 characters)
    status : TodoStatus
        Current status
    priority : TodoPriority
        Priority level
    due_date : datetime, optional
        When the todo is due
    tags : List[str]
        List of tag names
    """

    title: str = Field(min_length=1, max_length=200, description="Todo title")
    description: Optional[str] = Field(
        default=None, max_length=2000, description="Detailed description"
    )
    status: TodoStatus = Field(default=TodoStatus.PENDING, description="Todo status")
    priority: TodoPriority = Field(
        default=TodoPriority.MEDIUM, description="Priority level"
    )
    due_date: Optional[datetime] = Field(default=None, description="Due date")
    tags: List[str] = Field(default_factory=list, description="Tag names")


class TodoCreate(TodoBase):
    """
    Schema for creating a new todo.

    All fields from TodoBase are available.
    Owner is determined from authenticated user.
    """

    pass


class TodoUpdate(BaseModel):
    """
    Schema for updating a todo.

    All fields are optional for partial updates.

    Attributes
    ----------
    title : str, optional
        New title
    description : str, optional
        New description
    status : TodoStatus, optional
        New status
    priority : TodoPriority, optional
        New priority
    due_date : datetime, optional
        New due date
    tags : List[str], optional
        New list of tags
    """

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[TodoStatus] = None
    priority: Optional[TodoPriority] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TodoInDB(TodoBase):
    """
    Schema for todo as stored in database.

    Includes all database fields including IDs and timestamps.

    Attributes
    ----------
    id : UUID
        Unique identifier
    owner_id : UUID
        Owner's user ID
    assigned_to_id : UUID, optional
        Assigned user's ID
    position : int
        Custom ordering position
    completed_at : datetime, optional
        When the todo was completed
    created_at : datetime
        Creation timestamp
    updated_at : datetime
        Last modification timestamp
    """

    id: UUID
    owner_id: UUID
    assigned_to_id: Optional[UUID] = None
    position: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TodoResponse(TodoInDB):
    """
    Schema for todo in API responses.

    Identical to TodoInDB but explicitly named for API responses.
    """

    pass


class TodoFilterParams(BaseModel):
    """
    Query parameters for filtering todos.

    Attributes
    ----------
    status : TodoStatus, optional
        Filter by status
    priority : TodoPriority, optional
        Filter by priority
    tag : str, optional
        Filter by tag name
    search : str, optional
        Search in title and description
    sort_by : str
        Field to sort by
    sort_order : str
        Sort order (asc or desc)
    """

    status: Optional[TodoStatus] = None
    priority: Optional[TodoPriority] = None
    tag: Optional[str] = None
    search: Optional[str] = None
    sort_by: str = Field(
        default="created_at",
        pattern="^(created_at|due_date|priority|title|updated_at)$",
    )
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class TodoBulkUpdate(BaseModel):
    """
    Schema for bulk updating multiple todos.

    Attributes
    ----------
    todo_ids : List[UUID]
        List of todo IDs to update
    updates : TodoUpdate
        Fields to update
    """

    todo_ids: List[UUID] = Field(min_length=1, description="Todo IDs to update")
    updates: TodoUpdate = Field(description="Updates to apply")


class TodoBulkUpdateResponse(BaseModel):
    """
    Response for bulk update operation.

    Attributes
    ----------
    updated_count : int
        Number of todos updated
    todos : List[TodoResponse]
        Updated todo objects
    """

    updated_count: int
    todos: List[TodoResponse]


class TodoReorderRequest(BaseModel):
    """
    Schema for reordering todos.

    Attributes
    ----------
    todo_ids : List[UUID]
        Ordered list of todo IDs
    """

    todo_ids: List[UUID] = Field(
        min_length=1, description="Todo IDs in desired order"
    )
```

### Tag Schemas (`src/schemas/tag.py`)

```python
"""
Tag Pydantic schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class TagBase(BaseModel):
    """
    Base schema for tag with common fields.

    Attributes
    ----------
    name : str
        Tag name (1-50 characters)
    color : str, optional
        Hex color code
    """

    name: str = Field(min_length=1, max_length=50, description="Tag name")
    color: Optional[str] = Field(
        default=None, pattern="^#[0-9A-Fa-f]{6}$", description="Hex color code"
    )


class TagCreate(TagBase):
    """Schema for creating a new tag."""

    pass


class TagUpdate(BaseModel):
    """
    Schema for updating a tag.

    All fields are optional for partial updates.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class TagInDB(TagBase):
    """
    Schema for tag as stored in database.

    Attributes
    ----------
    id : UUID
        Unique identifier
    user_id : UUID
        Owner's user ID
    created_at : datetime
        Creation timestamp
    updated_at : datetime
        Last modification timestamp
    """

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagResponse(TagInDB):
    """Schema for tag in API responses."""

    pass
```

---

## Service Layer

### Todo Service (`src/services/todo_service.py`)

```python
"""
Todo business logic service.

Handles all todo-related business operations including CRUD,
filtering, pagination, and bulk operations.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.core.error_framework import (
    ResourceNotFoundError,
    UnauthorizedActionError,
    ValidationError,
    ErrorContext,
)
from src.models.todo import Todo
from src.models.tag import Tag
from src.schemas.todo import (
    TodoCreate,
    TodoUpdate,
    TodoFilterParams,
    TodoStatus,
)
from src.schemas.common import PaginationParams


class TodoService:
    """
    Service class for todo business logic.

    Provides methods for creating, reading, updating, and deleting todos,
    as well as advanced features like filtering, pagination, and bulk operations.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize todo service.

        Parameters
        ----------
        db : AsyncSession
            Database session for operations
        """
        self.db = db

    async def create_todo(self, user_id: UUID, todo_data: TodoCreate) -> Todo:
        """
        Create a new todo for the authenticated user.

        Parameters
        ----------
        user_id : UUID
            ID of the user creating the todo
        todo_data : TodoCreate
            Todo creation data

        Returns
        -------
        Todo
            Created todo object

        Raises
        ------
        ValidationError
            If validation fails
        """
        # Create todo object
        todo = Todo(
            title=todo_data.title,
            description=todo_data.description,
            status=todo_data.status.value,
            priority=todo_data.priority.value,
            due_date=todo_data.due_date,
            owner_id=user_id,
        )

        # Handle tags
        if todo_data.tags:
            tags = await self._get_or_create_tags(user_id, todo_data.tags)
            todo.tags = tags

        self.db.add(todo)
        await self.db.commit()
        await self.db.refresh(todo)

        return todo

    async def get_todo(self, todo_id: UUID, user_id: UUID) -> Todo:
        """
        Get a todo by ID.

        Parameters
        ----------
        todo_id : UUID
            ID of the todo
        user_id : UUID
            ID of the requesting user

        Returns
        -------
        Todo
            Todo object

        Raises
        ------
        ResourceNotFoundError
            If todo not found
        UnauthorizedActionError
            If user doesn't have access
        """
        query = (
            select(Todo)
            .options(selectinload(Todo.tags))
            .where(Todo.id == todo_id)
        )

        result = await self.db.execute(query)
        todo = result.scalar_one_or_none()

        if not todo:
            raise ResourceNotFoundError(
                resource_type="Todo",
                resource_id=str(todo_id),
                context=ErrorContext(
                    operation="get_todo",
                    user_id=str(user_id),
                ),
            )

        # Check authorization
        if todo.owner_id != user_id and todo.assigned_to_id != user_id:
            raise UnauthorizedActionError(
                action="view todo",
                resource=f"todo {todo_id}",
                context=ErrorContext(
                    operation="get_todo",
                    user_id=str(user_id),
                ),
            )

        return todo

    async def list_todos(
        self,
        user_id: UUID,
        filters: TodoFilterParams,
        pagination: PaginationParams,
    ) -> Tuple[List[Todo], int]:
        """
        List todos with filtering and pagination.

        Parameters
        ----------
        user_id : UUID
            ID of the requesting user
        filters : TodoFilterParams
            Filtering criteria
        pagination : PaginationParams
            Pagination parameters

        Returns
        -------
        Tuple[List[Todo], int]
            Tuple of (todos list, total count)
        """
        # Base query - user's owned or assigned todos
        query = select(Todo).where(
            or_(Todo.owner_id == user_id, Todo.assigned_to_id == user_id)
        )

        # Apply filters
        if filters.status:
            query = query.where(Todo.status == filters.status.value)

        if filters.priority:
            query = query.where(Todo.priority == filters.priority.value)

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    Todo.title.ilike(search_term),
                    Todo.description.ilike(search_term),
                )
            )

        if filters.tag:
            query = query.join(Todo.tags).where(Tag.name == filters.tag)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Apply sorting
        if filters.sort_order == "desc":
            query = query.order_by(getattr(Todo, filters.sort_by).desc())
        else:
            query = query.order_by(getattr(Todo, filters.sort_by).asc())

        # Apply pagination
        offset = (pagination.page - 1) * pagination.page_size
        query = query.offset(offset).limit(pagination.page_size)

        # Load tags
        query = query.options(selectinload(Todo.tags))

        # Execute query
        result = await self.db.execute(query)
        todos = result.scalars().all()

        return list(todos), total

    async def update_todo(
        self, todo_id: UUID, user_id: UUID, updates: TodoUpdate
    ) -> Todo:
        """
        Update a todo.

        Parameters
        ----------
        todo_id : UUID
            ID of the todo to update
        user_id : UUID
            ID of the requesting user
        updates : TodoUpdate
            Fields to update

        Returns
        -------
        Todo
            Updated todo object

        Raises
        ------
        ResourceNotFoundError
            If todo not found
        UnauthorizedActionError
            If user is not the owner
        """
        # Get existing todo
        todo = await self.get_todo(todo_id, user_id)

        # Check ownership
        if todo.owner_id != user_id:
            raise UnauthorizedActionError(
                action="update todo",
                resource=f"todo {todo_id}",
                context=ErrorContext(
                    operation="update_todo",
                    user_id=str(user_id),
                ),
            )

        # Apply updates
        update_data = updates.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "tags":
                # Handle tags specially
                tags = await self._get_or_create_tags(user_id, value)
                todo.tags = tags
            elif field in ("status", "priority"):
                # Handle enums
                setattr(todo, field, value.value if value else None)
            else:
                setattr(todo, field, value)

        # Auto-set completed_at when status becomes completed
        if updates.status == TodoStatus.COMPLETED and not todo.completed_at:
            todo.completed_at = datetime.utcnow()
        elif updates.status and updates.status != TodoStatus.COMPLETED:
            todo.completed_at = None

        await self.db.commit()
        await self.db.refresh(todo)

        return todo

    async def delete_todo(self, todo_id: UUID, user_id: UUID) -> None:
        """
        Delete a todo.

        Parameters
        ----------
        todo_id : UUID
            ID of the todo to delete
        user_id : UUID
            ID of the requesting user

        Raises
        ------
        ResourceNotFoundError
            If todo not found
        UnauthorizedActionError
            If user is not the owner
        """
        # Get existing todo
        todo = await self.get_todo(todo_id, user_id)

        # Check ownership
        if todo.owner_id != user_id:
            raise UnauthorizedActionError(
                action="delete todo",
                resource=f"todo {todo_id}",
                context=ErrorContext(
                    operation="delete_todo",
                    user_id=str(user_id),
                ),
            )

        await self.db.delete(todo)
        await self.db.commit()

    async def bulk_update_todos(
        self, todo_ids: List[UUID], user_id: UUID, updates: TodoUpdate
    ) -> List[Todo]:
        """
        Update multiple todos at once.

        Parameters
        ----------
        todo_ids : List[UUID]
            IDs of todos to update
        user_id : UUID
            ID of the requesting user
        updates : TodoUpdate
            Fields to update

        Returns
        -------
        List[Todo]
            Updated todo objects

        Raises
        ------
        UnauthorizedActionError
            If user doesn't own all specified todos
        """
        # Verify ownership of all todos
        query = select(Todo).where(
            and_(Todo.id.in_(todo_ids), Todo.owner_id == user_id)
        )
        result = await self.db.execute(query)
        todos = result.scalars().all()

        if len(todos) != len(todo_ids):
            raise UnauthorizedActionError(
                action="bulk update todos",
                resource="specified todos",
                context=ErrorContext(
                    operation="bulk_update_todos",
                    user_id=str(user_id),
                ),
            )

        # Apply updates to each todo
        update_data = updates.model_dump(exclude_unset=True)

        for todo in todos:
            for field, value in update_data.items():
                if field == "tags":
                    tags = await self._get_or_create_tags(user_id, value)
                    todo.tags = tags
                elif field in ("status", "priority"):
                    setattr(todo, field, value.value if value else None)
                else:
                    setattr(todo, field, value)

            # Auto-set completed_at
            if updates.status == TodoStatus.COMPLETED and not todo.completed_at:
                todo.completed_at = datetime.utcnow()

        await self.db.commit()

        return list(todos)

    async def reorder_todos(self, todo_ids: List[UUID], user_id: UUID) -> None:
        """
        Reorder todos by updating their position field.

        Parameters
        ----------
        todo_ids : List[UUID]
            Ordered list of todo IDs
        user_id : UUID
            ID of the requesting user

        Raises
        ------
        UnauthorizedActionError
            If user doesn't own all specified todos
        """
        # Verify ownership
        query = select(Todo).where(
            and_(Todo.id.in_(todo_ids), Todo.owner_id == user_id)
        )
        result = await self.db.execute(query)
        todos = {todo.id: todo for todo in result.scalars()}

        if len(todos) != len(todo_ids):
            raise UnauthorizedActionError(
                action="reorder todos",
                resource="specified todos",
                context=ErrorContext(
                    operation="reorder_todos",
                    user_id=str(user_id),
                ),
            )

        # Update positions
        for position, todo_id in enumerate(todo_ids):
            todos[todo_id].position = position

        await self.db.commit()

    async def _get_or_create_tags(
        self, user_id: UUID, tag_names: List[str]
    ) -> List[Tag]:
        """
        Get existing tags or create new ones.

        Parameters
        ----------
        user_id : UUID
            ID of the user
        tag_names : List[str]
            List of tag names

        Returns
        -------
        List[Tag]
            List of tag objects
        """
        tags = []

        for name in tag_names:
            # Try to find existing tag
            query = select(Tag).where(
                and_(Tag.name == name, Tag.user_id == user_id)
            )
            result = await self.db.execute(query)
            tag = result.scalar_one_or_none()

            if not tag:
                # Create new tag
                tag = Tag(name=name, user_id=user_id)
                self.db.add(tag)

            tags.append(tag)

        await self.db.flush()
        return tags
```

---

## API Routes

### Todo Routes (`src/routers/todos.py`)

```python
"""
Todo API endpoints.

Provides RESTful endpoints for todo CRUD operations.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user, get_db
from src.models.user import User
from src.schemas.todo import (
    TodoCreate,
    TodoUpdate,
    TodoResponse,
    TodoFilterParams,
    TodoBulkUpdate,
    TodoBulkUpdateResponse,
    TodoReorderRequest,
)
from src.schemas.common import PaginationParams, PaginatedResponse
from src.services.todo_service import TodoService
from src.core.error_responses import handle_service_error

router = APIRouter(prefix="/api/v1/todos", tags=["todos"])


@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new todo",
)
async def create_todo(
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new todo for the authenticated user.

    Parameters
    ----------
    todo_data : TodoCreate
        Todo creation data
    current_user : User
        Authenticated user
    db : AsyncSession
        Database session

    Returns
    -------
    TodoResponse
        Created todo
    """
    try:
        service = TodoService(db)
        todo = await service.create_todo(current_user.id, todo_data)
        return todo
    except Exception as e:
        return handle_service_error(e)


@router.get(
    "",
    response_model=PaginatedResponse[TodoResponse],
    summary="List todos with filtering and pagination",
)
async def list_todos(
    filters: TodoFilterParams = Depends(),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List todos with filtering, sorting, and pagination.

    Query parameters available:
    - status: Filter by status
    - priority: Filter by priority
    - tag: Filter by tag name
    - search: Search in title and description
    - sort_by: Field to sort by
    - sort_order: asc or desc
    - page: Page number
    - page_size: Items per page

    Parameters
    ----------
    filters : TodoFilterParams
        Filtering criteria
    pagination : PaginationParams
        Pagination parameters
    current_user : User
        Authenticated user
    db : AsyncSession
        Database session

    Returns
    -------
    PaginatedResponse[TodoResponse]
        Paginated list of todos
    """
    try:
        service = TodoService(db)
        todos, total = await service.list_todos(current_user.id, filters, pagination)

        pages = (total + pagination.page_size - 1) // pagination.page_size

        return PaginatedResponse(
            items=todos,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=pages,
        )
    except Exception as e:
        return handle_service_error(e)


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Get a specific todo by ID",
)
async def get_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific todo by ID.

    User must be the owner or assigned to the todo.

    Parameters
    ----------
    todo_id : UUID
        ID of the todo
    current_user : User
        Authenticated user
    db : AsyncSession
        Database session

    Returns
    -------
    TodoResponse
        Todo object
    """
    try:
        service = TodoService(db)
        todo = await service.get_todo(todo_id, current_user.id)
        return todo
    except Exception as e:
        return handle_service_error(e)


@router.patch(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Update a todo",
)
async def update_todo(
    todo_id: UUID,
    updates: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a todo.

    Only the owner can update the todo.
    All fields are optional for partial updates.

    Parameters
    ----------
    todo_id : UUID
        ID of the todo to update
    updates : TodoUpdate
        Fields to update
    current_user : User
        Authenticated user
    db : AsyncSession
        Database session

    Returns
    -------
    TodoResponse
        Updated todo
    """
    try:
        service = TodoService(db)
        todo = await service.update_todo(todo_id, current_user.id, updates)
        return todo
    except Exception as e:
        return handle_service_error(e)


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a todo",
)
async def delete_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a todo.

    Only the owner can delete the todo.

    Parameters
    ----------
    todo_id : UUID
        ID of the todo to delete
    current_user : User
        Authenticated user
    db : AsyncSession
        Database session
    """
    try:
        service = TodoService(db)
        await service.delete_todo(todo_id, current_user.id)
    except Exception as e:
        return handle_service_error(e)


@router.patch(
    "/bulk",
    response_model=TodoBulkUpdateResponse,
    summary="Bulk update multiple todos",
)
async def bulk_update_todos(
    bulk_data: TodoBulkUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update multiple todos at once.

    User must own all specified todos.

    Parameters
    ----------
    bulk_data : TodoBulkUpdate
        Todo IDs and updates to apply
    current_user : User
        Authenticated user
    db : AsyncSession
        Database session

    Returns
    -------
    TodoBulkUpdateResponse
        Updated todos and count
    """
    try:
        service = TodoService(db)
        todos = await service.bulk_update_todos(
            bulk_data.todo_ids, current_user.id, bulk_data.updates
        )

        return TodoBulkUpdateResponse(
            updated_count=len(todos),
            todos=todos,
        )
    except Exception as e:
        return handle_service_error(e)


@router.post(
    "/reorder",
    status_code=status.HTTP_200_OK,
    summary="Reorder todos",
)
async def reorder_todos(
    reorder_data: TodoReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reorder todos by specifying their new order.

    User must own all specified todos.

    Parameters
    ----------
    reorder_data : TodoReorderRequest
        Ordered list of todo IDs
    current_user : User
        Authenticated user
    db : AsyncSession
        Database session

    Returns
    -------
    dict
        Success message
    """
    try:
        service = TodoService(db)
        await service.reorder_todos(reorder_data.todo_ids, current_user.id)
        return {"message": "Todos reordered successfully"}
    except Exception as e:
        return handle_service_error(e)
```

---

## Database Migrations

### Initial Migration (Alembic)

```python
"""
Create users, todos, tags, and todo_tags tables

Revision ID: 001_initial
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])

    # Create todos table
    op.create_table(
        'todos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('priority', sa.String(20), default='medium', nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('position', sa.Integer, default=0, nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_to_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
        sa.CheckConstraint("status IN ('pending', 'in_progress', 'completed')", name='valid_status'),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name='valid_priority'),
    )
    op.create_index('idx_todos_owner_id', 'todos', ['owner_id'])
    op.create_index('idx_todos_status', 'todos', ['status'])
    op.create_index('idx_todos_due_date', 'todos', ['due_date'])
    op.create_index('idx_todos_owner_status', 'todos', ['owner_id', 'status'])

    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('color', sa.String(7)),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('name', 'user_id', name='unique_tag_per_user'),
    )
    op.create_index('idx_tags_user_id', 'tags', ['user_id'])

    # Create todo_tags junction table
    op.create_table(
        'todo_tags',
        sa.Column('todo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['todo_id'], ['todos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('todo_id', 'tag_id'),
    )


def downgrade():
    op.drop_table('todo_tags')
    op.drop_table('tags')
    op.drop_table('todos')
    op.drop_table('users')
```

---

## Testing Strategy

### Unit Tests

**Test Coverage:**
- ✅ Todo model validation
- ✅ Service layer business logic (mocked DB)
- ✅ Schema validation and serialization
- ✅ Error handling in service layer

**Example Test (`tests/unit/test_todo_service.py`):**

```python
"""
Unit tests for TodoService.

Tests business logic with mocked database operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.services.todo_service import TodoService
from src.schemas.todo import TodoCreate, TodoStatus, TodoPriority
from src.models.todo import Todo


@pytest.mark.unit
class TestTodoService:
    """Test suite for TodoService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create TodoService with mocked DB"""
        return TodoService(mock_db)

    @pytest.mark.asyncio
    async def test_create_todo_success(self, service, mock_db):
        """Test successful todo creation"""
        # Arrange
        user_id = uuid4()
        todo_data = TodoCreate(
            title="Test Todo",
            description="Test description",
            status=TodoStatus.PENDING,
            priority=TodoPriority.HIGH,
        )

        # Act
        todo = await service.create_todo(user_id, todo_data)

        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called
        assert todo.title == "Test Todo"
        assert todo.owner_id == user_id
```

### Integration Tests

**Test Coverage:**
- ✅ End-to-end API endpoint testing
- ✅ Database transactions
- ✅ Authentication flow
- ✅ Error responses

**Example Test (`tests/integration/test_todo_api.py`):**

```python
"""
Integration tests for Todo API endpoints.

Tests API with real database operations.
"""

import pytest
from httpx import AsyncClient
from fastapi import status

from src.main import app
from tests.conftest import test_user, auth_headers


@pytest.mark.integration
@pytest.mark.asyncio
class TestTodoAPI:
    """Test suite for Todo API endpoints"""

    async def test_create_todo_success(self, client: AsyncClient, auth_headers):
        """Test POST /api/v1/todos creates a todo"""
        # Arrange
        todo_data = {
            "title": "Test Todo",
            "description": "Test description",
            "priority": "high",
        }

        # Act
        response = await client.post(
            "/api/v1/todos",
            json=todo_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Test Todo"
        assert data["priority"] == "high"
        assert "id" in data

    async def test_list_todos_with_pagination(self, client: AsyncClient, auth_headers):
        """Test GET /api/v1/todos returns paginated results"""
        # Act
        response = await client.get(
            "/api/v1/todos?page=1&page_size=10",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
```

---

## Implementation Checklist

### Phase 1: Data Layer (Models)
- [ ] Create `src/models/base.py` with TimestampMixin and UUIDMixin
- [ ] Create `src/models/user.py` with User model
- [ ] Create `src/models/todo.py` with Todo model
- [ ] Create `src/models/tag.py` with Tag model and todo_tags junction table
- [ ] Write unit tests for models
- [ ] Create Alembic migration for initial schema

### Phase 2: Schema Layer (Pydantic)
- [ ] Create `src/schemas/common.py` with pagination schemas
- [ ] Create `src/schemas/todo.py` with all todo schemas
- [ ] Create `src/schemas/tag.py` with tag schemas
- [ ] Write unit tests for schema validation

### Phase 3: Service Layer (Business Logic)
- [ ] Create `src/services/todo_service.py` with TodoService
- [ ] Implement create_todo method
- [ ] Implement get_todo method
- [ ] Implement list_todos method with filters
- [ ] Implement update_todo method
- [ ] Implement delete_todo method
- [ ] Implement bulk_update_todos method
- [ ] Implement reorder_todos method
- [ ] Write unit tests for service layer (80%+ coverage)

### Phase 4: API Layer (Routes)
- [ ] Create `src/routers/todos.py` with FastAPI router
- [ ] Implement POST /api/v1/todos endpoint
- [ ] Implement GET /api/v1/todos endpoint with filters
- [ ] Implement GET /api/v1/todos/{todo_id} endpoint
- [ ] Implement PATCH /api/v1/todos/{todo_id} endpoint
- [ ] Implement DELETE /api/v1/todos/{todo_id} endpoint
- [ ] Implement PATCH /api/v1/todos/bulk endpoint
- [ ] Implement POST /api/v1/todos/reorder endpoint
- [ ] Write integration tests for all endpoints

### Phase 5: Integration & Testing
- [ ] Set up test database configuration
- [ ] Create test fixtures for users and todos
- [ ] Run all unit tests (target: 80%+ coverage)
- [ ] Run all integration tests
- [ ] Fix any failing tests
- [ ] Run mypy type checking
- [ ] Update documentation

### Phase 6: Documentation
- [ ] Document API endpoints in OpenAPI/Swagger
- [ ] Create usage examples
- [ ] Document error responses
- [ ] Update README with setup instructions

---

## Summary

This design provides a complete implementation plan for TODO CRUD operations with:

✅ **Complete Data Models**: SQLAlchemy models with proper relationships, constraints, and indexes
✅ **Type-Safe Schemas**: Pydantic schemas for request/response validation
✅ **Business Logic**: Service layer separating concerns from API routes
✅ **RESTful API**: FastAPI routes following REST principles
✅ **Error Handling**: Integration with Marcus Error Framework
✅ **Testing Strategy**: Unit and integration tests for 80%+ coverage
✅ **Database Migrations**: Alembic migration scripts
✅ **Documentation**: Comprehensive docstrings and API documentation

The implementation follows best practices including:
- Separation of concerns (Models, Schemas, Services, Routes)
- Type safety throughout
- Proper error handling with Marcus Error Framework
- Comprehensive testing
- Database optimization with indexes
- Authorization checks for all operations

This design is ready for implementation and can be built incrementally following the checklist phases.
