#!/usr/bin/env python3
"""
Test kanban-mcp with proper initialization
"""

import asyncio
import json
import subprocess
import sys
import os

async def test_mcp_properly():
    """Test MCP with proper protocol"""
    print("🔍 Testing MCP with proper initialization...")
    
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
    
    # Send proper initialization
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
    
    print("1. Sending initialize request...")
    proc.stdin.write(json.dumps(init_request) + '\n')
    proc.stdin.flush()
    
    response = proc.stdout.readline()
    print(f"Response: {json.loads(response)}")
    
    # Send initialized notification
    initialized = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    
    print("\n2. Sending initialized notification...")
    proc.stdin.write(json.dumps(initialized) + '\n')
    proc.stdin.flush()
    
    # Now try to list projects
    list_projects = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "mcp_kanban_board_project_manager",
            "arguments": {
                "action": "list_projects"
            }
        }
    }
    
    print("\n3. Listing projects...")
    proc.stdin.write(json.dumps(list_projects) + '\n')
    proc.stdin.flush()
    
    response = proc.stdout.readline()
    result = json.loads(response)
    print(f"Projects response: {json.dumps(result, indent=2)}")
    
    # Extract projects if successful
    if "result" in result and "content" in result["result"]:
        projects = json.loads(result["result"]["content"][0]["text"])
        print(f"\nFound {len(projects)} projects:")
        for p in projects:
            print(f"  - {p['name']} (ID: {p['id']})")
    
    proc.terminate()
    proc.wait()


if __name__ == "__main__":
    asyncio.run(test_mcp_properly())