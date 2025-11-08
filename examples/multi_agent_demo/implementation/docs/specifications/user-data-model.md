# User Data Model

## User Entity

### Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,

    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT username_length CHECK (char_length(username) >= 3),
    CONSTRAINT password_hash_not_empty CHECK (char_length(password_hash) > 0)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_created_at ON users(created_at);
```

### Refresh Token Storage

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,

    CONSTRAINT token_expiry CHECK (expires_at > created_at)
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
```

## Field Specifications

### User Fields

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | UUID | Auto | Unique user identifier | Auto-generated |
| email | String | Yes | User's email address | Valid email format, unique |
| username | String | Yes | Display name | 3-50 chars, unique, alphanumeric + underscore |
| password_hash | String | Yes | Bcrypt hashed password | Bcrypt hash (60 chars) |
| is_active | Boolean | No | Account active status | Default: true |
| is_verified | Boolean | No | Email verification status | Default: false |
| created_at | Timestamp | Auto | Account creation time | Auto-generated |
| updated_at | Timestamp | Auto | Last update time | Auto-updated |
| last_login | Timestamp | No | Last successful login | Updated on login |

### Refresh Token Fields

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| id | UUID | Auto | Token identifier | Auto-generated |
| user_id | UUID | Yes | Associated user | Foreign key to users |
| token_hash | String | Yes | Hashed refresh token | SHA-256 hash, unique |
| expires_at | Timestamp | Yes | Token expiration | Must be > created_at |
| is_revoked | Boolean | No | Revocation status | Default: false |
| created_at | Timestamp | Auto | Token creation time | Auto-generated |
| revoked_at | Timestamp | No | Revocation time | Set when revoked |
| ip_address | String | No | Request IP address | IPv4/IPv6 format |
| user_agent | String | No | Browser/client info | For security tracking |

## Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
- Maximum 128 characters (to prevent DoS via bcrypt)

## Data Model Relationships

```
┌──────────────────┐
│      users       │
│                  │
│  - id (PK)       │
│  - email (UQ)    │
│  - username (UQ) │
│  - password_hash │
│  - is_active     │
│  - is_verified   │
│  - created_at    │
│  - updated_at    │
│  - last_login    │
└────────┬─────────┘
         │
         │ 1:N
         │
         ▼
┌──────────────────┐
│ refresh_tokens   │
│                  │
│  - id (PK)       │
│  - user_id (FK)  │
│  - token_hash    │
│  - expires_at    │
│  - is_revoked    │
│  - created_at    │
│  - revoked_at    │
│  - ip_address    │
│  - user_agent    │
└──────────────────┘
```

## JSON Response Format

### User Object (Public)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "johndoe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-10-08T12:00:00Z",
  "last_login": "2025-10-08T15:30:00Z"
}
```

**Note**: `password_hash` is NEVER exposed in API responses.

## Data Privacy & Security

1. **Password Storage**: Passwords are hashed using bcrypt with cost factor 12
2. **Token Storage**: Refresh tokens are stored as SHA-256 hashes
3. **PII Protection**: Email and username are considered PII and protected
4. **Soft Delete**: Users can be deactivated (is_active=false) instead of hard deletion
5. **Audit Trail**: created_at, updated_at, last_login provide audit capability
