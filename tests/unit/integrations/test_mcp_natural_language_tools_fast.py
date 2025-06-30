"""
Unit tests for Fast Natural Language MCP Tools

Tests the fast version of natural language processing tools that use
pre-defined templates for project creation to avoid timeouts.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import logging

from src.integrations.mcp_natural_language_tools_fast import (
    FastProjectTemplates,
    create_project_from_natural_language_fast,
    create_project_from_natural_language
)
from src.core.models import Task, TaskStatus, Priority


class TestFastProjectTemplates:
    """Test suite for FastProjectTemplates class"""
    
    def test_detect_project_type_recipe_manager(self):
        """Test detection of recipe manager project type"""
        descriptions = [
            "Recipe management app",
            "Food tracker with meal planning",
            "Cooking assistant application",
            "A system for managing recipes and meals"
        ]
        
        for desc in descriptions:
            assert FastProjectTemplates.detect_project_type(desc) == 'recipe_manager'
    
    def test_detect_project_type_ecommerce(self):
        """Test detection of ecommerce project type"""
        descriptions = [
            "Online shop for clothing",
            "Ecommerce platform for books",
            "Product store with payment integration",
            "Shopping cart system"
        ]
        
        for desc in descriptions:
            assert FastProjectTemplates.detect_project_type(desc) == 'ecommerce'
    
    def test_detect_project_type_chat_app(self):
        """Test detection of chat application project type"""
        descriptions = [
            "Real-time chat application",
            "Message platform with video calls",  # Changed to match 'message'
            "Communication tool for teams",
            "Chat system with file sharing"
        ]
        
        for desc in descriptions:
            result = FastProjectTemplates.detect_project_type(desc)
            assert result == 'chat_app', f"Expected 'chat_app' for '{desc}', got '{result}'"
    
    def test_detect_project_type_task_manager(self):
        """Test detection of task manager project type"""
        descriptions = [
            "Task tracking system",
            "Todo list application",
            "Project management tool",
            "Task organizer with deadlines"
        ]
        
        for desc in descriptions:
            assert FastProjectTemplates.detect_project_type(desc) == 'task_manager'
    
    def test_detect_project_type_blog(self):
        """Test detection of blog project type"""
        descriptions = [
            "Blog platform with comments",
            "Article publishing system",
            "Content management system",
            "Personal blog with categories"
        ]
        
        for desc in descriptions:
            assert FastProjectTemplates.detect_project_type(desc) == 'blog'
    
    def test_detect_project_type_generic_web(self):
        """Test fallback to generic web project type"""
        descriptions = [
            "Weather dashboard",
            "Data visualization tool",
            "Analytics platform",
            "Custom web application"
        ]
        
        for desc in descriptions:
            assert FastProjectTemplates.detect_project_type(desc) == 'generic_web'
    
    def test_detect_project_type_case_insensitive(self):
        """Test that project type detection is case insensitive"""
        assert FastProjectTemplates.detect_project_type("RECIPE MANAGER") == 'recipe_manager'
        assert FastProjectTemplates.detect_project_type("Online SHOP") == 'ecommerce'
        assert FastProjectTemplates.detect_project_type("CHAT app") == 'chat_app'
    
    def test_get_template_tasks_recipe_manager(self):
        """Test getting template tasks for recipe manager project"""
        tasks = FastProjectTemplates.get_template_tasks('recipe_manager', 'Recipe app')
        
        assert len(tasks) == 5
        assert tasks[0]['name'] == "Setup project infrastructure"
        assert tasks[0]['priority'] == "high"
        assert "type:setup" in tasks[0]['labels']
        assert tasks[0]['estimated_hours'] == 8
        assert len(tasks[0]['subtasks']) == 3
        assert 'acceptance_criteria' in tasks[0]
        assert 'description' in tasks[0]
        
        # Check recipe-specific tasks
        recipe_tasks = [t['name'] for t in tasks]
        assert "Design database schema for recipes" in recipe_tasks
        assert "Implement recipe CRUD operations" in recipe_tasks
        assert "Build recipe UI components" in recipe_tasks
        assert "Implement meal planning feature" in recipe_tasks
    
    def test_get_template_tasks_generic_web(self):
        """Test getting template tasks for generic web project"""
        tasks = FastProjectTemplates.get_template_tasks('generic_web', 'Web app')
        
        assert len(tasks) == 5
        assert tasks[0]['name'] == "Setup project architecture"
        assert tasks[0]['priority'] == "high"
        assert "type:setup" in tasks[0]['labels']
        
        # Check generic tasks
        generic_tasks = [t['name'] for t in tasks]
        assert "Design system architecture" in generic_tasks
        assert "Implement core backend functionality" in generic_tasks
        assert "Build frontend interface" in generic_tasks
        assert "Testing and deployment" in generic_tasks
    
    def test_get_template_tasks_unknown_type_fallback(self):
        """Test that unknown project types fall back to generic template"""
        tasks = FastProjectTemplates.get_template_tasks('unknown_type', 'Some project')
        generic_tasks = FastProjectTemplates.get_template_tasks('generic_web', 'Some project')
        
        # Should use generic template for unknown types
        assert len(tasks) == len(generic_tasks)
        assert tasks[0]['name'] == generic_tasks[0]['name']
    
    def test_get_template_tasks_chat_app_fallback(self):
        """Test that chat_app type falls back to generic template"""
        # chat_app is detected but doesn't have its own template
        tasks = FastProjectTemplates.get_template_tasks('chat_app', 'Chat application')
        generic_tasks = FastProjectTemplates.get_template_tasks('generic_web', 'Web app')
        
        # Should use generic template for chat_app since it's not defined
        assert len(tasks) == len(generic_tasks)
        assert tasks[0]['name'] == generic_tasks[0]['name']
    
    def test_get_template_tasks_customization(self):
        """Test that template tasks are properly customized"""
        tasks = FastProjectTemplates.get_template_tasks('recipe_manager', 'My Recipe App')
        
        for task in tasks:
            # Check that customization fields are added
            assert 'acceptance_criteria' in task
            assert isinstance(task['acceptance_criteria'], list)
            assert len(task['acceptance_criteria']) == 3
            assert "Functionality is working as expected" in task['acceptance_criteria']
            
            assert 'description' in task
            assert task['description'].startswith("Implementation of")
            assert task['description'].endswith("for the project")
    
    def test_get_template_tasks_preserves_original_fields(self):
        """Test that original template fields are preserved during customization"""
        tasks = FastProjectTemplates.get_template_tasks('recipe_manager', 'Recipe app')
        
        # Check that all original fields are preserved
        for task in tasks:
            assert 'name' in task
            assert 'priority' in task
            assert 'labels' in task
            assert 'estimated_hours' in task
            assert 'subtasks' in task
            assert isinstance(task['labels'], list)
            assert isinstance(task['subtasks'], list)


class TestCreateProjectFromNaturalLanguageFast:
    """Test suite for create_project_from_natural_language_fast function"""
    
    @pytest.fixture
    def mock_state(self):
        """Create a mock state object"""
        state = Mock()
        state.kanban_client = None
        state.initialize_kanban = AsyncMock()
        state.refresh_project_state = AsyncMock()
        return state
    
    @pytest.fixture
    def mock_state_with_client(self):
        """Create a mock state with initialized kanban client"""
        state = Mock()
        state.kanban_client = Mock()
        state.kanban_client.create_task = AsyncMock()
        state.refresh_project_state = AsyncMock()
        return state
    
    @pytest.mark.asyncio
    async def test_create_project_success(self, mock_state_with_client):
        """Test successful project creation"""
        # Setup
        mock_state_with_client.kanban_client.create_task.return_value = Mock(id="task-1")
        
        # Execute
        result = await create_project_from_natural_language_fast(
            description="Recipe management app with meal planning",
            project_name="RecipeManager",
            state=mock_state_with_client
        )
        
        # Assert
        assert result['success'] is True
        assert result['project_name'] == "RecipeManager"
        assert result['project_type'] == 'recipe_manager'
        assert result['tasks_created'] == 5
        assert result['confidence'] == 0.75
        assert 'created_at' in result
        assert result['note'] == "Used fast template-based creation to avoid timeout"
        
        # Verify kanban client was called
        assert mock_state_with_client.kanban_client.create_task.call_count == 5
        assert mock_state_with_client.refresh_project_state.called
    
    @pytest.mark.asyncio
    async def test_create_project_empty_description(self, mock_state):
        """Test project creation with empty description"""
        result = await create_project_from_natural_language_fast(
            description="",
            project_name="TestProject",
            state=mock_state
        )
        
        assert result['success'] is False
        assert result['error'] == "Description is required"
    
    @pytest.mark.asyncio
    async def test_create_project_whitespace_description(self, mock_state):
        """Test project creation with whitespace-only description"""
        result = await create_project_from_natural_language_fast(
            description="   \n\t   ",
            project_name="TestProject",
            state=mock_state
        )
        
        assert result['success'] is False
        assert result['error'] == "Description is required"
    
    @pytest.mark.asyncio
    async def test_create_project_empty_name(self, mock_state):
        """Test project creation with empty project name"""
        result = await create_project_from_natural_language_fast(
            description="A test project",
            project_name="",
            state=mock_state
        )
        
        assert result['success'] is False
        assert result['error'] == "Project name is required"
    
    @pytest.mark.asyncio
    async def test_create_project_no_state(self):
        """Test project creation without state parameter"""
        result = await create_project_from_natural_language_fast(
            description="A test project",
            project_name="TestProject",
            state=None
        )
        
        assert result['success'] is False
        assert result['error'] == "State parameter is required"
    
    @pytest.mark.asyncio
    async def test_create_project_initialize_kanban(self, mock_state):
        """Test that kanban is initialized when not present"""
        # Setup
        mock_kanban = Mock()
        mock_kanban.create_task = AsyncMock(return_value=Mock(id="task-1"))
        
        # Configure mock_state to set kanban_client after initialize_kanban is called
        def set_kanban_client():
            mock_state.kanban_client = mock_kanban
        
        mock_state.initialize_kanban.side_effect = set_kanban_client
        
        result = await create_project_from_natural_language_fast(
            description="A simple web app",
            project_name="SimpleApp",
            state=mock_state
        )
        
        assert mock_state.initialize_kanban.called
        assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_create_project_kanban_init_failure(self, mock_state):
        """Test handling of kanban initialization failure"""
        mock_state.kanban_client = None
        mock_state.initialize_kanban.side_effect = Exception("Connection failed")
        
        result = await create_project_from_natural_language_fast(
            description="A test project",
            project_name="TestProject",
            state=mock_state
        )
        
        assert result['success'] is False
        assert "Failed to initialize kanban" in result['error']
        assert "Connection failed" in result['error']
    
    @pytest.mark.asyncio
    async def test_create_project_task_creation_failure(self, mock_state_with_client):
        """Test handling of individual task creation failures"""
        # Make first task succeed, second fail, rest succeed
        mock_state_with_client.kanban_client.create_task.side_effect = [
            Mock(id="task-1"),
            Exception("Task creation failed"),
            Mock(id="task-3"),
            Mock(id="task-4"),
            Mock(id="task-5")
        ]
        
        with patch('src.integrations.mcp_natural_language_tools_fast.logger') as mock_logger:
            result = await create_project_from_natural_language_fast(
                description="Recipe app",
                project_name="RecipeApp",
                state=mock_state_with_client
            )
        
        # Should still succeed but with fewer tasks
        assert result['success'] is True
        assert result['tasks_created'] == 4  # One task failed
        assert mock_logger.error.called
    
    @pytest.mark.asyncio
    async def test_create_project_task_breakdown_counts(self, mock_state_with_client):
        """Test that task breakdown counts are calculated correctly"""
        mock_state_with_client.kanban_client.create_task.return_value = Mock(id="task-1")
        
        result = await create_project_from_natural_language_fast(
            description="Recipe management system",
            project_name="RecipeSystem",
            state=mock_state_with_client
        )
        
        # Check task breakdown for recipe manager template
        assert result['task_breakdown']['setup'] == 1
        assert result['task_breakdown']['feature'] == 3
        assert result['task_breakdown']['design'] == 1
        assert result['task_breakdown']['testing'] == 0
    
    @pytest.mark.asyncio
    async def test_create_project_estimated_days_calculation(self, mock_state_with_client):
        """Test that estimated days are calculated correctly"""
        mock_state_with_client.kanban_client.create_task.return_value = Mock(id="task-1")
        
        result = await create_project_from_natural_language_fast(
            description="Recipe app",
            project_name="RecipeApp",
            state=mock_state_with_client
        )
        
        # Recipe template has 8+12+16+20+16 = 72 hours
        # With 2 devs (16 hours/day), that's 72/16 = 4.5 days (rounded down to 4)
        assert result['estimated_days'] == 4
    
    @pytest.mark.asyncio
    async def test_create_project_refresh_state_failure(self, mock_state_with_client):
        """Test handling of state refresh failure"""
        mock_state_with_client.kanban_client.create_task.return_value = Mock(id="task-1")
        mock_state_with_client.refresh_project_state.side_effect = Exception("Refresh failed")
        
        with patch('src.integrations.mcp_natural_language_tools_fast.logger') as mock_logger:
            result = await create_project_from_natural_language_fast(
                description="Test app",
                project_name="TestApp",
                state=mock_state_with_client
            )
        
        # Should still succeed even if refresh fails
        assert result['success'] is True
        assert mock_logger.warning.called
    
    @pytest.mark.asyncio
    async def test_create_project_no_tasks_created(self, mock_state_with_client):
        """Test behavior when no tasks are successfully created"""
        mock_state_with_client.kanban_client.create_task.side_effect = Exception("All tasks failed")
        
        with patch('src.integrations.mcp_natural_language_tools_fast.logger'):
            result = await create_project_from_natural_language_fast(
                description="Failed project",
                project_name="FailedProject", 
                state=mock_state_with_client
            )
        
        assert result['success'] is True
        assert result['tasks_created'] == 0
        # Should not attempt to refresh state when no tasks created
        assert not mock_state_with_client.refresh_project_state.called
    
    @pytest.mark.asyncio
    async def test_create_project_general_exception(self, mock_state_with_client):
        """Test handling of unexpected exceptions"""
        # Simulate an unexpected error
        with patch('src.integrations.mcp_natural_language_tools_fast.FastProjectTemplates.detect_project_type') as mock_detect:
            mock_detect.side_effect = RuntimeError("Unexpected error")
            
            with patch('src.integrations.mcp_natural_language_tools_fast.logger') as mock_logger:
                result = await create_project_from_natural_language_fast(
                    description="Test project",
                    project_name="TestProject",
                    state=mock_state_with_client
                )
        
        assert result['success'] is False
        assert "Unexpected error" in result['error']
        assert mock_logger.error.called
    
    @pytest.mark.asyncio
    async def test_create_project_with_options_parameter(self, mock_state_with_client):
        """Test that options parameter is accepted but not used"""
        mock_state_with_client.kanban_client.create_task.return_value = Mock(id="task-1")
        
        result = await create_project_from_natural_language_fast(
            description="Test app",
            project_name="TestApp",
            state=mock_state_with_client,
            options={"some": "options"}
        )
        
        assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_create_project_datetime_format(self, mock_state_with_client):
        """Test that created_at uses ISO format"""
        mock_state_with_client.kanban_client.create_task.return_value = Mock(id="task-1")
        
        result = await create_project_from_natural_language_fast(
            description="Test app",
            project_name="TestApp",
            state=mock_state_with_client
        )
        
        # Verify it's a valid ISO format datetime
        created_at = result['created_at']
        parsed_date = datetime.fromisoformat(created_at)
        assert isinstance(parsed_date, datetime)


class TestModuleExports:
    """Test module-level exports and aliases"""
    
    def test_create_project_alias(self):
        """Test that create_project_from_natural_language is aliased to fast version"""
        assert create_project_from_natural_language == create_project_from_natural_language_fast
    
    def test_fast_function_is_async(self):
        """Test that the main functions are async"""
        import inspect
        assert inspect.iscoroutinefunction(create_project_from_natural_language_fast)
        assert inspect.iscoroutinefunction(create_project_from_natural_language)