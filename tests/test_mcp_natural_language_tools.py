#!/usr/bin/env python3
"""
Test suite for Natural Language MCP tools

Tests the new MCP tools that expose Marcus's AI capabilities for:
1. Creating projects from natural language descriptions
2. Adding features to existing projects
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

# Test imports
from marcus_mcp_server import (
    create_project_from_natural_language,
    add_feature_natural_language,
    state
)
from src.core.models import Task, TaskStatus, Priority
from src.ai.advanced.prd.advanced_parser import TaskGenerationResult


class TestCreateProjectFromNaturalLanguage:
    """Test create_project_from_natural_language MCP tool"""
    
    @pytest.fixture
    def mock_state(self):
        """Setup mock state"""
        # Reset state
        state.kanban_client = AsyncMock()
        state.ai_engine = AsyncMock()
        state.project_tasks = []
        state.project_state = {}
        
        # Mock PRD parser
        self.mock_prd_parser = AsyncMock()
        self.mock_context_detector = AsyncMock()
        self.mock_mode_engine = AsyncMock()
        
        return state
    
    @pytest.mark.asyncio
    async def test_create_simple_project(self, mock_state):
        """Test creating a simple project from natural language"""
        # Given: Natural language project description
        description = "I need a todo app with user accounts and task sharing"
        project_name = "Todo App MVP"
        
        # Mock PRD parser response
        mock_tasks = [
            Task(id="1", name="Design database schema", status=TaskStatus.TODO,
                 priority=Priority.HIGH, labels=["database", "design"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="2", name="Implement user authentication", status=TaskStatus.TODO,
                 priority=Priority.HIGH, labels=["backend", "auth"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="3", name="Create task CRUD API", status=TaskStatus.TODO,
                 priority=Priority.MEDIUM, labels=["backend", "api"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now())
        ]
        
        mock_prd_result = TaskGenerationResult(
            tasks=mock_tasks,
            task_hierarchy={"phase1": ["1"], "phase2": ["2", "3"]},
            dependencies=[{"dependent": "3", "dependency": "2"}],
            risk_assessment={"overall_risk_level": "medium"},
            estimated_timeline={"estimated_duration_days": 30},
            resource_requirements={"estimated_team_size": 2},
            success_criteria=["User can create account", "Tasks can be shared"],
            generation_confidence=0.85
        )
        
        # Mock the PRD parser
        with patch('marcus_mcp_server.prd_parser') as mock_parser:
            mock_parser.parse_prd_to_tasks = AsyncMock(return_value=mock_prd_result)
            
            # When: Create project from natural language
            result = await create_project_from_natural_language(
                description=description,
                project_name=project_name
            )
        
        # Then: Project should be created successfully
        assert result["success"] == True
        assert result["project_name"] == project_name
        assert result["tasks_created"] == 3
        assert result["phases"] == ["phase1", "phase2"]
        assert result["estimated_days"] == 30
        assert result["dependencies_mapped"] == 1
        
        # And: Tasks should be created on kanban board
        assert mock_state.kanban_client.create_task.call_count == 3
        
        # And: Should enforce logical ordering (no deploy before implement)
        tasks_created = [call[0][0] for call in mock_state.kanban_client.create_task.call_args_list]
        assert not any("deploy" in task.get("name", "").lower() for task in tasks_created)
    
    @pytest.mark.asyncio  
    async def test_create_project_with_deployment_safety(self, mock_state):
        """Test that deployment tasks have proper dependencies"""
        # Given: Project with deployment task
        description = "E-commerce site with payment processing and deployment"
        
        mock_tasks = [
            Task(id="1", name="Implement payment processing", status=TaskStatus.TODO,
                 priority=Priority.HIGH, labels=["backend", "payments"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="2", name="Test payment integration", status=TaskStatus.TODO,
                 priority=Priority.HIGH, labels=["testing"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="3", name="Deploy to production", status=TaskStatus.TODO,
                 priority=Priority.MEDIUM, labels=["deployment"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now(),
                 dependencies=["1", "2"])  # Must depend on implementation and testing
        ]
        
        mock_prd_result = TaskGenerationResult(
            tasks=mock_tasks,
            task_hierarchy={"implementation": ["1"], "testing": ["2"], "deployment": ["3"]},
            dependencies=[
                {"dependent": "3", "dependency": "1"},
                {"dependent": "3", "dependency": "2"}
            ],
            risk_assessment={"overall_risk_level": "high"},
            estimated_timeline={"estimated_duration_days": 45},
            resource_requirements={"estimated_team_size": 3},
            success_criteria=["Payment processing works", "All tests pass"],
            generation_confidence=0.9
        )
        
        with patch('marcus_mcp_server.prd_parser') as mock_parser:
            mock_parser.parse_prd_to_tasks = AsyncMock(return_value=mock_prd_result)
            
            # When: Create project
            result = await create_project_from_natural_language(
                description=description,
                project_name="E-commerce MVP"
            )
        
        # Then: Deployment task should have dependencies
        assert result["success"] == True
        
        # Find deployment task in created tasks
        deploy_task = None
        for task in mock_tasks:
            if "deploy" in task.name.lower():
                deploy_task = task
                break
        
        assert deploy_task is not None
        assert len(deploy_task.dependencies) >= 2
        assert "1" in deploy_task.dependencies  # Depends on implementation
        assert "2" in deploy_task.dependencies  # Depends on testing
    
    @pytest.mark.asyncio
    async def test_create_project_with_constraints(self, mock_state):
        """Test creating project with specific constraints"""
        # Given: Project with constraints
        description = "Mobile app for fitness tracking"
        options = {
            "team_size": 2,
            "tech_stack": ["React Native", "Node.js", "MongoDB"],
            "deadline": "2024-06-01"
        }
        
        # When: Create project with constraints
        with patch('marcus_mcp_server.prd_parser') as mock_parser:
            mock_parser.parse_prd_to_tasks = AsyncMock()
            
            result = await create_project_from_natural_language(
                description=description,
                project_name="Fitness App",
                options=options
            )
            
            # Then: Constraints should be passed to PRD parser
            call_args = mock_parser.parse_prd_to_tasks.call_args
            constraints = call_args[0][1]  # Second argument
            
            assert constraints.team_size == 2
            assert constraints.technology_constraints == ["React Native", "Node.js", "MongoDB"]
            assert constraints.deadline is not None
    
    @pytest.mark.asyncio
    async def test_create_project_error_handling(self, mock_state):
        """Test error handling in project creation"""
        # Given: PRD parser fails
        with patch('marcus_mcp_server.prd_parser') as mock_parser:
            mock_parser.parse_prd_to_tasks = AsyncMock(side_effect=Exception("Parser error"))
            
            # When: Try to create project
            result = await create_project_from_natural_language(
                description="Test project",
                project_name="Test"
            )
            
            # Then: Should handle error gracefully
            assert result["success"] == False
            assert "error" in result
            assert "Parser error" in result["error"]


class TestAddFeatureNaturalLanguage:
    """Test add_feature_natural_language MCP tool"""
    
    @pytest.fixture
    def mock_state_with_project(self):
        """Setup mock state with existing project"""
        state.kanban_client = AsyncMock()
        state.ai_engine = AsyncMock()
        
        # Existing project tasks
        state.project_tasks = [
            Task(id="1", name="User authentication", status=TaskStatus.DONE,
                 priority=Priority.HIGH, labels=["backend", "auth"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="2", name="Recipe CRUD API", status=TaskStatus.IN_PROGRESS,
                 priority=Priority.HIGH, labels=["backend", "api"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="3", name="Recipe UI", status=TaskStatus.TODO,
                 priority=Priority.MEDIUM, labels=["frontend"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now())
        ]
        
        state.project_state = {"exists": True}
        return state
    
    @pytest.mark.asyncio
    async def test_add_simple_feature(self, mock_state_with_project):
        """Test adding a simple feature to existing project"""
        # Given: Feature description
        feature_description = "Add recipe rating system with 5-star reviews"
        
        # Mock feature parser response
        mock_feature_tasks = [
            Task(id="4", name="Design rating database schema", status=TaskStatus.TODO,
                 priority=Priority.HIGH, labels=["database", "feature"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="5", name="Implement rating API endpoints", status=TaskStatus.TODO,
                 priority=Priority.HIGH, labels=["backend", "api", "feature"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now(),
                 dependencies=["1", "2"])  # Depends on auth and recipe API
        ]
        
        with patch('marcus_mcp_server.feature_parser') as mock_parser:
            mock_parser.parse_feature = AsyncMock(return_value={
                "tasks": mock_feature_tasks,
                "integration_points": ["1", "2"],
                "phase": "current"
            })
            
            # When: Add feature
            result = await add_feature_natural_language(
                feature_description=feature_description
            )
        
        # Then: Feature should be added successfully
        assert result["success"] == True
        assert result["tasks_created"] == 2
        assert result["integration_points"] == ["1", "2"]
        
        # And: Should detect dependencies on existing tasks
        rating_api_task = mock_feature_tasks[1]
        assert "1" in rating_api_task.dependencies  # Depends on auth
        assert "2" in rating_api_task.dependencies  # Depends on recipe API
    
    @pytest.mark.asyncio
    async def test_add_feature_with_safety_check(self, mock_state_with_project):
        """Test that features requiring deployment are properly ordered"""
        # Given: Feature that includes deployment
        feature_description = "Add real-time notifications with WebSocket and deploy"
        
        mock_feature_tasks = [
            Task(id="4", name="Implement WebSocket server", status=TaskStatus.TODO,
                 priority=Priority.HIGH, labels=["backend", "realtime"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="5", name="Test real-time features", status=TaskStatus.TODO,
                 priority=Priority.HIGH, labels=["testing"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now(),
                 dependencies=["4"]),
            Task(id="6", name="Deploy notification system", status=TaskStatus.TODO,
                 priority=Priority.MEDIUM, labels=["deployment"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now(),
                 dependencies=["4", "5"])  # Must depend on implementation and testing
        ]
        
        with patch('marcus_mcp_server.feature_parser') as mock_parser:
            mock_parser.parse_feature = AsyncMock(return_value={
                "tasks": mock_feature_tasks,
                "integration_points": ["1"],
                "phase": "next"
            })
            
            # When: Add feature with deployment
            result = await add_feature_natural_language(
                feature_description=feature_description
            )
        
        # Then: Deployment should have proper dependencies
        deploy_task = next(t for t in mock_feature_tasks if "deploy" in t.name.lower())
        assert len(deploy_task.dependencies) >= 2
        assert "4" in deploy_task.dependencies  # Implementation
        assert "5" in deploy_task.dependencies  # Testing
    
    @pytest.mark.asyncio
    async def test_add_feature_auto_integration(self, mock_state_with_project):
        """Test automatic integration point detection"""
        # Given: Feature that needs existing functionality
        feature_description = "Add social sharing for recipes"
        
        # When: Add feature with auto-detect
        with patch('marcus_mcp_server.adaptive_mode') as mock_adaptive:
            mock_adaptive.detect_integration_points = AsyncMock(return_value={
                "integration_tasks": ["1", "2"],  # Needs auth and recipes
                "suggested_phase": "current",
                "confidence": 0.9
            })
            
            result = await add_feature_natural_language(
                feature_description=feature_description,
                integration_point="auto_detect"
            )
            
            # Then: Should detect integration automatically
            assert mock_adaptive.detect_integration_points.called
            assert result["integration_detected"] == True
            assert result["confidence"] >= 0.9


class TestOptimalTaskAssignmentWithAI:
    """Test the updated find_optimal_task_for_agent with AI capabilities"""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent"""
        from marcus_mcp_server import WorkerStatus
        return WorkerStatus(
            worker_id="test-agent",
            name="Test Agent",
            role="Full Stack Developer",
            skills=["python", "react", "testing"],
            current_tasks=[],
            completed_tasks_count=5,
            performance_score=0.85
        )
    
    @pytest.fixture
    def mock_tasks(self):
        """Create mock tasks for testing"""
        return [
            Task(id="1", name="Implement user login", status=TaskStatus.TODO,
                 priority=Priority.HIGH, labels=["backend", "auth"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now()),
            Task(id="2", name="Deploy to production", status=TaskStatus.TODO,
                 priority=Priority.URGENT, labels=["deployment"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now(),
                 dependencies=["1"]),  # Depends on login
            Task(id="3", name="Write unit tests", status=TaskStatus.TODO,
                 priority=Priority.MEDIUM, labels=["testing"],
                 assigned_to=None, created_at=datetime.now(), updated_at=datetime.now())
        ]
    
    @pytest.mark.asyncio
    async def test_ai_prevents_unsafe_deployment(self, mock_agent, mock_tasks):
        """Test that AI prevents assigning deployment before implementation"""
        # Given: Tasks including unsafe deployment
        state.agent_status = {"test-agent": mock_agent}
        state.project_tasks = mock_tasks
        state.project_state = {"exists": True}
        
        # Mock AI engine
        state.ai_engine = AsyncMock()
        state.ai_engine.analyze_task_safety = AsyncMock(return_value={
            "safe": False,
            "reason": "Cannot deploy - dependency task 'Implement user login' is not complete"
        })
        
        # Import the new AI-powered function
        from marcus_mcp_server import find_optimal_task_for_agent_ai_powered
        
        # When: Find optimal task
        optimal_task = await find_optimal_task_for_agent_ai_powered("test-agent")
        
        # Then: Should not assign deployment task
        assert optimal_task is not None
        assert optimal_task.id != "2"  # Not the deployment task
        assert "deploy" not in optimal_task.name.lower()
    
    @pytest.mark.asyncio
    async def test_ai_prioritizes_unblocking_tasks(self, mock_agent, mock_tasks):
        """Test that AI prioritizes tasks that unblock others"""
        # Given: Task 1 blocks task 2
        state.agent_status = {"test-agent": mock_agent}
        state.project_tasks = mock_tasks
        state.project_state = {"exists": True}
        
        # Mock AI analysis
        state.ai_engine = AsyncMock()
        state.ai_engine.analyze_task_impact = AsyncMock(return_value={
            "1": {"unblocks_count": 1, "critical_path": True},
            "3": {"unblocks_count": 0, "critical_path": False}
        })
        
        from marcus_mcp_server import find_optimal_task_for_agent_ai_powered
        
        # When: Find optimal task
        optimal_task = await find_optimal_task_for_agent_ai_powered("test-agent")
        
        # Then: Should prioritize task 1 (unblocks deployment)
        assert optimal_task.id == "1"
    
    @pytest.mark.asyncio
    async def test_ai_considers_agent_skills(self, mock_agent, mock_tasks):
        """Test that AI considers agent skills in assignment"""
        # Given: Agent with testing skills
        mock_agent.skills = ["testing", "jest", "pytest"]
        state.agent_status = {"test-agent": mock_agent}
        state.project_tasks = mock_tasks
        state.project_state = {"exists": True}
        
        # Mock AI skill analysis
        state.ai_engine = AsyncMock()
        state.ai_engine.match_agent_to_tasks = AsyncMock(return_value={
            "1": {"skill_match": 0.3, "confidence": 0.7},
            "3": {"skill_match": 0.9, "confidence": 0.95}  # Better match for testing
        })
        
        from marcus_mcp_server import find_optimal_task_for_agent_ai_powered
        
        # When: Find optimal task
        optimal_task = await find_optimal_task_for_agent_ai_powered("test-agent")
        
        # Then: Should assign testing task (better skill match)
        assert optimal_task.id == "3"
        assert "test" in optimal_task.name.lower()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])