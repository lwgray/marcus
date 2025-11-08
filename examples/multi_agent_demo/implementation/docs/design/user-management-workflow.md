# User Management Workflow Design

## Overview
This document describes the complete user management workflow for the Task Management API application, including registration, authentication, profile management, and administration flows.

## 1. User Registration Workflow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ POST /auth/register
       │ {username, email, password, full_name}
       │
       ▼
┌─────────────────────────────┐
│   Validate Input            │
│   - Check email format      │
│   - Check password strength │
│   - Check username format   │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check Uniqueness          │
│   - Email not exists        │
│   - Username not exists     │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Hash Password (bcrypt)    │
│   - Cost factor: 12         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Create User Record        │
│   - Set is_active = true    │
│   - Set is_verified = false │
│   - Set role = 'user'       │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Generate Verification     │
│   Token (JWT, 24h expiry)   │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Send Verification Email   │
│   - Link with token         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Return Success Response   │
│   - User object (no pwd)    │
│   - Verification message    │
└─────────────────────────────┘
```

**Edge Cases:**
- Duplicate email → 409 Conflict
- Duplicate username → 409 Conflict
- Invalid email format → 400 Bad Request
- Weak password → 400 Bad Request with requirements
- Server error → 500 Internal Server Error

## 2. Email Verification Workflow

```
┌─────────────┐
│   Client    │
│ (Email Link)│
└──────┬──────┘
       │
       │ POST /auth/verify-email?token=xxx
       │
       ▼
┌─────────────────────────────┐
│   Validate Token            │
│   - Check signature         │
│   - Check expiration        │
│   - Extract user_id         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check User Exists         │
│   and Not Already Verified  │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Update User Record        │
│   - Set is_verified = true  │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Return Success            │
└─────────────────────────────┘
```

**Edge Cases:**
- Token expired → 400 Bad Request (resend link)
- Invalid token → 400 Bad Request
- User not found → 404 Not Found
- Already verified → 200 OK (idempotent)

## 3. Login Workflow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ POST /auth/login
       │ {email, password}
       │
       ▼
┌─────────────────────────────┐
│   Find User by Email        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check User Exists         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Verify Password (bcrypt)  │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check is_active = true    │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check is_verified = true  │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Generate JWT Access Token │
│   - User ID, role in claims │
│   - 24 hour expiration      │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Update last_login         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Return Token Response     │
│   {access_token, user}      │
└─────────────────────────────┘
```

**Edge Cases:**
- Invalid credentials → 401 Unauthorized (don't reveal which is wrong)
- Account inactive → 403 Forbidden with message
- Email not verified → 403 Forbidden with resend option
- Multiple failed attempts → Consider rate limiting

## 4. Profile Update Workflow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ PUT /users/me
       │ Authorization: Bearer <token>
       │ {full_name, email, username}
       │
       ▼
┌─────────────────────────────┐
│   Validate JWT Token        │
│   - Check signature         │
│   - Check expiration        │
│   - Extract user_id         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Validate Input            │
│   - Email format (if given) │
│   - Username format         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check Uniqueness          │
│   - Email (if changed)      │
│   - Username (if changed)   │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Update User Record        │
│   - Set updated_at          │
│   - If email changed:       │
│     set is_verified = false │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Send Verification Email   │
│   (if email changed)        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Return Updated User       │
└─────────────────────────────┘
```

**Edge Cases:**
- Token expired → 401 Unauthorized
- Email/username taken → 409 Conflict
- Invalid format → 400 Bad Request
- Email change requires re-verification

## 5. Password Change Workflow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ PUT /users/me/password
       │ Authorization: Bearer <token>
       │ {current_password, new_password}
       │
       ▼
┌─────────────────────────────┐
│   Validate JWT Token        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Verify Current Password   │
│   (bcrypt compare)          │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Validate New Password     │
│   - Strength requirements   │
│   - Different from current  │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Hash New Password         │
│   (bcrypt, cost 12)         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Update password_hash      │
│   - Set updated_at          │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Invalidate All Sessions   │
│   (Optional security)       │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Return Success            │
└─────────────────────────────┘
```

**Edge Cases:**
- Wrong current password → 400 Bad Request
- New password too weak → 400 Bad Request with requirements
- New password same as current → 400 Bad Request

## 6. Password Reset Workflow

### Step 1: Request Reset

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ POST /auth/password-reset
       │ {email}
       │
       ▼
┌─────────────────────────────┐
│   Find User by Email        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Generate Reset Token      │
│   (JWT, 1h expiry)          │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Send Reset Email          │
│   - Link with token         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Return Success            │
│   (Always, for security)    │
└─────────────────────────────┘
```

**Security Note:** Always return success even if email not found to prevent email enumeration attacks.

### Step 2: Confirm Reset

```
┌─────────────┐
│   Client    │
│ (Email Link)│
└──────┬──────┘
       │
       │ POST /auth/password-reset/confirm
       │ {token, new_password}
       │
       ▼
┌─────────────────────────────┐
│   Validate Token            │
│   - Check signature         │
│   - Check expiration (1h)   │
│   - Extract user_id         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Validate New Password     │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Hash New Password         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Update password_hash      │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Invalidate All Sessions   │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Send Confirmation Email   │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Return Success            │
└─────────────────────────────┘
```

**Edge Cases:**
- Token expired → 400 Bad Request (restart process)
- Invalid token → 400 Bad Request
- Weak password → 400 Bad Request

## 7. Admin: List Users Workflow

```
┌─────────────┐
│   Admin     │
└──────┬──────┘
       │
       │ GET /users?page=1&limit=20&role=user&is_active=true
       │ Authorization: Bearer <token>
       │
       ▼
┌─────────────────────────────┐
│   Validate JWT Token        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check Role = admin        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Apply Filters             │
│   - role                    │
│   - is_active               │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Apply Pagination          │
│   - Calculate offset        │
│   - Limit results           │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Get Total Count           │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Return Paginated Response │
│   {items, total, page,      │
│    limit}                   │
└─────────────────────────────┘
```

**Edge Cases:**
- Non-admin user → 403 Forbidden
- Invalid page/limit → Use defaults

## 8. Admin: Deactivate User Workflow

```
┌─────────────┐
│   Admin     │
└──────┬──────┘
       │
       │ DELETE /users/{user_id}
       │ Authorization: Bearer <token>
       │
       ▼
┌─────────────────────────────┐
│   Validate JWT Token        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check Role = admin        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check User Exists         │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Check Not Self-Deletion   │
│   (Can't delete own account)│
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Set is_active = false     │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Invalidate User Sessions  │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Log Admin Action          │
│   (Audit trail)             │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Return Success            │
└─────────────────────────────┘
```

**Edge Cases:**
- Non-admin → 403 Forbidden
- User not found → 404 Not Found
- Self-deletion attempt → 400 Bad Request

## State Transitions

### User Account States

```
┌──────────────┐
│  REGISTERED  │ (is_active=true, is_verified=false)
└──────┬───────┘
       │
       │ Email verification
       ▼
┌──────────────┐
│   VERIFIED   │ (is_active=true, is_verified=true)
└──────┬───────┘
       │
       │ Admin deactivation
       ▼
┌──────────────┐
│  DEACTIVATED │ (is_active=false)
└──────────────┘
       ▲
       │
       │ Admin reactivation (set is_active=true)
       │
       └──────────────────┐
                          │
                          ▼
                 ┌──────────────┐
                 │   VERIFIED   │
                 └──────────────┘
```

## Security Considerations

### Rate Limiting
- Login attempts: 5 per 15 minutes per IP
- Password reset requests: 3 per hour per email
- Registration: 10 per hour per IP

### Session Management
- JWT tokens: 24-hour expiration
- Refresh token strategy (optional future enhancement)
- Token invalidation on password change

### Input Validation
- All inputs sanitized and validated
- Email format validation (RFC 5322)
- Password complexity enforced
- Username alphanumeric + limited special chars

### Logging and Monitoring
- Failed login attempts
- Password changes
- Admin actions (user deactivation, role changes)
- Suspicious patterns (multiple failed registrations)

## Error Handling Strategy

| Scenario | HTTP Code | Response |
|----------|-----------|----------|
| Invalid credentials | 401 | Generic message (don't reveal which field is wrong) |
| Account inactive | 403 | "Account is inactive. Contact support." |
| Email not verified | 403 | "Please verify your email address." |
| Duplicate email/username | 409 | "Email/username already exists." |
| Weak password | 400 | Password requirements details |
| Invalid token | 400 | "Invalid or expired token." |
| Permission denied | 403 | "Insufficient permissions." |
| Resource not found | 404 | "User not found." |
| Server error | 500 | Generic error message (log details) |

## Performance Considerations

### Database Indexes
- `users.email` (unique)
- `users.username` (unique)
- `users.is_active`
- `users.role`
- `users.created_at` (for sorting)

### Caching Strategy
- User sessions in Redis (optional)
- JWT token blacklist (for invalidation)

### Query Optimization
- Paginate user lists
- Select only needed fields
- Use prepared statements

## Future Enhancements
- OAuth2 integration (Google, GitHub)
- Two-factor authentication (2FA)
- Refresh token rotation
- Account deletion (GDPR compliance)
- Password history (prevent reuse)
- Account lockout after failed attempts
- Email change confirmation workflow
