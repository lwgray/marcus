# Todo Management API Specification

## Overview

This document provides the complete API specification for the Todo Management application integrated with Marcus. The API follows RESTful principles and provides comprehensive CRUD operations for todo items.

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://api.marcus-todos.com/v1
```

## Authentication

All API requests require authentication using JWT tokens or API keys.

### Headers
```http
Authorization: Bearer <jwt-token>
# OR
X-API-Key: <api-key>
```

## Common Response Format

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "TODO_NOT_FOUND",
    "message": "The requested todo item was not found",
    "details": {
      "todo_id": "123e4567-e89b-12d3-a456-426614174000"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

## Endpoints

### 1. Create Todo

Create a new todo item.

**Endpoint:** `POST /todos`

**Request Body:**
```json
{
  "title": "Complete project documentation",
  "description": "Write comprehensive documentation for the new feature",
  "priority": "high",
  "due_date": "2024-12-31T23:59:59Z",
  "category_ids": ["cat_123", "cat_456"],
  "tags": ["documentation", "urgent"]
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": "todo_789",
    "title": "Complete project documentation",
    "description": "Write comprehensive documentation for the new feature",
    "status": "pending",
    "priority": "high",
    "due_date": "2024-12-31T23:59:59Z",
    "completed_at": null,
    "category_ids": ["cat_123", "cat_456"],
    "tags": ["documentation", "urgent"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "created_by": "user_123"
  }
}
```

**Validation Rules:**
- `title`: Required, 1-500 characters
- `description`: Optional, max 5000 characters
- `priority`: Optional, one of: `low`, `medium`, `high`, `urgent`
- `due_date`: Optional, must be future date
- `category_ids`: Optional, array of valid category IDs
- `tags`: Optional, array of strings, max 10 tags

### 2. List Todos

Retrieve a paginated list of todos with filtering and sorting options.

**Endpoint:** `GET /todos`

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `per_page` (integer): Items per page (default: 20, max: 100)
- `status` (string): Filter by status: `pending`, `in_progress`, `completed`, `cancelled`
- `priority` (string): Filter by priority: `low`, `medium`, `high`, `urgent`
- `category_id` (string): Filter by category ID
- `tag` (string): Filter by tag (can be repeated)
- `search` (string): Search in title and description
- `due_before` (datetime): Filter todos due before this date
- `due_after` (datetime): Filter todos due after this date
- `sort_by` (string): Sort field: `created_at`, `updated_at`, `due_date`, `priority`
- `sort_order` (string): Sort order: `asc`, `desc` (default: `desc`)

**Example Request:**
```
GET /todos?status=pending&priority=high&sort_by=due_date&sort_order=asc
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "todo_789",
        "title": "Complete project documentation",
        "description": "Write comprehensive documentation",
        "status": "pending",
        "priority": "high",
        "due_date": "2024-12-31T23:59:59Z",
        "completed_at": null,
        "category_ids": ["cat_123"],
        "tags": ["documentation"],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ],
    "pagination": {
      "total": 42,
      "page": 1,
      "per_page": 20,
      "total_pages": 3,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 3. Get Todo Details

Retrieve detailed information about a specific todo.

**Endpoint:** `GET /todos/{todo_id}`

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "todo_789",
    "title": "Complete project documentation",
    "description": "Write comprehensive documentation for the new feature",
    "status": "pending",
    "priority": "high",
    "due_date": "2024-12-31T23:59:59Z",
    "completed_at": null,
    "category_ids": ["cat_123", "cat_456"],
    "categories": [
      {
        "id": "cat_123",
        "name": "Work",
        "color": "#FF5733"
      },
      {
        "id": "cat_456",
        "name": "Projects",
        "color": "#33FF57"
      }
    ],
    "tags": ["documentation", "urgent"],
    "attachments": [],
    "comments": [],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "created_by": {
      "id": "user_123",
      "name": "John Doe",
      "email": "john@example.com"
    }
  }
}
```

### 4. Update Todo

Update an existing todo item.

**Endpoint:** `PATCH /todos/{todo_id}`

**Request Body:**
```json
{
  "title": "Complete project documentation (Updated)",
  "status": "in_progress",
  "priority": "urgent",
  "due_date": "2024-12-25T23:59:59Z"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "todo_789",
    "title": "Complete project documentation (Updated)",
    "description": "Write comprehensive documentation for the new feature",
    "status": "in_progress",
    "priority": "urgent",
    "due_date": "2024-12-25T23:59:59Z",
    "completed_at": null,
    "category_ids": ["cat_123", "cat_456"],
    "tags": ["documentation", "urgent"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T14:30:00Z"
  }
}
```

### 5. Delete Todo

Delete a todo item (soft delete).

**Endpoint:** `DELETE /todos/{todo_id}`

**Response:** `204 No Content`

### 6. Complete Todo

Mark a todo as completed.

**Endpoint:** `POST /todos/{todo_id}/complete`

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "todo_789",
    "title": "Complete project documentation",
    "status": "completed",
    "completed_at": "2024-01-15T14:30:00Z",
    "updated_at": "2024-01-15T14:30:00Z"
  }
}
```

### 7. Bulk Operations

#### Bulk Update
Update multiple todos at once.

**Endpoint:** `POST /todos/bulk/update`

**Request Body:**
```json
{
  "todo_ids": ["todo_123", "todo_456", "todo_789"],
  "updates": {
    "status": "completed",
    "priority": "low"
  }
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "updated": 3,
    "failed": 0,
    "results": [
      {"id": "todo_123", "success": true},
      {"id": "todo_456", "success": true},
      {"id": "todo_789", "success": true}
    ]
  }
}
```

#### Bulk Delete
Delete multiple todos at once.

**Endpoint:** `POST /todos/bulk/delete`

**Request Body:**
```json
{
  "todo_ids": ["todo_123", "todo_456", "todo_789"]
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "deleted": 3,
    "failed": 0
  }
}
```

### 8. Categories

#### List Categories
**Endpoint:** `GET /categories`

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "cat_123",
        "name": "Work",
        "color": "#FF5733",
        "todo_count": 15
      }
    ]
  }
}
```

#### Create Category
**Endpoint:** `POST /categories`

**Request Body:**
```json
{
  "name": "Personal",
  "color": "#3357FF"
}
```

### 9. Statistics

Get todo statistics for the current user.

**Endpoint:** `GET /todos/stats`

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "total_todos": 42,
    "by_status": {
      "pending": 20,
      "in_progress": 10,
      "completed": 10,
      "cancelled": 2
    },
    "by_priority": {
      "low": 5,
      "medium": 20,
      "high": 15,
      "urgent": 2
    },
    "completion_rate": 0.238,
    "overdue_count": 3,
    "due_today": 2,
    "due_this_week": 8
  }
}
```

### 10. Marcus Integration

#### Convert to Marcus Task

Convert a todo into a Marcus task.

**Endpoint:** `POST /todos/{todo_id}/convert-to-task`

**Request Body:**
```json
{
  "project_id": "proj_123",
  "assign_to_agent": true,
  "priority_mapping": {
    "urgent": "high",
    "high": "medium",
    "medium": "low",
    "low": "low"
  }
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "todo_id": "todo_789",
    "marcus_task_id": "task_456",
    "project_id": "proj_123",
    "status": "converted"
  }
}
```

#### Sync with Marcus

Sync todo status with Marcus task status.

**Endpoint:** `POST /todos/{todo_id}/sync-marcus`

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "todo_status": "in_progress",
    "marcus_task_status": "in_progress",
    "last_synced": "2024-01-15T14:30:00Z"
  }
}
```

## WebSocket Events

Connect to receive real-time updates for todos.

**Endpoint:** `ws://localhost:8000/ws/todos`

### Event Types

#### Todo Created
```json
{
  "type": "todo.created",
  "data": {
    "id": "todo_789",
    "title": "New todo item",
    "created_by": "user_123"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Todo Updated
```json
{
  "type": "todo.updated",
  "data": {
    "id": "todo_789",
    "changes": {
      "status": "in_progress",
      "priority": "high"
    },
    "updated_by": "user_123"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Todo Deleted
```json
{
  "type": "todo.deleted",
  "data": {
    "id": "todo_789",
    "deleted_by": "user_123"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_REQUEST` | Invalid request format | 400 |
| `UNAUTHORIZED` | Missing or invalid authentication | 401 |
| `FORBIDDEN` | Access denied to resource | 403 |
| `TODO_NOT_FOUND` | Todo item not found | 404 |
| `CATEGORY_NOT_FOUND` | Category not found | 404 |
| `VALIDATION_ERROR` | Request validation failed | 422 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |
| `INTERNAL_ERROR` | Internal server error | 500 |

## Rate Limiting

- **Default limit:** 1000 requests per hour per user
- **Bulk operations:** 100 requests per hour
- **WebSocket connections:** 10 concurrent connections per user

Headers returned:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642255200
```

## Versioning

The API uses URL versioning. The current version is `v1`. When breaking changes are introduced, a new version will be created.

Example:
- Current: `https://api.marcus-todos.com/v1/todos`
- Future: `https://api.marcus-todos.com/v2/todos`

## SDK Examples

### JavaScript/TypeScript
```typescript
import { TodoClient } from '@marcus/todo-sdk';

const client = new TodoClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.marcus-todos.com/v1'
});

// Create a todo
const todo = await client.todos.create({
  title: 'Complete documentation',
  priority: 'high',
  dueDate: new Date('2024-12-31')
});

// List todos
const todos = await client.todos.list({
  status: 'pending',
  priority: 'high'
});

// Update todo
await client.todos.update(todo.id, {
  status: 'in_progress'
});
```

### Python
```python
from marcus_todo import TodoClient

client = TodoClient(
    api_key='your-api-key',
    base_url='https://api.marcus-todos.com/v1'
)

# Create a todo
todo = client.todos.create(
    title='Complete documentation',
    priority='high',
    due_date='2024-12-31T23:59:59Z'
)

# List todos
todos = client.todos.list(
    status='pending',
    priority='high'
)

# Update todo
client.todos.update(
    todo_id=todo.id,
    status='in_progress'
)
```
