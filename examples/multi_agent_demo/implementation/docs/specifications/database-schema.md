# Database Schema Specification

## Overview

This document specifies the database schema for the Task Management API. The schema supports user authentication, project management, task tracking, and commenting functionality.

## Technology Stack

- **ORM**: SQLAlchemy 2.0+
- **Database**: PostgreSQL (production) / SQLite (development)
- **Migration Tool**: Alembic (recommended for production)

## Entity Relationship Diagram

```
┌─────────────┐
│    User     │
├─────────────┤
│ id (PK)     │
│ email       │◄───────┐
│ hashed_pwd  │        │
│ full_name   │        │
│ is_active   │        │
│ is_superuser│        │
│ created_at  │        │
│ updated_at  │        │
└─────────────┘        │
       │               │
       │ owner_id (FK) │
       ▼               │
┌─────────────┐        │
│   Project   │        │
├─────────────┤        │
│ id (PK)     │        │
│ name        │        │
│ description │        │
│ owner_id (FK)        │
│ created_at  │        │
│ updated_at  │        │
└─────────────┘        │
       │               │
       │ project_id(FK)│
       ▼               │
┌─────────────┐        │
│    Task     │        │
├─────────────┤        │
│ id (PK)     │        │
│ title       │        │
│ description │        │
│ status      │        │
│ priority    │        │
│ project_id(FK)       │
│ assignee_id(FK)──────┘
│ created_at  │
│ updated_at  │
└─────────────┘
       │
       │ task_id (FK)
       ▼
┌─────────────┐
│   Comment   │
├─────────────┤
│ id (PK)     │
│ content     │
│ task_id (FK)│
│ author_id(FK)────────┐
│ created_at  │        │
│ updated_at  │        │
└─────────────┘        │
                       │
                       └─► User.id
```

## Table Specifications

### Users Table

**Purpose**: Stores user authentication and profile information.

| Column         | Type         | Constraints                    | Description                      |
|----------------|--------------|--------------------------------|----------------------------------|
| id             | INTEGER      | PRIMARY KEY, AUTO_INCREMENT    | Unique user identifier           |
| email          | VARCHAR(255) | UNIQUE, NOT NULL, INDEX        | User's email address             |
| hashed_password| VARCHAR(255) | NOT NULL                       | Bcrypt hashed password           |
| full_name      | VARCHAR(255) | NULLABLE                       | User's full name                 |
| is_active      | BOOLEAN      | NOT NULL, DEFAULT TRUE         | Account activation status        |
| is_superuser   | BOOLEAN      | NOT NULL, DEFAULT FALSE        | Superuser privileges flag        |
| created_at     | DATETIME     | NOT NULL, DEFAULT UTC NOW      | Account creation timestamp       |
| updated_at     | DATETIME     | NOT NULL, DEFAULT UTC NOW      | Last update timestamp            |

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE INDEX on `email`

**Cascade Rules**:
- ON DELETE: CASCADE to projects, tasks, and comments

---

### Projects Table

**Purpose**: Organizes tasks into logical groupings owned by users.

| Column      | Type         | Constraints                        | Description                      |
|-------------|--------------|------------------------------------|---------------------------------|
| id          | INTEGER      | PRIMARY KEY, AUTO_INCREMENT        | Unique project identifier        |
| name        | VARCHAR(255) | NOT NULL, INDEX                    | Project name                     |
| description | TEXT         | NULLABLE                           | Project description              |
| owner_id    | INTEGER      | FOREIGN KEY(users.id), NOT NULL    | Project owner reference          |
| created_at  | DATETIME     | NOT NULL, DEFAULT UTC NOW          | Project creation timestamp       |
| updated_at  | DATETIME     | NOT NULL, DEFAULT UTC NOW          | Last update timestamp            |

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `name`
- INDEX on `owner_id`

**Foreign Keys**:
- `owner_id` → `users.id` (ON DELETE CASCADE)

**Cascade Rules**:
- ON DELETE: CASCADE to tasks

---

### Tasks Table

**Purpose**: Represents individual work items within projects.

| Column      | Type                | Constraints                        | Description                      |
|-------------|---------------------|-----------------------------------|----------------------------------|
| id          | INTEGER             | PRIMARY KEY, AUTO_INCREMENT        | Unique task identifier           |
| title       | VARCHAR(255)        | NOT NULL, INDEX                    | Task title                       |
| description | TEXT                | NULLABLE                           | Detailed task description        |
| status      | ENUM                | NOT NULL, DEFAULT 'todo', INDEX    | Task status                      |
| priority    | ENUM                | NOT NULL, DEFAULT 'medium', INDEX  | Task priority                    |
| project_id  | INTEGER             | FOREIGN KEY(projects.id), NOT NULL | Parent project reference         |
| assignee_id | INTEGER             | FOREIGN KEY(users.id), NULLABLE    | Assigned user reference          |
| created_at  | DATETIME            | NOT NULL, DEFAULT UTC NOW          | Task creation timestamp          |
| updated_at  | DATETIME            | NOT NULL, DEFAULT UTC NOW          | Last update timestamp            |

**Enums**:
- `status`: 'todo', 'in_progress', 'completed', 'cancelled'
- `priority`: 'low', 'medium', 'high', 'urgent'

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `title`
- INDEX on `status`
- INDEX on `priority`
- INDEX on `project_id`
- INDEX on `assignee_id`

**Foreign Keys**:
- `project_id` → `projects.id` (ON DELETE CASCADE)
- `assignee_id` → `users.id` (ON DELETE CASCADE)

**Cascade Rules**:
- ON DELETE: CASCADE to comments

---

### Comments Table

**Purpose**: Enables discussion and collaboration on tasks.

| Column      | Type         | Constraints                        | Description                      |
|-------------|--------------|-----------------------------------|----------------------------------|
| id          | INTEGER      | PRIMARY KEY, AUTO_INCREMENT        | Unique comment identifier        |
| content     | TEXT         | NOT NULL                           | Comment text                     |
| task_id     | INTEGER      | FOREIGN KEY(tasks.id), NOT NULL    | Parent task reference            |
| author_id   | INTEGER      | FOREIGN KEY(users.id), NOT NULL    | Comment author reference         |
| created_at  | DATETIME     | NOT NULL, DEFAULT UTC NOW          | Comment creation timestamp       |
| updated_at  | DATETIME     | NOT NULL, DEFAULT UTC NOW          | Last update timestamp            |

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `task_id`
- INDEX on `author_id`

**Foreign Keys**:
- `task_id` → `tasks.id` (ON DELETE CASCADE)
- `author_id` → `users.id` (ON DELETE CASCADE)

---

## Cascade Behavior

The schema implements comprehensive cascade delete rules to maintain referential integrity:

1. **User Deletion**:
   - Deletes all projects owned by the user
   - Deletes all tasks assigned to the user
   - Deletes all comments authored by the user

2. **Project Deletion**:
   - Deletes all tasks in the project
   - By extension, deletes all comments on those tasks

3. **Task Deletion**:
   - Deletes all comments on the task

## Performance Considerations

### Indexing Strategy

1. **Primary Keys**: All tables have auto-incrementing integer primary keys for optimal join performance
2. **Foreign Keys**: All foreign key columns are indexed for efficient joins
3. **Search Fields**: Email, task title, status, and priority are indexed for fast lookups
4. **Composite Indexes**: Consider adding composite indexes for common query patterns:
   - `(project_id, status)` on tasks
   - `(assignee_id, status)` on tasks

### Query Optimization

- Use `pool_pre_ping=True` to handle stale connections
- Configure connection pooling (pool_size=5, max_overflow=10)
- Use `joinedload` or `selectinload` for eager loading relationships
- Implement pagination for list endpoints

## Security Considerations

1. **Password Storage**: Always use bcrypt for password hashing (cost factor: 12)
2. **Email Validation**: Enforce email format validation at application layer
3. **Soft Deletes**: Consider implementing soft deletes for users to preserve data integrity
4. **Audit Trail**: The `created_at` and `updated_at` fields provide basic audit capability

## Migration Strategy

For production deployments:

1. Use Alembic for schema migrations
2. Never modify models directly in production
3. Always create migration scripts for schema changes
4. Test migrations on a copy of production data
5. Implement rollback procedures

## Example Queries

### Get all tasks for a user with project info
```python
from sqlalchemy.orm import joinedload

tasks = db.query(Task)\
    .filter(Task.assignee_id == user_id)\
    .options(joinedload(Task.project))\
    .all()
```

### Get project with all tasks and comments
```python
from sqlalchemy.orm import joinedload, selectinload

project = db.query(Project)\
    .filter(Project.id == project_id)\
    .options(
        selectinload(Project.tasks).selectinload(Task.comments)
    )\
    .first()
```

### Count tasks by status for a project
```python
from sqlalchemy import func

status_counts = db.query(
    Task.status,
    func.count(Task.id)
)\
.filter(Task.project_id == project_id)\
.group_by(Task.status)\
.all()
```

## Future Enhancements

Potential schema extensions for future versions:

1. **Task Tags**: Many-to-many relationship for flexible categorization
2. **Task Dependencies**: Self-referential relationship for task ordering
3. **File Attachments**: Table for storing file metadata
4. **Activity Log**: Comprehensive audit trail of all changes
5. **Notifications**: User notification preferences and history
6. **Teams**: Group users into teams with shared projects
