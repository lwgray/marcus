# User Login Architecture

## Overview

This document describes the architecture and design decisions for the user login feature in the Task Management API.

## Architecture Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /api/v1/auth/login
       │ {email, password}
       ▼
┌─────────────────────────────────┐
│     FastAPI Application         │
│  ┌───────────────────────────┐  │
│  │  Login Endpoint           │  │
│  │  /auth/login              │  │
│  └───────────┬───────────────┘  │
│              │                   │
│              ▼                   │
│  ┌───────────────────────────┐  │
│  │  Request Validation       │  │
│  │  (Pydantic Schema)        │  │
│  │  - Email format           │  │
│  │  - Required fields        │  │
│  └───────────┬───────────────┘  │
│              │                   │
│              ▼                   │
│  ┌───────────────────────────┐  │
│  │  Authentication Logic     │  │
│  │  - Lookup user by email   │  │
│  │  - Verify password hash   │  │
│  │  - Check account active   │  │
│  │  - Generate JWT token     │  │
│  └───────────┬───────────────┘  │
│              │                   │
│              ▼                   │
│  ┌───────────────────────────┐  │
│  │  Data Access Layer        │  │
│  │  (SQLAlchemy ORM)         │  │
│  └───────────┬───────────────┘  │
└──────────────┼───────────────────┘
               │
               ▼
       ┌───────────────┐
       │   PostgreSQL  │
       │   Database    │
       │   (users      │
       │    table)     │
       └───────────────┘
```

## Component Design

### 1. Request Validation Layer

**Purpose**: Validate incoming login requests.

**Implementation**: Pydantic `LoginRequest` schema

**Validations**:
- Email format validation (RFC 5322)
- Password field presence (no strength check on login)
- No field length restrictions (handled during registration)

**Location**: `app/schemas/auth.py`

### 2. Authentication Logic Layer

**Purpose**: Verify user credentials and manage sessions.

**Workflow**:

1. **User Lookup**
   - Query database: `SELECT * FROM users WHERE email = ?`
   - Use indexed email column for O(log n) lookup
   - Return 401 if user not found (don't reveal whether email exists)

2. **Password Verification**
   - Use `passlib.verify()` with stored bcrypt hash
   - Constant-time comparison prevents timing attacks
   - Return 401 if password doesn't match
   - Use same error message as "user not found" to prevent user enumeration

3. **Account Status Check**
   - Verify `is_active = True`
   - Return 403 Forbidden if account inactive
   - Different status code helps distinguish deactivated accounts

4. **JWT Token Generation**
   - Create token with user ID as subject
   - Set expiration (24 hours from now)
   - Sign with secret key (HS256 algorithm)
   - Include in response

**Location**: `app/services/auth_service.py` (to be implemented)

### 3. Data Access Layer

**Purpose**: Retrieve user records from database.

**Query Pattern**:
```python
user = db.query(User)\
    .filter(User.email == email.lower())\
    .first()
```

**Optimizations**:
- Email column has B-tree index
- Use `.first()` instead of `.all()` to stop after first match
- Email comparison is case-insensitive

**Location**: `app/models/user.py`

## Security Considerations

### Preventing User Enumeration

**Problem**: Attackers can determine which emails are registered by observing different error messages.

**Solution**: Use identical error messages and response times for:
- User not found
- Invalid password

```python
# BAD - Reveals whether email exists
if not user:
    return 404, "Email not found"
if not verify_password(password, user.hashed_password):
    return 401, "Invalid password"

# GOOD - Same error for both cases
if not user or not verify_password(password, user.hashed_password):
    return 401, "Invalid email or password"
```

### Preventing Timing Attacks

**Problem**: Attackers can measure response time differences to determine if email exists.

**Solution**:
1. Always perform password hash verification, even if user doesn't exist
2. Use constant-time string comparison for email
3. Use bcrypt's built-in constant-time verification

```python
# Always hash a dummy password to maintain consistent timing
if not user:
    # Hash a dummy value to maintain timing consistency
    hash_password("dummy_password_for_timing")
    return 401, "Invalid email or password"

if not verify_password(password, user.hashed_password):
    return 401, "Invalid email or password"
```

### Password Security

1. **Verification Method**: bcrypt
   - Uses `passlib.verify(plain_password, hashed_password)`
   - Automatically handles salt extraction from hash
   - Constant-time comparison built-in

2. **No Password in Logs**
   - Never log password field
   - Exclude from Pydantic model serialization
   - Sanitize error messages

3. **Brute Force Protection** (Future Enhancement)
   - Rate limiting on login endpoint
   - Account lockout after N failed attempts
   - CAPTCHA after threshold

### JWT Token Security

Same as registration:
- Cryptographically secure secret key
- HS256 algorithm
- 24-hour expiration
- Include user ID in `sub` claim

### Account Status

Separate error codes:
- 401 Unauthorized: Invalid credentials
- 403 Forbidden: Account inactive

This allows frontend to show appropriate messages to users.

## Error Handling

### Validation Errors (400 Bad Request)

Returned when request data fails validation:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### Authentication Errors (401 Unauthorized)

Returned for invalid credentials:
```json
{
  "detail": "Invalid email or password"
}
```

**Important**: Same message for both "user not found" and "wrong password" to prevent user enumeration.

### Account Status Errors (403 Forbidden)

Returned when account is inactive:
```json
{
  "detail": "Account is inactive. Please contact support."
}
```

### Server Errors (500 Internal Server Error)

Returned for unexpected errors:
- Database connection failures
- Token generation failures
- Unexpected exceptions

## Performance Considerations

### Database Queries

1. **User Lookup**
   - Single SELECT with email index
   - O(log n) complexity
   - Typical latency: ~5ms

### Password Verification

- Bcrypt cost factor 12 = ~200-300ms
- Intentionally slow to prevent brute force
- Must be balanced with user experience
- Consider async processing for high concurrency

### JWT Token Generation

- Minimal overhead (<1ms)
- In-memory operation

### Total Estimated Latency

- Validation: <1ms
- User lookup: ~5ms
- Password verification: ~250ms
- Token generation: <1ms
- **Total: ~256ms**

## API Contract

### Endpoint

```
POST /api/v1/auth/login
```

### Request Headers

```
Content-Type: application/json
```

### Request Body

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"  // pragma: allowlist secret
}
```

### Success Response (200 OK)

```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",  // pragma: allowlist secret
  "token_type": "bearer"
}
```

### Response Headers

```
Content-Type: application/json
```

## Differences from Registration

| Aspect | Registration | Login |
|--------|-------------|-------|
| Password validation | Full strength check | Only presence check |
| Email uniqueness | Must be unique (409 if exists) | Must exist (401 if not found) |
| Response code | 201 Created | 200 OK |
| User creation | Creates new user | Retrieves existing user |
| Account activation | Auto-activates | Checks is_active |

## Testing Strategy

### Unit Tests

1. **Schema Validation Tests**
   - Valid email formats
   - Missing email/password
   - Invalid email formats

2. **Service Layer Tests** (with mocked database)
   - Successful login flow
   - Invalid email handling
   - Invalid password handling
   - Inactive account handling
   - Password verification
   - JWT token generation

### Integration Tests

1. **End-to-End Login**
   - Register user first
   - POST to /auth/login with correct credentials
   - Verify 200 response
   - Verify token works for authenticated endpoints
   - Verify token expiration

2. **Error Scenarios**
   - Non-existent email returns 401
   - Wrong password returns 401
   - Same error message for both
   - Inactive account returns 403
   - Invalid email format returns 400

### Security Tests

1. **User Enumeration Prevention**
   - Verify same error for invalid email and wrong password
   - Measure response times are similar
   - Check no information leakage in error messages

2. **Timing Attack Prevention**
   - Time responses for existing vs non-existing users
   - Verify timing difference is < 50ms
   - Test with multiple requests

3. **Token Security**
   - Verify token signature
   - Verify token expiration
   - Verify token claims (sub, exp, iat)
   - Test with invalid/expired tokens

## Rate Limiting (Future Enhancement)

Recommended limits for production:
- 5 attempts per IP per 15 minutes
- 10 attempts per email per hour
- Progressive backoff after failures
- CAPTCHA after 3 failed attempts

## Integration with Frontend

### Successful Login Flow

1. Frontend sends POST to `/auth/login`
2. Backend returns 200 with token
3. Frontend stores token in:
   - Memory (for current session)
   - localStorage/sessionStorage (for persistence)
   - HTTP-only cookie (most secure)
4. Frontend includes token in subsequent requests:
   ```
   Authorization: Bearer <token>
   ```

### Error Handling

- 401: Show "Invalid credentials" message
- 403: Show "Account inactive" with support contact
- 400: Show validation errors inline
- 500: Show generic "Try again later" message

## Dependencies

Same as registration:
- `fastapi` - Web framework
- `pydantic` - Request/response validation
- `sqlalchemy` - ORM
- `passlib[bcrypt]` - Password verification
- `python-jose[cryptography]` - JWT handling

## Monitoring

Track these metrics:
- Login success rate
- Login failure rate
- Average login latency
- Failed login patterns (potential attacks)
- Inactive account login attempts

## Future Enhancements

1. **Multi-Factor Authentication**
   - TOTP (Time-based One-Time Password)
   - SMS verification
   - Email verification codes

2. **Session Management**
   - Refresh tokens for longer sessions
   - Token revocation on logout
   - Multiple device sessions

3. **Account Recovery**
   - Password reset via email
   - Security questions
   - Account unlock procedures

4. **Audit Logging**
   - Log all login attempts
   - Track IP addresses and user agents
   - Detect suspicious patterns

## References

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Timing Attack Prevention](https://codahale.com/a-lesson-in-timing-attacks/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
