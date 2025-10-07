# Usability Requirements Implementation

## Overview

This document defines the usability requirements for the Task Management & Calendar Integration Platform, ensuring an intuitive, easy-to-navigate interface with clear labels and a minimal learning curve.

## Table of Contents

1. [Usability Principles](#usability-principles)
2. [API Usability Standards](#api-usability-standards)
3. [Error Handling Guidelines](#error-handling-guidelines)
4. [User Interface Guidelines](#user-interface-guidelines)
5. [Validation and Feedback](#validation-and-feedback)
6. [Accessibility Requirements](#accessibility-requirements)
7. [User Onboarding](#user-onboarding)
8. [Implementation Checklist](#implementation-checklist)

---

## 1. Usability Principles

### Core Principles

**1.1 Clarity Over Brevity**
- Use descriptive names for all fields and endpoints
- Prefer self-documenting code and API responses
- Avoid abbreviations unless universally understood

**1.2 Consistency**
- Maintain consistent naming conventions across all interfaces
- Use the same patterns for similar operations
- Follow REST conventions strictly

**1.3 Forgiveness**
- Allow users to undo actions where possible
- Provide confirmation for destructive operations
- Auto-save work when appropriate

**1.4 Feedback**
- Provide immediate feedback for all user actions
- Use clear, actionable error messages
- Show progress indicators for long-running operations

**1.5 Simplicity**
- Minimize required fields (make everything optional that can be)
- Provide sensible defaults
- Progressive disclosure of advanced features

### Success Metrics

- **Time to First Task**: < 2 minutes from registration
- **Task Completion Rate**: > 90% for core workflows
- **Error Recovery Rate**: > 95% of users recover from errors without support
- **User Satisfaction**: > 4.5/5.0 rating
- **Learning Curve**: 80% of users productive within first session

---

## 2. API Usability Standards

### 2.1 Endpoint Naming

**✅ Good Examples:**
```
POST   /api/v1/tasks              # Create task
GET    /api/v1/tasks              # List tasks
GET    /api/v1/tasks/{id}         # Get specific task
PATCH  /api/v1/tasks/{id}         # Update task
DELETE /api/v1/tasks/{id}         # Delete task
```

**❌ Bad Examples:**
```
POST   /api/v1/create_task        # Redundant verb
GET    /api/v1/getTasks           # Not RESTful
POST   /api/v1/task/update        # Inconsistent
DELETE /api/v1/remove/{id}        # Unclear resource
```

### 2.2 Request Body Design

**Principle: Make Required Fields Obvious**

```json
{
  "title": "Complete documentation",         // Required, obvious
  "description": "Write user guide",         // Optional, clear purpose
  "priority": "HIGH",                        // Optional, enum with clear values
  "due_date": "2025-10-15T17:00:00Z",       // Optional, ISO 8601 standard
  "tags": ["documentation", "urgent"]        // Optional, intuitive array
}
```

**Field Naming Standards:**
- Use `snake_case` for JSON fields (consistent with Python backend)
- Use full words: `description` not `desc`, `priority` not `prio`
- Boolean fields: prefix with `is_` or `has_` (e.g., `is_completed`, `has_subtasks`)
- Dates: use `_at` suffix (e.g., `created_at`, `updated_at`, `completed_at`)
- IDs: use `_id` suffix (e.g., `user_id`, `task_id`, `project_id`)

### 2.3 Response Format Standards

**Successful Response (Single Resource):**
```json
{
  "id": "uuid-here",
  "title": "Complete documentation",
  "status": "TODO",
  "priority": "HIGH",
  "created_at": "2025-10-06T14:30:00Z",
  "updated_at": "2025-10-06T14:30:00Z",
  "_links": {
    "self": "/api/v1/tasks/uuid-here",
    "subtasks": "/api/v1/tasks/uuid-here/subtasks",
    "time_entries": "/api/v1/time/entries?task_id=uuid-here"
  }
}
```

**Successful Response (Collection):**
```json
{
  "items": [...],
  "total": 45,
  "page": 1,
  "limit": 20,
  "total_pages": 3,
  "_links": {
    "self": "/api/v1/tasks?page=1&limit=20",
    "next": "/api/v1/tasks?page=2&limit=20",
    "prev": null,
    "first": "/api/v1/tasks?page=1&limit=20",
    "last": "/api/v1/tasks?page=3&limit=20"
  }
}
```

**Benefits:**
- Pagination info is obvious
- Navigation links provided (HATEOAS)
- Total count helps UI show progress
- Consistent across all list endpoints

### 2.4 Query Parameter Standards

**Filtering:**
```
GET /api/v1/tasks?status=TODO&priority=HIGH&tags=urgent,documentation
```

**Sorting:**
```
GET /api/v1/tasks?sort=due_date&order=asc
GET /api/v1/tasks?sort=-priority  # Minus sign for descending
```

**Pagination:**
```
GET /api/v1/tasks?page=1&limit=20
```

**Date Ranges:**
```
GET /api/v1/tasks?due_after=2025-10-01&due_before=2025-10-31
GET /api/v1/time/entries?start_date=2025-10-01&end_date=2025-10-31
```

**Search:**
```
GET /api/v1/tasks?q=documentation
```

---

## 3. Error Handling Guidelines

### 3.1 Error Response Format

**Standard Error Response:**
```json
{
  "error": "ValidationError",
  "message": "Invalid task data provided",
  "details": {
    "title": ["Title is required and cannot be empty"],
    "due_date": ["Date must be in the future"],
    "priority": ["Must be one of: LOW, MEDIUM, HIGH, URGENT"]
  },
  "request_id": "req_abc123xyz",
  "timestamp": "2025-10-06T14:30:00Z",
  "documentation_url": "https://docs.example.com/errors/validation-error"
}
```

### 3.2 User-Friendly Error Messages

**❌ Bad Error Messages:**
```
"Error: 500"
"Invalid input"
"Database error"
"NoneType object has no attribute 'id'"
```

**✅ Good Error Messages:**
```
"Task title is required. Please provide a title for your task."
"The due date must be in the future. Please select a date after today."
"You've reached the maximum of 10,000 tasks. Please archive or delete some tasks to continue."
"This calendar is already connected to your account. Try connecting a different calendar."
```

### 3.3 HTTP Status Codes with Clear Meanings

| Code | Usage | Example Message |
|------|-------|-----------------|
| 200 | Success | "Task updated successfully" |
| 201 | Created | "Task created successfully" |
| 204 | Deleted/No Content | (No body) |
| 400 | Bad Request | "Invalid task data. Please check the required fields." |
| 401 | Unauthorized | "Please log in to access this resource." |
| 403 | Forbidden | "You don't have permission to delete this task." |
| 404 | Not Found | "Task not found. It may have been deleted." |
| 409 | Conflict | "A task with this title already exists in this project." |
| 422 | Unprocessable | "The due date cannot be earlier than the start date." |
| 429 | Rate Limited | "Too many requests. Please try again in 60 seconds." |
| 500 | Server Error | "Something went wrong on our end. Please try again or contact support." |

### 3.4 Validation Error Details

**Field-Level Validation:**
```json
{
  "error": "ValidationError",
  "message": "Please fix the following errors:",
  "details": {
    "title": [
      "Title is required",
      "Title must be at least 3 characters long",
      "Title cannot exceed 200 characters"
    ],
    "email": [
      "Please enter a valid email address (e.g., user@example.com)"
    ],
    "estimated_duration": [
      "Duration must be a positive number in minutes (e.g., 30, 60, 120)"
    ]
  }
}
```

### 3.5 Actionable Error Recovery

**Include Next Steps:**
```json
{
  "error": "CalendarSyncError",
  "message": "Unable to sync with Google Calendar",
  "details": {
    "reason": "Your access token has expired",
    "next_steps": [
      "Go to Settings > Calendar Connections",
      "Click 'Reconnect' next to your Google Calendar",
      "Authorize the app again"
    ],
    "alternative": "You can also manually create tasks from calendar events"
  },
  "support_url": "https://support.example.com/calendar-sync-issues"
}
```

---

## 4. User Interface Guidelines

### 4.1 Task Status Labels

**Clear, Action-Oriented Labels:**

| Internal Value | Display Label | Color | Icon |
|----------------|---------------|-------|------|
| TODO | To Do | Blue | ○ |
| IN_PROGRESS | In Progress | Yellow | ◑ |
| COMPLETED | Completed | Green | ● |
| CANCELLED | Cancelled | Gray | ✕ |

**In UI Forms:**
```html
<select name="status" aria-label="Task status">
  <option value="TODO">To Do - Task not started yet</option>
  <option value="IN_PROGRESS">In Progress - Currently working on this</option>
  <option value="COMPLETED">Completed - Task is finished</option>
  <option value="CANCELLED">Cancelled - Task is no longer needed</option>
</select>
```

### 4.2 Priority Labels

| Internal Value | Display Label | Color | Description |
|----------------|---------------|-------|-------------|
| LOW | Low Priority | Gray | No rush, can be done anytime |
| MEDIUM | Medium Priority | Blue | Normal priority, regular workflow |
| HIGH | High Priority | Orange | Important, should be done soon |
| URGENT | Urgent | Red | Critical, needs immediate attention |

### 4.3 Form Field Labels

**✅ Good Labels:**
```html
<label for="task-title">
  Task Title *
  <span class="help-text">A clear, concise name for your task</span>
</label>
<input id="task-title" name="title" required
       placeholder="e.g., Review project proposal">

<label for="due-date">
  Due Date (Optional)
  <span class="help-text">When does this task need to be completed?</span>
</label>
<input id="due-date" name="due_date" type="datetime-local">

<label for="estimated-duration">
  Estimated Time (Optional)
  <span class="help-text">How long do you think this will take?</span>
</label>
<input id="estimated-duration" name="estimated_duration"
       type="number" placeholder="Minutes (e.g., 30)">
```

**❌ Bad Labels:**
```html
<label>Title:</label>
<input name="t">

<label>DD</label>
<input name="dd" type="date">

<label>Est</label>
<input name="dur">
```

### 4.4 Empty States

**Provide Guidance When No Data:**

```
┌─────────────────────────────────────┐
│                                     │
│         📋  No Tasks Yet            │
│                                     │
│  Get started by creating your      │
│  first task!                       │
│                                     │
│  [+ Create Your First Task]        │
│                                     │
│  Or import tasks from your         │
│  calendar:                         │
│  [🗓️  Connect Calendar]            │
│                                     │
└─────────────────────────────────────┘
```

### 4.5 Loading States

**Show Progress for Long Operations:**

```
┌─────────────────────────────────────┐
│  Syncing with Google Calendar...   │
│  ████████████░░░░░░░░░░  60%       │
│                                     │
│  Fetched 45 of 75 events           │
│  Estimated time remaining: 10s     │
└─────────────────────────────────────┘
```

### 4.6 Success Confirmations

**Provide Clear Feedback:**

```
┌─────────────────────────────────────┐
│  ✓ Task Created Successfully!       │
│                                     │
│  "Complete documentation" has been  │
│  added to your task list.          │
│                                     │
│  [View Task]  [Create Another]     │
└─────────────────────────────────────┘
```

---

## 5. Validation and Feedback

### 5.1 Inline Validation

**Validate as User Types (with debouncing):**

```
Title: [Review project proposa_]
       ✓ Looks good!

Email: [user@invalid]
       ✗ Please enter a complete email address

Due Date: [2025-09-30]
          ⚠ This date is in the past. Did you mean 2026-09-30?
```

### 5.2 Required vs Optional Fields

**Visual Indicators:**
- Required fields: Mark with asterisk (*) and "Required" label
- Optional fields: Mark with "Optional" label
- Provide reasonable defaults for optional fields

```
Task Title *                    (Required)
[________________________]

Description (Optional)          (Clearly marked as optional)
[________________________]

Priority                        (Default: Medium)
[Medium ▼]
```

### 5.3 Smart Defaults

**Reduce User Effort:**

| Field | Smart Default | Reasoning |
|-------|---------------|-----------|
| Status | TODO | New tasks start as not started |
| Priority | MEDIUM | Most tasks are normal priority |
| Start Date | Now | Usually want to start immediately |
| Timezone | User's profile timezone | Personalized to user |
| Estimated Duration | None | Better to leave blank than guess wrong |

### 5.4 Input Constraints

**Guide Users to Valid Input:**

```html
<!-- Clear min/max for numbers -->
<input type="number" min="1" max="1440"
       placeholder="1-1440 minutes"
       aria-label="Estimated duration in minutes">

<!-- Appropriate input types -->
<input type="email" placeholder="user@example.com">
<input type="date" min="2025-10-06">
<input type="time" step="900"> <!-- 15-minute intervals -->

<!-- Character limits with counter -->
<textarea maxlength="200" id="title"></textarea>
<span aria-live="polite">180 characters remaining</span>
```

---

## 6. Accessibility Requirements

### 6.1 WCAG 2.1 Level AA Compliance

**Required Standards:**
- All interactive elements keyboard accessible
- Color contrast ratio ≥ 4.5:1 for normal text
- Color contrast ratio ≥ 3:1 for large text
- Never rely on color alone to convey information
- All images have alt text
- Forms have proper labels
- Error messages associated with form fields

### 6.2 Semantic HTML

```html
<!-- ✅ Good: Semantic Structure -->
<main>
  <h1>My Tasks</h1>
  <nav aria-label="Task filters">
    <button aria-pressed="true">All</button>
    <button aria-pressed="false">To Do</button>
  </nav>

  <article aria-labelledby="task-1-title">
    <h2 id="task-1-title">Complete documentation</h2>
    <p>Due: <time datetime="2025-10-15">October 15, 2025</time></p>
  </article>
</main>

<!-- ❌ Bad: Div Soup -->
<div class="container">
  <div class="title">My Tasks</div>
  <div class="nav">
    <div class="button active">All</div>
  </div>
  <div class="task">
    <div class="task-title">Complete documentation</div>
  </div>
</div>
```

### 6.3 Screen Reader Support

**ARIA Labels and Descriptions:**

```html
<button aria-label="Delete task"
        aria-describedby="delete-help">
  🗑️
</button>
<span id="delete-help" class="sr-only">
  This action cannot be undone
</span>

<input type="checkbox"
       id="task-1"
       aria-label="Mark 'Complete documentation' as complete">

<div role="status" aria-live="polite">
  Task saved successfully
</div>
```

### 6.4 Keyboard Navigation

**Required Keyboard Shortcuts:**

| Key | Action |
|-----|--------|
| Tab | Navigate to next element |
| Shift + Tab | Navigate to previous element |
| Enter | Activate button/link |
| Space | Toggle checkbox |
| Esc | Close modal/cancel action |
| Arrow Keys | Navigate lists/dropdowns |
| / | Focus search box (common pattern) |
| n | New task (with modifier) |

**Focus Indicators:**
```css
*:focus {
  outline: 2px solid #3B82F6;
  outline-offset: 2px;
}

/* Never remove focus outline without replacement */
```

---

## 7. User Onboarding

### 7.1 First-Time User Experience

**Step 1: Welcome Screen**
```
┌─────────────────────────────────────┐
│  Welcome to TaskFlow! 👋            │
│                                     │
│  Let's get you started in 3 steps: │
│                                     │
│  1. Create your first task         │
│  2. Connect your calendar          │
│  3. Start tracking your time       │
│                                     │
│  [Get Started]  [Skip Tutorial]    │
└─────────────────────────────────────┘
```

**Step 2: Interactive Tutorial**
```
┌─────────────────────────────────────┐
│  🎯 Create Your First Task          │
│                                     │
│  Task Title * [_________________]  │
│               ↑                     │
│  Start by giving your task a name  │
│                                     │
│  [Next: Add Details]               │
│  Step 1 of 5                       │
└─────────────────────────────────────┘
```

### 7.2 Contextual Help

**Tooltips for Features:**
```html
<button class="help-icon"
        aria-label="Help about recurring tasks"
        data-tooltip="Set up tasks that repeat daily, weekly, or monthly">
  ?
</button>
```

**In-App Documentation Links:**
```
Can't find what you're looking for?
• [📖 User Guide](link)
• [🎥 Video Tutorials](link)
• [💬 Get Support](link)
```

### 7.3 Progressive Disclosure

**Show Advanced Features Gradually:**

```
Basic Task Creation (Default View):
┌─────────────────────────────┐
│ Title: [_______________]    │
│ Due Date: [___________]     │
│ Priority: [Medium ▼]        │
│                             │
│ [+ Show More Options]       │
└─────────────────────────────┘

Expanded View (After clicking):
┌─────────────────────────────┐
│ Title: [_______________]    │
│ Description: [_________]    │
│ Due Date: [___________]     │
│ Start Date: [_________]     │
│ Priority: [Medium ▼]        │
│ Project: [Select ▼]         │
│ Tags: [____________]        │
│ Recurrence: [None ▼]        │
│ Estimated Time: [____]      │
│                             │
│ [- Show Fewer Options]      │
└─────────────────────────────┘
```

---

## 8. Implementation Checklist

### 8.1 Backend Implementation

- [ ] **Error Response Standardization**
  - [ ] Implement consistent error response format
  - [ ] Create error handler middleware
  - [ ] Add request IDs to all responses
  - [ ] Include documentation URLs in errors

- [ ] **Validation Layer**
  - [ ] Use Pydantic models for all request validation
  - [ ] Provide field-specific error messages
  - [ ] Implement custom validators for business logic
  - [ ] Return all validation errors at once (not one at a time)

- [ ] **Response Formatting**
  - [ ] Add pagination links to all list endpoints
  - [ ] Include HATEOAS links in responses
  - [ ] Implement consistent date/time formatting (ISO 8601)
  - [ ] Add metadata to responses (request_id, timestamp)

- [ ] **API Documentation**
  - [ ] Generate OpenAPI/Swagger docs
  - [ ] Add request/response examples for all endpoints
  - [ ] Document all error codes and meanings
  - [ ] Provide code samples in multiple languages

### 8.2 Frontend Implementation

- [ ] **Form Design**
  - [ ] Mark required fields with asterisks
  - [ ] Show character counters for text inputs
  - [ ] Implement inline validation
  - [ ] Provide helpful placeholder text

- [ ] **Error Display**
  - [ ] Show field-level errors inline
  - [ ] Display summary errors at top of form
  - [ ] Use appropriate icons and colors
  - [ ] Provide actionable error recovery steps

- [ ] **Loading States**
  - [ ] Show spinners for async operations
  - [ ] Display progress bars for long operations
  - [ ] Disable buttons during submission
  - [ ] Show skeleton screens for data loading

- [ ] **Success Feedback**
  - [ ] Toast notifications for quick actions
  - [ ] Success pages for complex operations
  - [ ] Confirmation dialogs for destructive actions
  - [ ] Undo capability where possible

- [ ] **Empty States**
  - [ ] Design empty states for all list views
  - [ ] Provide quick actions in empty states
  - [ ] Show helpful tips for new users

- [ ] **Accessibility**
  - [ ] All forms have proper labels
  - [ ] Keyboard navigation works everywhere
  - [ ] Screen reader announcements for dynamic content
  - [ ] ARIA attributes for complex widgets
  - [ ] Color contrast meets WCAG AA

### 8.3 User Onboarding

- [ ] **Welcome Flow**
  - [ ] Create welcome screen
  - [ ] Build interactive tutorial
  - [ ] Add skip tutorial option
  - [ ] Track tutorial completion

- [ ] **Contextual Help**
  - [ ] Add tooltips for all major features
  - [ ] Create in-app help center
  - [ ] Link to video tutorials
  - [ ] Provide live chat support

- [ ] **Progressive Disclosure**
  - [ ] Implement show/hide for advanced options
  - [ ] Create beginner/advanced modes
  - [ ] Add feature discovery prompts

### 8.4 Testing

- [ ] **Usability Testing**
  - [ ] Test with 5+ first-time users
  - [ ] Measure time to complete common tasks
  - [ ] Track error rates and recovery
  - [ ] Collect qualitative feedback

- [ ] **Accessibility Testing**
  - [ ] Test with screen readers (NVDA, JAWS, VoiceOver)
  - [ ] Verify keyboard-only navigation
  - [ ] Run automated accessibility audits (axe, Lighthouse)
  - [ ] Test with high contrast mode

- [ ] **Cross-Browser Testing**
  - [ ] Chrome (latest 2 versions)
  - [ ] Firefox (latest 2 versions)
  - [ ] Safari (latest 2 versions)
  - [ ] Edge (latest version)

---

## Appendix A: Example Implementations

### A.1 Pydantic Model with User-Friendly Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class TaskCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="A clear, concise name for your task",
        example="Complete project documentation"
    )
    description: Optional[str] = Field(
        None,
        description="Additional details about the task",
        example="Write comprehensive user guide and API documentation"
    )
    priority: TaskPriority = Field(
        TaskPriority.MEDIUM,
        description="Task priority level (default: MEDIUM)"
    )
    due_date: Optional[datetime] = Field(
        None,
        description="When this task needs to be completed"
    )
    estimated_duration: Optional[int] = Field(
        None,
        ge=1,
        le=1440,
        description="Estimated time to complete in minutes (1-1440)"
    )

    @validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError(
                'Title is required and cannot be empty. '
                'Please provide a descriptive name for your task.'
            )
        return v.strip()

    @validator('due_date')
    def due_date_in_future(cls, v):
        if v and v < datetime.now():
            raise ValueError(
                'The due date must be in the future. '
                'Please select a date after today.'
            )
        return v

    class Config:
        schema_extra = {
            "example": {
                "title": "Complete project documentation",
                "description": "Write comprehensive user guide",
                "priority": "HIGH",
                "due_date": "2025-10-15T17:00:00Z",
                "estimated_duration": 120
            }
        }
```

### A.2 Error Handler Middleware

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import uuid
from datetime import datetime

async def user_friendly_error_handler(request: Request, exc: Exception):
    """Convert all errors to user-friendly format"""

    request_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"

    if isinstance(exc, ValidationError):
        # Pydantic validation error
        errors = {}
        for error in exc.errors():
            field = error['loc'][-1]
            message = error['msg']

            # Make message more user-friendly
            if 'field required' in message:
                message = f"{field.replace('_', ' ').title()} is required."

            if field not in errors:
                errors[field] = []
            errors[field].append(message)

        return JSONResponse(
            status_code=400,
            content={
                "error": "ValidationError",
                "message": "Please fix the following errors:",
                "details": errors,
                "request_id": request_id,
                "timestamp": timestamp,
                "documentation_url": "https://docs.example.com/errors/validation"
            }
        )

    elif isinstance(exc, HTTPException):
        # HTTP exceptions
        status_code = exc.status_code

        # User-friendly messages for common status codes
        messages = {
            401: "Please log in to access this resource.",
            403: "You don't have permission to perform this action.",
            404: "The requested resource was not found.",
            429: "Too many requests. Please try again in a moment.",
            500: "Something went wrong on our end. Please try again."
        }

        return JSONResponse(
            status_code=status_code,
            content={
                "error": exc.__class__.__name__,
                "message": messages.get(status_code, str(exc.detail)),
                "request_id": request_id,
                "timestamp": timestamp,
                "documentation_url": f"https://docs.example.com/errors/{status_code}"
            }
        )

    else:
        # Unexpected errors
        # Log the full error for debugging
        print(f"Unexpected error: {exc}")

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "Something unexpected happened. Our team has been notified.",
                "request_id": request_id,
                "timestamp": timestamp,
                "support_url": "https://support.example.com"
            }
        )
```

---

## Document Control

- **Version**: 1.0
- **Created**: 2025-10-06
- **Author**: Time Agent 5
- **Status**: Implementation Ready
- **Next Review**: Post-user testing

**Related Documents:**
- ARCHITECTURE.md - System architecture
- openapi.yaml - API specification
- SYSTEM_DIAGRAMS.md - Visual diagrams
