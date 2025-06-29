#!/usr/bin/env python3
"""
Test scenarios for the add_feature_natural_language tool

Tests various scenarios including:
- AI available vs fallback
- Different feature types
- Integration point detection
- Error handling
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_natural_language_tools import (
    add_feature_natural_language,
    NaturalLanguageFeatureAdder
)
from src.core.models import Task, TaskStatus, Priority


class TestAddFeatureScenarios:
    """Test various scenarios for add_feature_natural_language"""
    
    @pytest.fixture
    def mock_state(self):
        """Create mock state for testing"""
        mock = MagicMock()
        
        # Mock kanban client with create_task method
        mock.kanban_client = AsyncMock()
        mock.kanban_client.create_task = AsyncMock(return_value={"id": "new_task_1"})
        
        # Mock AI engine (set to None to test fallback)
        mock.ai_engine = None
        
        # Mock existing project tasks
        mock.project_tasks = [
            Task(
                id="1",
                name="Setup project structure",
                description="Initial project setup and configuration",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                labels=["setup", "backend"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                estimated_hours=4,
                due_date=None,
                dependencies=[]
            ),
            Task(
                id="2",
                name="Implement user authentication",
                description="Build user auth system with login and registration",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                labels=["auth", "backend", "security"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                estimated_hours=8,
                due_date=None,
                dependencies=["1"]
            ),
            Task(
                id="3",
                name="Create API endpoints",
                description="Implement REST API endpoints for core functionality",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.MEDIUM,
                labels=["api", "backend"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                estimated_hours=12,
                due_date=None,
                dependencies=["2"]
            )
        ]
        
        # Mock refresh method
        mock.refresh_project_state = AsyncMock()
        
        return mock
    
    @pytest.mark.asyncio
    async def test_add_feature_with_empty_description(self, mock_state):
        """Test that empty feature description is rejected"""
        with patch('mcp_natural_language_tools.marcus_mcp_server.state', mock_state):
            result = await add_feature_natural_language(
                feature_description="",
                integration_point="auto_detect"
            )
        
        assert result["success"] == False
        assert "required" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_add_feature_without_existing_project(self, mock_state):
        """Test that features cannot be added without existing project"""
        mock_state.project_tasks = []
        
        with patch('mcp_natural_language_tools.marcus_mcp_server.state', mock_state):
            result = await add_feature_natural_language(
                feature_description="Add user profile feature",
                integration_point="auto_detect"
            )
        
        assert result["success"] == False
        assert "no existing project" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_add_feature_fallback_api_type(self, mock_state):
        """Test fallback task generation for API feature"""
        with patch('mcp_natural_language_tools.marcus_mcp_server.state', mock_state):
            result = await add_feature_natural_language(
                feature_description="Add REST API for user profiles",
                integration_point="auto_detect"
            )
        
        assert result["success"] == True
        assert result["tasks_created"] > 0
        
        # Verify API-related tasks were created
        create_task_calls = mock_state.kanban_client.create_task.call_args_list
        task_names = [call[0][0]["name"] for call in create_task_calls]
        
        # Should have design, backend, test, and doc tasks
        assert any("Design" in name for name in task_names)
        assert any("backend" in name for name in task_names)
        assert any("Test" in name for name in task_names)
        assert any("Document" in name for name in task_names)
    
    @pytest.mark.asyncio
    async def test_add_feature_fallback_ui_type(self, mock_state):
        """Test fallback task generation for UI feature"""
        with patch('mcp_natural_language_tools.marcus_mcp_server.state', mock_state):
            result = await add_feature_natural_language(
                feature_description="Create user dashboard UI",
                integration_point="auto_detect"
            )
        
        assert result["success"] == True
        
        # Verify UI-related tasks were created
        create_task_calls = mock_state.kanban_client.create_task.call_args_list
        task_names = [call[0][0]["name"] for call in create_task_calls]
        
        assert any("UI components" in name for name in task_names)
    
    @pytest.mark.asyncio
    async def test_add_feature_integration_detection(self, mock_state):
        """Test integration point detection with existing tasks"""
        with patch('mcp_natural_language_tools.marcus_mcp_server.state', mock_state):
            result = await add_feature_natural_language(
                feature_description="Add user permissions system",
                integration_point="auto_detect"
            )
        
        assert result["success"] == True
        assert result["integration_detected"] == True
        
        # Should detect integration with auth task (task id "2")
        assert "2" in result["integration_points"]
    
    @pytest.mark.asyncio
    async def test_add_feature_with_ai_engine(self, mock_state):
        """Test feature addition when AI engine is available"""
        # Mock AI engine
        mock_state.ai_engine = AsyncMock()
        mock_state.ai_engine.analyze_feature_request = AsyncMock(return_value={
            "required_tasks": [
                {
                    "name": "AI Generated Task 1",
                    "description": "AI generated description",
                    "estimated_hours": 10,
                    "labels": ["ai", "feature"],
                    "critical": True
                }
            ]
        })
        mock_state.ai_engine.analyze_integration_points = AsyncMock(return_value={
            "suggested_phase": "development",
            "confidence": 0.95
        })
        
        with patch('mcp_natural_language_tools.marcus_mcp_server.state', mock_state):
            result = await add_feature_natural_language(
                feature_description="Add advanced search functionality",
                integration_point="auto_detect"
            )
        
        assert result["success"] == True
        assert result["confidence"] == 0.95
        assert result["feature_phase"] == "development"
        
        # Verify AI methods were called
        mock_state.ai_engine.analyze_feature_request.assert_called_once()
        mock_state.ai_engine.analyze_integration_points.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_feature_without_create_task_method(self, mock_state):
        """Test error when kanban client doesn't support create_task"""
        # Remove create_task method
        delattr(mock_state.kanban_client, 'create_task')
        
        with patch('mcp_natural_language_tools.marcus_mcp_server.state', mock_state):
            result = await add_feature_natural_language(
                feature_description="Add notification system",
                integration_point="auto_detect"
            )
        
        assert result["success"] == False
        assert "does not support task creation" in result["error"]
    
    @pytest.mark.asyncio
    async def test_add_feature_phase_detection(self, mock_state):
        """Test project phase detection in fallback mode"""
        # Set all tasks to completed
        for task in mock_state.project_tasks:
            task.status = TaskStatus.DONE
        
        with patch('mcp_natural_language_tools.marcus_mcp_server.state', mock_state):
            result = await add_feature_natural_language(
                feature_description="Add reporting feature",
                integration_point="auto_detect"
            )
        
        assert result["success"] == True
        # With all tasks done, should detect later phase
        assert result["feature_phase"] != "initial"
    
    @pytest.mark.asyncio
    async def test_add_feature_enrichment(self, mock_state):
        """Test that tasks are enriched with BasicEnricher"""
        with patch('mcp_natural_language_tools.marcus_mcp_server.state', mock_state):
            result = await add_feature_natural_language(
                feature_description="Add urgent bug fix for login",
                integration_point="auto_detect"
            )
        
        assert result["success"] == True
        
        # Check that priority was adjusted based on "urgent" keyword
        create_task_calls = mock_state.kanban_client.create_task.call_args_list
        priorities = [call[0][0]["priority"] for call in create_task_calls]
        
        # At least some tasks should have high/urgent priority
        assert any(p in ["high", "urgent"] for p in priorities)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])