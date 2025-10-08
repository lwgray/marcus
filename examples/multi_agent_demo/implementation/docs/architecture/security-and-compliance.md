# Security and Compliance Architecture

## Overview
This document outlines the security measures, compliance requirements, and best practices for the User Management system. It covers authentication, authorization, data protection, and regulatory compliance.

## 1. Authentication Security

### Password Security

#### Hashing Algorithm
- **Algorithm**: bcrypt
- **Cost Factor**: 12 (adjustable based on hardware)
- **Salt**: Automatically generated per password (bcrypt handles this)
- **Storage**: Only hashed passwords stored, never plaintext

**Rationale**: bcrypt is designed for password hashing with built-in salt and adaptive cost factor, resistant to rainbow table and brute-force attacks.

```python
# Implementation reference
import bcrypt

def hash_password(password: str) -> str:
    """Hash password using bcrypt with cost factor 12."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
```

#### Password Requirements
- **Minimum Length**: 8 characters
- **Complexity**:
  - At least 1 uppercase letter (A-Z)
  - At least 1 lowercase letter (a-z)
  - At least 1 digit (0-9)
  - At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
- **Validation**: Server-side enforcement (client-side for UX only)
- **Password Strength Meter**: Recommended for client implementations

```python
# Password validation pattern
import re

def validate_password_strength(password: str) -> dict:
    """
    Validate password meets security requirements.

    Returns dict with 'valid' bool and 'errors' list.
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")

    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        errors.append("Password must contain at least one special character")

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }
```

### JWT Token Security

#### Token Structure
- **Header**: Algorithm (HS256) and type (JWT)
- **Payload**: User claims (user_id, email, role, exp, iat, jti)
- **Signature**: HMAC SHA256 with secret key

#### Token Configuration
- **Algorithm**: HS256 (HMAC with SHA-256)
- **Expiration**: 24 hours (86400 seconds)
- **Secret Key**:
  - Minimum 256 bits (32 bytes) of random data
  - Stored in environment variables
  - Different keys for dev/staging/production
  - Rotated periodically (quarterly recommended)

#### Token Claims
```json
{
  "sub": "user_id_uuid",
  "email": "user@example.com",
  "role": "user",
  "exp": 1234567890,
  "iat": 1234481490,
  "jti": "unique_token_id"
}
```

- **sub** (subject): User ID
- **email**: User email (for convenience)
- **role**: User role for authorization
- **exp** (expiration): Unix timestamp
- **iat** (issued at): Unix timestamp
- **jti** (JWT ID): Unique token identifier (for blacklisting)

#### Token Invalidation Strategy
- **Session Blacklist**: Store invalidated token JTIs in Redis
- **Invalidation Triggers**:
  - User logout
  - Password change
  - Account deactivation
  - Admin action
- **Cleanup**: Automatically remove expired tokens from blacklist

```python
# Token blacklist pseudocode
async def invalidate_token(jti: str, exp: int):
    """Add token to blacklist until its expiration."""
    ttl = exp - current_timestamp()
    await redis.setex(f"blacklist:{jti}", ttl, "1")

async def is_token_blacklisted(jti: str) -> bool:
    """Check if token is blacklisted."""
    return await redis.exists(f"blacklist:{jti}")
```

### Session Management

#### Token Storage (Client-side)
- **Recommended**: HTTP-only cookie (XSS protection)
- **Alternative**: LocalStorage (more flexible, requires CSRF protection)
- **Never**: SessionStorage for persistent sessions

#### Token Transmission
- **HTTPS Only**: All authentication endpoints require HTTPS in production
- **Header**: `Authorization: Bearer <token>`
- **Cookie**: Secure, HttpOnly, SameSite=Strict flags

#### Token Refresh Strategy (Future Enhancement)
- **Refresh Token**: Long-lived token (30 days) for obtaining new access tokens
- **Rotation**: Issue new refresh token with each use
- **Storage**: Database with user association
- **Revocation**: Immediate revocation capability

## 2. Authorization and Access Control

### Role-Based Access Control (RBAC)

#### Roles
1. **user** (default)
   - Access own profile
   - Update own information
   - Change own password
   - Manage own preferences

2. **moderator**
   - All user permissions
   - View other users (read-only)
   - Flag content (future feature)

3. **admin**
   - All moderator permissions
   - Manage all users (CRUD)
   - Deactivate accounts
   - Change user roles
   - Access admin endpoints

#### Permission Matrix

| Endpoint | User | Moderator | Admin |
|----------|------|-----------|-------|
| POST /auth/register | ✓ (public) | ✓ (public) | ✓ (public) |
| POST /auth/login | ✓ (public) | ✓ (public) | ✓ (public) |
| POST /auth/logout | ✓ | ✓ | ✓ |
| GET /users/me | ✓ | ✓ | ✓ |
| PUT /users/me | ✓ | ✓ | ✓ |
| PUT /users/me/password | ✓ | ✓ | ✓ |
| GET /users/me/preferences | ✓ | ✓ | ✓ |
| PUT /users/me/preferences | ✓ | ✓ | ✓ |
| GET /users | ✗ | ✓ (read) | ✓ |
| GET /users/{id} | ✗ | ✓ (read) | ✓ |
| DELETE /users/{id} | ✗ | ✗ | ✓ |

### Authorization Implementation

```python
# Dependency for role checking
from fastapi import Depends, HTTPException, status
from typing import List

def require_role(allowed_roles: List[str]):
    """
    Dependency to check if user has required role.

    Parameters
    ----------
    allowed_roles : List[str]
        List of roles that can access the endpoint

    Returns
    -------
    Callable
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

# Usage in endpoints
@app.get("/users")
async def list_users(
    current_user: User = Depends(require_role(["admin"]))
):
    """List all users (admin only)."""
    pass
```

## 3. Input Validation and Sanitization

### Validation Strategy
- **Server-side validation**: Always enforce (primary security boundary)
- **Client-side validation**: UX improvement only (not trusted)
- **Database constraints**: Additional safety layer

### Input Validation Rules

#### Email Validation
- **Format**: RFC 5322 compliant
- **Max Length**: 254 characters
- **Normalization**: Lowercase before storage
- **Library**: `email-validator` Python package

```python
from email_validator import validate_email, EmailNotValidError

def validate_email_address(email: str) -> str:
    """
    Validate and normalize email address.

    Raises
    ------
    ValueError
        If email is invalid
    """
    try:
        validated = validate_email(email, check_deliverability=False)
        return validated.normalized
    except EmailNotValidError as e:
        raise ValueError(f"Invalid email: {str(e)}")
```

#### Username Validation
- **Pattern**: `^[a-zA-Z0-9_-]{3,50}$`
- **Min Length**: 3 characters
- **Max Length**: 50 characters
- **Allowed**: Letters, numbers, underscore, hyphen
- **Case**: Case-sensitive (but unique check is case-insensitive)

#### Data Sanitization
- **HTML Encoding**: All user-generated content
- **SQL Injection Prevention**: ORM with parameterized queries
- **NoSQL Injection Prevention**: Input validation and type checking
- **XSS Prevention**: Content Security Policy headers

### Pydantic Models for Validation

```python
from pydantic import BaseModel, EmailStr, Field, validator
import re

class UserRegistration(BaseModel):
    """User registration request model."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None

    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                'Username must contain only letters, numbers, '
                'underscores, and hyphens'
            )
        return v

    @validator('password')
    def validate_password(cls, v):
        result = validate_password_strength(v)
        if not result['valid']:
            raise ValueError(', '.join(result['errors']))
        return v
```

## 4. Data Protection

### Data at Rest
- **Database Encryption**: Enable at database level (e.g., PostgreSQL pgcrypto)
- **Sensitive Fields**: Password hashes (bcrypt handles encryption)
- **Backup Encryption**: All backups encrypted before storage
- **Key Management**: Separate key storage (AWS KMS, HashiCorp Vault)

### Data in Transit
- **TLS/SSL**: Required for all production traffic
- **Certificate**: Valid TLS 1.2+ certificate
- **HSTS**: HTTP Strict Transport Security header
- **Certificate Pinning**: Consider for mobile apps

```python
# Security headers middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["example.com", "*.example.com"]
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = \
        "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = \
        "default-src 'self'"
    return response
```

### Personal Data Handling
- **Minimize Collection**: Only collect necessary data
- **Purpose Limitation**: Use data only for stated purposes
- **Data Retention**: Define retention periods
- **Right to Deletion**: Implement account deletion (GDPR Article 17)
- **Data Portability**: Export user data on request (GDPR Article 20)

## 5. Rate Limiting and DDoS Protection

### Rate Limiting Strategy

#### Endpoint-Specific Limits
| Endpoint | Limit | Window | Identifier |
|----------|-------|--------|------------|
| POST /auth/login | 5 attempts | 15 minutes | IP + Email |
| POST /auth/register | 10 attempts | 1 hour | IP |
| POST /auth/password-reset | 3 attempts | 1 hour | IP + Email |
| POST /auth/verify-email | 10 attempts | 1 hour | IP |
| PUT /users/me | 20 attempts | 1 hour | User ID |
| GET /users | 100 requests | 1 minute | User ID |

#### Implementation

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/15minutes")
async def login(request: Request, credentials: UserLogin):
    """Login with rate limiting."""
    pass
```

#### Rate Limit Response
- **Status Code**: 429 Too Many Requests
- **Headers**:
  - `X-RateLimit-Limit`: Total allowed requests
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Unix timestamp for reset
  - `Retry-After`: Seconds until retry allowed

### DDoS Protection
- **Layer 4**: Network-level protection (firewall, load balancer)
- **Layer 7**: Application-level (rate limiting, CAPTCHA)
- **CDN**: Use CDN with DDoS protection (Cloudflare, AWS Shield)
- **IP Blocking**: Automatic blocking of malicious IPs

## 6. Audit Logging and Monitoring

### Security Events to Log

#### Authentication Events
- Failed login attempts (IP, email, timestamp)
- Successful logins (IP, user_id, timestamp)
- Account lockouts
- Password changes
- Password reset requests
- Token invalidations

#### Authorization Events
- Permission denied (403) events
- Role changes
- Admin actions (user deactivation, role modifications)

#### Suspicious Activity
- Multiple failed login attempts
- Access from unusual locations
- Rapid account creation from same IP
- Brute force patterns

### Log Format

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "event_type": "failed_login",
  "severity": "warning",
  "user_identifier": "user@example.com",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "details": {
    "reason": "invalid_password",
    "attempt_number": 3
  },
  "trace_id": "abc123xyz"
}
```

### Monitoring Alerts
- **Failed Login Threshold**: >5 attempts in 15 minutes
- **Account Enumeration**: Multiple 404s on user endpoints
- **Privilege Escalation**: Repeated 403 Forbidden responses
- **Mass Data Access**: Unusual number of user queries
- **Token Anomalies**: Expired token usage patterns

### Log Storage
- **Retention**: 90 days for security logs, 1 year for audit logs
- **Access Control**: Restricted to security team and admins
- **Encryption**: Logs encrypted at rest
- **Tampering Protection**: Write-once storage or blockchain

## 7. Regulatory Compliance

### GDPR (General Data Protection Regulation)

#### Lawful Basis
- **Consent**: Users consent to data processing during registration
- **Contract**: Processing necessary for service provision
- **Legitimate Interest**: Security and fraud prevention

#### User Rights Implementation

##### Right to Access (Article 15)
```python
@app.get("/users/me/data-export")
async def export_user_data(current_user: User = Depends(get_current_user)):
    """
    Export all user data in JSON format.

    Includes: profile, preferences, activity logs, audit trail
    """
    return {
        "profile": current_user.to_dict(),
        "preferences": await get_user_preferences(current_user.id),
        "created_at": current_user.created_at,
        "last_login": current_user.last_login,
        "export_date": datetime.utcnow()
    }
```

##### Right to Erasure (Article 17)
```python
@app.delete("/users/me/account")
async def delete_account(
    current_user: User = Depends(get_current_user),
    confirmation: str = Body(...)
):
    """
    Permanently delete user account and all associated data.

    - Anonymize data that must be retained for legal reasons
    - Delete personal information
    - Invalidate all sessions
    """
    if confirmation != "DELETE":
        raise HTTPException(400, "Invalid confirmation")

    await anonymize_user_data(current_user.id)
    await delete_user_sessions(current_user.id)
    await log_account_deletion(current_user.id)

    return {"message": "Account deleted successfully"}
```

##### Right to Rectification (Article 16)
- Implemented via `PUT /users/me` endpoint
- Users can update incorrect personal information

##### Right to Data Portability (Article 20)
- Implemented via `/users/me/data-export` endpoint
- Data provided in machine-readable format (JSON)

#### Data Protection by Design
- **Privacy by Default**: Minimal data collection
- **Pseudonymization**: User IDs are UUIDs, not sequential
- **Encryption**: All sensitive data encrypted
- **Access Controls**: Role-based access to personal data
- **Data Minimization**: Only collect necessary data

### CCPA (California Consumer Privacy Act)

#### Consumer Rights
- **Right to Know**: What data is collected (privacy policy)
- **Right to Delete**: Account deletion endpoint
- **Right to Opt-Out**: Email preferences in user settings
- **Non-Discrimination**: No penalty for exercising rights

#### Implementation
- Privacy policy disclosure
- Account deletion functionality
- Opt-out mechanisms for marketing
- No sale of personal information

### SOC 2 Considerations

#### Security Principle
- Access controls (RBAC)
- Encryption (at rest and in transit)
- Monitoring and logging
- Incident response plan

#### Availability Principle
- System uptime monitoring
- Backup and recovery procedures
- DDoS protection

#### Confidentiality Principle
- Data classification
- Need-to-know access
- NDA requirements

## 8. Incident Response

### Security Incident Types
- Data breach
- Unauthorized access
- Account compromise
- DDoS attack
- Vulnerability disclosure

### Response Procedure

1. **Detection**: Monitoring alerts, user reports
2. **Containment**: Isolate affected systems, revoke access
3. **Investigation**: Analyze logs, determine scope
4. **Eradication**: Remove threat, patch vulnerabilities
5. **Recovery**: Restore systems, verify integrity
6. **Post-Incident**: Document lessons, update procedures

### Breach Notification
- **Timeline**: Notify affected users within 72 hours (GDPR)
- **Content**: Nature of breach, data affected, mitigation steps
- **Channels**: Email, in-app notification, website notice
- **Authorities**: Report to relevant data protection authorities

## 9. Security Testing

### Testing Requirements

#### Unit Tests
- Password hashing verification
- Token generation and validation
- Input validation logic
- Permission checking

#### Integration Tests
- Authentication flows
- Authorization enforcement
- Rate limiting
- Session management

#### Security Tests
- **OWASP Top 10**:
  - SQL Injection (SQLMap)
  - XSS (XSS Hunter)
  - CSRF
  - Broken authentication
  - Security misconfiguration
  - Sensitive data exposure
- **Penetration Testing**: Quarterly by security firm
- **Dependency Scanning**: Automated (Snyk, Dependabot)
- **Static Analysis**: SAST tools (Bandit for Python)

### Vulnerability Management
- **Disclosure Policy**: Security email for reports
- **Bug Bounty**: Consider program for responsible disclosure
- **Patch Timeline**: Critical (24h), High (7d), Medium (30d)

## 10. Development Security Practices

### Secure Development Lifecycle

1. **Design Phase**
   - Threat modeling
   - Security requirements
   - Architecture review

2. **Implementation Phase**
   - Secure coding guidelines
   - Code review checklist
   - Pre-commit hooks (secrets scanning)

3. **Testing Phase**
   - Security test suite
   - Dependency scanning
   - SAST/DAST tools

4. **Deployment Phase**
   - Environment separation (dev/staging/prod)
   - Secrets management
   - Secure CI/CD pipeline

### Secrets Management
- **Never**: Commit secrets to version control
- **Environment Variables**: Use for configuration
- **Secrets Manager**: AWS Secrets Manager, HashiCorp Vault
- **Rotation**: Regular secret rotation policy

```bash
# .env.example (committed)
JWT_SECRET_KEY=<generate-random-256-bit-key>
DATABASE_URL=postgresql://user:password@localhost/dbname  # pragma: allowlist secret
REDIS_URL=redis://localhost:6379

# .env (gitignored, actual secrets)
JWT_SECRET_KEY=actual-secret-here  # pragma: allowlist secret
DATABASE_URL=postgresql://produser:prodpass@prodhost/proddb  # pragma: allowlist secret
REDIS_URL=redis://prodhost:6379
```

### Code Review Security Checklist
- [ ] Input validation on all user inputs
- [ ] Parameterized queries (no string concatenation)
- [ ] Authentication required for protected endpoints
- [ ] Authorization checks for sensitive operations
- [ ] No secrets in code or logs
- [ ] Error messages don't leak sensitive information
- [ ] Rate limiting on authentication endpoints
- [ ] HTTPS enforced in production
- [ ] Security headers configured
- [ ] Dependencies up to date

## 11. Production Security Checklist

### Pre-Deployment
- [ ] All secrets in environment variables
- [ ] JWT secret key is strong (256-bit random)
- [ ] Database credentials are unique and strong
- [ ] TLS/SSL certificate installed and valid
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Logging and monitoring configured
- [ ] Backup procedures tested
- [ ] Incident response plan documented

### Post-Deployment
- [ ] Security scan completed
- [ ] Penetration test passed
- [ ] Monitoring alerts configured
- [ ] Log aggregation working
- [ ] Backup verification successful
- [ ] Rollback procedure tested

## Summary

This security architecture provides:
- **Strong Authentication**: bcrypt password hashing, JWT tokens
- **Granular Authorization**: Role-based access control
- **Data Protection**: Encryption at rest and in transit
- **Regulatory Compliance**: GDPR, CCPA requirements met
- **Proactive Defense**: Rate limiting, monitoring, incident response
- **Secure Development**: Testing, code review, secrets management

### Security Contacts
- **Security Issues**: security@example.com
- **Privacy Questions**: privacy@example.com
- **Incident Response**: incident@example.com (24/7)

### References
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- GDPR: https://gdpr.eu/
- NIST Cybersecurity Framework: https://www.nist.gov/cyberframework
- JWT Best Practices: https://tools.ietf.org/html/rfc8725
