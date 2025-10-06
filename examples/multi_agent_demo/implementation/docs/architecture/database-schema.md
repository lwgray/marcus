# Task Management API - Database Schema Documentation

## Overview

This document describes the database schema for the Task Management API, including all tables, relationships, and constraints.

## Entity Relationship Diagram (ERD)

```
┌─────────────────┐         ┌─────────────────┐
│     User        │         │    Project      │
├─────────────────┤         ├─────────────────┤
│ PK id           │1───────*│ PK id           │
│    email        │  owns   │    name         │
│    username     │         │    description  │
│    hashed_pwd   │         │ FK owner_id     │
│    full_name    │         │    is_active    │
│    is_active    │         │    created_at   │
│    created_at   │         │    updated_at   │
│    updated_at   │         └─────────────────┘
└─────────────────┘                  │
        │                            │
        │ assigns                    │
        │                            │ contains
        │                            │
        │                            *
        │                   ┌─────────────────┐
        └──────────────────*│     Task        │
          assigned to       ├─────────────────┤
                            │ PK id           │
                            │    title        │
                            │    description  │
                            │    status       │
                            │    priority     │
                            │ FK project_id   │
                            │ FK assignee_id  │
                            │    due_date     │
                            │    created_at   │
                            │    updated_at   │
                            │    completed_at │
                            └─────────────────┘
                                     │
                                     │ has
                                     │
                                     *
┌─────────────────┐         ┌─────────────────┐
│     User        │         │    Comment      │
│  (see above)    │1───────*├─────────────────┤
│                 │ authors │ PK id           │
└─────────────────┘         │    content      │
                            │ FK task_id      │
                            │ FK author_id    │
                            │    created_at   │
                            │    updated_at   │
                            └─────────────────┘
```

## Tables

### User Table

Stores authenticated user information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, AUTO INCREMENT | Unique user identifier |
| email | String(255) | UNIQUE, NOT NULL, INDEX | User email for authentication |
| username | String(100) | UNIQUE, NOT NULL, INDEX | Unique username |
| hashed_password | String(255) | NOT NULL | Bcrypt hashed password |
| full_name | String(255) | NULLABLE | User's full name |
| is_active | Boolean | NOT NULL, DEFAULT TRUE | Account active status |
| created_at | DateTime | NOT NULL, DEFAULT NOW | Account creation timestamp |
| updated_at | DateTime | NOT NULL, DEFAULT NOW, AUTO UPDATE | Last update timestamp |

**Indexes:**
- `ix_users_email` on email
- `ix_users_username` on username

### Project Table

Stores project/workspace information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, AUTO INCREMENT | Unique project identifier |
| name | String(255) | NOT NULL, INDEX | Project name |
| description | Text | NULLABLE | Project description |
| owner_id | Integer | FOREIGN KEY (users.id), NOT NULL, CASCADE DELETE | Project owner |
| is_active | Boolean | NOT NULL, DEFAULT TRUE | Project active status |
| created_at | DateTime | NOT NULL, DEFAULT NOW | Project creation timestamp |
| updated_at | DateTime | NOT NULL, DEFAULT NOW, AUTO UPDATE | Last update timestamp |

**Indexes:**
- `ix_projects_name` on name

**Foreign Keys:**
- `owner_id` → `users.id` (ON DELETE CASCADE)

### Task Table

Stores individual task/work item information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, AUTO INCREMENT | Unique task identifier |
| title | String(255) | NOT NULL, INDEX | Task title |
| description | Text | NULLABLE | Detailed task description |
| status | Enum(TaskStatus) | NOT NULL, DEFAULT 'todo', INDEX | Task status (todo, in_progress, done, blocked) |
| priority | Enum(TaskPriority) | NOT NULL, DEFAULT 'medium', INDEX | Task priority (low, medium, high, urgent) |
| project_id | Integer | FOREIGN KEY (projects.id), NOT NULL, CASCADE DELETE | Parent project |
| assignee_id | Integer | FOREIGN KEY (users.id), NULLABLE, SET NULL | Assigned user |
| due_date | DateTime | NULLABLE | Task due date |
| created_at | DateTime | NOT NULL, DEFAULT NOW | Task creation timestamp |
| updated_at | DateTime | NOT NULL, DEFAULT NOW, AUTO UPDATE | Last update timestamp |
| completed_at | DateTime | NULLABLE | Task completion timestamp |

**Indexes:**
- `ix_tasks_title` on title
- `ix_tasks_status` on status
- `ix_tasks_priority` on priority

**Foreign Keys:**
- `project_id` → `projects.id` (ON DELETE CASCADE)
- `assignee_id` → `users.id` (ON DELETE SET NULL)

**Enums:**
- TaskStatus: `todo`, `in_progress`, `done`, `blocked`
- TaskPriority: `low`, `medium`, `high`, `urgent`

### Comment Table

Stores task comments and discussions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, AUTO INCREMENT | Unique comment identifier |
| content | Text | NOT NULL | Comment text content |
| task_id | Integer | FOREIGN KEY (tasks.id), NOT NULL, CASCADE DELETE | Parent task |
| author_id | Integer | FOREIGN KEY (users.id), NOT NULL, CASCADE DELETE | Comment author |
| created_at | DateTime | NOT NULL, DEFAULT NOW | Comment creation timestamp |
| updated_at | DateTime | NOT NULL, DEFAULT NOW, AUTO UPDATE | Last update timestamp |

**Foreign Keys:**
- `task_id` → `tasks.id` (ON DELETE CASCADE)
- `author_id` → `users.id` (ON DELETE CASCADE)

## Relationships

### One-to-Many Relationships

1. **User → Projects** (one user owns many projects)
   - User.projects ↔ Project.owner
   - Cascade: DELETE (deleting user deletes their projects)

2. **User → Tasks** (one user assigned to many tasks)
   - User.tasks ↔ Task.assignee
   - Cascade: SET NULL (deleting user unassigns their tasks)

3. **User → Comments** (one user authors many comments)
   - User.comments ↔ Comment.author
   - Cascade: DELETE (deleting user deletes their comments)

4. **Project → Tasks** (one project contains many tasks)
   - Project.tasks ↔ Task.project
   - Cascade: DELETE (deleting project deletes its tasks)

5. **Task → Comments** (one task has many comments)
   - Task.comments ↔ Comment.task
   - Cascade: DELETE (deleting task deletes its comments)

## Cascade Behavior

| Relationship | On Delete | Reasoning |
|--------------|-----------|-----------|
| User → Projects | CASCADE | Projects are owned by users; orphaned projects should be deleted |
| User → Tasks | SET NULL | Tasks can exist without assignees; preserve task history |
| User → Comments | CASCADE | Comments are user content; delete with user |
| Project → Tasks | CASCADE | Tasks belong to projects; no orphaned tasks |
| Task → Comments | CASCADE | Comments are task-specific; delete with task |

## Indexing Strategy

Indexes are created on:
- **Primary Keys**: All id columns (automatic)
- **Foreign Keys**: Improves join performance
- **Lookup Fields**: email, username (for authentication)
- **Filter Fields**: status, priority (for task queries)
- **Search Fields**: project.name, task.title (for search)

## Data Integrity

1. **NOT NULL Constraints**: All foreign keys (except assignee_id) are required
2. **UNIQUE Constraints**: email and username prevent duplicates
3. **CASCADE DELETE**: Maintains referential integrity
4. **DEFAULT VALUES**: Sensible defaults for status, priority, timestamps
5. **Enum Validation**: Status and priority use predefined values

## Migration Strategy

1. Create tables in order: User → Project → Task → Comment
2. Add indexes after table creation
3. Add foreign key constraints last
4. Use Alembic for version-controlled migrations

## Performance Considerations

1. **Indexes**: Created on frequently queried columns
2. **Cascade**: Efficient deletion of related records
3. **Enum Types**: Faster than string comparisons
4. **Timestamp Indexes**: For date-based queries
5. **Soft Deletes**: Consider is_active flag instead of hard deletes for audit trail
