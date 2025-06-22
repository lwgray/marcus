#!/usr/bin/env python3
"""
Create Todo App cards with moderate detail - simplified version
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

# Moderate card descriptions
MODERATE_CARDS = {
    "card-001": {
        "description": """## Project Setup
Initialize the Todo App project with proper structure and configuration.

**Key Tasks:**
- Create folder structure for frontend and backend
- Initialize package.json files
- Set up TypeScript configuration
- Configure ESLint and Prettier
- Create .env files for configuration

**Tech Stack:**
- Node.js + Express (Backend)
- React + TypeScript (Frontend)
- PostgreSQL (Database)""",
        "subtasks": [
            "Create project directory structure",
            "Initialize npm packages",
            "Configure TypeScript",
            "Set up linting tools",
            "Create environment files"
        ]
    },
    "card-002": {
        "description": """## Database Design
Design and implement the database schema for todos and users.

**Tables Required:**
- users (id, email, password_hash, created_at)
- todos (id, user_id, title, description, completed, created_at, updated_at)

**Considerations:**
- Use UUID for primary keys
- Add proper indexes for performance
- Include foreign key constraints""",
        "subtasks": [
            "Design database schema",
            "Create migration files",
            "Set up database indexes",
            "Add seed data"
        ]
    },
    "card-003": {
        "description": """## Todo Model Implementation
Create the Todo model with Sequelize ORM.

**Model Fields:**
- id (UUID)
- title (string, required)
- description (text, optional)
- completed (boolean, default: false)
- userId (foreign key)
- timestamps

**Methods:**
- CRUD operations
- Toggle completion status""",
        "subtasks": [
            "Define Todo model schema",
            "Add validation rules",
            "Create model methods",
            "Set up associations"
        ]
    },
    "card-004": {
        "description": """## Database Connection
Set up database connection and configuration.

**Requirements:**
- Connection pooling
- Environment-based config
- Error handling
- Connection health checks

**Tools:**
- Sequelize ORM
- pg driver
- dotenv for config""",
        "subtasks": [
            "Install database packages",
            "Configure Sequelize",
            "Set up connection pool",
            "Add error handling"
        ]
    },
    "card-005": {
        "description": """## REST API Endpoints
Implement CRUD API endpoints for todos.

**Endpoints:**
- GET /api/todos - List all todos
- POST /api/todos - Create new todo
- PUT /api/todos/:id - Update todo
- DELETE /api/todos/:id - Delete todo
- PATCH /api/todos/:id/toggle - Toggle completion

**Features:**
- Pagination for list endpoint
- Request validation
- Proper HTTP status codes""",
        "subtasks": [
            "Create todo controller",
            "Implement GET endpoints",
            "Implement POST endpoint",
            "Implement PUT/DELETE endpoints",
            "Add pagination support"
        ]
    },
    "card-006": {
        "description": """## Input Validation
Add validation middleware for API requests.

**Validation Rules:**
- Title: required, min 1 char, max 255 chars
- Description: optional, max 1000 chars
- Validate UUIDs for ID parameters

**Tools:**
- express-validator
- Custom validation middleware""",
        "subtasks": [
            "Install validation packages",
            "Create validation rules",
            "Add validation middleware",
            "Test validation"
        ]
    },
    "card-007": {
        "description": """## Error Handling
Implement centralized error handling.

**Requirements:**
- Global error handler middleware
- Custom error classes
- Proper error logging
- Client-friendly error messages

**Error Types:**
- Validation errors (400)
- Not found errors (404)
- Server errors (500)""",
        "subtasks": [
            "Create error handler middleware",
            "Define custom error classes",
            "Add error logging",
            "Test error scenarios"
        ]
    },
    "card-008": {
        "description": """## Frontend Setup
Initialize React application with TypeScript.

**Setup Tasks:**
- Create React App with TypeScript template
- Configure folder structure
- Set up routing
- Add CSS framework (Tailwind)
- Configure API client

**Structure:**
- components/
- pages/
- services/
- hooks/
- utils/""",
        "subtasks": [
            "Create React app",
            "Set up folder structure",
            "Configure routing",
            "Add Tailwind CSS",
            "Set up Axios"
        ]
    },
    "card-009": {
        "description": """## UI Design
Create UI mockups and design system.

**Design Elements:**
- Color scheme
- Typography
- Component library
- Responsive layouts
- Dark mode support

**Key Screens:**
- Todo list view
- Add/Edit todo form
- Empty state
- Loading states""",
        "subtasks": [
            "Define color palette",
            "Create component designs",
            "Design responsive layouts",
            "Create loading/empty states"
        ]
    },
    "card-010": {
        "description": """## TodoList Component
Build the main todo list component.

**Features:**
- Display list of todos
- Show completion status
- Click to view details
- Empty state when no todos
- Loading state

**Props:**
- todos: Todo[]
- onTodoClick: (id) => void
- loading: boolean""",
        "subtasks": [
            "Create component structure",
            "Add todo rendering",
            "Implement click handlers",
            "Add empty/loading states",
            "Style component"
        ]
    },
    "card-011": {
        "description": """## TodoItem Component
Create individual todo item component.

**Features:**
- Display todo details
- Toggle completion checkbox
- Edit/Delete buttons
- Hover effects
- Completed styling

**Props:**
- todo: Todo
- onToggle: (id) => void
- onEdit: (id) => void
- onDelete: (id) => void""",
        "subtasks": [
            "Create component",
            "Add checkbox functionality",
            "Implement action buttons",
            "Add styling and animations"
        ]
    },
    "card-012": {
        "description": """## AddTodo Form
Build form for creating new todos.

**Features:**
- Title input (required)
- Description textarea (optional)
- Submit button
- Form validation
- Clear form after submit

**Validation:**
- Title required
- Max length limits
- Show validation errors""",
        "subtasks": [
            "Create form component",
            "Add form controls",
            "Implement validation",
            "Handle form submission",
            "Add error display"
        ]
    },
    "card-013": {
        "description": """## API Client Service
Create service for API communication.

**Functions:**
- fetchTodos()
- createTodo(data)
- updateTodo(id, data)
- deleteTodo(id)
- toggleTodo(id)

**Features:**
- Axios interceptors
- Error handling
- Request/response logging""",
        "subtasks": [
            "Set up Axios instance",
            "Create API functions",
            "Add interceptors",
            "Handle errors"
        ]
    },
    "card-014": {
        "description": """## Frontend-Backend Integration
Connect React app to API endpoints.

**Tasks:**
- Configure API base URL
- Add API calls to components
- Handle loading states
- Display errors
- Update UI after mutations

**State Management:**
- React Query or Redux Toolkit
- Optimistic updates""",
        "subtasks": [
            "Install state management library",
            "Create API hooks",
            "Integrate with components",
            "Add error handling",
            "Test integration"
        ]
    },
    "card-015": {
        "description": """## User Authentication
Add user registration and login.

**Features:**
- Registration form
- Login form
- JWT authentication
- Protected routes
- User context

**Security:**
- Password hashing (bcrypt)
- JWT tokens
- Refresh tokens""",
        "subtasks": [
            "Create auth endpoints",
            "Build auth forms",
            "Implement JWT",
            "Add route protection",
            "Create user context"
        ]
    },
    "card-016": {
        "description": """## Testing
Write tests for the application.

**Test Types:**
- Unit tests (components, utils)
- Integration tests (API)
- E2E tests (user flows)

**Tools:**
- Jest + React Testing Library
- Supertest (API)
- Cypress (E2E)""",
        "subtasks": [
            "Set up test environment",
            "Write unit tests",
            "Create API tests",
            "Add E2E tests",
            "Set up CI"
        ]
    },
    "card-017": {
        "description": """## Deployment
Deploy application to production.

**Tasks:**
- Set up hosting (Vercel/Heroku)
- Configure environment variables
- Set up database (Supabase/RDS)
- Configure CI/CD
- Add monitoring

**Checklist:**
- Environment variables set
- Database migrated
- SSL configured
- Monitoring active""",
        "subtasks": [
            "Choose hosting providers",
            "Configure deployments",
            "Set up database",
            "Configure CI/CD",
            "Add monitoring",
            "Deploy application"
        ]
    }
}

async def create_moderate_cards():
    """Create Todo App cards with moderate detail"""
    print("🚀 Creating Todo App cards with moderate detail...")
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to kanban-mcp\n")
            
            # Get all projects
            print("📋 Finding Task Master Test project...")
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_projects",
                "page": 1,
                "perPage": 25
            })
            
            projects_data = json.loads(result.content[0].text)
            project = None
            
            for p in projects_data["items"]:
                if p["name"] == "Task Master Test":
                    project = p
                    break
            
            if not project:
                print("❌ Project not found!")
                return
                
            project_id = project["id"]
            print(f"✅ Found project: {project['name']} (ID: {project_id})")
            
            # Find the board in the included data
            board_id = None
            if "boards" in projects_data.get("included", {}):
                for board in projects_data["included"]["boards"]:
                    if board["projectId"] == project_id:
                        board_id = board["id"]
                        print(f"✅ Found board: {board['name']} (ID: {board_id})")
                        break
            
            if not board_id:
                print("❌ No board found for Task Master Test!")
                return
            
            # Get lists
            print("\n📋 Getting lists...")
            result = await session.call_tool("mcp_kanban_list_manager", {
                "action": "get_all",
                "boardId": board_id
            })
            
            lists = json.loads(result.content[0].text)
            backlog_list = next((l for l in lists if l["name"] == "Backlog"), None)
            
            if not backlog_list:
                print("❌ Backlog list not found!")
                return
                
            print(f"✅ Found list: {backlog_list['name']} (ID: {backlog_list['id']})")
            
            # Clear existing cards
            print("\n🧹 Clearing existing cards...")
            result = await session.call_tool("mcp_kanban_card_manager", {
                "action": "get_all",
                "listId": backlog_list["id"]
            })
            
            cards = []
            if result.content and result.content[0].text:
                try:
                    cards = json.loads(result.content[0].text)
                    if not isinstance(cards, list):
                        cards = []
                except:
                    cards = []
            for card in cards:
                await session.call_tool("mcp_kanban_card_manager", {
                    "action": "delete",
                    "cardId": card["id"]
                })
            print(f"  ✅ Cleared {len(cards)} existing cards")
            
            # Get labels
            print("\n🏷️  Getting labels...")
            result = await session.call_tool("mcp_kanban_label_manager", {
                "action": "get_all",
                "boardId": board_id
            })
            
            labels = json.loads(result.content[0].text)
            label_map = {label["name"]: label["id"] for label in labels}
            print(f"  ✅ Found {len(labels)} labels")
            
            # Create cards
            print("\n📝 Creating moderate detail cards...")
            cards_created = 0
            
            for i, card_data in enumerate(TODO_APP_DATA["cards"]):
                card_num = cards_created + 1
                card_key = card_data["id"]  # Use the card id as key
                print(f"\n[{card_num}/17] Creating: {card_data['title']}")
                
                # Get moderate description and subtasks
                moderate_info = MODERATE_CARDS.get(card_key, {})
                description = moderate_info.get("description", card_data["description"])
                subtasks = moderate_info.get("subtasks", [])
                
                # Use existing due date or create one
                if "dueDate" in card_data:
                    due_date = card_data["dueDate"]
                else:
                    # Create a due date based on position (1-2 days per card)
                    due_date = (datetime.now() + timedelta(days=i+2)).isoformat() + "Z"
                
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
                    print(f"  ✅ Created card ID: {card_id}")
                    
                    # Add labels
                    for label_name in card_data.get("labels", []):
                        if label_name in label_map:
                            await session.call_tool("mcp_kanban_label_manager", {
                                "action": "add_to_card",
                                "cardId": card_id,
                                "labelId": label_map[label_name]
                            })
                            print(f"  ✅ Added label: {label_name}")
                    
                    # Create subtasks
                    if subtasks:
                        print(f"  📋 Creating {len(subtasks)} subtasks...")
                        for i, subtask in enumerate(subtasks):
                            await session.call_tool("mcp_kanban_task_manager", {
                                "action": "create",
                                "cardId": card_id,
                                "name": subtask,
                                "position": i
                            })
                        print(f"  ✅ Created subtasks")
                    
                    # Update due date
                    await session.call_tool("mcp_kanban_card_manager", {
                        "action": "update",
                        "cardId": card_id,
                        "dueDate": due_date
                    })
                    
                    cards_created += 1
                    
                except Exception as e:
                    print(f"  ❌ Error creating card: {e}")
            
            print(f"\n✅ Successfully created {cards_created}/17 cards with moderate detail!")
            print("\n✨ Todo App project board is ready with moderate detail!")

if __name__ == "__main__":
    asyncio.run(create_moderate_cards())