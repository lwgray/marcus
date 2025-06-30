"""
Unit tests for BasicCreatorMode.

This module provides comprehensive test coverage for the BasicCreatorMode class,
which handles project creation from templates, customization, and task generation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List

from src.modes.creator.basic_creator import BasicCreatorMode
from src.modes.creator.template_library import (
    ProjectTemplate, WebAppTemplate, APIServiceTemplate, MobileAppTemplate,
    ProjectSize, PhaseTemplate, TaskTemplate
)
from src.core.models import Task, TaskStatus, Priority


class MockTask:
    """
    Mock Task class that includes metadata field for testing.
    
    The actual Task model doesn't have metadata, but the creator code uses it.
    This mock allows us to test the actual behavior.
    """
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'test-id')
        self.name = kwargs.get('name', 'Test Task')
        self.description = kwargs.get('description', 'Test description')
        self.status = kwargs.get('status', TaskStatus.TODO)
        self.priority = kwargs.get('priority', Priority.MEDIUM)
        self.labels = kwargs.get('labels', [])
        self.estimated_hours = kwargs.get('estimated_hours', 1.0)
        self.dependencies = kwargs.get('dependencies', [])
        self.metadata = kwargs.get('metadata', {})
        self.assigned_to = kwargs.get('assigned_to', None)
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.due_date = kwargs.get('due_date', None)
        self.actual_hours = kwargs.get('actual_hours', 0.0)


@pytest.fixture
def mock_task_generator():
    """Create a mock TaskGenerator."""
    generator = Mock()
    generator.generate_from_template = AsyncMock()
    return generator


@pytest.fixture
def mock_templates():
    """Create mock project templates."""
    templates = {
        'web': Mock(spec=WebAppTemplate),
        'api': Mock(spec=APIServiceTemplate),
        'mobile': Mock(spec=MobileAppTemplate)
    }
    
    # Setup template attributes
    for name, template in templates.items():
        template.name = f"{name.capitalize()} App Template"
        template.description = f"Template for {name} applications"
        template.category = name
        template.phases = [
            Mock(
                name="Planning",
                description="Project planning phase",
                tasks=[Mock(name="Task 1", estimated_hours=2)]
            )
        ]
        template.get_all_tasks = Mock(return_value=[
            Mock(name="Task 1", estimated_hours=2),
            Mock(name="Task 2", estimated_hours=3)
        ])
    
    return templates


@pytest.fixture
def basic_creator_mode(mock_templates, mock_task_generator):
    """Create BasicCreatorMode instance with mocked dependencies."""
    with patch('src.modes.creator.basic_creator.WebAppTemplate', return_value=mock_templates['web']), \
         patch('src.modes.creator.basic_creator.APIServiceTemplate', return_value=mock_templates['api']), \
         patch('src.modes.creator.basic_creator.MobileAppTemplate', return_value=mock_templates['mobile']), \
         patch('src.modes.creator.basic_creator.TaskGenerator', return_value=mock_task_generator):
        mode = BasicCreatorMode()
        mode.templates = mock_templates
        mode.task_generator = mock_task_generator
        return mode


class TestBasicCreatorModeInitialization:
    """Test suite for BasicCreatorMode initialization."""
    
    def test_initialization_creates_templates(self):
        """Test that initialization creates all required templates."""
        mode = BasicCreatorMode()
        
        assert 'web' in mode.templates
        assert 'api' in mode.templates
        assert 'mobile' in mode.templates
        assert hasattr(mode, 'task_generator')
        assert mode.state == {'active_project': None, 'generated_tasks': []}
    
    async def test_initialize_with_saved_state(self, basic_creator_mode):
        """Test initialization with saved state."""
        saved_state = {
            'active_project': {'name': 'test-project'},
            'generated_tasks': [{'id': 'task-1'}]
        }
        
        await basic_creator_mode.initialize(saved_state)
        
        assert basic_creator_mode.state['active_project'] == {'name': 'test-project'}
        assert basic_creator_mode.state['generated_tasks'] == [{'id': 'task-1'}]
    
    async def test_initialize_without_saved_state(self, basic_creator_mode):
        """Test initialization without saved state."""
        await basic_creator_mode.initialize(None)
        
        assert basic_creator_mode.state['active_project'] is None
        assert basic_creator_mode.state['generated_tasks'] == []


class TestBasicCreatorModeStateManagement:
    """Test suite for state management methods."""
    
    async def test_get_state_returns_copy(self, basic_creator_mode):
        """Test that get_state returns a copy of the state."""
        basic_creator_mode.state['test_key'] = 'test_value'
        
        state = await basic_creator_mode.get_state()
        state['test_key'] = 'modified'
        
        assert basic_creator_mode.state['test_key'] == 'test_value'
    
    async def test_get_status(self, basic_creator_mode):
        """Test get_status returns current mode information."""
        basic_creator_mode.state['active_project'] = {'name': 'test-project'}
        basic_creator_mode.state['generated_tasks'] = [{'id': '1'}, {'id': '2'}]
        
        status = await basic_creator_mode.get_status()
        
        assert status['mode'] == 'creator'
        assert status['active_project'] == {'name': 'test-project'}
        assert status['generated_tasks_count'] == 2
        assert status['available_templates'] == ['web', 'api', 'mobile']


class TestProjectCreationFromTemplate:
    """Test suite for project creation from templates."""
    
    async def test_create_project_success(self, basic_creator_mode):
        """Test successful project creation from template."""
        # Setup mock tasks
        mock_tasks = [
            MockTask(
                id='task-1',
                name='Setup project',
                phase='Planning',
                estimated_hours=2,
                metadata={'phase': 'Planning', 'phase_order': 1}
            ),
            MockTask(
                id='task-2',
                name='Create database schema',
                phase='Development',
                estimated_hours=4,
                metadata={'phase': 'Development', 'phase_order': 2}
            )
        ]
        basic_creator_mode.task_generator.generate_from_template.return_value = mock_tasks
        
        result = await basic_creator_mode.create_project_from_template(
            template_name='web',
            project_name='My Web App',
            customizations={'size': ProjectSize.MEDIUM}
        )
        
        assert result['success'] is True
        assert result['project_name'] == 'My Web App'
        assert result['template_used'] == 'web'
        assert result['tasks_generated'] == 2
        assert len(result['tasks']) == 2
        assert result['estimated_total_hours'] == 6
        assert 'phases' in result
        
        # Verify state was updated
        assert basic_creator_mode.state['active_project']['name'] == 'My Web App'
        assert len(basic_creator_mode.state['generated_tasks']) == 2
    
    async def test_create_project_invalid_template(self, basic_creator_mode):
        """Test project creation with invalid template name."""
        result = await basic_creator_mode.create_project_from_template(
            template_name='invalid',
            project_name='Test Project'
        )
        
        assert result['success'] is False
        assert 'Template \'invalid\' not found' in result['error']
        assert result['available_templates'] == ['web', 'api', 'mobile']
    
    async def test_create_project_with_exception(self, basic_creator_mode):
        """Test project creation when task generator raises exception."""
        basic_creator_mode.task_generator.generate_from_template.side_effect = Exception("Generator error")
        
        result = await basic_creator_mode.create_project_from_template(
            template_name='web',
            project_name='Test Project'
        )
        
        assert result['success'] is False
        assert result['error'] == "Generator error"
    
    async def test_create_project_without_customizations(self, basic_creator_mode):
        """Test project creation without customizations."""
        mock_tasks = [MockTask(id='task-1', estimated_hours=2)]
        basic_creator_mode.task_generator.generate_from_template.return_value = mock_tasks
        
        result = await basic_creator_mode.create_project_from_template(
            template_name='api',
            project_name='API Service'
        )
        
        # Verify customizations were created with project_name
        call_args = basic_creator_mode.task_generator.generate_from_template.call_args
        assert call_args[1]['customizations']['project_name'] == 'API Service'


class TestProjectCustomization:
    """Test suite for project customization."""
    
    async def test_customize_project_success(self, basic_creator_mode):
        """Test successful project customization."""
        # Setup active project
        basic_creator_mode.state['active_project'] = {
            'name': 'Test Project',
            'template': 'web',
            'customizations': {'size': ProjectSize.MEDIUM}
        }
        
        # Setup new tasks after customization
        mock_tasks = [
            MockTask(id='task-1', name='New task', estimated_hours=3)
        ]
        basic_creator_mode.task_generator.generate_from_template.return_value = mock_tasks
        
        adjustments = {'size': ProjectSize.LARGE, 'excluded_phases': ['Testing']}
        result = await basic_creator_mode.customize_project(adjustments)
        
        assert result['success'] is True
        assert result['message'] == "Project customized successfully"
        assert result['tasks_generated'] == 1
        
        # Verify customizations were merged
        updated_customizations = basic_creator_mode.state['active_project']['customizations']
        assert updated_customizations['size'] == ProjectSize.LARGE
        assert updated_customizations['excluded_phases'] == ['Testing']
    
    async def test_customize_project_no_active_project(self, basic_creator_mode):
        """Test customization when no active project exists."""
        result = await basic_creator_mode.customize_project({'size': ProjectSize.LARGE})
        
        assert result['success'] is False
        assert result['error'] == "No active project to customize"
    
    async def test_customize_project_with_exception(self, basic_creator_mode):
        """Test customization when task generator raises exception."""
        basic_creator_mode.state['active_project'] = {
            'name': 'Test Project',
            'template': 'web',
            'customizations': {}
        }
        basic_creator_mode.task_generator.generate_from_template.side_effect = Exception("Customization error")
        
        result = await basic_creator_mode.customize_project({'size': ProjectSize.LARGE})
        
        assert result['success'] is False
        assert result['error'] == "Customization error"


class TestTemplateOperations:
    """Test suite for template-related operations."""
    
    async def test_get_available_templates(self, basic_creator_mode):
        """Test retrieving available templates with details."""
        # Setup more detailed mock templates
        for name, template in basic_creator_mode.templates.items():
            # Create proper mock phase objects with attributes
            planning_phase = Mock()
            planning_phase.name = "Planning"
            planning_phase.description = "Initial planning"
            planning_phase.tasks = [Mock(), Mock()]  # 2 tasks
            
            dev_phase = Mock()
            dev_phase.name = "Development"
            dev_phase.description = "Core development"
            dev_phase.tasks = [Mock(), Mock(), Mock()]  # 3 tasks
            
            template.phases = [planning_phase, dev_phase]
            template.get_all_tasks.side_effect = lambda size=None: [
                Mock(estimated_hours=2), Mock(estimated_hours=3),
                Mock(estimated_hours=4), Mock(estimated_hours=1),
                Mock(estimated_hours=2)
            ]
        
        result = await basic_creator_mode.get_available_templates()
        
        assert 'templates' in result
        assert 'project_sizes' in result
        
        # Check template info
        for template_key in ['web', 'api', 'mobile']:
            template_info = result['templates'][template_key]
            assert 'name' in template_info
            assert 'description' in template_info
            assert 'phases' in template_info
            assert len(template_info['phases']) == 2
            assert template_info['total_tasks'] == 5
            
            # Check phase info
            phase_info = template_info['phases'][0]
            assert phase_info['name'] == 'Planning'
            assert phase_info['task_count'] == 2
        
        # Check project sizes
        assert result['project_sizes'] == ['mvp', 'small', 'medium', 'large', 'enterprise']
    
    async def test_preview_template_success(self, basic_creator_mode):
        """Test successful template preview."""
        # Setup mock template
        template = basic_creator_mode.templates['web']
        mock_tasks = [
            Mock(
                name='Setup project',
                description='Initialize project structure',
                phase='Planning',
                estimated_hours=2,
                priority=Priority.HIGH,
                optional=False
            ),
            Mock(
                name='Create UI',
                description='Build user interface',
                phase='Development',
                estimated_hours=8,
                priority=Priority.MEDIUM,
                optional=False
            ),
            Mock(
                name='Add analytics',
                description='Integrate analytics',
                phase='Development',
                estimated_hours=3,
                priority=Priority.LOW,
                optional=True
            )
        ]
        template.get_all_tasks.return_value = mock_tasks
        
        result = await basic_creator_mode.preview_template('web', 'medium')
        
        assert result['success'] is True
        assert result['template_name'] == 'Web App Template'
        assert result['size'] == 'medium'
        assert result['total_tasks'] == 3
        assert result['total_estimated_hours'] == 13
        
        # Check phases breakdown
        assert 'Planning' in result['phases']
        assert len(result['phases']['Planning']['tasks']) == 1
        assert result['phases']['Planning']['estimated_hours'] == 2
        
        assert 'Development' in result['phases']
        assert len(result['phases']['Development']['tasks']) == 2
        assert result['phases']['Development']['estimated_hours'] == 11
    
    async def test_preview_template_invalid_template(self, basic_creator_mode):
        """Test preview with invalid template name."""
        result = await basic_creator_mode.preview_template('invalid')
        
        assert result['success'] is False
        assert 'Template \'invalid\' not found' in result['error']
    
    async def test_preview_template_default_size(self, basic_creator_mode):
        """Test preview uses default size when not specified."""
        template = basic_creator_mode.templates['api']
        template.get_all_tasks.return_value = []
        
        result = await basic_creator_mode.preview_template('api')
        
        assert result['size'] == 'medium'  # Default size


class TestCreateFromDescription:
    """Test suite for natural language project creation."""
    
    async def test_create_from_description_mobile_keywords(self, basic_creator_mode):
        """Test description parsing detects mobile project."""
        mock_tasks = [MockTask(id='task-1')]
        basic_creator_mode.task_generator.generate_from_template.return_value = mock_tasks
        
        result = await basic_creator_mode.create_from_description(
            "Build an iOS app for task management",
            "TaskMaster"
        )
        
        # Verify mobile template was selected
        call_args = basic_creator_mode.task_generator.generate_from_template.call_args
        assert call_args.kwargs['template'] == basic_creator_mode.templates['mobile']
        assert result['suggestion_reasoning'].startswith("Based on your description, I suggested a mobile")
    
    async def test_create_from_description_api_keywords(self, basic_creator_mode):
        """Test description parsing detects API project."""
        mock_tasks = [MockTask(id='task-1')]
        basic_creator_mode.task_generator.generate_from_template.return_value = mock_tasks
        
        result = await basic_creator_mode.create_from_description(
            "Create a REST API service for user management",
            "UserAPI"
        )
        
        call_args = basic_creator_mode.task_generator.generate_from_template.call_args
        assert call_args.kwargs['template'] == basic_creator_mode.templates['api']
    
    async def test_create_from_description_web_keywords(self, basic_creator_mode):
        """Test description parsing detects web project."""
        mock_tasks = [MockTask(id='task-1')]
        basic_creator_mode.task_generator.generate_from_template.return_value = mock_tasks
        
        result = await basic_creator_mode.create_from_description(
            "Develop a full-stack website with React",
            "MyWebsite"
        )
        
        call_args = basic_creator_mode.task_generator.generate_from_template.call_args
        assert call_args.kwargs['template'] == basic_creator_mode.templates['web']
    
    async def test_create_from_description_mvp_size(self, basic_creator_mode):
        """Test description parsing detects MVP size."""
        mock_tasks = [MockTask(id='task-1')]
        basic_creator_mode.task_generator.generate_from_template.return_value = mock_tasks
        
        result = await basic_creator_mode.create_from_description(
            "Quick prototype for a mobile app",
            "Prototype"
        )
        
        call_args = basic_creator_mode.task_generator.generate_from_template.call_args
        customizations = call_args[1]['customizations']
        assert customizations['size'] == ProjectSize.MVP
    
    async def test_create_from_description_large_size(self, basic_creator_mode):
        """Test description parsing detects large size."""
        mock_tasks = [MockTask(id='task-1')]
        basic_creator_mode.task_generator.generate_from_template.return_value = mock_tasks
        
        result = await basic_creator_mode.create_from_description(
            "Enterprise-level complex system",
            "EnterpriseApp"
        )
        
        call_args = basic_creator_mode.task_generator.generate_from_template.call_args
        customizations = call_args[1]['customizations']
        assert customizations['size'] == ProjectSize.LARGE
    
    async def test_create_from_description_default_template(self, basic_creator_mode):
        """Test description defaults to web template when no keywords match."""
        mock_tasks = [MockTask(id='task-1')]
        basic_creator_mode.task_generator.generate_from_template.return_value = mock_tasks
        
        result = await basic_creator_mode.create_from_description(
            "Build something cool",
            "CoolProject"
        )
        
        call_args = basic_creator_mode.task_generator.generate_from_template.call_args
        assert call_args.kwargs['template'] == basic_creator_mode.templates['web']


class TestInternalMethods:
    """Test suite for internal helper methods."""
    
    def test_task_to_dict(self, basic_creator_mode):
        """Test conversion of Task object to dictionary."""
        task = MockTask(
            id='task-123',
            name='Test Task',
            description='Test description',
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            labels=['backend', 'api'],
            estimated_hours=5.0,
            dependencies=['task-100'],
            metadata={
                'phase': 'Development',
                'phase_order': 2,
                'generated': True
            }
        )
        
        result = basic_creator_mode._task_to_dict(task)
        
        assert result['id'] == 'task-123'
        assert result['name'] == 'Test Task'
        assert result['description'] == 'Test description'
        assert result['status'] == 'in_progress'
        assert result['priority'] == 'high'
        assert result['labels'] == ['backend', 'api']
        assert result['estimated_hours'] == 5.0
        assert result['dependencies'] == ['task-100']
        assert result['phase'] == 'Development'
        assert result['phase_order'] == 2
        assert result['generated'] is True
    
    def test_task_to_dict_missing_metadata(self, basic_creator_mode):
        """Test task_to_dict handles missing metadata gracefully."""
        task = MockTask(metadata={})
        
        result = basic_creator_mode._task_to_dict(task)
        
        assert result['phase'] is None
        assert result['phase_order'] is None
        assert result['generated'] is False
    
    def test_get_phases_summary(self, basic_creator_mode):
        """Test phase summary generation from tasks."""
        tasks = [
            MockTask(
                name='Task 1',
                estimated_hours=2,
                metadata={'phase': 'Planning', 'phase_order': 1}
            ),
            MockTask(
                name='Task 2',
                estimated_hours=3,
                metadata={'phase': 'Planning', 'phase_order': 1}
            ),
            MockTask(
                name='Task 3',
                estimated_hours=5,
                metadata={'phase': 'Development', 'phase_order': 2}
            ),
            MockTask(
                name='Task 4',
                estimated_hours=1,
                metadata={'phase': 'Testing', 'phase_order': 3}
            )
        ]
        
        result = basic_creator_mode._get_phases_summary(tasks)
        
        # Check phases are in correct order
        phase_names = list(result.keys())
        assert phase_names == ['Planning', 'Development', 'Testing']
        
        # Check Planning phase
        assert result['Planning']['order'] == 1
        assert result['Planning']['task_count'] == 2
        assert result['Planning']['estimated_hours'] == 5
        assert set(result['Planning']['task_names']) == {'Task 1', 'Task 2'}
        
        # Check Development phase
        assert result['Development']['order'] == 2
        assert result['Development']['task_count'] == 1
        assert result['Development']['estimated_hours'] == 5
        
        # Check Testing phase
        assert result['Testing']['order'] == 3
        assert result['Testing']['task_count'] == 1
        assert result['Testing']['estimated_hours'] == 1
    
    def test_get_phases_summary_no_metadata(self, basic_creator_mode):
        """Test phase summary handles tasks without metadata."""
        tasks = [
            MockTask(name='Task 1', estimated_hours=2, metadata={}),
            MockTask(name='Task 2', estimated_hours=3, metadata={'phase': 'Planning'})
        ]
        
        result = basic_creator_mode._get_phases_summary(tasks)
        
        assert 'Unknown' in result
        assert result['Unknown']['task_count'] == 1
        assert result['Unknown']['order'] == 0


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""
    
    async def test_empty_generated_tasks(self, basic_creator_mode):
        """Test handling of empty task generation."""
        basic_creator_mode.task_generator.generate_from_template.return_value = []
        
        result = await basic_creator_mode.create_project_from_template(
            template_name='web',
            project_name='Empty Project'
        )
        
        assert result['success'] is True
        assert result['tasks_generated'] == 0
        assert result['tasks'] == []
        assert result['estimated_total_hours'] == 0
    
    async def test_task_with_all_optional_fields(self, basic_creator_mode):
        """Test task conversion with all optional fields populated."""
        task = MockTask(
            id='full-task',
            name='Full Task',
            description='Task with all fields',
            status=TaskStatus.DONE,
            priority=Priority.URGENT,
            labels=['urgent', 'backend', 'database'],
            estimated_hours=10.0,
            dependencies=['dep-1', 'dep-2', 'dep-3'],
            metadata={
                'phase': 'Deployment',
                'phase_order': 5,
                'generated': True,
                'custom_field': 'custom_value'
            },
            assigned_to='worker-123',
            actual_hours=12.5,
            due_date=datetime.now()
        )
        
        result = basic_creator_mode._task_to_dict(task)
        
        assert result['id'] == 'full-task'
        assert result['status'] == 'done'
        assert result['priority'] == 'urgent'
        assert len(result['labels']) == 3
        assert len(result['dependencies']) == 3
        assert result['phase'] == 'Deployment'
    
    async def test_concurrent_customization_calls(self, basic_creator_mode):
        """Test that state remains consistent with concurrent customization."""
        basic_creator_mode.state['active_project'] = {
            'name': 'Test Project',
            'template': 'web',
            'customizations': {'size': ProjectSize.MEDIUM}
        }
        
        # Simulate different task results for each call
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return [MockTask(id=f'task-{call_count}', estimated_hours=call_count)]
        
        basic_creator_mode.task_generator.generate_from_template.side_effect = side_effect
        
        # Make two customization calls
        result1 = await basic_creator_mode.customize_project({'size': ProjectSize.LARGE})
        result2 = await basic_creator_mode.customize_project({'labels': ['urgent']})
        
        # Both should succeed
        assert result1['success'] is True
        assert result2['success'] is True
        
        # Final state should reflect last customization
        final_customizations = basic_creator_mode.state['active_project']['customizations']
        assert 'labels' in final_customizations
        assert final_customizations['labels'] == ['urgent']