#!/usr/bin/env python3
"""
Focused PM Agent Test Suite - Tests both server and client functionality
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pm_agent_mvp_fixed import PMAgentMVP


async def test_pm_agent_server_side():
    """Test PM Agent MCP Server functionality (without Kanban)"""
    print("\n🖥️  Testing PM Agent Server-Side (MCP Tools)")
    print("=" * 50)
    
    # Create PM Agent instance
    pm_agent = PMAgentMVP()
    
    # Test 1: Agent Registration
    print("\n1️⃣  Agent Registration")
    result = await pm_agent._register_agent(
        agent_id="backend_dev_1",
        name="Alice Backend",
        role="Backend Developer", 
        skills=["python", "django", "postgresql"]
    )
    print(f"   Result: {json.dumps(result, indent=2)}")
    
    # Test 2: Register another agent
    print("\n2️⃣  Register Second Agent")
    result = await pm_agent._register_agent(
        agent_id="frontend_dev_1",
        name="Bob Frontend",
        role="Frontend Developer",
        skills=["javascript", "react", "css"]
    )
    print(f"   Result: {json.dumps(result, indent=2)}")
    
    # Test 3: List all agents
    print("\n3️⃣  List Registered Agents")
    result = await pm_agent._list_registered_agents()
    print(f"   Found {result.get('agent_count', 0)} agents")
    for agent in result.get("agents", []):
        print(f"   - {agent['name']} ({agent['role']})")
    
    # Test 4: Get specific agent status
    print("\n4️⃣  Get Agent Status")
    result = await pm_agent._get_agent_status("backend_dev_1")
    if result.get("found"):
        print(f"   Agent: {result['agent_info']['name']}")
        print(f"   Skills: {', '.join(result['agent_info']['skills'])}")
    
    print("\n✅ Server-side tests completed (no Kanban needed)")
    return pm_agent


async def test_kanban_mcp_connection():
    """Test direct connection to Kanban MCP server"""
    print("\n🔗 Testing Kanban MCP Connection")
    print("=" * 50)
    
    server_params = StdioServerParameters(
        command="/Users/lwgray/.nvm/versions/node/v22.14.0/bin/node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env={
            "PLANKA_BASE_URL": "http://localhost:3333",
            "PLANKA_AGENT_EMAIL": "demo@demo.demo",
            "PLANKA_AGENT_PASSWORD": "demo"
        }
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connected to Kanban MCP")
                
                # Test getting projects
                print("\n   Testing get_projects...")
                result = await session.call_tool("mcp_kanban_project_board_manager", {
                    "action": "get_projects",
                    "page": 1,
                    "perPage": 25
                })
                
                projects = result.get("items", []) if isinstance(result, dict) else result
                print(f"   Found {len(projects) if isinstance(projects, list) else 1} projects")
                
                # Find Task Master Test project
                for project in (projects if isinstance(projects, list) else [projects]):
                    if "Task Master Test" in project.get("name", ""):
                        print(f"   ✅ Found Task Master Test project (ID: {project['id']})")
                        return True
                        
                print("   ⚠️  Task Master Test project not found")
                return True  # Connection still works
                
    except Exception as e:
        print(f"❌ Kanban connection failed: {e}")
        return False


async def test_pm_agent_with_kanban():
    """Test PM Agent with Kanban integration"""
    print("\n🔄 Testing PM Agent + Kanban Integration")
    print("=" * 50)
    
    pm_agent = PMAgentMVP()
    
    try:
        # Initialize Kanban connection
        print("\nConnecting PM Agent to Kanban...")
        await pm_agent.kanban_client.connect()
        print(f"✅ Connected to board: {pm_agent.kanban_client.board_id}")
        
        # Initialize AI engine
        await pm_agent.ai_engine.initialize()
        print("✅ AI engine initialized")
        
        # Register an agent if not already done
        agent_id = "test_fullstack_1"
        if agent_id not in pm_agent.agent_status:
            print("\nRegistering test agent...")
            await pm_agent._register_agent(
                agent_id=agent_id,
                name="Charlie Fullstack",
                role="Full Stack Developer",
                skills=["python", "javascript", "docker"]
            )
        
        # Test task request
        print("\n📝 Requesting task for agent...")
        result = await pm_agent._request_next_task(agent_id)
        
        if result.get("has_task"):
            assignment = result["assignment"]
            print(f"✅ Task assigned!")
            print(f"   Task: {assignment['task_name']}")
            print(f"   ID: {assignment['task_id']}")
            print(f"   Priority: {assignment['priority']}")
            print(f"   Instructions preview: {assignment['instructions'][:150]}...")
            
            # Test progress reporting
            print("\n📊 Testing progress report...")
            progress_result = await pm_agent._report_task_progress(
                agent_id=agent_id,
                task_id=assignment['task_id'],
                status="in_progress",
                progress=30,
                message="Initial setup completed, starting implementation"
            )
            print(f"   Progress reported: {progress_result.get('acknowledged')}")
            
            # Test blocker
            print("\n🚧 Testing blocker report...")
            blocker_result = await pm_agent._report_blocker(
                agent_id=agent_id,
                task_id=assignment['task_id'],
                blocker_description="Missing API documentation for third-party service integration",
                severity="medium"
            )
            if blocker_result.get("success"):
                print("   ✅ Blocker reported")
                print(f"   Resolution preview: {blocker_result['resolution_suggestion'][:150]}...")
                
        else:
            print(f"⚠️  No tasks available: {result.get('message', 'Unknown reason')}")
        
        # Test project status
        print("\n📈 Testing project status...")
        status_result = await pm_agent._get_project_status()
        if status_result.get("success"):
            stats = status_result["project_status"]
            print(f"   Total cards: {stats['total_cards']}")
            print(f"   Completion: {stats['completion_percentage']}%")
            print(f"   In Progress: {stats['in_progress_count']}")
        
        # Cleanup
        await pm_agent.kanban_client.disconnect()
        print("\n✅ PM Agent + Kanban integration tests completed")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all focused tests"""
    print("🧪 PM Agent Focused Test Suite")
    print("=" * 70)
    
    # Test 1: PM Agent Server-side (no external dependencies)
    await test_pm_agent_server_side()
    
    # Test 2: Kanban MCP connection only
    kanban_works = await test_kanban_mcp_connection()
    
    if kanban_works:
        # Test 3: Full integration
        await test_pm_agent_with_kanban()
    else:
        print("\n⚠️  Skipping integration tests due to Kanban connection issue")
    
    print("\n" + "=" * 70)
    print("✅ Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())