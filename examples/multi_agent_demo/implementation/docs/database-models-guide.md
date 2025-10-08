# Database Models Usage Guide

## Overview

This guide shows how to use the SQLAlchemy models in the Task Management API. All models are located in `app/models/` and use declarative base with automatic timestamps.

## Quick Start

### Importing Models

```python
from app.models import Base, User, Project, Task, Comment
from app.models.task import TaskStatus, TaskPriority
```

### Database Connection Setup

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Get database URL from environment or config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/taskmanagement")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables (for development only - use Alembic in production)
Base.metadata.create_all(bind=engine)
```

### Using Sessions

```python
# Create a session
db = SessionLocal()

try:
    # Your database operations here
    user = db.query(User).filter(User.username == "john").first()
    db.commit()
finally:
    db.close()
```

## Creating Records

### Create a User

```python
from app.models.user import User

# Create new user with bcrypt hashed password
new_user = User(
    username="johndoe",
    email="john@example.com",
    password_hash="$2b$12$hashed_password_here"  # Use bcrypt.hashpw()
)

db.add(new_user)
db.commit()
db.refresh(new_user)  # Get the auto-generated ID

print(f"Created user with ID: {new_user.id}")
```

### Create a Project

```python
from app.models.project import Project
from datetime import date

new_project = Project(
    name="Website Redesign",
    description="Complete overhaul of company website",
    start_date=date(2025, 1, 1),
    end_date=date(2025, 6, 30),
    created_by=new_user.id  # Foreign key to user
)

db.add(new_project)
db.commit()
db.refresh(new_project)
```

### Create a Task

```python
from app.models.task import Task, TaskStatus, TaskPriority
from datetime import date

new_task = Task(
    title="Design homepage mockup",
    description="Create responsive homepage design in Figma",
    due_date=date(2025, 1, 15),
    status=TaskStatus.TODO,
    priority=TaskPriority.HIGH,
    project_id=new_project.id,
    assigned_to=new_user.id,
    created_by=new_user.id
)

db.add(new_task)
db.commit()
db.refresh(new_task)
```

### Create a Comment

```python
from app.models.comment import Comment

new_comment = Comment(
    text="I'll start working on this tomorrow.",
    user_id=new_user.id,
    task_id=new_task.id
)

db.add(new_comment)
db.commit()
```

## Querying Records

### Basic Queries

```python
# Get user by ID
user = db.query(User).filter(User.id == 1).first()

# Get user by username
user = db.query(User).filter(User.username == "johndoe").first()

# Get all projects created by a user
projects = db.query(Project).filter(Project.created_by == user.id).all()

# Get tasks with specific status
todo_tasks = db.query(Task).filter(Task.status == TaskStatus.TODO).all()

# Get high priority tasks
high_priority = db.query(Task).filter(Task.priority == TaskPriority.HIGH).all()
```

### Using Relationships

```python
# Access project's tasks (via relationship)
project = db.query(Project).filter(Project.id == 1).first()
project_tasks = project.tasks  # Returns list of Task objects

# Access task's comments
task = db.query(Task).filter(Task.id == 1).first()
task_comments = task.comments  # Returns list of Comment objects

# Access task's assignee
assignee = task.assignee  # Returns User object or None

# Access user's created projects
user = db.query(User).filter(User.id == 1).first()
user_projects = user.created_projects  # Returns list of Project objects
```

### Complex Queries with Joins

```python
from sqlalchemy import and_, or_

# Get all tasks assigned to a user in a specific project
tasks = db.query(Task).filter(
    and_(
        Task.assigned_to == user.id,
        Task.project_id == project.id
    )
).all()

# Get tasks that are either high priority or past due
from datetime import date
tasks = db.query(Task).filter(
    or_(
        Task.priority == TaskPriority.HIGH,
        Task.due_date < date.today()
    )
).all()

# Get tasks with comments, using join
from sqlalchemy.orm import joinedload

tasks_with_comments = db.query(Task).options(
    joinedload(Task.comments)
).filter(Task.project_id == project.id).all()
```

### Filtering by Date

```python
from datetime import date, timedelta

# Tasks due this week
today = date.today()
week_end = today + timedelta(days=7)

tasks_this_week = db.query(Task).filter(
    and_(
        Task.due_date >= today,
        Task.due_date <= week_end
    )
).all()
```

## Updating Records

### Update Task Status

```python
task = db.query(Task).filter(Task.id == 1).first()
task.status = TaskStatus.IN_PROGRESS
db.commit()

# The updated_at timestamp is automatically updated
print(f"Updated at: {task.updated_at}")
```

### Update Multiple Fields

```python
task = db.query(Task).filter(Task.id == 1).first()
task.status = TaskStatus.COMPLETED
task.assigned_to = None  # Unassign task
db.commit()
```

### Bulk Update

```python
# Mark all TODO tasks in a project as IN_PROGRESS
db.query(Task).filter(
    and_(
        Task.project_id == project.id,
        Task.status == TaskStatus.TODO
    )
).update({Task.status: TaskStatus.IN_PROGRESS})
db.commit()
```

## Deleting Records

### Delete a Single Record

```python
# Delete a comment
comment = db.query(Comment).filter(Comment.id == 1).first()
db.delete(comment)
db.commit()
```

### Cascade Delete Effects

```python
# Deleting a project cascades to all its tasks and their comments
project = db.query(Project).filter(Project.id == 1).first()
db.delete(project)  # This will also delete all tasks and comments
db.commit()

# Deleting a user cascades to their assignments and comments
# but preserves tasks they created (sets created_by to NULL)
user = db.query(User).filter(User.id == 1).first()
db.delete(user)
db.commit()
```

## Model Methods

### Convert to Dictionary

```python
user = db.query(User).filter(User.id == 1).first()
user_dict = user.to_dict()
# Returns: {'id': 1, 'username': 'johndoe', 'email': 'john@example.com', ...}
```

### String Representation

```python
user = User(id=1, username="johndoe", email="john@example.com")
print(user)
# Output: <User(id=1, username='johndoe', email='john@example.com')>

task = Task(id=1, title="Build API", status=TaskStatus.TODO, priority=TaskPriority.HIGH)
print(task)
# Output: <Task(id=1, title='Build API', status=todo, priority=high)>
```

## Password Handling

### Hashing Passwords

```python
import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Create user with hashed password
password_hash = hash_password("SecurePassword123!")
user = User(
    username="newuser",
    email="newuser@example.com",
    password_hash=password_hash
)
```

### Verifying Passwords

```python
def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        password.encode('utf-8'),
        password_hash.encode('utf-8')
    )

# Check password during login
user = db.query(User).filter(User.username == "johndoe").first()
if user and verify_password("user_password", user.password_hash):
    print("Login successful")
else:
    print("Invalid credentials")
```

## Common Patterns

### Get or Create

```python
def get_or_create_user(db, username, email, password):
    """Get existing user or create new one."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
```

### Pagination

```python
def get_tasks_paginated(db, page=1, per_page=10):
    """Get paginated list of tasks."""
    offset = (page - 1) * per_page
    tasks = db.query(Task).offset(offset).limit(per_page).all()
    total = db.query(Task).count()
    return {
        'items': tasks,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }
```

### Filtering with Dynamic Conditions

```python
def filter_tasks(db, project_id=None, status=None, assigned_to=None):
    """Filter tasks with optional criteria."""
    query = db.query(Task)

    if project_id:
        query = query.filter(Task.project_id == project_id)
    if status:
        query = query.filter(Task.status == status)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)

    return query.all()
```

## Error Handling

### Handling Unique Constraint Violations

```python
from sqlalchemy.exc import IntegrityError

try:
    new_user = User(
        username="existing_user",  # Already exists
        email="duplicate@example.com",
        password_hash=hash_password("password")
    )
    db.add(new_user)
    db.commit()
except IntegrityError as e:
    db.rollback()
    if "username" in str(e.orig):
        print("Username already exists")
    elif "email" in str(e.orig):
        print("Email already exists")
```

### Handling Foreign Key Violations

```python
try:
    task = Task(
        title="Invalid task",
        project_id=999,  # Non-existent project
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM
    )
    db.add(task)
    db.commit()
except IntegrityError:
    db.rollback()
    print("Invalid project_id or other foreign key violation")
```

## Best Practices

1. **Always use sessions within try/finally blocks** to ensure cleanup
2. **Use relationships instead of manual joins** when possible
3. **Hash passwords with bcrypt** before storing in password_hash field
4. **Use enums (TaskStatus, TaskPriority)** for type safety
5. **Leverage cascade rules** - don't manually delete related records
6. **Use UTC timestamps** - all timestamps are already in UTC
7. **Call db.refresh()** after commit if you need auto-generated values
8. **Use bulk operations** for updating multiple records
9. **Add indexes** for frequently queried fields (already included in models)
10. **Validate data** before committing to catch errors early

## Integration with Flask/FastAPI

### Flask-SQLAlchemy Example

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)

# Import models after db initialization
from app.models import User, Project, Task, Comment

@app.route('/users/<int:user_id>')
def get_user(user_id):
    user = db.session.query(User).get(user_id)
    return user.to_dict()
```

### FastAPI Example

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/{user_id}")
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    return user.to_dict()
```

## Testing

### Using In-Memory SQLite for Tests

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

@pytest.fixture
def test_db():
    """Create in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()

def test_create_user(test_db):
    """Test user creation."""
    user = User(username="test", email="test@example.com", password_hash="hash")
    test_db.add(user)
    test_db.commit()
    assert user.id is not None
```

## Migration Workflow

```bash
# Apply migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "Add new field"

# Rollback one migration
alembic downgrade -1

# View current migration
alembic current
```

## Related Files

- Models: `app/models/` directory
- Migration: `alembic/versions/8f03f242faea_initial_database_schema_with_user_.py`
- Configuration: `alembic.ini` and `alembic/env.py`
- Schema Documentation: `docs/specifications/database-schema.md`
