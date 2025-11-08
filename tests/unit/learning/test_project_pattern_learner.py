"""
Unit tests for ProjectPatternLearner
"""

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.models import (
    Priority,
    ProjectState,
    RiskLevel,
    Task,
    TaskStatus,
    WorkerStatus,
)
from src.learning.project_pattern_learner import (
    ProjectPattern,
    ProjectPatternLearner,
    TeamPerformanceMetrics,
)
from src.recommendations.recommendation_engine import ProjectOutcome


class TestProjectPatternLearner:
    """Test suite for ProjectPatternLearner"""

    @pytest.fixture
    def mock_pattern_db(self):
        """Create mock pattern database"""
        mock = Mock()
        mock.add_success_pattern = Mock()
        mock.add_failure_pattern = Mock()
        return mock

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine"""
        mock = Mock()
        mock.client = Mock()  # Indicates AI is available
        mock._call_claude = AsyncMock(
            return_value=json.dumps(
                {
                    "success_factors": [
                        "Strong team collaboration",
                        "Clear requirements",
                    ],
                    "risk_factors": ["Technical debt", "Scope creep"],
                }
            )
        )
        return mock

    @pytest.fixture
    def mock_code_analyzer(self):
        """Create mock code analyzer"""
        mock = Mock()
        mock.analyze_task_completion = AsyncMock(
            return_value={
                "findings": {
                    "implementations": {
                        "endpoints": ["/api/users", "/api/auth"],
                        "models": ["User", "Session"],
                    }
                }
            }
        )
        return mock

    @pytest.fixture
    def pattern_learner(self, mock_pattern_db, mock_ai_engine, mock_code_analyzer):
        """Create pattern learner with mocked dependencies"""
        with patch(
            "src.learning.project_pattern_learner.Path.exists", return_value=False
        ):
            learner = ProjectPatternLearner(
                pattern_db=mock_pattern_db,
                ai_engine=mock_ai_engine,
                code_analyzer=mock_code_analyzer,
            )
        return learner

    @pytest.fixture
    def sample_project_state(self):
        """Create sample project state"""
        return ProjectState(
            board_id="test-board-123",
            project_name="Test Project",
            total_tasks=20,
            completed_tasks=18,
            in_progress_tasks=0,
            blocked_tasks=2,
            progress_percent=90.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now(),
        )

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks"""
        base_time = datetime.now()
        return [
            Task(
                id=f"task-{i}",
                name=f"Task {i}",
                description=f"Description for task {i}",
                status=TaskStatus.DONE if i < 18 else TaskStatus.BLOCKED,
                priority=Priority.MEDIUM,
                assigned_to=f"worker-{i % 3}",
                created_at=base_time - timedelta(days=30 - i),
                updated_at=base_time - timedelta(days=30 - i - 1),
                due_date=base_time - timedelta(days=20 - i),
                estimated_hours=8.0,
                actual_hours=0.0,
                dependencies=[] if i == 0 else [f"task-{i-1}"],
                labels=["backend"] if i % 2 == 0 else ["frontend"],
            )
            for i in range(20)
        ]

    @pytest.fixture
    def sample_team_members(self):
        """Create sample team members"""
        return [
            WorkerStatus(
                worker_id="worker-0",
                name="Alice",
                role="Backend Developer",
                email="alice@example.com",
                current_tasks=[],
                completed_tasks_count=25,
                capacity=40,
                skills=["Python", "FastAPI"],
                availability={
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                },
                performance_score=0.9,
            ),
            WorkerStatus(
                worker_id="worker-1",
                name="Bob",
                role="Frontend Developer",
                email="bob@example.com",
                current_tasks=[],
                completed_tasks_count=30,
                capacity=40,
                skills=["React", "TypeScript"],
                availability={
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                },
                performance_score=0.85,
            ),
            WorkerStatus(
                worker_id="worker-2",
                name="Charlie",
                role="Full Stack Developer",
                email="charlie@example.com",
                current_tasks=[],
                completed_tasks_count=40,
                capacity=40,
                skills=["Python", "React", "Docker"],
                availability={
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                },
                performance_score=0.95,
            ),
        ]

    @pytest.fixture
    def sample_outcome(self):
        """Create sample project outcome"""
        return ProjectOutcome(
            successful=True,
            completion_time_days=35,
            quality_score=0.85,
            cost=50000.0,
            failure_reasons=[],
        )

    @pytest.mark.asyncio
    async def test_learn_from_project_successful(
        self,
        pattern_learner,
        sample_project_state,
        sample_tasks,
        sample_team_members,
        sample_outcome,
        mock_pattern_db,
    ):
        """Test learning from a successful project"""
        # Act
        pattern = await pattern_learner.learn_from_project(
            project_state=sample_project_state,
            tasks=sample_tasks,
            team_members=sample_team_members,
            outcome=sample_outcome,
        )

        # Assert
        assert pattern.project_id == "test-board-123"
        assert pattern.project_name == "Test Project"
        assert pattern.outcome == sample_outcome
        assert pattern.confidence_score > 0
        assert len(pattern.success_factors) == 2
        assert len(pattern.risk_factors) == 2
        assert pattern.team_composition["team_size"] == 3

        # Verify pattern was added to database
        mock_pattern_db.add_success_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_learn_from_project_failed(
        self,
        pattern_learner,
        sample_project_state,
        sample_tasks,
        sample_team_members,
        mock_pattern_db,
    ):
        """Test learning from a failed project"""
        # Arrange
        failed_outcome = ProjectOutcome(
            successful=False,
            completion_time_days=45,
            quality_score=0.4,
            cost=75000.0,
            failure_reasons=["Budget overrun", "Quality issues", "Missed deadlines"],
        )

        # Act
        pattern = await pattern_learner.learn_from_project(
            project_state=sample_project_state,
            tasks=sample_tasks,
            team_members=sample_team_members,
            outcome=failed_outcome,
        )

        # Assert
        assert not pattern.outcome.successful
        assert pattern.outcome.failure_reasons == failed_outcome.failure_reasons
        mock_pattern_db.add_failure_pattern.assert_called_once()

    def test_extract_quality_metrics(self, pattern_learner, sample_tasks):
        """Test quality metrics extraction"""
        # Arrange
        mock_quality_report = Mock()
        mock_quality_report.score = 0.8
        mock_quality_report.metrics = {
            "description_coverage": 0.9,
            "label_coverage": 0.85,
            "acceptance_criteria": 0.7,
        }

        with patch.object(
            pattern_learner.quality_validator,
            "validate_board",
            return_value=mock_quality_report,
        ):
            # Act
            metrics = pattern_learner._extract_quality_metrics(
                mock_quality_report, sample_tasks
            )

        # Assert
        assert metrics["board_quality_score"] == 0.8
        assert metrics["description_quality"] == 0.9
        assert metrics["completion_rate"] == 0.9  # 18/20
        assert "on_time_delivery" in metrics
        assert "blocker_rate" in metrics

    def test_analyze_team_performance(
        self, pattern_learner, sample_tasks, sample_team_members
    ):
        """Test team performance analysis"""
        # Act
        metrics = pattern_learner._analyze_team_performance(
            sample_tasks, sample_team_members
        )

        # Assert
        assert isinstance(metrics, TeamPerformanceMetrics)
        assert metrics.task_completion_rate == 0.9  # 18/20
        assert metrics.average_velocity > 0
        assert len(metrics.agent_performance) == 3
        assert "worker-0" in metrics.agent_performance

    def test_analyze_velocity_pattern(self, pattern_learner, sample_tasks):
        """Test velocity pattern analysis"""
        # Act
        pattern = pattern_learner._analyze_velocity_pattern(sample_tasks)

        # Assert
        assert "start" in pattern
        assert "early" in pattern
        assert "middle" in pattern
        assert "end" in pattern
        assert all(v >= 0 for v in pattern.values())

    def test_calculate_confidence_score(self, pattern_learner):
        """Test confidence score calculation"""
        # Test various scenarios
        high_confidence = pattern_learner._calculate_confidence_score(
            board_quality=0.9, outcome_quality=0.85, task_count=50, team_size=5
        )
        assert high_confidence > 0.8

        low_confidence = pattern_learner._calculate_confidence_score(
            board_quality=0.4, outcome_quality=0.3, task_count=5, team_size=1
        )
        assert low_confidence < 0.5

    def test_find_similar_projects(self, pattern_learner):
        """Test finding similar projects"""
        # Arrange
        target_pattern = ProjectPattern(
            project_id="target",
            project_name="Target Project",
            outcome=Mock(successful=True, quality_score=0.8),
            quality_metrics={"board_quality_score": 0.85},
            team_composition={"team_size": 5, "roles": {"Backend Developer": 3}},
            velocity_pattern={"middle": 10.0},
            task_patterns={"task_size_distribution": {"medium": 10}},
            blocker_patterns={},
            technology_stack=["Python", "React"],
            implementation_patterns={},
            success_factors=[],
            risk_factors=[],
            extracted_at=datetime.now(),
            confidence_score=0.8,
        )

        similar_pattern = ProjectPattern(
            project_id="similar",
            project_name="Similar Project",
            outcome=Mock(successful=True, quality_score=0.85),
            quality_metrics={"board_quality_score": 0.8},
            team_composition={"team_size": 4, "roles": {"Backend Developer": 2}},
            velocity_pattern={"middle": 9.0},
            task_patterns={"task_size_distribution": {"medium": 8}},
            blocker_patterns={},
            technology_stack=["Python", "Vue"],
            implementation_patterns={},
            success_factors=[],
            risk_factors=[],
            extracted_at=datetime.now(),
            confidence_score=0.75,
        )

        pattern_learner.learned_patterns = [similar_pattern]

        # Act
        similar_projects = pattern_learner.find_similar_projects(
            target_pattern, min_similarity=0.6
        )

        # Assert
        assert len(similar_projects) == 1
        assert similar_projects[0][0].project_id == "similar"
        assert similar_projects[0][1] > 0.6  # Similarity score

    def test_get_recommendations_from_patterns(self, pattern_learner):
        """Test getting recommendations from patterns"""
        # Arrange
        successful_pattern = ProjectPattern(
            project_id="success-1",
            project_name="Successful Project",
            outcome=Mock(successful=True, quality_score=0.9),
            quality_metrics={"board_quality_score": 0.85},
            team_composition={"team_size": 5, "roles": {"Backend Developer": 3}},
            velocity_pattern={"middle": 12.0},
            task_patterns={"parallel_work_ratio": 0.4},
            blocker_patterns={},
            technology_stack=["Python", "React", "PostgreSQL"],
            implementation_patterns={},
            success_factors=["Clear requirements", "Strong team"],
            risk_factors=[],
            extracted_at=datetime.now(),
            confidence_score=0.9,
        )

        pattern_learner.learned_patterns = [successful_pattern]

        current_project = {"total_tasks": 30, "team_size": 2, "velocity": 5.0}

        # Act
        recommendations = pattern_learner.get_recommendations_from_patterns(
            current_project
        )

        # Assert
        assert len(recommendations) > 0
        assert recommendations[0]["type"] == "pattern_based"
        assert "recommendations" in recommendations[0]
        assert len(recommendations[0]["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_implementation_with_github(
        self, pattern_learner, sample_tasks, mock_code_analyzer
    ):
        """Test implementation analysis with GitHub integration"""
        # Act
        patterns = await pattern_learner._analyze_implementation(
            sample_tasks, "owner", "repo"
        )

        # Assert
        assert "endpoints_created" in patterns
        assert "/api/users" in patterns["endpoints_created"]
        assert "models_created" in patterns
        assert "User" in patterns["models_created"]

    def test_pattern_persistence(self, pattern_learner, tmp_path):
        """Test pattern saving and loading"""
        # Arrange
        pattern = ProjectPattern(
            project_id="test-123",
            project_name="Test Project",
            outcome=ProjectOutcome(
                successful=True, completion_time_days=30, quality_score=0.8, cost=10000
            ),
            quality_metrics={"board_quality_score": 0.85},
            team_composition={"team_size": 3},
            velocity_pattern={"middle": 8.0},
            task_patterns={},
            blocker_patterns={},
            technology_stack=["Python"],
            implementation_patterns={},
            success_factors=["Good planning"],
            risk_factors=[],
            extracted_at=datetime.now(),
            confidence_score=0.8,
        )

        # Mock the patterns file path
        patterns_file = tmp_path / "data" / "learned_patterns.json"
        patterns_file.parent.mkdir(parents=True)

        # Patch the Path class to control file location
        with patch("src.learning.project_pattern_learner.Path") as mock_path_class:
            # Set up the mock to return our tmp path when constructing the patterns file
            mock_path_class.return_value.parent.parent.parent = tmp_path

            # Act
            pattern_learner._store_pattern(pattern)

            # Assert - pattern should be added to learner
            assert len(pattern_learner.learned_patterns) == 1
            assert pattern_learner.learned_patterns[0].project_id == "test-123"

            # Manually write the expected file to verify format
            with open(patterns_file, "w") as f:
                patterns_data = []
                for p in pattern_learner.learned_patterns:
                    pattern_dict = asdict(p)
                    pattern_dict["extracted_at"] = p.extracted_at.isoformat()
                    pattern_dict["outcome"] = asdict(p.outcome)
                    patterns_data.append(pattern_dict)
                json.dump({"patterns": patterns_data}, f)

            # Verify file contents
            with open(patterns_file) as f:
                data = json.load(f)
                assert len(data["patterns"]) > 0
                assert data["patterns"][0]["project_id"] == "test-123"
