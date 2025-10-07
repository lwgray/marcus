# User Profile API - Architecture Documentation

## Task: Design Get User Profile
**Task ID**: task_user_profile_get_design

## Overview
This document provides the complete architectural design for the user profile retrieval endpoint in the Task Management API. The design establishes patterns for JWT authentication that will be used across all protected endpoints.

## API Endpoint Design

### Endpoint
```
GET /api/users/profile
```

### Purpose
Retrieve the authenticated user's profile information using their JWT token.

### Authentication
- **Method**: JWT Bearer Token
- **Header**: `Authorization: Bearer <token>`
- **Required**: Yes

## Data Models

### UserProfile Response Model
```json
{
  "id": 12345,
  "email": "user@example.com",
  "username": "john_doe",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-03-20T14:25:30Z"
}
```

**Fields**:
- `id` (integer, required): Unique user identifier from database
- `email` (string, required): User's email address (format validated)
- `username` (string, required): User's display name
- `created_at` (datetime, required): Account creation timestamp (ISO 8601)
- `updated_at` (datetime, required): Last profile modification timestamp (ISO 8601)

### Error Response Model
```json
{
  "error": "Error message description",
  "code": "ERROR_CODE"
}
```

## HTTP Status Codes

| Code | Meaning | When Returned |
|------|---------|---------------|
| 200 | Success | Profile retrieved successfully |
| 401 | Unauthorized | Missing, invalid, or expired JWT token |
| 404 | Not Found | User profile doesn't exist in database |
| 500 | Internal Error | Server-side error (database failure, etc.) |

## Request/Response Flow

### Successful Request
```
Client Request:
GET /api/users/profile HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Server Response:
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 12345,
  "email": "user@example.com",
  "username": "john_doe",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-03-20T14:25:30Z"
}
```

### Unauthorized Request
```
Client Request:
GET /api/users/profile HTTP/1.1
Host: api.example.com

Server Response:
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": "Authentication required",
  "code": "UNAUTHORIZED"
}
```

## JWT Token Specification

### Token Structure
- **Algorithm**: HS256 (HMAC SHA-256)
- **Expiry**: 24 hours from issuance
- **Claims**:
  - `user_id`: Integer identifier for user
  - `email`: User's email address
  - `iat`: Issued at timestamp
  - `exp`: Expiration timestamp

### Token Example (Decoded)
```json
{
  "user_id": 12345,
  "email": "user@example.com",
  "iat": 1704384600,
  "exp": 1704471000
}
```

## Backend Implementation Requirements

### Authentication Middleware
1. Extract `Authorization` header from request
2. Validate format: `Bearer <token>`
3. Verify JWT signature using secret key from environment
4. Check token expiration (`exp` claim)
5. Extract `user_id` from token claims
6. Attach user context to request
7. Return 401 on any validation failure

### Database Query
```sql
SELECT id, email, username, created_at, updated_at
FROM users
WHERE id = ?
```
- Use `user_id` from JWT claims as parameter
- Return 404 if no user found

### Environment Configuration
- `JWT_SECRET_KEY`: Secret key for token signing/verification (minimum 256 bits)
- Must be cryptographically secure random string
- Never commit to version control

## Frontend Integration Requirements

### Making Authenticated Requests
```javascript
fetch('https://api.example.com/api/users/profile', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(response => {
  if (response.status === 401) {
    // Redirect to login
    window.location.href = '/login';
  }
  return response.json();
})
.then(data => {
  // Handle user profile data
  console.log(data);
});
```

### Token Storage
- Store JWT in `localStorage` or HTTP-only cookies
- Include in Authorization header for all protected endpoints
- Remove on logout or 401 errors

## Security Considerations

### HTTPS Requirement
- All production traffic MUST use HTTPS
- Tokens transmitted over HTTP are vulnerable to interception

### Token Security
- Never log tokens
- Never include tokens in URLs
- Set appropriate CORS headers
- Implement rate limiting on auth endpoints

### Input Validation
- Validate Authorization header format
- Sanitize all user inputs (though this endpoint only reads)
- Use parameterized queries to prevent SQL injection

## Integration Points

### For Backend Team
- **Artifacts**:
  - OpenAPI spec: `docs/api/user-profile-api.yaml`
  - JWT design: `docs/design/jwt-auth-design.md`
- **Dependencies**: User registration/login endpoints must generate JWT tokens
- **Pattern**: This authentication pattern should be reused for all protected endpoints

### For Frontend Team
- **Artifacts**:
  - OpenAPI spec: `docs/api/user-profile-api.yaml`
  - JWT design: `docs/design/jwt-auth-design.md`
- **Usage**: After login, store JWT and use for profile retrieval and other protected requests
- **Error Handling**: Handle 401 errors by redirecting to login page

### For Database Team
- **Requirements**:
  - `users` table with fields: id, email, username, created_at, updated_at
  - Index on `id` for fast lookups

## Testing Requirements

### Unit Tests
- JWT token generation and verification
- Token expiration validation
- Authorization header parsing
- User ID extraction from claims

### Integration Tests
- Full request/response flow with valid token
- Invalid token rejection
- Expired token rejection
- Missing token rejection
- User not found scenario

### API Contract Tests
- Response schema validation against OpenAPI spec
- Status code validation
- Header validation

## Performance Considerations

### Caching Strategy
- Consider caching user profiles (with short TTL)
- Invalidate cache on profile updates
- Cache key: `user_profile:{user_id}`

### Database Optimization
- Ensure index on `users.id`
- Monitor query performance
- Consider connection pooling

## Monitoring & Logging

### Metrics to Track
- Request count (200, 401, 404, 500)
- Response time (p50, p95, p99)
- Authentication failure rate
- Token expiration frequency

### Logging
- Log authentication failures (without exposing tokens)
- Log 500 errors with stack traces
- Log unusual patterns (repeated 401s from same IP)

## Future Enhancements
1. **Refresh Tokens**: Long-lived refresh tokens for extended sessions
2. **Token Revocation**: Blacklist for logout/security events
3. **RBAC**: Role-based access control with role claims in JWT
4. **Profile Updates**: PUT/PATCH endpoints for profile modification
5. **MFA**: Multi-factor authentication support
6. **OAuth Integration**: Social login support

## References
- OpenAPI Specification: `docs/api/user-profile-api.yaml`
- JWT Authentication Design: `docs/design/jwt-auth-design.md`
- RFC 7519 (JWT): https://tools.ietf.org/html/rfc7519
- REST API Best Practices: https://restfulapi.net/

---
**Document Version**: 1.0
**Created**: 2025-10-06
**Author**: Integration & QA Agent
**Status**: Complete
