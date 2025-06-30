#!/usr/bin/env python3
"""
Debug MCP label manager responses to understand the issue
"""

import asyncio
import json
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))


async def debug_mcp_responses():
    """Debug the MCP label manager responses"""
    
    board_id = "1533859887128249584"
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("=== MCP Label Manager Debug ===\n")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test 1: Get all labels
            print("1. Testing get_all labels...")
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "get_all",
                    "boardId": board_id
                }
            )
            
            print(f"   Response type: {type(result)}")
            print(f"   Has content: {hasattr(result, 'content')}")
            if hasattr(result, 'content'):
                print(f"   Content: {result.content}")
                if result.content:
                    print(f"   Content[0].type: {result.content[0].type}")
                    print(f"   Content[0].text: {result.content[0].text[:200]}...")
            
            # Test 2: Try to create a label with minimal params
            print("\n2. Testing create label (minimal)...")
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "create",
                    "boardId": board_id,
                    "name": "test-label-minimal"
                }
            )
            
            print(f"   Response type: {type(result)}")
            print(f"   Has content: {hasattr(result, 'content')}")
            if hasattr(result, 'content'):
                print(f"   Content: {result.content}")
            
            # Test 3: Try to create a label with color
            print("\n3. Testing create label (with color)...")
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "create",
                    "boardId": board_id,
                    "name": "test-label-color",
                    "color": "berry-red"
                }
            )
            
            print(f"   Response type: {type(result)}")
            print(f"   Has content: {hasattr(result, 'content')}")
            if hasattr(result, 'content'):
                print(f"   Content: {result.content}")
                if result.content:
                    print(f"   Content length: {len(result.content)}")
                    for i, content in enumerate(result.content):
                        print(f"   Content[{i}]: type={content.type}")
                        if hasattr(content, 'text'):
                            print(f"   Content[{i}].text: {content.text}")
            
            # Test 4: List available tools to check exact schema
            print("\n4. Checking available tools...")
            tools = await session.list_tools()
            for tool in tools.tools:
                if "label" in tool.name.lower():
                    print(f"\n   Tool: {tool.name}")
                    print(f"   Description: {tool.description}")
                    print(f"   Input Schema: {json.dumps(tool.inputSchema, indent=4)}")


if __name__ == "__main__":
    try:
        asyncio.run(debug_mcp_responses())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()