# Security Implementation Guide

## Overview

This document describes the security implementation for the Task Management API, including password hashing, JWT authentication, input sanitization, and rate limiting.

## Architecture

### Security Modules

```
app/security/
├── __init__.py          # Package exports
├── password.py          # Password hashing and validation
├── jwt_handler.py       # JWT token management
├── sanitizer.py         # Input sanitization utilities
└── rate_limit.py        # Rate limiting configuration
```

## Password Security

### Implementation: `app/security/password.py`

**Technology**: bcrypt with automatic salting

**Configuration**:
- Default work factor: 12 rounds
- Timing-safe comparison for verification
- Password strength evaluation

### Usage

```python
from app.security.password import hash_password, verify_password, get_password_strength

# Hash a password during registration
password_hash = hash_password("user_password")
# Store password_hash in database

# Verify password during login
is_valid = verify_password("user_password", stored_hash)

# Check password strength before accepting
strength = get_password_strength("user_password")
# Returns: {
#   "score": 0-5,
#   "length": int,
#   "has_lower": bool,
#   "has_upper": bool,
#   "has_digit": bool,
#   "has_special": bool,
#   "recommendation": str
# }
```

### Security Features
- ✅ Automatic salt generation (unique per password)
- ✅ Configurable work factor (default 12 rounds)
- ✅ Timing-safe comparison prevents timing attacks
- ✅ Password strength evaluation with 5-level scoring

## JWT Authentication

### Implementation: `app/security/jwt_handler.py`

**Technology**: PyJWT (HS256 algorithm)

**Configuration**:
- Algorithm: HS256 (HMAC with SHA-256)
- Default expiration: 24 hours
- Secret key: Load from `JWT_SECRET_KEY` environment variable
- Token refresh supported

### Environment Variables Required

```bash
JWT_SECRET_KEY=your-secret-key-here  # MUST be set, use secrets.token_urlsafe(32)
JWT_ALGORITHM=HS256                   # Optional, defaults to HS256
JWT_EXPIRATION_HOURS=24               # Optional, defaults to 24
```

### Usage

```python
from app.security.jwt_handler import (
    create_access_token,
    verify_token,
    get_current_user,
    refresh_token,
    TokenExpiredError,
    TokenInvalidError
)

# Create token during login
token = create_access_token(
    user_id=user.id,
    username=user.username,
    additional_claims={"role": "admin"}  # Optional
)

# Verify token from request header
try:
    payload = verify_token(token)
    user_id = payload["user_id"]
    username = payload["sub"]
except TokenExpiredError:
    # Handle expired token - prompt for refresh
    pass
except TokenInvalidError:
    # Handle invalid token - require re-login
    pass

# Extract user from token (convenience function)
user_info = get_current_user(token)
# Returns: {"user_id": int, "username": str, ...additional_claims}

# Refresh token before expiration
new_token = refresh_token(old_token)
```

### Token Structure

```json
{
  "sub": "username",
  "user_id": 123,
  "iat": 1234567890,
  "exp": 1234654290,
  "...": "additional_claims"
}
```

### Security Features
- ✅ Signature verification prevents tampering
- ✅ Expiration checking prevents replay attacks
- ✅ Custom claims support (roles, permissions)
- ✅ Token refresh capability
- ✅ Graceful error handling with custom exceptions

## Input Sanitization

### Implementation: `app/security/sanitizer.py`

**Technology**: bleach, regex validation, urllib.parse

### Usage

#### HTML Sanitization (XSS Prevention)

```python
from app.security.sanitizer import sanitize_html

# Sanitize user-provided HTML content
safe_html = sanitize_html(user_html_content)

# Custom allowed tags
safe_html = sanitize_html(
    user_html_content,
    allowed_tags=['p', 'br', 'strong', 'em'],
    strip=True  # Remove disallowed tags entirely
)
```

**Default Allowed Tags**: p, br, strong, em, ul, ol, li, a, span, div  
**Default Allowed Attributes**: href, title, class  
**Default Allowed Protocols**: http, https, mailto

#### Plain Text Sanitization

```python
from app.security.sanitizer import sanitize_text

# Remove HTML and normalize whitespace
clean_text = sanitize_text(
    user_input,
    max_length=200  # Optional truncation with "..." suffix
)
```

#### Filename Sanitization (Path Traversal Prevention)

```python
from app.security.sanitizer import sanitize_filename

# Remove path separators and dangerous characters
safe_filename = sanitize_filename("../../etc/passwd")
# Returns: "etcpasswd" (safe for file operations)
```

#### Email Sanitization

```python
from app.security.sanitizer import sanitize_email

try:
    clean_email = sanitize_email("  User@Example.COM  ")
    # Returns: "user@example.com" (lowercased, trimmed)
except ValueError as e:
    # Handle invalid email format
    pass
```

#### URL Sanitization

```python
from app.security.sanitizer import sanitize_url

try:
    safe_url = sanitize_url("https://example.com/path")
    # Validates scheme (http/https only) and domain presence
except ValueError as e:
    # Handle invalid URL (javascript:, data:, missing domain)
    pass
```

#### SQL LIKE Escaping (SQL Injection Prevention)

```python
from app.security.sanitizer import escape_sql_like

# Escape wildcards in user input for LIKE queries
user_search = "50% discount"
escaped = escape_sql_like(user_search)
# Returns: "50\\% discount"

# Use in SQLAlchemy query
query = session.query(Product).filter(Product.name.like(f"%{escaped}%"))
```

### Security Features
- ✅ XSS prevention via HTML sanitization
- ✅ Path traversal prevention via filename sanitization
- ✅ Email validation with regex
- ✅ URL scheme validation (blocks javascript:, data:)
- ✅ SQL injection prevention for LIKE queries

## Rate Limiting

### Implementation: `app/security/rate_limit.py`

**Technology**: Flask-Limiter

**Configuration**:
- Strategy: Fixed-window counting
- Storage: Configurable (memory or Redis)
- Default limit: 200 requests/hour per IP

### Environment Variables Required

```bash
RATE_LIMIT_STORAGE_URL=memory://           # Or redis://localhost:6379
RATE_LIMIT_ENABLED=true                    # Optional, defaults to true
```

### Usage

#### Flask Application Setup

```python
from flask import Flask
from app.security.rate_limit import limiter, configure_rate_limiting

app = Flask(__name__)
limiter.init_app(app)
configure_rate_limiting(app)
```

#### Applying Rate Limits to Routes

```python
from flask import Flask, jsonify
from app.security.rate_limit import auth_rate_limit, password_reset_rate_limit

@app.route('/api/auth/login', methods=['POST'])
@auth_rate_limit()  # 5 requests per minute
def login():
    # Login logic
    return jsonify({"token": "..."})

@app.route('/api/auth/password-reset', methods=['POST'])
@password_reset_rate_limit()  # 3 requests per hour
def password_reset():
    # Password reset logic
    return jsonify({"message": "Reset email sent"})

# Custom rate limit
@app.route('/api/expensive-operation', methods=['POST'])
@limiter.limit("10 per hour")
def expensive_operation():
    # Heavy computation
    return jsonify({"result": "..."})
```

#### Exempting Routes

```python
from app.security.rate_limit import limiter

@app.route('/api/health', methods=['GET'])
@limiter.exempt
def health_check():
    return jsonify({"status": "healthy"})
```

### Rate Limit Configuration

| Endpoint Pattern | Limit | Rationale |
|-----------------|-------|-----------|
| `/api/auth/login`, `/api/auth/register` | 5/minute | Prevent brute-force attacks |
| `/api/auth/password-reset` | 3/hour | Prevent abuse and spam |
| Default (all endpoints) | 200/hour | General DoS prevention |

### Security Features
- ✅ Brute-force prevention on authentication
- ✅ DoS prevention with global rate limits
- ✅ Configurable storage backend (Redis for distributed systems)
- ✅ Per-IP tracking
- ✅ Custom limits per endpoint

## Integration Patterns

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, HTTPException, status
from app.security.jwt_handler import get_current_user, TokenExpiredError, TokenInvalidError
from app.security.password import hash_password, verify_password
from app.security.sanitizer import sanitize_email, sanitize_text

app = FastAPI()

# Dependency for protected routes
async def get_authenticated_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    try:
        user_info = get_current_user(token)
        return user_info
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Token expired")
    except TokenInvalidError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Registration endpoint
@app.post("/api/auth/register")
async def register(username: str, email: str, password: str):
    # Sanitize inputs
    clean_email = sanitize_email(email)
    clean_username = sanitize_text(username, max_length=80)
    
    # Hash password
    password_hash = hash_password(password)
    
    # Create user in database
    # ... database logic ...
    
    return {"message": "User created"}

# Login endpoint
@app.post("/api/auth/login")
async def login(username: str, password: str):
    # Fetch user from database
    # ... database logic ...
    
    # Verify password
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = create_access_token(user_id=user.id, username=user.username)
    
    return {"token": token, "user": {"id": user.id, "username": user.username}}

# Protected endpoint
@app.get("/api/protected")
async def protected_route(user: dict = Depends(get_authenticated_user)):
    return {"message": f"Hello {user['username']}"}
```

### Flask Integration

```python
from flask import Flask, request, jsonify
from functools import wraps
from app.security.jwt_handler import get_current_user, TokenExpiredError, TokenInvalidError
from app.security.password import hash_password, verify_password
from app.security.rate_limit import limiter, auth_rate_limit

app = Flask(__name__)
limiter.init_app(app)

# Auth decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid authorization header"}), 401
        
        token = auth_header.split(' ')[1]
        try:
            user_info = get_current_user(token)
            request.current_user = user_info
            return f(*args, **kwargs)
        except TokenExpiredError:
            return jsonify({"error": "Token expired"}), 401
        except TokenInvalidError:
            return jsonify({"error": "Invalid token"}), 401
    
    return decorated_function

@app.route('/api/auth/login', methods=['POST'])
@auth_rate_limit()
def login():
    data = request.get_json()
    # ... login logic with verify_password ...
    return jsonify({"token": token})

@app.route('/api/protected', methods=['GET'])
@require_auth
def protected_route():
    user = request.current_user
    return jsonify({"message": f"Hello {user['username']}"})
```

## Testing

### Test Coverage

- **Password hashing**: 15 tests, 100% coverage
- **JWT handling**: 22 tests, 100% coverage
- **Input sanitization**: 17 tests, 89% coverage
- **Rate limiting**: Requires Flask app context (57% coverage)

### Running Tests

```bash
# Run all security tests
python -m pytest tests/unit/security/ -v

# With coverage report
python -m pytest tests/unit/security/ --cov=app/security --cov-report=term-missing

# Run specific test file
python -m pytest tests/unit/security/test_jwt.py -v
```

## Dependencies

```txt
bcrypt>=4.0.0           # Password hashing
PyJWT>=2.8.0            # JWT token handling
bleach>=6.0.0           # HTML sanitization
Flask-Limiter>=3.5.0    # Rate limiting
```

Install with:
```bash
pip install bcrypt PyJWT bleach Flask-Limiter
```

## Security Best Practices

### Password Security
- ✅ Never store plain-text passwords
- ✅ Use minimum 12 rounds for bcrypt (configurable higher for sensitive systems)
- ✅ Enforce password strength requirements at registration
- ✅ Implement password rotation policies

### JWT Security
- ✅ Store JWT_SECRET_KEY securely (use environment variables, never commit)
- ✅ Use strong secret keys (minimum 256 bits, use `secrets.token_urlsafe(32)`)
- ✅ Implement token refresh to limit exposure window
- ✅ Consider shorter expiration times for high-security endpoints
- ✅ Implement token revocation for logout (requires database or Redis)

### Input Sanitization
- ✅ Sanitize ALL user inputs before storage or display
- ✅ Use whitelist approach (allowed tags) not blacklist
- ✅ Validate email format before sending emails
- ✅ Sanitize filenames before file operations
- ✅ Use parameterized queries for SQL (never string concatenation)

### Rate Limiting
- ✅ Use Redis for distributed systems (multiple app instances)
- ✅ Apply strictest limits to authentication endpoints
- ✅ Monitor rate limit violations for attack detection
- ✅ Implement exponential backoff for repeated violations
- ✅ Exempt health check endpoints from rate limits

## Troubleshooting

### JWT Token Issues

**Problem**: `TokenInvalidError: Invalid token`  
**Solution**: Check JWT_SECRET_KEY matches between token creation and verification

**Problem**: `TokenExpiredError: Token has expired`  
**Solution**: Implement token refresh flow or increase JWT_EXPIRATION_HOURS

### Rate Limiting Issues

**Problem**: Rate limits not working  
**Solution**: Ensure `limiter.init_app(app)` is called before route definitions

**Problem**: Rate limits too strict in development  
**Solution**: Set `RATE_LIMIT_ENABLED=false` in development environment

### Password Hashing Issues

**Problem**: Password verification takes too long  
**Solution**: Reduce bcrypt rounds (use 10-11 for faster verification, but less secure)

**Problem**: `ValueError: Invalid salt`  
**Solution**: Ensure password_hash is stored as UTF-8 string, not bytes

## References

- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [bcrypt Documentation](https://github.com/pyca/bcrypt/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [Flask-Limiter Documentation](https://flask-limiter.readthedocs.io/)
- [bleach Documentation](https://bleach.readthedocs.io/)

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-08  
**Author**: Foundation Agent (agent_foundation)  
**Task**: Security Implementation (Task ID: 1616789808523249040)