# Todo Application RESTful API Specification

## Version: 1.0.0
## Base URL: `/api/v1`

---

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Data Models](#data-models)
4. [API Endpoints](#api-endpoints)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Security Considerations](#security-considerations)

---

## Overview

This RESTful API provides a complete backend for a todo application with user management, task organization, and collaboration features.

### Design Principles
- **RESTful Architecture**: Resources identified by URIs, standard HTTP methods
- **Stateless**: Each request contains all necessary information
- **JSON Format**: All requests and responses use JSON
- **Versioning**: API version in URL path for backwards compatibility
- **HTTPS Only**: All communication encrypted in production
- **CORS Enabled**: Supports frontend single-page applications

### Technical Stack Recommendations
- **Framework**: FastAPI (Python) - high performance, automatic OpenAPI docs
- **Database**: PostgreSQL - robust, ACID compliant, JSON support
- **Authentication**: JWT (JSON Web Tokens)
- **Validation**: Pydantic models for request/response validation
- **Documentation**: Auto-generated OpenAPI/Swagger documentation

---

## Authentication

### Strategy
JWT-based authentication with Bearer token scheme.

### Authentication Flow
1. User registers or logs in
2. Server returns JWT access token (1 hour expiry) and refresh token (7 days expiry)
3. Client includes token in Authorization header: `Authorization: Bearer <token>`
4. Token refreshed using refresh token before expiry

### Protected Endpoints
All endpoints except `/auth/register` and `/auth/login` require authentication.

---

## Data Models

### User Model
```json
{
  "id": "uuid",
  "email": "string (unique, validated)",
  "username": "string (unique, 3-50 chars)",
  "first_name": "string (optional)",
  "last_name": "string (optional)",
  "created_at": "datetime (ISO 8601)",
  "updated_at": "datetime (ISO 8601)",
  "is_active": "boolean",
  "avatar_url": "string (optional)"
}
```

**Constraints:**
- Email must be unique and valid format
- Username must be unique, 3-50 characters, alphanumeric + underscore
- Password minimum 8 characters (never returned in responses)

---

### Todo Model
```json
{
  "id": "uuid",
  "title": "string (required, 1-200 chars)",
  "description": "string (optional, max 2000 chars)",
  "status": "enum ['pending', 'in_progress', 'completed']",
  "priority": "enum ['low', 'medium', 'high', 'urgent']",
  "due_date": "datetime (ISO 8601, optional)",
  "completed_at": "datetime (ISO 8601, optional)",
  "created_at": "datetime (ISO 8601)",
  "updated_at": "datetime (ISO 8601)",
  "owner_id": "uuid (foreign key to User)",
  "assigned_to_id": "uuid (foreign key to User, optional)",
  "tags": ["array of strings"],
  "position": "integer (for ordering)"
}
```

**Business Rules:**
- Status defaults to 'pending'
- Priority defaults to 'medium'
- Owner cannot be changed after creation
- Completed_at automatically set when status becomes 'completed'
- Position used for custom ordering within user's todo list

---

### Tag Model
```json
{
  "id": "uuid",
  "name": "string (unique per user, 1-50 chars)",
  "color": "string (hex color code, optional)",
  "user_id": "uuid (foreign key to User)",
  "created_at": "datetime (ISO 8601)"
}
```

---

## API Endpoints

### Authentication Endpoints

#### Register User
```
POST /api/v1/auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securePass123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response (201 Created):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "created_at": "2025-10-07T10:30:00Z"
  },
  "access_token": "jwt_token",
  "refresh_token": "refresh_jwt_token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors:**
- 400: Invalid input (validation errors)
- 409: Email or username already exists

---

#### Login
```
POST /api/v1/auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePass123"
}
```

**Response (200 OK):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "johndoe"
  },
  "access_token": "jwt_token",
  "refresh_token": "refresh_jwt_token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors:**
- 401: Invalid credentials
- 403: Account deactivated

---

#### Refresh Token
```
POST /api/v1/auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "refresh_jwt_token"
}
```

**Response (200 OK):**
```json
{
  "access_token": "new_jwt_token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors:**
- 401: Invalid or expired refresh token

---

#### Logout
```
POST /api/v1/auth/logout
```

**Headers:** `Authorization: Bearer <token>`

**Response (204 No Content)**

**Note:** Implements token blacklisting for security

---

### User Endpoints

#### Get Current User Profile
```
GET /api/v1/users/me
```

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2025-10-07T10:30:00Z",
  "updated_at": "2025-10-07T10:30:00Z",
  "is_active": true,
  "avatar_url": null
}
```

---

#### Update Current User Profile
```
PATCH /api/v1/users/me
```

**Headers:** `Authorization: Bearer <token>`

**Request Body (all fields optional):**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

**Response (200 OK):** Updated user object

**Errors:**
- 400: Invalid input

---

#### Change Password
```
POST /api/v1/users/me/password
```

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "current_password": "oldPass123",
  "new_password": "newSecurePass456"
}
```

**Response (204 No Content)**

**Errors:**
- 401: Invalid current password
- 400: New password doesn't meet requirements

---

### Todo Endpoints

#### List Todos (with filtering and pagination)
```
GET /api/v1/todos
```

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `status` (optional): Filter by status (pending, in_progress, completed)
- `priority` (optional): Filter by priority (low, medium, high, urgent)
- `tag` (optional): Filter by tag name
- `search` (optional): Search in title and description
- `sort_by` (optional): Field to sort by (created_at, due_date, priority, title)
- `sort_order` (optional): asc or desc (default: desc)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Complete API design",
      "description": "Design RESTful API for todo app",
      "status": "in_progress",
      "priority": "high",
      "due_date": "2025-10-10T17:00:00Z",
      "completed_at": null,
      "created_at": "2025-10-07T10:30:00Z",
      "updated_at": "2025-10-07T11:00:00Z",
      "owner_id": "uuid",
      "assigned_to_id": "uuid",
      "tags": ["work", "api"],
      "position": 1
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

---

#### Create Todo
```
POST /api/v1/todos
```

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Complete API design",
  "description": "Design RESTful API for todo app",
  "status": "pending",
  "priority": "high",
  "due_date": "2025-10-10T17:00:00Z",
  "tags": ["work", "api"]
}
```

**Response (201 Created):** Todo object with generated id

**Errors:**
- 400: Invalid input (missing title, invalid enum values)

---

#### Get Todo by ID
```
GET /api/v1/todos/{todo_id}
```

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):** Todo object

**Errors:**
- 404: Todo not found
- 403: User doesn't have access to this todo

---

#### Update Todo
```
PATCH /api/v1/todos/{todo_id}
```

**Headers:** `Authorization: Bearer <token>`

**Request Body (all fields optional):**
```json
{
  "title": "Updated title",
  "description": "Updated description",
  "status": "in_progress",
  "priority": "urgent",
  "due_date": "2025-10-12T17:00:00Z",
  "tags": ["work", "api", "urgent"]
}
```

**Response (200 OK):** Updated todo object

**Errors:**
- 400: Invalid input
- 404: Todo not found
- 403: User is not the owner

---

#### Delete Todo
```
DELETE /api/v1/todos/{todo_id}
```

**Headers:** `Authorization: Bearer <token>`

**Response (204 No Content)**

**Errors:**
- 404: Todo not found
- 403: User is not the owner

---

#### Bulk Update Todos
```
PATCH /api/v1/todos/bulk
```

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "todo_ids": ["uuid1", "uuid2", "uuid3"],
  "updates": {
    "status": "completed",
    "priority": "low"
  }
}
```

**Response (200 OK):**
```json
{
  "updated_count": 3,
  "todos": [/* updated todo objects */]
}
```

**Errors:**
- 400: Invalid input
- 403: User doesn't own all specified todos

---

#### Reorder Todos
```
POST /api/v1/todos/reorder
```

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "todo_ids": ["uuid3", "uuid1", "uuid2"]
}
```

**Response (200 OK):**
```json
{
  "message": "Todos reordered successfully"
}
```

---

### Tag Endpoints

#### List User Tags
```
GET /api/v1/tags
```

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "work",
      "color": "#FF5733",
      "user_id": "uuid",
      "created_at": "2025-10-07T10:30:00Z"
    }
  ],
  "total": 5
}
```

---

#### Create Tag
```
POST /api/v1/tags
```

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "work",
  "color": "#FF5733"
}
```

**Response (201 Created):** Tag object

**Errors:**
- 400: Invalid input
- 409: Tag name already exists for user

---

#### Update Tag
```
PATCH /api/v1/tags/{tag_id}
```

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "work-important",
  "color": "#FF0000"
}
```

**Response (200 OK):** Updated tag object

---

#### Delete Tag
```
DELETE /api/v1/tags/{tag_id}
```

**Headers:** `Authorization: Bearer <token>`

**Response (204 No Content)**

**Note:** Removes tag from all todos but doesn't delete the todos

---

### Statistics Endpoints

#### Get User Statistics
```
GET /api/v1/stats
```

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "total_todos": 42,
  "completed_todos": 28,
  "pending_todos": 10,
  "in_progress_todos": 4,
  "completion_rate": 66.7,
  "todos_by_priority": {
    "low": 5,
    "medium": 20,
    "high": 15,
    "urgent": 2
  },
  "overdue_todos": 3,
  "due_today": 2,
  "due_this_week": 7
}
```

---

## Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Specific validation error"
    },
    "timestamp": "2025-10-07T10:30:00Z",
    "request_id": "uuid"
  }
}
```

### HTTP Status Codes
- **200 OK**: Successful GET/PATCH request
- **201 Created**: Successful POST request creating resource
- **204 No Content**: Successful DELETE or action with no return value
- **400 Bad Request**: Invalid input, validation errors
- **401 Unauthorized**: Missing or invalid authentication token
- **403 Forbidden**: Authenticated but not authorized
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Resource already exists (e.g., duplicate email)
- **422 Unprocessable Entity**: Semantic validation errors
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server-side error
- **503 Service Unavailable**: Temporary service outage

### Common Error Codes
- `INVALID_CREDENTIALS`: Login failed
- `TOKEN_EXPIRED`: JWT token expired
- `TOKEN_INVALID`: JWT token malformed or invalid
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `VALIDATION_ERROR`: Request validation failed
- `DUPLICATE_RESOURCE`: Resource already exists
- `UNAUTHORIZED_ACTION`: User not authorized for action
- `RATE_LIMIT_EXCEEDED`: Too many requests

---

## Rate Limiting

### Limits
- **Anonymous requests**: 100 requests per hour
- **Authenticated requests**: 1000 requests per hour
- **Burst limit**: 20 requests per minute

### Headers
Response includes rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1633612800
```

### Exceeded Rate Limit Response (429)
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retry_after": 3600
  }
}
```

---

## Security Considerations

### 1. Authentication
- Passwords hashed using bcrypt (cost factor: 12)
- JWT tokens signed with HS256 algorithm
- Access tokens expire after 1 hour
- Refresh tokens expire after 7 days
- Token blacklisting on logout

### 2. Authorization
- Users can only access their own todos
- Assignment feature requires both users' consent
- Admin role for future user management features

### 3. Input Validation
- All inputs validated using Pydantic models
- SQL injection prevention via ORM (SQLAlchemy)
- XSS prevention by sanitizing HTML in descriptions
- CSRF protection for stateful operations

### 4. Data Protection
- HTTPS required in production
- Password minimum requirements enforced
- Sensitive data never logged
- Database credentials in environment variables

### 5. CORS Configuration
```python
CORS_ORIGINS = [
    "http://localhost:3000",  # Development
    "https://yourdomain.com"   # Production
]
```

### 6. API Versioning
- Version in URL path (/api/v1/)
- Breaking changes require new version
- Deprecated versions supported for 6 months

---

## Implementation Recommendations

### Database Schema

**Users Table:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Todos Table:**
```sql
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_to_id UUID REFERENCES users(id) ON DELETE SET NULL,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed')),
    CONSTRAINT valid_priority CHECK (priority IN ('low', 'medium', 'high', 'urgent'))
);
```

**Tags Table:**
```sql
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, user_id)
);
```

**Todo_Tags Junction Table:**
```sql
CREATE TABLE todo_tags (
    todo_id UUID REFERENCES todos(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (todo_id, tag_id)
);
```

**Indexes:**
```sql
CREATE INDEX idx_todos_owner_id ON todos(owner_id);
CREATE INDEX idx_todos_status ON todos(status);
CREATE INDEX idx_todos_due_date ON todos(due_date);
CREATE INDEX idx_todos_owner_status ON todos(owner_id, status);
CREATE INDEX idx_tags_user_id ON tags(user_id);
```

### FastAPI Project Structure
```
todo-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Configuration and settings
│   ├── database.py             # Database connection
│   ├── dependencies.py         # Dependency injection
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── todo.py
│   │   └── tag.py
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── todo.py
│   │   ├── tag.py
│   │   └── auth.py
│   ├── routers/                # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── todos.py
│   │   ├── tags.py
│   │   └── stats.py
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── todo_service.py
│   │   └── user_service.py
│   ├── middleware/             # Custom middleware
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── rate_limit.py
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── security.py
│       └── validators.py
├── tests/
│   ├── unit/
│   └── integration/
├── migrations/                 # Alembic migrations
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Documentation

The API will auto-generate OpenAPI (Swagger) documentation available at:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

---

## Future Enhancements

### Phase 2 Features
1. **Collaboration**: Share todos with other users
2. **Comments**: Add comments to todos
3. **Attachments**: Upload files to todos
4. **Notifications**: Real-time updates via WebSocket
5. **Categories/Projects**: Organize todos into projects
6. **Recurring Tasks**: Support for recurring todos
7. **Subtasks**: Nested todo items
8. **Activity Log**: Audit trail of changes

### Phase 3 Features
1. **Team Workspaces**: Multiple users in shared workspace
2. **Permissions**: Role-based access control
3. **Integrations**: Calendar sync, email notifications
4. **Mobile API**: Optimized endpoints for mobile apps
5. **Analytics**: Advanced statistics and reports
6. **Search**: Full-text search with Elasticsearch
7. **Export/Import**: Backup and restore functionality

---

## Testing Requirements

### Unit Tests
- Test all service layer functions
- Mock database calls
- 80%+ code coverage

### Integration Tests
- Test all API endpoints
- Test authentication flows
- Test database transactions
- Test error scenarios

### Performance Tests
- Load testing with 1000+ concurrent users
- Response time < 200ms for 95th percentile
- Database query optimization

---

## Deployment Considerations

### Environment Variables
```
DATABASE_URL=postgresql://user:pass@localhost:5432/tododb
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
ENVIRONMENT=production
```

### Containerization (Docker)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Monitoring and Logging
- Structured JSON logging
- APM integration (e.g., New Relic, Datadog)
- Health check endpoint: `GET /health`
- Metrics endpoint: `GET /metrics` (Prometheus format)

---

## Conclusion

This RESTful API design provides a solid foundation for a scalable todo application with:
- Clean, intuitive endpoints following REST principles
- Comprehensive authentication and authorization
- Flexible todo management with tags and priorities
- Pagination, filtering, and search capabilities
- Strong security practices
- Clear error handling
- Detailed documentation

The design is production-ready and can be implemented using FastAPI and PostgreSQL with straightforward scalability to support thousands of users.
