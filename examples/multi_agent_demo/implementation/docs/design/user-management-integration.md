# User Management Integration

## Overview
This document describes how the authentication system integrates with the user management system, including user lifecycle operations and authorization patterns.

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                        │
│  - Rate limiting                                           │
│  - CORS handling                                           │
│  - Request logging                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴─────────────┐
        │                          │
        ▼                          ▼
┌──────────────────┐      ┌──────────────────┐
│  Authentication  │      │  User Management │
│     Service      │◄────►│     Service      │
│                  │      │                  │
│ - JWT handling   │      │ - CRUD ops       │
│ - Token mgmt     │      │ - Profile mgmt   │
│ - Login/logout   │      │ - Role mgmt      │
└────────┬─────────┘      └────────┬─────────┘
         │                         │
         └────────────┬────────────┘
                      │
         ┌────────────▼─────────────┐
         │    Database Layer        │
         │  - users table           │
         │  - refresh_tokens table  │
         │  - user_roles table      │
         └──────────────────────────┘
```

## User Lifecycle Integration

### 1. User Registration Flow

```python
# Registration endpoint integrates authentication + user management

POST /api/auth/register
{
    "email": "user@example.com",
    "password": "SecureP@ssw0rd", <!-- pragma: allowlist secret -->
    "username": "johndoe"
}

# Integration steps:
1. Validate input (email, password strength, username format)
2. Check email/username uniqueness (User Management)
3. Hash password (Authentication Service)
4. Create user record (User Management)
5. Generate JWT tokens (Authentication Service)
6. Send verification email (User Management)
7. Return tokens + user object
```

**Service Interaction**:
```python
async def register_user(request: RegistrationRequest):
    # 1. User Management: Check uniqueness
    if await user_service.email_exists(request.email):
        raise EmailAlreadyExistsError()

    # 2. Authentication: Hash password
    password_hash = auth_service.hash_password(request.password)

    # 3. User Management: Create user
    user = await user_service.create_user(
        email=request.email,
        username=request.username,
        password_hash=password_hash
    )

    # 4. Authentication: Generate tokens
    tokens = auth_service.generate_tokens(user.id)

    # 5. User Management: Send verification email
    await user_service.send_verification_email(user.email)

    return {"tokens": tokens, "user": user.to_dict()}
```

### 2. User Login Flow

```python
POST /api/auth/login
{
    "email": "user@example.com",
    "password": "SecureP@ssw0rd" <!-- pragma: allowlist secret -->
}

# Integration steps:
1. Find user by email (User Management)
2. Verify password (Authentication Service)
3. Check if account is active (User Management)
4. Generate JWT tokens (Authentication Service)
5. Update last_login timestamp (User Management)
6. Return tokens + user object
```

**Service Interaction**:
```python
async def login_user(request: LoginRequest):
    # 1. User Management: Find user
    user = await user_service.get_by_email(request.email)
    if not user:
        raise InvalidCredentialsError()

    # 2. Authentication: Verify password
    if not auth_service.verify_password(request.password, user.password_hash):
        raise InvalidCredentialsError()

    # 3. User Management: Check active status
    if not user.is_active:
        raise AccountDeactivatedError()

    # 4. Authentication: Generate tokens
    tokens = auth_service.generate_tokens(user.id)

    # 5. User Management: Update last login
    await user_service.update_last_login(user.id)

    return {"tokens": tokens, "user": user.to_dict()}
```

### 3. Password Change Flow

```python
PUT /api/users/me/password
Authorization: Bearer <access_token>
{
    "current_password": "OldP@ssw0rd", <!-- pragma: allowlist secret -->
    "new_password": "NewP@ssw0rd" <!-- pragma: allowlist secret -->
}

# Integration steps:
1. Verify access token (Authentication Service)
2. Extract user_id from token
3. Fetch user (User Management)
4. Verify current password (Authentication Service)
5. Hash new password (Authentication Service)
6. Update password (User Management)
7. Revoke all refresh tokens (Authentication Service)
8. Send confirmation email (User Management)
```

**Service Interaction**:
```python
async def change_password(user_id: str, request: PasswordChangeRequest):
    # 1. User Management: Get user
    user = await user_service.get_by_id(user_id)

    # 2. Authentication: Verify current password
    if not auth_service.verify_password(request.current_password, user.password_hash):
        raise InvalidPasswordError()

    # 3. Authentication: Hash new password
    new_hash = auth_service.hash_password(request.new_password)

    # 4. User Management: Update password
    await user_service.update_password(user_id, new_hash)

    # 5. Authentication: Revoke all refresh tokens
    await auth_service.revoke_all_user_tokens(user_id)

    # 6. User Management: Send notification
    await user_service.send_password_changed_email(user.email)
```

### 4. User Deletion/Deactivation Flow

```python
DELETE /api/users/{user_id}
Authorization: Bearer <admin_access_token>

# Integration steps:
1. Verify admin token (Authentication Service)
2. Check admin permissions (User Management)
3. Deactivate user (User Management - soft delete)
4. Revoke all refresh tokens (Authentication Service)
5. Log audit event (User Management)
```

**Service Interaction**:
```python
async def deactivate_user(admin_id: str, user_id: str):
    # 1. User Management: Check admin permissions
    if not await user_service.is_admin(admin_id):
        raise UnauthorizedError()

    # 2. User Management: Deactivate user
    await user_service.deactivate_user(user_id)

    # 3. Authentication: Revoke all tokens
    await auth_service.revoke_all_user_tokens(user_id)

    # 4. User Management: Audit log
    await user_service.log_audit_event(
        action="user_deactivated",
        admin_id=admin_id,
        target_user_id=user_id
    )
```

## Authorization Integration

### Role-Based Access Control (RBAC)

```python
# Database schema extension
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID REFERENCES users(id),

    UNIQUE(user_id, role)
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role);
```

### Roles Definition

```python
class Role:
    USER = "user"           # Basic user access
    ADMIN = "admin"         # Admin access to user management
    MODERATOR = "moderator" # Moderate content
    SUPER_ADMIN = "super_admin"  # Full system access
```

### JWT Token with Roles

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "username": "adminuser",
  "roles": ["user", "admin"],
  "type": "access",
  "iat": 1696780800,
  "exp": 1696781700,
  "jti": "unique-token-id"
}
```

### Authorization Middleware

```python
from functools import wraps
from typing import List

def require_roles(required_roles: List[str]):
    """
    Decorator to enforce role-based access control.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract token from request
            token = extract_token_from_request()

            # Verify and decode token
            payload = auth_service.verify_access_token(token)

            # Check roles
            user_roles = payload.get("roles", [])
            if not any(role in user_roles for role in required_roles):
                raise InsufficientPermissionsError()

            # Add user context to request
            kwargs['user_id'] = payload['sub']
            kwargs['user_roles'] = user_roles

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@require_roles(["admin"])
async def delete_user(user_id: str, **context):
    admin_id = context['user_id']
    await user_service.delete_user(user_id, deleted_by=admin_id)
```

## Protected Endpoints Integration

### Authentication Middleware

```python
async def authenticate_request(request: Request) -> dict:
    """
    Middleware to authenticate all protected requests.

    Returns user context for authorized requests.
    Raises 401 for unauthorized requests.
    """
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid authorization header")

    # Extract token
    token = auth_header.split(" ")[1]

    # Verify token
    try:
        payload = auth_service.verify_access_token(token)
    except ExpiredTokenError:
        raise UnauthorizedError("Token has expired")
    except InvalidTokenError:
        raise UnauthorizedError("Invalid token")

    # Fetch user (verify still exists and active)
    user = await user_service.get_by_id(payload['sub'])
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    # Return user context
    return {
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
        "roles": payload.get("roles", ["user"])
    }
```

### Protected Route Example

```python
@app.get("/api/users/me")
async def get_current_user(request: Request):
    # Authenticate
    user_context = await authenticate_request(request)

    # Fetch user profile
    user = await user_service.get_by_id(user_context['user_id'])

    return {"success": True, "data": user.to_dict()}
```

## Email Verification Integration

### Verification Flow

```python
# 1. Registration triggers verification email
POST /api/auth/register → sends verification email

# 2. User clicks verification link
GET /api/auth/verify-email?token=<verification_token>

# Integration:
async def verify_email(token: str):
    # Authentication: Verify token
    payload = auth_service.verify_verification_token(token)
    user_id = payload['sub']

    # User Management: Mark as verified
    await user_service.mark_email_verified(user_id)

    return {"success": True, "message": "Email verified successfully"}
```

### Verification Token Generation

```python
def generate_verification_token(user_id: str) -> str:
    """
    Generate email verification token (24 hour expiry).
    """
    payload = {
        "sub": user_id,
        "type": "email_verification",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
```

## Password Reset Integration

### Reset Flow

```python
# 1. Request password reset
POST /api/auth/forgot-password
{
    "email": "user@example.com"
}

# 2. User clicks reset link in email
GET /api/auth/reset-password?token=<reset_token>

# 3. Submit new password
POST /api/auth/reset-password
{
    "token": "<reset_token>",
    "new_password": "NewP@ssw0rd" <!-- pragma: allowlist secret -->
}

# Integration:
async def reset_password(token: str, new_password: str):
    # Authentication: Verify reset token
    payload = auth_service.verify_reset_token(token)
    user_id = payload['sub']

    # Authentication: Hash new password
    password_hash = auth_service.hash_password(new_password)

    # User Management: Update password
    await user_service.update_password(user_id, password_hash)

    # Authentication: Revoke all refresh tokens
    await auth_service.revoke_all_user_tokens(user_id)

    # User Management: Send confirmation
    user = await user_service.get_by_id(user_id)
    await user_service.send_password_reset_confirmation(user.email)
```

## Service Boundaries

### Authentication Service Responsibilities
- Password hashing and verification
- JWT token generation and verification
- Token revocation and cleanup
- Rate limiting enforcement
- Session management

### User Management Service Responsibilities
- User CRUD operations
- Profile management
- Role assignment
- Email notifications
- Audit logging
- Email verification status

### Shared Concerns
- Both services access `users` table
- Authentication owns `refresh_tokens` table
- User Management owns `user_roles` table
- Both enforce business rules in their domain

## API Integration Examples

### Example 1: User Profile Update

```python
PUT /api/users/me
Authorization: Bearer <access_token>
{
    "username": "newusername"
}

# Flow:
1. Authentication middleware: Verify token, extract user_id
2. User Management: Validate new username
3. User Management: Update user record
4. Return updated user object
```

### Example 2: Admin User List

```python
GET /api/users?page=1&limit=20
Authorization: Bearer <admin_access_token>

# Flow:
1. Authentication middleware: Verify token, extract user_id and roles
2. Authorization: Check "admin" role
3. User Management: Fetch paginated user list
4. Return user list (passwords excluded)
```

### Example 3: Multi-Factor Authentication (Future)

```python
POST /api/auth/mfa/enable
Authorization: Bearer <access_token>

# Flow:
1. Authentication: Verify token
2. Authentication: Generate TOTP secret
3. User Management: Store encrypted TOTP secret
4. Return QR code for authenticator app
```

## Database Transaction Coordination

### Registration Transaction
```python
async def register_user_transaction(data: RegistrationRequest):
    async with database.transaction():
        # 1. Create user (User Management)
        user = await user_service.create_user(...)

        # 2. Assign default role (User Management)
        await user_service.assign_role(user.id, Role.USER)

        # 3. Create refresh token record (Authentication)
        refresh_token = auth_service.generate_refresh_token(user.id)
        await auth_service.store_refresh_token(refresh_token, user.id)

        # If any step fails, all rollback
```

## Event-Driven Integration (Optional)

### Event Publishing
```python
# User Management publishes events
await event_bus.publish("user.created", {"user_id": user.id})
await event_bus.publish("user.deactivated", {"user_id": user.id})
await event_bus.publish("password.changed", {"user_id": user.id})

# Authentication Service subscribes
@event_bus.subscribe("user.deactivated")
async def on_user_deactivated(event):
    await auth_service.revoke_all_user_tokens(event['user_id'])

@event_bus.subscribe("password.changed")
async def on_password_changed(event):
    await auth_service.revoke_all_user_tokens(event['user_id'])
```

## Integration Testing Considerations

### Test Scenarios
1. Registration → Login → Access protected resource
2. Password change → Old tokens invalidated
3. User deactivation → Token rejected
4. Role assignment → Access granted to admin endpoints
5. Email verification → Account status updated
6. Password reset → Tokens revoked

### Mock Integration Points
```python
# For unit testing, mock service boundaries
@pytest.fixture
def mock_user_service():
    service = Mock()
    service.get_by_email = AsyncMock(return_value=test_user)
    service.create_user = AsyncMock(return_value=test_user)
    return service
```
