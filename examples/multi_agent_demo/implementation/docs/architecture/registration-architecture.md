# User Registration Architecture

## Overview

This document describes the architecture and design decisions for the user registration feature in the Task Management API.

## Architecture Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /api/v1/auth/register
       │ {email, password, full_name?}
       ▼
┌─────────────────────────────────┐
│     FastAPI Application         │
│  ┌───────────────────────────┐  │
│  │  Registration Endpoint    │  │
│  │  /auth/register           │  │
│  └───────────┬───────────────┘  │
│              │                   │
│              ▼                   │
│  ┌───────────────────────────┐  │
│  │  Request Validation       │  │
│  │  (Pydantic Schema)        │  │
│  │  - Email format           │  │
│  │  - Password strength      │  │
│  │  - Field requirements     │  │
│  └───────────┬───────────────┘  │
│              │                   │
│              ▼                   │
│  ┌───────────────────────────┐  │
│  │  Business Logic Layer     │  │
│  │  - Check email uniqueness │  │
│  │  - Hash password (bcrypt) │  │
│  │  - Create user record     │  │
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

**Purpose**: Validate and sanitize incoming registration requests.

**Implementation**: Pydantic `UserRegisterRequest` schema

**Validations**:
- Email format validation (RFC 5322)
- Password strength requirements:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one digit
  - At least one special character
- Full name length limit (255 chars)

**Location**: `app/schemas/auth.py`

### 2. Business Logic Layer

**Purpose**: Handle registration workflow and business rules.

**Responsibilities**:
1. **Email Uniqueness Check**
   - Query database for existing email
   - Return 409 Conflict if email exists
   - Prevent duplicate accounts

2. **Password Hashing**
   - Use bcrypt with cost factor 12
   - Never store plain text passwords
   - Generate secure salt automatically

3. **User Creation**
   - Create User model instance
   - Set `is_active=True` by default
   - Set `is_superuser=False` by default
   - Persist to database via SQLAlchemy session

4. **JWT Token Generation**
   - Create token with user ID as subject
   - Set expiration (24 hours)
   - Sign with secret key (HS256 algorithm)
   - Include in response for immediate authentication

**Location**: `app/services/auth_service.py` (to be implemented)

### 3. Data Access Layer

**Purpose**: Persist user data to database.

**Implementation**: SQLAlchemy ORM with User model

**Operations**:
- `db.query(User).filter(User.email == email).first()` - Check existing
- `db.add(user)` - Add new user
- `db.commit()` - Persist changes
- `db.refresh(user)` - Reload user with generated ID

**Location**: `app/models/user.py`

## Security Considerations

### Password Security

1. **Hashing Algorithm**: bcrypt
   - Industry-standard password hashing
   - Built-in salt generation
   - Configurable cost factor (12 = 2^12 iterations)
   - Resistant to rainbow table attacks

2. **Password Strength Enforcement**
   - Enforced at validation layer (Pydantic)
   - Cannot be bypassed by API consumers
   - Clear error messages for weak passwords

3. **Password Storage**
   - Never logged or returned in responses
   - Stored only as bcrypt hash
   - Original password discarded after hashing

### Email Security

1. **Format Validation**
   - Pydantic EmailStr validates RFC 5322
   - Prevents injection attacks via malformed emails

2. **Case Normalization**
   - Store emails in lowercase
   - Prevent duplicate accounts via case variations

3. **Uniqueness Constraint**
   - Database-level unique constraint
   - Prevents race conditions
   - Transaction-safe

### JWT Token Security

1. **Token Generation**
   - Cryptographically secure secret key (256 bits minimum)
   - HS256 algorithm (HMAC with SHA-256)
   - Short expiration (24 hours)

2. **Token Claims**
   - `sub`: User ID (subject)
   - `exp`: Expiration timestamp
   - `iat`: Issued at timestamp

3. **Secret Key Management**
   - Stored in environment variable
   - Never committed to source control
   - Rotated periodically

## Error Handling

### Validation Errors (400 Bad Request)

Returned when request data fails Pydantic validation:
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must contain at least one uppercase letter",
      "type": "value_error"
    }
  ]
}
```

### Conflict Errors (409 Conflict)

Returned when email already exists:
```json
{
  "detail": "Email already registered"
}
```

### Server Errors (500 Internal Server Error)

Returned for unexpected errors:
- Database connection failures
- Token generation failures
- Unexpected exceptions

All errors logged for debugging and monitoring.

## Performance Considerations

### Database Queries

1. **Email Uniqueness Check**
   - Single SELECT query with index on email column
   - O(log n) complexity due to B-tree index
   - Typical latency: <5ms

2. **User Creation**
   - Single INSERT query
   - Triggers auto-increment for ID
   - Typical latency: <10ms

### Password Hashing

- Bcrypt cost factor 12 = ~200-300ms per hash
- Intentionally slow to prevent brute force
- Acceptable for registration (one-time operation)
- Consider async processing for high throughput

### JWT Token Generation

- Minimal overhead (<1ms)
- In-memory operation
- No database queries required

### Total Estimated Latency

- Validation: <1ms
- Email check: ~5ms
- Password hashing: ~250ms
- User creation: ~10ms
- Token generation: <1ms
- **Total: ~265ms** (well under 100ms target for most operations)

## API Contract

### Endpoint

```
POST /api/v1/auth/register
```

### Request Headers

```
Content-Type: application/json
```

### Request Body

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",  // pragma: allowlist secret
  "full_name": "John Doe"  // Optional
}
```

### Success Response (201 Created)

```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Response Headers

```
Content-Type: application/json
Location: /api/v1/users/1
```

## Testing Strategy

### Unit Tests

1. **Schema Validation Tests**
   - Valid email formats
   - Invalid email formats
   - Password strength requirements
   - Field length limits

2. **Service Layer Tests** (with mocked database)
   - Successful registration flow
   - Duplicate email handling
   - Password hashing verification
   - JWT token generation

### Integration Tests

1. **End-to-End Registration**
   - POST to /auth/register with valid data
   - Verify 201 response
   - Verify user created in database
   - Verify password is hashed
   - Verify token works for authentication

2. **Error Scenarios**
   - Duplicate email returns 409
   - Weak password returns 400
   - Invalid email returns 400

### Security Tests

1. **Password Storage**
   - Verify password never returned in response
   - Verify password stored as bcrypt hash
   - Verify hash format (bcrypt $2b$ prefix)

2. **SQL Injection**
   - Attempt injection in email field
   - Attempt injection in full_name field
   - Verify SQLAlchemy parameterization prevents attacks

3. **Token Security**
   - Verify token signature
   - Verify token expiration enforced
   - Verify token contains correct claims

## Dependencies

### Python Packages

- `fastapi` - Web framework
- `pydantic` - Request/response validation
- `pydantic[email]` - Email validation
- `sqlalchemy` - ORM
- `passlib[bcrypt]` - Password hashing
- `python-jose[cryptography]` - JWT token handling

### Environment Variables

```bash
# Required
SECRET_KEY=<256-bit-random-key>  # For JWT signing
DATABASE_URL=postgresql://user:pass@host/dbname  # pragma: allowlist secret

# Optional
TOKEN_EXPIRE_HOURS=24  # Default: 24
BCRYPT_ROUNDS=12       # Default: 12
```

## Deployment Considerations

### Database Migrations

Ensure User table exists with proper constraints:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_users_email ON users(email);
```

### Environment Setup

1. Generate secure SECRET_KEY:
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

2. Set environment variables in deployment platform

3. Verify database connectivity before starting app

### Monitoring

Monitor these metrics:
- Registration success rate
- Average registration latency
- 409 Conflict rate (duplicate emails)
- 400 Bad Request rate (validation failures)
- Password hash timing (for performance tuning)

## Future Enhancements

1. **Email Verification**
   - Send confirmation email
   - Require email verification before activation
   - Add `email_verified` field

2. **Rate Limiting**
   - Prevent registration spam
   - Limit attempts per IP address
   - Implement CAPTCHA for suspicious activity

3. **OAuth Integration**
   - Support Google/GitHub login
   - Link OAuth accounts to user records

4. **Multi-factor Authentication**
   - Optional MFA during registration
   - TOTP or SMS verification

5. **Password Policies**
   - Configurable password requirements
   - Password history to prevent reuse
   - Password expiration

## References

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [RFC 7519 - JSON Web Token](https://tools.ietf.org/html/rfc7519)
- [bcrypt Wikipedia](https://en.wikipedia.org/wiki/Bcrypt)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
