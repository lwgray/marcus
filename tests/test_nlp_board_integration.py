#!/usr/bin/env python3
"""
Integration test showing NLP project creation appears on actual board
This test actually creates tasks on your configured Kanban board
"""

import pytest
import asyncio
import os
from datetime import datetime
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.integrations.kanban_factory import KanbanFactory
from mcp_natural_language_tools import (
    create_project_from_natural_language,
    add_feature_natural_language
)

# Load environment variables
load_dotenv()

class TestNLPBoardIntegration:
    """Test that NLP tools create real tasks on the board"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup kanban client for tests"""
        self.provider = os.getenv('KANBAN_PROVIDER', 'planka')
        self.kanban = await KanbanFactory.create(self.provider)
        self.test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        yield
        # Cleanup would go here if needed
        
    @pytest.mark.asyncio
    async def test_project_appears_on_board(self):
        """Test that a project created via NLP appears on the actual board"""
        # Create unique project name
        project_name = f"Test NLP Project {self.test_timestamp}"
        
        # Create project using NLP
        result = await create_project_from_natural_language(
            description="I need a chat application with real-time messaging and user profiles",
            project_name=project_name,
            options={"team_size": 2}
        )
        
        # Verify creation succeeded
        assert result["success"] == True
        assert result["tasks_created"] > 0
        
        # Wait a moment for board to update
        await asyncio.sleep(1)
        
        # Get tasks from actual board
        all_tasks = await self.kanban.get_tasks()
        
        # Find our tasks
        our_tasks = [
            task for task in all_tasks
            if project_name in (task.title or '') or
               project_name in (task.description or '')
        ]
        
        # Verify tasks exist on board
        assert len(our_tasks) > 0, f"No tasks found on {self.provider} board"
        assert len(our_tasks) == result["tasks_created"], \
            f"Expected {result['tasks_created']} tasks, found {len(our_tasks)}"
            
        # Verify task structure
        for task in our_tasks:
            assert task.title is not None
            assert task.status is not None
            
        print(f"✅ Successfully created {len(our_tasks)} tasks on {self.provider}")
        
    @pytest.mark.asyncio
    async def test_feature_appears_on_board(self):
        """Test that features added via NLP appear on the board"""
        # First create a base project
        project_name = f"Test Feature Project {self.test_timestamp}"
        
        await create_project_from_natural_language(
            description="Basic web app with user authentication",
            project_name=project_name,
            options={"team_size": 1}
        )
        
        # Wait for project creation
        await asyncio.sleep(1)
        
        # Add a feature
        feature_result = await add_feature_natural_language(
            feature_description="Add two-factor authentication with SMS",
            integration_point="auto_detect"
        )
        
        assert feature_result["success"] == True
        assert feature_result["tasks_created"] > 0
        
        # Wait for board update
        await asyncio.sleep(1)
        
        # Get all tasks
        all_tasks = await self.kanban.get_tasks()
        
        # Find 2FA tasks
        twofa_tasks = [
            task for task in all_tasks
            if ('two-factor' in task.title.lower() or 
                '2fa' in task.title.lower() or
                'sms' in task.title.lower())
        ]
        
        assert len(twofa_tasks) > 0, "No 2FA tasks found on board"
        
        print(f"✅ Successfully added {len(twofa_tasks)} 2FA tasks to {self.provider}")
        
    @pytest.mark.asyncio  
    async def test_task_properties_preserved(self):
        """Test that task properties (labels, priority, etc) appear correctly"""
        project_name = f"Test Properties Project {self.test_timestamp}"
        
        # Create project with specific requirements
        result = await create_project_from_natural_language(
            description="""Create an urgent API endpoint for user management 
                          with high priority authentication features""",
            project_name=project_name,
            options={"team_size": 1}
        )
        
        assert result["success"] == True
        
        # Wait and fetch
        await asyncio.sleep(1)
        all_tasks = await self.kanban.get_tasks()
        
        # Find our tasks
        our_tasks = [
            task for task in all_tasks
            if project_name in (task.title or '') or
               project_name in (task.description or '')
        ]
        
        # Check that at least some tasks have properties
        has_labels = any(task.labels for task in our_tasks)
        has_priorities = any(task.priority for task in our_tasks)
        
        assert has_labels, "No tasks have labels"
        assert has_priorities, "No tasks have priorities"
        
        # Find high priority tasks
        high_priority_tasks = [
            task for task in our_tasks
            if task.priority and task.priority.value in ['urgent', 'high']
        ]
        
        assert len(high_priority_tasks) > 0, "No high priority tasks found"
        
        print(f"✅ Task properties preserved on {self.provider}")
        print(f"   - Tasks with labels: {sum(1 for t in our_tasks if t.labels)}")
        print(f"   - High priority tasks: {len(high_priority_tasks)}")

# Run directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])