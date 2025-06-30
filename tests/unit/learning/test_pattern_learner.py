"""
Unit tests for the PatternLearner module.

This module tests the pattern learning functionality that analyzes completed
projects to extract patterns for future recommendations. Tests cover pattern
extraction, updating, confidence calculation, and persistence.

Notes
-----
All external dependencies are mocked, including file I/O and ML operations.
Tests verify the learning algorithms without requiring actual project data.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from src.learning.pattern_learner import (
    PatternLearner, CompletedProject, ProjectLearnings,
    Pattern, Task, TaskStatus, Priority
)


class TestPatternLearner:
    """
    Test suite for the PatternLearner class.
    
    Tests pattern learning, extraction, updating, and recommendation
    functionality for improving future project execution.
    """
    
    @pytest.fixture
    def pattern_learner(self) -> PatternLearner:
        """Create a PatternLearner instance for testing."""
        return PatternLearner()
    
    @pytest.fixture
    def sample_task(self) -> Task:
        """Create a sample task for testing."""
        task = Task(
            id="TASK-001",
            name="Setup project structure",
            description="Initialize project with basic structure",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            assigned_to="agent1",
            created_at=datetime.now() - timedelta(days=5),
            updated_at=datetime.now() - timedelta(days=1),
            due_date=datetime.now() + timedelta(days=2),
            estimated_hours=4.0,
            actual_hours=5.0,
            dependencies=[],
            labels=["setup", "infrastructure"]
        )
        # Add completed_at as an attribute for testing
        task.completed_at = datetime.now() - timedelta(days=1)
        return task
    
    @pytest.fixture
    def sample_project(self, sample_task) -> CompletedProject:
        """Create a sample completed project for testing."""
        task2 = Task(
            id="TASK-002",
            name="Design API endpoints",
            description="Design REST API",
            status=TaskStatus.DONE,
            priority=Priority.MEDIUM,
            assigned_to="agent2",
            created_at=datetime.now() - timedelta(days=4),
            updated_at=datetime.now() - timedelta(hours=12),
            due_date=datetime.now() + timedelta(days=1),
            estimated_hours=6.0,
            actual_hours=8.0,
            dependencies=["TASK-001"],
            labels=["design", "api"]
        )
        task2.completed_at = datetime.now() - timedelta(hours=12)
        
        task3 = Task(
            id="TASK-003",
            name="Implement backend API",
            description="Build backend services",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            assigned_to="agent1",
            created_at=datetime.now() - timedelta(days=3),
            updated_at=datetime.now() - timedelta(hours=6),
            due_date=datetime.now(),
            estimated_hours=12.0,
            actual_hours=10.0,
            dependencies=["TASK-002"],
            labels=["backend", "implementation"]
        )
        task3.completed_at = datetime.now() - timedelta(hours=6)
        
        tasks = [sample_task, task2, task3]
        
        return CompletedProject(
            project_id="PROJ-001",
            name="Test Project",
            tasks=tasks,
            completion_date=datetime.now(),
            success_metrics={
                "planned_duration": 5,
                "quality_score": 0.9,
                "test_coverage": 0.85
            },
            team_size=2,
            duration_days=5,
            project_type="web_application"
        )
    
    def test_pattern_learner_initialization(self, pattern_learner):
        """Test PatternLearner initialization with default values."""
        assert pattern_learner.patterns == {}
        assert pattern_learner.project_history == []
        assert len(pattern_learner.task_type_patterns) == 8
        assert 'setup' in pattern_learner.task_type_patterns
        assert 'backend' in pattern_learner.task_type_patterns
    
    @pytest.mark.asyncio
    async def test_learn_from_project(self, pattern_learner, sample_project):
        """Test learning patterns from a completed project."""
        # Mock the internal methods
        pattern_learner._analyze_estimation_accuracy = AsyncMock(
            return_value={"setup": 0.8, "design": 0.75, "backend": 0.83}
        )
        pattern_learner._analyze_dependency_patterns = AsyncMock(
            return_value=[{
                "pattern": "setup_before_design",
                "description": "Setup tasks typically complete before design tasks",
                "confidence": 0.7
            }]
        )
        pattern_learner._analyze_workflow_patterns = AsyncMock(
            return_value={"max_parallelism": 2, "avg_daily_completions": 0.6}
        )
        pattern_learner._identify_success_factors = AsyncMock(
            return_value=["completed_on_time", "accurate_estimation"]
        )
        pattern_learner._identify_failure_points = AsyncMock(
            return_value=[]
        )
        pattern_learner._analyze_team_performance = AsyncMock(
            return_value={"velocity": 0.6, "team_size": 2}
        )
        pattern_learner.update_patterns = AsyncMock()
        
        await pattern_learner.learn_from_project(sample_project)
        
        # Verify project was added to history
        assert len(pattern_learner.project_history) == 1
        assert pattern_learner.project_history[0] == sample_project
        
        # Verify all analysis methods were called
        pattern_learner._analyze_estimation_accuracy.assert_called_once_with(sample_project)
        pattern_learner._analyze_dependency_patterns.assert_called_once_with(sample_project)
        pattern_learner._analyze_workflow_patterns.assert_called_once_with(sample_project)
        pattern_learner._identify_success_factors.assert_called_once_with(sample_project)
        pattern_learner._identify_failure_points.assert_called_once_with(sample_project)
        pattern_learner._analyze_team_performance.assert_called_once_with(sample_project)
        pattern_learner.update_patterns.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_estimation_accuracy(self, pattern_learner, sample_project):
        """Test estimation accuracy analysis."""
        # Add actual_hours attribute to tasks
        for task in sample_project.tasks:
            if task.id == "TASK-001":
                task.actual_hours = 5.0  # 4 estimated, 5 actual
            elif task.id == "TASK-002":
                task.actual_hours = 8.0  # 6 estimated, 8 actual
            elif task.id == "TASK-003":
                task.actual_hours = 10.0  # 12 estimated, 10 actual
        
        accuracy = await pattern_learner._analyze_estimation_accuracy(sample_project)
        
        assert "setup" in accuracy
        assert "design" in accuracy
        assert "backend" in accuracy
        
        # Check accuracy calculations
        assert 0.7 < accuracy["setup"] < 0.9  # 4/5 = 0.8
        assert 0.7 < accuracy["design"] < 0.8  # 6/8 = 0.75
        assert 0.8 < accuracy["backend"] < 0.9  # 10/12 = 0.833
    
    @pytest.mark.asyncio
    async def test_analyze_dependency_patterns(self, pattern_learner, sample_project):
        """Test dependency pattern analysis."""
        patterns = await pattern_learner._analyze_dependency_patterns(sample_project)
        
        assert len(patterns) >= 2  # At least 2 sequential patterns
        
        # Check pattern structure
        for pattern in patterns:
            assert "pattern" in pattern
            assert "description" in pattern
            assert "confidence" in pattern
            assert "evidence" in pattern
    
    @pytest.mark.asyncio
    async def test_analyze_workflow_patterns(self, pattern_learner, sample_project):
        """Test workflow pattern analysis."""
        patterns = await pattern_learner._analyze_workflow_patterns(sample_project)
        
        assert "max_parallelism" in patterns
        assert "avg_daily_completions" in patterns
        assert "phase_distribution" in patterns
        
        # Check phase distribution
        assert patterns["phase_distribution"]["setup"] == 1
        assert patterns["phase_distribution"]["design"] == 1
        assert patterns["phase_distribution"]["backend"] == 1
    
    @pytest.mark.asyncio
    async def test_identify_success_factors(self, pattern_learner, sample_project):
        """Test success factor identification."""
        factors = await pattern_learner._identify_success_factors(sample_project)
        
        assert "completed_on_time" in factors
        assert "high_completion_rate" in factors
        assert "team_collaboration" in factors
    
    @pytest.mark.asyncio
    async def test_identify_failure_points(self, pattern_learner, sample_project):
        """Test failure point identification."""
        # Add some blocked tasks
        sample_project.tasks.append(
            Task(
                id="TASK-004",
                name="Failed task",
                description="Task that got blocked",
                status=TaskStatus.BLOCKED,
                priority=Priority.HIGH,
                assigned_to="agent1",
                created_at=datetime.now() - timedelta(days=2),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                actual_hours=0.0
            )
        )
        
        failure_points = await pattern_learner._identify_failure_points(sample_project)
        
        # Should identify high blocked task rate if > 10%
        if len([t for t in sample_project.tasks if t.status.value in ['BLOCKED', 'CANCELLED']]) > len(sample_project.tasks) * 0.1:
            assert "high_blocked_task_rate" in failure_points
    
    @pytest.mark.asyncio
    async def test_analyze_team_performance(self, pattern_learner, sample_project):
        """Test team performance analysis."""
        performance = await pattern_learner._analyze_team_performance(sample_project)
        
        assert "velocity" in performance
        assert "team_size" in performance
        assert "tasks_per_person" in performance
        assert "task_type_distribution" in performance
        
        assert performance["team_size"] == 2
        assert performance["velocity"] == len(sample_project.tasks) / sample_project.duration_days
    
    @pytest.mark.asyncio
    async def test_update_estimation_patterns(self, pattern_learner):
        """Test updating estimation patterns."""
        accuracy_data = {
            "setup": 0.85,
            "backend": 0.90
        }
        
        await pattern_learner._update_estimation_patterns(accuracy_data)
        
        assert "estimation_setup" in pattern_learner.patterns
        assert "estimation_backend" in pattern_learner.patterns
        
        setup_pattern = pattern_learner.patterns["estimation_setup"]
        assert setup_pattern.pattern_type == "estimation"
        assert setup_pattern.recommendations["accuracy_multiplier"] == 0.85
        assert setup_pattern.confidence == 0.6
        assert setup_pattern.evidence_count == 1
    
    @pytest.mark.asyncio
    async def test_update_existing_estimation_pattern(self, pattern_learner):
        """Test updating an existing estimation pattern."""
        # Create initial pattern
        pattern_learner.patterns["estimation_setup"] = Pattern(
            pattern_id="estimation_setup",
            pattern_type="estimation",
            description="Estimation accuracy for setup tasks",
            conditions={"task_type": "setup"},
            recommendations={"accuracy_multiplier": 0.8},
            confidence=0.7,
            evidence_count=5,
            last_updated=datetime.now() - timedelta(days=1)
        )
        
        # Update with new data
        await pattern_learner._update_estimation_patterns({"setup": 0.9})
        
        updated_pattern = pattern_learner.patterns["estimation_setup"]
        assert updated_pattern.evidence_count == 6
        assert updated_pattern.confidence == 0.75  # Increased by 0.05
        # Check weighted average: 0.8 * 0.7 + 0.9 * 0.3 = 0.83
        assert 0.82 < updated_pattern.recommendations["accuracy_multiplier"] < 0.84
    
    @pytest.mark.asyncio
    async def test_update_dependency_patterns(self, pattern_learner):
        """Test updating dependency patterns."""
        dependency_patterns = [{
            "pattern": "setup_before_backend",
            "description": "Setup tasks complete before backend",
            "confidence": 0.75,
            "conditions": {"project_type": "web_application"}
        }]
        
        await pattern_learner._update_dependency_patterns(dependency_patterns)
        
        assert "dependency_setup_before_backend" in pattern_learner.patterns
        pattern = pattern_learner.patterns["dependency_setup_before_backend"]
        assert pattern.pattern_type == "dependency"
        assert pattern.confidence == 0.75
    
    @pytest.mark.asyncio
    async def test_update_workflow_patterns(self, pattern_learner):
        """Test updating workflow patterns."""
        workflow_data = {
            "max_parallelism": 3,
            "avg_daily_completions": 1.5,
            "phase_distribution": {"setup": 2, "backend": 4}
        }
        
        await pattern_learner._update_workflow_patterns(workflow_data)
        
        assert "workflow_characteristics" in pattern_learner.patterns
        pattern = pattern_learner.patterns["workflow_characteristics"]
        assert pattern.recommendations["max_parallelism"] == 3
        assert pattern.recommendations["avg_daily_completions"] == 1.5
    
    @pytest.mark.asyncio
    async def test_update_outcome_patterns(self, pattern_learner):
        """Test updating success and failure patterns."""
        success_factors = ["completed_on_time", "accurate_estimation"]
        failure_points = ["high_blocked_task_rate"]
        
        await pattern_learner._update_outcome_patterns(success_factors, failure_points)
        
        # Check success patterns
        assert "success_completed_on_time" in pattern_learner.patterns
        assert "success_accurate_estimation" in pattern_learner.patterns
        
        # Check failure patterns
        assert "failure_high_blocked_task_rate" in pattern_learner.patterns
        
        success_pattern = pattern_learner.patterns["success_completed_on_time"]
        assert success_pattern.pattern_type == "success_factor"
        assert success_pattern.recommendations["positive_impact"] is True
    
    @pytest.mark.asyncio
    async def test_prune_patterns(self, pattern_learner):
        """Test pruning old and low-confidence patterns."""
        # Add patterns with different ages and confidence levels
        pattern_learner.patterns = {
            "old_low_evidence": Pattern(
                pattern_id="old_low_evidence",
                pattern_type="estimation",
                description="Old pattern with low evidence",
                conditions={},
                recommendations={},
                confidence=0.5,
                evidence_count=1,
                last_updated=datetime.now() - timedelta(days=200)
            ),
            "low_confidence": Pattern(
                pattern_id="low_confidence",
                pattern_type="dependency",
                description="Low confidence pattern",
                conditions={},
                recommendations={},
                confidence=0.2,
                evidence_count=10,
                last_updated=datetime.now()
            ),
            "good_pattern": Pattern(
                pattern_id="good_pattern",
                pattern_type="workflow",
                description="Good pattern",
                conditions={},
                recommendations={},
                confidence=0.8,
                evidence_count=20,
                last_updated=datetime.now() - timedelta(days=30)
            )
        }
        
        await pattern_learner._prune_patterns()
        
        # Old with low evidence should be removed
        assert "old_low_evidence" not in pattern_learner.patterns
        # Low confidence should be removed
        assert "low_confidence" not in pattern_learner.patterns
        # Good pattern should remain
        assert "good_pattern" in pattern_learner.patterns
    
    @pytest.mark.asyncio
    async def test_calculate_confidence(self, pattern_learner):
        """Test confidence calculation with evidence and age factors."""
        pattern = Pattern(
            pattern_id="test_pattern",
            pattern_type="estimation",
            description="Test pattern",
            conditions={},
            recommendations={},
            confidence=0.7,
            evidence_count=10,
            last_updated=datetime.now() - timedelta(days=30)
        )
        
        confidence = await pattern_learner.calculate_confidence(pattern)
        
        # Base: 0.7, Evidence bonus: min(0.2, 10*0.02) = 0.2
        # Age penalty: min(0.3, 30*0.001) = 0.03
        # Final: 0.7 + 0.2 - 0.03 = 0.87
        assert 0.86 < confidence < 0.88
    
    def test_classify_task_type(self, pattern_learner, sample_task):
        """Test task type classification."""
        # Test setup task
        assert pattern_learner._classify_task_type(sample_task) == "setup"
        
        # Test backend task
        backend_task = Task(
            id="TASK-002",
            name="Implement backend API",
            description="Build REST endpoints",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0
        )
        assert pattern_learner._classify_task_type(backend_task) == "backend"
        
        # Test general task
        general_task = Task(
            id="TASK-003",
            name="Review code",
            description="Code review session",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0
        )
        assert pattern_learner._classify_task_type(general_task) == "general"
    
    @pytest.mark.asyncio
    async def test_get_patterns_for_context(self, pattern_learner):
        """Test retrieving patterns for a specific context."""
        # Add patterns with different conditions
        pattern_learner.patterns = {
            "web_pattern": Pattern(
                pattern_id="web_pattern",
                pattern_type="workflow",
                description="Web project pattern",
                conditions={"project_type": "web_application"},
                recommendations={"use_framework": "react"},
                confidence=0.8,
                evidence_count=15,
                last_updated=datetime.now()
            ),
            "mobile_pattern": Pattern(
                pattern_id="mobile_pattern",
                pattern_type="workflow",
                description="Mobile project pattern",
                conditions={"project_type": "mobile_app"},
                recommendations={"use_framework": "flutter"},
                confidence=0.7,
                evidence_count=10,
                last_updated=datetime.now()
            ),
            "general_pattern": Pattern(
                pattern_id="general_pattern",
                pattern_type="estimation",
                description="General pattern",
                conditions={},
                recommendations={"buffer": 1.2},
                confidence=0.9,
                evidence_count=50,
                last_updated=datetime.now()
            )
        }
        
        # Mock calculate_confidence to return the pattern's confidence
        pattern_learner.calculate_confidence = AsyncMock(side_effect=lambda p: p.confidence)
        
        # Get patterns for web context
        context = {"project_type": "web_application", "team_size": 3}
        patterns = await pattern_learner.get_patterns_for_context(context)
        
        assert len(patterns) == 2  # web_pattern and general_pattern
        assert patterns[0].pattern_id == "general_pattern"  # Higher confidence first
        assert patterns[1].pattern_id == "web_pattern"
    
    @pytest.mark.asyncio
    async def test_export_patterns(self, pattern_learner):
        """Test exporting patterns for persistence."""
        # Add some patterns
        pattern_learner.patterns = {
            "pattern1": Pattern(
                pattern_id="pattern1",
                pattern_type="estimation",
                description="Test pattern",
                conditions={"task_type": "setup"},
                recommendations={"multiplier": 1.2},
                confidence=0.8,
                evidence_count=10,
                last_updated=datetime.now()
            )
        }
        
        export_data = await pattern_learner.export_patterns()
        
        assert "patterns" in export_data
        assert "export_timestamp" in export_data
        assert "pattern_count" in export_data
        assert export_data["pattern_count"] == 1
        assert "pattern1" in export_data["patterns"]
    
    @pytest.mark.asyncio
    async def test_import_patterns(self, pattern_learner):
        """Test importing patterns from persistence."""
        import_data = {
            "patterns": {
                "imported_pattern": {
                    "pattern_id": "imported_pattern",
                    "pattern_type": "workflow",
                    "description": "Imported pattern",
                    "conditions": {},
                    "recommendations": {"test": "value"},
                    "confidence": 0.75,
                    "evidence_count": 5,
                    "last_updated": datetime.now().isoformat()
                }
            },
            "export_timestamp": datetime.now().isoformat(),
            "pattern_count": 1
        }
        
        await pattern_learner.import_patterns(import_data)
        
        assert "imported_pattern" in pattern_learner.patterns
        pattern = pattern_learner.patterns["imported_pattern"]
        assert pattern.pattern_type == "workflow"
        assert pattern.confidence == 0.75
        assert isinstance(pattern.last_updated, datetime)
    
    @pytest.mark.asyncio
    async def test_complete_learning_workflow(self, pattern_learner, sample_project):
        """Test complete learning workflow from project to patterns."""
        # Learn from project
        await pattern_learner.learn_from_project(sample_project)
        
        # Verify patterns were created
        assert len(pattern_learner.patterns) > 0
        
        # Get patterns for context
        context = {"project_type": "web_application"}
        patterns = await pattern_learner.get_patterns_for_context(context)
        
        assert len(patterns) > 0
        
        # Export and import patterns
        export_data = await pattern_learner.export_patterns()
        
        # Convert datetime objects to strings in the export data (simulating persistence)
        for pattern_dict in export_data["patterns"].values():
            if "last_updated" in pattern_dict and isinstance(pattern_dict["last_updated"], datetime):
                pattern_dict["last_updated"] = pattern_dict["last_updated"].isoformat()
        
        # Clear patterns
        pattern_learner.patterns = {}
        
        # Import back
        await pattern_learner.import_patterns(export_data)
        
        # Verify patterns were restored
        assert len(pattern_learner.patterns) == export_data["pattern_count"]
    
    @pytest.mark.asyncio
    async def test_error_handling_empty_project(self, pattern_learner):
        """Test handling of empty project data."""
        empty_project = CompletedProject(
            project_id="EMPTY-001",
            name="Empty Project",
            tasks=[],
            completion_date=datetime.now(),
            success_metrics={},
            team_size=0,
            duration_days=0,
            project_type="test"
        )
        
        # Should handle empty project gracefully
        await pattern_learner.learn_from_project(empty_project)
        
        assert len(pattern_learner.project_history) == 1
    
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, pattern_learner):
        """Test performance with large dataset."""
        # Create a project with many tasks
        tasks = []
        for i in range(100):
            task_type = ["setup", "backend", "frontend", "testing"][i % 4]
            task = Task(
                id=f"TASK-{i:03d}",
                name=f"{task_type} task {i}",
                description=f"Description for {task_type} task",
                status=TaskStatus.DONE,
                priority=Priority.MEDIUM,
                assigned_to=f"agent{i % 3}",
                created_at=datetime.now() - timedelta(days=30-i//10),
                updated_at=datetime.now() - timedelta(days=i//10),
                due_date=datetime.now() + timedelta(days=7),
                estimated_hours=float(4 + i % 8),
                actual_hours=float(4 + i % 8 + (i % 3 - 1)),
                dependencies=[],
                labels=[task_type]
            )
            task.completed_at = datetime.now() - timedelta(days=i//10)
            tasks.append(task)
        
        large_project = CompletedProject(
            project_id="LARGE-001",
            name="Large Project",
            tasks=tasks,
            completion_date=datetime.now(),
            success_metrics={"planned_duration": 30},
            team_size=3,
            duration_days=30,
            project_type="large_application"
        )
        
        # Should complete within reasonable time (test timeout enforces < 100ms)
        await pattern_learner.learn_from_project(large_project)
        
        # Verify patterns were learned
        assert len(pattern_learner.patterns) > 0
        assert len(pattern_learner.project_history) == 1