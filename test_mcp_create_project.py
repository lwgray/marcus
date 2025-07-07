#!/usr/bin/env python3
"""
Test creating a project through the MCP server
"""
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_create_project_via_mcp():
    """Test creating a project through the MCP server"""
    
    # Start the MCP server as a subprocess
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.marcus_mcp.server"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available MCP tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}")
            
            # Call create_project
            print("\n\nCalling create_project...")
            
            project_description = """
            Create a Simple Todo API with the following features:
            - CRUD operations for todos (Create, Read, Update, Delete)
            - Each todo should have: title, description, completed status, timestamps
            - User authentication using JWT tokens
            - Input validation and sanitization
            - Performance: Handle 100 requests per second
            - Security: JWT authentication for all endpoints
            """
            
            result = await session.call_tool(
                "create_project",
                arguments={
                    "description": project_description,
                    "project_name": "Simple Todo API Test",
                    "options": {"team_size": 3}
                }
            )
            
            print("\n\nMCP Response:")
            for content in result.content:
                if hasattr(content, 'text'):
                    # Parse the JSON response
                    try:
                        response_data = json.loads(content.text)
                        print(json.dumps(response_data, indent=2))
                        
                        if response_data.get("success"):
                            print(f"\n✅ Project created successfully!")
                            print(f"Tasks generated: {response_data.get('task_count', 0)}")
                            
                            if 'tasks' in response_data:
                                print("\nGenerated tasks:")
                                for i, task in enumerate(response_data['tasks'], 1):
                                    print(f"{i}. [{task.get('id', 'No ID')}] {task.get('name', 'Unnamed task')}")
                        else:
                            print(f"\n❌ Project creation failed: {response_data.get('error', 'Unknown error')}")
                    except json.JSONDecodeError:
                        print(content.text)

if __name__ == "__main__":
    asyncio.run(test_create_project_via_mcp())