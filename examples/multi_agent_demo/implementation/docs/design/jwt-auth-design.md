# JWT Authentication Design for Task Management API

## Overview
This document describes the JWT (JSON Web Token) authentication pattern for the Task Management API, establishing the security foundation for all protected endpoints.

## JWT Token Structure

### Algorithm
- **Algorithm**: HS256 (HMAC with SHA-256)
- **Reason**: Symmetric signing with secret key, suitable for single-service architecture

### Token Lifetime
- **Expiry**: 24 hours from issuance
- **Refresh Strategy**: Client must re-authenticate after expiry (refresh tokens to be designed separately)

### Token Claims

#### Standard Claims (RFC 7519)
- `iat` (Issued At): Unix timestamp of token creation
- `exp` (Expiration): Unix timestamp when token expires (iat + 24 hours)

#### Custom Claims
- `user_id`: Integer - Unique identifier for the authenticated user
- `email`: String - User's email address for reference

#### Example JWT Payload
```json
{
  "user_id": 12345,
  "email": "user@example.com",
  "iat": 1704384600,
  "exp": 1704471000
}
```

## Authorization Pattern

### Request Header Format
```
Authorization: Bearer <jwt_token>
```

### Token Extraction Flow
1. Server extracts `Authorization` header from request
2. Validates format matches "Bearer {token}"
3. Extracts token portion after "Bearer "
4. Verifies token signature using secret key
5. Validates expiration (`exp` claim > current time)
6. Extracts `user_id` claim for user identification

### Error Responses

#### Missing Token
- **HTTP Status**: 401 Unauthorized
- **Response Body**:
```json
{
  "error": "Authentication required",
  "code": "UNAUTHORIZED"
}
```

#### Invalid/Expired Token
- **HTTP Status**: 401 Unauthorized
- **Response Body**:
```json
{
  "error": "Invalid or expired token",
  "code": "UNAUTHORIZED"
}
```

## Security Considerations

### Secret Key Management
- Secret key MUST be stored in environment variables (never in code)
- Environment variable name: `JWT_SECRET_KEY`
- Minimum key length: 256 bits (32 bytes)
- Key should be randomly generated cryptographically secure string

### Token Storage (Client-Side)
- Recommended: HTTP-only cookies (prevents XSS attacks)
- Alternative: localStorage (if cookies not feasible, but less secure)
- Never expose tokens in URLs or logs

### HTTPS Requirement
- All API endpoints MUST be served over HTTPS in production
- Tokens transmitted over unencrypted HTTP are vulnerable to interception

## Integration with Endpoints

### Protected Endpoints
All endpoints requiring user authentication will:
1. Include `security: [BearerAuth: []]` in OpenAPI spec
2. Verify JWT token before processing request
3. Return 401 if token missing/invalid
4. Use `user_id` claim to identify requesting user

### Public Endpoints
Endpoints not requiring authentication (e.g., login, register) will:
- Not require Authorization header
- Not include security requirements in OpenAPI spec

## Implementation Notes for Backend Team

### Token Generation (Login/Register)
```python
import jwt
from datetime import datetime, timedelta

def generate_token(user_id: int, email: str, secret_key: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')
```

### Token Verification (Protected Endpoints)
```python
import jwt

def verify_token(token: str, secret_key: str) -> dict:
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid token")
```

### Middleware Pattern
Recommended to implement authentication middleware that:
1. Runs before protected endpoint handlers
2. Extracts and verifies JWT token
3. Attaches user information to request context
4. Returns 401 if verification fails

## Frontend Integration Notes

### Token Storage
```javascript
// After successful login/register
localStorage.setItem('jwt_token', token);

// On API requests
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
  'Content-Type': 'application/json'
};
```

### Error Handling
```javascript
if (response.status === 401) {
  // Token expired or invalid - redirect to login
  localStorage.removeItem('jwt_token');
  window.location.href = '/login';
}
```

## Future Enhancements
- Refresh token mechanism for extended sessions
- Token revocation/blacklist for logout functionality
- Role-based access control (RBAC) with additional claims
- Multi-factor authentication (MFA) support
