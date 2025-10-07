# Authentication System Architecture

## System Overview

This document describes the architecture and component interactions for the JWT-based authentication system.

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                │
│                                                                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │  Web App   │  │  Mobile    │  │  Desktop   │  │  Third     │    │
│  │            │  │  App       │  │  App       │  │  Party     │    │
│  │            │  │            │  │            │  │  Client    │    │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │
│         │               │               │               │             │
└─────────┼───────────────┼───────────────┼───────────────┼────────────┘
          │               │               │               │
          │         HTTPS REST API with JWT               │
          │               │               │               │
┌─────────┼───────────────┼───────────────┼───────────────┼────────────┐
│         │               │               │               │             │
│         └───────────────┴───────────────┴───────────────┘             │
│                            │                                           │
│                            ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              API GATEWAY / LOAD BALANCER                      │    │
│  │  - TLS termination                                            │    │
│  │  - Rate limiting (global)                                     │    │
│  │  - Request routing                                            │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                            │                                           │
│  ┌─────────────────────────┴──────────────────────────┐              │
│  │                                                     │              │
│  ▼                                                     ▼              │
│  ┌─────────────────────────┐      ┌──────────────────────────────┐  │
│  │  AUTH MIDDLEWARE        │      │  AUTHENTICATION SERVICE      │  │
│  │  ┌──────────────────┐   │      │  ┌────────────────────────┐ │  │
│  │  │ Token Validator  │───┼──────┼─▶│ Registration           │ │  │
│  │  │ - Parse JWT      │   │      │  │ - Validate input       │ │  │
│  │  │ - Verify sig     │   │      │  │ - Hash password        │ │  │
│  │  │ - Check exp      │   │      │  │ - Create user          │ │  │
│  │  │ - Check blacklist│   │      │  │ - Generate JWT         │ │  │
│  │  │ - Extract user   │   │      │  └────────────────────────┘ │  │
│  │  └──────────────────┘   │      │  ┌────────────────────────┐ │  │
│  └─────────────────────────┘      │  │ Login                  │ │  │
│             │                      │  │ - Validate creds       │ │  │
│             │ User Context         │  │ - Check account status │ │  │
│             │                      │  │ - Check lockout        │ │  │
│             ▼                      │  │ - Generate tokens      │ │  │
│  ┌─────────────────────────┐      │  │ - Update last_login    │ │  │
│  │  PROTECTED ENDPOINTS    │      │  └────────────────────────┘ │  │
│  │  - Todo API             │      │  ┌────────────────────────┐ │  │
│  │  - User Profile         │      │  │ Logout                 │ │  │
│  │  - Settings             │      │  │ - Blacklist token      │ │  │
│  │  - Admin APIs           │      │  │ - Revoke refresh token │ │  │
│  └─────────────────────────┘      │  └────────────────────────┘ │  │
│                                    │  ┌────────────────────────┐ │  │
│                                    │  │ Token Refresh          │ │  │
│                                    │  │ - Validate refresh tkn │ │  │
│                                    │  │ - Check revocation     │ │  │
│                                    │  │ - Rotate token         │ │  │
│                                    │  │ - Detect reuse         │ │  │
│                                    │  └────────────────────────┘ │  │
│                                    │  ┌────────────────────────┐ │  │
│                                    │  │ Password Reset         │ │  │
│                                    │  │ - Generate reset token │ │  │
│                                    │  │ - Send email           │ │  │
│                                    │  │ - Validate token       │ │  │
│                                    │  │ - Update password      │ │  │
│                                    │  └────────────────────────┘ │  │
│                                    └──────────────────────────────┘  │
│                                               │                       │
│  APPLICATION LAYER                           │                       │
└──────────────────────────────────────────────┼───────────────────────┘
                                               │
┌──────────────────────────────────────────────┼───────────────────────┐
│  DATA LAYER                                  │                       │
│                                               │                       │
│  ┌───────────────────────────────────────────▼─────────────────┐    │
│  │                    PRIMARY DATABASE                          │    │
│  │                                                               │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │    │
│  │  │   users     │  │  refresh_   │  │   token_    │         │    │
│  │  │             │  │  tokens     │  │  blacklist  │         │    │
│  │  │ - id        │  │             │  │             │         │    │
│  │  │ - email     │  │ - token_hash│  │ - token_jti │         │    │
│  │  │ - pass_hash │  │ - user_id   │  │ - user_id   │         │    │
│  │  │ - is_active │  │ - expires_at│  │ - expires_at│         │    │
│  │  │ - locked_   │  │ - revoked   │  │             │         │    │
│  │  │   until     │  │ - family_id │  │             │         │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │    │
│  │                                                               │    │
│  │  ┌─────────────┐  ┌─────────────┐                           │    │
│  │  │ password_   │  │ security_   │                           │    │
│  │  │ reset_tkns  │  │ events      │                           │    │
│  │  │             │  │             │                           │    │
│  │  │ - token     │  │ - event_type│                           │    │
│  │  │ - user_id   │  │ - user_id   │                           │    │
│  │  │ - expires_at│  │ - ip_address│                           │    │
│  │  │ - used      │  │ - timestamp │                           │    │
│  │  └─────────────┘  └─────────────┘                           │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                        │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │                    REDIS CACHE (Optional)                     │    │
│  │                                                               │    │
│  │  - Token blacklist (TTL-based)                               │    │
│  │  - Rate limiting counters                                    │    │
│  │  - Session data                                              │    │
│  │  - Failed login attempt counters                             │    │
│  └───────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│  EXTERNAL SERVICES                                                     │
│                                                                        │
│  ┌──────────────────────┐        ┌──────────────────────┐            │
│  │   Email Service      │        │  Monitoring/Logging  │            │
│  │   - Password reset   │        │  - Auth events       │            │
│  │   - Security alerts  │        │  - Failed logins     │            │
│  │   - Email verif.     │        │  - Token reuse       │            │
│  └──────────────────────┘        └──────────────────────┘            │
└────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Authentication Service

**Responsibilities:**
- User registration and validation
- Login and credential verification
- Token generation and management
- Password reset workflows
- Account lockout management

**Key Operations:**

#### Registration Flow
```
Client Request
      ↓
Validate Input (email format, password strength)
      ↓
Check Email Uniqueness
      ↓
Hash Password (bcrypt/argon2)
      ↓
Create User Record
      ↓
Generate JWT Token
      ↓
Return User + Token
```

#### Login Flow
```
Client Request (email, password)
      ↓
Rate Limit Check (10/15min/IP)
      ↓
Lookup User by Email
      ↓
Check Account Status (active, not locked)
      ↓
Verify Password (constant-time comparison)
      ↓
Check Failed Login Counter
      ↓
Generate Access + Refresh Tokens
      ↓
Update last_login Timestamp
      ↓
Log Security Event
      ↓
Return Tokens + User Data
```

#### Failed Login Handler
```
Failed Login Attempt
      ↓
Increment Failed Counter
      ↓
Check Threshold
      ├─ < 5 attempts: Allow retry
      ├─ 5 attempts: Lock for 30 minutes
      └─ 10 attempts: Lock for 2 hours
      ↓
Send Lock Notification Email
      ↓
Return Generic Error (no enumeration)
```

### 2. Token Validation Middleware

**Responsibilities:**
- Extract and validate JWT tokens
- Check token blacklist
- Verify token signatures and claims
- Extract user context
- Enforce authentication on protected routes

**Validation Pipeline:**
```
Incoming Request
      ↓
[1] Extract Authorization Header
      ├─ Missing → 401 AUTHENTICATION_REQUIRED
      └─ Present → Continue
      ↓
[2] Parse Bearer Token Format
      ├─ Invalid format → 401 INVALID_AUTH_HEADER
      └─ Valid → Continue
      ↓
[3] Verify JWT Signature
      ├─ Invalid → 401 INVALID_TOKEN_SIGNATURE
      └─ Valid → Continue
      ↓
[4] Check Expiration (exp claim)
      ├─ Expired → 401 TOKEN_EXPIRED
      └─ Valid → Continue
      ↓
[5] Verify Token Type = "access"
      ├─ Wrong type → 401 INVALID_TOKEN
      └─ Valid → Continue
      ↓
[6] Check Blacklist (by JTI)
      ├─ Blacklisted → 401 TOKEN_REVOKED
      └─ Not blacklisted → Continue
      ↓
[7] Extract User Context from Claims
      ├─ user_id, email, roles, permissions
      └─ Attach to request object
      ↓
[8] Continue to Route Handler
```

### 3. Token Management System

**Access Token:**
- **Lifespan:** 15 minutes - 1 hour
- **Storage:** Client-side only (memory/localStorage)
- **Purpose:** Authenticate API requests
- **Contains:** user_id, email, roles, permissions, expiration

**Refresh Token:**
- **Lifespan:** 7-30 days
- **Storage:** Database + client-side
- **Purpose:** Obtain new access tokens
- **Contains:** user_id, token_id, token_family_id, expiration

**Token Rotation Flow:**
```
Client sends Refresh Token
      ↓
Validate Token (signature, expiration)
      ↓
Check Database (not revoked)
      ↓
Generate NEW Access Token
      ↓
Generate NEW Refresh Token
      ↓
Revoke OLD Refresh Token
      ↓
Update token_family_id linkage
      ↓
Return New Tokens
```

**Token Reuse Detection:**
```
Client sends Revoked Refresh Token
      ↓
Detect token is revoked
      ↓
Check token_family_id
      ↓
SECURITY BREACH DETECTED
      ↓
Revoke ALL tokens in family
      ↓
Blacklist all active access tokens
      ↓
Send Security Alert Email
      ↓
Log Incident
      ↓
Return 401 TOKEN_REUSE_DETECTED
```

### 4. Blacklist Management

**Purpose:** Invalidate tokens before natural expiration

**Implementation Options:**

**Option A: Database Table**
```sql
CREATE TABLE token_blacklist (
    token_jti VARCHAR(255) PRIMARY KEY,
    user_id UUID,
    expires_at TIMESTAMP,
    created_at TIMESTAMP
);
```
- Pros: Persistent, reliable
- Cons: Slower lookup, requires cleanup job

**Option B: Redis Cache**
```
Key: "blacklist:{token_jti}"
Value: user_id
TTL: token expiration time
```
- Pros: Fast lookup, automatic expiration
- Cons: Requires Redis, potential data loss

**Recommended:** Hybrid approach
- Primary: Redis for speed
- Fallback: Database for reliability
- Background job: Sync Redis from DB on startup

### 5. Rate Limiting System

**Layers:**

**Global Rate Limit (API Gateway)**
- 1000 requests per IP per minute (total)

**Endpoint-Specific Limits:**
```
POST /api/auth/register      → 5 per IP per hour
POST /api/auth/login         → 10 per IP per 15 minutes
POST /api/auth/forgot-pass   → 3 per email per hour, 10 per IP per hour
POST /api/auth/refresh       → 30 per token per hour, 100 per IP per hour
```

**Implementation:**
```python
# Redis-based rate limiter
def check_rate_limit(key, limit, window_seconds):
    current = redis.incr(key)
    if current == 1:
        redis.expire(key, window_seconds)
    return current <= limit
```

### 6. Security Event Logging

**Events to Log:**

```python
SecurityEvent = {
    "login_success": {
        "user_id", "timestamp", "ip_address", "user_agent"
    },
    "login_failed": {
        "email", "timestamp", "ip_address", "reason"
    },
    "account_locked": {
        "user_id", "timestamp", "reason", "duration"
    },
    "logout": {
        "user_id", "timestamp", "logout_type"
    },
    "token_reuse_detected": {
        "user_id", "timestamp", "token_family_id"
    },
    "password_changed": {
        "user_id", "timestamp", "method"
    }
}
```

**Use Cases:**
- Security monitoring and alerts
- User activity audit trail
- Anomaly detection (ML-based)
- Compliance reporting

## Security Architecture

### Defense in Depth Layers

```
┌────────────────────────────────────────────────┐
│ Layer 1: Network Security                     │
│ - TLS/HTTPS encryption                         │
│ - Firewall rules                               │
│ - DDoS protection                              │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ Layer 2: API Gateway                           │
│ - Global rate limiting                         │
│ - IP whitelisting/blacklisting                 │
│ - Request validation                           │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ Layer 3: Authentication                        │
│ - JWT token validation                         │
│ - Token blacklist checking                     │
│ - Session management                           │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ Layer 4: Authorization                         │
│ - Role-based access control (RBAC)             │
│ - Permission checking                          │
│ - Resource ownership validation                │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ Layer 5: Application Logic                    │
│ - Input validation & sanitization              │
│ - Business logic enforcement                   │
│ - Data validation                              │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ Layer 6: Data Protection                       │
│ - Password hashing (bcrypt/argon2)             │
│ - Data encryption at rest                      │
│ - Secure token storage                         │
└────────────────────────────────────────────────┘
```

### Attack Prevention Strategies

**1. Brute Force Attacks**
- Rate limiting per IP and per account
- Progressive delays on failed attempts
- Account lockout after threshold
- CAPTCHA after multiple failures (optional)

**2. Token Theft**
- Short-lived access tokens (15-60 min)
- Refresh token rotation
- Token reuse detection
- Immediate revocation capability

**3. Timing Attacks**
- Constant-time password comparison
- Same response time for all auth failures
- Dummy operations for non-existent users

**4. User Enumeration**
- Generic error messages
- Same response for "user not found" and "wrong password"
- Same response time regardless of user existence

**5. XSS (Cross-Site Scripting)**
- Input sanitization (strip HTML)
- CSP headers
- HTTPOnly cookies for sensitive data
- Escape output

**6. SQL Injection**
- Parameterized queries
- ORM usage
- Input validation
- Principle of least privilege for DB user

**7. CSRF (Cross-Site Request Forgery)**
- CSRF tokens for state-changing operations
- SameSite cookie attribute
- Origin/Referer header validation

## Scalability Considerations

### Horizontal Scaling

**Stateless Design:**
- No server-side session state
- JWT tokens are self-contained
- Redis for shared state (blacklist, rate limits)

**Load Balancing:**
- Round-robin distribution
- Health checks
- Sticky sessions not required

### Performance Optimization

**Database:**
- Index on users.email (unique)
- Index on token_blacklist.token_jti
- Index on refresh_tokens.token_hash
- Partition security_events by timestamp

**Caching:**
- Cache token blacklist in Redis (TTL-based)
- Cache rate limit counters in Redis
- Consider CDN for static assets

**Token Validation:**
- Verify signature locally (no DB hit)
- Check blacklist in Redis (fast)
- Fallback to DB only if Redis unavailable

### Monitoring & Metrics

**Key Metrics:**
- Authentication success/failure rate
- Token refresh rate
- Token reuse detection events
- Account lockout frequency
- Rate limit violations
- API response times
- Database query performance

**Alerts:**
- Spike in failed login attempts (DDoS/brute force)
- Token reuse detected (potential breach)
- High rate of account lockouts
- Abnormal token refresh patterns
- Database connection issues

## Technology Stack Recommendations

**Backend Framework:**
- Python: FastAPI, Django, Flask
- Node.js: Express, NestJS
- Go: Gin, Echo
- Java: Spring Boot

**Database:**
- Primary: PostgreSQL (ACID compliant)
- Alternative: MySQL, MongoDB

**Cache/Session Store:**
- Redis (recommended)
- Memcached
- In-memory (single server only)

**JWT Library:**
- Python: PyJWT, python-jose
- Node.js: jsonwebtoken
- Go: golang-jwt
- Java: jjwt

**Password Hashing:**
- bcrypt (industry standard)
- argon2 (more modern, memory-hard)

**Email Service:**
- SendGrid
- AWS SES
- Mailgun
- Postmark

**Monitoring:**
- Application: Sentry, New Relic, DataDog
- Logs: ELK Stack, Splunk
- Metrics: Prometheus + Grafana

## Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│              Cloud Provider (AWS/GCP/Azure)     │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │          Load Balancer                    │ │
│  └───────────────────────────────────────────┘ │
│              │              │                   │
│  ┌───────────▼────┐  ┌──────▼──────────┐      │
│  │ App Server 1   │  │  App Server 2   │      │
│  │ (Auth Service) │  │  (Auth Service) │      │
│  └────────┬───────┘  └────────┬────────┘      │
│           │                    │                │
│  ┌────────▼────────────────────▼──────────┐   │
│  │       PostgreSQL (Primary)              │   │
│  │       - Read Replica (optional)         │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │       Redis Cluster                     │   │
│  │       - Token blacklist                 │   │
│  │       - Rate limiting                   │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Testing Strategy

**Unit Tests:**
- Password hashing/verification
- JWT generation/validation
- Input validation functions
- Rate limiting logic
- Token rotation logic

**Integration Tests:**
- Registration flow end-to-end
- Login flow with database
- Token refresh flow
- Password reset flow
- Middleware integration

**Security Tests:**
- Penetration testing
- Token theft scenarios
- Brute force resistance
- Timing attack resistance
- SQL injection attempts

**Performance Tests:**
- Load testing (1000+ concurrent logins)
- Token validation latency
- Database query performance
- Redis cache hit rates

## Future Enhancements

**OAuth 2.0 / Social Login:**
- Google Sign-In
- GitHub OAuth
- Facebook Login

**Multi-Factor Authentication (MFA):**
- TOTP (Time-based One-Time Password)
- SMS verification
- Email verification codes

**Biometric Authentication:**
- Fingerprint
- Face ID
- WebAuthn support

**Advanced Security:**
- Device fingerprinting
- Geolocation-based access control
- Behavioral biometrics
- Risk-based authentication

**Session Management:**
- View active sessions
- Remote session termination
- Session timeout policies
- Device trust management
