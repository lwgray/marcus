See: /Users/lwgray/dev/marcus/examples/multi_agent_demo/implementation/database_schema.py

SQLAlchemy database models with full ORM relationships:

## Models:
- **User**: Authentication & user management (email, username, password_hash, role)
- **Project**: Project organization (name, description, owner_id)
- **ProjectMember**: Many-to-many user-project relationships with roles
- **Task**: Work items (title, description, status, priority, due_date)
- **Comment**: Task discussions (content, task_id, author_id)

## Key Design Decisions:
- PostgreSQL with SQLAlchemy ORM
- Bcrypt password hashing (12 rounds)
- JWT authentication (stateless)
- Role-based access control (admin, manager, member, viewer)
- Proper cascading deletes and SET NULL where appropriate
- Comprehensive indexes on foreign keys and query fields

## Relationships:
- User owns multiple Projects (CASCADE delete)
- User has many ProjectMember entries (CASCADE delete)
- Project has many Tasks (CASCADE delete)
- Task has many Comments (CASCADE delete)
- User creates/assigned to Tasks (SET NULL on delete)
- User authors Comments (SET NULL on delete)

All models use proper numpy-style docstrings and include __repr__ methods.
