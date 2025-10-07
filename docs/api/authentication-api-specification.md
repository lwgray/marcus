# User Authentication and Authorization - API Specification

## Overview
This document defines the complete API specification for user authentication and authorization using JWT tokens. It is derived from comprehensive test-driven design specifications.

## Authentication Flow Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ 1. Register/Login
       ▼
┌─────────────────────────────────────┐
│      Authentication Service         │
│  - Password validation & hashing    │
│  - JWT token generation             │
│  - Session management               │
└──────┬──────────────────┬──────────┘
       │                  │
       │ 2. Store        │ 3. Return tokens
       ▼                  ▼
┌─────────────┐    ┌──────────────┐
│  Database   │    │    Client    │
│  - Users    │    │ - Store      │
│  - Tokens   │    │   tokens     │
└─────────────┘    └──────┬───────┘
                          │
       4. API Request     │
       with token         │
                          ▼
┌──────────────────────────────────────┐
│    Protected API Endpoints           │
│  ┌────────────────────────────┐     │
│  │  Auth Middleware           │     │
│  │  - Validate token          │     │
│  │  - Check blacklist         │     │
│  │  - Extract user context    │     │
│  └────────────────────────────┘     │
└──────────────────────────────────────┘
```

## API Endpoints

### 1. User Registration

**Endpoint:** `POST /api/auth/register`

**Description:** Create a new user account with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "username": "testuser"  // optional
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "testuser",
    "created_at": "2025-01-01T00:00:00Z"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_expires_at": "2025-01-01T24:00:00Z"
}
```

**Error Responses:**

*400 Bad Request - Invalid Email:*
```json
{
  "success": false,
  "error": {
    "code": "INVALID_EMAIL",
    "message": "Email format is invalid",
    "field": "email"
  }
}
```

*400 Bad Request - Weak Password:*
```json
{
  "success": false,
  "error": {
    "code": "WEAK_PASSWORD",
    "message": "Password does not meet strength requirements",
    "requirements": [
      "Minimum 8 characters",
      "At least 1 uppercase letter",
      "At least 1 lowercase letter",
      "At least 1 number",
      "At least 1 special character"
    ],
    "field": "password"
  }
}
```

*409 Conflict - Duplicate Email:*
```json
{
  "success": false,
  "error": {
    "code": "EMAIL_EXISTS",
    "message": "Email address is already registered",
    "field": "email"
  }
}
```

*429 Too Many Requests:*
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many registration attempts",
    "retry_after": 3600
  }
}
```

**Rate Limiting:** 5 attempts per IP per hour

**Security Requirements:**
- Hash passwords using bcrypt or argon2 (minimum 12 salt rounds)
- Sanitize input to prevent XSS attacks
- Never return password or hash in response
- Log registration attempts for monitoring

---

### 2. User Login

**Endpoint:** `POST /api/auth/login`

**Description:** Authenticate user and receive access/refresh tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "remember_me": false  // optional
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "testuser",
    "last_login": "2025-01-01T00:00:00Z"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_expires_at": "2025-01-01T01:00:00Z",
  "refresh_token": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Error Responses:**

*401 Unauthorized - Invalid Credentials:*
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email or password is incorrect"
  }
}
```

*403 Forbidden - Account Disabled:*
```json
{
  "success": false,
  "error": {
    "code": "ACCOUNT_DISABLED",
    "message": "This account has been disabled",
    "contact_support": true
  }
}
```

*423 Locked - Account Locked:*
```json
{
  "success": false,
  "error": {
    "code": "ACCOUNT_LOCKED",
    "message": "Account temporarily locked due to multiple failed login attempts",
    "locked_until": "2025-01-01T01:00:00Z",
    "unlock_methods": [
      "Wait until lock expires",
      "Reset password via email"
    ]
  }
}
```

*429 Too Many Requests:*
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many login attempts. Please try again later.",
    "retry_after": 900
  }
}
```

**Rate Limiting:** 10 attempts per IP per 15 minutes

**Account Lockout Policy:**
- 5 failed attempts → 30 minute lock
- 10 failed attempts → 2 hour lock
- Send security alert email on lockout

**Security Requirements:**
- Use constant-time comparison for password verification
- Prevent timing attacks (same response time for all failures)
- Log all login attempts (success and failure)
- Update last_login timestamp on success

---

### 3. User Logout

**Endpoint:** `POST /api/auth/logout`

**Description:** Invalidate current session and revoke tokens.

**Request Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Request Body (optional):**
```json
{
  "refresh_token": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully logged out"
}
```

**Error Responses:**

*401 Unauthorized - Missing Token:*
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Access token is required"
  }
}
```

**Side Effects:**
- Add access token to blacklist
- Revoke refresh token in database
- Clear server-side session data
- Log logout event

---

### 4. Logout All Devices

**Endpoint:** `POST /api/auth/logout-all`

**Description:** Revoke all tokens and sessions for current user.

**Request Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully logged out from all devices",
  "sessions_revoked": 3
}
```

**Side Effects:**
- Revoke ALL refresh tokens for user
- Add all active access tokens to blacklist
- Send email notification

---

### 5. Token Refresh

**Endpoint:** `POST /api/auth/refresh`

**Description:** Obtain new access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_expires_at": "2025-01-01T01:00:00Z",
  "refresh_token": "550e8400-e29b-41d4-a716-446655440002",
  "refresh_token_expires_at": "2025-01-08T00:00:00Z"
}
```

**Error Responses:**

*401 Unauthorized - Token Expired:*
```json
{
  "success": false,
  "error": {
    "code": "REFRESH_TOKEN_EXPIRED",
    "message": "Refresh token has expired. Please login again.",
    "expired_at": "2025-01-01T00:00:00Z",
    "login_endpoint": "/api/auth/login"
  }
}
```

*401 Unauthorized - Token Revoked:*
```json
{
  "success": false,
  "error": {
    "code": "REFRESH_TOKEN_REVOKED",
    "message": "Refresh token has been revoked",
    "reason": "User logged out"
  }
}
```

*401 Unauthorized - Token Reuse Detected:*
```json
{
  "success": false,
  "error": {
    "code": "TOKEN_REUSE_DETECTED",
    "message": "Security breach detected. All sessions have been terminated.",
    "action_required": "Please login and change your password",
    "security_alert_sent": true
  }
}
```

**Token Rotation Policy:**
- Generate new refresh token on each use
- Revoke old refresh token immediately
- Link tokens via token_family_id for breach detection
- Detect and respond to token reuse (potential theft)

**Rate Limiting:** 30 attempts per token per hour, 100 per IP per hour

---

### 6. Forgot Password

**Endpoint:** `POST /api/auth/forgot-password`

**Description:** Initiate password reset flow via email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "If the email exists, a password reset link has been sent"
}
```

**Security:**
- Always return success (don't reveal if email exists)
- Generate secure reset token (UUID)
- Token expires in 1 hour
- Invalidate previous reset tokens

**Rate Limiting:** 3 attempts per email per hour, 10 per IP per hour

---

### 7. Reset Password

**Endpoint:** `POST /api/auth/reset-password`

**Description:** Complete password reset with token.

**Request Body:**
```json
{
  "token": "550e8400-e29b-41d4-a716-446655440003",
  "new_password": "NewSecurePass123!"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Password successfully reset. Please login with your new password.",
  "login_endpoint": "/api/auth/login"
}
```

**Error Responses:**

*400 Bad Request - Token Expired:*
```json
{
  "success": false,
  "error": {
    "code": "RESET_TOKEN_EXPIRED",
    "message": "Password reset link has expired. Please request a new one.",
    "forgot_password_endpoint": "/api/auth/forgot-password"
  }
}
```

**Side Effects:**
- Update password hash
- Mark reset token as used
- Revoke all existing sessions
- Send confirmation email
- Log security event

---

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP
);

CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
```

### Refresh Tokens Table

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    token_family_id UUID NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_family ON refresh_tokens(token_family_id);
```

### Token Blacklist Table

```sql
CREATE TABLE token_blacklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    reason VARCHAR(100)
);

CREATE UNIQUE INDEX idx_token_blacklist_jti ON token_blacklist(token_jti);
CREATE INDEX idx_token_blacklist_expires_at ON token_blacklist(expires_at);
```

### Password Reset Tokens Table

```sql
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP
);

CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
```

### Security Events Log Table

```sql
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES users(id),
    email VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_security_events_type ON security_events(event_type);
CREATE INDEX idx_security_events_user_id ON security_events(user_id);
CREATE INDEX idx_security_events_created_at ON security_events(created_at);
CREATE INDEX idx_security_events_ip ON security_events(ip_address);
```

---

## JWT Token Structure

### Access Token Payload

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "roles": ["user"],
  "permissions": ["read:todos", "write:todos"],
  "iat": 1704067200,
  "exp": 1704070800,
  "jti": "550e8400-e29b-41d4-a716-446655440010",
  "type": "access"
}
```

**Token Lifespan:** 15 minutes - 1 hour

### Refresh Token Payload

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "token_id": "550e8400-e29b-41d4-a716-446655440001",
  "token_family_id": "550e8400-e29b-41d4-a716-446655440020",
  "iat": 1704067200,
  "exp": 1706659200,
  "type": "refresh"
}
```

**Token Lifespan:** 7-30 days (configurable)

---

## Middleware Flow

### Token Validation Middleware

```
1. Extract Authorization header
   ↓
2. Validate format: "Bearer <token>"
   ↓
3. Verify JWT signature
   ↓
4. Check expiration (exp claim)
   ↓
5. Verify token type = "access"
   ↓
6. Check token blacklist
   ↓
7. Extract user context
   ↓
8. Attach to request object
   ↓
9. Continue to route handler
```

---

## Security Considerations

### Password Storage
- **Algorithm:** bcrypt or argon2
- **Salt Rounds:** Minimum 12
- **Never** store plain text passwords
- **Never** return password hashes in API responses

### Token Security
- **Signing Algorithm:** HS256 (shared secret) or RS256 (public/private key)
- **JTI Claim:** Required for blacklist functionality
- **Rotation:** Refresh tokens rotate on use
- **Revocation:** Support for immediate token revocation

### Rate Limiting
- **Registration:** 5 per IP per hour
- **Login:** 10 per IP per 15 minutes
- **Forgot Password:** 3 per email per hour, 10 per IP per hour
- **Token Refresh:** 30 per token per hour, 100 per IP per hour

### Account Protection
- **Lockout:** 5 failed logins → 30 min, 10 failed → 2 hours
- **Timing Attacks:** Constant-time password comparison
- **User Enumeration:** Generic error messages
- **Token Reuse:** Detect and respond to potential theft

### Monitoring & Logging
- Log all authentication events
- Monitor failed login patterns
- Alert on suspicious activity
- Track token reuse attempts
- Audit trail for security events

---

## Implementation Checklist

- [ ] Implement user registration with password hashing
- [ ] Implement login with JWT generation
- [ ] Implement logout with token blacklisting
- [ ] Implement token refresh with rotation
- [ ] Implement password reset flow
- [ ] Set up database schema
- [ ] Create token validation middleware
- [ ] Implement rate limiting
- [ ] Implement account lockout mechanism
- [ ] Set up security event logging
- [ ] Configure email service for notifications
- [ ] Add token reuse detection
- [ ] Write comprehensive tests
- [ ] Security audit and penetration testing
- [ ] Documentation and API client examples
