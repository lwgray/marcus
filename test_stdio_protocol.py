#!/usr/bin/env python3
"""
Test kanban-mcp with proper stdio protocol
"""

import asyncio
import json

async def test_stdio_protocol():
    """Test with proper MCP stdio initialization"""
    print("🔍 Testing kanban-mcp stdio protocol")
    print("=" * 60)
    
    # Start the process
    process = await asyncio.create_subprocess_exec(
        '/Users/lwgray/.nvm/versions/node/v22.14.0/bin/node',
        '/Users/lwgray/dev/kanban-mcp/dist/index.js',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            "PLANKA_BASE_URL": "http://localhost:3333",
            "PLANKA_AGENT_EMAIL": "demo@demo.demo",
            "PLANKA_AGENT_PASSWORD": "demo"
        }
    )
    
    print("\n1. Process started")
    print(f"   PID: {process.pid}")
    
    # MCP servers expect an initialization message
    init_message = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }
    
    try:
        # Send initialization
        print("\n2. Sending initialization...")
        message = json.dumps(init_message) + '\n'
        process.stdin.write(message.encode())
        await process.stdin.drain()
        
        # Read response with timeout
        print("3. Waiting for response...")
        async with asyncio.timeout(5):
            response = await process.stdout.readline()
            if response:
                print(f"✅ Got response: {response.decode().strip()}")
            else:
                print("❌ No response")
                
            # Check stderr for errors
            stderr_task = asyncio.create_task(process.stderr.read())
            try:
                async with asyncio.timeout(1):
                    stderr = await stderr_task
                    if stderr:
                        print(f"\nStderr output: {stderr.decode()}")
            except asyncio.TimeoutError:
                pass
                
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for response")
        
        # Check if process is still running
        if process.returncode is None:
            print("   Process is still running")
            # Try to get any error output
            try:
                stderr = await asyncio.wait_for(process.stderr.read(1000), timeout=1)
                if stderr:
                    print(f"   Stderr: {stderr.decode()}")
            except:
                pass
        else:
            print(f"   Process exited with code: {process.returncode}")
    
    finally:
        # Clean up
        if process.returncode is None:
            process.terminate()
            await process.wait()
            print("\n4. Process terminated")


if __name__ == "__main__":
    asyncio.run(test_stdio_protocol())