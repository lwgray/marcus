#!/usr/bin/env python3
"""
Script to create Todo App development tasks on the Task Master Test board in Planka
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.integrations.mcp_kanban_client_simplified import MCPKanbanClientSimplified
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager


# Task definitions for the Todo App project
TODO_APP_TASKS = [
    {
        "title": "Set up project structure",
        "description": "Initialize the project with proper folder structure, package.json, and basic configuration files.\n\n### Acceptance Criteria:\n- Project initialized with npm/yarn\n- Folder structure created (src, tests, config, etc.)\n- Basic configuration files added (.gitignore, .env.example)\n- README.md with initial project description",
        "priority": "high",
        "due_days": 5,
        "dependencies": []
    },
    {
        "title": "Design database schema",
        "description": "Design the database schema for todos including all necessary fields and relationships.\n\n### Requirements:\n- Support for multiple users\n- Todo items with all necessary fields\n- Categories/tags support\n- Audit fields (created, updated timestamps)",
        "priority": "high",
        "due_days": 6,
        "dependencies": []
    },
    {
        "title": "Create Todo model",
        "description": "Implement the Todo model/entity with proper data types, validation, and business logic.\n\n### Model Requirements:\n- All CRUD operations\n- Data validation\n- Business logic methods\n- Proper error handling",
        "priority": "high",
        "due_days": 8,
        "dependencies": ["Set up project structure", "Design database schema"]
    },
    {
        "title": "Set up database connection",
        "description": "Configure database connection with proper pooling, error handling, and environment-based configuration.\n\n### Requirements:\n- Connection pooling\n- Retry logic\n- Environment-based configuration\n- Health check endpoint",
        "priority": "high",
        "due_days": 7,
        "dependencies": ["Set up project structure"]
    },
    {
        "title": "Create API endpoints for CRUD operations",
        "description": "Implement RESTful API endpoints for todo operations.\n\n### Endpoints to implement:\n- GET /api/todos - List all todos with pagination\n- GET /api/todos/:id - Get single todo\n- POST /api/todos - Create new todo\n- PUT /api/todos/:id - Update todo\n- DELETE /api/todos/:id - Delete todo\n- PATCH /api/todos/:id/complete - Mark as complete",
        "priority": "high",
        "due_days": 10,
        "dependencies": ["Create Todo model", "Set up database connection"]
    },
    {
        "title": "Add input validation middleware",
        "description": "Create middleware to validate todo input data using a validation library like Joi or Yup.\n\n### Validation Rules:\n- Title: required, min 3 chars, max 255 chars\n- Description: optional, max 1000 chars\n- Priority: enum (low, medium, high, urgent)\n- Due date: valid future date",
        "priority": "medium",
        "due_days": 12,
        "dependencies": ["Create API endpoints for CRUD operations"]
    },
    {
        "title": "Implement error handling",
        "description": "Add comprehensive error handling throughout the application.\n\n### Requirements:\n- Global error handler middleware\n- Custom error classes\n- Proper error logging\n- User-friendly error messages",
        "priority": "medium",
        "due_days": 13,
        "dependencies": ["Create API endpoints for CRUD operations"]
    },
    {
        "title": "Create frontend app structure",
        "description": "Set up the frontend application with a modern framework and proper architecture.\n\n### Tech Stack:\n- React with TypeScript\n- Component-based architecture\n- State management (Redux/Context)\n- Routing setup\n- API service layer",
        "priority": "high",
        "due_days": 9,
        "dependencies": ["Set up project structure"]
    },
    {
        "title": "Design UI mockups",
        "description": "Create UI/UX designs for all application screens.\n\n### Screens to design:\n- Todo list view (desktop & mobile)\n- Add/Edit todo modal\n- Filter sidebar\n- User profile/settings\n- Login/Register screens",
        "priority": "medium",
        "due_days": 8,
        "dependencies": []
    },
    {
        "title": "Build TodoList component",
        "description": "Create the main todo list component that displays all todos.\n\n### Features:\n- Display todos in a clean list format\n- Show todo status with icons/colors\n- Priority indicators\n- Due date display\n- Empty state",
        "priority": "high",
        "due_days": 14,
        "dependencies": ["Create frontend app structure", "Design UI mockups"]
    },
    {
        "title": "Build TodoItem component",
        "description": "Create individual todo item component with all interactive features.\n\n### Features:\n- Checkbox for completion\n- Edit button\n- Delete button with confirmation\n- Priority badge\n- Due date with overdue styling",
        "priority": "high",
        "due_days": 15,
        "dependencies": ["Build TodoList component"]
    },
    {
        "title": "Build AddTodo form component",
        "description": "Create form component for adding new todos with validation.\n\n### Form Fields:\n- Title (required)\n- Description (textarea)\n- Priority selector\n- Due date picker\n- Tags input",
        "priority": "high",
        "due_days": 16,
        "dependencies": ["Create frontend app structure", "Design UI mockups"]
    },
    {
        "title": "Implement API client service",
        "description": "Create a service layer to handle all API communications.\n\n### Requirements:\n- Axios/Fetch wrapper\n- Request/Response interceptors\n- Error handling\n- Auth token management",
        "priority": "high",
        "due_days": 11,
        "dependencies": ["Create frontend app structure"]
    },
    {
        "title": "Connect frontend to backend",
        "description": "Wire up all frontend components to use the API service.\n\n### Integration Points:\n- Fetch todos on mount\n- Create todo submission\n- Update todo\n- Delete todo\n- Real-time updates",
        "priority": "high",
        "due_days": 18,
        "dependencies": ["Build TodoList component", "Build TodoItem component", "Build AddTodo form component", "Implement API client service", "Create API endpoints for CRUD operations"]
    },
    {
        "title": "Add todo status management",
        "description": "Implement status transitions (pending -> in-progress -> completed) with UI updates.\n\n### Features:\n- Status dropdown/buttons\n- Visual status indicators\n- Transition animations\n- Status filtering",
        "priority": "medium",
        "due_days": 19,
        "dependencies": ["Connect frontend to backend"]
    },
    {
        "title": "Implement filtering and sorting",
        "description": "Add ability to filter todos by status, priority, and sort by date/priority.\n\n### Features:\n- Filter by status\n- Filter by priority\n- Sort by creation date\n- Sort by due date\n- Sort by priority",
        "priority": "medium",
        "due_days": 20,
        "dependencies": ["Connect frontend to backend"]
    },
    {
        "title": "Add search functionality",
        "description": "Implement search feature to find todos by title or description.\n\n### Features:\n- Real-time search\n- Highlight search terms\n- Search suggestions\n- Clear search button",
        "priority": "medium",
        "due_days": 21,
        "dependencies": ["Connect frontend to backend"]
    },
    {
        "title": "Style the application",
        "description": "Apply CSS/styling framework to make the app visually appealing.\n\n### Requirements:\n- Consistent color scheme\n- Responsive design\n- Modern UI patterns\n- Smooth animations",
        "priority": "medium",
        "due_days": 22,
        "dependencies": ["Build TodoList component", "Build TodoItem component", "Build AddTodo form component"]
    },
    {
        "title": "Write API tests",
        "description": "Create unit and integration tests for all API endpoints.\n\n### Test Coverage:\n- All CRUD endpoints\n- Error scenarios\n- Validation tests\n- Auth tests",
        "priority": "high",
        "due_days": 23,
        "dependencies": ["Create API endpoints for CRUD operations", "Add input validation middleware", "Implement error handling"]
    },
    {
        "title": "Write frontend component tests",
        "description": "Create unit tests for all React components.\n\n### Test Coverage:\n- Component rendering\n- User interactions\n- State management\n- API integration",
        "priority": "high",
        "due_days": 24,
        "dependencies": ["Build TodoList component", "Build TodoItem component", "Build AddTodo form component"]
    },
    {
        "title": "Add user authentication",
        "description": "Implement user registration and login functionality.\n\n### Features:\n- User registration\n- Email verification\n- Login/Logout\n- JWT tokens\n- Password reset",
        "priority": "medium",
        "due_days": 25,
        "dependencies": ["Create API endpoints for CRUD operations"]
    },
    {
        "title": "Add authorization",
        "description": "Ensure users can only see and modify their own todos.\n\n### Requirements:\n- User-specific todo filtering\n- Authorization middleware\n- Secure API endpoints\n- Frontend route guards",
        "priority": "high",
        "due_days": 26,
        "dependencies": ["Add user authentication"]
    },
    {
        "title": "Performance optimization",
        "description": "Optimize database queries and implement caching where needed.\n\n### Optimizations:\n- Database query optimization\n- API response caching\n- Frontend bundle optimization\n- Lazy loading",
        "priority": "low",
        "due_days": 27,
        "dependencies": ["Write API tests", "Write frontend component tests"]
    },
    {
        "title": "Deploy to production",
        "description": "Deploy the application to a cloud provider.\n\n### Deployment Steps:\n- Set up cloud infrastructure\n- Configure CI/CD pipeline\n- Set up monitoring\n- Configure SSL certificates",
        "priority": "high",
        "due_days": 30,
        "dependencies": ["Performance optimization", "Add authorization"]
    }
]


async def create_mcp_function_caller():
    """Create a real MCP function caller for testing"""
    @asynccontextmanager
    async def get_client():
        server_params = StdioServerParameters(
            command="node",
            args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    
    async def mcp_call(tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool"""
        async with get_client() as session:
            result = await session.call_tool(tool_name, arguments)
            if result.content:
                text = result.content[0].text
                # Try to parse JSON response
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
            return None
    
    return mcp_call


async def create_tasks_on_board():
    """Create all Todo App tasks on the Task Master Test board"""
    print("🚀 Starting to create Todo App tasks on Task Master Test board...")
    
    # Create MCP function caller
    mcp_caller = await create_mcp_function_caller()
    
    # Create client with MCP caller
    client = MCPKanbanClientSimplified(mcp_caller)
    
    try:
        # Initialize the client
        print("\n1. Initializing connection to Task Master Test...")
        await client.initialize("Task Master Test")
        print(f"✅ Connected to project: {client.project_id}")
        print(f"✅ Using board: {client.board_id}")
        
        # Get the TODO list ID (where we'll create all tasks initially)
        print("\n2. Finding TODO list...")
        lists = await client._get_lists()
        todo_list = None
        for lst in lists:
            if "TODO" in lst.get("name", "").upper() or "BACKLOG" in lst.get("name", "").upper():
                todo_list = lst
                break
        
        if not todo_list:
            print("❌ No TODO or Backlog list found!")
            return
        
        print(f"✅ Found list: {todo_list['name']} (ID: {todo_list['id']})")
        
        # Create a mapping of task titles to card IDs for dependencies
        task_id_map = {}
        
        # Create all tasks
        print("\n3. Creating tasks...")
        created_count = 0
        
        for i, task_def in enumerate(TODO_APP_TASKS, 1):
            print(f"\n   Creating task {i}/{len(TODO_APP_TASKS)}: {task_def['title']}")
            
            # Calculate due date
            due_date = datetime.now() + timedelta(days=task_def['due_days'])
            
            # Create the card
            try:
                card_data = await mcp_caller("mcp_kanban_card_manager", {
                    "action": "create",
                    "listId": todo_list['id'],
                    "name": task_def['title'],
                    "description": task_def['description']
                })
                
                if card_data and isinstance(card_data, dict):
                    card_id = card_data.get('id')
                    if card_id:
                        task_id_map[task_def['title']] = card_id
                        print(f"   ✅ Created card with ID: {card_id}")
                        
                        # Add priority label
                        if task_def['priority']:
                            label_color = {
                                'high': 'red',
                                'medium': 'orange',
                                'low': 'green'
                            }.get(task_def['priority'], 'gray')
                            
                            try:
                                await mcp_caller("mcp_kanban_label_manager", {
                                    "action": "add",
                                    "cardId": card_id,
                                    "name": task_def['priority'],
                                    "color": label_color
                                })
                                print(f"   ✅ Added {task_def['priority']} priority label")
                            except Exception as e:
                                print(f"   ⚠️  Could not add label: {str(e)}")
                        
                        # Add due date comment (since direct due date setting might not be available)
                        due_date_str = due_date.strftime("%Y-%m-%d")
                        await client.add_comment(
                            card_id,
                            f"📅 Due date: {due_date_str}"
                        )
                        
                        # Add dependencies as comments
                        if task_def['dependencies']:
                            deps_text = "Dependencies:\\n"
                            for dep in task_def['dependencies']:
                                deps_text += f"- {dep}\\n"
                            await client.add_comment(card_id, deps_text)
                        
                        created_count += 1
                    else:
                        print(f"   ❌ Failed to get card ID from response")
                else:
                    print(f"   ❌ Invalid response when creating card")
                    
            except Exception as e:
                print(f"   ❌ Error creating task: {str(e)}")
        
        print(f"\n✅ Successfully created {created_count}/{len(TODO_APP_TASKS)} tasks!")
        
        # Get board summary
        print("\n4. Getting board summary...")
        try:
            all_cards = await client._get_cards()
            print(f"✅ Total cards on board: {len(all_cards)}")
        except Exception as e:
            print(f"❌ Could not get board summary: {str(e)}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(create_tasks_on_board())