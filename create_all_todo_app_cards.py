#!/usr/bin/env python3
"""
Create all 17 Todo App development cards with detailed information
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment variables
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

# Load the JSON data
with open('todo_app_planka_cards.json', 'r') as f:
    TODO_APP_DATA = json.load(f)

# Label color mapping for Planka
LABEL_COLORS = {
    "Feature": "lagoon-blue",
    "Frontend": "pink-tulip",
    "Backend": "berry-red",
    "Database": "pumpkin-orange",
    "Testing": "bright-moss",
    "Bug": "red-burgundy",
    "High Priority": "midnight-blue",
    "Enhancement": "sunny-grass",
    "Documentation": "light-mud",
    "Security": "tank-green",
    "DevOps": "antique-blue",
    "Performance": "coral-green",
    "UI/UX": "light-orange",
    "API": "wet-moss",
    "Infrastructure": "desert-sand"
}

# Enhanced card data with better descriptions and subtasks
ENHANCED_CARDS = {
    "card-001": {
        "description": """## Overview
Set up the foundational project structure for the Todo App with proper organization and configuration.

## Objectives
- Create a scalable folder structure
- Set up development environment
- Configure build tools and dependencies
- Establish coding standards

## Technical Requirements

### Project Structure
```
todo-app/
├── backend/
│   ├── src/
│   │   ├── controllers/
│   │   ├── models/
│   │   ├── services/
│   │   ├── middleware/
│   │   ├── utils/
│   │   └── config/
│   ├── tests/
│   ├── package.json
│   └── tsconfig.json
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── styles/
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── database/
│   ├── migrations/
│   └── seeds/
├── docs/
├── scripts/
└── docker-compose.yml
```

### Configuration Files
- **package.json**: Dependencies and scripts
- **tsconfig.json**: TypeScript configuration
- **.env.example**: Environment variables template
- **.gitignore**: Version control exclusions
- **.eslintrc**: Code style rules
- **prettier.config.js**: Code formatting

### Development Tools
- Node.js 18+ and npm/yarn
- TypeScript 5+
- ESLint and Prettier
- Git hooks with Husky
- Commitizen for commit messages

## Implementation Steps
1. Initialize npm workspaces for monorepo
2. Set up TypeScript configuration
3. Configure ESLint and Prettier
4. Set up Git hooks for code quality
5. Create Docker configuration
6. Set up environment variables
7. Create initial documentation

## Success Criteria
- [ ] All configuration files created
- [ ] Build scripts working
- [ ] Linting and formatting configured
- [ ] Git repository initialized
- [ ] Development environment documented
""",
        "subtasks": [
            "Initialize npm workspaces for monorepo structure",
            "Create backend folder structure and package.json",
            "Create frontend folder structure and package.json",
            "Configure TypeScript for both frontend and backend",
            "Set up ESLint with TypeScript support",
            "Configure Prettier for code formatting",
            "Create .gitignore with comprehensive exclusions",
            "Set up Husky for Git hooks",
            "Create docker-compose.yml for local development",
            "Write initial README.md with setup instructions",
            "Create .env.example with all required variables",
            "Set up commitizen for conventional commits"
        ],
        "labels": ["Infrastructure", "High Priority", "Backend", "Frontend"],
        "priority": "high",
        "timeEstimate": 16,
        "dependencies": []
    },
    "card-002": {
        "description": """## Overview
Design a robust and scalable database schema for the Todo App that supports all required features.

## Database Design

### Core Tables

#### 1. Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. Todos Table
```sql
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(50) DEFAULT 'medium',
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    position INTEGER NOT NULL DEFAULT 0,
    parent_id UUID REFERENCES todos(id) ON DELETE CASCADE
);
```

#### 3. Categories Table
```sql
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7) DEFAULT '#808080',
    icon VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);
```

#### 4. Tags Table
```sql
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7) DEFAULT '#808080',
    UNIQUE(user_id, name)
);
```

#### 5. Junction Tables
```sql
CREATE TABLE todo_categories (
    todo_id UUID REFERENCES todos(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (todo_id, category_id)
);

CREATE TABLE todo_tags (
    todo_id UUID REFERENCES todos(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (todo_id, tag_id)
);
```

### Features Support
- User authentication and profiles
- Todo CRUD operations
- Hierarchical todos (subtasks)
- Categories and tags
- Due dates and priorities
- Soft deletes
- Audit trails
- Full-text search

### Performance Considerations
- Proper indexing strategy
- Partitioning for large datasets
- Query optimization
- Connection pooling
- Caching strategy

## Migration Strategy
1. Version control for schema changes
2. Rollback capabilities
3. Data seeding for development
4. Zero-downtime migrations
""",
        "subtasks": [
            "Design users table with authentication fields",
            "Design todos table with all required fields",
            "Create categories and tags tables",
            "Design junction tables for many-to-many relationships",
            "Add indexes for performance optimization",
            "Create audit tables for change tracking",
            "Design notification preferences table",
            "Create database views for common queries",
            "Write migration files for all tables",
            "Create seed data for development",
            "Document database relationships",
            "Set up database backup strategy"
        ],
        "labels": ["Database", "High Priority", "Backend"],
        "priority": "high",
        "timeEstimate": 24,
        "dependencies": []
    },
    "card-003": {
        "description": """## Overview
Implement the core Todo model with comprehensive business logic, validation, and database operations.

## Model Architecture

### Todo Model Features
- Full CRUD operations
- Data validation
- Business logic encapsulation
- Query builders
- Event handling
- Serialization

### Model Definition
```typescript
interface ITodo {
    id: string;
    userId: string;
    title: string;
    description?: string;
    status: TodoStatus;
    priority: TodoPriority;
    dueDate?: Date;
    completedAt?: Date;
    position: number;
    parentId?: string;
    categories: ICategory[];
    tags: ITag[];
    createdAt: Date;
    updatedAt: Date;
}

enum TodoStatus {
    PENDING = 'pending',
    IN_PROGRESS = 'in_progress',
    COMPLETED = 'completed',
    CANCELLED = 'cancelled'
}

enum TodoPriority {
    LOW = 'low',
    MEDIUM = 'medium',
    HIGH = 'high',
    URGENT = 'urgent'
}
```

### Validation Rules
- Title: Required, 1-255 characters
- Description: Optional, max 5000 characters
- Status: Must be valid enum value
- Priority: Must be valid enum value
- Due date: Must be future date (for new todos)
- Parent ID: Must exist if provided

### Business Logic
- Automatic position calculation
- Status transitions validation
- Completion timestamp management
- Subtask management
- Overdue calculations
- Progress tracking

### Query Methods
- `findByUser(userId: string)`
- `findByStatus(status: TodoStatus)`
- `findOverdue()`
- `findByDateRange(start: Date, end: Date)`
- `search(query: string)`
- `findWithSubtasks(todoId: string)`

## Implementation Requirements
- Use ORM (TypeORM/Prisma)
- Implement repository pattern
- Add transaction support
- Include soft deletes
- Add event hooks
- Support batch operations
""",
        "subtasks": [
            "Create Todo entity/model class",
            "Define model interfaces and types",
            "Implement validation decorators/rules",
            "Create TodoRepository class",
            "Implement CRUD methods",
            "Add complex query methods",
            "Implement status transition logic",
            "Add position management for sorting",
            "Create model serializers",
            "Implement event hooks (onCreate, onUpdate)",
            "Add transaction support",
            "Write comprehensive unit tests",
            "Add model documentation"
        ],
        "labels": ["Backend", "High Priority", "Feature"],
        "priority": "high",
        "timeEstimate": 20,
        "dependencies": ["card-001", "card-002"]
    },
    "card-004": {
        "description": """## Overview
Configure a robust database connection system with pooling, monitoring, and error handling.

## Connection Architecture

### Database Configuration
```typescript
interface DatabaseConfig {
    host: string;
    port: number;
    database: string;
    username: string;
    password: string;
    ssl: boolean;
    poolSize: number;
    idleTimeout: number;
    connectionTimeout: number;
}
```

### Connection Pool Settings
- **Minimum connections**: 5
- **Maximum connections**: 20
- **Idle timeout**: 30 seconds
- **Connection timeout**: 10 seconds
- **Retry attempts**: 3
- **Retry delay**: 1 second

### Features to Implement
1. **Connection Management**
   - Automatic reconnection
   - Connection health checks
   - Graceful shutdown
   - Connection lifecycle events

2. **Performance Optimization**
   - Query caching
   - Prepared statements
   - Batch operations
   - Read replicas support

3. **Monitoring**
   - Connection metrics
   - Query performance tracking
   - Error logging
   - Slow query alerts

4. **Security**
   - SSL/TLS encryption
   - Connection string encryption
   - SQL injection prevention
   - Access control

### Error Handling
- Connection failure recovery
- Transaction rollback
- Deadlock detection
- Timeout management
- Circuit breaker pattern

## Health Check Endpoint
```typescript
GET /health/database
{
    "status": "healthy",
    "connections": {
        "active": 5,
        "idle": 15,
        "total": 20
    },
    "latency": 2.5,
    "version": "14.5"
}
```
""",
        "subtasks": [
            "Install and configure database driver",
            "Create database configuration module",
            "Implement connection pool setup",
            "Add connection retry logic",
            "Create health check endpoint",
            "Implement query logging",
            "Add performance monitoring",
            "Set up connection event handlers",
            "Configure SSL/TLS for production",
            "Create database utilities module",
            "Add migration runner",
            "Implement graceful shutdown",
            "Write connection tests"
        ],
        "labels": ["Backend", "Infrastructure", "High Priority"],
        "priority": "high",
        "timeEstimate": 16,
        "dependencies": ["card-001"]
    },
    "card-005": {
        "description": """## Overview
Implement comprehensive RESTful API endpoints for all Todo CRUD operations with proper validation and error handling.

## API Endpoints

### 1. List Todos
```
GET /api/todos
Query params:
- page: number (default: 1)
- limit: number (default: 20, max: 100)
- status: string (pending|in_progress|completed)
- priority: string (low|medium|high|urgent)
- category: string
- search: string
- sortBy: string (createdAt|dueDate|priority)
- sortOrder: string (asc|desc)

Response: {
    data: Todo[],
    pagination: {
        page: number,
        limit: number,
        total: number,
        totalPages: number
    }
}
```

### 2. Get Single Todo
```
GET /api/todos/:id
Response: { data: Todo }
```

### 3. Create Todo
```
POST /api/todos
Body: {
    title: string (required),
    description?: string,
    priority?: string,
    dueDate?: string (ISO 8601),
    categoryIds?: string[],
    tagIds?: string[],
    parentId?: string
}
Response: { data: Todo }
```

### 4. Update Todo
```
PUT /api/todos/:id
Body: Partial<Todo>
Response: { data: Todo }
```

### 5. Delete Todo
```
DELETE /api/todos/:id
Response: { message: string }
```

### 6. Update Status
```
PATCH /api/todos/:id/status
Body: { status: string }
Response: { data: Todo }
```

### 7. Bulk Operations
```
POST /api/todos/bulk
Body: {
    action: 'update'|'delete',
    ids: string[],
    data?: Partial<Todo>
}
Response: { affected: number }
```

## Implementation Requirements
- Request validation middleware
- Authentication middleware
- Error handling middleware
- Rate limiting
- API versioning
- OpenAPI documentation
- Response caching
- CORS configuration
""",
        "subtasks": [
            "Set up Express router for todos",
            "Implement GET /todos with pagination",
            "Add filtering and search functionality",
            "Implement GET /todos/:id endpoint",
            "Create POST /todos with validation",
            "Implement PUT /todos/:id endpoint",
            "Add DELETE /todos/:id endpoint",
            "Create PATCH /todos/:id/status",
            "Implement bulk operations endpoint",
            "Add request validation middleware",
            "Implement error handling",
            "Add authentication checks",
            "Create API documentation",
            "Write integration tests"
        ],
        "labels": ["Backend", "API", "High Priority", "Feature"],
        "priority": "high",
        "timeEstimate": 40,
        "dependencies": ["card-003", "card-004"]
    },
    "card-006": {
        "description": """## Overview
Create comprehensive input validation middleware to ensure data integrity and security.

## Validation Strategy

### Validation Library
Use Joi or Yup for schema validation with custom rules.

### Validation Schemas

#### Todo Creation Schema
```javascript
const createTodoSchema = {
    title: Joi.string().min(1).max(255).required(),
    description: Joi.string().max(5000).optional(),
    priority: Joi.string().valid('low', 'medium', 'high', 'urgent').optional(),
    dueDate: Joi.date().iso().min('now').optional(),
    categoryIds: Joi.array().items(Joi.string().uuid()).optional(),
    tagIds: Joi.array().items(Joi.string().uuid()).optional(),
    parentId: Joi.string().uuid().optional()
};
```

#### User Registration Schema
```javascript
const registerSchema = {
    email: Joi.string().email().required(),
    password: Joi.string()
        .min(8)
        .pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])/)
        .required(),
    fullName: Joi.string().min(2).max(100).required()
};
```

### Validation Rules

1. **String Validation**
   - Trim whitespace
   - HTML sanitization
   - SQL injection prevention
   - XSS prevention

2. **Date Validation**
   - ISO 8601 format
   - Future dates for due dates
   - Timezone handling

3. **Array Validation**
   - Maximum items limit
   - Unique values
   - Valid references

4. **Custom Validators**
   - Email uniqueness
   - Parent todo existence
   - Category ownership
   - Business rule validation

### Error Response Format
```json
{
    "error": "Validation Error",
    "message": "Invalid input data",
    "details": [
        {
            "field": "title",
            "message": "Title is required"
        },
        {
            "field": "dueDate",
            "message": "Due date must be in the future"
        }
    ]
}
```

## Security Measures
- Input sanitization
- Type coercion prevention
- Maximum payload size
- Nested object depth limit
- Array size limits
""",
        "subtasks": [
            "Install validation library (Joi/Yup)",
            "Create validation schemas directory",
            "Implement todo validation schemas",
            "Create user validation schemas",
            "Add custom validation rules",
            "Create validation middleware",
            "Implement error formatter",
            "Add input sanitization",
            "Create reusable validators",
            "Add async validation support",
            "Implement file upload validation",
            "Write validation tests",
            "Document validation rules"
        ],
        "labels": ["Backend", "Security", "Feature"],
        "priority": "medium",
        "timeEstimate": 24,
        "dependencies": ["card-005"]
    },
    "card-007": {
        "description": """## Overview
Implement robust error handling throughout the application for better debugging and user experience.

## Error Handling Architecture

### Error Types
```typescript
class AppError extends Error {
    statusCode: number;
    isOperational: boolean;
    
    constructor(message: string, statusCode: number) {
        super(message);
        this.statusCode = statusCode;
        this.isOperational = true;
    }
}

class ValidationError extends AppError {
    constructor(message: string) {
        super(message, 400);
    }
}

class AuthenticationError extends AppError {
    constructor(message: string = 'Not authenticated') {
        super(message, 401);
    }
}

class AuthorizationError extends AppError {
    constructor(message: string = 'Not authorized') {
        super(message, 403);
    }
}

class NotFoundError extends AppError {
    constructor(resource: string) {
        super(`${resource} not found`, 404);
    }
}
```

### Global Error Handler
```typescript
const errorHandler = (err: Error, req: Request, res: Response, next: NextFunction) => {
    let error = { ...err };
    error.message = err.message;

    // Log error
    logger.error({
        err,
        request: req.url,
        method: req.method,
        ip: req.ip
    });

    // Mongoose bad ObjectId
    if (err.name === 'CastError') {
        const message = 'Resource not found';
        error = new NotFoundError(message);
    }

    // Mongoose duplicate key
    if (err.code === 11000) {
        const message = 'Duplicate field value entered';
        error = new ValidationError(message);
    }

    // Mongoose validation error
    if (err.name === 'ValidationError') {
        const message = Object.values(err.errors).map(val => val.message).join(', ');
        error = new ValidationError(message);
    }

    res.status(error.statusCode || 500).json({
        success: false,
        error: {
            message: error.message || 'Server Error',
            ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
        }
    });
};
```

### Error Logging
- Structured logging with Winston
- Error categorization
- Stack trace capture
- Request context
- User information
- Performance impact

### Client Error Handling
```typescript
class ErrorBoundary extends React.Component {
    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        logger.error('React error boundary', { error, errorInfo });
        // Send to error tracking service
    }
}
```

## Monitoring Integration
- Sentry/Rollbar integration
- Error alerting
- Error analytics
- Performance monitoring
""",
        "subtasks": [
            "Create custom error classes",
            "Implement global error handler middleware",
            "Set up Winston logger",
            "Add error logging with context",
            "Create async error wrapper",
            "Implement error response formatter",
            "Add Sentry integration",
            "Create error tracking dashboard",
            "Add error recovery mechanisms",
            "Implement circuit breaker pattern",
            "Create error notification system",
            "Write error handling tests",
            "Document error codes"
        ],
        "labels": ["Backend", "Infrastructure", "Feature"],
        "priority": "medium",
        "timeEstimate": 16,
        "dependencies": ["card-005"]
    },
    "card-008": {
        "description": """## Overview
Set up a modern frontend application with React, TypeScript, and a scalable architecture.

## Frontend Architecture

### Technology Stack
- **Framework**: React 18+
- **Language**: TypeScript 5+
- **State Management**: Redux Toolkit / Zustand
- **Routing**: React Router v6
- **Styling**: Tailwind CSS / Styled Components
- **Build Tool**: Vite
- **Testing**: Jest + React Testing Library

### Project Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   ├── todos/
│   │   ├── auth/
│   │   └── layout/
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Login.tsx
│   │   └── Register.tsx
│   ├── hooks/
│   │   ├── useTodos.ts
│   │   ├── useAuth.ts
│   │   └── useDebounce.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── auth.service.ts
│   │   └── todo.service.ts
│   ├── store/
│   │   ├── index.ts
│   │   ├── auth.slice.ts
│   │   └── todo.slice.ts
│   ├── types/
│   │   └── index.ts
│   ├── utils/
│   │   └── helpers.ts
│   └── App.tsx
├── public/
├── index.html
└── vite.config.ts
```

### Core Features
1. **Routing Setup**
   - Public routes
   - Protected routes
   - Route guards
   - Lazy loading

2. **State Management**
   - Global state for auth
   - Todo state management
   - Persistent state
   - Optimistic updates

3. **API Integration**
   - Axios setup
   - Request interceptors
   - Error handling
   - Loading states

4. **Component Library**
   - Reusable components
   - Storybook setup
   - Component documentation
   - Accessibility

5. **Performance**
   - Code splitting
   - Lazy loading
   - Memo optimization
   - Virtual scrolling

### Development Experience
- Hot Module Replacement
- TypeScript strict mode
- ESLint + Prettier
- Pre-commit hooks
- Component generators
""",
        "subtasks": [
            "Initialize React app with Vite",
            "Configure TypeScript with strict mode",
            "Set up React Router v6",
            "Configure state management solution",
            "Set up Tailwind CSS or styling solution",
            "Create base component structure",
            "Set up API service layer",
            "Configure Axios with interceptors",
            "Create authentication context",
            "Set up route guards",
            "Configure environment variables",
            "Set up Storybook",
            "Create component library",
            "Configure testing environment"
        ],
        "labels": ["Frontend", "High Priority", "Infrastructure"],
        "priority": "high",
        "timeEstimate": 24,
        "dependencies": ["card-001"]
    },
    "card-009": {
        "description": """## Overview
Design comprehensive UI/UX mockups for all Todo App screens with modern, accessible interfaces.

## Design Requirements

### Design System
1. **Color Palette**
   - Primary: Blue (#3B82F6)
   - Secondary: Purple (#8B5CF6)
   - Success: Green (#10B981)
   - Warning: Yellow (#F59E0B)
   - Error: Red (#EF4444)
   - Neutrals: Gray scale

2. **Typography**
   - Headings: Inter/Poppins
   - Body: Inter/Roboto
   - Monospace: Fira Code

3. **Spacing System**
   - Base unit: 4px
   - Scale: 4, 8, 12, 16, 24, 32, 48, 64

### Screens to Design

#### 1. Dashboard
- Todo list view
- Quick add form
- Filters sidebar
- Stats overview
- Calendar widget

#### 2. Todo List View
- List/Grid toggle
- Sort options
- Bulk actions
- Infinite scroll
- Empty states

#### 3. Todo Detail Modal
- Edit form
- Subtasks
- Comments
- Activity log
- Attachments

#### 4. Add/Edit Todo Form
- Title input
- Rich text editor
- Date picker
- Priority selector
- Category/Tag selector
- Validation states

#### 5. Authentication Screens
- Login form
- Registration form
- Password reset
- Email verification
- Two-factor auth

#### 6. User Profile
- Profile information
- Settings
- Preferences
- Security options
- API tokens

### Responsive Design
- Mobile first approach
- Breakpoints: 640px, 768px, 1024px, 1280px
- Touch-friendly interfaces
- Progressive disclosure

### Accessibility Requirements
- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- High contrast mode
- Focus indicators
- ARIA labels

### Interactive Elements
- Hover states
- Active states
- Loading states
- Error states
- Success feedback
- Transitions

### Dark Mode
- Separate color palette
- Smooth transitions
- System preference detection
- Manual toggle
""",
        "subtasks": [
            "Create design system documentation",
            "Design color palette and typography",
            "Create component library in Figma",
            "Design dashboard layout",
            "Create todo list view variations",
            "Design todo detail modal",
            "Create add/edit form designs",
            "Design authentication screens",
            "Create user profile screens",
            "Design mobile responsive versions",
            "Create dark mode variations",
            "Design loading and empty states",
            "Create interactive prototypes",
            "Document design decisions"
        ],
        "labels": ["UI/UX", "Frontend", "Feature"],
        "priority": "medium",
        "timeEstimate": 32,
        "dependencies": []
    },
    "card-010": {
        "description": """## Overview
Build the main TodoList component that displays todos with filtering, sorting, and pagination.

## Component Architecture

### TodoList Component
```typescript
interface TodoListProps {
    todos: Todo[];
    loading: boolean;
    error: Error | null;
    onTodoClick: (todo: Todo) => void;
    onTodoUpdate: (id: string, updates: Partial<Todo>) => void;
    onTodoDelete: (id: string) => void;
    onSort: (field: string, order: 'asc' | 'desc') => void;
}
```

### Features
1. **Display Modes**
   - List view (default)
   - Grid view
   - Compact view
   - Calendar view

2. **Todo Item Display**
   - Checkbox for completion
   - Title and description
   - Priority indicator
   - Due date with overdue styling
   - Category/tag badges
   - Progress bar for subtasks

3. **Sorting Options**
   - Due date
   - Priority
   - Created date
   - Alphabetical
   - Custom order (drag & drop)

4. **Filtering**
   - By status
   - By priority
   - By category
   - By date range
   - By tags

5. **Bulk Actions**
   - Select all/none
   - Bulk complete
   - Bulk delete
   - Bulk categorize

6. **Performance**
   - Virtual scrolling for large lists
   - Memo optimization
   - Lazy loading
   - Skeleton loading

### Component Structure
```
TodoList/
├── TodoList.tsx
├── TodoListItem.tsx
├── TodoListHeader.tsx
├── TodoListFilters.tsx
├── TodoListBulkActions.tsx
├── TodoListEmpty.tsx
├── TodoListSkeleton.tsx
└── TodoList.module.css
```

### State Management
- Local state for UI (view mode, selection)
- Global state for todos
- Optimistic updates
- Error recovery
""",
        "subtasks": [
            "Create TodoList component structure",
            "Implement list rendering logic",
            "Add TodoListItem component",
            "Create priority indicators",
            "Implement due date display",
            "Add checkbox functionality",
            "Create sorting dropdown",
            "Implement filter sidebar",
            "Add bulk selection logic",
            "Create empty state component",
            "Add loading skeleton",
            "Implement virtual scrolling",
            "Add drag and drop sorting",
            "Write component tests"
        ],
        "labels": ["Frontend", "Component", "High Priority", "Feature"],
        "priority": "high",
        "timeEstimate": 24,
        "dependencies": ["card-008", "card-009"]
    },
    "card-011": {
        "description": """## Overview
Create an interactive TodoItem component with all necessary actions and states.

## Component Design

### TodoItem Component
```typescript
interface TodoItemProps {
    todo: Todo;
    isSelected: boolean;
    isEditing: boolean;
    onToggleComplete: (id: string) => void;
    onEdit: (id: string) => void;
    onDelete: (id: string) => void;
    onSelect: (id: string) => void;
    onDragStart: (e: DragEvent, todo: Todo) => void;
    onDragEnd: (e: DragEvent) => void;
}
```

### Visual Features
1. **Layout**
   - Checkbox on left
   - Content in center
   - Actions on right
   - Expandable description
   - Subtask progress

2. **Interactive Elements**
   - Hover effects
   - Click to expand
   - Double-click to edit
   - Right-click menu
   - Keyboard shortcuts

3. **Status Indicators**
   - Completion state
   - Overdue warning
   - Priority badge
   - Category tags
   - Progress bar

4. **Actions Menu**
   - Edit
   - Delete
   - Duplicate
   - Convert to subtask
   - Share
   - Archive

### States
- Default
- Hover
- Selected
- Editing
- Completed
- Overdue
- Dragging

### Animations
- Smooth checkbox transition
- Expand/collapse animation
- Delete animation
- Reorder animation
- Completion celebration

### Accessibility
- Keyboard navigation
- Screen reader announcements
- Focus management
- ARIA attributes
""",
        "subtasks": [
            "Create TodoItem component base",
            "Implement checkbox with animation",
            "Add title and description display",
            "Create priority badge component",
            "Implement due date display",
            "Add category tag display",
            "Create actions dropdown menu",
            "Implement expand/collapse logic",
            "Add hover and active states",
            "Create inline edit mode",
            "Implement drag handle",
            "Add keyboard shortcuts",
            "Create completion animation",
            "Write component tests"
        ],
        "labels": ["Frontend", "Component", "High Priority", "Feature"],
        "priority": "high",
        "timeEstimate": 24,
        "dependencies": ["card-010"]
    },
    "card-012": {
        "description": """## Overview
Build a comprehensive form component for creating and editing todos with rich features.

## Form Design

### AddTodoForm Component
```typescript
interface AddTodoFormProps {
    initialData?: Partial<Todo>;
    onSubmit: (data: TodoFormData) => Promise<void>;
    onCancel: () => void;
    mode: 'create' | 'edit';
}

interface TodoFormData {
    title: string;
    description?: string;
    priority: Priority;
    dueDate?: Date;
    categoryIds: string[];
    tagIds: string[];
    parentId?: string;
    attachments?: File[];
}
```

### Form Fields

1. **Title Field**
   - Auto-focus on mount
   - Character counter
   - Validation feedback
   - Clear button

2. **Description Field**
   - Rich text editor (Markdown)
   - Toolbar for formatting
   - Preview mode
   - Emoji picker
   - @mentions

3. **Priority Selector**
   - Visual indicators
   - Keyboard navigation
   - Default: Medium

4. **Due Date Picker**
   - Calendar widget
   - Time selection
   - Quick options (Today, Tomorrow, Next Week)
   - Timezone support

5. **Category/Tag Selection**
   - Multi-select dropdown
   - Create new inline
   - Color indicators
   - Search functionality

6. **Attachments**
   - Drag & drop zone
   - File preview
   - Progress upload
   - Size validation

### Features
- Real-time validation
- Auto-save draft
- Keyboard shortcuts (Ctrl+Enter to save)
- Form templates
- Smart suggestions
- Voice input

### Validation
- Required field indicators
- Inline error messages
- Submit button state
- Validation on blur
- Async validation

### UX Enhancements
- Loading states
- Success feedback
- Error recovery
- Unsaved changes warning
- Mobile optimized
""",
        "subtasks": [
            "Create form component structure",
            "Implement controlled form inputs",
            "Add title field with validation",
            "Integrate rich text editor",
            "Create priority selector component",
            "Implement date/time picker",
            "Build category multi-select",
            "Add tag management",
            "Create file upload zone",
            "Implement form validation",
            "Add auto-save functionality",
            "Create form templates",
            "Add keyboard shortcuts",
            "Write form tests"
        ],
        "labels": ["Frontend", "Component", "High Priority", "Feature"],
        "priority": "high",
        "timeEstimate": 32,
        "dependencies": ["card-008", "card-009"]
    },
    "card-013": {
        "description": """## Overview
Create a robust API client service layer for seamless frontend-backend communication.

## API Client Architecture

### Base API Configuration
```typescript
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

class ApiClient {
    private instance: AxiosInstance;
    private token: string | null = null;

    constructor(baseURL: string) {
        this.instance = axios.create({
            baseURL,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        this.setupInterceptors();
    }

    private setupInterceptors(): void {
        // Request interceptor
        this.instance.interceptors.request.use(
            (config) => {
                if (this.token) {
                    config.headers.Authorization = `Bearer ${this.token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Response interceptor
        this.instance.interceptors.response.use(
            (response) => response.data,
            async (error) => {
                if (error.response?.status === 401) {
                    await this.refreshToken();
                    return this.instance(error.config);
                }
                return Promise.reject(error);
            }
        );
    }
}
```

### Service Layer

#### TodoService
```typescript
class TodoService {
    constructor(private api: ApiClient) {}

    async getTodos(params?: TodoQueryParams): Promise<PaginatedResponse<Todo>> {
        return this.api.get('/todos', { params });
    }

    async getTodo(id: string): Promise<Todo> {
        return this.api.get(`/todos/${id}`);
    }

    async createTodo(data: CreateTodoDto): Promise<Todo> {
        return this.api.post('/todos', data);
    }

    async updateTodo(id: string, data: UpdateTodoDto): Promise<Todo> {
        return this.api.put(`/todos/${id}`, data);
    }

    async deleteTodo(id: string): Promise<void> {
        return this.api.delete(`/todos/${id}`);
    }

    async bulkUpdate(ids: string[], data: Partial<Todo>): Promise<void> {
        return this.api.post('/todos/bulk', { ids, data });
    }
}
```

### Features
1. **Request Management**
   - Request cancellation
   - Request deduplication
   - Retry logic
   - Timeout handling

2. **Response Handling**
   - Type safety
   - Error transformation
   - Response caching
   - Data normalization

3. **Authentication**
   - Token management
   - Auto-refresh
   - Logout on 401
   - Secure storage

4. **Performance**
   - Request batching
   - Response caching
   - Concurrent requests
   - Progressive loading

### Error Handling
```typescript
class ApiError extends Error {
    constructor(
        public statusCode: number,
        public message: string,
        public errors?: any[]
    ) {
        super(message);
    }
}
```

### Hooks Integration
```typescript
function useTodos() {
    const [todos, setTodos] = useState<Todo[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const fetchTodos = useCallback(async (params?: TodoQueryParams) => {
        setLoading(true);
        try {
            const response = await todoService.getTodos(params);
            setTodos(response.data);
        } catch (err) {
            setError(err as Error);
        } finally {
            setLoading(false);
        }
    }, []);

    return { todos, loading, error, fetchTodos };
}
```
""",
        "subtasks": [
            "Set up Axios instance",
            "Create base API client class",
            "Implement request interceptors",
            "Add response interceptors",
            "Create TodoService class",
            "Implement all CRUD methods",
            "Add AuthService class",
            "Create error handling utilities",
            "Implement request cancellation",
            "Add response caching",
            "Create TypeScript types",
            "Implement retry logic",
            "Add request queuing",
            "Write service tests"
        ],
        "labels": ["Frontend", "API", "High Priority", "Infrastructure"],
        "priority": "high",
        "timeEstimate": 16,
        "dependencies": ["card-008"]
    },
    "card-014": {
        "description": """## Overview
Connect all frontend components to the backend API with proper state management and error handling.

## Integration Architecture

### State Management Setup
```typescript
// Redux Toolkit Slice
const todoSlice = createSlice({
    name: 'todos',
    initialState: {
        items: [],
        loading: false,
        error: null,
        filters: {},
        pagination: {}
    },
    reducers: {
        // Optimistic updates
        addTodoOptimistic: (state, action) => {
            state.items.unshift({ ...action.payload, pending: true });
        },
        updateTodoOptimistic: (state, action) => {
            const todo = state.items.find(t => t.id === action.payload.id);
            if (todo) Object.assign(todo, action.payload);
        }
    },
    extraReducers: (builder) => {
        // Async thunks
        builder
            .addCase(fetchTodos.pending, (state) => {
                state.loading = true;
            })
            .addCase(fetchTodos.fulfilled, (state, action) => {
                state.items = action.payload.data;
                state.pagination = action.payload.pagination;
                state.loading = false;
            })
            .addCase(fetchTodos.rejected, (state, action) => {
                state.error = action.error.message;
                state.loading = false;
            });
    }
});
```

### Component Integration

#### TodoList Integration
```typescript
function TodoListContainer() {
    const dispatch = useAppDispatch();
    const { items, loading, error } = useAppSelector(state => state.todos);
    
    useEffect(() => {
        dispatch(fetchTodos());
    }, [dispatch]);

    const handleUpdate = useCallback(async (id: string, updates: Partial<Todo>) => {
        // Optimistic update
        dispatch(updateTodoOptimistic({ id, ...updates }));
        
        try {
            await dispatch(updateTodo({ id, updates })).unwrap();
        } catch (error) {
            // Revert on error
            dispatch(fetchTodos());
            toast.error('Failed to update todo');
        }
    }, [dispatch]);

    return (
        <TodoList
            todos={items}
            loading={loading}
            error={error}
            onUpdate={handleUpdate}
        />
    );
}
```

### Real-time Updates
```typescript
// WebSocket integration
useEffect(() => {
    const ws = new WebSocket(WS_URL);
    
    ws.onmessage = (event) => {
        const { type, payload } = JSON.parse(event.data);
        
        switch (type) {
            case 'TODO_CREATED':
                dispatch(addTodo(payload));
                break;
            case 'TODO_UPDATED':
                dispatch(updateTodo(payload));
                break;
            case 'TODO_DELETED':
                dispatch(removeTodo(payload.id));
                break;
        }
    };

    return () => ws.close();
}, [dispatch]);
```

### Error Handling
```typescript
// Global error boundary
function ErrorFallback({ error, resetErrorBoundary }) {
    return (
        <div role="alert">
            <p>Something went wrong:</p>
            <pre>{error.message}</pre>
            <button onClick={resetErrorBoundary}>Try again</button>
        </div>
    );
}

// API error handling
const handleApiError = (error: any) => {
    if (error.response?.status === 401) {
        // Redirect to login
    } else if (error.response?.status === 403) {
        toast.error('You don\'t have permission to do that');
    } else if (error.response?.status === 404) {
        toast.error('Resource not found');
    } else {
        toast.error('An unexpected error occurred');
    }
};
```

### Performance Optimizations
1. **Data Caching**
   - React Query integration
   - Stale-while-revalidate
   - Background refetching

2. **Optimistic Updates**
   - Immediate UI feedback
   - Rollback on error
   - Conflict resolution

3. **Batch Operations**
   - Debounced updates
   - Request queuing
   - Bulk actions

### Testing Strategy
- Integration tests
- API mocking
- Error scenario testing
- Performance testing
""",
        "subtasks": [
            "Set up Redux store configuration",
            "Create todo slice with actions",
            "Implement async thunks",
            "Connect TodoList to store",
            "Wire up AddTodo form",
            "Implement optimistic updates",
            "Add error handling logic",
            "Set up WebSocket connection",
            "Implement real-time updates",
            "Add loading states",
            "Create error boundaries",
            "Implement data caching",
            "Add offline support",
            "Write integration tests"
        ],
        "labels": ["Frontend", "Integration", "High Priority", "Feature"],
        "priority": "high",
        "timeEstimate": 32,
        "dependencies": ["card-010", "card-011", "card-012", "card-013", "card-005"]
    },
    "card-015": {
        "description": """## Overview
Implement complete user authentication system with registration, login, and session management.

## Authentication Flow

### Registration Process
1. User fills registration form
2. Client-side validation
3. Check email availability
4. Submit to backend
5. Hash password with bcrypt
6. Create user record
7. Send verification email
8. Show success message

### Login Process
1. User enters credentials
2. Validate input
3. Check credentials
4. Generate JWT tokens
5. Set refresh token cookie
6. Return access token
7. Redirect to dashboard

### Token Management
```typescript
interface AuthTokens {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
}

class AuthManager {
    private accessToken: string | null = null;
    private refreshTimer: NodeJS.Timeout | null = null;

    setTokens(tokens: AuthTokens): void {
        this.accessToken = tokens.accessToken;
        
        // Schedule refresh before expiry
        const refreshTime = (tokens.expiresIn - 60) * 1000;
        this.refreshTimer = setTimeout(() => {
            this.refreshAccessToken();
        }, refreshTime);
    }

    async refreshAccessToken(): Promise<void> {
        try {
            const response = await api.post('/auth/refresh');
            this.setTokens(response.data);
        } catch (error) {
            this.logout();
        }
    }

    logout(): void {
        this.accessToken = null;
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }
        // Clear cookies and redirect
    }
}
```

### Security Features
1. **Password Requirements**
   - Minimum 8 characters
   - Mixed case letters
   - Numbers and symbols
   - Not in common passwords list

2. **Account Security**
   - Email verification
   - Password reset flow
   - Account lockout
   - Login history
   - Device management

3. **Session Security**
   - Secure httpOnly cookies
   - CSRF protection
   - Session invalidation
   - Concurrent session limits

### OAuth Integration
```typescript
// Google OAuth
async function handleGoogleLogin() {
    const { data } = await api.get('/auth/google');
    window.location.href = data.authUrl;
}

// OAuth callback handler
async function handleOAuthCallback(code: string) {
    const { data } = await api.post('/auth/google/callback', { code });
    authManager.setTokens(data.tokens);
    navigate('/dashboard');
}
```

### Protected Routes
```typescript
function ProtectedRoute({ children }: { children: ReactNode }) {
    const { isAuthenticated, loading } = useAuth();
    
    if (loading) return <LoadingSpinner />;
    if (!isAuthenticated) return <Navigate to="/login" />;
    
    return <>{children}</>;
}
```
""",
        "subtasks": [
            "Create user registration endpoint",
            "Implement password hashing",
            "Add email verification system",
            "Create login endpoint",
            "Implement JWT generation",
            "Add refresh token logic",
            "Create logout endpoint",
            "Implement password reset",
            "Add OAuth providers",
            "Create auth middleware",
            "Build login form UI",
            "Build registration form UI",
            "Implement protected routes",
            "Add session management",
            "Write auth tests"
        ],
        "labels": ["Backend", "Frontend", "Security", "High Priority", "Feature"],
        "priority": "high",
        "timeEstimate": 40,
        "dependencies": ["card-005"]
    },
    "card-016": {
        "description": """## Overview
Implement comprehensive testing strategy covering unit tests, integration tests, and end-to-end tests.

## Testing Architecture

### Backend Testing

#### Unit Tests
```typescript
// Todo Model Tests
describe('Todo Model', () => {
    describe('validation', () => {
        it('should require a title', async () => {
            const todo = new Todo({ title: '' });
            await expect(todo.validate()).rejects.toThrow('Title is required');
        });

        it('should validate priority enum', async () => {
            const todo = new Todo({ title: 'Test', priority: 'invalid' });
            await expect(todo.validate()).rejects.toThrow('Invalid priority');
        });
    });

    describe('business logic', () => {
        it('should set completedAt when marked complete', () => {
            const todo = new Todo({ title: 'Test' });
            todo.markComplete();
            expect(todo.completedAt).toBeInstanceOf(Date);
            expect(todo.status).toBe('completed');
        });
    });
});
```

#### Integration Tests
```typescript
// API Endpoint Tests
describe('POST /api/todos', () => {
    it('should create a new todo', async () => {
        const response = await request(app)
            .post('/api/todos')
            .set('Authorization', `Bearer ${token}`)
            .send({
                title: 'Test Todo',
                priority: 'high'
            });

        expect(response.status).toBe(201);
        expect(response.body.data).toMatchObject({
            title: 'Test Todo',
            priority: 'high'
        });
    });

    it('should validate required fields', async () => {
        const response = await request(app)
            .post('/api/todos')
            .set('Authorization', `Bearer ${token}`)
            .send({});

        expect(response.status).toBe(400);
        expect(response.body.error).toContain('Title is required');
    });
});
```

### Frontend Testing

#### Component Tests
```typescript
// TodoList Component Tests
describe('TodoList', () => {
    it('renders todos correctly', () => {
        const todos = [
            { id: '1', title: 'Test 1', status: 'pending' },
            { id: '2', title: 'Test 2', status: 'completed' }
        ];

        render(<TodoList todos={todos} />);
        
        expect(screen.getByText('Test 1')).toBeInTheDocument();
        expect(screen.getByText('Test 2')).toBeInTheDocument();
    });

    it('calls onToggle when checkbox clicked', async () => {
        const onToggle = jest.fn();
        const todos = [{ id: '1', title: 'Test', status: 'pending' }];

        render(<TodoList todos={todos} onToggle={onToggle} />);
        
        await userEvent.click(screen.getByRole('checkbox'));
        expect(onToggle).toHaveBeenCalledWith('1');
    });
});
```

#### Hook Tests
```typescript
// useTodos Hook Tests
describe('useTodos', () => {
    it('fetches todos on mount', async () => {
        const { result, waitForNextUpdate } = renderHook(() => useTodos());

        expect(result.current.loading).toBe(true);
        
        await waitForNextUpdate();
        
        expect(result.current.loading).toBe(false);
        expect(result.current.todos).toHaveLength(2);
    });
});
```

### E2E Testing
```typescript
// Cypress E2E Tests
describe('Todo App E2E', () => {
    beforeEach(() => {
        cy.login('test@example.com', 'password');
    });

    it('creates a new todo', () => {
        cy.visit('/');
        cy.get('[data-testid="add-todo-button"]').click();
        
        cy.get('[data-testid="todo-title"]').type('New Todo');
        cy.get('[data-testid="todo-priority"]').select('high');
        cy.get('[data-testid="submit-button"]').click();
        
        cy.contains('New Todo').should('be.visible');
        cy.get('[data-testid="priority-badge"]').should('contain', 'High');
    });
});
```

### Testing Strategy
1. **Coverage Goals**
   - Unit tests: 80%+
   - Integration tests: Critical paths
   - E2E tests: User journeys

2. **Test Pyramid**
   - Many unit tests
   - Some integration tests
   - Few E2E tests

3. **Continuous Testing**
   - Pre-commit hooks
   - CI/CD pipeline
   - Automated reports
""",
        "subtasks": [
            "Set up Jest for backend",
            "Configure testing database",
            "Write model unit tests",
            "Write service unit tests",
            "Create API integration tests",
            "Set up React Testing Library",
            "Write component unit tests",
            "Test custom hooks",
            "Test Redux actions/reducers",
            "Set up Cypress",
            "Write E2E test scenarios",
            "Configure test coverage",
            "Set up CI test pipeline",
            "Create test documentation"
        ],
        "labels": ["Testing", "Quality", "High Priority"],
        "priority": "high",
        "timeEstimate": 32,
        "dependencies": ["card-014", "card-015"]
    },
    "card-017": {
        "description": """## Overview
Deploy the Todo App to production with proper CI/CD pipeline, monitoring, and scaling setup.

## Deployment Architecture

### Infrastructure Setup
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
    ports:
      - "3000:3000"
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    environment:
      - REACT_APP_API_URL=${API_URL}
    ports:
      - "80:80"

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=todoapp
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "443:443"
    depends_on:
      - backend
      - frontend
```

### CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm test
      - run: npm run test:e2e

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker images
        run: |
          docker build -t todoapp-backend ./backend
          docker build -t todoapp-frontend ./frontend
      - name: Push to registry
        run: |
          docker push todoapp-backend
          docker push todoapp-frontend

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          ssh ${{ secrets.PROD_SERVER }} 'docker-compose pull && docker-compose up -d'
```

### Monitoring Setup
1. **Application Monitoring**
   - Sentry for error tracking
   - New Relic for performance
   - Custom metrics dashboard

2. **Infrastructure Monitoring**
   - CloudWatch/Datadog
   - Uptime monitoring
   - SSL certificate monitoring

3. **Logging**
   - Centralized logging (ELK)
   - Log retention policies
   - Alert rules

### Security Measures
1. **SSL/TLS**
   - Let's Encrypt certificates
   - Auto-renewal
   - Strong cipher suites

2. **Security Headers**
   - CSP
   - HSTS
   - X-Frame-Options

3. **Secrets Management**
   - Environment variables
   - AWS Secrets Manager
   - Rotation policies

### Scaling Strategy
1. **Horizontal Scaling**
   - Load balancer
   - Multiple app instances
   - Database read replicas

2. **Caching**
   - Redis for sessions
   - CDN for static assets
   - API response caching

3. **Performance**
   - Image optimization
   - Code splitting
   - Lazy loading

### Backup & Recovery
1. **Database Backups**
   - Daily automated backups
   - Point-in-time recovery
   - Offsite storage

2. **Disaster Recovery**
   - Recovery procedures
   - RTO/RPO targets
   - Regular drills
""",
        "subtasks": [
            "Set up production servers",
            "Configure Docker images",
            "Create docker-compose config",
            "Set up CI/CD pipeline",
            "Configure GitHub Actions",
            "Set up container registry",
            "Configure Nginx reverse proxy",
            "Set up SSL certificates",
            "Configure monitoring tools",
            "Set up logging infrastructure",
            "Implement backup strategy",
            "Create deployment scripts",
            "Configure auto-scaling",
            "Set up CDN",
            "Create runbooks",
            "Performance testing"
        ],
        "labels": ["DevOps", "Infrastructure", "High Priority", "Deployment"],
        "priority": "high",
        "timeEstimate": 32,
        "dependencies": ["card-016"]
    }
}


async def create_all_cards():
    """Create all Todo App development cards"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🚀 Creating all Todo App development cards...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("✅ Connected to kanban-mcp")
            
            # 1. Find Task Master Test project
            print("\n📋 Finding Task Master Test project...")
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_projects",
                "page": 1,
                "perPage": 25
            })
            
            projects_data = json.loads(result.content[0].text)
            project_id = None
            board_id = None
            
            for project in projects_data["items"]:
                if project["name"] == "Task Master Test":
                    project_id = project["id"]
                    print(f"✅ Found project: {project['name']} (ID: {project_id})")
                    break
            
            if not project_id:
                print("❌ Task Master Test project not found!")
                return
            
            # Find the board
            if "boards" in projects_data.get("included", {}):
                for board in projects_data["included"]["boards"]:
                    if board["projectId"] == project_id:
                        board_id = board["id"]
                        print(f"✅ Found board: {board['name']} (ID: {board_id})")
                        break
            
            if not board_id:
                print("❌ No board found for Task Master Test!")
                return
            
            # 2. Clear existing cards
            print("\n🧹 Clearing existing cards...")
            try:
                # Get all lists first
                lists_result = await session.call_tool("mcp_kanban_list_manager", {
                    "action": "get_all",
                    "boardId": board_id
                })
                lists = json.loads(lists_result.content[0].text)
                
                # Get cards from each list
                for lst in lists:
                    try:
                        cards_result = await session.call_tool("mcp_kanban_card_manager", {
                            "action": "get_by_list",
                            "listId": lst["id"]
                        })
                        
                        if cards_result.content and cards_result.content[0].text:
                            try:
                                cards = json.loads(cards_result.content[0].text)
                                if isinstance(cards, list):
                                    for card in cards:
                                        await session.call_tool("mcp_kanban_card_manager", {
                                            "action": "delete",
                                            "cardId": card["id"]
                                        })
                                        print(f"  ✅ Deleted: {card.get('name', 'Unnamed')}")
                            except:
                                pass
                    except:
                        pass
            except Exception as e:
                print(f"  ⚠️  Error clearing cards: {str(e)}")
            
            # 3. Get lists
            print("\n📋 Getting lists...")
            backlog_list = None
            
            for lst in lists:
                if "BACKLOG" in lst["name"].upper():
                    backlog_list = lst
                    print(f"✅ Found list: {lst['name']} (ID: {lst['id']})")
                    break
            
            if not backlog_list:
                print("❌ No Backlog list found!")
                return
            
            # 4. Create labels first
            print("\n🏷️  Creating labels...")
            label_ids = {}
            
            for label_name, color in LABEL_COLORS.items():
                try:
                    # Try to create the label
                    result = await session.call_tool("mcp_kanban_label_manager", {
                        "action": "create",
                        "boardId": board_id,
                        "name": label_name,
                        "color": color
                    })
                    label = json.loads(result.content[0].text)
                    label_ids[label_name] = label["id"]
                    print(f"  ✅ Created label: {label_name}")
                except:
                    # Label might exist, try to get it
                    try:
                        labels_result = await session.call_tool("mcp_kanban_label_manager", {
                            "action": "get_all",
                            "boardId": board_id
                        })
                        labels = json.loads(labels_result.content[0].text)
                        
                        for existing_label in labels:
                            if existing_label["name"] == label_name:
                                label_ids[label_name] = existing_label["id"]
                                print(f"  ✅ Found existing label: {label_name}")
                                break
                    except:
                        print(f"  ❌ Could not create/find label: {label_name}")
            
            # 5. Create all cards
            print("\n📝 Creating cards...")
            created_count = 0
            card_id_map = {}
            
            for card_data in TODO_APP_DATA["cards"][:17]:  # Only first 17 cards
                print(f"\n[{created_count + 1}/17] Creating: {card_data['title']}")
                
                # Get enhanced description and subtasks
                enhanced = ENHANCED_CARDS.get(card_data["id"], {})
                description = enhanced.get("description", card_data["description"])
                subtasks = enhanced.get("subtasks", [])
                
                # Calculate due date
                # Parse due date string (e.g., "2 days" -> 2)
                due_date_str = card_data.get("dueDate", "7 days")
                due_days = int(due_date_str.split()[0]) if " day" in due_date_str else 7
                due_date = datetime.now() + timedelta(days=due_days)
                
                try:
                    # Create the card
                    result = await session.call_tool("mcp_kanban_card_manager", {
                        "action": "create",
                        "listId": backlog_list["id"],
                        "name": card_data["title"],
                        "description": description
                    })
                    
                    card = json.loads(result.content[0].text)
                    card_id = card["id"]
                    card_id_map[card_data["title"]] = card_id
                    print(f"  ✅ Created card ID: {card_id}")
                    
                    # Add labels
                    for label_name in enhanced.get("labels", card_data.get("labels", [])):
                        if label_name in label_ids:
                            try:
                                await session.call_tool("mcp_kanban_label_manager", {
                                    "action": "add_to_card",
                                    "cardId": card_id,
                                    "labelId": label_ids[label_name]
                                })
                                print(f"  ✅ Added label: {label_name}")
                            except Exception as e:
                                print(f"  ❌ Could not add label {label_name}: {str(e)}")
                    
                    # Create subtasks
                    if subtasks:
                        print(f"  📋 Creating {len(subtasks)} subtasks...")
                        for i, subtask_name in enumerate(subtasks[:10], 1):  # Limit to 10 subtasks
                            try:
                                await session.call_tool("mcp_kanban_task_manager", {
                                    "action": "create",
                                    "cardId": card_id,
                                    "name": subtask_name,
                                    "position": i
                                })
                            except:
                                pass
                        print(f"  ✅ Created subtasks")
                    
                    # Add time estimate and other details
                    time_estimate = enhanced.get("timeEstimate", 8)
                    priority = enhanced.get("priority", "medium")
                    
                    details_comment = f"""📊 **Task Details**
⏱️ **Time Estimate**: {time_estimate} hours
📅 **Due Date**: {due_date.strftime('%B %d, %Y')}
🎯 **Priority**: {priority.capitalize()}
👥 **Team Size**: 1-2 developers"""
                    
                    await session.call_tool("mcp_kanban_comment_manager", {
                        "action": "create",
                        "cardId": card_id,
                        "text": details_comment
                    })
                    
                    # Add dependencies if any
                    dependencies = enhanced.get("dependencies", [])
                    if dependencies:
                        dep_names = []
                        for dep_id in dependencies:
                            # Find the card with this ID
                            for c in TODO_APP_DATA["cards"]:
                                if c["id"] == dep_id:
                                    dep_names.append(c["title"])
                                    break
                        
                        if dep_names:
                            deps_comment = "🔗 **Dependencies**:\n" + "\n".join(f"- {name}" for name in dep_names)
                            await session.call_tool("mcp_kanban_comment_manager", {
                                "action": "create",
                                "cardId": card_id,
                                "text": deps_comment
                            })
                    
                    created_count += 1
                    
                except Exception as e:
                    print(f"  ❌ Error creating card: {str(e)}")
            
            print(f"\n✅ Successfully created {created_count}/17 cards!")
            
            # 6. Summary
            print("\n📊 Summary:")
            print(f"  - Cards created: {created_count}")
            print(f"  - Labels created: {len(label_ids)}")
            print(f"  - All cards in Backlog list")
            print("\n✨ Todo App project board is ready!")


if __name__ == "__main__":
    asyncio.run(create_all_cards())