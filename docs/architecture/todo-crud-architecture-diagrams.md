# TODO CRUD Architecture Diagrams

## Version: 1.0.0
## Author: Backend Agent 2
## Date: 2025-10-07

---

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Database Schema](#database-schema)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Component Interactions](#component-interactions)
5. [Error Handling Flow](#error-handling-flow)
6. [Authentication Flow](#authentication-flow)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│              (Web, Mobile, Desktop, CLI)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/REST
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     API Gateway / Load Balancer              │
│                    (NGINX / AWS ALB)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Middleware Layer                        │  │
│  │  - CORS                                              │  │
│  │  - Authentication (JWT)                              │  │
│  │  - Rate Limiting                                     │  │
│  │  - Request Logging                                   │  │
│  │  - Error Handling                                    │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │              API Routes Layer                        │  │
│  │  - /auth/*      (Authentication)                     │  │
│  │  - /users/*     (User Management)                    │  │
│  │  - /todos/*     (Todo CRUD)                          │  │
│  │  - /tags/*      (Tag Management)                     │  │
│  │  - /stats/*     (Statistics)                         │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │              Service Layer                           │  │
│  │  - TodoService                                       │  │
│  │  - TagService                                        │  │
│  │  - UserService                                       │  │
│  │  - AuthService                                       │  │
│  │  (Business Logic & Validation)                       │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │              Data Access Layer                       │  │
│  │  - SQLAlchemy ORM                                    │  │
│  │  - Models (User, Todo, Tag)                          │  │
│  │  - Database Session Management                       │  │
│  └──────────────┬───────────────────────────────────────┘  │
└─────────────────┼────────────────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────────────┐
│              PostgreSQL Database                         │
│  - Users Table                                           │
│  - Todos Table                                           │
│  - Tags Table                                            │
│  - Todo_Tags Junction Table                             │
└──────────────────────────────────────────────────────────┘

External Services:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Redis Cache   │     │  Email Service  │     │   File Storage  │
│  (Sessions)     │     │  (Notifications)│     │    (Avatars)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Database Schema

### Entity Relationship Diagram (ERD)

```
┌─────────────────────────────────────────┐
│              USERS                      │
├─────────────────────────────────────────┤
│ PK │ id (UUID)                          │
│    │ email (VARCHAR 255) UNIQUE         │
│    │ username (VARCHAR 50) UNIQUE       │
│    │ password_hash (VARCHAR 255)        │
│    │ first_name (VARCHAR 100)           │
│    │ last_name (VARCHAR 100)            │
│    │ avatar_url (TEXT)                  │
│    │ is_active (BOOLEAN)                │
│    │ created_at (TIMESTAMP)             │
│    │ updated_at (TIMESTAMP)             │
└──────────┬──────────────────────┬───────┘
           │                      │
           │ 1                    │ 1
           │                      │
           │ owner_id             │ assigned_to_id
           │                      │
           │ *                    │ *
┌──────────▼──────────────────────▼───────┐
│              TODOS                      │
├─────────────────────────────────────────┤
│ PK │ id (UUID)                          │
│ FK │ owner_id (UUID) → users.id         │
│ FK │ assigned_to_id (UUID) → users.id   │
│    │ title (VARCHAR 200) NOT NULL       │
│    │ description (TEXT)                 │
│    │ status (VARCHAR 20) DEFAULT pending│
│    │ priority (VARCHAR 20) DEFAULT med  │
│    │ due_date (TIMESTAMP)               │
│    │ completed_at (TIMESTAMP)           │
│    │ position (INTEGER) DEFAULT 0       │
│    │ created_at (TIMESTAMP)             │
│    │ updated_at (TIMESTAMP)             │
│    │                                    │
│    │ CHECK: status IN (pending,         │
│    │        in_progress, completed)     │
│    │ CHECK: priority IN (low, medium,   │
│    │        high, urgent)               │
└──────────┬──────────────────────────────┘
           │
           │ *
           │
┌──────────▼──────────────────────────────┐
│           TODO_TAGS (Junction)          │
├─────────────────────────────────────────┤
│ PK │ todo_id (UUID) → todos.id          │
│ PK │ tag_id (UUID) → tags.id            │
└──────────┬──────────────────────────────┘
           │
           │ *
           │
┌──────────▼──────────────────────────────┐
│              TAGS                       │
├─────────────────────────────────────────┤
│ PK │ id (UUID)                          │
│ FK │ user_id (UUID) → users.id          │
│    │ name (VARCHAR 50) NOT NULL         │
│    │ color (VARCHAR 7) (hex color)      │
│    │ created_at (TIMESTAMP)             │
│    │ updated_at (TIMESTAMP)             │
│    │                                    │
│    │ UNIQUE: (name, user_id)            │
└──────────┬──────────────────────────────┘
           │
           │ *
           │ user_id
           │ 1
           │
      (back to USERS)
```

### Database Indexes

**Users Table:**
- `idx_users_email` on `email` (for login lookups)
- `idx_users_username` on `username` (for profile lookups)

**Todos Table:**
- `idx_todos_owner_id` on `owner_id` (for user's todos)
- `idx_todos_status` on `status` (for filtering by status)
- `idx_todos_due_date` on `due_date` (for sorting by due date)
- `idx_todos_owner_status` on `(owner_id, status)` (compound index for common queries)

**Tags Table:**
- `idx_tags_user_id` on `user_id` (for user's tags)

### Cardinality

- **User → Owned Todos**: One-to-Many (1:N)
- **User → Assigned Todos**: One-to-Many (1:N)
- **User → Tags**: One-to-Many (1:N)
- **Todo → Tags**: Many-to-Many (N:M) via todo_tags
- **Todo → Owner**: Many-to-One (N:1)
- **Todo → Assigned User**: Many-to-One (N:1)

---

## Data Flow Diagrams

### Create Todo Flow

```
┌──────┐      POST /api/v1/todos       ┌─────────┐
│Client├────────────────────────────────►API     │
└──────┘    {title, description, ...}  │Router   │
                                        └────┬────┘
                                             │
                                             │ 1. Extract JWT token
                                             │ 2. Authenticate user
                                             │
                                        ┌────▼────┐
                                        │Auth     │
                                        │Depend.  │
                                        └────┬────┘
                                             │
                                             │ current_user
                                             │
                                        ┌────▼────┐
                                        │Todo     │
                                        │Service  │
                                        └────┬────┘
                                             │
                   ┌─────────────────────────┼─────────────────────────┐
                   │                         │                         │
                   │ 1. Validate input       │ 2. Get/create tags      │
                   │                         │                         │
              ┌────▼────┐              ┌─────▼─────┐            ┌─────▼─────┐
              │Create   │              │Query tags │            │Create new │
              │Todo obj │              │by name    │            │tags if    │
              └────┬────┘              └─────┬─────┘            │needed     │
                   │                         │                  └─────┬─────┘
                   │                         │                        │
                   └─────────────────────────┴────────────────────────┘
                                             │
                                             │ 3. Associate tags
                                             │
                                        ┌────▼────┐
                                        │Database │
                                        │Session  │
                                        └────┬────┘
                                             │
                                             │ INSERT INTO todos
                                             │ INSERT INTO todo_tags
                                             │
                                        ┌────▼────┐
                                        │PostgreSQL│
                                        │Database │
                                        └────┬────┘
                                             │
                                             │ COMMIT
                                             │
                                        ┌────▼────┐
                                        │Return   │
                                        │Todo obj │
                                        └────┬────┘
                                             │
┌──────┐         201 Created            ┌───▼─────┐
│Client│◄────────────────────────────────┤API      │
└──────┘    {id, title, owner_id, ...}  │Response │
                                         └─────────┘
```

### List Todos with Filters Flow

```
┌──────┐   GET /api/v1/todos?status=pending&page=1  ┌─────────┐
│Client├───────────────────────────────────────────►│API      │
└──────┘                                             │Router   │
                                                     └────┬────┘
                                                          │
                                         ┌────────────────┴──────────────────┐
                                         │                                   │
                                    ┌────▼────┐                        ┌─────▼─────┐
                                    │Auth     │                        │Parse query│
                                    │Depend.  │                        │params     │
                                    └────┬────┘                        └─────┬─────┘
                                         │                                   │
                                         │ current_user                      │
                                         │                                   │
                                         └──────────────┬────────────────────┘
                                                        │
                                                   ┌────▼────┐
                                                   │Todo     │
                                                   │Service  │
                                                   └────┬────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        │                               │                               │
                   ┌────▼────┐                     ┌────▼────┐                    ┌────▼────┐
                   │Build    │                     │Apply    │                    │Apply    │
                   │base     │────────────────────►│filters  │───────────────────►│pagination│
                   │query    │   WHERE owner_id    │& sort   │   status, priority,│& sort   │
                   └─────────┘                     └─────────┘   search, tag       └────┬────┘
                                                                                         │
                                                                 ┌───────────────────────┤
                                                                 │                       │
                                                            ┌────▼────┐            ┌─────▼─────┐
                                                            │COUNT    │            │SELECT     │
                                                            │query    │            │with LIMIT │
                                                            └────┬────┘            │& OFFSET   │
                                                                 │                 └─────┬─────┘
                                                                 │                       │
                                                            ┌────▼───────────────────────▼────┐
                                                            │Execute queries                  │
                                                            └────┬────────────────────────────┘
                                                                 │
                                                            ┌────▼────┐
                                                            │PostgreSQL│
                                                            │Database │
                                                            └────┬────┘
                                                                 │
                                                                 │ Results
                                                                 │
                                                            ┌────▼────┐
                                                            │Build    │
                                                            │paginated│
                                                            │response │
                                                            └────┬────┘
                                                                 │
┌──────┐         200 OK                                    ┌────▼────┐
│Client│◄──────────────────────────────────────────────────┤API      │
└──────┘    {items: [...], total: 42, page: 1, ...}       │Response │
                                                            └─────────┘
```

### Update Todo Flow

```
┌──────┐   PATCH /api/v1/todos/{id}     ┌─────────┐
│Client├────────────────────────────────►│API      │
└──────┘    {status: "completed"}        │Router   │
                                          └────┬────┘
                                               │
                                          ┌────▼────┐
                                          │Auth     │
                                          │Depend.  │
                                          └────┬────┘
                                               │
                                          ┌────▼────┐
                                          │Todo     │
                                          │Service  │
                                          └────┬────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
               ┌────▼────┐                ┌────▼────┐               ┌─────▼─────┐
               │Get todo │                │Check    │               │Validate   │
               │by ID    │───────────────►│ownership│──────────────►│updates    │
               └────┬────┘    404 if not  └────┬────┘   403 if not  └─────┬─────┘
                    │         found            │        owner             │
                    │                          │                          │
                    │         Todo object      │                          │
                    └──────────────────────────┴──────────────────────────┘
                                               │
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
               ┌────▼────┐                ┌────▼────┐               ┌─────▼─────┐
               │Update   │                │Handle   │               │Auto-set   │
               │fields   │                │tags if  │               │completed_ │
               │         │                │included │               │at if      │
               │         │                │         │               │completed  │
               └────┬────┘                └────┬────┘               └─────┬─────┘
                    │                          │                          │
                    └──────────────────────────┴──────────────────────────┘
                                               │
                                          ┌────▼────┐
                                          │Database │
                                          │Session  │
                                          └────┬────┘
                                               │
                                               │ UPDATE todos SET ...
                                               │
                                          ┌────▼────┐
                                          │PostgreSQL│
                                          │Database │
                                          └────┬────┘
                                               │
                                               │ COMMIT & REFRESH
                                               │
┌──────┐         200 OK                  ┌────▼────┐
│Client│◄────────────────────────────────┤Updated  │
└──────┘    {id, status: "completed",    │Todo obj │
             completed_at: "2025-...", }  └─────────┘
```

### Delete Todo Flow

```
┌──────┐   DELETE /api/v1/todos/{id}    ┌─────────┐
│Client├────────────────────────────────►│API      │
└──────┘                                  │Router   │
                                          └────┬────┘
                                               │
                                          ┌────▼────┐
                                          │Auth     │
                                          │Depend.  │
                                          └────┬────┘
                                               │
                                          ┌────▼────┐
                                          │Todo     │
                                          │Service  │
                                          └────┬────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
               ┌────▼────┐                ┌────▼────┐               ┌─────▼─────┐
               │Get todo │                │Check    │               │Delete     │
               │by ID    │───────────────►│ownership│──────────────►│todo       │
               └────┬────┘    404 if not  └────┬────┘   403 if not  └─────┬─────┘
                    │         found            │        owner             │
                    └──────────────────────────┴──────────────────────────┘
                                               │
                                          ┌────▼────┐
                                          │Database │
                                          │Session  │
                                          └────┬────┘
                                               │
                                               │ DELETE FROM todo_tags WHERE todo_id=...
                                               │ DELETE FROM todos WHERE id=...
                                               │ (CASCADE handled by FK)
                                               │
                                          ┌────▼────┐
                                          │PostgreSQL│
                                          │Database │
                                          └────┬────┘
                                               │
                                               │ COMMIT
                                               │
┌──────┐         204 No Content          ┌────▼────┐
│Client│◄────────────────────────────────┤API      │
└──────┘         (empty body)             │Response │
                                          └─────────┘
```

---

## Component Interactions

### Service Layer Dependencies

```
┌───────────────────────────────────────────────────────────┐
│                   TodoService                             │
├───────────────────────────────────────────────────────────┤
│  + create_todo(user_id, todo_data)                        │
│  + get_todo(todo_id, user_id)                             │
│  + list_todos(user_id, filters, pagination)               │
│  + update_todo(todo_id, user_id, updates)                 │
│  + delete_todo(todo_id, user_id)                          │
│  + bulk_update_todos(todo_ids, user_id, updates)          │
│  + reorder_todos(todo_ids, user_id)                       │
│  - _get_or_create_tags(user_id, tag_names)                │
└────────┬────────────────────────────┬─────────────────────┘
         │                            │
         │ uses                       │ uses
         │                            │
         ▼                            ▼
┌─────────────────┐          ┌─────────────────┐
│   Todo Model    │          │   Tag Model     │
├─────────────────┤          ├─────────────────┤
│ - id            │          │ - id            │
│ - title         │◄─────────┤ - name          │
│ - description   │   N:M    │ - color         │
│ - status        │          │ - user_id       │
│ - priority      │          └─────────────────┘
│ - owner_id      │
│ - tags          │
└─────────────────┘
```

### Router → Service → Model Flow

```
                HTTP Request
                     │
┌────────────────────▼────────────────────┐
│         FastAPI Router Layer            │
│  - Request validation (Pydantic)        │
│  - Authentication (JWT dependency)      │
│  - Response serialization               │
└────────────────────┬────────────────────┘
                     │
                     │ DTO (Data Transfer Objects)
                     │ - TodoCreate
                     │ - TodoUpdate
                     │ - TodoFilterParams
                     │
┌────────────────────▼────────────────────┐
│         Service Layer                   │
│  - Business logic                       │
│  - Data validation                      │
│  - Authorization checks                 │
│  - Transaction management               │
└────────────────────┬────────────────────┘
                     │
                     │ ORM Operations
                     │ - session.add()
                     │ - session.execute()
                     │ - session.commit()
                     │
┌────────────────────▼────────────────────┐
│         SQLAlchemy ORM                  │
│  - Object-relational mapping            │
│  - Query building                       │
│  - Relationship loading                 │
└────────────────────┬────────────────────┘
                     │
                     │ SQL Queries
                     │ - INSERT
                     │ - SELECT
                     │ - UPDATE
                     │ - DELETE
                     │
┌────────────────────▼────────────────────┐
│         PostgreSQL Database             │
│  - Data persistence                     │
│  - Transaction management               │
│  - Constraint enforcement               │
└─────────────────────────────────────────┘
```

---

## Error Handling Flow

### Error Propagation Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  Application Layer                         │
└────────────────────┬───────────────────────────────────────┘
                     │
                     │ Exception raised
                     │
┌────────────────────▼───────────────────────────────────────┐
│               Service Layer Errors                         │
│  - ResourceNotFoundError                                   │
│  - UnauthorizedActionError                                 │
│  - ValidationError                                         │
│  - ConflictError                                           │
└────────────────────┬───────────────────────────────────────┘
                     │
                     │ Caught by exception handler
                     │
┌────────────────────▼───────────────────────────────────────┐
│           Marcus Error Framework                           │
│  - ErrorContext injection                                  │
│  - Error logging                                           │
│  - Metric recording                                        │
└────────────────────┬───────────────────────────────────────┘
                     │
                     │ Formatted error response
                     │
┌────────────────────▼───────────────────────────────────────┐
│           Error Response Handler                           │
│  - HTTP status code mapping                                │
│  - Error message formatting                                │
│  - Response serialization                                  │
└────────────────────┬───────────────────────────────────────┘
                     │
                     │ JSON error response
                     │
┌────────────────────▼───────────────────────────────────────┐
│               Client Receives Error                        │
│  {                                                         │
│    "error": {                                              │
│      "code": "RESOURCE_NOT_FOUND",                         │
│      "message": "Todo not found",                          │
│      "details": {"todo_id": "123..."},                     │
│      "timestamp": "2025-10-07T...",                        │
│      "request_id": "abc..."                                │
│    }                                                       │
│  }                                                         │
└────────────────────────────────────────────────────────────┘
```

### Error Types and HTTP Status Mapping

```
┌──────────────────────────┬──────────────┬─────────────────┐
│    Error Type            │ HTTP Status  │   When to Use   │
├──────────────────────────┼──────────────┼─────────────────┤
│ ResourceNotFoundError    │     404      │ Todo not found  │
├──────────────────────────┼──────────────┼─────────────────┤
│ UnauthorizedActionError  │     403      │ Not owner       │
├──────────────────────────┼──────────────┼─────────────────┤
│ ValidationError          │     400      │ Invalid input   │
├──────────────────────────┼──────────────┼─────────────────┤
│ ConflictError            │     409      │ Duplicate tag   │
├──────────────────────────┼──────────────┼─────────────────┤
│ AuthenticationError      │     401      │ Invalid token   │
└──────────────────────────┴──────────────┴─────────────────┘
```

---

## Authentication Flow

### JWT Authentication Sequence

```
┌──────┐                                              ┌─────────┐
│Client│                                              │  API    │
└───┬──┘                                              └────┬────┘
    │                                                      │
    │  1. POST /api/v1/auth/login                         │
    │     {email, password}                               │
    ├────────────────────────────────────────────────────►│
    │                                                      │
    │                                         ┌────────────▼────────┐
    │                                         │ AuthService         │
    │                                         │ - Verify password   │
    │                                         │ - Generate JWT      │
    │                                         └────────────┬────────┘
    │                                                      │
    │  2. 200 OK                                           │
    │     {access_token, refresh_token, user}             │
    │◄─────────────────────────────────────────────────────┤
    │                                                      │
    │  3. Store tokens in local storage                   │
    │                                                      │
    │                                                      │
    │  4. GET /api/v1/todos                               │
    │     Authorization: Bearer <access_token>            │
    ├────────────────────────────────────────────────────►│
    │                                                      │
    │                                         ┌────────────▼────────┐
    │                                         │ JWT Middleware      │
    │                                         │ - Extract token     │
    │                                         │ - Verify signature  │
    │                                         │ - Check expiration  │
    │                                         │ - Load user         │
    │                                         └────────────┬────────┘
    │                                                      │
    │                                                      │ current_user
    │                                                      │
    │                                         ┌────────────▼────────┐
    │                                         │ TodoService         │
    │                                         │ - Process request   │
    │                                         │   with user_id      │
    │                                         └────────────┬────────┘
    │                                                      │
    │  5. 200 OK                                           │
    │     {items: [...], total: 42, ...}                  │
    │◄─────────────────────────────────────────────────────┤
    │                                                      │
┌───┴──┐                                              ┌────┴────┐
│Client│                                              │  API    │
└──────┘                                              └─────────┘
```

### Token Refresh Flow

```
Access Token Expiring Soon:

┌──────┐                                              ┌─────────┐
│Client│                                              │  API    │
└───┬──┘                                              └────┬────┘
    │                                                      │
    │  1. POST /api/v1/auth/refresh                       │
    │     {refresh_token}                                 │
    ├────────────────────────────────────────────────────►│
    │                                                      │
    │                                         ┌────────────▼────────┐
    │                                         │ AuthService         │
    │                                         │ - Verify refresh    │
    │                                         │   token             │
    │                                         │ - Check blacklist   │
    │                                         │ - Generate new      │
    │                                         │   access token      │
    │                                         └────────────┬────────┘
    │                                                      │
    │  2. 200 OK                                           │
    │     {access_token, expires_in}                      │
    │◄─────────────────────────────────────────────────────┤
    │                                                      │
    │  3. Update stored access token                      │
    │                                                      │
┌───┴──┐                                              ┌────┴────┐
│Client│                                              │  API    │
└──────┘                                              └─────────┘
```

---

## Performance Considerations

### Query Optimization

**Indexes Used:**
```
List Todos Query:
  SELECT * FROM todos
  WHERE owner_id = ? AND status = ?
  ORDER BY created_at DESC
  LIMIT 20 OFFSET 0;

Uses index: idx_todos_owner_status (compound index)
```

**N+1 Query Prevention:**
```python
# Use selectinload to eagerly load tags
query = select(Todo).options(selectinload(Todo.tags))

# This generates:
# SELECT * FROM todos WHERE ...
# SELECT * FROM tags WHERE id IN (tag_ids from todos)
# Instead of N separate queries for each todo's tags
```

### Caching Strategy

```
┌──────────────────────────────────────────┐
│         Cache Layers                     │
├──────────────────────────────────────────┤
│  1. Application Cache (Redis)            │
│     - User sessions (30 min TTL)         │
│     - Token blacklist                    │
│     - Rate limit counters                │
│                                          │
│  2. Database Query Cache                 │
│     - Frequent read queries              │
│     - User statistics (5 min TTL)        │
│                                          │
│  3. CDN Cache (for static assets)        │
│     - API documentation                  │
│     - Avatar images                      │
└──────────────────────────────────────────┘
```

---

## Scalability Architecture

### Horizontal Scaling

```
                    ┌──────────────┐
                    │ Load Balancer│
                    └───────┬──────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
    ┌─────▼─────┐     ┌─────▼─────┐     ┌────▼──────┐
    │ API Node 1│     │ API Node 2│     │ API Node N│
    │ (Stateless)│     │ (Stateless)│     │ (Stateless)│
    └─────┬─────┘     └─────┬─────┘     └────┬──────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
    ┌─────▼─────┐     ┌─────▼─────┐     ┌────▼──────┐
    │PostgreSQL │     │   Redis   │     │  Object   │
    │ Primary   │     │   Cache   │     │  Storage  │
    └─────┬─────┘     └───────────┘     └───────────┘
          │
    ┌─────▼─────┐
    │PostgreSQL │
    │ Read      │
    │ Replicas  │
    └───────────┘
```

---

## Summary

This architecture provides:

✅ **Clear Separation of Concerns**: Layers are well-defined and independent
✅ **Scalable Design**: Stateless API nodes can scale horizontally
✅ **Optimized Queries**: Strategic indexes and eager loading prevent N+1 queries
✅ **Robust Error Handling**: Comprehensive error propagation with context
✅ **Secure Authentication**: JWT-based auth with token refresh
✅ **Performance**: Caching strategy and query optimization
✅ **Database Integrity**: Foreign keys, constraints, and cascade rules

The architecture supports:
- High concurrency (multiple API nodes)
- Fast queries (optimized indexes)
- Data integrity (database constraints)
- Secure access (JWT authentication)
- Clear error messages (error framework)
- Easy testing (layer separation)
