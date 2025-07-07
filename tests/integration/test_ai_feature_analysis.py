#!/usr/bin/env python3
"""
Test AI-powered feature analysis in add_feature tool

Tests that the AI engine methods are properly integrated.
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime

from src.core.models import Priority, Task, TaskStatus
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.integrations.mcp_natural_language_tools import NaturalLanguageFeatureAdder


class TestAIFeatureAnalysis:
    """Test AI-powered feature analysis"""

    @pytest.mark.asyncio
    async def test_ai_analyze_feature_request(self):
        """Test the analyze_feature_request method"""
        engine = AIAnalysisEngine()

        # Test with fallback (no API key)
        result = await engine.analyze_feature_request(
            "Add user profile page with avatar upload"
        )

        assert "required_tasks" in result
        assert len(result["required_tasks"]) > 0
        assert "feature_complexity" in result

        # Check task structure
        for task in result["required_tasks"]:
            assert "name" in task
            assert "description" in task
            assert "estimated_hours" in task
            assert "labels" in task
            assert "critical" in task
            assert "task_type" in task

    @pytest.mark.asyncio
    async def test_ai_analyze_integration_points(self):
        """Test the analyze_integration_points method"""
        engine = AIAnalysisEngine()

        # Create test tasks
        feature_tasks = [
            Task(
                id="f1",
                name="Add user profile API",
                description="Create API for user profiles",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                labels=["api", "backend"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                estimated_hours=8,
                due_date=None,
                dependencies=[],
            )
        ]

        existing_tasks = [
            Task(
                id="1",
                name="User authentication system",
                description="Build auth system",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                labels=["auth", "backend"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                estimated_hours=12,
                due_date=None,
                dependencies=[],
            )
        ]

        # Test with fallback
        result = await engine.analyze_integration_points(feature_tasks, existing_tasks)

        assert "dependent_task_ids" in result
        assert "suggested_phase" in result
        assert "integration_complexity" in result
        assert "confidence" in result
        assert isinstance(result["confidence"], (int, float))
        assert 0 <= result["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_feature_adder_with_ai(self):
        """Test NaturalLanguageFeatureAdder with AI engine"""
        # Mock dependencies
        mock_kanban = AsyncMock()
        mock_kanban.create_task = AsyncMock(return_value={"id": "new_1"})

        # Create real AI engine
        ai_engine = AIAnalysisEngine()

        existing_tasks = [
            Task(
                id="1",
                name="Setup database",
                description="Configure database",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                labels=["database", "backend"],
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                estimated_hours=4,
                due_date=None,
                dependencies=[],
            )
        ]

        # Create feature adder with real AI
        adder = NaturalLanguageFeatureAdder(
            kanban_client=mock_kanban, ai_engine=ai_engine, project_tasks=existing_tasks
        )

        # Test adding a feature
        result = await adder.add_feature_from_description(
            feature_description="Add REST API for managing user preferences with caching",
            integration_point="auto_detect",
        )

        assert result["success"] == True
        assert result["tasks_created"] > 0

        # Verify AI was used (check created tasks have AI-generated content)
        create_calls = mock_kanban.create_task.call_args_list
        assert len(create_calls) > 0

        # Check task quality
        for call in create_calls:
            task_data = call[0][0]
            assert (
                len(task_data["description"]) > 20
            )  # AI generates detailed descriptions
            assert len(task_data["labels"]) > 0
            assert task_data["estimated_hours"] > 0

    @pytest.mark.asyncio
    async def test_ai_with_mock_claude_response(self):
        """Test with mocked Claude API response"""
        engine = AIAnalysisEngine()

        # Mock the client to enable AI mode
        engine.client = Mock()

        # Mock the _call_claude method
        mock_response = json.dumps(
            {
                "required_tasks": [
                    {
                        "name": "Design user profile data model",
                        "description": "Design database schema for user profiles including avatar storage",
                        "estimated_hours": 4,
                        "labels": ["design", "database", "backend"],
                        "critical": True,
                        "task_type": "design",
                    },
                    {
                        "name": "Implement profile API endpoints",
                        "description": "Create REST API endpoints for CRUD operations on user profiles",
                        "estimated_hours": 12,
                        "labels": ["api", "backend", "rest"],
                        "critical": True,
                        "task_type": "backend",
                    },
                    {
                        "name": "Build profile UI components",
                        "description": "Create React components for profile display and editing",
                        "estimated_hours": 10,
                        "labels": ["frontend", "react", "ui"],
                        "critical": True,
                        "task_type": "frontend",
                    },
                ],
                "feature_complexity": "moderate",
                "technical_requirements": [
                    "image storage",
                    "form validation",
                    "API integration",
                ],
                "dependencies_on_existing": ["authentication", "api"],
            }
        )

        with patch.object(engine, "_call_claude", return_value=mock_response):
            result = await engine.analyze_feature_request("Add user profile page")

            assert len(result["required_tasks"]) == 3
            assert result["feature_complexity"] == "moderate"
            assert "authentication" in result["dependencies_on_existing"]

            # Verify task details
            design_task = result["required_tasks"][0]
            assert design_task["name"] == "Design user profile data model"
            assert design_task["critical"] == True
            assert design_task["task_type"] == "design"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
