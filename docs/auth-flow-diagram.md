# Authentication Flow Diagram

## User Registration Flow
1. User submits registration form
2. Server validates input
3. Password hashed with bcrypt
4. User record created
5. Verification email sent
6. User clicks verification link
7. Account activated

## Login Flow
1. User submits credentials
2. Server validates credentials
3. JWT token generated (15 min expiry)
4. Refresh token generated (7 days)
5. Tokens returned to client
