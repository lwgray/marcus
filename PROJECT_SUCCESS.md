# Time Project - PROJECT SUCCESS Documentation

## Project Overview

The **Time Project** is a planned production-quality REST API for task management with authentication, user management, projects, tasks, and comments. This documentation describes the intended architecture and implementation approach.

**Status**: Project planned but not yet implemented. All tasks remain in "todo" status.

## Architecture Overview

### Technology Stack

- **Backend Framework**: FastAPI (Python)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: JWT tokens with bcrypt password hashing
- **API Style**: REST
- **Testing**: Pytest with >80% coverage target

### System Components

#### 1. Database Models

The system is designed around four core SQLAlchemy models:

**User Model**
- Fields: id, email, password_hash, created_at, updated_at
- Relationships: One-to-many with Projects, Tasks, Comments
- Features: Email validation, secure password storage

**Project Model**
- Fields: id, name, description, owner_id, created_at, updated_at
- Relationships: Belongs to User, has many Tasks
- Cascade rules: Proper cascade deletes configured

**Task Model**
- Fields: id, title, description, status, priority, project_id, assigned_to, created_at, updated_at, due_date
- Relationships: Belongs to Project and User, has many Comments
- Validation: Status and priority enums

**Comment Model**
- Fields: id, content, task_id, author_id, created_at, updated_at
- Relationships: Belongs to Task and User
- Features: Supports threaded discussions

#### 2. Authentication System

**User Registration Flow**
- Endpoint: `POST /api/auth/register`
- Input: email, password
- Validation: Email format, password strength
- Password hashing: bcrypt with salt
- Response: JWT token + user object

**User Login Flow**
- Endpoint: `POST /api/auth/login`
- Input: email, password
- Verification: bcrypt password comparison
- Response: JWT token + user object
- Security: Rate limiting on auth endpoints

**JWT Token Management**
- Algorithm: HS256 or RS256
- Expiration: Configurable (default 24 hours)
- Claims: user_id, email, issued_at, expires_at
- Refresh: Token refresh endpoint planned

#### 3. API Endpoints

All endpoints follow REST conventions with proper HTTP methods and status codes.

**Authentication Endpoints**
```
POST   /api/auth/register    - Create new user account
POST   /api/auth/login       - Authenticate and get token
POST   /api/auth/refresh     - Refresh JWT token
GET    /api/auth/me          - Get current user info
```

**Project Endpoints** (Requires authentication)
```
GET    /api/projects         - List user's projects
POST   /api/projects         - Create new project
GET    /api/projects/:id     - Get project details
PUT    /api/projects/:id     - Update project
DELETE /api/projects/:id     - Delete project
```

**Task Endpoints** (Requires authentication)
```
GET    /api/projects/:id/tasks       - List project tasks
POST   /api/projects/:id/tasks       - Create task
GET    /api/tasks/:id                - Get task details
PUT    /api/tasks/:id                - Update task
DELETE /api/tasks/:id                - Delete task
PATCH  /api/tasks/:id/status         - Update task status
PATCH  /api/tasks/:id/assign         - Assign task to user
```

**Comment Endpoints** (Requires authentication)
```
GET    /api/tasks/:id/comments       - List task comments
POST   /api/tasks/:id/comments       - Add comment
PUT    /api/comments/:id             - Update comment
DELETE /api/comments/:id             - Delete comment
```

## How It Works

### Request Flow

1. **Client Request** → API Gateway (FastAPI)
2. **Authentication Middleware** → Verify JWT token
3. **Route Handler** → Business logic layer
4. **Data Layer** → SQLAlchemy ORM operations
5. **Database** → PostgreSQL queries
6. **Response** → JSON serialization back to client

### Data Flow

```
User Registration:
Browser → POST /api/auth/register → Validate input → Hash password →
Create User record → Generate JWT → Return token + user

Task Creation:
Browser → POST /api/projects/123/tasks → Verify JWT → Check project ownership →
Validate task data → Create Task record → Return task object

Task Update:
Browser → PUT /api/tasks/456 → Verify JWT → Check task permissions →
Update Task record → Return updated task
```

### Security Model

- **Authentication**: JWT Bearer tokens in Authorization header
- **Authorization**: Role-based access control (RBAC)
  - Users can only access their own projects
  - Project owners can manage all project tasks
  - Task assignees can update task status
- **Input Validation**: Pydantic models for all requests
- **SQL Injection Prevention**: SQLAlchemy ORM parameterized queries
- **Password Security**: Bcrypt hashing with salt rounds
- **Rate Limiting**: Configured on authentication endpoints

## How to Run It

### Prerequisites

```bash
# System Requirements
- Python 3.9 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)
- virtualenv or venv

# Development Tools (optional)
- Docker (for containerized database)
- Postman or curl (for API testing)
```

### Setup Instructions

#### 1. Clone and Environment Setup

```bash
# Navigate to project directory
cd /Users/lwgray/dev/marcus/projects/time

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Database Setup

**Option A: Local PostgreSQL**
```bash
# Install PostgreSQL (if not already installed)
brew install postgresql  # macOS
# or use your system's package manager

# Start PostgreSQL service
brew services start postgresql

# Create database
createdb time_app

# Create database user
psql -c "CREATE USER time_user WITH PASSWORD 'secure_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE time_app TO time_user;"
```

**Option B: Docker PostgreSQL**
```bash
# Run PostgreSQL in Docker
docker run -d \
  --name time_postgres \
  -e POSTGRES_DB=time_app \
  -e POSTGRES_USER=time_user \
  -e POSTGRES_PASSWORD=secure_password \
  -p 5432:5432 \
  postgres:14-alpine

# Verify container is running
docker ps | grep time_postgres
```

#### 3. Configuration

```bash
# Create .env file
cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://time_user:secure_password@localhost:5432/time_app

# JWT Configuration
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Security
BCRYPT_ROUNDS=12

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
RELOAD=True

# CORS (adjust for production)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
EOF

# Secure the .env file
chmod 600 .env
```

#### 4. Database Migration

```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Generate initial migration
alembic revision --autogenerate -m "Initial database schema"

# Apply migrations
alembic upgrade head

# Verify tables created
psql time_app -c "\dt"
# Should show: users, projects, tasks, comments tables
```

#### 5. Start the Application

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

#### 6. Verify Installation

```bash
# Test health check endpoint
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "database": "connected"}

# View API documentation (OpenAPI/Swagger)
# Open in browser: http://localhost:8000/docs

# Alternative API docs (ReDoc)
# Open in browser: http://localhost:8000/redoc
```

### Quick Start Example

```bash
# Register a new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'

# Save the token from response
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Create a project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "My First Project",
    "description": "Testing the API"
  }'

# List projects
curl http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN"
```

## How to Test It

### Test Structure

The project follows a comprehensive testing strategy:

```
tests/
├── unit/                          # Fast, isolated tests
│   ├── test_models.py            # Database model tests
│   ├── test_auth.py              # Authentication logic tests
│   └── test_validation.py        # Input validation tests
├── integration/                   # API endpoint tests
│   ├── test_auth_endpoints.py    # Auth API tests
│   ├── test_project_endpoints.py # Project API tests
│   └── test_task_endpoints.py    # Task API tests
├── performance/                   # Load and performance tests
│   └── test_response_times.py    # <100ms target tests
└── conftest.py                    # Shared fixtures
```

### Running Tests

#### Run All Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Run full test suite
pytest

# Expected output:
# ======================== test session starts =========================
# collected 45 items
#
# tests/unit/test_models.py ........                            [ 17%]
# tests/unit/test_auth.py .......                               [ 33%]
# tests/integration/test_auth_endpoints.py .......               [ 50%]
# tests/integration/test_project_endpoints.py ........           [ 67%]
# tests/integration/test_task_endpoints.py ..........            [ 89%]
# tests/performance/test_response_times.py .....                 [100%]
#
# ======================== 45 passed in 3.24s =========================
```

#### Run Specific Test Categories
```bash
# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Performance tests only
pytest tests/performance/ -v

# Tests with specific marker
pytest -m "not slow"
```

#### Coverage Report
```bash
# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Expected output:
# ----------- coverage: platform darwin, python 3.11.5 -----------
# Name                       Stmts   Miss  Cover
# ----------------------------------------------
# src/__init__.py               0      0   100%
# src/models.py               120     10    92%
# src/auth.py                  85      8    91%
# src/routes/auth.py          110     15    86%
# src/routes/projects.py      135     18    87%
# src/routes/tasks.py         150     22    85%
# src/database.py              45      2    96%
# ----------------------------------------------
# TOTAL                       645     75    88%

# View detailed HTML report
open htmlcov/index.html
```

#### Test Database Setup
```bash
# Create test database
createdb time_app_test

# Run tests with test database
TEST_DATABASE_URL=postgresql://time_user:secure_password@localhost:5432/time_app_test pytest

# Tests should automatically:
# 1. Create tables before tests
# 2. Run tests in transactions
# 3. Rollback after each test
# 4. Clean up at the end
```

### Test Coverage Goals

- **Overall Target**: >80% code coverage
- **Critical Paths**: 100% coverage for:
  - Authentication logic
  - Password hashing/verification
  - JWT token generation/validation
  - Input validation
  - Database cascade operations

### Performance Testing

```bash
# Run performance tests
pytest tests/performance/ -v

# Expected results:
# - CRUD operations: <100ms response time
# - Authentication: <200ms response time
# - Database queries: Optimized with proper indexing
# - Connection pooling: Configured and tested

# Load testing (requires locust)
pip install locust
locust -f tests/load/locustfile.py
# Open http://localhost:8089 for UI
```

### Security Testing

```bash
# SQL injection tests
pytest tests/security/test_sql_injection.py

# Authentication tests
pytest tests/security/test_auth_security.py

# Rate limiting tests
pytest tests/security/test_rate_limiting.py

# All security tests should pass:
# ✓ SQL injection prevention verified
# ✓ Password hashing secure
# ✓ JWT validation working
# ✓ Rate limiting enforced
# ✓ Input sanitization active
```

## Non-Functional Requirements

### Performance Requirements
- Response times: <100ms for CRUD operations
- Database connection pooling configured
- Efficient queries with proper indexing
- Query optimization for N+1 problems

### Security Requirements
- JWT-based authentication
- Bcrypt password hashing (12+ rounds)
- Rate limiting on auth endpoints (5 attempts/minute)
- Input sanitization for all endpoints
- CORS configured properly
- SQL injection prevention via ORM

### Reliability Requirements
- Database connection retry logic
- Transaction management for complex operations
- Error handling with proper HTTP status codes
- Logging for debugging and monitoring

## Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string in .env
echo $DATABASE_URL

# Test connection manually
psql $DATABASE_URL -c "SELECT 1"
```

**Import Errors**
```bash
# Verify virtual environment is activated
which python
# Should show: /path/to/venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Migration Issues**
```bash
# Reset migrations (WARNING: drops all data)
alembic downgrade base
alembic upgrade head

# Check migration status
alembic current
alembic history
```

**JWT Token Errors**
```bash
# Verify SECRET_KEY is set
echo $SECRET_KEY

# Regenerate secret key
openssl rand -hex 32

# Update .env file with new key
```

**Port Already in Use**
```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)

# Or use different port
uvicorn main:app --port 8001
```

### Development Tips

1. **Use API Documentation**: Visit `/docs` for interactive Swagger UI
2. **Enable Debug Mode**: Set `DEBUG=True` in .env for detailed errors
3. **Check Logs**: Application logs are in `logs/app.log`
4. **Use Database GUI**: Tools like pgAdmin or DBeaver for inspecting data
5. **Postman Collection**: Import API endpoints for easier testing

## Project Status

**Current State**: Architecture designed, tasks planned, not yet implemented

**Completed**:
- ✓ Architecture design documented
- ✓ Database schema designed
- ✓ API endpoints specified
- ✓ Security requirements defined
- ✓ Testing strategy outlined

**Pending**:
- ☐ Database models implementation (Task: 1615085423674000490)
- ☐ User registration implementation (Tasks: 1615085429227259025, 1615085430879814812)
- ☐ User login implementation (Tasks: 1615085433991988400, 1615085435694875835)
- ☐ Security implementation (Task: 1615085440602211546)
- ☐ Performance optimization (Task: 1615085438932878543)
- ☐ Test suite implementation (Tasks: 1615085427423708293, 1615085432431707302, 1615085437271934149)

**Next Steps**:
1. Implement database models with SQLAlchemy
2. Set up FastAPI application structure
3. Implement authentication endpoints
4. Create test suite with >80% coverage
5. Add security features (rate limiting, input validation)
6. Optimize performance (<100ms response times)
7. Deploy to production environment

## Success Metrics

When fully implemented, success will be measured by:

1. **Functionality**: All API endpoints working as specified
2. **Security**: All security requirements met (JWT, bcrypt, rate limiting)
3. **Performance**: Response times <100ms for CRUD operations
4. **Quality**: >80% test coverage with all tests passing
5. **Documentation**: Complete API documentation via OpenAPI
6. **Reliability**: Error handling and logging in place
7. **Maintainability**: Clean code following best practices

## Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **JWT Best Practices**: https://tools.ietf.org/html/rfc8725
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Testing with Pytest**: https://docs.pytest.org/

---

**Document Version**: 1.0
**Last Updated**: 2025-10-06
**Status**: Planning phase - awaiting implementation
**Contact**: See project board for task assignments
