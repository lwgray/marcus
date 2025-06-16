#!/usr/bin/env python3
"""
Quick start script for PM Agent
"""

import os
import sys
import subprocess
import asyncio


def check_prerequisites():
    """Check all prerequisites are met"""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print("✅ Python version OK")
    
    # Check environment variables
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set - AI features will use fallback mode")
    else:
        print("✅ ANTHROPIC_API_KEY found")
    
    # Check Planka
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:3333"],
            capture_output=True,
            text=True
        )
        if result.stdout == "200":
            print("✅ Planka is running")
        else:
            print("❌ Planka not accessible at http://localhost:3333")
            return False
    except:
        print("⚠️  Could not check Planka status")
    
    # Check config
    if os.path.exists("config_pm_agent.json"):
        print("✅ Configuration file found")
    else:
        print("❌ config_pm_agent.json not found")
        print("   Run: python scripts/setup/configure_board.py YOUR_BOARD_ID")
        return False
    
    return True


async def quick_test_connection():
    """Quick test of kanban connection"""
    print("\n🔌 Testing Kanban connection...")
    
    try:
        from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient
        import json
        
        with open("config_pm_agent.json", "r") as f:
            config = json.load(f)
        
        client = MCPKanbanClient()
        client.project_id = config.get("project_id")
        client.board_id = config.get("board_id")
        
        async with asyncio.timeout(5):
            async with client.connect() as conn:
                print("✅ Kanban connection successful")
                return True
                
    except asyncio.TimeoutError:
        print("❌ Kanban connection timed out")
        print("\nTry starting Kanban MCP manually:")
        print("cd /Users/lwgray/dev/kanban-mcp")
        print("node dist/index.js")
        return False
    except Exception as e:
        print(f"❌ Kanban connection failed: {e}")
        return False


def main():
    """Main quick start function"""
    print("🚀 PM Agent Quick Start")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above.")
        return 1
    
    # Test connection
    if not asyncio.run(quick_test_connection()):
        print("\n❌ Connection test failed. Please check Kanban MCP.")
        return 1
    
    print("\n✅ All checks passed!")
    print("\n📋 Starting PM Agent...")
    print("-" * 50)
    
    # Start PM Agent
    try:
        subprocess.run([sys.executable, "pm_agent_mvp_fixed.py"])
    except KeyboardInterrupt:
        print("\n\n👋 PM Agent stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())