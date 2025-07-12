# Error Handling Strategy

## Overview
Consistent error handling across the Recipe Management API to provide clear, actionable feedback to clients while maintaining security.

## Error Response Format

### Standard Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid data",
    "details": {
      "field_errors": [
        {
          "field": "email",
          "code": "INVALID_FORMAT",
          "message": "Email format is invalid"
        }
      ]
    },
    "request_id": "req_123abc",
    "timestamp": "2025-07-07T15:30:00Z"
  }
}
```

## Error Categories

### 1. Client Errors (4xx)

#### 400 Bad Request
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "The request cannot be processed",
    "details": {
      "reason": "Missing required header: Content-Type"
    }
  }
}
```

#### 401 Unauthorized
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required",
    "details": {
      "auth_url": "/auth/login"
    }
  }
}
```

#### 403 Forbidden
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You don't have permission to access this resource",
    "details": {
      "required_role": "premium",
      "current_role": "user"
    }
  }
}
```

#### 404 Not Found
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": {
      "resource_type": "recipe",
      "resource_id": "123abc"
    }
  }
}
```

#### 422 Unprocessable Entity
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "field_errors": [
        {
          "field": "ingredients[0].quantity",
          "code": "MIN_VALUE",
          "message": "Quantity must be greater than 0"
        }
      ]
    }
  }
}
```

#### 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "limit": 1000,
      "window": "1h",
      "retry_after": 3600
    }
  }
}
```

### 2. Server Errors (5xx)

#### 500 Internal Server Error
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "request_id": "req_123abc"
  }
}
```

#### 503 Service Unavailable
```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Service temporarily unavailable",
    "details": {
      "retry_after": 30
    }
  }
}
```

## Error Codes Reference

### Authentication Errors
- `AUTH_INVALID_CREDENTIALS` - Invalid email or password
- `AUTH_TOKEN_EXPIRED` - JWT token has expired
- `AUTH_TOKEN_INVALID` - JWT token is malformed
- `AUTH_REFRESH_TOKEN_INVALID` - Refresh token is invalid
- `AUTH_ACCOUNT_LOCKED` - Account locked due to failed attempts
- `AUTH_EMAIL_NOT_VERIFIED` - Email verification required

### Validation Errors
- `VALIDATION_REQUIRED_FIELD` - Required field missing
- `VALIDATION_INVALID_FORMAT` - Field format is invalid
- `VALIDATION_MIN_LENGTH` - Value too short
- `VALIDATION_MAX_LENGTH` - Value too long
- `VALIDATION_MIN_VALUE` - Numeric value too small
- `VALIDATION_MAX_VALUE` - Numeric value too large
- `VALIDATION_INVALID_ENUM` - Value not in allowed list
- `VALIDATION_DUPLICATE` - Duplicate value not allowed

### Resource Errors
- `RESOURCE_NOT_FOUND` - Requested resource doesn't exist
- `RESOURCE_ALREADY_EXISTS` - Resource with identifier exists
- `RESOURCE_CONFLICT` - Resource state conflict
- `RESOURCE_DELETED` - Resource has been deleted
- `RESOURCE_QUOTA_EXCEEDED` - User quota exceeded

### Business Logic Errors
- `RECIPE_PRIVATE` - Recipe is private
- `RECIPE_ALREADY_RATED` - User already rated this recipe
- `INGREDIENT_NOT_IN_PANTRY` - Ingredient not in user's pantry
- `MEAL_PLAN_DATE_CONFLICT` - Meal already planned for this date
- `SUBSCRIPTION_REQUIRED` - Premium subscription required

## Error Handling Implementation

### 1. Custom Exception Classes

```python
class APIException(Exception):
    status_code = 500
    error_code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}

class ValidationError(APIException):
    status_code = 422
    error_code = "VALIDATION_ERROR"

class NotFoundError(APIException):
    status_code = 404
    error_code = "NOT_FOUND"

class AuthenticationError(APIException):
    status_code = 401
    error_code = "UNAUTHORIZED"

class PermissionError(APIException):
    status_code = 403
    error_code = "FORBIDDEN"
```

### 2. Global Error Handler

```python
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request.state.request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

### 3. Validation Error Handler

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "code": error["type"].upper(),
            "message": error["msg"]
        })

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": {"field_errors": errors}
            }
        }
    )
```

## Client-Side Error Handling

### JavaScript/TypeScript Example
```typescript
interface APIError {
  code: string;
  message: string;
  details?: any;
  request_id?: string;
}

class APIClient {
  async request(url: string, options: RequestInit) {
    try {
      const response = await fetch(url, options);
      const data = await response.json();

      if (!response.ok) {
        throw new APIError(data.error);
      }

      return data.data;
    } catch (error) {
      if (error instanceof APIError) {
        this.handleAPIError(error);
      }
      throw error;
    }
  }

  handleAPIError(error: APIError) {
    switch (error.code) {
      case 'AUTH_TOKEN_EXPIRED':
        // Refresh token
        break;
      case 'RATE_LIMIT_EXCEEDED':
        // Show rate limit message
        break;
      case 'VALIDATION_ERROR':
        // Display field errors
        break;
      default:
        // Show generic error
    }
  }
}
```

## Logging and Monitoring

### Error Logging Format
```json
{
  "level": "error",
  "timestamp": "2025-07-07T15:30:00Z",
  "request_id": "req_123abc",
  "user_id": "user_456def",
  "method": "POST",
  "path": "/api/recipes",
  "status_code": 422,
  "error_code": "VALIDATION_ERROR",
  "error_message": "Validation failed",
  "stack_trace": "...",
  "request_body": "...",
  "response_time_ms": 45
}
```

### Monitoring Alerts
- 5xx errors > 1% of requests
- 4xx errors > 10% of requests
- Specific error codes spike
- Response time > 1 second

## Security Considerations

### Information Disclosure
- Never expose internal error details in production
- Sanitize error messages for user consumption
- Log full details server-side only
- Use generic messages for authentication failures

### Error Message Examples
```
# Bad - Information disclosure
"User with email john@example.com not found"

# Good - Generic message
"Invalid credentials"

# Bad - System details
"PostgreSQL error: duplicate key violates unique constraint"

# Good - User-friendly
"An account with this email already exists"
```
