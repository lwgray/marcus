# Authentication & Authorization Design

## Overview
The Recipe Management API uses JWT (JSON Web Tokens) for stateless authentication with support for OAuth2 social login providers.

## Authentication Flow

### 1. JWT Authentication

#### Token Structure
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "username": "johndoe",
    "roles": ["user"],
    "iat": 1625097600,
    "exp": 1625101200,
    "jti": "unique-token-id"
  }
}
```

#### Token Types
- **Access Token**: Short-lived (15 minutes), used for API requests
- **Refresh Token**: Long-lived (30 days), used to obtain new access tokens

#### Token Storage Recommendations
- Access Token: Store in memory or sessionStorage
- Refresh Token: Store in httpOnly secure cookie

### 2. OAuth2 Integration

#### Supported Providers
- Google
- Facebook
- GitHub
- Apple Sign-In

#### OAuth Flow
1. Client redirects to provider's authorization URL
2. User authorizes the application
3. Provider redirects back with authorization code
4. Backend exchanges code for provider tokens
5. Backend creates/updates user account
6. Backend issues JWT tokens to client

## Authorization System

### 1. Role-Based Access Control (RBAC)

#### User Roles
```python
class UserRole(Enum):
    GUEST = "guest"              # Unauthenticated user
    USER = "user"                # Regular authenticated user
    PREMIUM = "premium"          # Premium subscription user
    MODERATOR = "moderator"      # Community moderator
    ADMIN = "admin"              # System administrator
```

### 2. Permission Matrix

| Resource | Action | Guest | User | Premium | Moderator | Admin |
|----------|--------|-------|------|---------|-----------|-------|
| Recipe | View Public | ✓ | ✓ | ✓ | ✓ | ✓ |
| Recipe | View Private | ✗ | Owner | Owner | ✓ | ✓ |
| Recipe | Create | ✗ | ✓ | ✓ | ✓ | ✓ |
| Recipe | Update | ✗ | Owner | Owner | ✓ | ✓ |
| Recipe | Delete | ✗ | Owner | Owner | ✓ | ✓ |
| Recipe | Rate | ✗ | ✓ | ✓ | ✓ | ✓ |
| Comment | Create | ✗ | ✓ | ✓ | ✓ | ✓ |
| Comment | Delete | ✗ | Owner | Owner | ✓ | ✓ |
| User | View Profile | ✓ | ✓ | ✓ | ✓ | ✓ |
| User | Update Profile | ✗ | Owner | Owner | ✗ | ✓ |
| Meal Plan | Create | ✗ | 3/month | Unlimited | Unlimited | Unlimited |
| Shopping List | Generate | ✗ | 5/month | Unlimited | Unlimited | Unlimited |
| AI Recommendations | Access | ✗ | Basic | Advanced | Advanced | Advanced |

### 3. Resource-Level Permissions

#### Recipe Visibility
```python
class RecipeVisibility(Enum):
    PUBLIC = "public"          # Visible to everyone
    UNLISTED = "unlisted"      # Accessible via direct link only
    PRIVATE = "private"        # Visible to owner only
    FRIENDS = "friends"        # Visible to friends only
```

#### Sharing Permissions
```python
class SharingPermission(Enum):
    VIEW = "view"              # Can view recipe
    COMMENT = "comment"        # Can view and comment
    EDIT = "edit"              # Can view, comment, and edit
    ADMIN = "admin"            # Full control including delete
```

## Implementation Details

### 1. Authentication Middleware

```python
# FastAPI dependency for authentication
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return await get_user(user_id)
    except JWTError:
        raise credentials_exception
```

### 2. Authorization Decorators

```python
# Permission checking decorator
def requires_permission(resource: str, action: str):
    async def permission_checker(current_user = Depends(get_current_user)):
        if not has_permission(current_user, resource, action):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return permission_checker

# Usage example
@app.post("/recipes", dependencies=[Depends(requires_permission("recipe", "create"))])
async def create_recipe(recipe: RecipeCreate):
    # Implementation
```

### 3. API Key Authentication (Alternative)

For third-party integrations and automated systems:

```
Authorization: ApiKey YOUR_API_KEY
```

API Keys features:
- Scoped permissions
- Rate limiting per key
- Usage tracking
- Revocation capability

## Security Best Practices

### 1. Token Security
- Use strong secret keys (min 256 bits)
- Implement token rotation
- Blacklist compromised tokens
- Short expiration times for access tokens

### 2. Password Security
- Bcrypt with cost factor 12
- Password strength requirements
- Password history (prevent reuse)
- Account lockout after failed attempts

### 3. API Security
- HTTPS only
- CORS configuration
- Rate limiting per user/IP
- Request signing for sensitive operations
- Input validation and sanitization

### 4. Session Management
- Secure session storage
- Session timeout
- Concurrent session limits
- Device tracking and management

## Rate Limiting

### Tiers
| Tier | Requests/Hour | Burst | Daily Limit |
|------|---------------|-------|-------------|
| Guest | 100 | 10 | 1,000 |
| User | 1,000 | 50 | 10,000 |
| Premium | 5,000 | 100 | 50,000 |
| API Key | Custom | Custom | Custom |

### Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1625101200
```

## Account Security Features

### 1. Two-Factor Authentication (2FA)
- TOTP (Time-based One-Time Password)
- SMS backup codes
- Recovery codes

### 2. Account Recovery
- Email-based password reset
- Security questions (optional)
- Admin-assisted recovery

### 3. Security Notifications
- Login from new device
- Password changed
- Email changed
- Suspicious activity detected

## Compliance Considerations

### GDPR Compliance
- Right to access data
- Right to delete account
- Data portability
- Consent management

### Security Headers
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```
