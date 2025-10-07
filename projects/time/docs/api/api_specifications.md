# API Specifications - Time Tracking Platform

## Overview

This document provides detailed API specifications for the Time Tracking and Data Analytics Platform. All APIs follow REST principles and return JSON responses.

**Base URL**: `https://api.timetracker.com/api/v1`

**Authentication**: Bearer token (JWT) in Authorization header

**Content-Type**: `application/json`

## Common Response Formats

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2025-10-06T12:00:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      "field": ["Validation error message"]
    }
  },
  "meta": {
    "timestamp": "2025-10-06T12:00:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2025-10-06T12:00:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT, PATCH requests |
| 201 | Created | Successful POST request creating resource |
| 204 | No Content | Successful DELETE request |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

## Authentication Service

### POST /auth/register
Register a new user account.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Validation Rules**:
- `email`: Valid email format, unique, max 255 chars
- `password`: Min 8 chars, must contain uppercase, lowercase, number, special char
- `full_name`: Min 2 chars, max 255 chars

**Response** (201):
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe",
      "created_at": "2025-10-06T12:00:00Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Errors**:
- 400: Invalid email format
- 422: Email already registered

---

### POST /auth/login
Authenticate user and receive JWT tokens.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe",
      "last_login": "2025-10-06T12:00:00Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 900
  }
}
```

**Errors**:
- 401: Invalid credentials
- 403: Account locked (too many failed attempts)

---

### POST /auth/refresh
Refresh access token using refresh token.

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 900
  }
}
```

---

### POST /auth/logout
Invalidate current session.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "data": {
    "message": "Successfully logged out"
  }
}
```

---

### GET /auth/me
Get current authenticated user details.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2025-10-06T12:00:00Z",
    "is_active": true
  }
}
```

---

### PUT /auth/password
Change user password.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "message": "Password updated successfully"
  }
}
```

**Errors**:
- 401: Current password incorrect
- 422: New password doesn't meet requirements

---

## Task Management Service

### GET /tasks
List all tasks for authenticated user with filtering and pagination.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `page` (int, default: 1): Page number
- `per_page` (int, default: 20, max: 100): Items per page
- `status` (string, optional): Filter by status (todo, in_progress, done, archived)
- `priority` (string, optional): Filter by priority (low, medium, high, urgent)
- `search` (string, optional): Search in title and description
- `tags` (string, optional): Comma-separated tags
- `due_before` (ISO datetime, optional): Tasks due before date
- `due_after` (ISO datetime, optional): Tasks due after date
- `sort_by` (string, default: created_at): Sort field
- `sort_order` (string, default: desc): asc or desc

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Complete project proposal",
      "description": "Write and submit Q4 project proposal",
      "status": "in_progress",
      "priority": "high",
      "due_date": "2025-10-15T17:00:00Z",
      "created_at": "2025-10-01T09:00:00Z",
      "updated_at": "2025-10-05T14:30:00Z",
      "tags": ["work", "important"],
      "estimated_hours": 8.0,
      "time_tracked_hours": 5.5
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### POST /tasks
Create a new task.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "title": "Complete project proposal",
  "description": "Write and submit Q4 project proposal",
  "status": "todo",
  "priority": "high",
  "due_date": "2025-10-15T17:00:00Z",
  "tags": ["work", "important"],
  "estimated_hours": 8.0
}
```

**Validation Rules**:
- `title`: Required, max 200 chars
- `description`: Optional, max 5000 chars
- `status`: Optional, default "todo", enum values
- `priority`: Optional, default "medium", enum values
- `due_date`: Optional, ISO datetime format
- `tags`: Optional, array of strings
- `estimated_hours`: Optional, positive number

**Response** (201):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Complete project proposal",
    "description": "Write and submit Q4 project proposal",
    "status": "todo",
    "priority": "high",
    "due_date": "2025-10-15T17:00:00Z",
    "created_at": "2025-10-06T12:00:00Z",
    "updated_at": "2025-10-06T12:00:00Z",
    "tags": ["work", "important"],
    "estimated_hours": 8.0,
    "time_tracked_hours": 0.0
  }
}
```

---

### GET /tasks/{task_id}
Get detailed information about a specific task.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Complete project proposal",
    "description": "Write and submit Q4 project proposal",
    "status": "in_progress",
    "priority": "high",
    "due_date": "2025-10-15T17:00:00Z",
    "created_at": "2025-10-01T09:00:00Z",
    "updated_at": "2025-10-05T14:30:00Z",
    "tags": ["work", "important"],
    "estimated_hours": 8.0,
    "time_tracked_hours": 5.5,
    "time_entries": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440000",
        "start_time": "2025-10-05T10:00:00Z",
        "end_time": "2025-10-05T12:30:00Z",
        "duration_hours": 2.5
      }
    ]
  }
}
```

**Errors**:
- 404: Task not found
- 403: Task belongs to another user

---

### PUT /tasks/{task_id}
Update an existing task (full update).

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "title": "Complete project proposal - UPDATED",
  "description": "Write and submit Q4 project proposal with budget",
  "status": "in_progress",
  "priority": "urgent",
  "due_date": "2025-10-14T17:00:00Z",
  "tags": ["work", "important", "urgent"],
  "estimated_hours": 10.0
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Complete project proposal - UPDATED",
    "description": "Write and submit Q4 project proposal with budget",
    "status": "in_progress",
    "priority": "urgent",
    "due_date": "2025-10-14T17:00:00Z",
    "created_at": "2025-10-01T09:00:00Z",
    "updated_at": "2025-10-06T12:00:00Z",
    "tags": ["work", "important", "urgent"],
    "estimated_hours": 10.0,
    "time_tracked_hours": 5.5
  }
}
```

---

### PATCH /tasks/{task_id}/status
Update only the status of a task.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "status": "done"
}
```

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "done",
    "updated_at": "2025-10-06T12:00:00Z"
  }
}
```

---

### DELETE /tasks/{task_id}
Delete a task permanently.

**Headers**: `Authorization: Bearer <token>`

**Response** (204): No content

**Errors**:
- 404: Task not found
- 403: Task belongs to another user

---

### GET /tasks/search
Advanced search for tasks with full-text search.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `q` (string, required): Search query
- `page` (int, default: 1)
- `per_page` (int, default: 20)

**Response** (200): Same format as GET /tasks

---

## Time Tracking Service

### POST /time/start
Start time tracking for a task or general time.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "description": "Working on project proposal"
}
```

**Validation Rules**:
- `task_id`: Optional, valid UUID, task must exist
- `description`: Optional, max 500 chars
- Only one active time entry allowed per user

**Response** (201):
```json
{
  "success": true,
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "start_time": "2025-10-06T12:00:00Z",
    "end_time": null,
    "duration_seconds": 0,
    "description": "Working on project proposal",
    "is_active": true,
    "created_at": "2025-10-06T12:00:00Z"
  }
}
```

**Errors**:
- 400: Already have active time entry
- 404: Task not found

---

### POST /time/stop
Stop the currently active time tracking.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "start_time": "2025-10-06T12:00:00Z",
    "end_time": "2025-10-06T14:30:00Z",
    "duration_seconds": 9000,
    "duration_hours": 2.5,
    "description": "Working on project proposal",
    "is_active": false
  }
}
```

**Errors**:
- 400: No active time entry

---

### POST /time/pause
Pause (same as stop but can be resumed).

**Headers**: `Authorization: Bearer <token>`

**Response** (200): Same as stop

---

### GET /time/active
Get the currently active time entry if any.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "success": true,
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_title": "Complete project proposal",
    "start_time": "2025-10-06T12:00:00Z",
    "duration_seconds": 1800,
    "description": "Working on project proposal",
    "is_active": true
  }
}
```

**Response when no active entry** (200):
```json
{
  "success": true,
  "data": null
}
```

---

### GET /time/entries
List time entries with filtering and pagination.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `page` (int, default: 1)
- `per_page` (int, default: 20, max: 100)
- `task_id` (UUID, optional): Filter by task
- `start_date` (ISO date, optional): Entries starting on or after
- `end_date` (ISO date, optional): Entries starting on or before
- `sort_by` (string, default: start_time): Sort field
- `sort_order` (string, default: desc): asc or desc

**Response** (200):
```json
{
  "success": true,
  "data": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_title": "Complete project proposal",
      "start_time": "2025-10-06T12:00:00Z",
      "end_time": "2025-10-06T14:30:00Z",
      "duration_seconds": 9000,
      "duration_hours": 2.5,
      "description": "Working on project proposal",
      "is_active": false,
      "created_at": "2025-10-06T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8
  }
}
```

---

### POST /time/entries
Create a manual time entry (for past work).

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "start_time": "2025-10-05T10:00:00Z",
  "end_time": "2025-10-05T12:30:00Z",
  "description": "Worked on budget section"
}
```

**Validation Rules**:
- `start_time`: Required, ISO datetime
- `end_time`: Required, ISO datetime, must be after start_time
- `task_id`: Optional, valid UUID
- `description`: Optional, max 500 chars

**Response** (201):
```json
{
  "success": true,
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "start_time": "2025-10-05T10:00:00Z",
    "end_time": "2025-10-05T12:30:00Z",
    "duration_seconds": 9000,
    "duration_hours": 2.5,
    "description": "Worked on budget section",
    "is_active": false
  }
}
```

---

### PUT /time/entries/{entry_id}
Update an existing time entry.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "start_time": "2025-10-05T10:00:00Z",
  "end_time": "2025-10-05T13:00:00Z",
  "description": "Worked on budget and timeline sections"
}
```

**Response** (200): Same format as create

**Errors**:
- 404: Entry not found
- 403: Entry belongs to another user
- 400: Cannot update active entry

---

### DELETE /time/entries/{entry_id}
Delete a time entry.

**Headers**: `Authorization: Bearer <token>`

**Response** (204): No content

---

## Analytics Service

### GET /analytics/dashboard
Get dashboard metrics for specified date range.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `start_date` (ISO date, required): Start of date range
- `end_date` (ISO date, required): End of date range

**Response** (200):
```json
{
  "success": true,
  "data": {
    "date_range": {
      "start": "2025-10-01",
      "end": "2025-10-06"
    },
    "total_tasks_completed": 12,
    "total_tasks_in_progress": 5,
    "total_tasks_todo": 8,
    "total_time_tracked_hours": 45.5,
    "average_task_completion_time_hours": 3.79,
    "tasks_completed_on_time": 10,
    "tasks_completed_late": 2,
    "productivity_score": 85.5,
    "daily_breakdown": [
      {
        "date": "2025-10-01",
        "tasks_completed": 2,
        "time_tracked_hours": 8.0
      }
    ]
  }
}
```

---

### GET /analytics/productivity
Get productivity trends over time.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `period` (string, default: week): day, week, month, year
- `start_date` (ISO date, required)
- `end_date` (ISO date, required)

**Response** (200):
```json
{
  "success": true,
  "data": {
    "period": "week",
    "trends": [
      {
        "period_start": "2025-09-30",
        "period_end": "2025-10-06",
        "tasks_completed": 12,
        "time_tracked_hours": 45.5,
        "productivity_score": 85.5,
        "comparison_previous_period": {
          "tasks_completed_change": 20.0,
          "time_tracked_change": 15.5,
          "score_change": 5.2
        }
      }
    ]
  }
}
```

---

### GET /analytics/tasks
Get task completion statistics.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `start_date` (ISO date, required)
- `end_date` (ISO date, required)
- `group_by` (string, default: status): status, priority, tag

**Response** (200):
```json
{
  "success": true,
  "data": {
    "total_tasks": 25,
    "by_status": {
      "todo": 8,
      "in_progress": 5,
      "done": 12,
      "archived": 0
    },
    "by_priority": {
      "low": 5,
      "medium": 12,
      "high": 6,
      "urgent": 2
    },
    "completion_rate": 48.0,
    "on_time_completion_rate": 83.3
  }
}
```

---

### GET /analytics/time-distribution
Get time distribution across tasks, tags, and priorities.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `start_date` (ISO date, required)
- `end_date` (ISO date, required)
- `group_by` (string, default: task): task, tag, priority, day, hour

**Response** (200):
```json
{
  "success": true,
  "data": {
    "total_hours": 45.5,
    "distribution": [
      {
        "group": "Complete project proposal",
        "hours": 12.5,
        "percentage": 27.5
      },
      {
        "group": "Review code changes",
        "hours": 8.0,
        "percentage": 17.6
      }
    ],
    "top_productive_hours": [9, 10, 14, 15, 16]
  }
}
```

---

### GET /analytics/export
Export analytics data in various formats.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `format` (string, required): csv, pdf, json
- `report_type` (string, required): tasks, time_entries, productivity, full
- `start_date` (ISO date, required)
- `end_date` (ISO date, required)

**Response** (200):
- Content-Type: application/csv, application/pdf, or application/json
- Content-Disposition: attachment; filename="report_2025-10-06.csv"

---

## Rate Limiting

All endpoints are rate-limited per user:
- **Authentication endpoints**: 5 requests per minute
- **Read endpoints (GET)**: 100 requests per minute
- **Write endpoints (POST, PUT, PATCH, DELETE)**: 50 requests per minute

Rate limit headers included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1696598400
```

## Webhook Support (Future Enhancement)

```
POST /webhooks/subscribe
GET /webhooks
DELETE /webhooks/{webhook_id}
```

## Versioning

API versions are included in the URL path: `/api/v1/...`

Breaking changes will result in a new version (v2, v3, etc.).

Non-breaking changes (new optional fields, new endpoints) will be added to existing versions.

## Support

For API support, contact: api-support@timetracker.com

API documentation (interactive): https://api.timetracker.com/docs
