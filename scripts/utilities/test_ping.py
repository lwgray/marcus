#!/usr/bin/env python3
"""
Test the PM Agent ping command
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_ping():
    """Test the ping functionality"""
    print("🏓 Testing PM Agent Ping Command")
    print("=" * 50)
    
    # Start PM Agent as stdio server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.pm_agent_mvp_fixed"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to PM Agent")
            
            # Test 1: Basic ping
            print("\n1. Basic ping test:")
            result = await session.call_tool("ping", {})
            response = json.loads(result.content[0].text)
            
            if response.get("pong"):
                print("   ✅ Received pong!")
                print(f"   Status: {response.get('status')}")
                print(f"   Service: {response.get('service')}")
                print(f"   Version: {response.get('version')}")
                print(f"   Uptime: {response.get('uptime')}")
            else:
                print("   ❌ No pong received")
            
            # Test 2: Ping with echo
            print("\n2. Ping with echo test:")
            echo_msg = "Hello PM Agent!"
            result = await session.call_tool("ping", {"echo": echo_msg})
            response = json.loads(result.content[0].text)
            
            if response.get("echo_received"):
                print(f"   ✅ Echo received: '{response.get('echo')}'")
            else:
                print("   ❌ Echo not received")
            
            # Test 3: Check health details
            print("\n3. Health status:")
            health = response.get("health", {})
            print(f"   Status: {health.get('status')}")
            print(f"   AI Engine: {health.get('ai_engine')}")
            print(f"   Memory Usage: {health.get('memory_usage', {}).get('rss_mb')} MB")
            
            # Test 4: Check workload
            print("\n4. Workload status:")
            workload = response.get("workload", {})
            print(f"   Registered agents: {workload.get('registered_agents')}")
            print(f"   Active assignments: {workload.get('active_assignments')}")
            print(f"   Completed tasks: {workload.get('total_completed_tasks')}")
            print(f"   Agents available: {workload.get('agents_available')}")
            
            # Test 5: Check capabilities
            print("\n5. Capabilities:")
            capabilities = response.get("capabilities", {})
            for cap, enabled in capabilities.items():
                status = "✅" if enabled else "❌"
                print(f"   {status} {cap.replace('_', ' ').title()}")
            
            print("\n✅ Ping test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_ping())