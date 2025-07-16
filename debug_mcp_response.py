#!/usr/bin/env python3
"""
Debug script to test MCP response handling
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime


async def test_mcp_response():
    """Test if MCP server is properly returning responses"""

    # Start the MCP server
    cmd = [sys.executable, "-m", "src.marcus_mcp.server"]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,  # Unbuffered
    )

    try:
        # Wait for server to start
        await asyncio.sleep(2)

        # Send a simple ping request
        ping_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "ping", "arguments": {"echo": "test"}},
            "id": 1,
        }

        print(f"[{datetime.now()}] Sending ping request...")
        process.stdin.write(json.dumps(ping_request) + "\n")
        process.stdin.flush()

        # Try to read response
        print(f"[{datetime.now()}] Waiting for response...")
        response_line = process.stdout.readline()
        if response_line:
            print(f"[{datetime.now()}] Received response: {response_line}")
        else:
            print(f"[{datetime.now()}] No response received")

        # Now try create_project
        create_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "create_project",
                "arguments": {
                    "description": "Simple test project",
                    "project_name": "Test Project",
                    "options": {"complexity": "prototype"},
                },
            },
            "id": 2,
        }

        print(f"[{datetime.now()}] Sending create_project request...")
        process.stdin.write(json.dumps(create_request) + "\n")
        process.stdin.flush()

        # Try to read response with timeout
        print(f"[{datetime.now()}] Waiting for create_project response...")
        try:
            # Use asyncio to implement timeout
            reader = asyncio.create_task(asyncio.to_thread(process.stdout.readline))
            response_line = await asyncio.wait_for(reader, timeout=30.0)
            print(f"[{datetime.now()}] Received response: {response_line}")
        except asyncio.TimeoutError:
            print(f"[{datetime.now()}] Timeout waiting for response")

    finally:
        process.terminate()


if __name__ == "__main__":
    asyncio.run(test_mcp_response())
