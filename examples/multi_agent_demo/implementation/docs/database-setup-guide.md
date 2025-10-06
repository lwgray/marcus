# Database Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install sqlalchemy psycopg2-binary  # For PostgreSQL
# OR
pip install sqlalchemy  # For SQLite (no additional driver needed)
```

### 2. Configure Database URL

Set the `DATABASE_URL` environment variable:

```bash
# SQLite (Development)
export DATABASE_URL="sqlite:///./task_management.db"

# PostgreSQL (Production)
export DATABASE_URL="postgresql://user:password@localhost/task_management"  # pragma: allowlist secret

# MySQL (Production)
export DATABASE_URL="mysql+pymysql://user:password@localhost/task_management"  # pragma: allowlist secret
```

### 3. Initialize Database

```python
from database import init_db

# Create all tables
init_db()
```

Or run directly:
```bash
python database.py
```

## Using the Database in Your Application

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, Project, Task

app = FastAPI()

@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.post("/users")
def create_user(email: str, username: str, password: str, db: Session = Depends(get_db)):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(password)

    user = User(
        email=email,
        username=username,
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

### Working with Relationships

```python
# Create a user with a project
user = User(email="user@example.com", username="user1", hashed_password="...")
db.add(user)
db.commit()

project = Project(name="My Project", owner_id=user.id)
db.add(project)
db.commit()

# Access relationships
print(user.projects)  # List of projects owned by user
print(project.owner)  # User who owns the project

# Create a task
task = Task(
    title="Implement feature",
    project_id=project.id,
    assignee_id=user.id,
    status=TaskStatus.TODO,
    priority=TaskPriority.HIGH
)
db.add(task)
db.commit()

# Query with joins
tasks_with_project = db.query(Task).join(Project).filter(
    Project.owner_id == user.id
).all()
```

## Model Usage Examples

### User Model
```python
from models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create user
user = User(
    email="john@example.com",
    username="johndoe",
    hashed_password=pwd_context.hash("secret"),
    full_name="John Doe"
)
db.add(user)
db.commit()

# Verify password
if pwd_context.verify(plain_password, user.hashed_password):
    print("Password correct")
```

### Project Model
```python
from models import Project

# Create project
project = Project(
    name="Task Management System",
    description="A REST API for managing tasks",
    owner_id=user.id
)
db.add(project)
db.commit()

# Deactivate project (soft delete)
project.is_active = False
db.commit()
```

### Task Model
```python
from models import Task, TaskStatus, TaskPriority
from datetime import datetime, timedelta

# Create task
task = Task(
    title="Design database schema",
    description="Create SQLAlchemy models",
    project_id=project.id,
    assignee_id=user.id,
    status=TaskStatus.IN_PROGRESS,
    priority=TaskPriority.HIGH,
    due_date=datetime.utcnow() + timedelta(days=7)
)
db.add(task)
db.commit()

# Complete task
task.status = TaskStatus.DONE
task.completed_at = datetime.utcnow()
db.commit()

# Query tasks by status
todo_tasks = db.query(Task).filter(Task.status == TaskStatus.TODO).all()
```

### Comment Model
```python
from models import Comment

# Add comment to task
comment = Comment(
    content="This looks good, please proceed",
    task_id=task.id,
    author_id=user.id
)
db.add(comment)
db.commit()

# Get all comments for a task
task_comments = db.query(Comment).filter(Comment.task_id == task.id).all()
```

## Advanced Queries

### Filtering and Pagination
```python
# Get high priority tasks
high_priority = db.query(Task).filter(
    Task.priority == TaskPriority.HIGH
).all()

# Pagination
page = 1
page_size = 10
tasks = db.query(Task).offset((page - 1) * page_size).limit(page_size).all()

# Sorting
recent_tasks = db.query(Task).order_by(Task.created_at.desc()).all()
```

### Aggregations
```python
from sqlalchemy import func

# Count tasks by status
task_counts = db.query(
    Task.status,
    func.count(Task.id)
).group_by(Task.status).all()

# Get projects with task counts
project_stats = db.query(
    Project.name,
    func.count(Task.id).label('task_count')
).join(Task).group_by(Project.id).all()
```

### Complex Joins
```python
# Get all tasks with project and assignee info
results = db.query(Task, Project, User).join(
    Project, Task.project_id == Project.id
).join(
    User, Task.assignee_id == User.id
).all()

for task, project, user in results:
    print(f"{task.title} in {project.name} assigned to {user.username}")
```

## Database Migrations with Alembic

### Initial Setup
```bash
pip install alembic
alembic init alembic
```

### Configure alembic.ini
```ini
sqlalchemy.url = postgresql://user:password@localhost/task_management  # pragma: allowlist secret
```

### Create Migration
```bash
# Auto-generate migration from models
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Production Considerations

### Connection Pooling
```python
# Adjust pool settings for production
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Number of connections to keep
    max_overflow=40,       # Additional connections under load
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

### Performance Tips
1. Use indexes on frequently queried columns (already configured)
2. Use `joinedload()` or `selectinload()` to avoid N+1 queries
3. Use pagination for large result sets
4. Consider read replicas for read-heavy workloads
5. Use connection pooling (configured by default)

### Security
1. Always use parameterized queries (SQLAlchemy does this automatically)
2. Never store plain text passwords (use bcrypt via passlib)
3. Use environment variables for credentials
4. Enable SSL for database connections in production
5. Implement row-level security if needed

## Troubleshooting

### Common Issues

**SQLite: "database is locked"**
- Use `timeout` parameter: `create_engine(..., connect_args={"timeout": 30})`

**PostgreSQL: "too many clients"**
- Reduce `pool_size` and `max_overflow`
- Check for connection leaks

**Migrations: "Target database is not up to date"**
- Run `alembic upgrade head`
- Check alembic_version table

## Testing

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

@pytest.fixture
def db():
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()

def test_create_user(db):
    user = User(email="test@example.com", username="test", hashed_password="hash")
    db.add(user)
    db.commit()

    assert db.query(User).count() == 1
```
