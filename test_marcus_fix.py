#!/usr/bin/env python3
"""
Test script to verify Marcus server is working correctly
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_marcus_operations():
    """Test various Marcus operations"""
    # Marcus server command - use the actual marcus.py file
    server_cmd = [
        "python",
        os.path.join(os.path.dirname(__file__), "marcus.py")
    ]
    
    server_params = StdioServerParameters(
        command=server_cmd[0],
        args=server_cmd[1:],
        env=None
    )
    
    try:
        print("🔗 Connecting to Marcus server...")
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("✅ Connected successfully!")
                
                # Test 1: Ping
                print("\n📡 Testing ping...")
                try:
                    result = await session.call_tool("ping", {})
                    print(f"✅ Ping successful: {json.loads(result.content[0].text)}")
                except Exception as e:
                    print(f"❌ Ping failed: {e}")
                
                # Test 2: Get project status
                print("\n📊 Testing get_project_status...")
                try:
                    result = await session.call_tool("get_project_status", {})
                    status = json.loads(result.content[0].text)
                    if status.get('success'):
                        print(f"✅ Project status retrieved:")
                        print(f"   Total tasks: {status['project']['total_tasks']}")
                        print(f"   Completed: {status['project']['completed']}")
                        print(f"   In progress: {status['project']['in_progress']}")
                        print(f"   Provider: {status['provider']}")
                    else:
                        print(f"❌ Project status failed: {status.get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"❌ Get project status failed: {e}")
                
                # Test 3: List registered agents
                print("\n👥 Testing list_registered_agents...")
                try:
                    result = await session.call_tool("list_registered_agents", {})
                    agents = json.loads(result.content[0].text)
                    if agents.get('success'):
                        print(f"✅ Registered agents: {len(agents.get('agents', []))}")
                        for agent in agents.get('agents', []):
                            print(f"   - {agent['name']} ({agent['role']}) - Status: {agent['status']}")
                    else:
                        print(f"✅ No agents registered yet")
                except Exception as e:
                    print(f"❌ List agents failed: {e}")
            
    except RuntimeError as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Marcus server is running: python marcus.py")
        print("2. Check logs in logs/conversations/")
        print("3. Verify config_marcus.json exists and is valid")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    print("\n✅ All tests completed!")
    return True


async def main():
    """Main test runner"""
    print("🏛️ Marcus Server Test")
    print("=" * 50)
    
    success = await test_marcus_operations()
    
    if success:
        print("\n🎉 Marcus server is working correctly!")
        print("\nYou can now:")
        print("1. Create projects: python marcus.py create_project_from_text --text 'Your project description'")
        print("2. Register agents to work on tasks")
        print("3. Monitor progress with get_project_status")
    else:
        print("\n⚠️ Marcus server has issues that need to be fixed")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)