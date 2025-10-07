# TODO CRUD API Contracts

## Version: 1.0.0
## Author: Backend Agent 2
## Date: 2025-10-07

---

## Table of Contents
1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Request/Response Examples](#requestresponse-examples)
4. [Error Scenarios](#error-scenarios)
5. [Validation Rules](#validation-rules)
6. [Testing Guide](#testing-guide)

---

## Overview

This document defines the exact API contracts for TODO CRUD operations, including request/response formats, validation rules, and error scenarios.

### Base URL
```
/api/v1
```

### Authentication
All endpoints require JWT authentication via Bearer token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### Content Type
All requests and responses use JSON:
```
Content-Type: application/json
```

---

## API Endpoints

### 1. Create Todo

**Endpoint:** `POST /api/v1/todos`

**Description:** Create a new todo for the authenticated user.

**Authentication:** Required

**Request Body:**
```json
{
  "title": "string (required, 1-200 chars)",
  "description": "string (optional, max 2000 chars)",
  "status": "pending | in_progress | completed (default: pending)",
  "priority": "low | medium | high | urgent (default: medium)",
  "due_date": "ISO 8601 datetime (optional)",
  "tags": ["string", "string", ...] (optional, default: [])
}
```

**Success Response:**
- **Status:** 201 Created
- **Body:**
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string | null",
  "status": "pending | in_progress | completed",
  "priority": "low | medium | high | urgent",
  "due_date": "ISO 8601 datetime | null",
  "completed_at": "ISO 8601 datetime | null",
  "owner_id": "uuid",
  "assigned_to_id": "uuid | null",
  "position": "integer",
  "tags": ["string", ...],
  "created_at": "ISO 8601 datetime",
  "updated_at": "ISO 8601 datetime"
}
```

**Error Responses:**
- **400 Bad Request:** Invalid input
- **401 Unauthorized:** Missing or invalid token
- **422 Unprocessable Entity:** Validation errors

---

### 2. List Todos

**Endpoint:** `GET /api/v1/todos`

**Description:** List todos with filtering, sorting, and pagination.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| status | string | No | - | Filter by status (pending, in_progress, completed) |
| priority | string | No | - | Filter by priority (low, medium, high, urgent) |
| tag | string | No | - | Filter by tag name |
| search | string | No | - | Search in title and description |
| sort_by | string | No | created_at | Field to sort by (created_at, due_date, priority, title, updated_at) |
| sort_order | string | No | desc | Sort order (asc, desc) |
| page | integer | No | 1 | Page number (min: 1) |
| page_size | integer | No | 20 | Items per page (min: 1, max: 100) |

**Success Response:**
- **Status:** 200 OK
- **Body:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "string",
      "description": "string | null",
      "status": "pending | in_progress | completed",
      "priority": "low | medium | high | urgent",
      "due_date": "ISO 8601 datetime | null",
      "completed_at": "ISO 8601 datetime | null",
      "owner_id": "uuid",
      "assigned_to_id": "uuid | null",
      "position": "integer",
      "tags": ["string", ...],
      "created_at": "ISO 8601 datetime",
      "updated_at": "ISO 8601 datetime"
    }
  ],
  "total": "integer",
  "page": "integer",
  "page_size": "integer",
  "pages": "integer"
}
```

**Error Responses:**
- **400 Bad Request:** Invalid query parameters
- **401 Unauthorized:** Missing or invalid token

---

### 3. Get Todo by ID

**Endpoint:** `GET /api/v1/todos/{todo_id}`

**Description:** Get a specific todo by ID.

**Authentication:** Required

**Path Parameters:**
- `todo_id` (UUID, required): ID of the todo to retrieve

**Success Response:**
- **Status:** 200 OK
- **Body:**
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string | null",
  "status": "pending | in_progress | completed",
  "priority": "low | medium | high | urgent",
  "due_date": "ISO 8601 datetime | null",
  "completed_at": "ISO 8601 datetime | null",
  "owner_id": "uuid",
  "assigned_to_id": "uuid | null",
  "position": "integer",
  "tags": ["string", ...],
  "created_at": "ISO 8601 datetime",
  "updated_at": "ISO 8601 datetime"
}
```

**Error Responses:**
- **401 Unauthorized:** Missing or invalid token
- **403 Forbidden:** User doesn't have access to this todo
- **404 Not Found:** Todo not found

---

### 4. Update Todo

**Endpoint:** `PATCH /api/v1/todos/{todo_id}`

**Description:** Update a todo. Only the owner can update.

**Authentication:** Required

**Path Parameters:**
- `todo_id` (UUID, required): ID of the todo to update

**Request Body (all fields optional):**
```json
{
  "title": "string (1-200 chars)",
  "description": "string (max 2000 chars)",
  "status": "pending | in_progress | completed",
  "priority": "low | medium | high | urgent",
  "due_date": "ISO 8601 datetime | null",
  "tags": ["string", ...]
}
```

**Success Response:**
- **Status:** 200 OK
- **Body:** Updated todo object (same structure as create response)

**Business Rules:**
- When status is changed to "completed", `completed_at` is automatically set to current timestamp
- When status is changed from "completed" to another status, `completed_at` is set to null
- Tags are replaced entirely (not merged) if included in the update

**Error Responses:**
- **400 Bad Request:** Invalid input
- **401 Unauthorized:** Missing or invalid token
- **403 Forbidden:** User is not the owner
- **404 Not Found:** Todo not found
- **422 Unprocessable Entity:** Validation errors

---

### 5. Delete Todo

**Endpoint:** `DELETE /api/v1/todos/{todo_id}`

**Description:** Delete a todo. Only the owner can delete.

**Authentication:** Required

**Path Parameters:**
- `todo_id` (UUID, required): ID of the todo to delete

**Success Response:**
- **Status:** 204 No Content
- **Body:** Empty

**Error Responses:**
- **401 Unauthorized:** Missing or invalid token
- **403 Forbidden:** User is not the owner
- **404 Not Found:** Todo not found

---

### 6. Bulk Update Todos

**Endpoint:** `PATCH /api/v1/todos/bulk`

**Description:** Update multiple todos at once. User must own all specified todos.

**Authentication:** Required

**Request Body:**
```json
{
  "todo_ids": ["uuid", "uuid", ...],
  "updates": {
    "status": "pending | in_progress | completed",
    "priority": "low | medium | high | urgent",
    "tags": ["string", ...]
  }
}
```

**Success Response:**
- **Status:** 200 OK
- **Body:**
```json
{
  "updated_count": "integer",
  "todos": [
    {
      "id": "uuid",
      "title": "string",
      ...
    }
  ]
}
```

**Error Responses:**
- **400 Bad Request:** Invalid input or empty todo_ids
- **401 Unauthorized:** Missing or invalid token
- **403 Forbidden:** User doesn't own all specified todos

---

### 7. Reorder Todos

**Endpoint:** `POST /api/v1/todos/reorder`

**Description:** Reorder todos by updating their position. User must own all specified todos.

**Authentication:** Required

**Request Body:**
```json
{
  "todo_ids": ["uuid", "uuid", "uuid", ...]
}
```

**Success Response:**
- **Status:** 200 OK
- **Body:**
```json
{
  "message": "Todos reordered successfully"
}
```

**Business Rules:**
- The order of UUIDs in the array determines the new order
- Position values are automatically assigned (0, 1, 2, ...)

**Error Responses:**
- **400 Bad Request:** Empty todo_ids array
- **401 Unauthorized:** Missing or invalid token
- **403 Forbidden:** User doesn't own all specified todos

---

## Request/Response Examples

### Example 1: Create a Simple Todo

**Request:**
```bash
POST /api/v1/todos HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "Buy groceries",
  "priority": "high"
}
```

**Response:**
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Buy groceries",
  "description": null,
  "status": "pending",
  "priority": "high",
  "due_date": null,
  "completed_at": null,
  "owner_id": "123e4567-e89b-12d3-a456-426614174000",
  "assigned_to_id": null,
  "position": 0,
  "tags": [],
  "created_at": "2025-10-07T10:30:00Z",
  "updated_at": "2025-10-07T10:30:00Z"
}
```

---

### Example 2: Create a Todo with Tags and Due Date

**Request:**
```bash
POST /api/v1/todos HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "Complete API design document",
  "description": "Design RESTful API for todo application with CRUD operations",
  "status": "in_progress",
  "priority": "urgent",
  "due_date": "2025-10-10T17:00:00Z",
  "tags": ["work", "api", "backend"]
}
```

**Response:**
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "660e9511-f39c-52e5-b827-557766551111",
  "title": "Complete API design document",
  "description": "Design RESTful API for todo application with CRUD operations",
  "status": "in_progress",
  "priority": "urgent",
  "due_date": "2025-10-10T17:00:00Z",
  "completed_at": null,
  "owner_id": "123e4567-e89b-12d3-a456-426614174000",
  "assigned_to_id": null,
  "position": 0,
  "tags": ["work", "api", "backend"],
  "created_at": "2025-10-07T10:35:00Z",
  "updated_at": "2025-10-07T10:35:00Z"
}
```

---

### Example 3: List Todos with Filters

**Request:**
```bash
GET /api/v1/todos?status=in_progress&priority=high&sort_by=due_date&sort_order=asc&page=1&page_size=10 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "items": [
    {
      "id": "660e9511-f39c-52e5-b827-557766551111",
      "title": "Complete API design document",
      "description": "Design RESTful API for todo application",
      "status": "in_progress",
      "priority": "high",
      "due_date": "2025-10-09T17:00:00Z",
      "completed_at": null,
      "owner_id": "123e4567-e89b-12d3-a456-426614174000",
      "assigned_to_id": null,
      "position": 1,
      "tags": ["work", "api"],
      "created_at": "2025-10-07T10:35:00Z",
      "updated_at": "2025-10-07T11:00:00Z"
    },
    {
      "id": "770f0622-g40d-63f6-c938-668877662222",
      "title": "Review pull request",
      "description": null,
      "status": "in_progress",
      "priority": "high",
      "due_date": "2025-10-10T12:00:00Z",
      "completed_at": null,
      "owner_id": "123e4567-e89b-12d3-a456-426614174000",
      "assigned_to_id": null,
      "position": 2,
      "tags": ["work"],
      "created_at": "2025-10-07T09:15:00Z",
      "updated_at": "2025-10-07T09:15:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 10,
  "pages": 1
}
```

---

### Example 4: Search Todos

**Request:**
```bash
GET /api/v1/todos?search=api&page=1&page_size=20 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "items": [
    {
      "id": "660e9511-f39c-52e5-b827-557766551111",
      "title": "Complete API design document",
      "description": "Design RESTful API for todo application",
      "status": "in_progress",
      "priority": "urgent",
      "due_date": "2025-10-10T17:00:00Z",
      "completed_at": null,
      "owner_id": "123e4567-e89b-12d3-a456-426614174000",
      "assigned_to_id": null,
      "position": 0,
      "tags": ["work", "api", "backend"],
      "created_at": "2025-10-07T10:35:00Z",
      "updated_at": "2025-10-07T10:35:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

---

### Example 5: Update Todo (Mark as Completed)

**Request:**
```bash
PATCH /api/v1/todos/660e9511-f39c-52e5-b827-557766551111 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "status": "completed"
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "660e9511-f39c-52e5-b827-557766551111",
  "title": "Complete API design document",
  "description": "Design RESTful API for todo application with CRUD operations",
  "status": "completed",
  "priority": "urgent",
  "due_date": "2025-10-10T17:00:00Z",
  "completed_at": "2025-10-07T14:25:30Z",
  "owner_id": "123e4567-e89b-12d3-a456-426614174000",
  "assigned_to_id": null,
  "position": 0,
  "tags": ["work", "api", "backend"],
  "created_at": "2025-10-07T10:35:00Z",
  "updated_at": "2025-10-07T14:25:30Z"
}
```

**Note:** `completed_at` was automatically set when status changed to "completed"

---

### Example 6: Update Todo (Change Multiple Fields)

**Request:**
```bash
PATCH /api/v1/todos/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "Buy groceries and cook dinner",
  "description": "Buy ingredients for pasta and make dinner by 7pm",
  "priority": "urgent",
  "due_date": "2025-10-07T19:00:00Z",
  "tags": ["personal", "urgent"]
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Buy groceries and cook dinner",
  "description": "Buy ingredients for pasta and make dinner by 7pm",
  "status": "pending",
  "priority": "urgent",
  "due_date": "2025-10-07T19:00:00Z",
  "completed_at": null,
  "owner_id": "123e4567-e89b-12d3-a456-426614174000",
  "assigned_to_id": null,
  "position": 0,
  "tags": ["personal", "urgent"],
  "created_at": "2025-10-07T10:30:00Z",
  "updated_at": "2025-10-07T14:30:00Z"
}
```

---

### Example 7: Delete Todo

**Request:**
```bash
DELETE /api/v1/todos/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```http
HTTP/1.1 204 No Content
```

---

### Example 8: Bulk Update Todos

**Request:**
```bash
PATCH /api/v1/todos/bulk HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "todo_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e9511-f39c-52e5-b827-557766551111",
    "770f0622-g40d-63f6-c938-668877662222"
  ],
  "updates": {
    "status": "completed",
    "tags": ["done"]
  }
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "updated_count": 3,
  "todos": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Buy groceries",
      "status": "completed",
      "completed_at": "2025-10-07T15:00:00Z",
      "tags": ["done"],
      ...
    },
    {
      "id": "660e9511-f39c-52e5-b827-557766551111",
      "title": "Complete API design document",
      "status": "completed",
      "completed_at": "2025-10-07T15:00:00Z",
      "tags": ["done"],
      ...
    },
    {
      "id": "770f0622-g40d-63f6-c938-668877662222",
      "title": "Review pull request",
      "status": "completed",
      "completed_at": "2025-10-07T15:00:00Z",
      "tags": ["done"],
      ...
    }
  ]
}
```

---

### Example 9: Reorder Todos

**Request:**
```bash
POST /api/v1/todos/reorder HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "todo_ids": [
    "770f0622-g40d-63f6-c938-668877662222",
    "550e8400-e29b-41d4-a716-446655440000",
    "660e9511-f39c-52e5-b827-557766551111"
  ]
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message": "Todos reordered successfully"
}
```

**Result:** The todos will have positions: 0, 1, 2 respectively

---

## Error Scenarios

### Error Response Format

All error responses follow this structure:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional context"
    },
    "timestamp": "ISO 8601 datetime",
    "request_id": "uuid"
  }
}
```

---

### 1. Validation Error (400 Bad Request)

**Scenario:** Title too long

**Request:**
```bash
POST /api/v1/todos HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "This is a very long title that exceeds the maximum allowed length of 200 characters and will cause a validation error because it's way too long for a todo title and should be rejected by the API validation layer which enforces the 200 character limit",
  "priority": "high"
}
```

**Response:**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "title": "String should have at most 200 characters"
    },
    "timestamp": "2025-10-07T15:30:00Z",
    "request_id": "abc123-def456-ghi789"
  }
}
```

---

### 2. Validation Error - Invalid Enum

**Scenario:** Invalid status value

**Request:**
```bash
POST /api/v1/todos HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "title": "Test todo",
  "status": "finished"
}
```

**Response:**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "status": "Input should be 'pending', 'in_progress' or 'completed'"
    },
    "timestamp": "2025-10-07T15:32:00Z",
    "request_id": "abc124-def457-ghi790"
  }
}
```

---

### 3. Authentication Error (401 Unauthorized)

**Scenario:** Missing or invalid token

**Request:**
```bash
GET /api/v1/todos HTTP/1.1
Host: api.example.com
```

**Response:**
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication credentials were not provided",
    "details": {},
    "timestamp": "2025-10-07T15:35:00Z",
    "request_id": "abc125-def458-ghi791"
  }
}
```

---

### 4. Authorization Error (403 Forbidden)

**Scenario:** User tries to update someone else's todo

**Request:**
```bash
PATCH /api/v1/todos/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "status": "completed"
}
```

**Response:**
```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": {
    "code": "UNAUTHORIZED_ACTION",
    "message": "You do not have permission to update this todo",
    "details": {
      "action": "update todo",
      "resource": "todo 550e8400-e29b-41d4-a716-446655440000"
    },
    "timestamp": "2025-10-07T15:40:00Z",
    "request_id": "abc126-def459-ghi792"
  }
}
```

---

### 5. Not Found Error (404 Not Found)

**Scenario:** Todo doesn't exist

**Request:**
```bash
GET /api/v1/todos/999e9999-e99b-99d9-a999-999999999999 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Todo not found",
    "details": {
      "resource_type": "Todo",
      "resource_id": "999e9999-e99b-99d9-a999-999999999999"
    },
    "timestamp": "2025-10-07T15:45:00Z",
    "request_id": "abc127-def460-ghi793"
  }
}
```

---

### 6. Bulk Update Authorization Error

**Scenario:** User doesn't own all specified todos

**Request:**
```bash
PATCH /api/v1/todos/bulk HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "todo_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "888e8888-e88b-88d8-a888-888888888888"
  ],
  "updates": {
    "status": "completed"
  }
}
```

**Response:**
```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": {
    "code": "UNAUTHORIZED_ACTION",
    "message": "You do not have permission to perform bulk update on specified todos",
    "details": {
      "action": "bulk update todos",
      "resource": "specified todos"
    },
    "timestamp": "2025-10-07T15:50:00Z",
    "request_id": "abc128-def461-ghi794"
  }
}
```

---

## Validation Rules

### Title Field
- **Required:** Yes
- **Type:** String
- **Min Length:** 1
- **Max Length:** 200
- **Allowed Characters:** Any UTF-8 characters
- **Trimming:** Leading/trailing whitespace should be trimmed

### Description Field
- **Required:** No
- **Type:** String or null
- **Max Length:** 2000
- **Allowed Characters:** Any UTF-8 characters including newlines

### Status Field
- **Required:** No (defaults to "pending")
- **Type:** Enum
- **Valid Values:** "pending", "in_progress", "completed"
- **Case Sensitive:** Yes (lowercase only)

### Priority Field
- **Required:** No (defaults to "medium")
- **Type:** Enum
- **Valid Values:** "low", "medium", "high", "urgent"
- **Case Sensitive:** Yes (lowercase only)

### Due Date Field
- **Required:** No
- **Type:** ISO 8601 datetime string or null
- **Format:** "YYYY-MM-DDTHH:MM:SSZ"
- **Timezone:** Must include timezone (Z for UTC or +/-HH:MM)
- **Validation:** Must be a valid datetime, no past date restriction

### Tags Field
- **Required:** No (defaults to empty array)
- **Type:** Array of strings
- **Item Min Length:** 1
- **Item Max Length:** 50
- **Max Array Length:** 20 tags per todo
- **Allowed Characters:** Alphanumeric, hyphen, underscore
- **Case:** Case-insensitive (stored as lowercase)
- **Duplicates:** Automatically deduplicated

### Query Parameters

**page:**
- **Type:** Integer
- **Min:** 1
- **Default:** 1

**page_size:**
- **Type:** Integer
- **Min:** 1
- **Max:** 100
- **Default:** 20

**sort_by:**
- **Type:** String
- **Valid Values:** "created_at", "due_date", "priority", "title", "updated_at"
- **Default:** "created_at"

**sort_order:**
- **Type:** String
- **Valid Values:** "asc", "desc"
- **Default:** "desc"

---

## Testing Guide

### Unit Test Checklist

**Todo Creation:**
- [ ] Create todo with only required fields
- [ ] Create todo with all fields
- [ ] Create todo with tags
- [ ] Create todo with invalid title (too long)
- [ ] Create todo with invalid status
- [ ] Create todo with invalid priority
- [ ] Verify owner_id is set correctly
- [ ] Verify default values (status, priority, position)

**Todo Listing:**
- [ ] List todos without filters
- [ ] List todos with status filter
- [ ] List todos with priority filter
- [ ] List todos with tag filter
- [ ] List todos with search query
- [ ] List todos with pagination
- [ ] List todos with sorting (asc/desc)
- [ ] Verify only user's todos are returned
- [ ] Verify pagination metadata is correct

**Todo Retrieval:**
- [ ] Get existing todo by ID
- [ ] Get non-existent todo (404)
- [ ] Get todo owned by another user (403)

**Todo Update:**
- [ ] Update single field
- [ ] Update multiple fields
- [ ] Update status to completed (verify completed_at)
- [ ] Update tags (verify replacement)
- [ ] Update non-existent todo (404)
- [ ] Update todo owned by another user (403)
- [ ] Update with invalid data (400)

**Todo Deletion:**
- [ ] Delete existing todo
- [ ] Delete non-existent todo (404)
- [ ] Delete todo owned by another user (403)
- [ ] Verify todo is removed from database
- [ ] Verify cascade deletion of todo_tags

**Bulk Operations:**
- [ ] Bulk update multiple todos
- [ ] Bulk update with partial ownership (403)
- [ ] Reorder todos
- [ ] Reorder with partial ownership (403)

**Edge Cases:**
- [ ] Empty string title (400)
- [ ] Title with only whitespace (400)
- [ ] Very long description (2000 chars)
- [ ] Description with newlines and special chars
- [ ] Due date in the past
- [ ] Due date far in the future
- [ ] Page size exceeding maximum (100)
- [ ] Negative page number
- [ ] Invalid UUID format

### Integration Test Checklist

**End-to-End Flows:**
- [ ] Create → Read → Update → Delete flow
- [ ] Create todo with tags → List with tag filter
- [ ] Create multiple todos → Bulk update → Verify
- [ ] Create todos → Reorder → Verify order
- [ ] Mark todo as completed → Verify completed_at

**Authentication:**
- [ ] Request without token (401)
- [ ] Request with expired token (401)
- [ ] Request with invalid token (401)

**Database Integrity:**
- [ ] Verify foreign key constraints
- [ ] Verify cascade deletion
- [ ] Verify unique constraints
- [ ] Verify check constraints (status, priority)

---

## Summary

This API contract document provides:

✅ **Complete Endpoint Specifications:** All 7 CRUD endpoints fully documented
✅ **Request/Response Examples:** Real-world examples for all operations
✅ **Error Scenarios:** Comprehensive error handling examples
✅ **Validation Rules:** Detailed validation for all fields
✅ **Testing Guide:** Complete test checklists for unit and integration tests

Developers can use this document to:
- Implement the API endpoints with exact specifications
- Write comprehensive tests
- Understand error handling requirements
- Validate their implementation against the contract
