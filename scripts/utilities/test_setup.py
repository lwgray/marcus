#!/usr/bin/env python3
"""
Quick test to verify PM Agent setup
"""

import os
import subprocess
import json
import sys

print("🔍 PM Agent Setup Verification")
print("=" * 60)

# 1. Check environment
print("\n1. Checking environment:")
checks = {
    "Python": sys.version.split()[0],
    "Working directory": os.getcwd(),
    "Config exists": os.path.exists("config_pm_agent.json")
}

for key, value in checks.items():
    print(f"   {key}: {value}")

# 2. Check config
if os.path.exists("config_pm_agent.json"):
    with open("config_pm_agent.json") as f:
        config = json.load(f)
    print(f"\n2. Configuration:")
    print(f"   Project: {config.get('project_name', 'Not set')}")
    print(f"   Board: {config.get('board_name', 'Not set')}")
    print(f"   Board ID: {config.get('board_id', 'Not set')}")

# 3. Check kanban-mcp
print("\n3. Checking kanban-mcp:")
kanban_path = "../kanban-mcp/dist/index.js"
if os.path.exists(kanban_path):
    print("   ✅ kanban-mcp is installed")
    print("   (It will start automatically when needed)")
else:
    print("   ❌ kanban-mcp NOT found at ../kanban-mcp")
    print("   Please install kanban-mcp")

# 4. Check Planka
print("\n4. Checking Planka:")
try:
    import requests
    response = requests.get("http://localhost:3333", timeout=2)
    if response.status_code == 200:
        print("   ✅ Planka is running at http://localhost:3333")
    else:
        print(f"   ⚠️  Planka returned status {response.status_code}")
except:
    print("   ❌ Planka is NOT accessible at http://localhost:3333")
    print("   Make sure Planka/Docker is running")

# 5. Summary
print("\n" + "=" * 60)
print("📋 Next Steps:")
print("\n1. To view the board:")
print("   python view_todo_board.py")
print("\n2. To run interactive tests:")
print("   python interactive_test.py")
print("\n3. To run the full test:")
print("   python scripts/test_pm_agent_end_to_end.py")
print("\n4. To start PM Agent as MCP server:")
print("   python start_pm_agent_task_master.py")
print("\nNote: kanban-mcp starts automatically when scripts connect to it!")