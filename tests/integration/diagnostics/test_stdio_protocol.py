#!/usr/bin/env python3
"""
Test kanban-mcp with low-level stdio protocol
Useful for debugging protocol-level communication issues
"""

import asyncio
import json
import os
import sys
from typing import Optional

# Add parent directories to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


async def test_stdio_protocol() -> None:
    """Test with raw MCP stdio protocol"""
    print("🔍 Testing kanban-mcp stdio protocol (low-level)")
    print("=" * 60)

    # Try to find node and kanban-mcp
    node_paths = [
        "node",
        "/opt/homebrew/bin/node",
        "/usr/local/bin/node",
        os.path.expanduser("~/.nvm/versions/node/v22.14.0/bin/node"),
    ]

    node_cmd: Optional[str] = None
    for path in node_paths:
        if os.path.exists(path) or os.system(f"which {path} > /dev/null 2>&1") == 0:
            node_cmd = path
            break

    if not node_cmd:
        print("❌ Could not find node executable")
        return

    kanban_paths = [
        "../../../kanban-mcp/dist/index.js",
        "../../kanban-mcp/dist/index.js",
        "../kanban-mcp/dist/index.js",
        os.path.expanduser("~/dev/kanban-mcp/dist/index.js"),
    ]

    kanban_path: Optional[str] = None
    for path in kanban_paths:
        if os.path.exists(path):
            kanban_path = path
            break

    if not kanban_path:
        print("❌ Could not find kanban-mcp/dist/index.js")
        return

    print(f"Using node: {node_cmd}")
    print(f"Using kanban-mcp: {kanban_path}")

    # Start the process
    process = await asyncio.create_subprocess_exec(
        node_cmd,
        kanban_path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            "PLANKA_BASE_URL": "http://localhost:3333",
            "PLANKA_AGENT_EMAIL": "demo@demo.demo",
            "PLANKA_AGENT_PASSWORD": "demo",
        },
    )

    print("\n1. Process started")
    print(f"   PID: {process.pid}")

    # MCP servers expect an initialization message
    init_message = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
        "id": 1,
    }

    try:
        # Send initialization
        print("\n2. Sending initialization...")
        message = json.dumps(init_message) + "\n"
        if process.stdin:
            process.stdin.write(message.encode())
            await process.stdin.drain()

        # Read response with timeout
        print("3. Waiting for response...")
        async with asyncio.timeout(5):
            response = await process.stdout.readline() if process.stdout else b""
            if response:
                print(f"✅ Got response: {response.decode().strip()}")
                try:
                    data = json.loads(response.decode())
                    print(
                        f"   Response type: {data.get('result', {}).get('protocolVersion', 'unknown')}"
                    )
                except:
                    pass
            else:
                print("❌ No response")

            # Check stderr for errors
            stderr_task = (
                asyncio.create_task(process.stderr.read()) if process.stderr else None
            )
            if stderr_task:
                try:
                    async with asyncio.timeout(1):
                        stderr = await stderr_task
                        if stderr:
                            print(f"\nStderr output: {stderr.decode()}")
                except asyncio.TimeoutError:
                    pass

        # Send initialized notification
        print("\n4. Sending initialized notification...")
        initialized_msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        message = json.dumps(initialized_msg) + "\n"
        if process.stdin:
            process.stdin.write(message.encode())
            await process.stdin.drain()

        # Try a tool call
        print("\n5. Testing tool call...")
        tool_call = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "mcp_kanban_project_board_manager",
                "arguments": {"action": "get_projects", "page": 1, "perPage": 5},
            },
            "id": 2,
        }
        message = json.dumps(tool_call) + "\n"
        if process.stdin:
            process.stdin.write(message.encode())
            await process.stdin.drain()

        async with asyncio.timeout(5):
            response = await process.stdout.readline() if process.stdout else b""
            if response:
                print(f"✅ Got tool response")
                data = json.loads(response.decode())
                if "result" in data:
                    print("   Tool call successful")
                elif "error" in data:
                    print(f"   Tool error: {data['error']}")

    except asyncio.TimeoutError:
        print("❌ Timeout waiting for response")

        # Check if process is still running
        if process.returncode is None:
            print("   Process is still running")
            # Try to get any error output
            try:
                if process.stderr:
                    stderr = await asyncio.wait_for(
                        process.stderr.read(1000), timeout=1
                    )
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
            print("\n6. Process terminated")


if __name__ == "__main__":
    asyncio.run(test_stdio_protocol())
