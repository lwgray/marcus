#!/usr/bin/env python3
"""
Debug and fix the MCP create_project timeout issue
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("=== MCP Create Project Timeout Fix ===\n")

# 1. Check Marcus server status
print("1. Checking Marcus server status...")
import subprocess
result = subprocess.run(['lsof', '-i', ':3000'], capture_output=True, text=True)
if 'LISTEN' in result.stdout:
    print("   ✗ Port 3000 is occupied (likely by Docker)")
    print("   Fix: Marcus MCP server needs a different port\n")
else:
    print("   ✓ Port 3000 is available\n")

# 2. Check for timeout settings
print("2. Checking MCP timeout settings...")
mcp_files = [
    "src/marcus_mcp/server.py",
    "src/marcus_mcp/handlers.py",
    "src/ai/advanced/prd/advanced_parser.py"
]

for file in mcp_files:
    if os.path.exists(file):
        with open(file, 'r') as f:
            content = f.read()
            if 'timeout' in content.lower():
                print(f"   Found timeout reference in {file}")

print("\n3. Identified issues:")
print("   a) Port 3000 conflict with Docker")
print("   b) AI processing taking too long for MCP timeout")
print("   c) No chunking/streaming for long operations")

print("\n4. Recommended fixes:")
print("   a) Change Marcus MCP server port to 3001")
print("   b) Add timeout configuration to MCP handlers")
print("   c) Implement progress reporting for long operations")
print("   d) Add simplified/fast mode for project creation")

print("\n5. Quick fix - Create a wrapper with longer timeout:")
print("""
# In your MCP client configuration, add:
"create_project": {
    "timeout": 300000  # 5 minutes instead of default 2 minutes
}
""")

print("\n6. Alternative approach:")
print("   Use the direct Python API instead of MCP for long operations")
print("   Example: python create_recipe_project_simple.py")