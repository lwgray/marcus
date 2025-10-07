# Authentication Implementation Guide

## Overview
This guide provides step-by-step instructions for implementing the user authentication system based on the design specifications.

## Quick Reference

**Related Documents**:
- API Specification: `docs/api/auth-api-spec.yaml`
- Architecture Decisions: `docs/architecture/auth-architecture.md`
- User Model Spec: `docs/specifications/user-model-spec.md`

**Key Endpoints**:
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user profile

## Prerequisites

### Required Dependencies
```bash
# Python 3.9+
pip install sqlalchemy==2.0.23
pip install alembic==1.12.1
pip install bcrypt==4.1.1
pip install pyjwt==2.8.0
pip install psycopg2-binary==2.9.9  # PostgreSQL driver
pip install python-dotenv==1.0.0
```

### Environment Variables
Create `.env` file:
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/taskmanagement

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Application
ENVIRONMENT=development
DEBUG=true
```

**SECURITY WARNING**: Never commit `.env` to version control. Add to `.gitignore`.

## Implementation Steps

### Step 1: Database Setup

#### 1.1 Create Database
```bash
# PostgreSQL
createdb taskmanagement

# Or using psql
psql -U postgres
CREATE DATABASE taskmanagement;
```

#### 1.2 Initialize Alembic
```bash
alembic init alembic
```

Edit `alembic.ini`:
```ini
sqlalchemy.url = postgresql://user:password@localhost:5432/taskmanagement
```

Edit `alembic/env.py`:
```python
from models.user import Base
target_metadata = Base.metadata
```

#### 1.3 Create Migration
```bash
# Create migration based on model
alembic revision --autogenerate -m "Create users table"

# Apply migration
alembic upgrade head
```

### Step 2: Implement User Model

**File**: `models/user.py`

See complete implementation in `docs/specifications/user-model-spec.md`.

Key methods:
- `validate_email()` - Email format validation
- `to_dict()` - Convert to API response (excludes password_hash)

### Step 3: Implement Authentication Service

**File**: `services/auth_service.py`

```python
"""
Authentication service for user login and JWT token management.
"""
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models.user import User
import os


class AuthService:
    """
    Service for handling user authentication operations.

    Attributes
    ----------
    secret_key : str
        JWT secret key from environment
    algorithm : str
        JWT algorithm (default: HS256)
    expiration_hours : int
        Token expiration time in hours (default: 24)
    """

    def __init__(self):
        """Initialize authentication service with config from environment."""
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        self.algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
        self.expiration_hours = int(os.getenv('JWT_EXPIRATION_HOURS', 24))

        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be set in environment")

    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.

        Parameters
        ----------
        password : str
            Plain text password

        Returns
        -------
        str
            bcrypt hashed password
        """
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash.

        Parameters
        ----------
        password : str
            Plain text password to verify
        password_hash : str
            bcrypt hash to check against

        Returns
        -------
        bool
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )

    def create_token(self, user: User) -> str:
        """
        Create JWT token for authenticated user.

        Parameters
        ----------
        user : User
            Authenticated user object

        Returns
        -------
        str
            JWT token string
        """
        now = datetime.utcnow()
        expiration = now + timedelta(hours=self.expiration_hours)

        payload = {
            'user_id': user.id,
            'email': user.email,
            'exp': expiration,
            'iat': now
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token.

        Parameters
        ----------
        token : str
            JWT token to verify

        Returns
        -------
        dict or None
            Decoded token payload if valid, None if invalid/expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def login(self, db: Session, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user and return token with user data.

        Parameters
        ----------
        db : Session
            Database session
        email : str
            User's email
        password : str
            User's password

        Returns
        -------
        dict or None
            {"token": str, "user": dict} if successful, None if failed
        """
        # Find user by email (case-insensitive)
        user = db.query(User).filter(
            User.email == email.lower()
        ).first()

        if not user:
            return None

        # Verify password
        if not self.verify_password(password, user.password_hash):
            return None

        # Create token
        token = self.create_token(user)

        return {
            'token': token,
            'user': user.to_dict()
        }

    def get_current_user(self, db: Session, token: str) -> Optional[User]:
        """
        Get user from JWT token.

        Parameters
        ----------
        db : Session
            Database session
        token : str
            JWT token

        Returns
        -------
        User or None
            User object if token valid, None otherwise
        """
        payload = self.verify_token(token)
        if not payload:
            return None

        user_id = payload.get('user_id')
        if not user_id:
            return None

        return db.query(User).filter(User.id == user_id).first()
```

### Step 4: Implement API Endpoints

**File**: `routes/auth_routes.py`

```python
"""
Authentication API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Any
from services.auth_service import AuthService
from database import get_db

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()
auth_service = AuthService()


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """User response schema."""
    id: int
    email: str
    full_name: str | None
    created_at: str


class LoginResponse(BaseModel):
    """Login response schema."""
    token: str
    user: UserResponse


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    User login endpoint.

    Authenticates user with email and password, returns JWT token.

    Parameters
    ----------
    request : LoginRequest
        Login credentials
    db : Session
        Database session (injected)

    Returns
    -------
    dict
        {"token": str, "user": dict}

    Raises
    ------
    HTTPException
        401 if credentials invalid
    """
    result = auth_service.login(db, request.email, request.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    return result


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current authenticated user's profile.

    Requires valid JWT token in Authorization header.

    Parameters
    ----------
    credentials : HTTPAuthorizationCredentials
        Bearer token from Authorization header
    db : Session
        Database session (injected)

    Returns
    -------
    dict
        User profile data

    Raises
    ------
    HTTPException
        401 if token invalid or missing
    """
    token = credentials.credentials
    user = auth_service.get_current_user(db, token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return user.to_dict()
```

### Step 5: Database Connection Setup

**File**: `database.py`

```python
"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in environment")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    echo=os.getenv('DEBUG', 'false').lower() == 'true'  # Log SQL in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.

    Yields
    ------
    Session
        SQLAlchemy database session

    Notes
    -----
    Automatically closes session after request
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Step 6: Testing

#### Unit Tests

**File**: `tests/unit/test_auth_service.py`

```python
"""
Unit tests for authentication service.
"""
import pytest
from services.auth_service import AuthService
from models.user import User
from unittest.mock import Mock


class TestAuthService:
    """Test suite for AuthService."""

    @pytest.fixture
    def auth_service(self, monkeypatch):
        """Create auth service with test config."""
        monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key')
        monkeypatch.setenv('JWT_ALGORITHM', 'HS256')
        monkeypatch.setenv('JWT_EXPIRATION_HOURS', '24')
        return AuthService()

    def test_hash_password(self, auth_service):
        """Test password hashing."""
        password = "SecurePass123!"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        # Hashes should be different (different salts)
        assert hash1 != hash2
        assert hash1.startswith('$2b$12$')

    def test_verify_password_success(self, auth_service):
        """Test password verification with correct password."""
        password = "SecurePass123!"
        password_hash = auth_service.hash_password(password)

        assert auth_service.verify_password(password, password_hash) is True

    def test_verify_password_failure(self, auth_service):
        """Test password verification with incorrect password."""
        password = "SecurePass123!"
        password_hash = auth_service.hash_password(password)

        assert auth_service.verify_password("WrongPassword", password_hash) is False

    def test_create_token(self, auth_service):
        """Test JWT token creation."""
        user = User(id=1, email="test@example.com")
        token = auth_service.create_token(user)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_success(self, auth_service):
        """Test JWT token verification with valid token."""
        user = User(id=1, email="test@example.com")
        token = auth_service.create_token(user)

        payload = auth_service.verify_token(token)

        assert payload is not None
        assert payload['user_id'] == 1
        assert payload['email'] == "test@example.com"

    def test_verify_token_invalid(self, auth_service):
        """Test JWT token verification with invalid token."""
        payload = auth_service.verify_token("invalid.token.here")

        assert payload is None
```

Run tests:
```bash
pytest tests/unit/test_auth_service.py -v
```

## Integration with Frontend

### Example: Login Flow

```javascript
// Login request
async function login(email, password) {
  const response = await fetch('http://localhost:8000/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error('Login failed');
  }

  const data = await response.json();
  // Store token in localStorage
  localStorage.setItem('authToken', data.token);

  return data.user;
}

// Get current user
async function getCurrentUser() {
  const token = localStorage.getItem('authToken');

  const response = await fetch('http://localhost:8000/api/auth/me', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    // Token invalid/expired, redirect to login
    localStorage.removeItem('authToken');
    window.location.href = '/login';
    return;
  }

  return await response.json();
}
```

## Security Checklist

- [ ] JWT_SECRET_KEY is strong random string (256+ bits)
- [ ] JWT_SECRET_KEY stored in environment variables, not code
- [ ] .env file added to .gitignore
- [ ] HTTPS enabled in production
- [ ] Password minimum length enforced (8+ characters)
- [ ] bcrypt cost factor set to 12
- [ ] Email stored in lowercase for consistency
- [ ] password_hash never exposed in API responses
- [ ] Database uses unique constraint on email
- [ ] Token expiration set appropriately (24 hours)
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention via parameterized queries
- [ ] Rate limiting configured (future enhancement)

## Deployment Notes

### Production Environment Variables
```bash
DATABASE_URL=postgresql://user:password@prod-db.example.com:5432/taskmanagement
JWT_SECRET_KEY=<strong-random-256-bit-key>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
ENVIRONMENT=production
DEBUG=false
```

### Generate Strong Secret Key
```python
import secrets
print(secrets.token_urlsafe(32))
```

## Troubleshooting

### Issue: "Invalid or expired token"
- Check token is being sent in Authorization header
- Verify token hasn't expired (24h default)
- Ensure JWT_SECRET_KEY matches between token creation and verification

### Issue: "Invalid email or password"
- Verify email is lowercase in database
- Check password was hashed with bcrypt
- Confirm user exists in database

### Issue: Database connection errors
- Verify DATABASE_URL is correct
- Check database server is running
- Ensure database exists and migrations applied

## Next Steps

1. **User Registration**: Implement POST /api/auth/register endpoint
2. **Password Reset**: Email-based password reset flow
3. **Refresh Tokens**: Long-lived refresh tokens for better UX
4. **Rate Limiting**: Prevent brute-force attacks
5. **Audit Logging**: Track login attempts and security events

## Support

For implementation questions, refer to:
- Architecture decisions: `docs/architecture/auth-architecture.md`
- API specification: `docs/api/auth-api-spec.yaml`
- Data model: `docs/specifications/user-model-spec.md`
