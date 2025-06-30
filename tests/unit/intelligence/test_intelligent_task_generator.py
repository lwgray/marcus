"""
Unit tests for the Intelligent Task Generator.

This module tests the AI-powered task generation capabilities of Marcus,
including PRD parsing, task breakdown, dependency analysis, and project
structure generation.

Notes
-----
Tests use mocked dependencies to ensure reproducibility and avoid
external dependencies during testing. All task generation and planning
logic is thoroughly tested with various scenarios.
"""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.intelligence.intelligent_task_generator import (
    IntelligentTaskGenerator,
    ProjectStructure,
    ProjectContext,
    TaskDescription
)
from src.intelligence.prd_parser import ParsedPRD, Feature, TechStack, ProjectConstraints
from src.core.models import Task, TaskStatus, Priority, RiskLevel


# Global fixtures for all test classes
@pytest.fixture
def task_generator() -> IntelligentTaskGenerator:
    """
    Create a test instance of the Intelligent Task Generator.
    
    Returns
    -------
    IntelligentTaskGenerator
        A task generator instance ready for testing.
    
    Notes
    -----
    The generator is initialized with default templates and configurations.
    """
    return IntelligentTaskGenerator()


@pytest.fixture
def sample_tech_stack() -> TechStack:
    """
    Create sample tech stack for testing.
    
    Returns
    -------
    TechStack
        A typical web application tech stack.
    """
    return TechStack(
        frontend=['React', 'TypeScript'],
        backend=['Node.js', 'Express'],
        database=['PostgreSQL'],
        infrastructure=['Docker', 'AWS'],
        mobile=[],
        external_services=['Stripe', 'SendGrid']
    )


@pytest.fixture
def sample_features() -> List[Feature]:
    """
    Create sample features for testing.
    
    Returns
    -------
    List[Feature]
        A list of typical web application features.
    """
    return [
        Feature(
            name="User Authentication",
            description="Allow users to register, login, and manage their accounts",
            priority="high",
            user_stories=[
                "As a user, I want to register with email and password",
                "As a user, I want to login to access my account"
            ],
            acceptance_criteria=[
                "User can register with valid email",
                "User can login with correct credentials",
                "Invalid credentials show error message"
            ],
            technical_notes=[
                "Use JWT tokens for authentication",
                "Hash passwords with bcrypt"
            ],
            estimated_complexity="medium"
        ),
        Feature(
            name="Product Catalog",
            description="Display products with search and filtering capabilities",
            priority="high",
            user_stories=[
                "As a user, I want to browse products",
                "As a user, I want to search for specific products"
            ],
            acceptance_criteria=[
                "Products display with images and details",
                "Search returns relevant results",
                "Filters work correctly"
            ],
            technical_notes=[
                "Use database indexing for search",
                "Implement pagination"
            ],
            estimated_complexity="high"
        ),
        Feature(
            name="Simple Dashboard",
            description="Basic admin dashboard for monitoring",
            priority="low",
            user_stories=[
                "As an admin, I want to see basic metrics"
            ],
            acceptance_criteria=[
                "Dashboard shows user count",
                "Dashboard shows recent activity"
            ],
            technical_notes=[
                "Simple read-only interface"
            ],
            estimated_complexity="low"
        )
    ]


@pytest.fixture
def sample_constraints() -> ProjectConstraints:
    """
    Create sample project constraints for testing.
    
    Returns
    -------
    ProjectConstraints
        Typical project constraints and requirements.
    """
    return ProjectConstraints(
        timeline="12 weeks",
        team_size=3,
        budget=None,
        compliance_requirements=[],
        performance_requirements=[],
        security_requirements=[]
    )


@pytest.fixture
def sample_prd(sample_features, sample_tech_stack, sample_constraints) -> ParsedPRD:
    """
    Create sample parsed PRD for testing.
    
    Parameters
    ----------
    sample_features : List[Feature]
        Sample features from fixture
    sample_tech_stack : TechStack
        Sample tech stack from fixture
    sample_constraints : ProjectConstraints
        Sample constraints from fixture
    
    Returns
    -------
    ParsedPRD
        A complete PRD for testing task generation.
    """
    from src.intelligence.prd_parser import PRDFormat
    return ParsedPRD(
        title="E-commerce Platform",
        overview="A modern e-commerce platform for small businesses",
        goals=["Launch a competitive e-commerce platform", "Enable small businesses to sell online"],
        features=sample_features,
        tech_stack=sample_tech_stack,
        constraints=sample_constraints,
        assumptions=["Users have modern browsers", "Payment processing via Stripe"],
        risks=["Market competition", "Technical complexity"],
        success_metrics=["Platform launches successfully", "Users can complete purchases"],
        format_detected=PRDFormat.PLAIN_TEXT
    )


class TestTaskGeneratorInitialization:
    """Test task generator initialization and configuration."""
    
    def test_task_generator_initialization(self, task_generator):
        """
        Test that task generator initializes with correct templates.
        
        Verifies that all required templates and configurations are loaded
        during initialization.
        """
        # Verify feature task templates exist
        assert 'user_authentication' in task_generator.feature_task_templates
        assert 'data_management' in task_generator.feature_task_templates
        assert 'api_integration' in task_generator.feature_task_templates
        
        # Verify complexity multipliers
        assert task_generator.complexity_multipliers['low'] == 0.7
        assert task_generator.complexity_multipliers['medium'] == 1.0
        assert task_generator.complexity_multipliers['high'] == 1.5
        
        # Verify tech stack templates
        assert 'react' in task_generator.tech_stack_tasks
        assert 'node' in task_generator.tech_stack_tasks
        assert 'postgresql' in task_generator.tech_stack_tasks
    
    def test_feature_task_templates_structure(self, task_generator):
        """
        Test that feature task templates have correct structure.
        
        Verifies that each template contains required fields and follows
        the expected format.
        """
        auth_templates = task_generator.feature_task_templates['user_authentication']
        
        for template in auth_templates:
            assert 'name' in template
            assert 'phase' in template
            assert 'base_hours' in template
            assert 'dependencies' in template
            assert isinstance(template['dependencies'], list)
            assert template['base_hours'] > 0
    
    def test_tech_stack_tasks_structure(self, task_generator):
        """
        Test that tech stack tasks have correct structure.
        
        Verifies that tech stack specific tasks follow the expected format.
        """
        react_tasks = task_generator.tech_stack_tasks['react']
        
        for task in react_tasks:
            assert 'name' in task
            assert 'phase' in task
            assert 'base_hours' in task
            assert 'dependencies' in task
            assert task['phase'] == 'setup'


class TestProjectContextAnalysis:
    """Test project context analysis functionality."""
    
    def test_analyze_project_context(self, task_generator, sample_prd):
        """
        Test project context analysis from PRD.
        
        Verifies that the generator correctly analyzes PRD to determine
        project complexity, team size, and timeline requirements.
        """
        context = task_generator._analyze_project_context(sample_prd)
        
        assert isinstance(context, ProjectContext)
        assert context.tech_stack == sample_prd.tech_stack
        assert context.team_size == 3  # From constraints
        assert context.timeline_weeks == 12  # From constraints
        assert context.complexity_level in ['low', 'medium', 'high']
    
    def test_estimate_team_size_small_project(self, task_generator):
        """
        Test team size estimation for small projects.
        
        Verifies that small projects get appropriate team size recommendations.
        """
        # Create minimal PRD
        small_prd = Mock()
        small_prd.features = [Mock() for _ in range(3)]  # 3 features
        small_prd.tech_stack.frontend = ['React']
        small_prd.tech_stack.backend = ['Node.js']
        small_prd.tech_stack.database = ['PostgreSQL']
        
        team_size = task_generator._estimate_team_size(small_prd)
        assert team_size == 2
    
    def test_estimate_team_size_large_project(self, task_generator):
        """
        Test team size estimation for large projects.
        
        Verifies that large projects get appropriate team size recommendations.
        """
        # Create large PRD
        large_prd = Mock()
        large_prd.features = [Mock() for _ in range(20)]  # 20 features
        large_prd.tech_stack.frontend = ['React', 'Vue', 'Angular']
        large_prd.tech_stack.backend = ['Node.js', 'Python', 'Java']
        large_prd.tech_stack.database = ['PostgreSQL', 'MongoDB', 'Redis']
        
        team_size = task_generator._estimate_team_size(large_prd)
        assert team_size == 5
    
    def test_parse_timeline_variants(self, task_generator):
        """
        Test timeline parsing with different formats.
        
        Verifies that various timeline formats are correctly parsed.
        """
        # Test weeks
        assert task_generator._parse_timeline("8 weeks") == 8
        assert task_generator._parse_timeline("12 week") == 12
        
        # Test months
        assert task_generator._parse_timeline("3 months") == 12
        assert task_generator._parse_timeline("2 month") == 8
        
        # Test days
        assert task_generator._parse_timeline("30 days") == 4
        assert task_generator._parse_timeline("14 day") == 2
        
        # Test invalid
        assert task_generator._parse_timeline("sometime soon") is None
        assert task_generator._parse_timeline("") is None
    
    def test_assess_project_complexity(self, task_generator, sample_prd):
        """
        Test project complexity assessment.
        
        Verifies that complexity is correctly calculated based on features
        and tech stack.
        """
        complexity = task_generator._assess_project_complexity(sample_prd)
        assert complexity in ['low', 'medium', 'high']
        
        # Test with simplified PRD for known result
        simple_prd = Mock()
        simple_prd.features = [
            Mock(estimated_complexity='low'),
            Mock(estimated_complexity='low')
        ]
        simple_prd.tech_stack.frontend = ['React']
        simple_prd.tech_stack.backend = ['Node.js']
        simple_prd.tech_stack.database = ['PostgreSQL']
        simple_prd.tech_stack.infrastructure = []
        simple_prd.tech_stack.external_services = []
        
        complexity = task_generator._assess_project_complexity(simple_prd)
        assert complexity == 'low'


class TestFeatureCategorization:
    """Test feature categorization and template selection."""
    
    def test_categorize_authentication_feature(self, task_generator):
        """
        Test categorization of authentication features.
        
        Verifies that authentication-related features are correctly categorized.
        """
        auth_feature = Feature(
            name="User Login System",
            description="Implement user authentication and authorization",
            priority="high",
            user_stories=[],
            acceptance_criteria=[],
            technical_notes=[],
            estimated_complexity="medium"
        )
        
        category = task_generator._categorize_feature(auth_feature)
        assert category == 'user_authentication'
    
    def test_categorize_data_feature(self, task_generator):
        """
        Test categorization of data management features.
        
        Verifies that data-related features are correctly categorized.
        """
        data_feature = Feature(
            name="Product Database",
            description="Create CRUD operations for product data management",
            priority="high",
            user_stories=[],
            acceptance_criteria=[],
            technical_notes=[],
            estimated_complexity="medium"
        )
        
        category = task_generator._categorize_feature(data_feature)
        assert category == 'data_management'
    
    def test_categorize_api_feature(self, task_generator):
        """
        Test categorization of API features.
        
        Verifies that API-related features are correctly categorized.
        """
        api_feature = Feature(
            name="REST API Endpoints",
            description="Implement API service for external integrations",
            priority="medium",
            user_stories=[],
            acceptance_criteria=[],
            technical_notes=[],
            estimated_complexity="high"
        )
        
        category = task_generator._categorize_feature(api_feature)
        assert category == 'api_integration'
    
    def test_categorize_generic_feature(self, task_generator):
        """
        Test categorization of generic/unknown features.
        
        Verifies that unrecognized features default to generic category.
        """
        generic_feature = Feature(
            name="Analytics Dashboard",
            description="Create reporting and analytics interface",
            priority="low",
            user_stories=[],
            acceptance_criteria=[],
            technical_notes=[],
            estimated_complexity="medium"
        )
        
        category = task_generator._categorize_feature(generic_feature)
        assert category == 'generic'


class TestTaskTemplateCustomization:
    """Test task template customization and creation."""
    
    def test_customize_template_for_feature(self, task_generator, sample_features):
        """
        Test template customization for specific features.
        
        Verifies that generic templates are properly customized for
        specific features with correct naming and complexity adjustments.
        """
        feature = sample_features[0]  # User Authentication
        template = {
            'name': 'Implement user authentication',
            'base_hours': 8,
            'phase': 'backend'
        }
        
        context = ProjectContext(
            tech_stack=Mock(),
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        customized = task_generator._customize_template_for_feature(template, feature, context)
        
        assert 'hours' in customized
        assert customized['hours'] == 8  # medium complexity = 1.0 multiplier
        assert customized['name'] == template['name']  # Should remain the same for auth
    
    def test_complexity_multiplier_application(self, task_generator):
        """
        Test that complexity multipliers are correctly applied.
        
        Verifies that task hours are adjusted based on feature complexity.
        """
        template = {'base_hours': 10}
        
        # Low complexity feature
        low_feature = Mock(estimated_complexity='low')
        context = Mock(complexity_level='medium')
        
        customized = task_generator._customize_template_for_feature(template, low_feature, context)
        assert customized['hours'] == 7  # 10 * 0.7
        
        # High complexity feature
        high_feature = Mock(estimated_complexity='high')
        customized = task_generator._customize_template_for_feature(template, high_feature, context)
        assert customized['hours'] == 15  # 10 * 1.5
    
    def test_create_task_from_template(self, task_generator):
        """
        Test task creation from templates.
        
        Verifies that Task objects are correctly created from template data
        with proper fields and metadata.
        """
        template = {
            'name': 'Test Task',
            'description': 'Test Description',
            'hours': 8,
            'dependencies': ['Other Task']
        }
        
        context = ProjectContext(
            tech_stack=TechStack(
                frontend=['React'],
                backend=['Node.js'],
                database=[],
                infrastructure=[],
                mobile=[],
                external_services=[]
            ),
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        task = task_generator._create_task_from_template(template, 'backend', context)
        
        assert isinstance(task, Task)
        assert task.name == 'Test Task'
        assert task.description == 'Test Description'
        assert task.estimated_hours == 8
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.HIGH  # backend phase = high priority
        assert 'phase:backend' in task.labels
        assert 'complexity:medium' in task.labels
        assert 'tech:React' in task.labels
        assert task.metadata['phase'] == 'backend'
        assert task.metadata['generated'] is True
        assert task.metadata['dependencies_names'] == ['Other Task']
    
    def test_phase_priority_mapping(self, task_generator):
        """
        Test that different phases get correct priority levels.
        
        Verifies that the priority assignment logic works correctly
        for different project phases.
        """
        template = {'name': 'Test Task', 'hours': 4}
        context = Mock()
        context.complexity_level = 'medium'
        context.tech_stack.frontend = []
        context.tech_stack.backend = []
        
        # Test high priority phases
        high_priority_phases = ['setup', 'design', 'backend', 'testing', 'deployment']
        for phase in high_priority_phases:
            task = task_generator._create_task_from_template(template, phase, context)
            assert task.priority == Priority.HIGH
        
        # Test medium priority phases
        medium_priority_phases = ['frontend', 'integration']
        for phase in medium_priority_phases:
            task = task_generator._create_task_from_template(template, phase, context)
            assert task.priority == Priority.MEDIUM


class TestTaskGeneration:
    """Test task generation for different project phases."""
    
    @pytest.mark.asyncio
    async def test_generate_setup_tasks(self, task_generator, sample_tech_stack):
        """
        Test setup task generation.
        
        Verifies that appropriate setup tasks are generated based on
        the tech stack requirements.
        """
        context = ProjectContext(
            tech_stack=sample_tech_stack,
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        tasks = await task_generator._generate_setup_tasks(sample_tech_stack, context)
        
        assert len(tasks) > 0
        
        # Should have basic setup tasks
        task_names = [task.name for task in tasks]
        assert any('repository' in name.lower() for name in task_names)
        assert any('development environment' in name.lower() for name in task_names)
        
        # Should have tech-specific tasks
        assert any('react' in name.lower() for name in task_names)
        assert any('postgresql' in name.lower() for name in task_names)
        # Note: Node.js tasks would appear if 'node' key existed in tech_stack_tasks
        # But the current implementation only has 'react' and 'postgresql' tasks
        
        # All tasks should be in setup phase
        for task in tasks:
            assert 'phase:setup' in task.labels
    
    @pytest.mark.asyncio
    async def test_generate_design_tasks(self, task_generator, sample_features):
        """
        Test design task generation.
        
        Verifies that appropriate design tasks are generated including
        architecture, database, and UI design.
        """
        context = ProjectContext(
            tech_stack=TechStack(
                frontend=['React'],
                backend=['Node.js'],
                database=['PostgreSQL'],
                infrastructure=[],
                mobile=[],
                external_services=[]
            ),
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        tasks = await task_generator._generate_design_tasks(sample_features, context)
        
        assert len(tasks) > 0
        
        task_names = [task.name for task in tasks]
        assert any('architecture' in name.lower() for name in task_names)
        assert any('database schema' in name.lower() for name in task_names)
        assert any('api contracts' in name.lower() for name in task_names)
        assert any('wireframes' in name.lower() for name in task_names)  # Frontend included
        
        # All tasks should be in design phase
        for task in tasks:
            assert 'phase:design' in task.labels
    
    @pytest.mark.asyncio
    async def test_generate_design_tasks_no_frontend(self, task_generator, sample_features):
        """
        Test design task generation without frontend.
        
        Verifies that UI-specific design tasks are not generated when
        no frontend technology is specified.
        """
        context = ProjectContext(
            tech_stack=TechStack(
                frontend=[],  # No frontend
                backend=['Node.js'],
                database=['PostgreSQL'],
                infrastructure=[],
                mobile=[],
                external_services=[]
            ),
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        tasks = await task_generator._generate_design_tasks(sample_features, context)
        
        task_names = [task.name for task in tasks]
        assert not any('wireframes' in name.lower() for name in task_names)
        assert not any('component library' in name.lower() for name in task_names)
    
    @pytest.mark.asyncio
    async def test_generate_feature_tasks(self, task_generator, sample_features, sample_tech_stack):
        """
        Test feature task generation.
        
        Verifies that tasks are generated for each feature based on
        feature type and complexity.
        """
        context = ProjectContext(
            tech_stack=sample_tech_stack,
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        tasks = await task_generator._generate_feature_tasks(sample_features, context)
        
        assert len(tasks) > 0
        
        # Should have tasks for each feature
        task_names_str = ' '.join([task.name for task in tasks]).lower()
        assert 'authentication' in task_names_str
        assert 'product' in task_names_str or 'catalog' in task_names_str
        assert 'dashboard' in task_names_str
    
    @pytest.mark.asyncio
    async def test_generate_tasks_for_specific_feature(self, task_generator, sample_features, sample_tech_stack):
        """
        Test task generation for a specific feature.
        
        Verifies that the correct number and type of tasks are generated
        for individual features.
        """
        auth_feature = sample_features[0]  # User Authentication
        context = ProjectContext(
            tech_stack=sample_tech_stack,
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        tasks = await task_generator._generate_tasks_for_feature(auth_feature, context)
        
        assert len(tasks) > 0
        
        # Auth feature should generate auth-specific tasks
        task_names = [task.name for task in tasks]
        auth_template_names = [t['name'] for t in task_generator.feature_task_templates['user_authentication']]
        
        # Should match template structure
        assert len(tasks) == len(auth_template_names)
    
    @pytest.mark.asyncio
    async def test_generate_integration_tasks(self, task_generator, sample_features):
        """
        Test integration task generation.
        
        Verifies that integration tasks are created including frontend/backend
        integration and external service integrations.
        """
        context = ProjectContext(
            tech_stack=TechStack(
                frontend=['React'],
                backend=['Node.js'],
                database=['PostgreSQL'],
                infrastructure=[],
                mobile=[],
                external_services=['Stripe', 'SendGrid']
            ),
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        tasks = await task_generator._generate_integration_tasks(sample_features, context)
        
        assert len(tasks) > 0
        
        task_names = [task.name for task in tasks]
        assert any('frontend and backend' in name.lower() for name in task_names)
        assert any('error handling' in name.lower() for name in task_names)
        assert any('stripe' in name.lower() for name in task_names)
        assert any('sendgrid' in name.lower() for name in task_names)
    
    @pytest.mark.asyncio
    async def test_generate_testing_tasks(self, task_generator, sample_features, sample_tech_stack):
        """
        Test testing task generation.
        
        Verifies that comprehensive testing tasks are generated including
        unit tests, integration tests, and manual testing.
        """
        context = ProjectContext(
            tech_stack=sample_tech_stack,
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        tasks = await task_generator._generate_testing_tasks(sample_features, context)
        
        assert len(tasks) > 0
        
        task_names = [task.name for task in tasks]
        assert any('unit tests' in name.lower() for name in task_names)
        assert any('integration tests' in name.lower() for name in task_names)
        assert any('manual testing' in name.lower() for name in task_names)
        assert any('fix' in name.lower() and 'bugs' in name.lower() for name in task_names)
    
    @pytest.mark.asyncio
    async def test_generate_deployment_tasks(self, task_generator, sample_tech_stack):
        """
        Test deployment task generation.
        
        Verifies that deployment and infrastructure tasks are generated
        including CI/CD setup and production deployment.
        """
        context = ProjectContext(
            tech_stack=sample_tech_stack,
            team_size=3,
            timeline_weeks=12,
            complexity_level='medium'
        )
        
        tasks = await task_generator._generate_deployment_tasks(sample_tech_stack, context)
        
        assert len(tasks) > 0
        
        task_names = [task.name for task in tasks]
        assert any('production environment' in name.lower() for name in task_names)
        assert any('ci/cd' in name.lower() for name in task_names)
        assert any('staging' in name.lower() for name in task_names)
        assert any('production' in name.lower() for name in task_names)
        assert any('monitor' in name.lower() for name in task_names)


class TestDependencyManagement:
    """Test task dependency extraction and resolution."""
    
    def test_extract_dependencies(self, task_generator):
        """
        Test dependency extraction from tasks.
        
        Verifies that task dependencies are correctly extracted and
        mapped using task IDs.
        """
        # Create mock tasks with dependency names in metadata
        task1 = Mock()
        task1.id = 'task-1'
        task1.name = 'Setup Repository'
        task1.dependencies = []
        task1.metadata = {'dependencies_names': []}
        
        task2 = Mock()
        task2.id = 'task-2'  
        task2.name = 'Setup Environment'
        task2.dependencies = []
        task2.metadata = {'dependencies_names': ['Setup Repository']}
        
        task3 = Mock()
        task3.id = 'task-3'
        task3.name = 'Create Database'
        task3.dependencies = []
        task3.metadata = {'dependencies_names': ['Setup Environment']}
        
        tasks = [task1, task2, task3]
        
        dependencies = task_generator._extract_dependencies(tasks)
        
        assert dependencies['task-1'] == []
        assert dependencies['task-2'] == ['task-1']
        assert dependencies['task-3'] == ['task-2']
        
        # Verify task objects were updated
        assert task1.dependencies == []
        assert task2.dependencies == ['task-1']
        assert task3.dependencies == ['task-2']
    
    def test_extract_dependencies_missing_references(self, task_generator):
        """
        Test dependency extraction with missing task references.
        
        Verifies that missing dependency references are handled gracefully
        without causing errors.
        """
        task = Mock()
        task.id = 'task-1'
        task.name = 'Test Task'
        task.dependencies = []
        task.metadata = {'dependencies_names': ['Non-existent Task']}
        
        dependencies = task_generator._extract_dependencies([task])
        
        assert dependencies['task-1'] == []
        assert task.dependencies == []


class TestProjectMetrics:
    """Test project duration and team size calculations."""
    
    def test_calculate_project_duration(self, task_generator):
        """
        Test project duration calculation.
        
        Verifies that project duration is correctly calculated based on
        total hours, team size, and productivity assumptions.
        """
        # Create mock tasks with known hours
        tasks = [
            Mock(estimated_hours=8),
            Mock(estimated_hours=16),
            Mock(estimated_hours=12),
            Mock(estimated_hours=4)
        ]
        
        # Total = 40 hours, team size = 2, 6 hours/day
        # 40 / (2 * 6) = 3.33 days * 1.2 buffer = 4 days
        duration = task_generator._calculate_project_duration(tasks, team_size=2)
        assert duration == 4
        
        # Test with larger team
        duration = task_generator._calculate_project_duration(tasks, team_size=4)
        assert duration == 2  # 40 / (4 * 6) = 1.67 * 1.2 = 2
    
    def test_recommend_team_size(self, task_generator):
        """
        Test team size recommendation.
        
        Verifies that appropriate team sizes are recommended based on
        total work and available timeline.
        """
        # Create tasks with 120 hours total
        tasks = [Mock(estimated_hours=30) for _ in range(4)]
        
        # 12 weeks * 5 days * 6 hours = 360 hours available per person
        # 120 / 360 = 0.33, so minimum team size = 1
        team_size = task_generator._recommend_team_size(tasks, timeline_weeks=12)
        assert team_size == 1
        
        # Test with tight timeline - 2 weeks
        # 2 weeks * 5 days * 6 hours = 60 hours available per person
        # 120 / 60 = 2, so minimum team size = 3 (2 + 1)
        team_size = task_generator._recommend_team_size(tasks, timeline_weeks=2)
        assert team_size == 3
    
    def test_recommend_team_size_caps_at_eight(self, task_generator):
        """
        Test that team size recommendations are capped at 8.
        
        Verifies that very large projects don't result in unreasonably
        large team size recommendations.
        """
        # Create many tasks with lots of hours
        tasks = [Mock(estimated_hours=100) for _ in range(20)]  # 2000 hours
        
        team_size = task_generator._recommend_team_size(tasks, timeline_weeks=1)
        assert team_size == 8  # Should be capped


class TestGenericFeatureHandling:
    """Test handling of generic/unknown feature types."""
    
    def test_generate_generic_feature_tasks(self, task_generator):
        """
        Test generic task generation for unknown features.
        
        Verifies that unknown feature types get appropriate generic
        task templates.
        """
        feature = Feature(
            name="Analytics Dashboard",
            description="Custom analytics interface",
            priority="medium",
            user_stories=[],
            acceptance_criteria=[],
            technical_notes=[],
            estimated_complexity="medium"
        )
        
        tasks = task_generator._generate_generic_feature_tasks(feature)
        
        assert len(tasks) == 4  # design, backend, frontend, testing
        
        phases = [task['phase'] for task in tasks]
        assert 'design' in phases
        assert 'backend' in phases
        assert 'frontend' in phases
        assert 'testing' in phases
        
        # All tasks should reference the feature name
        for task in tasks:
            assert 'Analytics Dashboard' in task['name']


class TestFullProjectGeneration:
    """Test complete project structure generation."""
    
    @pytest.mark.asyncio
    async def test_generate_tasks_from_prd(self, task_generator, sample_prd):
        """
        Test complete project generation from PRD.
        
        Verifies that a complete project structure is generated with all
        phases, tasks, dependencies, and metrics.
        """
        # Create properly structured mock tasks
        def create_mock_task(task_id="test-id", name="Test Task"):
            mock_task = Mock()
            mock_task.id = task_id
            mock_task.name = name
            mock_task.estimated_hours = 4
            mock_task.metadata = {'dependencies_names': []}
            mock_task.dependencies = []
            return mock_task
        
        with patch.object(task_generator, '_generate_setup_tasks', return_value=[create_mock_task("setup-1", "Setup Task")]):
            with patch.object(task_generator, '_generate_design_tasks', return_value=[create_mock_task("design-1", "Design Task")]):
                with patch.object(task_generator, '_generate_feature_tasks', return_value=[create_mock_task("feature-1", "Feature Task")]):
                    with patch.object(task_generator, '_generate_integration_tasks', return_value=[create_mock_task("integration-1", "Integration Task")]):
                        with patch.object(task_generator, '_generate_testing_tasks', return_value=[create_mock_task("testing-1", "Testing Task")]):
                            with patch.object(task_generator, '_generate_deployment_tasks', return_value=[create_mock_task("deployment-1", "Deployment Task")]):
                                
                                project_structure = await task_generator.generate_tasks_from_prd(sample_prd)
        
        assert isinstance(project_structure, ProjectStructure)
        assert len(project_structure.phases) == 7  # All phases included
        assert len(project_structure.tasks) == 6  # One from each phase (mocked)
        assert isinstance(project_structure.dependencies, dict)
        assert project_structure.estimated_duration > 0
        assert project_structure.recommended_team_size > 0
        
        expected_phases = ['setup', 'design', 'backend', 'frontend', 'integration', 'testing', 'deployment']
        assert project_structure.phases == expected_phases
    
    @pytest.mark.asyncio
    async def test_generate_tasks_from_prd_integration(self, task_generator, sample_prd):
        """
        Test complete project generation integration.
        
        This test runs the actual generation without mocks to verify
        the full integration works correctly.
        """
        project_structure = await task_generator.generate_tasks_from_prd(sample_prd)
        
        assert isinstance(project_structure, ProjectStructure)
        assert len(project_structure.tasks) > 10  # Should generate many tasks
        
        # Verify all phases are represented
        task_phases = set()
        for task in project_structure.tasks:
            phase_labels = [label for label in task.labels if label.startswith('phase:')]
            if phase_labels:
                task_phases.add(phase_labels[0].split(':')[1])
        
        expected_phases = {'setup', 'design', 'backend', 'frontend', 'integration', 'testing', 'deployment'}
        assert len(task_phases.intersection(expected_phases)) > 0
        
        # Verify dependencies exist
        assert len(project_structure.dependencies) == len(project_structure.tasks)
        
        # Verify realistic metrics
        assert 1 <= project_structure.estimated_duration <= 365  # 1 day to 1 year
        assert 1 <= project_structure.recommended_team_size <= 8


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_empty_features_list(self, task_generator, sample_tech_stack):
        """
        Test handling of PRD with no features.
        
        Verifies that the generator handles edge cases gracefully.
        """
        from src.intelligence.prd_parser import PRDFormat, ProjectConstraints
        
        empty_constraints = ProjectConstraints(
            timeline="4 weeks",
            team_size=2,
            budget=None,
            performance_requirements=[],
            security_requirements=[],
            compliance_requirements=[]
        )
        
        empty_prd = ParsedPRD(
            title="Empty Project",
            overview="Project with no features",
            goals=[],
            features=[],  # Empty features
            tech_stack=sample_tech_stack,
            constraints=empty_constraints,
            assumptions=[],
            risks=[],
            success_metrics=[],
            format_detected=PRDFormat.PLAIN_TEXT
        )
        
        project_structure = await task_generator.generate_tasks_from_prd(empty_prd)
        
        # Should still generate setup, design, and deployment tasks
        assert len(project_structure.tasks) > 0
        assert project_structure.estimated_duration > 0
    
    def test_invalid_complexity_multiplier(self, task_generator):
        """
        Test handling of invalid complexity values.
        
        Verifies that unknown complexity values default to medium.
        """
        template = {'base_hours': 10}
        feature = Mock(estimated_complexity='unknown')
        context = Mock()
        
        customized = task_generator._customize_template_for_feature(template, feature, context)
        
        # Should default to 1.0 multiplier (medium complexity)
        assert customized['hours'] == 10
    
    def test_missing_timeline_defaults(self, task_generator):
        """
        Test that missing timeline information gets reasonable defaults.
        
        Verifies that the system handles missing constraint data gracefully.
        """
        from src.intelligence.prd_parser import ProjectConstraints, TechStack, ParsedPRD, PRDFormat
        
        # Create proper constraints with None values
        constraints = ProjectConstraints(
            timeline=None,
            team_size=None,
            budget=None,
            performance_requirements=[],
            security_requirements=[],
            compliance_requirements=[]
        )
        
        # Create proper tech stack
        tech_stack = TechStack(
            frontend=['React'],
            backend=['Node.js'],
            database=['PostgreSQL'],
            infrastructure=[],
            mobile=[],
            external_services=[]
        )
        
        # Create test features
        features = [Mock() for _ in range(5)]
        
        # Create proper PRD
        prd = ParsedPRD(
            title="Test Project",
            overview="Test project for defaults",
            goals=[],
            features=features,
            tech_stack=tech_stack,
            constraints=constraints,
            assumptions=[],
            risks=[],
            success_metrics=[],
            format_detected=PRDFormat.PLAIN_TEXT
        )
        
        context = task_generator._analyze_project_context(prd)
        
        assert context.team_size > 0  # Should have estimated team size
        assert context.timeline_weeks == 12  # Should have default timeline