#!/usr/bin/env python3
"""
Diagnose the create_project MCP tool issue
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_create_project():
    """Test the MCP create_project tool to diagnose issues"""
    
    print("=== Diagnosing MCP create_project Tool ===\n")
    
    # Check if Marcus server is running
    print("1. Checking Marcus MCP server...")
    marcus_pids = os.popen("ps aux | grep marcus.py | grep -v grep").read()
    if marcus_pids:
        print("   ✓ Marcus server appears to be running")
        print(f"   PIDs: {marcus_pids.strip()}")
    else:
        print("   ✗ Marcus server not found running")
        print("   Start it with: python marcus.py")
        return
    
    # Set up MCP client connection
    print("\n2. Setting up MCP client connection...")
    
    # Marcus uses stdio, not network port
    server_params = StdioServerParameters(
        command="python",
        args=["marcus.py"],
        env=os.environ.copy()
    )
    
    try:
        print("   Connecting to Marcus MCP server...")
        start_time = time.time()
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print(f"   ✓ Connected in {time.time() - start_time:.2f}s")
                
                # Initialize the session
                print("\n3. Initializing MCP session...")
                init_start = time.time()
                await session.initialize()
                print(f"   ✓ Initialized in {time.time() - init_start:.2f}s")
                
                # List available tools
                print("\n4. Checking available tools...")
                tools = await session.list_tools()
                tool_names = [tool.name for tool in tools]
                
                if "create_project" in tool_names:
                    print("   ✓ create_project tool is available")
                else:
                    print("   ✗ create_project tool NOT found!")
                    print(f"   Available tools: {', '.join(tool_names)}")
                    return
                
                # Try a simple project creation
                print("\n5. Testing create_project with simple input...")
                
                test_description = "A simple test project with just a few tasks"
                test_name = f"Test Project {datetime.now().strftime('%H:%M:%S')}"
                
                print(f"   Project: {test_name}")
                print(f"   Description: {test_description}")
                print("   Starting tool call...")
                
                call_start = time.time()
                
                try:
                    # Make the actual tool call
                    result = await session.call_tool(
                        "create_project",
                        {
                            "description": test_description,
                            "project_name": test_name,
                            "options": {
                                "max_tasks": 5  # Limit tasks to speed up
                            }
                        }
                    )
                    
                    elapsed = time.time() - call_start
                    print(f"\n   ✓ Tool call completed in {elapsed:.2f}s")
                    
                    # Parse result
                    if result and hasattr(result, 'content') and result.content:
                        result_data = json.loads(result.content[0].text)
                        print(f"   Result: {json.dumps(result_data, indent=2)}")
                    else:
                        print("   ✗ No result content received")
                        
                except asyncio.TimeoutError:
                    elapsed = time.time() - call_start
                    print(f"\n   ✗ Tool call timed out after {elapsed:.2f}s")
                    print("   This confirms it's a timeout issue")
                    
                except Exception as e:
                    elapsed = time.time() - call_start
                    print(f"\n   ✗ Tool call failed after {elapsed:.2f}s")
                    print(f"   Error: {type(e).__name__}: {e}")
                    
                print("\n6. Checking where the delay occurs...")
                print("   The delay is likely in:")
                print("   - AI processing (parse_prd_to_tasks)")
                print("   - Multiple task creation API calls")
                print("   - MCP communication overhead")
                
    except Exception as e:
        print(f"\n✗ Failed to connect to Marcus MCP server")
        print(f"   Error: {type(e).__name__}: {e}")
        print("\n   Troubleshooting:")
        print("   1. Make sure Marcus is running: python marcus.py")
        print("   2. Check if another process is using the connection")
        print("   3. Try restarting Marcus")


if __name__ == "__main__":
    print("Starting diagnostic...\n")
    asyncio.run(test_mcp_create_project())