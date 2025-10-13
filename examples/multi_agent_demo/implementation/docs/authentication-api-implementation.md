# Authentication API Implementation Guide

## Overview

Complete JWT-based authentication system implemented with FastAPI, bcrypt password hashing, and refresh token management.

## API Endpoints

### Base URL: `/api/auth`

All authentication endpoints are prefixed with `/api/auth`.

---

### 1. POST /api/auth/register

Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecureP@ssw0rd123" <!-- pragma: allowlist secret -->
}
```

**Password Requirements:**
- 8-128 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

**Username Requirements:**
- 3-50 characters
- Alphanumeric and underscore only

**Success Response (201 Created):**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", <!-- pragma: allowlist secret -->
    "refresh_token": "a1b2c3d4e5f6...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": 1,
      "email": "user@example.com",
      "username": "johndoe",
      "is_active": true,
      "is_verified": false,
      "created_at": "2025-10-08T12:00:00Z",
      "last_login": "2025-10-08T12:00:00Z"
    }
  }
}
```

**Error Responses:**
- 400 Bad Request: Invalid input (validation error)
- 409 Conflict: Email or username already exists

---

### 2. POST /api/auth/login

Authenticate user and return tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecureP@ssw0rd123" <!-- pragma: allowlist secret -->
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", <!-- pragma: allowlist secret -->
    "refresh_token": "a1b2c3d4e5f6...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": 1,
      "email": "user@example.com",
      "username": "johndoe",
      "is_active": true,
      "is_verified": false,
      "created_at": "2025-10-08T12:00:00Z",
      "last_login": "2025-10-08T13:30:00Z"
    }
  }
}
```

**Error Responses:**
- 401 Unauthorized: Invalid credentials or inactive account

---

### 3. POST /api/auth/refresh

Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "a1b2c3d4e5f6..."
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", <!-- pragma: allowlist secret -->
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

**Error Responses:**
- 401 Unauthorized: Invalid, expired, or revoked refresh token

---

### 4. POST /api/auth/logout

Revoke refresh token and logout user.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "refresh_token": "a1b2c3d4e5f6..."
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Logout successful"
}
```

**Error Responses:**
- 401 Unauthorized: Invalid or missing token

---

### 5. GET /api/auth/me

Get current authenticated user's profile.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-10-08T12:00:00Z",
  "last_login": "2025-10-08T13:30:00Z"
}
```

**Error Responses:**
- 401 Unauthorized: Invalid or expired access token
- 404 Not Found: User not found

---

## Token Information

### Access Tokens
- **Expiration**: 15 minutes (900 seconds)
- **Algorithm**: HS256
- **Format**: JWT
- **Usage**: Include in Authorization header as `Bearer <token>`

**Access Token Payload:**
```json
{
  "sub": "johndoe",
  "user_id": 1,
  "email": "user@example.com",
  "roles": ["user"],
  "type": "access",
  "iat": 1696780800,
  "exp": 1696781700
}
```

### Refresh Tokens
- **Expiration**: 7 days
- **Storage**: Hashed (SHA-256) in database
- **Usage**: Use to obtain new access tokens
- **Revocation**: Can be revoked (logout)

---

## Authentication Flow

### Initial Registration/Login
1. User submits credentials → POST /auth/register or /auth/login
2. Server validates and returns both tokens
3. Client stores both tokens securely
4. Client uses access_token for API requests

### Making Authenticated Requests
1. Include access token in Authorization header: `Bearer <access_token>`
2. Server validates token and extracts user info
3. Request proceeds if valid

### Token Refresh Flow
1. Access token expires (15 minutes)
2. Client receives 401 Unauthorized
3. Client sends refresh_token → POST /auth/refresh
4. Server validates and returns new access_token
5. Client retries original request with new token

### Logout Flow
1. Client sends both tokens → POST /auth/logout
2. Server revokes refresh_token in database
3. Client discards both tokens

---

## Implementation Details

### Database Models

**RefreshToken Model:**
```python
- id: int (PK)
- user_id: int (FK to users)
- token_hash: str (SHA-256 hash)
- expires_at: datetime
- is_revoked: bool
- created_at: datetime
- revoked_at: datetime (nullable)
- ip_address: str (nullable)
- user_agent: str (nullable)
```

**User Model Extensions:**
- `is_active`: bool - Account status
- `is_verified`: bool - Email verification status
- `last_login`: datetime - Last successful login

### Service Layer

**AuthService Methods:**
- `register_user()` - User registration with tokens
- `login_user()` - Authentication with tokens
- `refresh_access_token()` - Token refresh
- `revoke_refresh_token()` - Logout
- `get_user_by_id()` - User retrieval
- `cleanup_expired_tokens()` - Maintenance task

### Security Features

1. **Password Hashing:** bcrypt with cost factor 12
2. **Token Storage:** Refresh tokens stored as SHA-256 hashes
3. **Input Validation:** Pydantic schemas with complexity requirements
4. **Error Handling:** Consistent error responses
5. **Token Expiration:** Short-lived access tokens
6. **Token Revocation:** Database-backed revocation

---

## Testing Examples

### cURL Examples

**Register:**
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"SecureP@ss123!"}' <!-- pragma: allowlist secret -->
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecureP@ss123!"}' <!-- pragma: allowlist secret -->
```

**Get Profile:**
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

**Refresh Token:**
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

**Logout:**
```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

---

## Integration Notes

### For Frontend Teams
- Store tokens securely (httpOnly cookies recommended for web)
- Implement automatic token refresh before expiration
- Handle 401 errors by attempting refresh
- Clear tokens on logout

### For Backend Teams
- Use `get_current_user` dependency for protected endpoints
- Access user info from dependency: `current_user["user_id"]`
- User roles available in: `current_user["roles"]`
- Check user permissions as needed

### For Test Teams
- 25 schema validation tests in `tests/unit/schemas/test_auth_schemas.py`
- 19 service logic tests in `tests/unit/services/test_auth_service.py`
- All endpoints follow OpenAPI spec in `docs/api/auth-api-spec.yaml`
- Mock authentication for unit tests
- Use test database for integration tests

---

## Files Created

### Models:
- `app/models/refresh_token.py` - RefreshToken model
- Updated `app/models/user.py` - Added is_active, is_verified, last_login

### Schemas:
- `app/schemas/auth.py` - Auth request/response schemas

### Services:
- `app/services/auth_service.py` - Authentication business logic

### Routes:
- `app/routes/auth.py` - FastAPI authentication endpoints

### Tests:
- `tests/unit/schemas/test_auth_schemas.py` - Schema validation tests (25 tests)
- `tests/unit/services/test_auth_service.py` - Service logic tests (19 tests)

---

## Dependencies

Required packages (already in use):
- `fastapi` - Web framework
- `pydantic` - Data validation
- `PyJWT` - JWT tokens
- `bcrypt` - Password hashing
- `sqlalchemy` - ORM
- `asyncpg` - Async PostgreSQL driver

---

## Configuration

Environment variables needed:
```bash
# JWT Configuration
JWT_SECRET_KEY=<strong-random-key>  # Required!
ACCESS_TOKEN_EXPIRE_MINUTES=15      # Optional (default: 15)
REFRESH_TOKEN_EXPIRE_DAYS=7         # Optional (default: 7)

# Database
DATABASE_URL=postgresql://user:pass@localhost/dbname <!-- pragma: allowlist secret -->

# Security
BCRYPT_COST_FACTOR=12               # Optional (default: 12)
```

---

## Next Steps

1. **Database Migration:** Create migration for refresh_tokens table
2. **Database Setup:** Configure database session dependency in routes
3. **Integration Testing:** Test full authentication flow
4. **Email Verification:** Implement email verification endpoints
5. **Password Reset:** Implement forgot/reset password flow
6. **Rate Limiting:** Add rate limiting to login endpoint
7. **Monitoring:** Add logging for security events

---

## Contact

- **Task ID:** 1616789800747009387
- **Agent:** agent_api (API Development Agent)
- **Implementation Date:** 2025-10-08
- **Dependencies Met:** task_database_models_design, task_user_authentication_design, task_user_management_design
