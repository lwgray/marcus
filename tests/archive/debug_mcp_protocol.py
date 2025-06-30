#!/usr/bin/env python3
"""Debug MCP protocol version"""

import asyncio
import json
import subprocess
import os

async def debug_protocol():
    """Debug the protocol version negotiation"""
    print("🔍 Debugging MCP Protocol Version")
    print("-" * 50)
    
    # Start kanban-mcp and manually test protocol negotiation
    env = os.environ.copy()
    env.update({
        "PLANKA_BASE_URL": "http://localhost:3333",
        "PLANKA_AGENT_EMAIL": "demo@demo.demo",
        "PLANKA_AGENT_PASSWORD": "demo",
        "PLANKA_ADMIN_EMAIL": "demo@demo.demo"
    })
    
    proc = await asyncio.create_subprocess_exec(
        "/opt/homebrew/bin/node",
        "../kanban-mcp/dist/index.js",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    
    print("✅ Process started")
    
    # Test different protocol versions
    protocol_versions = ["1.0.0", "2024-11-05", "2024-10-07", "0.1.0"]
    
    for version in protocol_versions:
        print(f"\n📤 Testing protocol version: {version}")
        
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": version,
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        # Send request
        proc.stdin.write((json.dumps(request) + "\n").encode())
        await proc.stdin.drain()
        
        # Read response
        try:
            response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=2)
            response = json.loads(response_line.decode())
            
            if "result" in response:
                server_version = response["result"].get("protocolVersion")
                print(f"   ✅ Success! Server returned protocol: {server_version}")
                
                # If successful, try listing tools
                tools_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 2
                }
                proc.stdin.write((json.dumps(tools_request) + "\n").encode())
                await proc.stdin.drain()
                
                tools_response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=2)
                tools_response = json.loads(tools_response_line.decode())
                
                if "result" in tools_response:
                    tool_count = len(tools_response["result"].get("tools", []))
                    print(f"   📋 Found {tool_count} tools")
                
                break
            else:
                print(f"   ❌ Error: {response.get('error', 'Unknown error')}")
                
        except asyncio.TimeoutError:
            print("   ⏱️  Timeout - no response")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Check for stderr
    stderr_data = await proc.stderr.read()
    if stderr_data:
        print(f"\n⚠️  Server errors:\n{stderr_data.decode()}")
    
    # Cleanup
    proc.terminate()
    await proc.wait()
    
    print("\n" + "-" * 50)
    print("✅ Debug complete")

if __name__ == "__main__":
    asyncio.run(debug_protocol())