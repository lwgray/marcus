#!/usr/bin/env python3
"""
List available tools from kanban-mcp
"""

import asyncio
import json
import subprocess
import sys
import os

async def list_tools():
    """List available MCP tools"""
    print("🔍 Listing available MCP tools...")
    
    cmd = [
        "node",
        "/Users/lwgray/dev/kanban-mcp/dist/index.js"
    ]
    
    env = os.environ.copy()
    env.update({
        'PLANKA_BASE_URL': 'http://localhost:3333',
        'PLANKA_AGENT_EMAIL': 'demo@demo.demo',
        'PLANKA_AGENT_PASSWORD': 'demo'
    })
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=1
    )
    
    # Initialize
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "pm-agent-test",
                "version": "1.0.0"
            }
        }
    }
    
    proc.stdin.write(json.dumps(init_request) + '\n')
    proc.stdin.flush()
    response = proc.stdout.readline()
    
    # Send initialized
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + '\n')
    proc.stdin.flush()
    
    # List tools
    list_tools_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    print("\nRequesting tools list...")
    proc.stdin.write(json.dumps(list_tools_req) + '\n')
    proc.stdin.flush()
    
    response = proc.stdout.readline()
    result = json.loads(response)
    
    if "result" in result and "tools" in result["result"]:
        tools = result["result"]["tools"]
        print(f"\nFound {len(tools)} tools:")
        for tool in tools:
            print(f"\n  Tool: {tool['name']}")
            print(f"  Description: {tool.get('description', 'No description')}")
            if 'inputSchema' in tool:
                print(f"  Input schema: {json.dumps(tool['inputSchema'], indent=4)}")
    else:
        print(f"Unexpected response: {json.dumps(result, indent=2)}")
    
    proc.terminate()
    proc.wait()


if __name__ == "__main__":
    asyncio.run(list_tools())