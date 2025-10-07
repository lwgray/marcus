# User Model Specification

## Overview
Database schema and model specification for the User entity in the Task Management API authentication system.

## Database Schema

### Users Table

**Table Name**: `users`

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique user identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | User's email address (login identifier) |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt hashed password (never exposed in API) |
| full_name | VARCHAR(255) | NULL | User's display name |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last modification timestamp |

**SQL Schema (PostgreSQL)**:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast email lookups during login
CREATE INDEX idx_users_email ON users(email);

-- Trigger for updated_at (PostgreSQL)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**SQL Schema (SQLite - for testing)**:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- Trigger for updated_at (SQLite)
CREATE TRIGGER update_users_updated_at
    AFTER UPDATE ON users
    FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

## SQLAlchemy Model

**File**: `models/user.py`

```python
"""
User model for authentication system.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates
import re

Base = declarative_base()


class User(Base):
    """
    User model representing authenticated users.

    Attributes
    ----------
    id : int
        Unique user identifier (primary key)
    email : str
        User's email address (unique, indexed)
    password_hash : str
        bcrypt hashed password (never exposed in API responses)
    full_name : str, optional
        User's display name
    created_at : datetime
        Timestamp when user account was created
    updated_at : datetime
        Timestamp when user record was last modified
    """

    __tablename__ = 'users'
    __table_args__ = (
        Index('idx_users_email', 'email'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @validates('email')
    def validate_email(self, key, email):
        """
        Validate email format using regex.

        Parameters
        ----------
        key : str
            Field name being validated
        email : str
            Email address to validate

        Returns
        -------
        str
            Validated email address

        Raises
        ------
        ValueError
            If email format is invalid
        """
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            raise ValueError(f"Invalid email format: {email}")
        return email.lower()  # Store emails in lowercase for consistency

    def to_dict(self, include_timestamps=True):
        """
        Convert user model to dictionary for API responses.

        Parameters
        ----------
        include_timestamps : bool, optional
            Whether to include created_at and updated_at fields (default: True)

        Returns
        -------
        dict
            User data as dictionary (excludes password_hash)

        Notes
        -----
        NEVER include password_hash in the response
        """
        user_dict = {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
        }

        if include_timestamps:
            user_dict['created_at'] = self.created_at.isoformat() if self.created_at else None
            user_dict['updated_at'] = self.updated_at.isoformat() if self.updated_at else None

        return user_dict

    def __repr__(self):
        """String representation of User for debugging."""
        return f"<User(id={self.id}, email='{self.email}')>"
```

## Validation Rules

### Email Validation
- **Format**: Must match RFC 5322 email format
- **Regex**: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
- **Case**: Stored in lowercase for consistency
- **Uniqueness**: Enforced at database level (UNIQUE constraint)

### Password Validation
- **Minimum Length**: 8 characters
- **Hashing**: bcrypt with cost factor 12
- **Storage**: Only password_hash stored, never plain text
- **Validation**: Performed before hashing (at service layer)

### Full Name Validation
- **Optional**: Can be NULL
- **Max Length**: 255 characters
- **Format**: Any printable characters allowed

## API Response Format

### User Object (Public)
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Fields Excluded from API**:
- `password_hash` - NEVER exposed in any API response
- `updated_at` - Optional, only included if explicitly requested

## Security Considerations

### Password Hash Security
- **Algorithm**: bcrypt
- **Cost Factor**: 12 (2^12 = 4096 iterations)
- **Salt**: Automatically generated and included in hash
- **Format**: `$2b$12$[22-character salt][31-character hash]`

### Email Privacy
- Email addresses should be treated as PII (Personally Identifiable Information)
- Only exposed to the authenticated user themselves
- Not shared across user profiles (unless explicit sharing feature added)

### Data Retention
- Soft delete recommended (add `deleted_at` column in future)
- GDPR compliance: Provide data export and deletion mechanisms
- Audit trail: Log all user modifications

## Database Indexing Strategy

### Primary Index
- **Column**: `id` (PRIMARY KEY)
- **Type**: B-tree (default)
- **Purpose**: Fast lookups by user ID

### Email Index
- **Column**: `email`
- **Type**: B-tree
- **Purpose**: Fast lookups during login (most frequent query)
- **Cardinality**: High (unique values)

### Future Indexes (if needed)
- `created_at`: For analytics queries (user growth over time)
- Composite index `(email, password_hash)`: If login queries need optimization

## Migration Strategy

### Alembic Migration (Initial)

**File**: `alembic/versions/001_create_users_table.py`

```python
"""Create users table

Revision ID: 001
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create users table with indexes and constraints."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'])


def downgrade():
    """Drop users table."""
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
```

## Testing Considerations

### Unit Tests
- Email validation (valid/invalid formats)
- Password hashing and verification
- `to_dict()` method excludes password_hash
- Timestamp auto-population

### Integration Tests
- User creation with duplicate email (should fail)
- Email case-insensitivity (user@example.com == USER@EXAMPLE.COM)
- Concurrent user creation (race conditions)

### Test Fixtures
```python
@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        email="test@example.com",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeRox8N0iKJmJ5FBa",  # hashed "password123"
        full_name="Test User"
    )
```

## References
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- bcrypt Specification: https://en.wikipedia.org/wiki/Bcrypt
- Email RFC 5322: https://tools.ietf.org/html/rfc5322
- Alembic Migrations: https://alembic.sqlalchemy.org/

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-06 | Foundation Agent | Initial model specification |
