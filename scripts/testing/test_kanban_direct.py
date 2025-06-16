#!/usr/bin/env python3
"""
Test kanban-mcp directly with minimal setup
"""

import asyncio
import json
import subprocess
import sys
import os

async def test_direct_mcp():
    """Test MCP connection directly"""
    print("🔍 Testing direct MCP connection...")
    
    # First check if we can communicate with kanban-mcp via stdio
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
    
    print("Starting kanban-mcp process...")
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )
    
    # Send initialization request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        }
    }
    
    print(f"Sending: {json.dumps(init_request)}")
    proc.stdin.write(json.dumps(init_request) + '\n')
    proc.stdin.flush()
    
    # Try to read response
    print("Waiting for response...")
    try:
        # Set a timeout
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("No response from kanban-mcp")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)  # 5 second timeout
        
        response = proc.stdout.readline()
        signal.alarm(0)  # Cancel timeout
        
        if response:
            print(f"Response: {response}")
            data = json.loads(response)
            print(f"Parsed: {json.dumps(data, indent=2)}")
        else:
            print("No response received")
            
    except TimeoutError:
        print("❌ Timeout waiting for response")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    asyncio.run(test_direct_mcp())