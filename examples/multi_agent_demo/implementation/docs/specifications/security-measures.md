# Security Measures and Best Practices

## Authentication Security

### 1. Password Security

#### Password Hashing
- **Algorithm**: bcrypt with cost factor 12
- **Rationale**: Adaptive hashing resistant to brute-force attacks
- **Implementation**:
  ```python
  import bcrypt

  def hash_password(password: str) -> str:
      salt = bcrypt.gensalt(rounds=12)
      return bcrypt.hashpw(password.encode(), salt).decode()

  def verify_password(password: str, hashed: str) -> bool:
      return bcrypt.checkpw(password.encode(), hashed.encode())
  ```

#### Password Requirements
- Minimum 8 characters, maximum 128 (DoS prevention)
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one digit (0-9)
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
- Check against common password lists (Have I Been Pwned API)

#### Password Validation
```python
import re

def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if len(password) > 128:
        return False, "Password too long (max 128 characters)"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain digit"
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        return False, "Password must contain special character"
    return True, "Password is strong"
```

### 2. Rate Limiting

#### Login Rate Limiting
- **Purpose**: Prevent brute-force attacks
- **Strategy**: Progressive delays + account lockout

**Implementation**:
```python
# Per IP address
LOGIN_ATTEMPTS_PER_IP = 5
LOCKOUT_DURATION_MINUTES = 15

# Per account
LOGIN_ATTEMPTS_PER_ACCOUNT = 5
ACCOUNT_LOCKOUT_DURATION_MINUTES = 30

# Rate limiting windows
RATE_LIMIT_WINDOW_MINUTES = 15
```

**Lockout Logic**:
1. Track failed login attempts per IP and per account
2. After 5 failed attempts: 15-minute lockout
3. After 10 failed attempts: 1-hour lockout
4. After 20 failed attempts: 24-hour lockout
5. Send security alert email to user

#### API Rate Limiting
- **Global**: 100 requests per minute per IP
- **Auth endpoints**: 10 requests per minute per IP
- **Authenticated users**: 1000 requests per hour

**Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1696781700
```

### 3. Token Security

#### Token Storage (Server)
- Refresh tokens: Store as SHA-256 hash only
- Never store access tokens server-side
- Use database transactions for token operations
- Implement token cleanup job (remove expired tokens daily)

#### Token Storage (Client Recommendations)
- **Web**: httpOnly, secure, SameSite cookies
- **Mobile**: Secure storage (Keychain/KeyStore)
- **Never**: URL parameters, localStorage (if XSS risk)

#### Token Transmission
- Always use HTTPS in production
- Include in `Authorization: Bearer <token>` header
- Never log full tokens (log last 4 characters only)

### 4. HTTPS/TLS

#### Requirements
- **Development**: HTTP acceptable (localhost only)
- **Production**: HTTPS required (TLS 1.2+)
- **Certificate**: Valid SSL certificate (Let's Encrypt)
- **HSTS**: Strict-Transport-Security header enabled

**Headers**:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### 5. CORS (Cross-Origin Resource Sharing)

#### Configuration
```python
ALLOWED_ORIGINS = [
    "https://app.example.com",
    "https://www.example.com"
]

# Development only
if ENVIRONMENT == "development":
    ALLOWED_ORIGINS.append("http://localhost:3000")

CORS_CONFIG = {
    "origins": ALLOWED_ORIGINS,
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_credentials": True,
    "max_age": 3600
}
```

### 6. CSRF Protection

#### Strategy
- Use SameSite cookies for session tokens
- Implement CSRF tokens for state-changing operations
- Verify Origin/Referer headers

**Implementation**:
```python
# Cookie configuration
COOKIE_CONFIG = {
    "httponly": True,
    "secure": True,  # HTTPS only
    "samesite": "Strict",
    "max_age": 900  # 15 minutes
}
```

### 7. XSS Protection

#### Measures
- Sanitize all user input
- Escape output in HTML contexts
- Content Security Policy (CSP) headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY

**Headers**:
```
Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

### 8. SQL Injection Prevention

#### Measures
- Use parameterized queries (always)
- ORM with proper escaping
- Input validation on all parameters
- Principle of least privilege (database user)

**Example (SQLAlchemy)**:
```python
# GOOD: Parameterized query
user = session.query(User).filter(User.email == email).first()

# BAD: String concatenation (NEVER DO THIS)
# query = f"SELECT * FROM users WHERE email = '{email}'"
```

### 9. Input Validation

#### Validation Rules
- **Email**: RFC 5322 compliant format
- **Username**: Alphanumeric + underscore, 3-50 chars
- **UUID**: Valid UUID v4 format
- **Timestamps**: ISO 8601 format

**Implementation**:
```python
from pydantic import BaseModel, EmailStr, validator

class RegistrationRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]{3,50}$', v):
            raise ValueError('Invalid username format')
        return v

    @validator('password')
    def validate_password(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v
```

### 10. Logging and Monitoring

#### Security Logging
- Log all authentication attempts (success/failure)
- Log token generation and refresh
- Log password changes
- Log account lockouts
- **Never log**: Passwords, tokens, sensitive PII

**Log Format**:
```json
{
  "timestamp": "2025-10-08T12:00:00Z",
  "event": "login_failed",
  "user_id": null,
  "email": "user@example.com",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "reason": "invalid_password",
  "attempt_number": 3
}
```

#### Monitoring Alerts
- **Critical**: 10+ failed logins from single IP
- **High**: Account locked due to failed attempts
- **Medium**: Password changed without recent login
- **Low**: Refresh token used after revocation

### 11. Account Security Features

#### Email Verification
- Send verification email on registration
- Account limited until email verified
- Verification link expires in 24 hours

#### Password Reset
- Generate secure random token (32 bytes)
- Token expires in 1 hour
- Invalidate all tokens on password change
- Send confirmation email after reset

#### Two-Factor Authentication (Future)
- TOTP-based (Google Authenticator compatible)
- Backup codes for recovery
- Optional but recommended

### 12. Session Management

#### Session Security
- Generate new session ID on login
- Invalidate sessions on logout
- Implement session timeout (7 days max)
- Track concurrent sessions (limit to 5)

#### Session Fixation Prevention
- Regenerate session ID after authentication
- Bind sessions to IP address (optional)
- Detect session hijacking attempts

### 13. Database Security

#### Access Control
- Separate database user for application
- Read-only user for reporting
- No root/admin access from application
- Principle of least privilege

#### Encryption
- Encrypt data at rest (database encryption)
- Encrypt backups
- Sensitive fields: additional encryption layer

#### Connection Security
- Use SSL/TLS for database connections
- Restrict database access to application servers
- Use connection pooling with limits

### 14. Error Handling

#### Secure Error Messages
- **User-facing**: Generic messages ("Invalid credentials")
- **Logs**: Detailed error information
- **Never expose**: Stack traces, SQL queries, internal paths

**Example**:
```python
# Public error
return {"success": false, "error": "Invalid email or password"}

# Log (internal)
logger.error(f"Login failed for {email}: password_mismatch, attempt {attempt_num}")
```

### 15. Dependency Security

#### Best Practices
- Keep dependencies updated (monthly review)
- Use dependency scanning (Dependabot, Snyk)
- Pin dependency versions
- Review security advisories

**Tools**:
```bash
# Python
pip install safety
safety check

# Automated scanning
pip install pip-audit
pip-audit
```

## Security Checklist

### Pre-Production
- [ ] All secrets in environment variables
- [ ] HTTPS enforced (HSTS enabled)
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Security headers set
- [ ] Input validation comprehensive
- [ ] SQL injection prevention verified
- [ ] XSS prevention verified
- [ ] CSRF protection enabled
- [ ] Password requirements enforced
- [ ] Bcrypt cost factor appropriate (12+)
- [ ] Token expiry appropriate
- [ ] Logging configured (no sensitive data)
- [ ] Error messages sanitized
- [ ] Dependencies scanned for vulnerabilities
- [ ] Database access restricted
- [ ] Account lockout implemented
- [ ] Email verification enabled

### Ongoing
- [ ] Monitor failed login attempts
- [ ] Review security logs weekly
- [ ] Update dependencies monthly
- [ ] Rotate JWT secret keys quarterly
- [ ] Security audit annually
- [ ] Penetration testing annually

## Compliance Considerations

### GDPR (if applicable)
- User consent for data collection
- Right to data deletion
- Data breach notification (72 hours)
- Data encryption at rest and in transit

### CCPA (if applicable)
- Privacy policy disclosure
- Right to opt-out
- Data access requests

### OWASP Top 10 Coverage
1. ✅ Broken Access Control - JWT + role-based authorization
2. ✅ Cryptographic Failures - bcrypt, HTTPS, token hashing
3. ✅ Injection - Parameterized queries, input validation
4. ✅ Insecure Design - Secure authentication flow
5. ✅ Security Misconfiguration - Security headers, CORS
6. ✅ Vulnerable Components - Dependency scanning
7. ✅ Authentication Failures - Rate limiting, strong passwords
8. ✅ Data Integrity Failures - JWT signatures, HTTPS
9. ✅ Logging Failures - Comprehensive security logging
10. ✅ SSRF - Input validation, URL restrictions
