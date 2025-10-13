"""
Integration test for About task hierarchical formatting with real subtask decomposition.

This test verifies that the About task correctly displays hierarchical subtask
information AFTER subtask decomposition has occurred.
"""

from datetime import datetime

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_tools import NaturalLanguageProjectCreator


@pytest.mark.integration
@pytest.mark.asyncio
class TestAboutTaskWithRealSubtasks:
    """Integration tests for About task with actual subtask decomposition."""

    @pytest.fixture
    async def project_creator(self, mock_kanban_client, mock_ai_engine):
        """Create a project creator with real subtask manager."""
        from src.marcus_mcp.coordinator.subtask_manager import SubtaskManager

        subtask_manager = SubtaskManager()
        creator = NaturalLanguageProjectCreator(
            kanban_client=mock_kanban_client,
            ai_engine=mock_ai_engine,
            subtask_manager=subtask_manager,
        )
        return creator

    @pytest.fixture
    def mock_kanban_client(self, mocker):
        """Mock kanban client that returns task with real ID."""
        client = mocker.Mock()
        client.project_id = "test_project"
        client.board_id = "test_board"

        # Mock create_task to return task with Planka-like ID
        def create_task_side_effect(task_data):
            created_task = mocker.Mock()
            created_task.id = f"planka_{task_data['name'].replace(' ', '_')}"
            created_task.name = task_data["name"]
            return created_task

        client.create_task.side_effect = create_task_side_effect
        return client

    @pytest.fixture
    def mock_ai_engine(self, mocker):
        """Mock AI engine that returns subtask decomposition."""
        engine = mocker.Mock()

        # Mock decompose_task_to_subtasks to return realistic subtasks
        async def decompose_side_effect(task, instructions):
            if "Design" in task.name:
                # Design tasks get decomposed into smaller design subtasks
                return {
                    "success": True,
                    "subtasks": [
                        {
                            "name": "Create Database Schema Design",
                            "description": "Design database tables and relationships",
                            "estimated_hours": 2.0,
                        },
                        {
                            "name": "Design API Endpoints",
                            "description": "Define REST API endpoint structure",
                            "estimated_hours": 2.0,
                        },
                    ],
                    "shared_conventions": {"design_pattern": "REST"},
                }
            elif "Implement" in task.name:
                # Implementation tasks get decomposed
                return {
                    "success": True,
                    "subtasks": [
                        {
                            "name": "Set up FastAPI project",
                            "description": "Initialize FastAPI application",
                            "estimated_hours": 3.0,
                        },
                        {
                            "name": "Implement GET /time endpoint",
                            "description": "Create endpoint returning current time",
                            "estimated_hours": 3.0,
                        },
                        {
                            "name": "Add input validation",
                            "description": "Validate request parameters",
                            "estimated_hours": 2.0,
                        },
                    ],
                    "shared_conventions": {"framework": "FastAPI"},
                }
            else:
                # Small tasks don't get decomposed
                return {"success": False, "error": "Task too small"}

        engine.decompose_task_to_subtasks.side_effect = decompose_side_effect
        return engine

    async def test_about_task_contains_hierarchical_subtasks(
        self, project_creator, mocker
    ):
        """Test that About task shows hierarchical structure after decomposition."""
        description = "Create a simple REST API with GET /time endpoint"
        project_name = "Simple Time API"

        # Create tasks that will be decomposed
        tasks = [
            Task(
                id="task_1",
                name="Design Time API",
                description="Design the API structure",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,  # >= 4 hours, will be decomposed
                dependencies=[],
                labels=["design", "backend"],
            ),
            Task(
                id="task_2",
                name="Implement Time API",
                description="Build the API endpoints",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,  # >= 4 hours, will be decomposed
                dependencies=["task_1"],
                labels=["implementation", "backend"],
            ),
            Task(
                id="task_3",
                name="Write Documentation",
                description="Document the API",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,  # < 4 hours, won't be decomposed
                dependencies=["task_2"],
                labels=["documentation"],
            ),
        ]

        # Patch decompose_task and should_decompose
        with mocker.patch(
            "src.marcus_mcp.coordinator.should_decompose",
            side_effect=lambda t: t.estimated_hours >= 4.0,
        ):
            with mocker.patch(
                "src.marcus_mcp.coordinator.decompose_task",
                side_effect=lambda task, engine, project_context: (
                    project_creator.ai_engine.decompose_task_to_subtasks(
                        task, "Decompose this task"
                    )
                ),
            ):
                # Patch _add_subtasks_as_checklist to avoid real Planka calls
                async def mock_add_checklist(parent_id, subtasks):
                    pass

                mocker.patch.object(
                    project_creator,
                    "_add_subtasks_as_checklist",
                    side_effect=mock_add_checklist,
                )

                # Create About task BEFORE decomposition (current behavior)
                about_task_before = project_creator._create_about_task(
                    description, project_name, tasks
                )

                # Verify About task does NOT have subtask hierarchy yet
                assert "**Subtasks:**" not in about_task_before.description
                assert "1.1." not in about_task_before.description
                assert "2.1." not in about_task_before.description

                # Now create tasks on board (which triggers decomposition)
                created_tasks = await project_creator.create_tasks_on_board(tasks)

                # Verify decomposition happened
                assert project_creator.subtask_manager.has_subtasks("planka_task_1")
                assert project_creator.subtask_manager.has_subtasks("planka_task_2")
                assert not project_creator.subtask_manager.has_subtasks("planka_task_3")

                # Get subtasks from manager
                task_1_subtasks = project_creator.subtask_manager.get_subtasks(
                    "planka_task_1"
                )
                task_2_subtasks = project_creator.subtask_manager.get_subtasks(
                    "planka_task_2"
                )

                assert len(task_1_subtasks) == 2
                assert len(task_2_subtasks) == 3

                # NOW create About task AFTER decomposition (desired behavior)
                # Need to update task IDs to match created tasks
                updated_tasks = []
                for i, created in enumerate(created_tasks):
                    original = tasks[i]
                    updated_task = Task(
                        id=created.id,  # Use real Planka ID
                        name=original.name,
                        description=original.description,
                        status=original.status,
                        priority=original.priority,
                        assigned_to=original.assigned_to,
                        created_at=original.created_at,
                        updated_at=original.updated_at,
                        due_date=original.due_date,
                        estimated_hours=original.estimated_hours,
                        dependencies=original.dependencies,
                        labels=original.labels,
                    )
                    updated_tasks.append(updated_task)

                about_task_after = project_creator._create_about_task(
                    description, project_name, updated_tasks
                )

                # ASSERT: About task NOW contains hierarchical subtask information
                assert "**Subtasks:**" in about_task_after.description

                # Verify task 1 subtasks are shown hierarchically
                assert "### 1. Design Time API" in about_task_after.description
                assert (
                    "  1.1. Create Database Schema Design"
                    in about_task_after.description
                )
                assert (
                    "     - Design database tables and relationships"
                    in about_task_after.description
                )
                assert "     - Estimated: 2.0h" in about_task_after.description
                assert "  1.2. Design API Endpoints" in about_task_after.description

                # Verify task 2 subtasks are shown hierarchically
                assert "### 2. Implement Time API" in about_task_after.description
                assert "  2.1. Set up FastAPI project" in about_task_after.description
                assert (
                    "  2.2. Implement GET /time endpoint"
                    in about_task_after.description
                )
                assert "  2.3. Add input validation" in about_task_after.description

                # Verify task 3 (no subtasks) is still shown flat
                assert "### 3. Write Documentation" in about_task_after.description
                assert (
                    "**Description:** Document the API" in about_task_after.description
                )
                # Task 3 should NOT have subtasks marker
                count_subtask_markers = about_task_after.description.count(
                    "**Subtasks:**"
                )
                assert count_subtask_markers == 2  # Only for task 1 and task 2

    async def test_about_task_updates_when_subtasks_added_later(
        self, project_creator, mocker
    ):
        """Test that About task can be regenerated after subtasks are added."""
        description = "Simple API"
        project_name = "Test API"

        tasks = [
            Task(
                id="task_1",
                name="Large Task",
                description="A large task",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=10.0,
                dependencies=[],
                labels=["backend"],
            )
        ]

        # Initially, no subtasks
        about_v1 = project_creator._create_about_task(description, project_name, tasks)
        assert "**Subtasks:**" not in about_v1.description

        # Manually add subtasks to subtask manager
        from src.marcus_mcp.coordinator.subtask_manager import (
            Subtask,
            SubtaskMetadata,
        )

        subtasks = [
            Subtask(
                id="sub_1",
                parent_task_id="task_1",
                name="Subtask 1",
                description="First subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                estimated_hours=5.0,
                order=0,
            ),
            Subtask(
                id="sub_2",
                parent_task_id="task_1",
                name="Subtask 2",
                description="Second subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                estimated_hours=5.0,
                order=1,
            ),
        ]

        metadata = SubtaskMetadata(shared_conventions={}, decomposed_by="test")
        project_creator.subtask_manager.add_subtasks("task_1", subtasks, metadata)

        # Now regenerate About task - it should include subtasks
        about_v2 = project_creator._create_about_task(description, project_name, tasks)
        assert "**Subtasks:**" in about_v2.description
        assert "  1.1. Subtask 1" in about_v2.description
        assert "  1.2. Subtask 2" in about_v2.description
        assert "     - First subtask" in about_v2.description
        assert "     - Estimated: 5.0h" in about_v2.description
