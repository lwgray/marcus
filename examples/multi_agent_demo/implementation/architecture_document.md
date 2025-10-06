# Task Management API - System Architecture

**Author:** Foundation Agent
**Task:** Design Authentication System (task_authentication_system_design)
**Date:** 2025-10-05
**Version:** 1.0.0

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture Decisions](#architecture-decisions)
4. [Database Design](#database-design)
5. [API Architecture](#api-architecture)
6. [Authentication & Authorization](#authentication--authorization)
7. [Security Considerations](#security-considerations)
8. [Data Flow Diagrams](#data-flow-diagrams)
9. [Implementation Guidelines](#implementation-guidelines)
10. [Dependencies](#dependencies)

---

## Executive Summary

This document describes the architecture for a production-quality REST API for task management. The system uses a modern, scalable architecture with JWT-based stateless authentication, PostgreSQL database with SQLAlchemy ORM, and RESTful API design patterns.

**Key Technologies:**
- **Backend Framework:** Python with FastAPI/Flask
- **Database:** PostgreSQL 14+
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic
- **Authentication:** JWT (JSON Web Tokens)
- **Password Hashing:** bcrypt (12 rounds)

---

## System Overview

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  (Web App, Mobile App, CLI, Third-party Integrations)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway / Load Balancer              │
│                    (HTTPS, Rate Limiting)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    REST API Application                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Authentication Middleware (JWT Verification)        │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Route Handlers (Auth, Users, Projects, Tasks)      │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Business Logic Layer (Validation, Authorization)    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Data Access Layer (SQLAlchemy ORM)                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                        │
│  (Users, Projects, Tasks, Comments, Indexes)                │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Decisions

### ADR-001: JWT for Authentication

**Decision:** Use JWT (JSON Web Tokens) for authentication

**Rationale:**
- Stateless authentication (no session storage required)
- Scalable across multiple API instances
- Self-contained tokens with claims
- Standard industry practice for REST APIs
- Easy integration with frontend applications

**Consequences:**
- Token revocation requires additional logic (blacklist or short expiration)
- Token size is larger than session IDs
- Need secure secret key management

**Implementation:**
- Access tokens expire in 1 hour (configurable)
- Include user ID, email, and role in token payload
- Use HS256 algorithm for signing
- Implement refresh token mechanism for seamless UX

### ADR-002: PostgreSQL with SQLAlchemy ORM

**Decision:** Use PostgreSQL as primary database with SQLAlchemy ORM

**Rationale:**
- ACID compliance for data integrity
- Rich relationship support (foreign keys, cascades)
- Excellent performance with proper indexing
- Strong Python ecosystem integration
- Advanced features (JSON columns, full-text search)

**Consequences:**
- Database-specific features may limit portability
- ORM adds abstraction layer (minor performance overhead)
- Requires database migrations management

**Implementation:**
- Use Alembic for schema migrations
- Implement proper indexes on foreign keys and query fields
- Use connection pooling for performance
- Enable query logging in development

### ADR-003: RESTful API Design

**Decision:** Use REST architecture with resource-based URLs

**Rationale:**
- Industry standard, well-understood pattern
- Clear separation of concerns
- Easy to document and consume
- HTTP methods map naturally to CRUD operations
- Stateless communication

**Consequences:**
- May require multiple requests for complex operations
- Need careful API versioning strategy
- Pagination required for large datasets

**Implementation:**
- Use HTTP verbs correctly (GET, POST, PATCH, DELETE)
- Resource-based URLs: `/api/v1/projects/{id}/tasks`
- Consistent error responses with status codes
- API versioning in URL path

### ADR-004: Role-Based Access Control (RBAC)

**Decision:** Implement role-based access control with hierarchical permissions

**Rationale:**
- Scalable permission management
- Clear separation of responsibilities
- Easy to understand and maintain
- Supports multi-tenant scenarios

**Roles:**
- **Admin:** Full system access
- **Manager:** Project creation, team management
- **Member:** Task management, collaboration
- **Viewer:** Read-only access

**Implementation:**
- Store role in User model
- Project-level roles in ProjectMember model
- Middleware validates permissions on each request
- Owner always has full access to their resources

---

## Database Design

### Entity-Relationship Diagram

```
┌─────────────────────┐
│       User          │
│  ─────────────────  │
│  id (PK)            │
│  email (UNIQUE)     │
│  username (UNIQUE)  │
│  password_hash      │
│  first_name         │
│  last_name          │
│  role               │
│  is_active          │
│  is_verified        │
│  created_at         │
│  updated_at         │
│  last_login         │
└─────────────────────┘
    │        │        │
    │        │        │ (owner)
    │        │        ↓
    │        │    ┌─────────────────────┐
    │        │    │      Project        │
    │        │    │  ─────────────────  │
    │        │    │  id (PK)            │
    │        │    │  name               │
    │        │    │  description        │
    │        │    │  owner_id (FK)      │
    │        │    │  is_archived        │
    │        │    │  created_at         │
    │        │    │  updated_at         │
    │        │    └─────────────────────┘
    │        │            │
    │        │            │
    │        │            ↓
    │        │    ┌─────────────────────┐
    │        │    │   ProjectMember     │
    │        │    │  ─────────────────  │
    │        ├───→│  id (PK)            │
    │        │    │  project_id (FK)    │
    │        └───→│  user_id (FK)       │
    │             │  role               │
    │             │  joined_at          │
    │             └─────────────────────┘
    │
    │ (created_by, assigned_to)
    │
    ↓
┌─────────────────────┐
│        Task         │
│  ─────────────────  │
│  id (PK)            │
│  title              │
│  description        │
│  project_id (FK)    │
│  created_by_id (FK) │
│  assigned_to_id(FK) │
│  status             │
│  priority           │
│  due_date           │
│  created_at         │
│  updated_at         │
│  completed_at       │
└─────────────────────┘
    │
    │
    ↓
┌─────────────────────┐
│      Comment        │
│  ─────────────────  │
│  id (PK)            │
│  content            │
│  task_id (FK)       │
│  author_id (FK)     │
│  created_at         │
│  updated_at         │
└─────────────────────┘
```

### Key Relationships

1. **User ↔ Project (Owner)**
   - One-to-Many: User owns multiple Projects
   - Cascade: DELETE (when user deleted, their projects are deleted)

2. **User ↔ ProjectMember ↔ Project**
   - Many-to-Many through ProjectMember
   - Unique constraint: (project_id, user_id)
   - Cascade: DELETE on both sides

3. **Project ↔ Task**
   - One-to-Many: Project contains multiple Tasks
   - Cascade: DELETE (when project deleted, tasks are deleted)

4. **User ↔ Task (Creator/Assignee)**
   - Many-to-One: User creates/assigned multiple Tasks
   - Cascade: SET NULL (when user deleted, reference nullified)

5. **Task ↔ Comment**
   - One-to-Many: Task has multiple Comments
   - Cascade: DELETE (when task deleted, comments deleted)

6. **User ↔ Comment**
   - One-to-Many: User authors multiple Comments
   - Cascade: SET NULL (preserve comments when user deleted)

### Indexes

Critical indexes for query performance:

```sql
-- Users
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_username ON users(username);

-- Projects
CREATE INDEX ix_projects_owner_id ON projects(owner_id);

-- ProjectMembers
CREATE INDEX ix_project_members_project_id ON project_members(project_id);
CREATE INDEX ix_project_members_user_id ON project_members(user_id);
CREATE UNIQUE INDEX uq_project_user ON project_members(project_id, user_id);

-- Tasks
CREATE INDEX ix_tasks_project_id ON tasks(project_id);
CREATE INDEX ix_tasks_assigned_to_id ON tasks(assigned_to_id);
CREATE INDEX ix_tasks_status ON tasks(status);
CREATE INDEX ix_tasks_priority ON tasks(priority);

-- Comments
CREATE INDEX ix_comments_task_id ON comments(task_id);
CREATE INDEX ix_comments_author_id ON comments(author_id);
```

---

## API Architecture

### URL Structure

```
/api/v1/
├── auth/
│   ├── register          POST    - Create new user account
│   ├── login             POST    - Authenticate and get token
│   ├── me                GET     - Get current user info
│   └── refresh           POST    - Refresh access token
│
├── users/
│   ├── /                 GET     - List users (admin only)
│   └── /{user_id}
│       ├── GET                   - Get user details
│       └── PATCH                 - Update user
│
├── projects/
│   ├── /                 GET     - List user's projects
│   ├── /                 POST    - Create new project
│   ├── /{project_id}
│   │   ├── GET                   - Get project details
│   │   ├── PATCH                 - Update project
│   │   └── DELETE                - Delete project
│   └── /{project_id}/members
│       ├── GET                   - List project members
│       ├── POST                  - Add member
│       └── /{member_id}
│           └── DELETE            - Remove member
│
├── tasks/
│   ├── /                 GET     - List tasks (with filters)
│   ├── /                 POST    - Create new task
│   ├── /{task_id}
│   │   ├── GET                   - Get task details
│   │   ├── PATCH                 - Update task
│   │   └── DELETE                - Delete task
│   └── /{task_id}/comments
│       ├── GET                   - List task comments
│       └── POST                  - Create comment
│
└── comments/
    └── /{comment_id}
        ├── PATCH                 - Update comment
        └── DELETE                - Delete comment
```

### Response Format

**Success Response (200, 201):**
```json
{
  "id": 1,
  "name": "Project Name",
  "created_at": "2025-10-05T10:30:00Z",
  ...
}
```

**List Response (200):**
```json
{
  "items": [
    { "id": 1, ... },
    { "id": 2, ... }
  ],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

**Error Response (4xx, 5xx):**
```json
{
  "error": "validation_error",
  "message": "Invalid input data",
  "details": {
    "field": "email",
    "reason": "Invalid email format"
  }
}
```

### HTTP Status Codes

- **200 OK**: Successful GET, PATCH
- **201 Created**: Successful POST (resource created)
- **204 No Content**: Successful DELETE
- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Valid auth but insufficient permissions
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Resource already exists or conflict state
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server-side errors

---

## Authentication & Authorization

### Authentication Flow

```
1. User Registration
   ┌──────────┐                              ┌──────────┐
   │  Client  │                              │   API    │
   └────┬─────┘                              └────┬─────┘
        │  POST /auth/register                    │
        │  {email, password, ...}                 │
        ├────────────────────────────────────────→│
        │                                          │
        │                    Validate input        │
        │                    Hash password (bcrypt)│
        │                    Create User record    │
        │                    Generate JWT token    │
        │                                          │
        │  {access_token, user}                    │
        │←────────────────────────────────────────┤
        │                                          │

2. User Login
   ┌──────────┐                              ┌──────────┐
   │  Client  │                              │   API    │
   └────┬─────┘                              └────┬─────┘
        │  POST /auth/login                       │
        │  {email, password}                      │
        ├────────────────────────────────────────→│
        │                                          │
        │                    Find user by email    │
        │                    Verify password       │
        │                    Generate JWT token    │
        │                    Update last_login     │
        │                                          │
        │  {access_token, token_type, expires_in}  │
        │←────────────────────────────────────────┤
        │                                          │

3. Authenticated Request
   ┌──────────┐                              ┌──────────┐
   │  Client  │                              │   API    │
   └────┬─────┘                              └────┬─────┘
        │  GET /projects                          │
        │  Authorization: Bearer <token>          │
        ├────────────────────────────────────────→│
        │                                          │
        │                    Verify JWT signature  │
        │                    Check token expiration│
        │                    Extract user claims   │
        │                    Load user from DB     │
        │                    Check permissions     │
        │                    Process request       │
        │                                          │
        │  {items: [...], meta: {...}}             │
        │←────────────────────────────────────────┤
```

### JWT Token Structure

**Header:**
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload:**
```json
{
  "sub": "1",              // User ID
  "email": "user@example.com",
  "role": "member",
  "iat": 1696512000,       // Issued at
  "exp": 1696515600        // Expires at (1 hour)
}
```

**Signature:**
```
HMACSHA256(
  base64UrlEncode(header) + "." +
  base64UrlEncode(payload),
  secret_key
)
```

### Authorization Matrix

| Resource | Action | Admin | Manager | Member | Viewer | Owner |
|----------|--------|-------|---------|--------|--------|-------|
| User (self) | Read | ✓ | ✓ | ✓ | ✓ | - |
| User (self) | Update | ✓ | ✓ | ✓ | ✓ | - |
| User (any) | Read | ✓ | - | - | - | - |
| User (any) | Update | ✓ | - | - | - | - |
| Project | Create | ✓ | ✓ | ✓ | - | - |
| Project | Read | ✓ | Member | Member | Member | ✓ |
| Project | Update | ✓ | - | - | - | ✓ |
| Project | Delete | ✓ | - | - | - | ✓ |
| Project Members | Add | ✓ | - | - | - | ✓ |
| Project Members | Remove | ✓ | - | - | - | ✓ |
| Task | Create | ✓ | Member | Member | - | - |
| Task | Read | ✓ | Member | Member | Member | - |
| Task | Update | ✓ | Member | Member | - | - |
| Task | Delete | ✓ | - | Creator | - | Owner |
| Comment | Create | ✓ | Member | Member | - | - |
| Comment | Read | ✓ | Member | Member | Member | - |
| Comment | Update | ✓ | - | Author | - | - |
| Comment | Delete | ✓ | - | Author | - | - |

---

## Security Considerations

### Password Security

1. **Hashing Algorithm:** bcrypt with 12 rounds
   ```python
   import bcrypt

   # Hash password
   password_hash = bcrypt.hashpw(
       password.encode('utf-8'),
       bcrypt.gensalt(rounds=12)
   )

   # Verify password
   is_valid = bcrypt.checkpw(
       password.encode('utf-8'),
       stored_hash
   )
   ```

2. **Password Requirements:**
   - Minimum 8 characters
   - Must contain uppercase, lowercase, number
   - No common passwords (implement blocklist)

### Token Security

1. **Secret Key Management:**
   - Use strong random secret (256-bit minimum)
   - Store in environment variables, never in code
   - Rotate secrets periodically
   - Use different secrets for dev/staging/prod

2. **Token Expiration:**
   - Access tokens: 1 hour (configurable)
   - Refresh tokens: 7 days (optional)
   - Implement token blacklist for logout

3. **Token Transmission:**
   - HTTPS only in production
   - HttpOnly cookies (optional, for web apps)
   - Authorization header: `Bearer <token>`

### API Security

1. **Input Validation:**
   - Validate all inputs server-side
   - Use Pydantic models for request validation
   - Sanitize SQL inputs (ORM handles this)
   - Limit request size

2. **Rate Limiting:**
   - Per-IP: 100 requests/minute
   - Per-user: 1000 requests/hour
   - Login endpoint: 5 attempts/15 minutes

3. **CORS Configuration:**
   - Whitelist allowed origins
   - Credentials: true for cookie support
   - Expose necessary headers only

4. **SQL Injection Prevention:**
   - Use SQLAlchemy ORM (parameterized queries)
   - Never use string concatenation for queries
   - Validate all user inputs

---

## Data Flow Diagrams

### Create Task Flow

```
┌──────┐    ┌─────────────┐    ┌──────────┐    ┌──────────┐
│Client│    │Auth         │    │Business  │    │Database  │
│      │    │Middleware   │    │Logic     │    │Layer     │
└──┬───┘    └──┬──────────┘    └────┬─────┘    └────┬─────┘
   │           │                     │               │
   │ POST /tasks                     │               │
   │ {title, project_id, ...}        │               │
   ├──────────→│                     │               │
   │           │                     │               │
   │           │ Verify JWT token    │               │
   │           │ Extract user_id     │               │
   │           ├────────────────────→│               │
   │           │                     │               │
   │           │                     │ Check user is │
   │           │                     │ project member│
   │           │                     ├──────────────→│
   │           │                     │               │
   │           │                     │ Validate input│
   │           │                     │ Create Task   │
   │           │                     ├──────────────→│
   │           │                     │               │
   │           │                     │ Task created  │
   │           │                     │←──────────────┤
   │           │                     │               │
   │           │ {task_data}         │               │
   │           │←────────────────────┤               │
   │           │                     │               │
   │ 201 Created                     │               │
   │ {id, title, ...}                │               │
   │←──────────┤                     │               │
```

### Permission Check Flow

```
┌──────────────────────────────────────────────────────┐
│  1. Extract user from JWT token                      │
│     - Verify signature                               │
│     - Check expiration                               │
│     - Load user from database                        │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────┐
│  2. Identify resource and action                     │
│     - Parse URL and HTTP method                      │
│     - Determine required permission                  │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────┐
│  3. Check global permissions                         │
│     - Is user admin? → ALLOW                         │
│     - Is resource public? → ALLOW                    │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────┐
│  4. Check resource-specific permissions              │
│     - Is user the owner? → Check owner permissions   │
│     - Is user a project member? → Check role         │
│     - Check authorization matrix                     │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────┐
│  5. Allow or Deny                                    │
│     - ALLOW: Process request                         │
│     - DENY: Return 403 Forbidden                     │
└──────────────────────────────────────────────────────┘
```

---

## Implementation Guidelines

### Project Structure

```
task-management-api/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Application entry point
│   ├── config.py                # Configuration management
│   ├── database.py              # Database connection
│   │
│   ├── models/                  # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── task.py
│   │   └── comment.py
│   │
│   ├── schemas/                 # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── task.py
│   │   └── comment.py
│   │
│   ├── routes/                  # API routes
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── projects.py
│   │   ├── tasks.py
│   │   └── comments.py
│   │
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── project_service.py
│   │   └── task_service.py
│   │
│   ├── middleware/              # Middleware
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── error_handler.py
│   │
│   └── utils/                   # Utilities
│       ├── __init__.py
│       ├── security.py          # Password hashing, JWT
│       ├── permissions.py       # Authorization logic
│       └── pagination.py
│
├── alembic/                     # Database migrations
│   ├── versions/
│   └── env.py
│
├── tests/                       # Test suite
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
├── alembic.ini                  # Alembic configuration
└── README.md
```

### Environment Variables

```bash
# Database  # pragma: allowlist secret
DATABASE_URL=postgresql://user:password@localhost:5432/taskmanagement  # pragma: allowlist secret
DATABASE_POOL_SIZE=10

# Security
SECRET_KEY=your-secret-key-here-use-strong-random-256-bit
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# API
API_V1_PREFIX=/api/v1
ALLOWED_ORIGINS=http://localhost:3000,https://app.example.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# Application
DEBUG=False
LOG_LEVEL=INFO
```

### Database Migration Workflow

```bash
# Create new migration
alembic revision --autogenerate -m "Create user table"

# Review migration file
# Edit alembic/versions/xxx_create_user_table.py

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check current version
alembic current
```

### Testing Strategy

1. **Unit Tests:**
   - Test models (validation, relationships)
   - Test utilities (password hashing, JWT)
   - Test business logic in services
   - Mock database calls

2. **Integration Tests:**
   - Test API endpoints
   - Test authentication flow
   - Test authorization rules
   - Use test database

3. **Performance Tests:**
   - Load testing on critical endpoints
   - Database query performance
   - Response time benchmarks

---

## Dependencies

### Core Dependencies

```txt
# Web Framework
fastapi>=0.104.0
uvicorn[standard]>=0.24.0

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.9

# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6

# Validation
pydantic>=2.4.0
email-validator>=2.1.0

# Utilities
python-dotenv>=1.0.0
```

### Development Dependencies

```txt
# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0

# Code Quality
black>=23.10.0
flake8>=6.1.0
mypy>=1.6.0
isort>=5.12.0

# Documentation
mkdocs>=1.5.0
mkdocs-material>=9.4.0
```

---

## Next Steps for Implementation Team

1. **Backend Team:**
   - Set up FastAPI application structure
   - Implement database models from `database_schema.py`
   - Set up Alembic migrations
   - Implement authentication endpoints
   - Implement CRUD endpoints per API specification

2. **Frontend Team:**
   - Review `auth_api_spec.yaml` for API contracts
   - Implement authentication flow (login, register, token management)
   - Build UI components for Projects, Tasks, Comments
   - Implement API client with proper error handling

3. **DevOps Team:**
   - Set up PostgreSQL database
   - Configure environment variables
   - Set up CI/CD pipeline
   - Configure HTTPS and rate limiting
   - Set up monitoring and logging

4. **Testing Team:**
   - Write unit tests for models and utilities
   - Write integration tests for API endpoints
   - Perform security testing (OWASP Top 10)
   - Conduct load testing

---

## Appendix

### Glossary

- **JWT**: JSON Web Token - A compact, URL-safe means of representing claims
- **ORM**: Object-Relational Mapping - Database abstraction layer
- **RBAC**: Role-Based Access Control - Permission system based on roles
- **CRUD**: Create, Read, Update, Delete - Basic data operations
- **REST**: Representational State Transfer - API architecture style

### References

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [JWT Specification](https://tools.ietf.org/html/rfc7519)
- [OpenAPI Specification](https://swagger.io/specification/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
