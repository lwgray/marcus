#!/usr/bin/env python3
"""Minimal test of Kanban MCP connection"""

import asyncio
import json
import subprocess
import sys

async def test_minimal():
    """Test with direct subprocess communication"""
    print("🔍 Testing Kanban MCP with subprocess")
    
    # Start the kanban-mcp process
    proc = subprocess.Popen(
        ["/opt/homebrew/bin/node", "../kanban-mcp/dist/index.js"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            "PLANKA_BASE_URL": "http://localhost:3333",
            "PLANKA_AGENT_EMAIL": "demo@demo.demo",
            "PLANKA_AGENT_PASSWORD": "demo",
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
        }
    )
    
    print("✅ Process started, PID:", proc.pid)
    
    # Send initialize request
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0.0",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }
    
    print("\n📤 Sending initialize request...")
    proc.stdin.write(json.dumps(init_request) + "\n")
    proc.stdin.flush()
    
    # Try to read response
    print("📥 Waiting for response...")
    try:
        # Set a timeout
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        print("⏱️  Process still running (good)")
    
    # Check stderr for any errors
    stderr_output = proc.stderr.read()
    if stderr_output:
        print(f"❌ Error output: {stderr_output}")
    
    # Try to read stdout
    stdout_output = proc.stdout.readline()
    if stdout_output:
        print(f"📨 Response: {stdout_output}")
    else:
        print("⚠️  No response received")
    
    # Clean up
    proc.terminate()
    print("\n🧹 Process terminated")

if __name__ == "__main__":
    asyncio.run(test_minimal())