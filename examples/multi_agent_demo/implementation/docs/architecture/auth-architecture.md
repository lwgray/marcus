# Authentication Architecture - Design Decisions

## Overview
This document outlines the architectural decisions for the user authentication system in the Task Management API.

## Core Design Decisions

### 1. Authentication Strategy: JWT (JSON Web Tokens)

**Decision**: Use JWT tokens for stateless authentication

**Rationale**:
- **Stateless**: No server-side session storage required, enabling horizontal scaling
- **Self-contained**: Token contains all necessary user information
- **Industry Standard**: Well-supported across languages and frameworks
- **RESTful**: Aligns with REST API principles (stateless communication)
- **Mobile-friendly**: Easy to use in mobile apps and SPAs

**Trade-offs**:
- Tokens cannot be invalidated before expiration (mitigated with short expiration times)
- Slightly larger payload than session IDs
- Requires careful secret key management

**Implementation Notes**:
- Token expiration: 24 hours (configurable)
- Secret key stored in environment variables
- Algorithm: HS256 (HMAC with SHA-256)

### 2. Password Security: bcrypt Hashing

**Decision**: Use bcrypt for password hashing

**Rationale**:
- **Adaptive**: Cost factor can be increased as hardware improves
- **Salt included**: Automatically generates and stores salt with hash
- **Proven security**: Industry-standard, resistant to rainbow table attacks
- **Slow by design**: Makes brute-force attacks computationally expensive

**Implementation Notes**:
- Cost factor: 12 rounds (balance between security and performance)
- Passwords never stored in plain text
- Minimum password length: 8 characters (enforced at validation layer)

### 3. API Design Pattern: RESTful Endpoints

**Decision**: Follow REST principles for authentication endpoints

**Endpoints**:
```
POST /api/auth/login      - User authentication
GET  /api/auth/me         - Get current user profile
```

**Rationale**:
- **Predictable**: Standard HTTP methods and status codes
- **Discoverable**: Clear resource-based URLs
- **Cacheable**: GET /auth/me can be cached with token as cache key
- **Consistent**: Matches pattern for other API resources

### 4. Request/Response Format: JSON

**Decision**: Use JSON for all request and response bodies

**Login Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"  # pragma: allowlist secret
}
```

**Login Response (Success)**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Error Response**:
```json
{
  "error": "Invalid email or password"
}
```

**Rationale**:
- Ubiquitous format, supported by all clients
- Human-readable for debugging
- Easy to validate and parse

### 5. Authorization Header Format: Bearer Token

**Decision**: Use Authorization: Bearer <token> header for authenticated requests

**Example**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Rationale**:
- **Standard**: RFC 6750 (OAuth 2.0 Bearer Token Usage)
- **Secure**: Not included in URLs (prevents leaking in logs/history)
- **Framework support**: Native support in most HTTP libraries

### 6. Error Handling Strategy

**Decision**: Use HTTP status codes with consistent error format

**Status Codes**:
- `200 OK`: Successful login or profile retrieval
- `401 Unauthorized`: Invalid credentials or missing/invalid token
- `422 Unprocessable Entity`: Validation errors (malformed email, short password)

**Error Response Format**:
```json
{
  "error": "Error message",
  "details": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

**Rationale**:
- Clear distinction between authentication failures and validation errors
- Consistent error format across all endpoints
- Detailed validation feedback for client-side error handling

## Data Models

### User Model

**Fields**:
- `id` (integer): Primary key, auto-incrementing
- `email` (string): Unique, indexed, validated format
- `password_hash` (string): bcrypt hash, never exposed in API
- `full_name` (string): Optional display name
- `created_at` (timestamp): Account creation time
- `updated_at` (timestamp): Last modification time

**Database Constraints**:
- `email`: UNIQUE, NOT NULL, indexed for fast lookups
- `password_hash`: NOT NULL
- `created_at`: NOT NULL, default CURRENT_TIMESTAMP

### JWT Token Payload

**Claims**:
```json
{
  "user_id": 1,
  "email": "user@example.com",
  "exp": 1706198400,
  "iat": 1706112000
}
```

- `user_id`: For quick user lookup without DB query
- `email`: For logging/debugging
- `exp`: Expiration timestamp (Unix epoch)
- `iat`: Issued at timestamp (Unix epoch)

## Security Considerations

### 1. Password Requirements
- Minimum length: 8 characters
- Recommended: Mix of uppercase, lowercase, numbers, symbols (enforced client-side)
- Stored as bcrypt hash with cost factor 12

### 2. Token Security
- Secret key: Strong random string, stored in environment variables
- Never commit secret keys to version control
- Rotate secret keys periodically (forces re-authentication)
- Short expiration time (24h) to limit exposure window

### 3. Transport Security
- HTTPS required in production (TLS 1.2+)
- Tokens transmitted in headers, not URL parameters
- No sensitive data in logs or error messages

### 4. Rate Limiting (Future Enhancement)
- Limit login attempts per IP: 5 attempts per 15 minutes
- Prevents brute-force attacks
- Returns 429 Too Many Requests with Retry-After header

### 5. Input Validation
- Email format validation (RFC 5322 compliant)
- Password length validation
- SQL injection prevention via parameterized queries
- XSS prevention via proper escaping

## Integration Points

### For Frontend Developers
1. **Login Flow**:
   - POST credentials to `/api/auth/login`
   - Store returned token in localStorage or sessionStorage
   - Include token in Authorization header for all authenticated requests

2. **Profile Retrieval**:
   - GET `/api/auth/me` with Bearer token
   - Use for displaying current user info
   - Cache response to minimize API calls

3. **Error Handling**:
   - 401 responses: Redirect to login page
   - 422 responses: Display field-level validation errors
   - Network errors: Show retry option

### For Backend Developers
1. **Authentication Middleware**:
   - Extract token from Authorization header
   - Verify token signature and expiration
   - Attach user object to request context
   - Return 401 if token invalid/missing

2. **Protected Endpoints**:
   - Apply auth middleware to all endpoints requiring authentication
   - Access current user via request context
   - Pattern: `@require_auth` decorator or middleware

3. **Database Integration**:
   - User table with email uniqueness constraint
   - Index on email for fast login lookups
   - Never expose password_hash in API responses

## Future Enhancements

1. **Refresh Tokens**: Long-lived refresh tokens to obtain new access tokens without re-login
2. **Multi-Factor Authentication (MFA)**: TOTP-based 2FA for enhanced security
3. **OAuth2/Social Login**: Google, GitHub integration
4. **Password Reset Flow**: Email-based password reset
5. **Session Management**: View/revoke active sessions
6. **Audit Logging**: Track login attempts, successful/failed authentications

## References

- OpenAPI Specification: `docs/api/auth-api-spec.yaml`
- JWT Standard: [RFC 7519](https://tools.ietf.org/html/rfc7519)
- Bearer Token Usage: [RFC 6750](https://tools.ietf.org/html/rfc6750)
- bcrypt: [Provos-Mazières](https://www.usenix.org/legacy/events/usenix99/provos/provos.pdf)

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-06 | Foundation Agent | Initial architecture design |
