# User Authentication System Design

**Project:** todo1
**Task:** Design User Authentication
**Agent:** database-agent-1
**Date:** 2025-10-07
**Version:** 1.0

---

## Executive Summary

This document outlines the design for a secure user authentication system implementing register, login, and logout functionalities using JWT tokens and PostgreSQL database.

---

## 1. Database Schema

### 1.1 Users Table

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);
```

**Fields:**
- `id`: Primary key, auto-incrementing
- `email`: Unique identifier for user login, validated format
- `password_hash`: Bcrypt hashed password (cost factor 12)
- `first_name`, `last_name`: Optional user profile information
- `is_active`: Soft delete flag, allows account deactivation
- `is_verified`: Email verification status
- `created_at`: Account creation timestamp
- `updated_at`: Last account modification timestamp
- `last_login_at`: Tracks user engagement

### 1.2 Refresh Tokens Table

```sql
CREATE TABLE refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    device_info VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
```

**Fields:**
- `id`: Primary key
- `user_id`: Foreign key to users table
- `token_hash`: SHA-256 hash of refresh token for secure storage
- `device_info`: Device identifier for multi-device support
- `ip_address`: Source IP for security auditing
- `user_agent`: Browser/client information
- `expires_at`: Token expiration timestamp (7 days)
- `created_at`: Token issuance timestamp
- `revoked_at`: Token revocation timestamp for logout

### 1.3 Database Trigger for Updated Timestamp

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## 2. API Endpoints

### 2.1 Register User

**Endpoint:** `POST /api/auth/register`

**Request Body:**
```json
{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "first_name": "John",
    "last_name": "Doe"
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "data": {
        "user": {
            "id": 1,
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "is_verified": false,
            "created_at": "2025-10-07T10:30:00Z"
        },
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "a1b2c3d4e5f6...",
        "expires_in": 900
    }
}
```

**Validations:**
- Email format validation
- Email uniqueness check
- Password strength: minimum 8 characters, uppercase, lowercase, number, special character
- Required fields: email, password

**Process:**
1. Validate input data
2. Check email uniqueness
3. Hash password using bcrypt (cost factor 12)
4. Insert user record
5. Generate JWT access token (15 min expiry)
6. Generate refresh token (7 day expiry)
7. Store refresh token hash in database
8. Return user data and tokens

### 2.2 Login User

**Endpoint:** `POST /api/auth/login`

**Request Body:**
```json
{
    "email": "user@example.com",
    "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "user": {
            "id": 1,
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "last_login_at": "2025-10-07T10:30:00Z"
        },
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "a1b2c3d4e5f6...",
        "expires_in": 900
    }
}
```

**Error Response (401 Unauthorized):**
```json
{
    "success": false,
    "error": {
        "code": "INVALID_CREDENTIALS",
        "message": "Invalid email or password"
    }
}
```

**Process:**
1. Validate email format
2. Retrieve user by email
3. Verify user is active (`is_active = true`)
4. Compare password with bcrypt hash
5. Update `last_login_at` timestamp
6. Generate new JWT access token
7. Generate new refresh token
8. Store refresh token hash with device info
9. Return user data and tokens

**Security Notes:**
- Generic error message to prevent email enumeration
- Rate limiting: 5 failed attempts per 15 minutes per IP
- Account lockout after 10 failed attempts in 24 hours

### 2.3 Refresh Access Token

**Endpoint:** `POST /api/auth/refresh`

**Request Body:**
```json
{
    "refresh_token": "a1b2c3d4e5f6..."
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expires_in": 900
    }
}
```

**Process:**
1. Hash provided refresh token
2. Lookup token in database
3. Verify token not expired
4. Verify token not revoked
5. Generate new access token
6. Return new access token

### 2.4 Logout User

**Endpoint:** `POST /api/auth/logout`

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

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Successfully logged out"
}
```

**Process:**
1. Verify access token
2. Hash provided refresh token
3. Mark refresh token as revoked (`revoked_at = CURRENT_TIMESTAMP`)
4. Return success response

**Optional:** Logout from all devices
**Endpoint:** `POST /api/auth/logout/all`

Revokes all refresh tokens for the authenticated user.

---

## 3. JWT Token Structure

### 3.1 Access Token Payload

```json
{
    "sub": 1,
    "email": "user@example.com",
    "type": "access",
    "iat": 1696680000,
    "exp": 1696680900
}
```

**Claims:**
- `sub`: User ID (subject)
- `email`: User email
- `type`: Token type ("access")
- `iat`: Issued at timestamp
- `exp`: Expiration timestamp (15 minutes)

### 3.2 Token Configuration

- **Algorithm:** HS256 (HMAC with SHA-256)
- **Secret Key:** Stored in environment variable `JWT_SECRET_KEY` (minimum 32 characters)
- **Access Token Expiry:** 15 minutes
- **Refresh Token Expiry:** 7 days
- **Refresh Token Storage:** SHA-256 hash in database

---

## 4. Security Considerations

### 4.1 Password Security

- **Hashing Algorithm:** bcrypt
- **Cost Factor:** 12 (adjustable based on hardware)
- **Password Requirements:**
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 number
  - At least 1 special character
- **Password History:** Optional future enhancement to prevent password reuse

### 4.2 Token Security

- **Access Token:** Short-lived (15 min), stored in memory only
- **Refresh Token:**
  - Stored as SHA-256 hash in database
  -Httponly, Secure, SameSite=Strict cookie (recommended)
  - One-time use with rotation (future enhancement)
- **JWT Secret:** Strong random string, environment variable
- **Token Revocation:** Immediate via database flag

### 4.3 Protection Mechanisms

1. **Rate Limiting:**
   - Login: 5 attempts per 15 minutes per IP
   - Register: 3 attempts per hour per IP
   - Refresh: 10 attempts per 5 minutes per user

2. **Account Lockout:**
   - 10 failed login attempts in 24 hours
   - Unlock via email verification or admin intervention

3. **SQL Injection:** Parameterized queries only
4. **XSS Protection:** Input sanitization, output encoding
5. **CSRF Protection:** SameSite cookies, CSRF tokens
6. **HTTPS Only:** All authentication endpoints require TLS

### 4.4 Session Management

- Multiple concurrent sessions supported (multi-device)
- Device tracking via user agent and IP
- Ability to revoke specific device sessions
- Automatic cleanup of expired tokens (daily cron job)

---

## 5. Error Handling

### 5.1 Standard Error Response Format

```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "details": {}
    }
}
```

### 5.2 Authentication Error Codes

| Code | Status | Description |
|------|--------|-------------|
| INVALID_CREDENTIALS | 401 | Invalid email or password |
| ACCOUNT_LOCKED | 403 | Too many failed login attempts |
| ACCOUNT_INACTIVE | 403 | Account has been deactivated |
| TOKEN_EXPIRED | 401 | Access token has expired |
| TOKEN_INVALID | 401 | Token signature invalid |
| TOKEN_REVOKED | 401 | Refresh token has been revoked |
| EMAIL_EXISTS | 409 | Email already registered |
| WEAK_PASSWORD | 400 | Password doesn't meet requirements |
| INVALID_EMAIL | 400 | Email format invalid |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |

---

## 6. Integration Points

### 6.1 Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/todo1

# JWT Configuration
JWT_SECRET_KEY=<strong-random-secret-32-chars-min>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
BCRYPT_COST_FACTOR=12
PASSWORD_MIN_LENGTH=8

# Rate Limiting
RATE_LIMIT_LOGIN_ATTEMPTS=5
RATE_LIMIT_LOGIN_WINDOW_MINUTES=15
```

### 6.2 Dependencies for Backend Implementation

```
- bcrypt: Password hashing
- PyJWT: JWT token generation and verification
- SQLAlchemy: Database ORM
- psycopg2: PostgreSQL adapter
- python-dotenv: Environment configuration
- email-validator: Email validation
```

### 6.3 Frontend Integration

1. **Registration Flow:**
   - POST to `/api/auth/register`
   - Store access token in memory
   - Store refresh token in httpOnly cookie
   - Redirect to dashboard

2. **Login Flow:**
   - POST to `/api/auth/login`
   - Store tokens as above
   - Set Authorization header for API calls

3. **API Requests:**
   - Include `Authorization: Bearer <access_token>` header
   - Handle 401 responses by refreshing token
   - Retry original request with new token

4. **Logout Flow:**
   - POST to `/api/auth/logout` with refresh token
   - Clear tokens from memory and cookies
   - Redirect to login page

---

## 7. Database Migrations

### 7.1 Migration Script: 001_create_users_table.sql

```sql
-- Migration: Create users and authentication tables
-- Version: 001
-- Date: 2025-10-07

BEGIN;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Create refresh tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    device_info VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for refresh tokens
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- Create trigger function for updating updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;
```

### 7.2 Rollback Script: 001_create_users_table_down.sql

```sql
-- Rollback Migration 001
BEGIN;

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS users CASCADE;

COMMIT;
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

- Password hashing and verification
- JWT token generation and validation
- Email format validation
- Password strength validation

### 8.2 Integration Tests

- Complete registration flow
- Complete login flow
- Token refresh flow
- Logout flow
- Rate limiting enforcement
- Account lockout mechanism

### 8.3 Security Tests

- SQL injection attempts
- XSS payload injection
- CSRF token validation
- Brute force protection
- Token tampering detection

---

## 9. Architectural Decisions

### 9.1 Why JWT over Session-Based Auth?

**Chosen:** JWT (JSON Web Tokens)

**Rationale:**
- Stateless: No server-side session storage required
- Scalable: Works across distributed systems
- Cross-domain: Supports microservices architecture
- Mobile-friendly: Easy to use in mobile apps
- Performance: No database lookup for each request

**Trade-offs:**
- Cannot invalidate access tokens immediately (mitigated by short expiry)
- Slightly larger payload than session IDs
- Refresh token requires database storage

### 9.2 Why Bcrypt over Argon2?

**Chosen:** Bcrypt

**Rationale:**
- Mature and battle-tested (20+ years)
- Well-supported across all languages
- Automatic salt generation
- Adjustable cost factor for future-proofing
- Proven resistance to GPU attacks

**Alternative:** Argon2 is newer and more resistant to specialized hardware attacks, but bcrypt is sufficient for most use cases and has broader library support.

### 9.3 Token Expiry Times

**Access Token: 15 minutes**
- Balance between security and user experience
- Limits exposure window for stolen tokens
- Short enough to require refresh, limiting damage

**Refresh Token: 7 days**
- Allows "remember me" functionality
- Requires re-authentication weekly
- Long enough for good UX, short enough for security

---

## 10. Future Enhancements

### 10.1 Short-term (Next Sprint)

1. Email verification flow
2. Password reset via email
3. Account lockout notifications
4. Login history tracking

### 10.2 Medium-term (Next Quarter)

1. Two-factor authentication (2FA)
2. OAuth2 integration (Google, GitHub)
3. Password change endpoint
4. Session management dashboard
5. Refresh token rotation

### 10.3 Long-term (Future Roadmap)

1. Biometric authentication support
2. Risk-based authentication
3. Device fingerprinting
4. Anomaly detection
5. RBAC (Role-Based Access Control)

---

## 11. Deployment Checklist

- [ ] PostgreSQL database provisioned
- [ ] Environment variables configured
- [ ] JWT secret generated (cryptographically secure)
- [ ] Database migrations executed
- [ ] SSL/TLS certificates installed
- [ ] Rate limiting configured
- [ ] CORS policy configured
- [ ] Logging and monitoring enabled
- [ ] Backup strategy implemented
- [ ] Security headers configured
- [ ] Password policy documented for users

---

## 12. API Documentation Template

For integration with Swagger/OpenAPI:

```yaml
/api/auth/register:
  post:
    summary: Register a new user
    tags: [Authentication]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [email, password]
            properties:
              email:
                type: string
                format: email
              password:
                type: string
                format: password
                minLength: 8
              first_name:
                type: string
              last_name:
                type: string
    responses:
      201:
        description: User registered successfully
      400:
        description: Invalid input
      409:
        description: Email already exists
```

---

## Document Control

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-07 | database-agent-1 | Initial design |

**Approval:**
- [ ] Technical Lead Review
- [ ] Security Review
- [ ] Backend Team Review
- [ ] Frontend Team Review

**Next Steps:**
1. Review and approval of design
2. Backend implementation task creation
3. Frontend implementation task creation
4. Database migration execution
5. API endpoint implementation

---

**End of Document**
