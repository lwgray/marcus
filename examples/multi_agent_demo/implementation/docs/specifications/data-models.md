# User Management Data Models

## Overview
This document specifies the data models for the user management system, including database schemas, relationships, constraints, and indexes.

## Database Choice
**Recommended**: PostgreSQL 14+

**Rationale**:
- ACID compliance for data integrity
- Strong support for UUID primary keys
- JSON/JSONB for flexible preferences
- Excellent performance with proper indexing
- Built-in encryption extensions (pgcrypto)
- Mature ecosystem and tooling

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────┐
│                         users                            │
├──────────────────────┬────────────────────┬─────────────┤
│ id (PK)              │ UUID               │ NOT NULL    │
│ username             │ VARCHAR(50)        │ UNIQUE      │
│ email                │ VARCHAR(254)       │ UNIQUE      │
│ password_hash        │ VARCHAR(255)       │ NOT NULL    │
│ full_name            │ VARCHAR(255)       │ NULL        │
│ role                 │ user_role_enum     │ NOT NULL    │
│ is_active            │ BOOLEAN            │ DEFAULT true│
│ is_verified          │ BOOLEAN            │ DEFAULT false│
│ created_at           │ TIMESTAMP          │ NOT NULL    │
│ updated_at           │ TIMESTAMP          │ NOT NULL    │
│ last_login           │ TIMESTAMP          │ NULL        │
└──────────────────────┴────────────────────┴─────────────┘
                              │
                              │ 1:1
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                    user_preferences                       │
├──────────────────────┬────────────────────┬──────────────┤
│ id (PK)              │ UUID               │ NOT NULL     │
│ user_id (FK)         │ UUID               │ UNIQUE       │
│ theme                │ VARCHAR(20)        │ DEFAULT 'light'│
│ language             │ VARCHAR(10)        │ DEFAULT 'en' │
│ notifications_enabled│ BOOLEAN            │ DEFAULT true │
│ created_at           │ TIMESTAMP          │ NOT NULL     │
│ updated_at           │ TIMESTAMP          │ NOT NULL     │
└──────────────────────┴────────────────────┴──────────────┘
```

## Table Specifications

### Table: users

**Purpose**: Core user account information

```sql
CREATE TYPE user_role_enum AS ENUM ('user', 'admin', 'moderator');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role user_role_enum NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT username_format CHECK (username ~ '^[a-zA-Z0-9_-]{3,50}$'),
    CONSTRAINT email_format CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$'),
    CONSTRAINT password_hash_length CHECK (length(password_hash) >= 60)
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_is_verified ON users(is_verified);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Field Specifications**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique identifier |
| username | VARCHAR(50) | UNIQUE, NOT NULL, CHECK | User's chosen username (3-50 chars, alphanumeric + _-) |
| email | VARCHAR(254) | UNIQUE, NOT NULL, CHECK | User's email address (RFC 5322 max length) |
| password_hash | VARCHAR(255) | NOT NULL, CHECK | bcrypt hash (60 chars, allow extra) |
| full_name | VARCHAR(255) | NULL | User's full name (optional) |
| role | user_role_enum | NOT NULL, DEFAULT 'user' | User role (user, admin, moderator) |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Account active status |
| is_verified | BOOLEAN | NOT NULL, DEFAULT false | Email verification status |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW | Account creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW | Last update timestamp (auto-updated) |
| last_login | TIMESTAMP WITH TIME ZONE | NULL | Last successful login |

**Business Rules**:
- Username is case-sensitive for display but unique check is case-insensitive
- Email is normalized to lowercase before storage
- Password must never be stored in plaintext
- role defaults to 'user' for new registrations
- is_active controls login ability
- is_verified controls email verification status
- updated_at auto-updates on any row modification

### Table: user_preferences

**Purpose**: User-specific preferences and settings

```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    theme VARCHAR(20) NOT NULL DEFAULT 'light',
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    notifications_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key
    CONSTRAINT fk_user_preferences_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT theme_valid CHECK (theme IN ('light', 'dark')),
    CONSTRAINT language_format CHECK (language ~ '^[a-z]{2}(-[A-Z]{2})?$')
);

-- Index for foreign key
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

-- Trigger for updated_at
CREATE TRIGGER user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Field Specifications**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | Unique identifier |
| user_id | UUID | FK, UNIQUE, NOT NULL | Reference to users table (1:1) |
| theme | VARCHAR(20) | NOT NULL, CHECK, DEFAULT 'light' | UI theme (light/dark) |
| language | VARCHAR(10) | NOT NULL, CHECK, DEFAULT 'en' | Language code (ISO 639-1, optional region) |
| notifications_enabled | BOOLEAN | NOT NULL, DEFAULT true | Email notification preference |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW | Preferences creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW | Last update timestamp |

**Business Rules**:
- One preference record per user (enforced by UNIQUE on user_id)
- Preferences created automatically on user registration
- Cascading delete: preferences deleted when user is deleted
- Theme limited to 'light' or 'dark'
- Language follows ISO 639-1 format (e.g., 'en', 'en-US')

## Optional Table: user_sessions (for token blacklisting)

**Purpose**: Track active sessions and enable token revocation

```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    jti VARCHAR(255) NOT NULL UNIQUE,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT false,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address INET,

    -- Foreign key
    CONSTRAINT fk_user_sessions_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_jti ON user_sessions(jti);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_revoked ON user_sessions(revoked) WHERE revoked = false;

-- Cleanup function for expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM user_sessions
    WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;
```

**Note**: This table is optional. A simpler approach using Redis for blacklisting is often sufficient for smaller applications.

## Python Data Models (Pydantic/SQLAlchemy)

### SQLAlchemy Models

```python
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Enum, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

class UserRole(str, enum.Enum):
    """User role enumeration."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class User(Base):
    """
    User account model.

    Attributes
    ----------
    id : UUID
        Unique user identifier
    username : str
        Unique username (3-50 chars)
    email : str
        Unique email address
    password_hash : str
        bcrypt password hash
    full_name : str, optional
        User's full name
    role : UserRole
        User role (user, admin, moderator)
    is_active : bool
        Whether account is active
    is_verified : bool
        Whether email is verified
    created_at : datetime
        Account creation timestamp
    updated_at : datetime
        Last update timestamp
    last_login : datetime, optional
        Last successful login timestamp
    """

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    email = Column(
        String(254),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash = Column(
        String(255),
        nullable=False
    )
    full_name = Column(String(255))
    role = Column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.USER,
        index=True
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    last_login = Column(DateTime(timezone=True))

    # Relationships
    preferences = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "username ~ '^[a-zA-Z0-9_-]{3,50}$'",
            name="username_format"
        ),
        CheckConstraint(
            "length(password_hash) >= 60",
            name="password_hash_length"
        ),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

class UserPreferences(Base):
    """
    User preferences model.

    Attributes
    ----------
    id : UUID
        Unique preference identifier
    user_id : UUID
        Foreign key to users table
    theme : str
        UI theme (light, dark)
    language : str
        Language code (ISO 639-1)
    notifications_enabled : bool
        Email notification preference
    created_at : datetime
        Preferences creation timestamp
    updated_at : datetime
        Last update timestamp
    """

    __tablename__ = "user_preferences"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    theme = Column(
        String(20),
        nullable=False,
        default="light"
    )
    language = Column(
        String(10),
        nullable=False,
        default="en"
    )
    notifications_enabled = Column(
        Boolean,
        nullable=False,
        default=True
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="preferences")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "theme IN ('light', 'dark')",
            name="theme_valid"
        ),
        CheckConstraint(
            "language ~ '^[a-z]{2}(-[A-Z]{2})?$'",
            name="language_format"
        ),
    )

    def __repr__(self):
        return f"<UserPreferences(user_id={self.user_id}, theme={self.theme})>"
```

### Pydantic Schemas (API Models)

```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re

class UserBase(BaseModel):
    """Base user schema with common attributes."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None

    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                'Username must contain only letters, numbers, '
                'underscores, and hyphens'
            )
        return v

class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(..., min_length=8)

    @validator('password')
    def validate_password(cls, v):
        # Password strength validation
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', v):
            raise ValueError('Password must contain special character')
        return v

class UserUpdate(BaseModel):
    """Schema for user profile updates."""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None

class UserResponse(UserBase):
    """Schema for user responses (excludes password)."""

    id: uuid.UUID
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True

class UserPreferencesBase(BaseModel):
    """Base preferences schema."""

    theme: str = Field(default="light", pattern="^(light|dark)$")
    language: str = Field(default="en", pattern="^[a-z]{2}(-[A-Z]{2})?$")
    notifications_enabled: bool = True

class UserPreferencesCreate(UserPreferencesBase):
    """Schema for creating preferences."""
    pass

class UserPreferencesUpdate(UserPreferencesBase):
    """Schema for updating preferences (all optional)."""

    theme: Optional[str] = Field(None, pattern="^(light|dark)$")
    language: Optional[str] = Field(None, pattern="^[a-z]{2}(-[A-Z]{2})?$")
    notifications_enabled: Optional[bool] = None

class UserPreferencesResponse(UserPreferencesBase):
    """Schema for preferences responses."""

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
```

## Data Migration Scripts

### Initial Migration (Alembic)

```python
"""create users and preferences tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-15 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create enum type
    user_role_enum = postgresql.ENUM(
        'user', 'admin', 'moderator',
        name='user_role_enum'
    )
    user_role_enum.create(op.get_bind())

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('email', sa.String(254), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('role', user_role_enum, nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.CheckConstraint("username ~ '^[a-zA-Z0-9_-]{3,50}$'",
                          name='username_format'),
        sa.CheckConstraint("length(password_hash) >= 60",
                          name='password_hash_length')
    )

    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    op.create_index('idx_users_is_verified', 'users', ['is_verified'])
    op.create_index('idx_users_created_at', 'users', [sa.desc('created_at')])

    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False,
                  unique=True),
        sa.Column('theme', sa.String(20), nullable=False, server_default='light'),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('notifications_enabled', sa.Boolean, nullable=False,
                  server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint("theme IN ('light', 'dark')", name='theme_valid'),
        sa.CheckConstraint("language ~ '^[a-z]{2}(-[A-Z]{2})?$'",
                          name='language_format')
    )

    # Create index
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'])

    # Create updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create triggers
    op.execute("""
        CREATE TRIGGER users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER user_preferences_updated_at
        BEFORE UPDATE ON user_preferences
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

def downgrade():
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS users_updated_at ON users")
    op.execute("DROP TRIGGER IF EXISTS user_preferences_updated_at ON user_preferences")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables
    op.drop_table('user_preferences')
    op.drop_table('users')

    # Drop enum type
    sa.Enum(name='user_role_enum').drop(op.get_bind())
```

## Data Seeding

### Development Seed Data

```python
"""Seed development database with test users."""

import asyncio
from app.core.security import hash_password
from app.db.models import User, UserPreferences, UserRole
from app.db.session import AsyncSession

async def seed_users(session: AsyncSession):
    """Create test users for development."""

    users_data = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "password": "Admin123!",  # pragma: allowlist secret
            "full_name": "Admin User",
            "role": UserRole.ADMIN,
            "is_verified": True
        },
        {
            "username": "moderator",
            "email": "moderator@example.com",
            "password": "Moderator123!",  # pragma: allowlist secret
            "full_name": "Moderator User",
            "role": UserRole.MODERATOR,
            "is_verified": True
        },
        {
            "username": "testuser",
            "email": "user@example.com",
            "password": "User123!",  # pragma: allowlist secret
            "full_name": "Test User",
            "role": UserRole.USER,
            "is_verified": True
        }
    ]

    for user_data in users_data:
        password = user_data.pop("password")
        user = User(
            **user_data,
            password_hash=hash_password(password)
        )
        session.add(user)
        await session.flush()

        # Create preferences
        preferences = UserPreferences(user_id=user.id)
        session.add(preferences)

    await session.commit()
    print(f"✓ Seeded {len(users_data)} test users")

if __name__ == "__main__":
    asyncio.run(seed_users())
```

## Query Patterns and Examples

### Common Queries

```python
# Find user by email
user = await session.execute(
    select(User).where(User.email == email.lower())
)
user = user.scalar_one_or_none()

# Find user with preferences (eager loading)
result = await session.execute(
    select(User)
    .options(joinedload(User.preferences))
    .where(User.id == user_id)
)
user = result.unique().scalar_one_or_none()

# List users with pagination and filters
query = select(User).where(User.is_active == True)
if role:
    query = query.where(User.role == role)
query = query.offset(offset).limit(limit).order_by(User.created_at.desc())
result = await session.execute(query)
users = result.scalars().all()

# Count total users (for pagination)
count_query = select(func.count()).select_from(User).where(User.is_active == True)
total = await session.scalar(count_query)

# Update user
user.full_name = new_name
user.updated_at = func.now()  # Trigger handles this automatically
await session.commit()

# Soft delete (deactivate)
user.is_active = False
await session.commit()
```

## Performance Considerations

### Index Strategy
- **Primary Keys**: Automatically indexed (UUID)
- **Unique Constraints**: Automatically indexed (email, username)
- **Foreign Keys**: Explicitly indexed (user_id in preferences)
- **Query Filters**: Indexed (role, is_active, is_verified)
- **Sorting**: Indexed (created_at DESC for recent users)

### Query Optimization
- Use `joinedload()` for eager loading relationships
- Use `selectinload()` for collections
- Add pagination to all list endpoints
- Use `count()` queries separately from data queries
- Consider database connection pooling (SQLAlchemy async engine)

### Caching Opportunities
- User sessions (Redis, 24h TTL)
- User preferences (Redis, 1h TTL)
- Role permissions (in-memory, invalidate on role change)

## Data Retention and Archival

### Active Data
- All user accounts (active and inactive)
- User preferences
- Current sessions

### Archival Policy
- Deactivated accounts: Retain for 90 days, then anonymize
- Deleted accounts: Immediate anonymization (GDPR compliance)
- Audit logs: Retain for 1 year

### Anonymization Procedure
```sql
-- Anonymize user data (GDPR right to erasure)
UPDATE users SET
    email = 'deleted_' || id || '@deleted.local',
    username = 'deleted_' || LEFT(id::TEXT, 8),
    full_name = NULL,
    password_hash = 'deleted',  -- pragma: allowlist secret
    is_active = false
WHERE id = $1;

DELETE FROM user_preferences WHERE user_id = $1;
```

## Summary

This data model provides:
- **Scalable Design**: UUID primary keys, proper indexing
- **Data Integrity**: Foreign keys, check constraints, triggers
- **Security**: No plaintext passwords, email normalization
- **Flexibility**: JSON preferences, enum roles
- **Compliance**: Soft deletes, anonymization procedures
- **Performance**: Strategic indexes, eager loading patterns

### Next Steps for Implementation
1. Set up database (PostgreSQL)
2. Configure SQLAlchemy models
3. Create Alembic migrations
4. Implement Pydantic schemas
5. Seed development data
6. Write database access layer (repositories)
7. Add unit tests for models
