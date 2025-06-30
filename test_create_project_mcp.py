#!/usr/bin/env python3
"""
Test the create_project MCP tool properly
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# This script assumes marcus.py is already running as an MCP server
print("=== Testing MCP create_project Tool ===\n")
print("IMPORTANT: This test requires marcus.py to be running in another terminal!")
print("If not running, open a new terminal and run: python marcus.py\n")

input("Press Enter when marcus.py is running...")

# Now let's check how to properly call the MCP tool
print("\nThe create_project tool should be called through an MCP client that connects")
print("to the already-running Marcus server.\n")

print("Since Marcus is designed to be used with Claude Desktop or other MCP clients,")
print("the typical usage would be:\n")

print("1. Start Marcus MCP server: python marcus.py")
print("2. Configure your MCP client (e.g., Claude Desktop) to connect to Marcus")
print("3. Use the tool through the client interface\n")

print("For testing without an MCP client, you can use the direct API:")
print("python create_recipe_project_simple.py\n")

print("The timeout you're experiencing is likely because:")
print("1. The MCP client (Claude) has a default timeout of 2 minutes")
print("2. The AI processing for large projects takes longer than this")
print("3. Marcus doesn't implement progress streaming for long operations\n")

print("Possible solutions:")
print("1. Configure longer timeout in your MCP client settings")
print("2. Use smaller project descriptions to reduce processing time")
print("3. Use the direct Python API instead of MCP for large projects")
print("4. Implement progress streaming in Marcus (requires code changes)")

# Let's also check if we can find MCP client configuration
config_locations = [
    "~/.claude/config.json",
    "~/.config/claude/config.json",
    "~/Library/Application Support/Claude/config.json"
]

print("\nChecking for MCP client configuration files...")
for loc in config_locations:
    expanded = os.path.expanduser(loc)
    if os.path.exists(expanded):
        print(f"✓ Found config at: {expanded}")
        print("  You can add timeout settings here")
        break
else:
    print("✗ No MCP client configuration found")
    print("  This might be configured in your MCP client directly")