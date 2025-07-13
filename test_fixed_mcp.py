#!/usr/bin/env python3
"""Test if the MCP communication is fixed."""

import asyncio
import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_fixed_mcp():
    """Test the fixed MCP server."""
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.marcus_mcp.server"],
        env=os.environ.copy(),
        cwd="/Users/lwgray/dev/marcus"
    )
    
    print("🚀 Testing fixed Marcus MCP server...\n")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("📡 Initializing session...")
                await session.initialize()
                print("✅ Session initialized!\n")
                
                # Test ping
                print("🏓 Testing ping...")
                result = await session.call_tool("ping", {"echo": "hello"})
                ping_data = json.loads(result.content[0].text)
                print(f"✅ Ping response: {ping_data.get('echo')}\n")
                
                # Test get_project_status
                print("📊 Testing get_project_status...")
                result = await session.call_tool("get_project_status", {})
                status_data = json.loads(result.content[0].text)
                print(f"✅ Project status: success={status_data.get('success')}\n")
                
                print("✅ All tests passed! MCP communication is working!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_mcp())