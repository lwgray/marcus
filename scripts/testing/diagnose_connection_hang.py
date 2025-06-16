#!/usr/bin/env python3
"""
Diagnostic script to debug why select_task_master_board.py is hanging
"""

import asyncio
import json
import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

async def test_connection():
    """Test the connection step by step"""
    print("🔍 Starting connection diagnostics...")
    print("=" * 60)
    
    # Check kanban-mcp path
    kanban_path = "/Users/lwgray/dev/kanban-mcp/dist/index.js"
    print(f"\n1. Checking kanban-mcp path:")
    print(f"   Path: {kanban_path}")
    print(f"   Exists: {os.path.exists(kanban_path)}")
    
    # Test basic import
    print("\n2. Testing import...")
    try:
        from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient
        print("   ✅ Import successful")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return
    
    # Test client creation
    print("\n3. Creating client...")
    try:
        client = MCPKanbanClient()
        client.project_id = "1533678301472621705"
        print(f"   ✅ Client created")
        print(f"   Project ID: {client.project_id}")
        print(f"   Kanban MCP path: {client._kanban_mcp_path}")
    except Exception as e:
        print(f"   ❌ Client creation failed: {e}")
        return
    
    # Test connection with timeout
    print("\n4. Testing connection (10 second timeout)...")
    try:
        async def connect_with_timeout():
            async with client.connect() as conn:
                print("   ✅ Connection established!")
                return True
        
        result = await asyncio.wait_for(connect_with_timeout(), timeout=10.0)
        print(f"   Connection result: {result}")
        
    except asyncio.TimeoutError:
        print("   ❌ Connection timed out after 10 seconds")
        print("\n   Possible issues:")
        print("   - kanban-mcp server not running")
        print("   - Wrong path to kanban-mcp")
        print("   - Port conflict")
        print("   - Node.js issues")
    except Exception as e:
        print(f"   ❌ Connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # Test direct node execution
    print("\n5. Testing direct node execution...")
    try:
        import subprocess
        result = subprocess.run(
            ["node", kanban_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"   Return code: {result.returncode}")
        print(f"   Stdout: {result.stdout}")
        print(f"   Stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("   ❌ Node execution timed out")
    except Exception as e:
        print(f"   ❌ Node execution failed: {e}")
    
    # Check if kanban-mcp process is running
    print("\n6. Checking for running kanban-mcp processes...")
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        kanban_processes = [line for line in result.stdout.split('\n') if 'kanban-mcp' in line and 'grep' not in line]
        if kanban_processes:
            print("   Found running kanban-mcp processes:")
            for proc in kanban_processes:
                print(f"   - {proc[:100]}...")
        else:
            print("   ⚠️  No kanban-mcp processes found")
    except Exception as e:
        print(f"   ❌ Process check failed: {e}")

    # Check environment variables
    print("\n7. Checking environment variables...")
    env_vars = ['PLANKA_BASE_URL', 'PLANKA_AGENT_EMAIL', 'PLANKA_AGENT_PASSWORD']
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"   ✅ {var}: {value[:20]}...")
        else:
            print(f"   ⚠️  {var}: Not set")

if __name__ == "__main__":
    asyncio.run(test_connection())