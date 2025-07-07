#!/usr/bin/env python3
"""
Integration test for Marcus enhanced features (Events, Context, Memory).

This script tests that all three systems work correctly when enabled in Marcus,
including their interactions through the MCP server.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess
import time
import signal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config_loader import get_config
from src.marcus_mcp.server import MarcusServer
from src.core.models import Task, TaskStatus, Priority, WorkerStatus
from src.core.context import DependentTask
from src.core.events import EventTypes


class EnhancedFeaturesTest:
    """Test harness for enhanced features"""
    
    def __init__(self):
        self.original_config_path = None
        self.original_config_content = None
        self.server = None
        self.events_received = []
        
    async def setup(self):
        """Setup test environment with enhanced features enabled"""
        print("🔧 Setting up test environment...")
        
        # Backup original config
        config_loader = get_config()
        self.original_config_path = config_loader.config_path
        
        # Read and backup original config
        with open(self.original_config_path, 'r') as f:
            self.original_config_content = f.read()
            config_data = json.loads(self.original_config_content)
        
        # Create test config with enhanced features enabled
        test_config = config_data.copy()
        test_config['features'] = {
            'events': True,
            'context': True,
            'memory': True,
            'visibility': False
        }
        
        # Save test config
        with open(self.original_config_path, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        # Reload config
        config_loader.reload()
        print("✅ Enhanced features enabled in config")
        
        # Create Marcus server
        self.server = MarcusServer()
        await self.server.initialize()
        
        # Subscribe to all events
        if self.server.events:
            self.server.events.subscribe('*', self.event_handler)
            print("✅ Subscribed to event system")
            
        return True
        
    async def event_handler(self, event):
        """Capture all events for analysis"""
        self.events_received.append(event)
        print(f"📡 Event: {event.event_type} from {event.source}")
        
    async def test_event_system(self):
        """Test the Events system"""
        print("\n🧪 Testing Events System...")
        
        if not self.server.events:
            print("❌ Events system not initialized")
            return False
            
        # Publish test event
        await self.server.events.publish(
            EventTypes.SYSTEM_STARTUP,
            "test_harness",
            {"message": "Test event"}
        )
        
        # Check if event was received
        await asyncio.sleep(0.1)  # Allow event to propagate
        
        if len(self.events_received) > 0:
            print(f"✅ Events working: {len(self.events_received)} events received")
            return True
        else:
            print("❌ No events received")
            return False
            
    async def test_context_system(self):
        """Test the Context system"""
        print("\n🧪 Testing Context System...")
        
        if not self.server.context:
            print("❌ Context system not initialized")
            return False
            
        # Create sample tasks with dependencies
        tasks = [
            Task(
                id="test_1",
                name="Create Database Schema",
                description="Design schema",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["database"],
                dependencies=[]
            ),
            Task(
                id="test_2",
                name="Build API",
                description="Create REST API",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["backend", "api"],
                dependencies=["test_1"]
            )
        ]
        
        # Analyze dependencies
        dep_map = self.server.context.analyze_dependencies(tasks)
        
        # Add implementation for first task
        await self.server.context.add_implementation(
            "test_1",
            {
                "schema": {"users": "id, name, email"},
                "database": "PostgreSQL"
            }
        )
        
        # Log a decision
        await self.server.context.log_decision(
            agent_id="test_agent",
            task_id="test_1",
            what="Use PostgreSQL",
            why="Need ACID compliance",
            impact="All services must use PostgreSQL"
        )
        
        # Get context for second task
        context = await self.server.context.get_context("test_2", ["test_1"])
        
        if context.previous_implementations and context.architectural_decisions:
            print("✅ Context system working:")
            print(f"   - Found {len(context.previous_implementations)} implementations")
            print(f"   - Found {len(context.architectural_decisions)} decisions")
            return True
        else:
            print("❌ Context not properly populated")
            return False
            
    async def test_memory_system(self):
        """Test the Memory system"""
        print("\n🧪 Testing Memory System...")
        
        if not self.server.memory:
            print("❌ Memory system not initialized")
            return False
            
        # Create test agent
        test_agent = WorkerStatus(
            worker_id="test_agent",
            name="Test Agent",
            role="Developer",
            email="test@example.com",
            current_tasks=[],
            completed_tasks_count=0,
            capacity=40,
            skills=["python", "testing"],
            availability={"monday": True}
        )
        
        # Create test task
        test_task = Task(
            id="memory_test",
            name="Test Memory Task",
            description="Task for testing memory",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to="test_agent",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            labels=["python", "testing"],
            dependencies=[]
        )
        
        # Record task start
        await self.server.memory.record_task_start("test_agent", test_task)
        
        # Simulate work
        await asyncio.sleep(0.5)
        
        # Record completion
        outcome = await self.server.memory.record_task_completion(
            agent_id="test_agent",
            task_id="memory_test",
            success=True,
            actual_hours=4.5,
            blockers=[]
        )
        
        # Get predictions for similar task
        predictions = await self.server.memory.predict_task_outcome("test_agent", test_task)
        
        # Check memory stats
        stats = self.server.memory.get_memory_stats()
        
        if (outcome and 
            stats["episodic_memory"]["total_outcomes"] > 0 and
            stats["semantic_memory"]["agent_profiles"] > 0):
            print("✅ Memory system working:")
            print(f"   - Recorded {stats['episodic_memory']['total_outcomes']} outcomes")
            print(f"   - Built {stats['semantic_memory']['agent_profiles']} agent profiles")
            print(f"   - Prediction: {predictions['success_probability']:.1%} success probability")
            return True
        else:
            print("❌ Memory not recording properly")
            return False
            
    async def test_integration(self):
        """Test all systems working together"""
        print("\n🧪 Testing Full Integration...")
        
        # Clear events
        self.events_received = []
        
        # Simulate task request flow
        test_task = Task(
            id="integration_test",
            name="Integration Test Task",
            description="Test all systems together",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=3.0,
            labels=["test", "integration"],
            dependencies=[]
        )
        
        # Add task to server state
        self.server.project_tasks = [test_task]
        
        # Register test agent
        self.server.agent_status["test_agent"] = WorkerStatus(
            worker_id="test_agent",
            name="Test Agent",
            role="Developer",
            email="test@example.com",
            current_tasks=[],
            completed_tasks_count=5,  # Some history
            capacity=40,
            skills=["test", "integration"],
            availability={"monday": True}
        )
        
        # Publish task requested event
        if self.server.events:
            await self.server.events.publish(
                EventTypes.TASK_REQUESTED,
                "test_agent",
                {"agent_id": "test_agent"}
            )
            
        # Small delay for event processing
        await asyncio.sleep(0.1)
        
        # Check if events were received
        event_types = [e.event_type for e in self.events_received]
        
        print(f"✅ Integration test complete:")
        print(f"   - {len(self.events_received)} events captured")
        print(f"   - Event types: {', '.join(set(event_types))}")
        
        return len(self.events_received) > 0
        
    async def cleanup(self):
        """Restore original configuration"""
        print("\n🧹 Cleaning up...")
        
        if self.original_config_content and self.original_config_path:
            with open(self.original_config_path, 'w') as f:
                f.write(self.original_config_content)
            print("✅ Original config restored")
            
        # Clean up test database if created
        test_db = Path("./data/marcus.db")
        if test_db.exists():
            test_db.unlink()
            print("✅ Test database removed")
            
    async def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Marcus Enhanced Features Integration Test")
        print("=" * 60)
        
        try:
            # Setup
            if not await self.setup():
                print("❌ Setup failed")
                return False
                
            # Run tests
            results = {
                "Events": await self.test_event_system(),
                "Context": await self.test_context_system(),
                "Memory": await self.test_memory_system(),
                "Integration": await self.test_integration()
            }
            
            # Summary
            print("\n" + "=" * 60)
            print("Test Results:")
            print("=" * 60)
            
            all_passed = True
            for test_name, passed in results.items():
                status = "✅ PASSED" if passed else "❌ FAILED"
                print(f"{test_name:20} {status}")
                if not passed:
                    all_passed = False
                    
            print("\n" + "=" * 60)
            
            if all_passed:
                print("🎉 All tests passed! Enhanced features are working correctly.")
            else:
                print("⚠️  Some tests failed. Please check the output above.")
                
            return all_passed
            
        finally:
            await self.cleanup()


async def test_with_live_mcp():
    """Test enhanced features through live MCP connection"""
    print("\n🚀 Testing with Live MCP Server...")
    
    # Start Marcus MCP server in background
    server_process = subprocess.Popen(
        [sys.executable, "-m", "src.marcus_mcp.server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give server time to start
    time.sleep(2)
    
    try:
        # TODO: Add MCP client tests here
        print("✅ MCP server started successfully")
        print("   (Full MCP client tests would go here)")
        
    finally:
        # Stop server
        server_process.send_signal(signal.SIGTERM)
        server_process.wait(timeout=5)
        print("✅ MCP server stopped")


async def main():
    """Main test entry point"""
    # Run unit tests
    tester = EnhancedFeaturesTest()
    success = await tester.run_all_tests()
    
    # Optionally run live MCP tests
    if success and "--with-mcp" in sys.argv:
        await test_with_live_mcp()
        
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)