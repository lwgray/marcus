# JWT Implementation Guide for Todo App

## Overview
This guide covers the implementation of JSON Web Tokens (JWT) for the Todo App authentication system.

## JWT Structure

### Access Token Claims
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "role": "user",
  "iat": 1706620800,
  "exp": 1706621700,
  "iss": "todo-app",
  "aud": "todo-app-frontend"
}
```

### Refresh Token Claims
```json
{
  "sub": "user-uuid",
  "tokenFamily": "family-uuid",
  "iat": 1706620800,
  "exp": 1707225600,
  "iss": "todo-app",
  "type": "refresh"
}
```

## Implementation

### 1. Token Generation

```typescript
import jwt from 'jsonwebtoken';
import { randomBytes } from 'crypto';

interface TokenPair {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

class JWTService {
  private readonly accessTokenSecret: string;
  private readonly refreshTokenSecret: string;
  private readonly accessTokenExpiry: string = '15m';
  private readonly refreshTokenExpiry: string = '7d';

  constructor() {
    this.accessTokenSecret = process.env.JWT_ACCESS_SECRET!;
    this.refreshTokenSecret = process.env.JWT_REFRESH_SECRET!;
  }

  generateTokenPair(userId: string, email: string, role: string): TokenPair {
    const tokenFamily = randomBytes(16).toString('hex');
    
    const accessToken = jwt.sign(
      {
        sub: userId,
        email,
        role,
        iss: 'todo-app',
        aud: 'todo-app-frontend'
      },
      this.accessTokenSecret,
      { expiresIn: this.accessTokenExpiry }
    );

    const refreshToken = jwt.sign(
      {
        sub: userId,
        tokenFamily,
        type: 'refresh',
        iss: 'todo-app'
      },
      this.refreshTokenSecret,
      { expiresIn: this.refreshTokenExpiry }
    );

    return {
      accessToken,
      refreshToken,
      expiresIn: 900 // 15 minutes in seconds
    };
  }

  verifyAccessToken(token: string): any {
    return jwt.verify(token, this.accessTokenSecret);
  }

  verifyRefreshToken(token: string): any {
    return jwt.verify(token, this.refreshTokenSecret);
  }
}
```

### 2. Token Storage

#### Backend (Sessions Table)
```typescript
async function storeRefreshToken(
  userId: string, 
  refreshToken: string, 
  tokenFamily: string,
  ipAddress: string,
  userAgent: string
): Promise<void> {
  const hashedToken = await bcrypt.hash(refreshToken, 10);
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days

  await db.query(`
    INSERT INTO sessions (user_id, refresh_token, refresh_token_family, expires_at, ip_address, user_agent)
    VALUES ($1, $2, $3, $4, $5, $6)
  `, [userId, hashedToken, tokenFamily, expiresAt, ipAddress, userAgent]);
}
```

#### Frontend Storage
```typescript
class TokenManager {
  private static readonly ACCESS_TOKEN_KEY = 'todo_access_token';
  private static readonly REFRESH_TOKEN_KEY = 'todo_refresh_token';

  static setTokens(accessToken: string, refreshToken: string): void {
    // Store access token in memory only
    sessionStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
    
    // Store refresh token in httpOnly cookie (set by backend)
    // Or in secure storage for mobile apps
  }

  static getAccessToken(): string | null {
    return sessionStorage.getItem(this.ACCESS_TOKEN_KEY);
  }

  static clearTokens(): void {
    sessionStorage.removeItem(this.ACCESS_TOKEN_KEY);
    // Clear cookies through logout endpoint
  }
}
```

### 3. Token Refresh Implementation

```typescript
class TokenRefreshService {
  async refreshTokens(oldRefreshToken: string): Promise<TokenPair> {
    try {
      // Verify the refresh token
      const decoded = this.jwtService.verifyRefreshToken(oldRefreshToken);
      
      // Check if token exists and is not revoked
      const session = await this.findValidSession(oldRefreshToken);
      if (!session) {
        throw new UnauthorizedException('Invalid refresh token');
      }

      // Check token family for rotation
      const familySessions = await this.getTokenFamily(decoded.tokenFamily);
      
      // Revoke all tokens in the family (rotation)
      await this.revokeTokenFamily(decoded.tokenFamily);

      // Generate new token pair
      const user = await this.userService.findById(decoded.sub);
      const newTokens = this.jwtService.generateTokenPair(
        user.id,
        user.email,
        user.role
      );

      // Store new refresh token
      await this.storeRefreshToken(
        user.id,
        newTokens.refreshToken,
        decoded.tokenFamily,
        session.ipAddress,
        session.userAgent
      );

      return newTokens;
    } catch (error) {
      // Log potential token theft attempt
      await this.logSecurityEvent('refresh_token_failed', { 
        error: error.message 
      });
      throw new UnauthorizedException('Token refresh failed');
    }
  }
}
```

### 4. Middleware Implementation

```typescript
export const authenticateToken = async (
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
      return res.status(401).json({ error: 'Access token required' });
    }

    const decoded = jwt.verify(token, process.env.JWT_ACCESS_SECRET!);
    req.user = decoded;
    next();
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Token expired' });
    }
    return res.status(403).json({ error: 'Invalid token' });
  }
};
```

### 5. Auto-Refresh on Frontend

```typescript
class AuthInterceptor {
  private refreshing = false;
  private refreshSubscribers: ((token: string) => void)[] = [];

  setupInterceptors(axiosInstance: AxiosInstance): void {
    // Request interceptor
    axiosInstance.interceptors.request.use(
      (config) => {
        const token = TokenManager.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    axiosInstance.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.refreshing) {
            // Wait for refresh to complete
            return new Promise((resolve) => {
              this.refreshSubscribers.push((token: string) => {
                originalRequest.headers.Authorization = `Bearer ${token}`;
                resolve(axiosInstance(originalRequest));
              });
            });
          }

          originalRequest._retry = true;
          this.refreshing = true;

          try {
            const response = await this.refreshAccessToken();
            const { accessToken } = response.data;
            
            TokenManager.setTokens(accessToken, response.data.refreshToken);
            this.onRefreshed(accessToken);
            
            return axiosInstance(originalRequest);
          } catch (refreshError) {
            // Refresh failed, redirect to login
            this.redirectToLogin();
            return Promise.reject(refreshError);
          } finally {
            this.refreshing = false;
            this.refreshSubscribers = [];
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private onRefreshed(token: string): void {
    this.refreshSubscribers.forEach(callback => callback(token));
  }

  private async refreshAccessToken(): Promise<any> {
    return axios.post('/api/auth/refresh', {}, {
      withCredentials: true // Send httpOnly cookie
    });
  }

  private redirectToLogin(): void {
    TokenManager.clearTokens();
    window.location.href = '/login';
  }
}
```

## Security Best Practices

### 1. Token Security
- Use strong, unique secrets for signing tokens
- Rotate secrets periodically
- Never expose secrets in client-side code
- Use different secrets for access and refresh tokens

### 2. Token Expiration
- Access tokens: 15 minutes
- Refresh tokens: 7 days
- Implement sliding sessions for active users

### 3. Token Storage
- Never store tokens in localStorage (XSS vulnerable)
- Use httpOnly, secure, sameSite cookies for refresh tokens
- Store access tokens in memory or sessionStorage
- Clear tokens on logout

### 4. Token Validation
- Always validate token signature
- Check expiration time
- Verify issuer and audience claims
- Validate user still exists and is active

### 5. Refresh Token Rotation
- Generate new refresh token on each use
- Revoke old refresh tokens
- Track token families to detect theft
- Invalidate all tokens on suspicious activity

## Environment Variables

```env
# JWT Configuration
JWT_ACCESS_SECRET=your-super-secret-access-key-min-32-chars
JWT_REFRESH_SECRET=your-super-secret-refresh-key-min-32-chars
JWT_ACCESS_EXPIRY=15m
JWT_REFRESH_EXPIRY=7d
JWT_ISSUER=todo-app
JWT_AUDIENCE=todo-app-frontend

# Security
BCRYPT_ROUNDS=10
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=15m
```

## Testing

### Unit Tests
```typescript
describe('JWTService', () => {
  it('should generate valid token pair', () => {
    const tokens = jwtService.generateTokenPair('user-id', 'test@example.com', 'user');
    expect(tokens.accessToken).toBeDefined();
    expect(tokens.refreshToken).toBeDefined();
    expect(tokens.expiresIn).toBe(900);
  });

  it('should verify valid access token', () => {
    const tokens = jwtService.generateTokenPair('user-id', 'test@example.com', 'user');
    const decoded = jwtService.verifyAccessToken(tokens.accessToken);
    expect(decoded.sub).toBe('user-id');
    expect(decoded.email).toBe('test@example.com');
  });

  it('should reject expired token', async () => {
    const expiredToken = jwt.sign(
      { sub: 'user-id' },
      process.env.JWT_ACCESS_SECRET!,
      { expiresIn: '-1h' }
    );
    
    expect(() => jwtService.verifyAccessToken(expiredToken))
      .toThrow('jwt expired');
  });
});
```

## Common Issues and Solutions

### 1. Token Expiration During Request
**Problem**: User makes a request but token expires before completion.
**Solution**: Implement request retry with token refresh.

### 2. Multiple Concurrent Requests
**Problem**: Multiple 401 responses trigger multiple refresh attempts.
**Solution**: Queue requests during refresh and retry after new token obtained.

### 3. Refresh Token Theft
**Problem**: Attacker steals refresh token and uses it.
**Solution**: Implement token rotation and family tracking to detect reuse.

### 4. Clock Skew
**Problem**: Server and client clocks differ causing premature expiration.
**Solution**: Add small buffer (30s) to expiration validation.