#!/usr/bin/env python3
"""Test working connection to kanban-mcp"""

import asyncio
import json
import subprocess
import sys
from typing import Any, Dict

class SimpleKanbanMCPClient:
    """Simple client that handles the kanban-mcp protocol"""
    
    def __init__(self):
        self.proc = None
        self.request_id = 0
        
    async def connect(self):
        """Start the kanban-mcp process and initialize"""
        env = {
            **os.environ,
            "PLANKA_BASE_URL": "http://localhost:3333",
            "PLANKA_AGENT_EMAIL": "demo@demo.demo",
            "PLANKA_AGENT_PASSWORD": "demo",
            "PLANKA_ADMIN_EMAIL": "demo@demo.demo"
        }
        
        self.proc = await asyncio.create_subprocess_exec(
            "/opt/homebrew/bin/node",
            "../kanban-mcp/dist/index.js",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        print("✅ Process started")
        
        # Initialize
        result = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",  # Use the version the server expects
            "capabilities": {},
            "clientInfo": {
                "name": "pm-agent-test",
                "version": "1.0.0"
            }
        })
        
        print(f"✅ Initialized: {result}")
        return result
        
    async def send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send a JSON-RPC request and wait for response"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }
        
        # Send request
        self.proc.stdin.write((json.dumps(request) + "\n").encode())
        await self.proc.stdin.drain()
        
        # Read response
        response_line = await self.proc.stdout.readline()
        response = json.loads(response_line.decode())
        
        if "error" in response:
            raise Exception(f"Error: {response['error']}")
            
        return response.get("result")
        
    async def list_tools(self):
        """List available tools"""
        return await self.send_request("tools/list", {})
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """Call a tool"""
        return await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
    async def close(self):
        """Close the connection"""
        if self.proc:
            self.proc.terminate()
            await self.proc.wait()


async def test_connection():
    """Test the connection with our simple client"""
    print("🔍 Testing Kanban-MCP Connection with Simple Client")
    print("-" * 50)
    
    client = SimpleKanbanMCPClient()
    
    try:
        # Connect
        await client.connect()
        
        # List tools
        print("\n📋 Listing tools...")
        tools = await client.list_tools()
        print(f"Found {len(tools.get('tools', []))} tools")
        
        # Test a tool call
        print("\n🔧 Testing tool call...")
        result = await client.call_tool("mcp_kanban_project_board_manager", {
            "action": "get_projects",
            "page": 1,
            "perPage": 10
        })
        print(f"Result: {result}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.close()


import os
if __name__ == "__main__":
    asyncio.run(test_connection())