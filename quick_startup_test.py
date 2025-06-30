#!/usr/bin/env python3
"""
Quick test to see if Marcus can initialize without errors
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("=== Quick Marcus Startup Test ===\n")

try:
    print("1. Testing imports...")
    from src.marcus_mcp.server import MarcusServer
    print("   ✓ MCP server imports successful")
    
    print("\n2. Testing server creation...")
    server = MarcusServer()
    print("   ✓ Marcus server created successfully")
    print(f"   ✓ Provider: {server.provider}")
    
    print("\n3. Testing configuration loading...")
    # This should trigger the config loading
    server._ensure_environment_config()
    print("   ✓ Configuration loaded")
    
    print(f"\n✅ Marcus initialization successful!")
    print("\nYou can now start Marcus with: python marcus.py")
    print("Then connect via your MCP client")
    
except Exception as e:
    print(f"\n❌ Marcus initialization failed: {e}")
    import traceback
    traceback.print_exc()
    print("\nFix these issues before starting Marcus")