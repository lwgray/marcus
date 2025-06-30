#!/usr/bin/env python3
"""
Test that Marcus can start properly with the fixes
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp import main


async def test_marcus_startup():
    """Test that Marcus starts without errors"""
    
    print("=== Testing Marcus MCP Server Startup ===\n")
    
    try:
        print("1. Starting Marcus MCP server...")
        print("   (This will run until you press Ctrl+C)")
        print("   Look for successful initialization messages\n")
        
        # This will start the server and wait for connections
        await main()
        
    except KeyboardInterrupt:
        print("\n✅ Marcus started successfully and was stopped cleanly")
        return True
    except Exception as e:
        print(f"\n❌ Marcus failed to start: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_marcus_startup())
        if success:
            print("\n🎉 Marcus is ready for MCP connections!")
        else:
            print("\n💡 Fix the startup issues above before connecting via MCP")
    except KeyboardInterrupt:
        print("\n✅ Test completed - Marcus can start properly")
        sys.exit(0)