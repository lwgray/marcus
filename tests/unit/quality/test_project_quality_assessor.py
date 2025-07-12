"""
Unit tests for ProjectQualityAssessor
"""

import json
from datetime import datetime, timedelta
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
from src.quality.project_quality_assessor import (
    CodeQualityMetrics,
    ProcessQualityMetrics,
    ProjectQualityAssessment,
    ProjectQualityAssessor,
)


class TestProjectQualityAssessor:
    """Test suite for ProjectQualityAssessor"""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine"""
        mock = Mock()
        mock.client = Mock()  # Indicates AI is available
        mock._call_claude = AsyncMock(
            return_value=json.dumps(
                {
                    "insights": [
                        "Strong test coverage ensures reliability",
                        "Fast code review turnaround",
                    ],
                    "recommendations": [
                        "Improve documentation coverage",
                        "Implement automated deployment",
                    ],
                    "overall_assessment": "good",
                    "strengths": ["Quality focus", "Team collaboration"],
                    "weaknesses": ["Manual deployments"],
                }
            )
        )
        return mock

    @pytest.fixture
    def mock_github_mcp(self):
        """Create mock GitHub MCP interface"""
        mock = Mock()

        # Mock commit data
        mock.list_commits = AsyncMock(
            return_value={
                "commits": [
                    {
                        "commit": {
                            "author": {"date": "2025-01-10T10:00:00Z"},
                            "message": "Add user authentication",
                        }
                    },
                    {
                        "commit": {
                            "author": {"date": "2025-01-09T10:00:00Z"},
                            "message": "Update README documentation",
                        }
                    },
                ]
            }
        )

        # Mock PR data
        mock.search_issues = AsyncMock(
            side_effect=[
                {  # PRs
                    "items": [
                        {
                            "number": 1,
                            "created_at": "2025-01-09T10:00:00Z",
                            "merged_at": "2025-01-10T10:00:00Z",
                            "user": {"login": "dev1"},
                        }
                    ]
                },
                {  # Issues
                    "items": [
                        {
                            "created_at": "2025-01-08T10:00:00Z",
                            "closed_at": "2025-01-09T10:00:00Z",
                        }
                    ]
                },
            ]
        )

        # Mock reviews
        mock.list_pr_reviews = AsyncMock(
            return_value={
                "reviews": [
                    {
                        "state": "APPROVED",
                        "pull_request_url": "https://github.com/owner/repo/pull/1",
                        "user": {"login": "reviewer1"},
                    }
                ]
            }
        )

        return mock

    @pytest.fixture
    def mock_board_validator(self):
        """Create mock board validator"""
        mock = Mock()
        mock.validate_board = Mock(
            return_value=Mock(
                score=0.85,
                metrics={
                    "description_coverage": 0.9,
                    "acceptance_criteria": 0.8,
                    "label_coverage": 0.85,
                },
            )
        )
        return mock

    @pytest.fixture
    def quality_assessor(self, mock_ai_engine, mock_github_mcp, mock_board_validator):
        """Create quality assessor with mocked dependencies"""
        return ProjectQualityAssessor(
            ai_engine=mock_ai_engine,
            github_mcp=mock_github_mcp,
            board_validator=mock_board_validator,
        )

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
                updated_at=base_time - timedelta(days=25 - i),
                due_date=base_time - timedelta(days=20 - i),
                estimated_hours=8.0,
                actual_hours=0.0,
                dependencies=[],
                labels=["backend", "tested"] if i % 2 == 0 else ["frontend"],
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
                completed_tasks_count=6,
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
                completed_tasks_count=6,
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
                completed_tasks_count=6,
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

    @pytest.mark.asyncio
    async def test_assess_project_quality_without_github(
        self, quality_assessor, sample_project_state, sample_tasks, sample_team_members
    ):
        """Test quality assessment without GitHub integration"""
        # Act
        assessment = await quality_assessor.assess_project_quality(
            project_state=sample_project_state,
            tasks=sample_tasks,
            team_members=sample_team_members,
            github_config=None,
        )

        # Assert
        assert isinstance(assessment, ProjectQualityAssessment)
        assert assessment.project_id == "test-board-123"
        assert assessment.project_name == "Test Project"
        assert assessment.overall_score > 0
        assert assessment.overall_score <= 1
        assert len(assessment.quality_insights) > 0
        assert len(assessment.improvement_areas) > 0

    @pytest.mark.asyncio
    async def test_assess_project_quality_with_github(
        self,
        quality_assessor,
        sample_project_state,
        sample_tasks,
        sample_team_members,
        mock_github_mcp,
    ):
        """Test quality assessment with GitHub integration"""
        # Arrange
        github_config = {
            "github_owner": "test-owner",
            "github_repo": "test-repo",
            "project_start_date": "2025-01-01",
        }

        # Act
        assessment = await quality_assessor.assess_project_quality(
            project_state=sample_project_state,
            tasks=sample_tasks,
            team_members=sample_team_members,
            github_config=github_config,
        )

        # Assert
        assert assessment.code_quality_score > 0
        assert assessment.process_quality_score > 0
        assert assessment.code_metrics.code_review_coverage > 0
        assert assessment.process_metrics.pr_approval_rate > 0

        # Verify GitHub calls were made
        mock_github_mcp.list_commits.assert_called_once()
        mock_github_mcp.search_issues.assert_called()

    def test_analyze_task_quality(self, quality_assessor, sample_tasks):
        """Test task quality analysis"""
        # Act
        metrics = quality_assessor._analyze_task_quality(sample_tasks)

        # Assert
        assert metrics["total_tasks"] == 20
        assert metrics["completed_tasks"] == 18
        assert metrics["completion_rate"] == 0.9
        assert metrics["board_quality_score"] == 0.85
        assert metrics["blocked_task_rate"] == 0.1

    def test_analyze_team_quality(
        self, quality_assessor, sample_tasks, sample_team_members
    ):
        """Test team quality analysis"""
        # Act
        metrics = quality_assessor._analyze_team_quality(
            sample_tasks, sample_team_members
        )

        # Assert
        assert metrics["team_size"] == 3
        assert metrics["avg_tasks_per_member"] == pytest.approx(20 / 3, 0.1)
        assert metrics["skill_diversity"] == 5  # Unique skills
        assert "workload_balance" in metrics
        assert "member_performance" in metrics
        assert len(metrics["member_performance"]) == 3

    def test_analyze_delivery_quality(
        self, quality_assessor, sample_project_state, sample_tasks
    ):
        """Test delivery quality analysis"""
        # Act
        metrics = quality_assessor._analyze_delivery_quality(
            sample_project_state, sample_tasks
        )

        # Assert
        assert metrics["progress_percent"] == 90.0
        assert metrics["velocity_trend"] == "stable"
        assert "on_time_delivery_rate" in metrics
        assert metrics["risk_score"] == 0.5  # Default value when not present

    @pytest.mark.asyncio
    async def test_analyze_code_quality(self, quality_assessor):
        """Test code quality analysis from GitHub data"""
        # Arrange
        github_data = {
            "commits": [
                {
                    "commit": {
                        "author": {"date": "2025-01-10T10:00:00Z"},
                        "message": "Add tests",
                    }
                },
                {
                    "commit": {
                        "author": {"date": "2025-01-09T10:00:00Z"},
                        "message": "Update docs",
                    }
                },
                {
                    "commit": {
                        "author": {"date": "2025-01-08T10:00:00Z"},
                        "message": "Fix bug",
                    }
                },
            ],
            "pull_requests": [{"number": 1}, {"number": 2}],
            "reviews": [
                {"state": "APPROVED", "pull_request_url": "/pull/1"},
                {"state": "APPROVED", "pull_request_url": "/pull/2"},
            ],
        }

        # Act
        metrics = await quality_assessor._analyze_code_quality(github_data)

        # Assert
        assert isinstance(metrics, CodeQualityMetrics)
        assert metrics.commit_frequency > 0
        assert metrics.code_review_coverage == 1.0  # 2 reviewed PRs / 2 PRs
        assert metrics.documentation_coverage > 0
        assert metrics.maintainability_index > 0

    @pytest.mark.asyncio
    async def test_analyze_process_quality(self, quality_assessor):
        """Test process quality analysis from GitHub data"""
        # Arrange
        github_data = {
            "pull_requests": [
                {
                    "created_at": "2025-01-09T10:00:00Z",
                    "merged_at": "2025-01-10T10:00:00Z",
                    "user": {"login": "dev1"},
                }
            ],
            "reviews": [{"state": "APPROVED", "user": {"login": "reviewer1"}}],
            "issues": [
                {
                    "created_at": "2025-01-08T10:00:00Z",
                    "closed_at": "2025-01-09T10:00:00Z",
                }
            ],
        }

        # Act
        metrics = await quality_assessor._analyze_process_quality(github_data)

        # Assert
        assert isinstance(metrics, ProcessQualityMetrics)
        assert metrics.pr_approval_rate == 1.0
        assert metrics.avg_review_time_hours == 24.0
        assert metrics.issue_resolution_time == 1.0

    def test_determine_project_success(self, quality_assessor):
        """Test project success determination"""
        # Test successful project
        delivery_metrics = {
            "progress_percent": 98,
            "on_time_delivery_rate": 0.9,
            "risk_score": 0.1,
        }
        ai_assessment = {"overall_assessment": "excellent"}

        result = quality_assessor._determine_project_success(
            overall_score=0.85,
            delivery_metrics=delivery_metrics,
            ai_assessment=ai_assessment,
        )

        assert result["is_successful"] is True
        assert result["confidence"] > 0.8
        assert "reasoning" in result

        # Test failed project
        delivery_metrics["progress_percent"] = 60
        delivery_metrics["risk_score"] = 0.8
        ai_assessment["overall_assessment"] = "poor"

        result = quality_assessor._determine_project_success(
            overall_score=0.4,
            delivery_metrics=delivery_metrics,
            ai_assessment=ai_assessment,
        )

        assert result["is_successful"] is False
        assert result["confidence"] < 0.5

    def test_calculate_workload_balance(
        self, quality_assessor, sample_tasks, sample_team_members
    ):
        """Test workload balance calculation"""
        # Act
        balance = quality_assessor._calculate_workload_balance(
            sample_tasks, sample_team_members
        )

        # Assert
        assert 0 <= balance <= 1
        # With evenly distributed tasks, balance should be high
        assert balance > 0.7

    def test_extract_quality_insights(self, quality_assessor):
        """Test quality insights extraction"""
        # Arrange
        code_metrics = CodeQualityMetrics(test_coverage=0.85, code_review_coverage=0.95)
        process_metrics = ProcessQualityMetrics(avg_review_time_hours=12)
        delivery_metrics = {"on_time_delivery_rate": 0.95}
        team_metrics = {"workload_balance": 0.85}
        ai_assessment = {"insights": ["AI insight 1", "AI insight 2"]}

        # Act
        insights = quality_assessor._extract_quality_insights(
            code_metrics, process_metrics, delivery_metrics, team_metrics, ai_assessment
        )

        # Assert
        assert len(insights) > 0
        assert any("test coverage" in i.lower() for i in insights)
        assert any("code review" in i.lower() for i in insights)

    def test_identify_improvement_areas(self, quality_assessor):
        """Test improvement area identification"""
        # Arrange
        ai_assessment = {"recommendations": ["Use CI/CD", "Add more tests"]}

        # Act
        areas = quality_assessor._identify_improvement_areas(
            code_score=0.6,
            process_score=0.5,
            delivery_score=0.8,
            team_score=0.9,
            ai_assessment=ai_assessment,
        )

        # Assert
        assert len(areas) > 0
        assert any("process" in area.lower() for area in areas)
        assert any("code quality" in area.lower() for area in areas)
