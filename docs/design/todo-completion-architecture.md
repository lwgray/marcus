# Todo Completion Feature - Architecture Diagrams

## System Architecture Overview

### High-Level Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              React Components                               │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │ │
│  │  │ TodoList     │  │ TodoItem     │  │ CompletionStats │  │ │
│  │  │              │  │              │  │                 │  │ │
│  │  │ - Render     │  │ - Checkbox   │  │ - Progress Bar  │  │ │
│  │  │ - Filter     │  │ - Content    │  │ - Metrics       │  │ │
│  │  │ - Sort       │  │ - Actions    │  │ - Charts        │  │ │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │ │
│  │         │                  │                   │           │ │
│  │         └──────────────────┼───────────────────┘           │ │
│  │                            │                               │ │
│  │  ┌─────────────────────────▼────────────────────────────┐ │ │
│  │  │          State Management (Redux/Zustand)            │ │ │
│  │  │                                                       │ │ │
│  │  │  - Todos Store                                       │ │ │
│  │  │  - Optimistic Updates                                │ │ │
│  │  │  - Selection State                                   │ │ │
│  │  │  - Statistics Cache                                  │ │ │
│  │  └─────────────────────────┬────────────────────────────┘ │ │
│  └────────────────────────────┼──────────────────────────────┘ │
│                               │                                 │
│  ┌────────────────────────────▼──────────────────────────────┐ │
│  │              API Service Layer                            │ │
│  │                                                            │ │
│  │  - todoApi.toggleComplete()                              │ │
│  │  - todoApi.updateTodo()                                  │ │
│  │  - todoApi.bulkUpdateStatus()                            │ │
│  │  - todoApi.getCompletionStats()                          │ │
│  │                                                            │ │
│  │  Features:                                                │ │
│  │  • Request/Response Interceptors                         │ │
│  │  • Error Handling                                        │ │
│  │  • Retry Logic                                           │ │
│  │  • Request Deduplication                                 │ │
│  └────────────────────────────┬──────────────────────────────┘ │
└─────────────────────────────────┼────────────────────────────────┘
                                  │
                            HTTP/HTTPS
                                  │
┌─────────────────────────────────▼────────────────────────────────┐
│                         Backend Layer                             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Application                      │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │                API Routers                            │  │  │
│  │  │                                                       │  │  │
│  │  │  POST   /api/v1/todos/{id}/toggle-complete          │  │  │
│  │  │  PATCH  /api/v1/todos/{id}                           │  │  │
│  │  │  PATCH  /api/v1/todos/bulk                           │  │  │
│  │  │  GET    /api/v1/stats/completion                     │  │  │
│  │  └──────────────────────┬───────────────────────────────┘  │  │
│  │                         │                                   │  │
│  │  ┌──────────────────────▼───────────────────────────────┐  │  │
│  │  │            Middleware Layer                          │  │  │
│  │  │                                                       │  │  │
│  │  │  • Authentication (JWT Verification)                 │  │  │
│  │  │  • Rate Limiting                                     │  │  │
│  │  │  • CORS Headers                                      │  │  │
│  │  │  • Request Logging                                   │  │  │
│  │  │  • Error Handler                                     │  │  │
│  │  └──────────────────────┬───────────────────────────────┘  │  │
│  │                         │                                   │  │
│  │  ┌──────────────────────▼───────────────────────────────┐  │  │
│  │  │              Service Layer                           │  │  │
│  │  │                                                       │  │  │
│  │  │  TodoService:                                        │  │  │
│  │  │    - toggle_complete()                               │  │  │
│  │  │    - bulk_update_status()                            │  │  │
│  │  │    - get_completion_stats()                          │  │  │
│  │  │                                                       │  │  │
│  │  │  Business Logic:                                     │  │  │
│  │  │    • Status Transition Validation                    │  │  │
│  │  │    • Timestamp Management                            │  │  │
│  │  │    • Ownership Verification                          │  │  │
│  │  │    • Statistics Calculation                          │  │  │
│  │  └──────────────────────┬───────────────────────────────┘  │  │
│  │                         │                                   │  │
│  │  ┌──────────────────────▼───────────────────────────────┐  │  │
│  │  │              Data Access Layer                       │  │  │
│  │  │                                                       │  │  │
│  │  │  SQLAlchemy ORM:                                     │  │  │
│  │  │    - Todo Model                                      │  │  │
│  │  │    - Query Builder                                   │  │  │
│  │  │    - Transaction Management                          │  │  │
│  │  └──────────────────────┬───────────────────────────────┘  │  │
│  └─────────────────────────┼──────────────────────────────────┘  │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                      Database Connection
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                    PostgreSQL Database                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     Tables                                  │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │  todos                                                │  │  │
│  │  │  - id (UUID, PK)                                     │  │  │
│  │  │  - title (VARCHAR)                                   │  │  │
│  │  │  - status (VARCHAR) ← Modified by completion        │  │  │
│  │  │  - completed_at (TIMESTAMP) ← Set on completion     │  │  │
│  │  │  - owner_id (UUID, FK)                               │  │  │
│  │  │  - created_at (TIMESTAMP)                            │  │  │
│  │  │  - updated_at (TIMESTAMP)                            │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                              │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │  Indexes                                              │  │  │
│  │  │  - idx_todos_status                                   │  │  │
│  │  │  - idx_todos_completed_at                             │  │  │
│  │  │  - idx_todos_owner_status (composite)                 │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. Single Todo Completion Flow

```
User Action                     Frontend                Backend              Database
    │                              │                       │                    │
    │  Click Checkbox              │                       │                    │
    ├─────────────────────────────▶│                       │                    │
    │                              │                       │                    │
    │                              │ Optimistic Update    │                    │
    │                              │ (Update UI)          │                    │
    │                              │                       │                    │
    │                              │ POST /toggle-complete │                    │
    │                              ├──────────────────────▶│                    │
    │                              │                       │                    │
    │                              │                       │ Validate Ownership│
    │                              │                       │ Check Status       │
    │                              │                       │                    │
    │                              │                       │ UPDATE todos       │
    │                              │                       │ SET status=        │
    │                              │                       │   'completed',     │
    │                              │                       │   completed_at=NOW │
    │                              │                       ├───────────────────▶│
    │                              │                       │                    │
    │                              │                       │    Success         │
    │                              │                       │◀───────────────────┤
    │                              │                       │                    │
    │                              │  Todo Object          │                    │
    │                              │◀──────────────────────┤                    │
    │                              │                       │                    │
    │  Updated UI                  │ Confirm Update       │                    │
    │◀─────────────────────────────┤ Update Stats         │                    │
    │  (Strikethrough, etc)        │                       │                    │
    │                              │                       │                    │
```

### 2. Rollback on Error Flow

```
User Action                     Frontend                Backend              Database
    │                              │                       │                    │
    │  Click Checkbox              │                       │                    │
    ├─────────────────────────────▶│                       │                    │
    │                              │                       │                    │
    │                              │ Optimistic Update    │                    │
    │                              │ (Update UI)          │                    │
    │                              │                       │                    │
    │                              │ POST /toggle-complete │                    │
    │                              ├──────────────────────▶│                    │
    │                              │                       │                    │
    │                              │                       │  ❌ ERROR          │
    │                              │                       │  (Permission/      │
    │                              │                       │   Network/DB)      │
    │                              │                       │                    │
    │                              │  Error Response       │                    │
    │                              │◀──────────────────────┤                    │
    │                              │                       │                    │
    │                              │ Rollback Optimistic  │                    │
    │                              │ Show Error Toast     │                    │
    │                              │                       │                    │
    │  Reverted UI                 │                       │                    │
    │  Error Message               │                       │                    │
    │◀─────────────────────────────┤                       │                    │
    │                              │                       │                    │
```

### 3. Bulk Completion Flow

```
User Action                     Frontend                Backend              Database
    │                              │                       │                    │
    │  Select Multiple Todos       │                       │                    │
    ├─────────────────────────────▶│                       │                    │
    │                              │                       │                    │
    │  Click "Mark Complete"       │                       │                    │
    ├─────────────────────────────▶│                       │                    │
    │                              │                       │                    │
    │                              │ Optimistic Updates   │                    │
    │                              │ (All Selected)        │                    │
    │                              │                       │                    │
    │                              │ PATCH /bulk           │                    │
    │                              ├──────────────────────▶│                    │
    │                              │                       │                    │
    │                              │                       │ BEGIN TRANSACTION │
    │                              │                       ├──────────────────▶│
    │                              │                       │                    │
    │                              │                       │ Verify Ownership  │
    │                              │                       │ (All Todos)        │
    │                              │                       │                    │
    │                              │                       │ UPDATE todos       │
    │                              │                       │ WHERE id IN (...)  │
    │                              │                       │ SET status=        │
    │                              │                       │   'completed'      │
    │                              │                       ├──────────────────▶│
    │                              │                       │                    │
    │                              │                       │ COMMIT             │
    │                              │                       ├──────────────────▶│
    │                              │                       │                    │
    │                              │  Bulk Response        │                    │
    │                              │  {updated_count: N}   │                    │
    │                              │◀──────────────────────┤                    │
    │                              │                       │                    │
    │  Success Toast               │ Confirm Updates      │                    │
    │  "N todos completed"         │ Clear Selection      │                    │
    │◀─────────────────────────────┤ Refresh Stats        │                    │
    │                              │                       │                    │
```

---

## Component Architecture

### Frontend Component Hierarchy

```
┌────────────────────────────────────────────────────────────┐
│                        TodoApp                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  TodoList                             │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │         TodoListHeader                          │  │  │
│  │  │  ┌──────────────┐    ┌────────────────────┐    │  │  │
│  │  │  │ BulkActions  │    │ CompletionStats    │    │  │  │
│  │  │  │              │    │                    │    │  │  │
│  │  │  │ - Select All │    │ - Progress Bar     │    │  │  │
│  │  │  │ - Mark       │    │ - Percentage       │    │  │  │
│  │  │  │   Complete   │    │ - Counts           │    │  │  │
│  │  │  │ - Mark       │    │                    │    │  │  │
│  │  │  │   Incomplete │    │                    │    │  │  │
│  │  │  └──────────────┘    └────────────────────┘    │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │         TodoItem (Repeats)                      │  │  │
│  │  │  ┌──────────────────────────────────────────┐  │  │  │
│  │  │  │  ┌─────────┐  ┌──────────────┐  ┌──────┐ │  │  │  │
│  │  │  │  │Selection│  │ Completion   │  │Todo  │ │  │  │  │
│  │  │  │  │Checkbox │  │ Checkbox     │  │Content│││  │  │  │
│  │  │  │  │         │  │              │  │      │ │  │  │  │
│  │  │  │  │ (Bulk   │  │ ✓ Complete   │  │Title │ │  │  │  │
│  │  │  │  │  Ops)   │  │   /Incomplete│  │Desc  │ │  │  │  │
│  │  │  │  │         │  │              │  │Meta  │ │  │  │  │
│  │  │  │  └─────────┘  └──────────────┘  └──────┘ │  │  │  │
│  │  │  │                                  ┌──────┐ │  │  │  │
│  │  │  │                                  │Actions││ │  │  │  │
│  │  │  │                                  │      │ │  │  │  │
│  │  │  │                                  │Edit  │ │  │  │  │
│  │  │  │                                  │Delete│ │  │  │  │
│  │  │  │                                  └──────┘ │  │  │  │
│  │  │  └──────────────────────────────────────────┘  │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘

Props Flow:
TodoApp
  ├─ todos: Todo[]
  ├─ onToggleComplete: (id: string) => Promise<void>
  ├─ onBulkUpdate: (ids: string[], status: string) => Promise<void>
  └─ stats: CompletionStats

TodoList
  ├─ receives: todos, onToggleComplete, onBulkUpdate
  └─ manages: selection state

TodoItem
  ├─ receives: todo, onToggleComplete
  └─ renders: CompletionCheckbox, TodoContent

CompletionCheckbox
  ├─ receives: todo.status, onToggleComplete
  └─ renders: styled checkbox with states
```

---

## State Flow Architecture

### Redux Store Structure

```
┌─────────────────────────────────────────────────────────────┐
│                      Redux Store                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  todos                                                 │  │
│  │  ├─ byId: Record<string, Todo>                        │  │
│  │  ├─ allIds: string[]                                  │  │
│  │  ├─ loading: boolean                                  │  │
│  │  └─ error: string | null                              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  optimisticUpdates                                     │  │
│  │  └─ [todoId]: Partial<Todo>                           │  │
│  │     (Temporary state during API call)                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  selection                                             │  │
│  │  └─ selectedIds: string[]                             │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  stats                                                 │  │
│  │  ├─ total: number                                     │  │
│  │  ├─ completed: number                                 │  │
│  │  ├─ pending: number                                   │  │
│  │  ├─ in_progress: number                               │  │
│  │  ├─ completion_rate: number                           │  │
│  │  └─ loading: boolean                                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

Actions Flow:
┌────────────────┐
│ User Interaction│
└────────┬────────┘
         │
         ▼
┌────────────────┐
│ Action Creator │ (toggleComplete)
└────────┬────────┘
         │
         ▼
┌────────────────┐
│  Async Thunk   │
│  1. Optimistic │
│     Update     │
│  2. API Call   │
│  3. Success/   │
│     Failure    │
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌────────────────┐  ┌──────────────┐
│ Success Action │  │ Failure Action│
└────────┬────────┘  └──────┬───────┘
         │                  │
         ▼                  ▼
┌────────────────────────────────────┐
│         Reducer                     │
│  - Update todos.byId                │
│  - Clear optimisticUpdates          │
│  - Or rollback on failure           │
└────────┬────────────────────────────┘
         │
         ▼
┌────────────────┐
│  Store Updated │
└────────┬────────┘
         │
         ▼
┌────────────────┐
│   Components   │
│   Re-render    │
└────────────────┘
```

---

## API Request/Response Architecture

### Request Pipeline

```
Frontend Component
      │
      ▼
┌──────────────────────────────┐
│   API Service Layer          │
│                              │
│ 1. Prepare Request           │
│    - Add auth token          │
│    - Add headers             │
│    - Serialize data          │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   HTTP Client (Axios)        │
│                              │
│ - Request Interceptor        │
│   • Add Authorization        │
│   • Add Request ID           │
│   • Log Request              │
│                              │
│ - Response Interceptor       │
│   • Handle Errors            │
│   • Refresh Token            │
│   • Transform Data           │
└──────────┬───────────────────┘
           │
           ▼ HTTP/HTTPS
┌──────────────────────────────┐
│   API Gateway / Load Balancer│
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   FastAPI Application        │
│                              │
│ 1. CORS Middleware           │
│ 2. Rate Limit Middleware     │
│ 3. Auth Middleware           │
│    - Verify JWT              │
│    - Extract user_id         │
│ 4. Router Handler            │
│ 5. Service Layer             │
│ 6. Database Layer            │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   PostgreSQL Database        │
└──────────────────────────────┘
```

### Response Pipeline

```
PostgreSQL Database
      │
      ▼ Query Result
┌──────────────────────────────┐
│   SQLAlchemy ORM             │
│   - Map to Model             │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   Service Layer              │
│   - Business Logic           │
│   - Transform Data           │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   Pydantic Schema            │
│   - Validate                 │
│   - Serialize to JSON        │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   FastAPI Response           │
│   - Add Headers              │
│   - Set Status Code          │
└──────────┬───────────────────┘
           │
           ▼ HTTP Response
┌──────────────────────────────┐
│   Axios Response Interceptor │
│   - Check Status             │
│   - Parse JSON               │
│   - Handle Errors            │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   API Service Layer          │
│   - Transform to App Format  │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   Redux Action               │
│   - Dispatch Success         │
│   - Update Store             │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│   React Component            │
│   - Re-render with New Data  │
└──────────────────────────────┘
```

---

## Database Schema Diagram

```
┌──────────────────────────────────────────────────────────┐
│                      users                                │
│──────────────────────────────────────────────────────────│
│ 🔑 id                  UUID         PRIMARY KEY          │
│    email               VARCHAR(255) UNIQUE NOT NULL      │
│    username            VARCHAR(50)  UNIQUE NOT NULL      │
│    password_hash       VARCHAR(255) NOT NULL             │
│    first_name          VARCHAR(100)                      │
│    last_name           VARCHAR(100)                      │
│    avatar_url          TEXT                              │
│    is_active           BOOLEAN      DEFAULT TRUE         │
│    created_at          TIMESTAMP    DEFAULT NOW()        │
│    updated_at          TIMESTAMP    DEFAULT NOW()        │
└──────────────────────────┬───────────────────────────────┘
                           │
                           │ 1
                           │
                           │ owner_id (FK)
                           │
                           │ *
                           ▼
┌──────────────────────────────────────────────────────────┐
│                      todos                                │
│──────────────────────────────────────────────────────────│
│ 🔑 id                  UUID         PRIMARY KEY          │
│    title               VARCHAR(200) NOT NULL             │
│    description         TEXT                              │
│    status              VARCHAR(20)  DEFAULT 'pending'    │
│    priority            VARCHAR(20)  DEFAULT 'medium'     │
│    due_date            TIMESTAMP                         │
│ ★  completed_at        TIMESTAMP    ← NEW FIELD         │
│ 🔐 owner_id            UUID         REFERENCES users(id) │
│    assigned_to_id      UUID         REFERENCES users(id) │
│    position            INTEGER      DEFAULT 0            │
│    created_at          TIMESTAMP    DEFAULT NOW()        │
│    updated_at          TIMESTAMP    DEFAULT NOW()        │
│                                                           │
│ ✓ CONSTRAINT valid_status                                │
│   CHECK (status IN ('pending', 'in_progress',            │
│                     'completed'))                         │
│                                                           │
│ ✓ CONSTRAINT completed_at_requires_status                │
│   CHECK ((status = 'completed' AND                       │
│           completed_at IS NOT NULL) OR                   │
│          (status != 'completed' AND                      │
│           completed_at IS NULL))                         │
└──────────────────────────┬───────────────────────────────┘
                           │
                           │ *
                           │
                           │ todo_id (FK)
                           │
                           │ *
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   todo_tags                               │
│──────────────────────────────────────────────────────────│
│ 🔑 todo_id             UUID         REFERENCES todos(id) │
│ 🔑 tag_id              UUID         REFERENCES tags(id)  │
│                                                           │
│    PRIMARY KEY (todo_id, tag_id)                         │
└───────────────────────────────────────────────────────────┘
                           ▲
                           │ *
                           │
                           │ tag_id (FK)
                           │
                           │ *
┌──────────────────────────┴───────────────────────────────┐
│                      tags                                 │
│──────────────────────────────────────────────────────────│
│ 🔑 id                  UUID         PRIMARY KEY          │
│    name                VARCHAR(50)  NOT NULL             │
│    color               VARCHAR(7)                        │
│ 🔐 user_id             UUID         REFERENCES users(id) │
│    created_at          TIMESTAMP    DEFAULT NOW()        │
│                                                           │
│    UNIQUE (name, user_id)                                │
└──────────────────────────────────────────────────────────┘

Indexes:
┌────────────────────────────────────────┐
│ idx_todos_status                        │
│ idx_todos_completed_at          ← NEW  │
│ idx_todos_owner_status                  │
│ idx_todos_owner_id                      │
│ idx_todos_due_date                      │
│ idx_tags_user_id                        │
└────────────────────────────────────────┘
```

---

## Security Architecture

### Authentication & Authorization Flow

```
┌──────────────┐
│   User       │
└──────┬───────┘
       │
       │ 1. Login
       ▼
┌──────────────────────────────────┐
│   POST /api/v1/auth/login        │
│   { email, password }            │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│   Verify Credentials             │
│   - Hash password                │
│   - Compare with DB              │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│   Generate JWT Tokens            │
│   - Access Token (1h)            │
│   - Refresh Token (7d)           │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│   Return Tokens                  │
│   { access_token, refresh_token }│
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│   Client Stores Tokens           │
│   - localStorage or httpOnly     │
│     cookie                       │
└──────────┬───────────────────────┘
           │
           │ 2. Subsequent Requests
           ▼
┌──────────────────────────────────┐
│   Authorization: Bearer <token>  │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│   Auth Middleware                │
│   - Extract token                │
│   - Verify signature             │
│   - Check expiration             │
│   - Extract user_id              │
└──────────┬───────────────────────┘
           │
           ├─── Valid ──────┐
           │                │
           │                ▼
           │     ┌──────────────────┐
           │     │  Attach user_id  │
           │     │  to request      │
           │     └─────────┬────────┘
           │               │
           │               ▼
           │     ┌──────────────────┐
           │     │  Route Handler   │
           │     │  - Check         │
           │     │    ownership     │
           │     └──────────────────┘
           │
           └─── Invalid ───┐
                           │
                           ▼
                ┌──────────────────┐
                │  401 Unauthorized│
                └──────────────────┘
```

---

## Performance Optimization Architecture

### Caching Strategy

```
┌──────────────────────────────────────────────────────────┐
│                   Client Layer                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │  React Query / SWR Cache                           │  │
│  │  - Cache todos for 5 minutes                       │  │
│  │  - Invalidate on mutations                         │  │
│  │  - Background refetch                              │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Service Worker (PWA)                              │  │
│  │  - Cache API responses                             │  │
│  │  - Offline support                                 │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   Server Layer                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Redis Cache                                       │  │
│  │  - Cache completion stats (TTL: 1 min)            │  │
│  │  - Cache user todos (invalidate on update)        │  │
│  │  - Rate limit counters                            │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                Database Layer                             │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Query Optimization                                │  │
│  │  - Indexed columns for filtering                  │  │
│  │  - Composite indexes for common queries           │  │
│  │  - Connection pooling                             │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

### Database Query Optimization

```sql
-- Efficient completion stats query
-- Uses indexes: idx_todos_owner_status, idx_todos_status

SELECT
    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress_count,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
    COUNT(*) as total_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE status = 'completed') / NULLIF(COUNT(*), 0),
        2
    ) as completion_rate
FROM todos
WHERE owner_id = $1;

-- Efficient filtered todo list query
-- Uses index: idx_todos_owner_status

SELECT *
FROM todos
WHERE owner_id = $1
  AND status = ANY($2)  -- Array of statuses
ORDER BY
    CASE WHEN status = 'completed' THEN 1 ELSE 0 END,  -- Completed last
    priority DESC,
    due_date ASC NULLS LAST
LIMIT $3 OFFSET $4;
```

---

## Deployment Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      CDN (CloudFlare)                       │
│  - Static assets (JS, CSS, images)                         │
│  - DDoS protection                                          │
│  - SSL termination                                          │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                 Load Balancer (AWS ALB)                     │
│  - Health checks                                            │
│  - SSL termination                                          │
│  - Request routing                                          │
└────────┬────────────────────────────────┬──────────────────┘
         │                                │
         ▼                                ▼
┌──────────────────┐            ┌──────────────────┐
│  Frontend Tier   │            │  Backend Tier    │
│  (ECS/Fargate)   │            │  (ECS/Fargate)   │
│                  │            │                  │
│  - React SPA     │            │  - FastAPI       │
│  - Nginx         │            │  - Uvicorn       │
│  - Auto-scaling  │            │  - Auto-scaling  │
└──────────────────┘            └────────┬─────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │  Redis Cache     │
                              │  (ElastiCache)   │
                              └──────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │  PostgreSQL DB   │
                              │  (RDS)           │
                              │  - Multi-AZ      │
                              │  - Read replicas │
                              └──────────────────┘
```

---

## Monitoring & Observability

```
┌────────────────────────────────────────────────────────────┐
│                    Application Metrics                      │
│                                                             │
│  Frontend:                    Backend:                      │
│  - Page load time             - Request latency             │
│  - Checkbox click latency     - Database query time         │
│  - API call duration          - Error rates                 │
│  - Error rates                - Throughput (req/sec)        │
│  - User interactions          - Active connections          │
└────────────┬───────────────────────────┬────────────────────┘
             │                           │
             ▼                           ▼
┌──────────────────┐          ┌──────────────────┐
│  Browser RUM     │          │  APM Tool        │
│  (DataDog/NR)    │          │  (DataDog/NR)    │
└──────────────────┘          └──────────────────┘
             │                           │
             └───────────┬───────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                  Centralized Logging                        │
│  - ELK Stack / CloudWatch Logs                             │
│  - Structured JSON logs                                     │
│  - Request tracing                                          │
│  - Error tracking (Sentry)                                  │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                   Alerting System                           │
│  - Error rate threshold exceeded                            │
│  - Response time degradation                                │
│  - Database connection issues                               │
│  - Rate limit exceeded                                      │
└────────────────────────────────────────────────────────────┘
```

---

## Legend

```
🔑 Primary Key
🔐 Foreign Key
★  New/Modified Field
✓  Constraint/Check
│  Flow/Connection
▼  Direction Down
►  Direction Right
```

---

**End of Architecture Diagrams**
