#!/usr/bin/env python3
"""
Simple PM Agent Test - Tests core functionality without hanging
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
print("Testing imports...")
try:
    from pm_agent_mvp_fixed import PMAgentMVP
    print("✅ PM Agent MVP imported")
except Exception as e:
    print(f"❌ Failed to import PM Agent: {e}")
    sys.exit(1)


async def test_pm_agent_server():
    """Test PM Agent server-side functionality"""
    print("\n🚀 Testing PM Agent Server Functions")
    print("=" * 50)
    
    # Create PM Agent instance (without starting server)
    pm_agent = PMAgentMVP()
    
    # Test 1: Agent Registration
    print("\n1️⃣ Testing Agent Registration")
    try:
        result = await pm_agent._register_agent(
            agent_id="test_dev_1",
            name="Alice Developer",
            role="Backend Developer",
            skills=["python", "fastapi", "postgresql"]
        )
        
        if result.get("success"):
            print(f"✅ Agent registered: {result['agent_data']['name']}")
        else:
            print(f"❌ Registration failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        
    # Test 2: List Agents
    print("\n2️⃣ Testing List Agents")
    try:
        result = await pm_agent._list_registered_agents()
        
        if result.get("success"):
            print(f"✅ Found {result['agent_count']} agents:")
            for agent in result["agents"]:
                print(f"   - {agent['name']} ({agent['role']})")
        else:
            print(f"❌ List failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ List error: {e}")
        
    # Test 3: Get Agent Status
    print("\n3️⃣ Testing Get Agent Status")
    try:
        result = await pm_agent._get_agent_status("test_dev_1")
        
        if result.get("found"):
            info = result["agent_info"]
            print(f"✅ Agent status retrieved:")
            print(f"   Name: {info['name']}")
            print(f"   Role: {info['role']}")
            print(f"   Skills: {', '.join(info['skills'])}")
        else:
            print(f"❌ Status failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Status error: {e}")
        
    print("\n" + "=" * 50)
    print("✅ Server-side tests completed!")


async def test_kanban_connection():
    """Test just the Kanban connection separately"""
    print("\n🔗 Testing Kanban Connection")
    print("=" * 50)
    
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"]
    )
    
    try:
        print("Connecting to Kanban MCP...")
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connected to Kanban MCP")
                
                # Get projects
                result = await session.call_tool("mcp_kanban_project_board_manager", {
                    "action": "get_projects",
                    "page": 1,
                    "perPage": 25
                })
                
                print(f"✅ Projects retrieved: {type(result)}")
                
    except Exception as e:
        print(f"❌ Kanban connection failed: {e}")
        import traceback
        traceback.print_exc()


async def test_full_workflow():
    """Test a complete workflow with Kanban integration"""
    print("\n🔄 Testing Full Workflow (with Kanban)")
    print("=" * 50)
    
    pm_agent = PMAgentMVP()
    
    try:
        # Initialize connections
        print("Initializing PM Agent with Kanban...")
        await pm_agent.kanban_client.connect()
        await pm_agent.ai_engine.initialize()
        print("✅ PM Agent initialized with Kanban")
        
        # Register agent
        print("\nRegistering agent...")
        await pm_agent._register_agent(
            agent_id="workflow_test_1",
            name="Bob Builder",
            role="Full Stack Developer",
            skills=["javascript", "react", "nodejs"]
        )
        
        # Request task
        print("\nRequesting task...")
        result = await pm_agent._request_next_task("workflow_test_1")
        
        if result.get("has_task"):
            assignment = result["assignment"]
            print(f"✅ Task assigned: {assignment['task_name']}")
            print(f"   Priority: {assignment['priority']}")
            print(f"   Task ID: {assignment['task_id']}")
            
            # Report progress
            print("\nReporting progress...")
            progress_result = await pm_agent._report_task_progress(
                agent_id="workflow_test_1",
                task_id=assignment['task_id'],
                status="in_progress",
                progress=25,
                message="Started working on the task"
            )
            
            if progress_result.get("acknowledged"):
                print("✅ Progress reported")
            
        else:
            print(f"⚠️ No tasks available: {result.get('message')}")
            
        # Get project status
        print("\nGetting project status...")
        status = await pm_agent._get_project_status()
        
        if status.get("success"):
            stats = status["project_status"]
            print(f"✅ Project Status:")
            print(f"   Total cards: {stats['total_cards']}")
            print(f"   Completion: {stats['completion_percentage']}%")
            
        # Cleanup
        await pm_agent.kanban_client.disconnect()
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    print("🧪 PM Agent Test Suite")
    print("=" * 70)
    
    # Test server functions first (no Kanban needed)
    await test_pm_agent_server()
    
    # Test Kanban connection separately
    await test_kanban_connection()
    
    # Test full workflow
    await test_full_workflow()
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())