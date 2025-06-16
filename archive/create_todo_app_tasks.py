#!/usr/bin/env python3
"""
Create Todo App tasks in Planka for testing PM Agent
"""

import asyncio
import json
from datetime import datetime, timedelta
from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient


# Task definitions for the Todo App project
TASKS = [
    # Phase 1: Project Setup
    {
        "name": "BACKEND-001: Initialize Python project with FastAPI",
        "description": """Create the initial Python project structure for our Todo API:

1. Create project directory structure:
   - src/
   - src/api/
   - src/models/
   - src/services/
   - tests/

2. Create requirements.txt with:
   - fastapi
   - uvicorn
   - sqlalchemy
   - pytest
   - httpx (for testing)

3. Create main.py with basic FastAPI app
4. Add .gitignore for Python
5. Create README.md with setup instructions""",
        "labels": ["backend", "python", "setup"],
        "priority": "high",
        "estimated_hours": 2
    },
    {
        "name": "FRONTEND-001: Initialize React project",
        "description": """Create React application with TypeScript:

1. Use create-react-app with TypeScript template
2. Set up folder structure:
   - src/components/
   - src/services/
   - src/types/
   - src/styles/

3. Install additional dependencies:
   - axios for API calls
   - react-query for data fetching
   - styled-components or tailwind for styling

4. Configure TypeScript properly
5. Set up basic App component""",
        "labels": ["frontend", "react", "setup"],
        "priority": "high",
        "estimated_hours": 2
    },
    {
        "name": "DEVOPS-001: Create Docker compose setup",
        "description": """Create Docker configuration for development:

1. Create Dockerfile for backend API
2. Create Dockerfile for frontend (nginx to serve build)
3. Create docker-compose.yml with:
   - backend service (port 8000)
   - frontend service (port 3000)
   - volume mounts for development

4. Add docker-compose.dev.yml for development
5. Create .env.example file""",
        "labels": ["devops", "docker", "setup"],
        "priority": "high",
        "estimated_hours": 3
    },
    
    # Phase 2: Core API
    {
        "name": "BACKEND-002: Create Todo model and database schema",
        "description": """Implement database model for todos:

1. Create SQLAlchemy model:
   - id (UUID primary key)
   - title (string, required)
   - description (text, optional)
   - completed (boolean, default false)
   - created_at (timestamp)
   - updated_at (timestamp)

2. Create database initialization script
3. Set up Alembic for migrations
4. Create initial migration""",
        "labels": ["backend", "database", "python"],
        "priority": "high",
        "dependencies": ["BACKEND-001"],
        "estimated_hours": 3
    },
    {
        "name": "BACKEND-003: Implement CRUD endpoints",
        "description": """Create REST API endpoints:

1. POST /api/todos - Create new todo
2. GET /api/todos - List all todos (with pagination)
3. GET /api/todos/{id} - Get single todo
4. PUT /api/todos/{id} - Update todo
5. DELETE /api/todos/{id} - Delete todo

Include:
- Proper error handling
- Input validation with Pydantic
- Status codes
- Response models""",
        "labels": ["backend", "api", "python"],
        "priority": "high",
        "dependencies": ["BACKEND-002"],
        "estimated_hours": 4
    },
    {
        "name": "BACKEND-004: Add API documentation",
        "description": """Configure comprehensive API documentation:

1. Ensure all endpoints have proper OpenAPI docs
2. Add request/response examples
3. Document error responses
4. Add API versioning (/api/v1)
5. Create Postman collection for testing""",
        "labels": ["backend", "documentation"],
        "priority": "medium",
        "dependencies": ["BACKEND-003"],
        "estimated_hours": 2
    },
    {
        "name": "TEST-001: Write backend unit tests",
        "description": """Comprehensive backend testing:

1. Test all CRUD operations
2. Test validation (invalid inputs)
3. Test error cases
4. Test pagination
5. Achieve 80% code coverage
6. Set up pytest configuration""",
        "labels": ["testing", "backend", "pytest"],
        "priority": "high",
        "dependencies": ["BACKEND-003"],
        "estimated_hours": 4
    },
    
    # Phase 3: Frontend Development
    {
        "name": "FRONTEND-002: Create Todo list component",
        "description": """Build main todo list display:

1. Create TodoList component
2. Create TodoItem component
3. Implement responsive design
4. Add loading states
5. Add empty state
6. Style with chosen CSS solution""",
        "labels": ["frontend", "react", "component"],
        "priority": "medium",
        "dependencies": ["FRONTEND-001"],
        "estimated_hours": 3
    },
    {
        "name": "FRONTEND-003: Add todo creation form",
        "description": """Implement todo creation:

1. Create AddTodo component
2. Form with title and description
3. Client-side validation
4. Submit handling
5. Clear form after submission
6. Show success/error messages""",
        "labels": ["frontend", "react", "form"],
        "priority": "medium",
        "dependencies": ["FRONTEND-002"],
        "estimated_hours": 3
    },
    {
        "name": "FRONTEND-004: Implement edit/delete functionality",
        "description": """Add todo management features:

1. Inline editing for todo title
2. Modal for editing description
3. Delete with confirmation dialog
4. Mark as complete/incomplete
5. Optimistic updates
6. Error handling and rollback""",
        "labels": ["frontend", "react", "feature"],
        "priority": "medium",
        "dependencies": ["FRONTEND-003"],
        "estimated_hours": 4
    },
    {
        "name": "FRONTEND-005: Connect to backend API",
        "description": """Integrate with backend:

1. Create API service layer
2. Configure axios with base URL
3. Implement all CRUD operations
4. Add error interceptors
5. Handle loading states
6. Add retry logic for failed requests""",
        "labels": ["frontend", "integration", "api"],
        "priority": "high",
        "dependencies": ["FRONTEND-004", "BACKEND-003"],
        "estimated_hours": 4
    }
]


async def create_tasks_in_planka():
    """Create all tasks in Planka"""
    client = MCPKanbanClient()
    client.project_id = "1533678301472621705"  # Task Master project
    
    print("🚀 Creating Todo App tasks in Planka...")
    
    async with client.connect() as conn:
        # First, ensure we have a board
        if not client.board_id:
            print("❌ No board found. Please run select_task_master_board.py first")
            return
        
        print(f"📋 Using board: {client.board_id}")
        
        # Get the first list (TODO list)
        lists_result = await conn.call_tool("mcp_kanban_list_manager", {
            "action": "get_lists",
            "boardId": client.board_id
        })
        lists_data = json.loads(lists_result.content[0].text)
        
        if not lists_data.get("lists"):
            print("❌ No lists found in board")
            return
        
        todo_list = lists_data["lists"][0]  # First list is usually "To Do"
        print(f"📝 Adding tasks to list: {todo_list['name']}")
        
        # Create tasks
        created_count = 0
        for task_data in TASKS:
            try:
                # Prepare task for creation
                task = {
                    "name": task_data["name"],
                    "description": task_data["description"],
                    "listId": todo_list["id"],
                    "position": created_count + 1
                }
                
                # Create the task
                result = await conn.call_tool("mcp_kanban_card_manager", {
                    "action": "create_card",
                    **task
                })
                
                card_data = json.loads(result.content[0].text)
                card_id = card_data["id"]
                
                # Add labels
                if task_data.get("labels"):
                    for label in task_data["labels"]:
                        await conn.call_tool("mcp_kanban_label_manager", {
                            "action": "add_label",
                            "cardId": card_id,
                            "name": label,
                            "color": get_label_color(label)
                        })
                
                # Add priority as comment
                if task_data.get("priority"):
                    await conn.call_tool("mcp_kanban_comment_manager", {
                        "action": "create_comment",
                        "cardId": card_id,
                        "text": f"Priority: {task_data['priority']}\nEstimated hours: {task_data.get('estimated_hours', 'TBD')}"
                    })
                
                created_count += 1
                print(f"✅ Created: {task_data['name']}")
                
            except Exception as e:
                print(f"❌ Failed to create {task_data['name']}: {e}")
        
        print(f"\n🎉 Created {created_count} tasks successfully!")
        print("\n📋 Next steps:")
        print("1. Start PM Agent: python start_pm_agent_task_master.py")
        print("2. Start worker agents to work on these tasks")
        print("3. Monitor progress in Planka")


def get_label_color(label: str) -> str:
    """Get color for label based on type"""
    color_map = {
        "backend": "#4CAF50",      # Green
        "frontend": "#2196F3",     # Blue  
        "testing": "#FF9800",      # Orange
        "devops": "#9C27B0",       # Purple
        "setup": "#F44336",        # Red
        "api": "#00BCD4",          # Cyan
        "database": "#795548",     # Brown
        "python": "#3776AB",       # Python blue
        "react": "#61DAFB",        # React blue
        "docker": "#0066CC",       # Docker blue
    }
    return color_map.get(label, "#757575")  # Default gray


if __name__ == "__main__":
    asyncio.run(create_tasks_in_planka())