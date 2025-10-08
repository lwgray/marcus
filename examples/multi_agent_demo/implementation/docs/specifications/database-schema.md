# Database Schema Documentation

## Overview

This document describes the database schema for the Task Management API. The schema uses PostgreSQL with SQLAlchemy ORM and Alembic for migrations.

## Entity Relationship Diagram

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ PK  id          │
│ UQ  username    │
│ UQ  email       │
│     password_hash│
│     created_at  │
│     updated_at  │
└─────────────────┘
        │
        │ 1:N (created_by)
        │
        ▼
┌─────────────────┐
│    projects     │
├─────────────────┤
│ PK  id          │
│     name        │
│     description │
│     start_date  │
│     end_date    │
│ FK  created_by  │──┐ CASCADE
│     created_at  │  │
│     updated_at  │  │
└─────────────────┘  │
        │            │
        │ 1:N        │
        │            │
        ▼            │
┌─────────────────┐  │
│      tasks      │  │
├─────────────────┤  │
│ PK  id          │  │
│     title       │  │
│     description │  │
│     due_date    │  │
│     status      │  │
│     priority    │  │
│ FK  project_id  │──┘ CASCADE
│ FK  assigned_to │──┐ CASCADE
│ FK  created_by  │──┼─ SET NULL
│     created_at  │  │
│     updated_at  │  │
└─────────────────┘  │
        │            │
        │ 1:N        │
        │            │
        ▼            │
┌─────────────────┐  │
│    comments     │  │
├─────────────────┤  │
│ PK  id          │  │
│     text        │  │
│ FK  user_id     │──┘ CASCADE
│ FK  task_id     │──┐ CASCADE
│     created_at  │  │
│     updated_at  │  │
└─────────────────┘  │
                     │
                     └─ (from tasks table)
```

## Tables

### users

Stores user authentication and profile information.

**Columns:**
- `id` (Integer, PK, Auto-increment): Unique user identifier
- `username` (String(80), Unique, Not Null): Username for login
- `email` (String(120), Unique, Not Null): User email address
- `password_hash` (String(255), Not Null): Bcrypt hashed password
- `created_at` (DateTime, Not Null, Default: now()): Record creation timestamp (UTC)
- `updated_at` (DateTime, Not Null, Default: now()): Record update timestamp (UTC)

**Indexes:**
- `ix_users_username`: Single column index on username
- `ix_users_email`: Single column index on email
- `ix_users_username_email`: Composite index on (username, email)

**Relationships:**
- One-to-Many with `projects` (as creator)
- One-to-Many with `tasks` (as assignee)
- One-to-Many with `tasks` (as creator)
- One-to-Many with `comments` (as author)

### projects

Stores project information and ownership.

**Columns:**
- `id` (Integer, PK, Auto-increment): Unique project identifier
- `name` (String(200), Not Null): Project name
- `description` (Text, Nullable): Detailed project description
- `start_date` (Date, Nullable): Project start date
- `end_date` (Date, Nullable): Project end date
- `created_by` (Integer, FK→users.id, Not Null): User who created the project
- `created_at` (DateTime, Not Null, Default: now()): Record creation timestamp (UTC)
- `updated_at` (DateTime, Not Null, Default: now()): Record update timestamp (UTC)

**Indexes:**
- `ix_projects_name`: Single column index on name
- `ix_projects_created_by`: Single column index on created_by
- `ix_projects_created_by_name`: Composite index on (created_by, name)
- `ix_projects_dates`: Composite index on (start_date, end_date)

**Foreign Keys:**
- `created_by` → `users.id` (ON DELETE CASCADE)

**Relationships:**
- Many-to-One with `users` (creator)
- One-to-Many with `tasks`

### tasks

Stores task information, assignments, and tracking.

**Columns:**
- `id` (Integer, PK, Auto-increment): Unique task identifier
- `title` (String(200), Not Null): Task title
- `description` (Text, Nullable): Detailed task description
- `due_date` (Date, Nullable): Task due date
- `status` (String(20), Not Null, Default: 'todo'): Task status (todo, in_progress, in_review, completed, blocked)
- `priority` (String(20), Not Null, Default: 'medium'): Task priority (low, medium, high, critical)
- `project_id` (Integer, FK→projects.id, Not Null): Parent project
- `assigned_to` (Integer, FK→users.id, Nullable): User assigned to task
- `created_by` (Integer, FK→users.id, Nullable): User who created task
- `created_at` (DateTime, Not Null, Default: now()): Record creation timestamp (UTC)
- `updated_at` (DateTime, Not Null, Default: now()): Record update timestamp (UTC)

**Indexes:**
- `ix_tasks_title`: Single column index on title
- `ix_tasks_due_date`: Single column index on due_date
- `ix_tasks_status`: Single column index on status
- `ix_tasks_priority`: Single column index on priority
- `ix_tasks_project_id`: Single column index on project_id
- `ix_tasks_assigned_to`: Single column index on assigned_to
- `ix_tasks_created_by`: Single column index on created_by
- `ix_tasks_project_status`: Composite index on (project_id, status)
- `ix_tasks_assigned_status`: Composite index on (assigned_to, status)
- `ix_tasks_priority_status`: Composite index on (priority, status)
- `ix_tasks_due_date_status`: Composite index on (due_date, status)

**Foreign Keys:**
- `project_id` → `projects.id` (ON DELETE CASCADE)
- `assigned_to` → `users.id` (ON DELETE CASCADE)
- `created_by` → `users.id` (ON DELETE SET NULL)

**Relationships:**
- Many-to-One with `projects`
- Many-to-One with `users` (assignee)
- Many-to-One with `users` (creator)
- One-to-Many with `comments`

**Enumerations:**
- `TaskStatus`: todo, in_progress, in_review, completed, blocked
- `TaskPriority`: low, medium, high, critical

### comments

Stores task comments and discussions.

**Columns:**
- `id` (Integer, PK, Auto-increment): Unique comment identifier
- `text` (Text, Not Null): Comment content
- `user_id` (Integer, FK→users.id, Not Null): User who wrote the comment
- `task_id` (Integer, FK→tasks.id, Not Null): Task this comment belongs to
- `created_at` (DateTime, Not Null, Default: now()): Record creation timestamp (UTC)
- `updated_at` (DateTime, Not Null, Default: now()): Record update timestamp (UTC)

**Indexes:**
- `ix_comments_user_id`: Single column index on user_id
- `ix_comments_task_id`: Single column index on task_id
- `ix_comments_task_created`: Composite index on (task_id, created_at)
- `ix_comments_user_created`: Composite index on (user_id, created_at)

**Foreign Keys:**
- `user_id` → `users.id` (ON DELETE CASCADE)
- `task_id` → `tasks.id` (ON DELETE CASCADE)

**Relationships:**
- Many-to-One with `users` (author)
- Many-to-One with `tasks`

## Cascade Rules

### ON DELETE CASCADE
- Deleting a **user** cascades to:
  - All projects created by that user
  - All tasks assigned to that user
  - All comments written by that user

- Deleting a **project** cascades to:
  - All tasks in that project
  - All comments on those tasks (via task deletion)

- Deleting a **task** cascades to:
  - All comments on that task

### ON DELETE SET NULL
- Deleting a user who created tasks sets `tasks.created_by` to NULL
  - This preserves the task while removing the creator reference

## Migration Information

**Alembic Revision:** 8f03f242faea

**Migration File:** `alembic/versions/8f03f242faea_initial_database_schema_with_user_.py`

### Applying Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# View current version
alembic current

# View migration history
alembic history
```

### Environment Variables

The database URL can be configured via environment variable:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/taskmanagement"
```

Or use the default in `alembic.ini`:
```ini
sqlalchemy.url = postgresql://localhost/taskmanagement
```

## Data Model Design Decisions

1. **UTC Timestamps**: All `created_at` and `updated_at` fields use UTC timezone for consistency across distributed systems.

2. **Password Security**: Passwords are stored as bcrypt hashes (255 chars) to support future algorithm updates.

3. **Cascade Deletes**: Aggressive cascade rules ensure referential integrity while preserving task history by using SET NULL for creator references.

4. **Composite Indexes**: Added for common query patterns:
   - Tasks by project and status
   - Tasks by assignee and status
   - Tasks by priority and status
   - Comments by task ordered by creation time

5. **Enum Types**: Task status and priority use string enums (not native PostgreSQL enums) for easier migration and modification.

6. **Nullable Relationships**: `assigned_to` is nullable to support unassigned tasks, while `created_by` uses SET NULL to preserve historical data.

## Future Considerations

1. **Soft Deletes**: Consider adding `deleted_at` timestamp for soft delete functionality
2. **Audit Trail**: Add audit tables for tracking all changes to critical entities
3. **Team Members**: Add many-to-many relationship for project team members
4. **Task Dependencies**: Add self-referential relationship for task dependencies
5. **File Attachments**: Add table for task/comment file attachments
6. **Activity Log**: Add table for user activity tracking

## Model Files

- `app/models/base.py`: Base model and timestamp mixin
- `app/models/user.py`: User model
- `app/models/project.py`: Project model
- `app/models/task.py`: Task model with enums
- `app/models/comment.py`: Comment model
- `app/models/__init__.py`: Package exports
