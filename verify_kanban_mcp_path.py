#!/usr/bin/env python3
"""
Verify kanban-mcp path configuration
"""

import os
import sys
import json

# Expected path
EXPECTED_PATH = "/Users/lwgray/dev/kanban-mcp/dist/index.js"

print("🔍 Verifying kanban-mcp path configuration")
print("=" * 60)

# Check if the path exists
if os.path.exists(EXPECTED_PATH):
    print(f"✅ kanban-mcp found at: {EXPECTED_PATH}")
else:
    print(f"❌ kanban-mcp NOT found at: {EXPECTED_PATH}")
    print("\nPlease ensure kanban-mcp is located at the expected path.")
    sys.exit(1)

# Check Python files
print("\n📄 Checking Python files...")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient

client = MCPKanbanClient()
if client._kanban_mcp_path == EXPECTED_PATH:
    print(f"✅ MCPKanbanClient uses correct path: {client._kanban_mcp_path}")
else:
    print(f"❌ MCPKanbanClient uses incorrect path: {client._kanban_mcp_path}")

# Check if Node.js can run it
print("\n🔧 Checking if kanban-mcp is executable...")
try:
    import subprocess
    result = subprocess.run(
        ["node", "--version"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"✅ Node.js available: {result.stdout.strip()}")
        
        # Try to run kanban-mcp with --help or --version
        result = subprocess.run(
            ["node", EXPECTED_PATH, "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "kanban" in result.stdout.lower() or "mcp" in result.stdout.lower():
            print("✅ kanban-mcp appears to be working")
        else:
            print("⚠️  kanban-mcp ran but output unexpected")
    else:
        print("❌ Node.js not available")
except Exception as e:
    print(f"⚠️  Could not test kanban-mcp execution: {e}")

print("\n✅ Path verification complete")
print(f"\nAll components should use: {EXPECTED_PATH}")
print("\nIf you're seeing errors, ensure:")
print("1. kanban-mcp is at the expected location")
print("2. Node.js is installed and accessible")
print("3. kanban-mcp dependencies are installed (npm install)")