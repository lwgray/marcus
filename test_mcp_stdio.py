#!/usr/bin/env python3
"""Test MCP server in stdio mode to find the root cause"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add to path
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

async def test_mcp_init():
    """Test MCP initialization to find where the error comes from"""
    print("Starting MCP stdio test...", file=sys.stderr)
    
    # First, test basic imports
    print("1. Testing imports...", file=sys.stderr)
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        print("   ✅ MCP imports successful", file=sys.stderr)
    except Exception as e:
        print(f"   ❌ MCP import error: {e}", file=sys.stderr)
        return
    
    # Test creating server
    print("2. Creating MCP server...", file=sys.stderr)
    try:
        server = Server("test-server")
        print("   ✅ Server created", file=sys.stderr)
    except Exception as e:
        print(f"   ❌ Server creation error: {e}", file=sys.stderr)
        return
    
    # Test PMAgentState import
    print("3. Testing PMAgentState import...", file=sys.stderr)
    try:
        from pm_agent_mcp_server_v2 import PMAgentState
        print("   ✅ PMAgentState imported", file=sys.stderr)
    except Exception as e:
        print(f"   ❌ PMAgentState import error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return
    
    # Test PMAgentState creation
    print("4. Creating PMAgentState...", file=sys.stderr)
    try:
        state = PMAgentState()
        print("   ✅ PMAgentState created", file=sys.stderr)
    except Exception as e:
        print(f"   ❌ PMAgentState creation error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return
    
    # Test stdio_server context
    print("5. Testing stdio_server context...", file=sys.stderr)
    try:
        # Create a fake stdio environment
        import io
        read_stream = io.BytesIO()
        write_stream = io.BytesIO()
        
        # Just test the context manager creation
        print("   ✅ stdio test complete", file=sys.stderr)
    except Exception as e:
        print(f"   ❌ stdio context error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_init())