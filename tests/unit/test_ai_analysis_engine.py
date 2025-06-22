import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.core.models import Task, TaskStatus, Priority, WorkerStatus, ProjectState, RiskLevel
from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine


class TestAIAnalysisEngine:
    """
    Test suite for the AI Analysis Engine.
    
    This tests the core intelligence of our PM Agent - how it makes decisions
    about task assignments, analyzes blockers, and provides recommendations.
    """
    
    @pytest.fixture
    def ai_engine(self):
        """
        STEP 1: Create a test instance of the AI Analysis Engine
        
        What's happening:
        - We create an instance of our AI engine
        - In tests, we'll mock the Anthropic client to avoid real API calls
        - This fixture runs before each test method
        """
        with patch('anthropic.Anthropic') as mock_anthropic:
            engine = AIAnalysisEngine()
            # Mock the client to avoid real API calls in tests
            engine.client = Mock()
            return engine
    
    @pytest.fixture
    def sample_tasks(self):
        """
        STEP 2: Create sample task data for testing
        
        What's happening:
        - We create realistic task objects that represent different scenarios
        - These tasks have varying priorities, skills requirements, and complexities
        - This helps us test how the AI makes decisions with different inputs
        """
        return [
            Task(
                id="TASK-001",
                name="Implement user authentication",
                description="Add OAuth2 login functionality",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=3),
                estimated_hours=16.0,
                dependencies=[],
                labels=["backend", "security", "oauth"]
            ),
            Task(
                id="TASK-002",
                name="Create dashboard UI",
                description="Design and implement analytics dashboard",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=5),
                estimated_hours=24.0,
                dependencies=["TASK-001"],
                labels=["frontend", "react", "ui/ux"]
            ),
            Task(
                id="TASK-003",
                name="Fix critical bug in payment system",
                description="Payment processing fails for certain cards",
                status=TaskStatus.TODO,
                priority=Priority.URGENT,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=datetime.now() + timedelta(hours=4),
                estimated_hours=4.0,
                dependencies=[],
                labels=["backend", "payments", "bug", "critical"]
            )
        ]
    
    @pytest.fixture
    def sample_workers(self):
        """
        STEP 3: Create sample worker profiles
        
        What's happening:
        - We create different worker personas with varying skills and capacities
        - Each worker has different strengths (backend vs frontend, senior vs junior)
        - This tests how the AI matches tasks to the right people
        """
        return {
            "backend_senior": WorkerStatus(
                worker_id="dev-001",
                name="Alice Johnson",
                role="Senior Backend Developer",
                email="alice@example.com",
                current_tasks=[],
                completed_tasks_count=50,
                capacity=40,
                skills=["python", "django", "postgresql", "oauth", "payments", "security"],
                availability={"monday": True, "tuesday": True, "wednesday": True},
                performance_score=1.2  # Above average performer
            ),
            "frontend_dev": WorkerStatus(
                worker_id="dev-002", 
                name="Bob Smith",
                role="Frontend Developer",
                email="bob@example.com",
                current_tasks=[],
                completed_tasks_count=30,
                capacity=35,
                skills=["react", "typescript", "css", "ui/ux", "javascript"],
                availability={"monday": True, "tuesday": True},
                performance_score=1.0
            ),
            "fullstack_junior": WorkerStatus(
                worker_id="dev-003",
                name="Charlie Davis",
                role="Junior Full-stack Developer",
                email="charlie@example.com",
                current_tasks=[],
                completed_tasks_count=10,
                capacity=30,
                skills=["python", "react", "basic"],
                availability={"monday": True},
                performance_score=0.8  # Still learning
            )
        }
    
    @pytest.mark.asyncio
    async def test_match_task_to_agent_urgent_priority(self, ai_engine, sample_tasks, sample_workers):
        """
        TEST 1: Verify AI assigns urgent tasks to the most qualified available agent
        
        What's being tested:
        1. The AI recognizes task priority (URGENT > HIGH > MEDIUM)
        2. It matches task requirements (payments) to worker skills
        3. It selects the senior developer for critical work
        
        Step-by-step:
        1. We mock the AI's response to return TASK-003 (urgent payment bug)
        2. We ask the AI to find a task for our senior backend developer
        3. We verify it chose the urgent task over others
        """
        # STEP 1: Mock the Claude API response
        mock_response = {
            "recommended_task_id": "TASK-003",  # The urgent payment bug
            "confidence_score": 0.95,
            "reasoning": "Urgent payment bug requires immediate attention from experienced developer",
            "alternative_tasks": ["TASK-001"],
            "considerations": ["Critical business impact", "Matches developer skills"]
        }
        
        ai_engine._call_claude = AsyncMock(return_value=json.dumps(mock_response))
        
        # STEP 2: Create a simple project state
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=10,
            completed_tasks=3,
            in_progress_tasks=2,
            blocked_tasks=0,
            progress_percent=30.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.MEDIUM,
            last_updated=datetime.now()
        )
        
        # STEP 3: Call the AI to match a task
        result = await ai_engine.match_task_to_agent(
            sample_tasks,
            sample_workers["backend_senior"],
            project_state
        )
        
        # STEP 4: Verify the results
        assert result is not None
        assert result.id == "TASK-003"
        assert result.priority == Priority.URGENT
        
        # STEP 5: Verify the AI was called with proper context
        call_args = ai_engine._call_claude.call_args[0][0]
        assert "payment" in call_args.lower()
        assert "urgent" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_generate_task_instructions(self, ai_engine, sample_tasks, sample_workers):
        """
        TEST 2: Verify AI generates appropriate instructions based on worker experience
        
        What's being tested:
        1. The AI tailors instructions to the worker's skill level
        2. Instructions are comprehensive and actionable
        3. The AI considers the task context and requirements
        
        Step-by-step:
        1. We test with both senior and junior developers
        2. We verify instructions are more detailed for juniors
        3. We check that instructions include relevant technical details
        """
        # Test Case 1: Instructions for senior developer
        senior_task = sample_tasks[0]  # Auth implementation
        senior_worker = sample_workers["backend_senior"]
        
        # Mock response for senior developer
        ai_engine._call_claude = AsyncMock(
            return_value="""## OAuth2 Implementation Instructions

Given your experience with authentication systems, here's the streamlined approach:

1. **Setup OAuth2 Provider**
   - Configure Google/GitHub OAuth credentials
   - Set up redirect URIs in provider console

2. **Implementation**
   - Use `authlib` or `python-social-auth` 
   - Implement callback handlers
   - Store tokens securely (consider Redis for sessions)

3. **Security Considerations**
   - Implement PKCE flow for additional security
   - Set up proper CORS policies
   - Add rate limiting on auth endpoints

You're familiar with these patterns, so focus on our specific business requirements."""
        )
        
        senior_instructions = await ai_engine.generate_task_instructions(
            senior_task,
            senior_worker
        )
        
        # Verify senior instructions are concise but thorough
        assert "OAuth2" in senior_instructions
        assert "PKCE" in senior_instructions  # Advanced security concept
        assert len(senior_instructions) < 1000  # Not overly verbose
        
        # Test Case 2: Instructions for junior developer
        junior_worker = sample_workers["fullstack_junior"]
        
        # Mock more detailed response for junior
        ai_engine._call_claude = AsyncMock(
            return_value="""## OAuth2 Implementation Instructions - Detailed Guide

Since this is your first OAuth2 implementation, here's a step-by-step guide:

1. **Understanding OAuth2**
   - OAuth2 is a protocol that allows users to log in using existing accounts
   - Read this primer first: [link to OAuth2 basics]

2. **Detailed Implementation Steps**
   
   a. Install required packages:
   ```bash
   pip install authlib requests
   ```
   
   b. Create OAuth configuration:
   ```python
   # config/oauth.py
   OAUTH_PROVIDERS = {
       'google': {
           'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
           'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
           'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
           'token_url': 'https://oauth2.googleapis.com/token'
       }
   }
   ```
   
   c. Implement the login route:
   ```python
   @app.route('/login/<provider>')
   def login(provider):
       # Detailed implementation here...
   ```

3. **Testing Your Implementation**
   - Start with local testing
   - Use ngrok for callback URL testing
   - Write unit tests for each component

4. **Getting Help**
   - Check with Alice (senior backend) if you get stuck
   - Useful debugging tips: check network tab, log all responses

Remember: Take your time, test thoroughly, and ask questions!"""
        )
        
        junior_instructions = await ai_engine.generate_task_instructions(
            senior_task,
            junior_worker
        )
        
        # Verify junior instructions are more detailed
        assert len(junior_instructions) > len(senior_instructions)
        assert "step-by-step" in junior_instructions.lower()
        assert "pip install" in junior_instructions  # Includes basic setup
        assert "Getting Help" in junior_instructions  # Guidance on asking for help
    
    @pytest.mark.asyncio
    async def test_analyze_blocker_with_escalation(self, ai_engine):
        """
        TEST 3: Verify AI correctly analyzes blockers and determines escalation needs
        
        What's being tested:
        1. The AI identifies root causes of blockers
        2. It determines when escalation is needed
        3. It provides actionable resolution steps
        
        Step-by-step:
        1. We present a serious production blocker
        2. The AI analyzes it and determines escalation is needed
        3. We verify the response includes proper escalation procedures
        """
        # Simulate a critical production blocker
        task_id = "TASK-100"
        blocker_description = "Production database is showing 90% CPU usage, queries timing out"
        severity = "critical"
        
        # Mock AI response for critical blocker
        mock_analysis = {
            "root_cause": "Database query optimization needed - missing indexes on large tables",
            "impact_assessment": "All users experiencing slow response times, potential data loss",
            "needs_coordination": True,
            "resolution_steps": [
                "1. Immediately add read replica to distribute load",
                "2. Identify slow queries using pg_stat_statements",
                "3. Add missing indexes on user_transactions table",
                "4. Implement query result caching",
                "5. Schedule database maintenance window"
            ],
            "required_resources": ["DBA", "Senior Backend Developer", "DevOps"],
            "estimated_hours": 6,
            "escalation_needed": True,
            "prevention_measures": [
                "Implement query performance monitoring",
                "Add automated index recommendations",
                "Set up capacity planning alerts"
            ]
        }
        
        ai_engine._call_claude = AsyncMock(return_value=json.dumps(mock_analysis))
        
        # Call the blocker analysis
        result = await ai_engine.analyze_blocker(task_id, blocker_description, severity)
        
        # Verify critical elements of the response
        assert result["escalation_needed"] is True
        assert result["needs_coordination"] is True
        assert "DBA" in result["required_resources"]
        assert result["estimated_hours"] >= 4  # Significant time needed
        assert len(result["resolution_steps"]) >= 3  # Multiple steps required
        assert "prevention_measures" in result  # Includes future prevention
    
    @pytest.mark.asyncio 
    async def test_project_health_analysis(self, ai_engine):
        """
        TEST 4: Verify AI correctly assesses overall project health
        
        What's being tested:
        1. The AI synthesizes multiple data points into health assessment
        2. It identifies risks and provides recommendations
        3. It predicts timeline impacts
        
        Step-by-step:
        1. We provide project data showing warning signs
        2. The AI analyzes trends and team capacity
        3. We verify it identifies the issues and suggests fixes
        """
        # Create project state with some concerning metrics
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="E-commerce Platform",
            total_tasks=100,
            completed_tasks=25,
            in_progress_tasks=30,  # Too many tasks in progress
            blocked_tasks=8,       # High number of blockers
            progress_percent=25.0,
            overdue_tasks=[],      # Will be populated
            team_velocity=3.0,     # Low velocity
            risk_level=RiskLevel.HIGH,
            last_updated=datetime.now()
        )
        
        # Recent activities showing problems
        recent_activities = [
            {"type": "task_blocked", "count": 5, "timeframe": "last_week"},
            {"type": "task_completed", "count": 3, "timeframe": "last_week"},
            {"type": "deadline_missed", "count": 2, "timeframe": "last_week"}
        ]
        
        # Team showing capacity issues
        team_status = [
            WorkerStatus(
                worker_id="dev-001",
                name="Alice",
                role="Senior Dev",
                email="alice@example.com",
                current_tasks=[Mock(), Mock(), Mock(), Mock()],  # Overloaded
                completed_tasks_count=20,
                capacity=40,
                skills=["python"],
                availability={},
                performance_score=0.7  # Performance dropping
            )
        ]
        
        # Mock AI health analysis response
        mock_analysis = {
            "overall_health": "red",
            "progress_assessment": "Project is at high risk of missing deadline",
            "risk_factors": [
                {
                    "type": "resource",
                    "severity": "high",
                    "description": "Team is overloaded - 30 tasks in progress with only 5 developers"
                },
                {
                    "type": "technical",
                    "severity": "medium", 
                    "description": "High blocker rate indicates architectural issues"
                },
                {
                    "type": "timeline",
                    "severity": "high",
                    "description": "Current velocity of 3 tasks/week won't meet deadline"
                }
            ],
            "recommendations": [
                {
                    "action": "Immediately limit work in progress to 2 tasks per developer",
                    "priority": "high",
                    "owner": "Project Manager"
                },
                {
                    "action": "Conduct blocker retrospective to identify patterns",
                    "priority": "high",
                    "owner": "Tech Lead"
                },
                {
                    "action": "Consider bringing in additional resources or extending timeline",
                    "priority": "medium",
                    "owner": "Stakeholders"
                }
            ],
            "timeline_prediction": {
                "on_track": False,
                "estimated_completion": "2024-06-15",  # 3 months late
                "confidence": 0.3
            },
            "resource_optimization": [
                {
                    "suggestion": "Redistribute tasks from overloaded developers",
                    "impact": "Could improve velocity by 40%"
                }
            ]
        }
        
        ai_engine._call_claude = AsyncMock(return_value=json.dumps(mock_analysis))
        
        # Run the analysis
        result = await ai_engine.analyze_project_health(
            project_state,
            recent_activities,
            team_status
        )
        
        # Verify the AI identified all major issues
        assert result["overall_health"] == "red"
        assert result["timeline_prediction"]["on_track"] is False
        assert len(result["risk_factors"]) >= 3
        assert any(risk["type"] == "resource" for risk in result["risk_factors"])
        assert len(result["recommendations"]) >= 2
        assert result["timeline_prediction"]["confidence"] < 0.5  # Low confidence
    
    @pytest.mark.asyncio
    async def test_fallback_behavior_on_api_error(self, ai_engine, sample_tasks, sample_workers):
        """
        TEST 5: Verify system degrades gracefully when AI is unavailable
        
        What's being tested:
        1. The system doesn't crash when Claude API fails
        2. It falls back to reasonable defaults
        3. Basic functionality continues working
        
        Step-by-step:
        1. We simulate an API error
        2. The system falls back to simple priority-based assignment
        3. We verify the fallback produces valid results
        """
        # Simulate API failure
        ai_engine._call_claude = AsyncMock(side_effect=Exception("API rate limit exceeded"))
        
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=10,
            completed_tasks=5,
            in_progress_tasks=3,
            blocked_tasks=0,
            progress_percent=50.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        # Should fall back to highest priority task
        result = await ai_engine.match_task_to_agent(
            sample_tasks,
            sample_workers["backend_senior"],
            project_state
        )
        
        # Verify fallback behavior
        assert result is not None
        assert result.priority == Priority.URGENT  # Picked highest priority
        
        # Test blocker analysis fallback
        blocker_result = await ai_engine.analyze_blocker(
            "TASK-999",
            "Cannot connect to external API",
            "high"
        )
        
        # Verify fallback provides basic structure
        assert "resolution_steps" in blocker_result
        assert "escalation_needed" in blocker_result
        assert blocker_result["escalation_needed"] is True  # Conservative approach
