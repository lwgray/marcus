#!/usr/bin/env python3
"""Minimal MCP test to check if communication works."""

import asyncio
import json
import subprocess
import sys

async def test_minimal_mcp():
    """Test MCP communication with a minimal setup."""
    
    # Start the MCP server as a subprocess
    cmd = [sys.executable, "-m", "src.marcus_mcp.server"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,  # Unbuffered
        cwd="/Users/lwgray/dev/marcus"
    )
    
    try:
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test_client",
                    "version": "1.0.0"
                }
            }
        }
        
        request_str = json.dumps(init_request) + "\n"
        print(f"Sending: {request_str.strip()}")
        proc.stdin.write(request_str)
        proc.stdin.flush()
        
        # Read response with timeout
        response_line = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, proc.stdout.readline),
            timeout=5.0
        )
        
        if response_line:
            print(f"Received: {response_line.strip()}")
            response = json.loads(response_line)
            if "error" in response:
                print(f"❌ Error: {response['error']}")
            else:
                print("✅ Successfully initialized!")
                
                # Try calling ping tool
                ping_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "ping",
                        "arguments": {"echo": "hello"}
                    }
                }
                
                request_str = json.dumps(ping_request) + "\n"
                print(f"\nSending: {request_str.strip()}")
                proc.stdin.write(request_str)
                proc.stdin.flush()
                
                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, proc.stdout.readline),
                    timeout=5.0
                )
                
                if response_line:
                    print(f"Received: {response_line.strip()}")
                    print("✅ MCP communication is working!")
        else:
            print("❌ No response received")
            
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for response")
        # Check stderr for any error messages
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"\nStderr output:\n{stderr_output}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    asyncio.run(test_minimal_mcp())