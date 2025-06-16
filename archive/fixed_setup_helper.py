#!/usr/bin/env python3
"""
Fixed setup script that works with your MCP server configuration.
This version uses the kanban MCP server you have configured rather than
trying to create its own connection.
"""

import asyncio
import sys
import os
from pathlib import Path


async def test_mcp_connection():
    """Test if we can connect to the kanban MCP server through Claude's function calls."""
    
    print("Testing MCP kanban server connection...")
    
    # This script should be run through Claude with access to the kanban MCP tools
    # Let's create a simple test that can be run manually
    
    print("""
    This script needs to be run through Claude with MCP server access.
    
    To set up the Task Master Test project:
    
    1. Make sure your kanban MCP server is running (check your MCP config)
    2. Open Claude with MCP servers enabled
    3. Ask Claude to run these commands:
    
    # Get projects
    mcp_kanban_project_board_manager({
        "action": "get_projects", 
        "page": 1, 
        "perPage": 25
    })
    
    # If "Task Master Test" project doesn't exist, create it
    # If it exists, get its boards and create test tasks
    
    Alternatively, you can ask Claude directly:
    "Please set up a test project called 'Task Master Test' on the kanban board 
     with some sample tasks for testing the PM agent integration."
    """)
    
    return True


def create_manual_setup_instructions():
    """Create step-by-step manual setup instructions."""
    
    instructions = """
# Manual Setup Instructions for Task Master Test Project

## Prerequisites
1. Planka server running on http://localhost:3333
2. MCP kanban server configured and running
3. Claude with MCP server access

## Setup Steps

### Step 1: Check if project exists
Ask Claude: "List all projects on the kanban board"

### Step 2: Create project if needed
If "Task Master Test" doesn't exist, ask Claude:
"Create a new project called 'Task Master Test' on the kanban board"

### Step 3: Create test board
Ask Claude: "Create a board called 'Test Development Board' in the Task Master Test project"

### Step 4: Create test tasks
Ask Claude to create these tasks:

1. **Implement user authentication**
   - Description: Add OAuth2 login with Google and GitHub  
   - Priority: high
   - Labels: backend, security, oauth
   - Estimated: 16 hours

2. **Create dashboard UI**
   - Description: Design and implement analytics dashboard
   - Priority: medium  
   - Labels: frontend, react, ui/ux
   - Estimated: 24 hours

3. **Fix payment processing bug**
   - Description: Payments failing for international cards
   - Priority: urgent
   - Labels: backend, payments, bug
   - Estimated: 4 hours

4. **Add unit tests for API** 
   - Description: Increase test coverage to 80%
   - Priority: medium
   - Labels: testing, backend, quality
   - Estimated: 12 hours

5. **Optimize database queries**
   - Description: Improve query performance for reports
   - Priority: low
   - Labels: backend, database, performance  
   - Estimated: 8 hours

### Step 5: Verify setup
Ask Claude: "Show me all tasks in the Task Master Test project"

## Alternative: Use Claude Commands

You can ask Claude to run these exact commands:

```
# List projects
mcp_kanban_project_board_manager({"action": "get_projects", "page": 1, "perPage": 25})

# Create project (if needed)
mcp_kanban_project_board_manager({"action": "create_project", "name": "Task Master Test"})

# Get boards for project  
mcp_kanban_project_board_manager({"action": "get_boards", "projectId": "PROJECT_ID"})

# Create tasks
mcp_kanban_card_manager({"action": "create", "listId": "LIST_ID", "name": "Task Name", "description": "Task Description"})
```

## Testing the Setup

Once set up, you can test the PM agent integration by running:

```bash
cd /Users/lwgray/dev/pm-agent
python -m pytest tests/integration/test_real_kanban_integration.py -v -s
```

## Troubleshooting

If the setup doesn't work:

1. **Check MCP server status**: Make sure your kanban MCP server is running
2. **Check Planka connection**: Visit http://localhost:3333 and verify you can log in
3. **Check Claude MCP access**: Make sure Claude can see your MCP servers
4. **Manual verification**: Create the project manually in Planka web UI

## Next Steps

After setup is complete:
1. Run the integration tests
2. Test the PM agent functionality
3. Verify task assignment and status updates work
"""
    
    return instructions


if __name__ == "__main__":
    print("PM Agent Test Setup Helper")
    print("=" * 50)
    
    # Check if we're running in the right directory
    if not os.path.exists("pm_agent_mcp_server.py"):
        print("ERROR: Please run this from the pm-agent directory")
        print("cd /Users/lwgray/dev/pm-agent")
        sys.exit(1)
    
    # Check for required files
    required_files = [
        "pm_agent_mcp_server.py",
        "src/integrations/mcp_kanban_client.py", 
        "tests/integration/test_real_kanban_integration.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("ERROR: Missing required files:")
        for file in missing_files:
            print(f"  - {file}")
        sys.exit(1)
    
    print("✅ All required files found")
    print("\nSince this script can't directly access your MCP kanban server,")
    print("please follow the manual setup instructions below:\n")
    
    instructions = create_manual_setup_instructions()
    print(instructions)
    
    # Write instructions to file
    with open("SETUP_INSTRUCTIONS.md", "w") as f:
        f.write(instructions)
    
    print(f"\n📝 Instructions saved to: SETUP_INSTRUCTIONS.md")
    print("\n🤖 Recommended: Ask Claude to set up the test project using the MCP kanban tools")
