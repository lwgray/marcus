#!/usr/bin/env python3
"""
Test the fixed get_project_status by calling it directly through the MCP server
"""

import asyncio
import json
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer


async def test_fixed_get_project_status():
    """Test that get_project_status now works with the config loading fix"""
    
    print("=== Testing Fixed get_project_status ===\n")
    
    # Create a Marcus server instance (this simulates what happens in MCP)
    server = MarcusServer()
    
    print("1. Created Marcus server instance")
    
    # Test the get_project_status function directly
    from src.marcus_mcp.tools.project_tools import get_project_status
    
    print("2. Calling get_project_status...")
    
    try:
        result = await get_project_status(server)
        
        print("3. Result:")
        print(json.dumps(result, indent=2))
        
        if result.get("success"):
            print("\n✅ get_project_status is now working!")
            print("   The MCP tool should work correctly now.")
        else:
            print(f"\n❌ Still failing: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fixed_get_project_status())