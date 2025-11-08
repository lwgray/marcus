# JWT Implementation Specification

## Overview
This document specifies the implementation details for JWT-based authentication in the Task Management API.

## JWT Structure

### Access Token Payload

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "johndoe",
  "type": "access",
  "iat": 1696780800,
  "exp": 1696781700,
  "jti": "unique-token-id"
}
```

**Fields:**
- `sub` (Subject): User ID (UUID)
- `email`: User's email address
- `username`: User's username
- `type`: Token type ("access")
- `iat` (Issued At): Unix timestamp when token was created
- `exp` (Expiration): Unix timestamp when token expires (15 minutes from iat)
- `jti` (JWT ID): Unique token identifier for revocation tracking

### Refresh Token Payload

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "type": "refresh",
  "iat": 1696780800,
  "exp": 1697385600,
  "jti": "unique-refresh-token-id"
}
```

**Fields:**
- `sub` (Subject): User ID (UUID)
- `type`: Token type ("refresh")
- `iat` (Issued At): Unix timestamp when token was created
- `exp` (Expiration): Unix timestamp when token expires (7 days from iat)
- `jti` (JWT ID): Unique token identifier for rotation tracking

## Token Generation

### Algorithm
- **Algorithm**: HS256 (HMAC with SHA-256)
- **Alternative for production**: RS256 (RSA Signature with SHA-256) for better security

### Secret Key Management
```python
# Development
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")

# Production (must be strong random key)
# Generated via: openssl rand -base64 64
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # Required in production

# For RS256
JWT_PRIVATE_KEY_PATH = os.getenv("JWT_PRIVATE_KEY_PATH")
JWT_PUBLIC_KEY_PATH = os.getenv("JWT_PUBLIC_KEY_PATH")
```

### Token Expiry Configuration

```python
# Access token: 15 minutes (900 seconds)
ACCESS_TOKEN_EXPIRE_MINUTES = 15

# Refresh token: 7 days (604800 seconds)
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Configurable via environment variables
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
```

## Token Verification

### Verification Steps

1. **Extract Token**: Get token from `Authorization: Bearer <token>` header
2. **Verify Signature**: Validate JWT signature using secret key
3. **Check Expiration**: Ensure `exp` claim is in the future
4. **Validate Type**: Verify `type` claim matches expected value
5. **Check Revocation**: For refresh tokens, verify not in revocation list
6. **Extract Claims**: Parse payload and extract user information

### Verification Pseudocode

```python
def verify_access_token(token: str) -> dict:
    """
    Verify JWT access token and return payload.

    Raises:
        InvalidTokenError: If signature invalid
        ExpiredTokenError: If token expired
        InvalidTokenTypeError: If not an access token
    """
    try:
        # Decode and verify signature
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )

        # Verify token type
        if payload.get("type") != "access":
            raise InvalidTokenTypeError("Not an access token")

        return payload

    except jwt.ExpiredSignatureError:
        raise ExpiredTokenError("Token has expired")
    except jwt.InvalidSignatureError:
        raise InvalidTokenError("Invalid token signature")
    except jwt.DecodeError:
        raise InvalidTokenError("Token decode failed")
```

## Token Rotation

### Refresh Token Rotation Strategy

1. **On Refresh**: When refresh token is used to get new access token
   - Generate new access token
   - Optionally rotate refresh token (recommended)
   - Invalidate old refresh token if rotated

2. **Rotation Benefits**:
   - Limits damage if refresh token is stolen
   - Provides audit trail of token usage
   - Detects token replay attacks

### Rotation Implementation

```python
def rotate_refresh_token(old_refresh_token: str) -> tuple[str, str]:
    """
    Use old refresh token to generate new access and refresh tokens.

    Returns:
        tuple: (new_access_token, new_refresh_token)
    """
    # Verify old refresh token
    payload = verify_refresh_token(old_refresh_token)
    user_id = payload["sub"]

    # Generate new tokens
    new_access_token = generate_access_token(user_id)
    new_refresh_token = generate_refresh_token(user_id)

    # Revoke old refresh token
    revoke_refresh_token(old_refresh_token)

    # Store new refresh token hash
    store_refresh_token_hash(new_refresh_token, user_id)

    return new_access_token, new_refresh_token
```

## Token Revocation

### Revocation Mechanisms

1. **Refresh Token Revocation**:
   - Mark token as revoked in `refresh_tokens` table
   - Set `is_revoked = true` and `revoked_at = NOW()`
   - Check revocation status on every refresh request

2. **Access Token Revocation** (Advanced):
   - Not implemented by default (short expiry mitigates risk)
   - Optional: Maintain in-memory blacklist with Redis
   - Check blacklist in authentication middleware

### Revocation Scenarios

- **Logout**: User explicitly logs out → revoke refresh token
- **Password Change**: User changes password → revoke all refresh tokens
- **Security Breach**: Admin detects compromise → revoke all user tokens
- **Token Rotation**: Old refresh token replaced → revoke old token
- **Suspicious Activity**: Rate limiting triggered → temporary revocation

## Storage and Hashing

### Refresh Token Storage

```python
def store_refresh_token(token: str, user_id: str, request_info: dict):
    """
    Store refresh token securely in database.
    """
    # Hash the token (SHA-256)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # Store in database
    RefreshToken.create(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=request_info.get("ip_address"),
        user_agent=request_info.get("user_agent")
    )
```

### Token Lookup

```python
def verify_refresh_token_not_revoked(token: str) -> bool:
    """
    Check if refresh token is revoked.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    token_record = RefreshToken.get_by_hash(token_hash)

    if not token_record:
        return False  # Token not found

    if token_record.is_revoked:
        return False  # Token revoked

    if token_record.expires_at < datetime.utcnow():
        return False  # Token expired

    return True  # Token valid
```

## Error Handling

### Error Types

| Error | HTTP Status | Description | User Action |
|-------|-------------|-------------|-------------|
| InvalidTokenError | 401 | Token format invalid | Re-login |
| ExpiredTokenError | 401 | Token expired | Refresh token |
| InvalidSignatureError | 401 | Signature verification failed | Re-login |
| InvalidTokenTypeError | 401 | Wrong token type | Use correct token |
| RevokedTokenError | 401 | Token revoked | Re-login |
| MissingTokenError | 401 | No token provided | Provide token |

### Error Response Format

```json
{
  "success": false,
  "error": "Token has expired",
  "error_code": "TOKEN_EXPIRED",
  "details": {
    "expired_at": "2025-10-08T12:15:00Z",
    "action": "refresh_token"
  }
}
```

## Implementation Libraries

### Python (Recommended)

```python
# PyJWT - JWT encoding/decoding
pip install PyJWT

# Usage
import jwt
from datetime import datetime, timedelta

def generate_access_token(user_id: str, email: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "username": username,
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
```

## Security Considerations

1. **Key Management**:
   - Never commit secret keys to version control
   - Use environment variables for configuration
   - Rotate keys periodically (every 90 days)
   - Use strong random keys (minimum 256 bits for HS256)

2. **Token Storage (Client)**:
   - Store tokens in httpOnly cookies (preferred) or localStorage
   - Never store in localStorage if XSS risk is high
   - Clear tokens on logout

3. **Token Transmission**:
   - Always use HTTPS in production
   - Include tokens in Authorization header, not URL parameters
   - Implement CORS properly

4. **Token Lifetime**:
   - Keep access tokens short-lived (15 minutes)
   - Refresh tokens longer but not excessive (7 days)
   - Implement sliding sessions if needed

5. **Revocation**:
   - Always implement refresh token revocation
   - Consider access token blacklist for high-security scenarios
   - Clean up expired tokens periodically
