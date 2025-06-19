#!/usr/bin/env python3
"""
Test PM Agent locally with kanban-mcp
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import PM Agent components
from src.integrations.kanban_factory import KanbanFactory
from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine
from src.monitoring.project_monitor import ProjectMonitor
from src.communication.communication_hub import CommunicationHub
from src.logging.conversation_logger import conversation_logger


async def test_pm_agent():
    """Test PM Agent with kanban-mcp"""
    print("🚀 Testing PM Agent with kanban-mcp...")
    print(f"   Kanban Provider: {os.getenv('KANBAN_PROVIDER', 'planka')}")
    
    # Create kanban client
    print("\n1️⃣ Creating Kanban Client...")
    try:
        kanban_client = KanbanFactory.create_default()
        print("   ✅ Kanban client created")
    except Exception as e:
        print(f"   ❌ Failed to create kanban client: {e}")
        return
    
    # Connect to kanban
    print("\n2️⃣ Connecting to Planka...")
    try:
        connected = await kanban_client.connect()
        if connected:
            print("   ✅ Connected to Planka")
        else:
            print("   ❌ Failed to connect to Planka")
            return
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return
    
    # Get available tasks
    print("\n3️⃣ Getting available tasks...")
    try:
        tasks = await kanban_client.get_available_tasks()
        print(f"   ✅ Found {len(tasks)} available tasks")
        
        if tasks:
            print("\n   📋 Available tasks:")
            for i, task in enumerate(tasks[:5]):  # Show first 5
                print(f"      {i+1}. {task.name} (ID: {task.id}, Priority: {task.priority.value})")
        else:
            print("   ℹ️  No tasks available in Planka")
    except Exception as e:
        print(f"   ❌ Failed to get tasks: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test AI Engine
    print("\n4️⃣ Testing AI Analysis Engine...")
    try:
        ai_engine = AIAnalysisEngine()
        await ai_engine.initialize()
        if ai_engine.client:
            print("   ✅ AI Engine initialized with Anthropic")
        else:
            print("   ⚠️  AI Engine in fallback mode (no API key)")
    except Exception as e:
        print(f"   ❌ AI Engine error: {e}")
    
    # Disconnect
    print("\n5️⃣ Disconnecting...")
    await kanban_client.disconnect()
    print("   ✅ Disconnected")
    
    print("\n✨ PM Agent test complete!")


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run test
    asyncio.run(test_pm_agent())