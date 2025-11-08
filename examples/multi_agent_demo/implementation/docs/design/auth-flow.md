# User Authentication Flow

## Overview
This document describes the JWT-based authentication flow for the Task Management API.

## Authentication Flow Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ 1. POST /api/auth/register
       │    {email, password, username}
       ▼
┌─────────────────────────────────────┐
│         Registration Flow           │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Validate Input               │  │
│  │ - Email format               │  │
│  │ - Password strength          │  │
│  │ - Username uniqueness        │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │ Hash Password (bcrypt)       │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │ Store User in Database       │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │ Generate JWT Access Token    │  │
│  │ Generate JWT Refresh Token   │  │
│  └──────────┬───────────────────┘  │
│             │                       │
└─────────────┼───────────────────────┘
              │
              │ Response: {access_token, refresh_token, user}
              ▼
       ┌─────────────┐
       │   Client    │
       │ (Store JWT) │
       └──────┬──────┘
              │
              │ 2. POST /api/auth/login
              │    {email, password}
              ▼
┌─────────────────────────────────────┐
│            Login Flow               │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Validate Credentials         │  │
│  │ - Find user by email         │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │ Verify Password (bcrypt)     │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │ Generate JWT Access Token    │  │
│  │ Generate JWT Refresh Token   │  │
│  └──────────┬───────────────────┘  │
│             │                       │
└─────────────┼───────────────────────┘
              │
              │ Response: {access_token, refresh_token, user}
              ▼
       ┌─────────────┐
       │   Client    │
       │ (Store JWT) │
       └──────┬──────┘
              │
              │ 3. GET /api/users/me
              │    Authorization: Bearer <access_token>
              ▼
┌─────────────────────────────────────┐
│       Protected Resource Flow       │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Extract JWT from Header      │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │ Verify JWT Signature         │  │
│  │ - Check expiration           │  │
│  │ - Validate signature         │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │ Extract User ID from Token   │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │ Fetch User Data              │  │
│  └──────────┬───────────────────┘  │
│             │                       │
└─────────────┼───────────────────────┘
              │
              │ Response: {user data}
              ▼
       ┌─────────────┐
       │   Client    │
       └──────┬──────┘
              │
              │ 4. POST /api/auth/refresh
              │    {refresh_token}
              ▼
┌─────────────────────────────────────┐
│         Token Refresh Flow          │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Verify Refresh Token         │  │
│  │ - Check signature            │  │
│  │ - Check expiration           │  │
│  │ - Check revocation status    │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │ Generate New Access Token    │  │
│  └──────────┬───────────────────┘  │
│             │                       │
└─────────────┼───────────────────────┘
              │
              │ Response: {access_token}
              ▼
       ┌─────────────┐
       │   Client    │
       └─────────────┘
```

## Token Lifecycle

1. **Access Token**: Short-lived (15 minutes), used for API authentication
2. **Refresh Token**: Long-lived (7 days), used to obtain new access tokens
3. **Token Rotation**: Refresh tokens are rotated on each use for security

## Error Handling

- **401 Unauthorized**: Invalid or expired token
- **403 Forbidden**: Valid token but insufficient permissions
- **429 Too Many Requests**: Rate limiting triggered
