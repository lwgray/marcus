"""
Natural Language MCP Tools for Marcus (Refactored)

These tools expose Marcus's AI capabilities for:
1. Creating projects from natural language descriptions
2. Adding features to existing projects

This refactored version eliminates code duplication by using base classes and utilities.
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.detection.board_analyzer import BoardAnalyzer
from src.detection.context_detector import ContextDetector, MarcusMode
from src.modes.adaptive.basic_adaptive import BasicAdaptiveMode
from src.modes.enricher.enricher_mode import EnricherMode
from src.ai.core.ai_engine import MarcusAIEngine
from src.ai.types import AnalysisContext
from src.core.models import Task, TaskStatus, Priority

# Import refactored base classes and utilities
from src.integrations.nlp_base import NaturalLanguageTaskCreator
from src.integrations.nlp_task_utils import TaskType, TaskClassifier, TaskBuilder, SafetyChecker

logger = logging.getLogger(__name__)


class NaturalLanguageProjectCreator(NaturalLanguageTaskCreator):
    """
    Handles creation of projects from natural language descriptions.
    
    Refactored to use base class and eliminate code duplication.
    """
    
    def __init__(self, kanban_client, ai_engine):
        super().__init__(kanban_client, ai_engine)
        self.prd_parser = AdvancedPRDParser()
        self.board_analyzer = BoardAnalyzer()
        self.context_detector = ContextDetector(self.board_analyzer)
    
    async def process_natural_language(
        self, 
        description: str,
        project_name: str = None,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """
        Process project description into tasks.
        
        Implementation of abstract method from base class.
        """
        # Detect context (Phase 1)
        board_state = await self.board_analyzer.analyze_board("default", [])
        context = await self.context_detector.detect_optimal_mode(
            user_id="system",
            board_id="default",
            tasks=[]
        )
        
        if context.recommended_mode != MarcusMode.CREATOR:
            logger.warning(f"Expected creator mode but got {context.recommended_mode}")
        
        # Parse PRD with AI (Phase 4)
        constraints = self._build_constraints(options)
        logger.info(f"Parsing PRD with constraints: {constraints}")
        
        prd_result = await self.prd_parser.parse_prd_to_tasks(description, constraints)
        
        return prd_result.tasks
    
    async def create_project_from_description(
        self,
        description: str,
        project_name: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete project from natural language description.
        
        Uses the base class implementation for common functionality.
        """
        try:
            logger.info(f"Creating project '{project_name}' from natural language")
            
            # Parse tasks
            tasks = await self.process_natural_language(description, project_name, options)
            
            # Apply safety checks using base class
            safe_tasks = await self.apply_safety_checks(tasks)
            
            # Create tasks on board using base class
            created_tasks = await self.create_tasks_on_board(safe_tasks)
            
            # Get task classification
            classified_tasks = self.classify_tasks(created_tasks)
            
            # Create project metadata (specific to project creation)
            # Create a snapshot of the dictionary to avoid modification during iteration
            task_breakdown = {}
            for task_type, tasks in list(classified_tasks.items()):
                if tasks:
                    task_breakdown[task_type.value] = len(tasks)
            
            result = {
                "success": True,
                "project_name": project_name,
                "tasks_created": len(created_tasks),
                "task_breakdown": task_breakdown,
                "phases": self._extract_phases(created_tasks),
                "estimated_days": self._estimate_duration(created_tasks),
                "dependencies_mapped": self._count_dependencies(created_tasks),
                "risk_level": self._assess_risk(classified_tasks),
                "confidence": 0.85,
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully created project with {len(created_tasks)} tasks")
            return result
            
        except Exception as e:
            # Log detailed traceback for debugging
            import traceback
            print(f"\n{'='*80}")
            print("ERROR IN create_project_from_description")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"{'='*80}")
            traceback.print_exc()
            print(f"{'='*80}\n")
            
            logger.error(f"Error creating project: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_constraints(self, options: Optional[Dict[str, Any]]) -> ProjectConstraints:
        """Build project constraints from options"""
        if not options:
            return ProjectConstraints()
            
        constraints = ProjectConstraints(
            team_size=options.get("team_size", 3),
            available_skills=options.get("tech_stack", []),
            technology_constraints=options.get("tech_stack", [])
        )
        
        if "deadline" in options:
            try:
                constraints.deadline = datetime.fromisoformat(options["deadline"])
            except:
                pass
                
        return constraints
    
    def _extract_phases(self, tasks: List[Task]) -> List[str]:
        """Extract project phases from tasks"""
        phases = set()
        for task in tasks:
            for label in task.labels:
                if label in ["infrastructure", "backend", "frontend", "testing", "deployment"]:
                    phases.add(label)
        return sorted(phases)
    
    def _estimate_duration(self, tasks: List[Task]) -> int:
        """Estimate project duration in days"""
        total_hours = sum(task.estimated_hours for task in tasks if task.estimated_hours)
        # Assume 8 hours per day, with some parallelization factor
        return int(total_hours / (8 * 2))  # 2 developers working in parallel
    
    def _count_dependencies(self, tasks: List[Task]) -> int:
        """Count total dependencies"""
        return sum(len(task.dependencies) for task in tasks)
    
    def _assess_risk(self, classified_tasks: Dict[TaskType, List[Task]]) -> str:
        """Assess project risk level"""
        # Create a list to avoid modification during iteration
        total_tasks = sum(len(tasks) for tasks in list(classified_tasks.values()))
        
        if total_tasks > 50:
            return "high"
        elif total_tasks > 20:
            return "medium"
        else:
            return "low"


class NaturalLanguageFeatureAdder(NaturalLanguageTaskCreator):
    """
    Handles adding features to existing projects using natural language.
    
    Refactored to use base class and eliminate code duplication.
    """
    
    def __init__(self, kanban_client, ai_engine, project_tasks):
        super().__init__(kanban_client, ai_engine)
        self.project_tasks = project_tasks
        self.adaptive_mode = BasicAdaptiveMode()
        from src.modes.enricher.basic_enricher import BasicEnricher
        self.enricher = BasicEnricher()
    
    async def process_natural_language(
        self, 
        description: str,
        integration_point: str = "auto_detect",
        **kwargs
    ) -> List[Task]:
        """
        Process feature description into tasks.
        
        Implementation of abstract method from base class.
        """
        # Parse feature into tasks
        feature_tasks = await self._parse_feature_to_tasks(description)
        
        # Enrich the parsed tasks
        for i, task in enumerate(feature_tasks):
            feature_tasks[i] = self.enricher.enrich_task(task)
        
        # Detect integration points
        if integration_point == "auto_detect":
            integration_info = await self._detect_integration_points(
                feature_tasks, 
                self.project_tasks
            )
        else:
            integration_info = {"tasks": [], "phase": integration_point}
        
        # Map dependencies to existing tasks
        for feature_task in feature_tasks:
            for integration_task_id in integration_info.get("tasks", []):
                if integration_task_id not in feature_task.dependencies:
                    feature_task.dependencies.append(integration_task_id)
        
        # Store integration info for later use
        self._integration_info = integration_info
        
        return feature_tasks
    
    async def add_feature_from_description(
        self,
        feature_description: str,
        integration_point: str = "auto_detect"
    ) -> Dict[str, Any]:
        """
        Add a feature to existing project from natural language.
        
        Uses the base class implementation for common functionality.
        """
        try:
            logger.info(f"Adding feature: {feature_description}")
            
            # Parse and process tasks
            tasks = await self.process_natural_language(
                feature_description, 
                integration_point=integration_point
            )
            
            # Apply safety checks using base class
            safe_tasks = await self.apply_safety_checks(tasks)
            
            # Create tasks on board using base class
            created_tasks = await self.create_tasks_on_board(safe_tasks)
            
            # Get task classification
            classified_tasks = self.classify_tasks(created_tasks)
            
            # Create feature-specific result
            # Create a snapshot of the dictionary to avoid modification during iteration
            task_breakdown = {}
            for task_type, tasks in list(classified_tasks.items()):
                if tasks:
                    task_breakdown[task_type.value] = len(tasks)
            
            result = {
                "success": True,
                "tasks_created": len(created_tasks),
                "task_breakdown": task_breakdown,
                "integration_points": self._integration_info.get("tasks", []),
                "integration_detected": integration_point == "auto_detect",
                "confidence": self._integration_info.get("confidence", 0.8),
                "feature_phase": self._integration_info.get("phase", "current"),
                "complexity": self._calculate_complexity(created_tasks)
            }
            
            logger.info(f"Successfully added feature with {len(created_tasks)} tasks")
            return result
            
        except Exception as e:
            logger.error(f"Error adding feature: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _parse_feature_to_tasks(self, feature_description: str) -> List[Task]:
        """Parse feature description into tasks using AI"""
        try:
            # Use AI engine to analyze the feature request
            feature_analysis = await self.ai_engine.analyze_feature_request(feature_description)
        except Exception as e:
            logger.warning(f"AI analysis failed, using fallback: {str(e)}")
            feature_analysis = self._generate_fallback_tasks(feature_description)
        
        # Generate tasks based on analysis
        tasks = []
        task_id_counter = len(self.project_tasks) + 1
        
        for task_info in feature_analysis.get("required_tasks", []):
            task = Task(
                id=str(task_id_counter),
                name=task_info["name"],
                description=task_info.get("description", ""),
                status=TaskStatus.TODO,
                priority=Priority.HIGH if task_info.get("critical") else Priority.MEDIUM,
                labels=task_info.get("labels", ["feature"]),
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                estimated_hours=task_info.get("estimated_hours", 8),
                dependencies=[],
                due_date=None
            )
            tasks.append(task)
            task_id_counter += 1
        
        return tasks
    
    async def _detect_integration_points(
        self, 
        feature_tasks: List[Task], 
        existing_tasks: List[Task]
    ) -> Dict[str, Any]:
        """Detect where feature should integrate with existing project"""
        try:
            # Use AI engine to analyze integration points
            integration_analysis = await self.ai_engine.analyze_integration_points(
                feature_tasks,
                existing_tasks
            )
        except Exception as e:
            logger.warning(f"AI integration analysis failed, using fallback: {str(e)}")
            integration_analysis = self._analyze_integration_fallback(feature_tasks, existing_tasks)
        
        # Use AI-detected dependencies or fall back to label matching
        if "dependent_task_ids" in integration_analysis:
            integration_tasks = integration_analysis["dependent_task_ids"]
        else:
            # Use utility to find related tasks
            integration_tasks = []
            for existing_task in existing_tasks:
                related_features = self.safety_checker._find_related_tasks(
                    existing_task, feature_tasks
                )
                if related_features:
                    integration_tasks.append(existing_task.id)
        
        return {
            "tasks": integration_tasks,
            "phase": integration_analysis.get("suggested_phase", "current"),
            "confidence": integration_analysis.get("confidence", 0.8),
            "complexity": integration_analysis.get("integration_complexity", "medium"),
            "risks": integration_analysis.get("integration_risks", [])
        }
    
    def _calculate_complexity(self, tasks: List[Task]) -> str:
        """Calculate feature complexity based on tasks"""
        total_hours = sum(task.estimated_hours for task in tasks if task.estimated_hours)
        
        if total_hours > 40:
            return "high"
        elif total_hours > 20:
            return "medium"
        else:
            return "low"
    
    def _analyze_integration_fallback(self, feature_tasks: List[Task], existing_tasks: List[Task]) -> Dict[str, Any]:
        """Analyze integration points without AI"""
        # Determine project phase based on existing tasks
        completed_tasks = [t for t in existing_tasks if t.status == TaskStatus.DONE]
        in_progress_tasks = [t for t in existing_tasks if t.status == TaskStatus.IN_PROGRESS]
        
        # Classify existing tasks
        classified_existing = self.classify_tasks(existing_tasks)
        
        # Determine phase based on task types
        if classified_existing[TaskType.DEPLOYMENT]:
            phase = "post-deployment"
            confidence = 0.8
        elif classified_existing[TaskType.TESTING]:
            phase = "testing"
            confidence = 0.85
        elif classified_existing[TaskType.IMPLEMENTATION]:
            phase = "development"
            confidence = 0.85
        else:
            phase = "initial"
            confidence = 0.9
        
        return {
            "suggested_phase": phase,
            "confidence": confidence,
            "project_maturity": len(completed_tasks) / len(existing_tasks) if existing_tasks else 0
        }
    
    def _generate_fallback_tasks(self, feature_description: str) -> Dict[str, Any]:
        """Generate intelligent fallback tasks based on feature description keywords"""
        feature_lower = feature_description.lower()
        tasks = []
        
        # Analyze feature type
        feature_types = {
            'api': ['api', 'endpoint', 'rest', 'graphql'],
            'ui': ['ui', 'interface', 'screen', 'page', 'component', 'frontend'],
            'auth': ['auth', 'login', 'user', 'permission', 'security'],
            'data': ['database', 'model', 'schema', 'data', 'storage'],
            'integration': ['integrate', 'connect', 'sync', 'webhook']
        }
        
        detected_types = []
        for ftype, keywords in list(feature_types.items()):
            if any(word in feature_lower for word in keywords):
                detected_types.append(ftype)
        
        # Always start with design/planning task
        tasks.append({
            "name": f"Design {feature_description}",
            "description": f"Create technical design and plan for implementing {feature_description}",
            "estimated_hours": 4,
            "labels": ["feature", "design", "planning"],
            "critical": False
        })
        
        # Add type-specific tasks
        task_templates = {
            'data': {
                "name": f"Create database schema for {feature_description}",
                "description": f"Design and implement database models and migrations",
                "estimated_hours": 6,
                "labels": ["feature", "database", "backend"],
                "critical": True
            },
            'api': {
                "name": f"Implement backend for {feature_description}",
                "description": f"Create backend services, APIs, and business logic",
                "estimated_hours": 12,
                "labels": ["feature", "backend", "api"],
                "critical": True
            },
            'ui': {
                "name": f"Build UI components for {feature_description}",
                "description": f"Create frontend components and user interface",
                "estimated_hours": 10,
                "labels": ["feature", "frontend", "ui"],
                "critical": True
            },
            'auth': {
                "name": f"Implement security for {feature_description}",
                "description": f"Add authentication, authorization, and security measures",
                "estimated_hours": 8,
                "labels": ["feature", "security", "auth"],
                "critical": True
            },
            'integration': {
                "name": f"Build integration layer for {feature_description}",
                "description": f"Implement integration points and data synchronization",
                "estimated_hours": 8,
                "labels": ["feature", "integration", "backend"],
                "critical": True
            }
        }
        
        # Add tasks for detected types
        for dtype in detected_types:
            if dtype in task_templates:
                tasks.append(task_templates[dtype])
        
        # If no specific type detected, add generic implementation
        if not detected_types:
            tasks.append(task_templates['api'])  # Default to backend
        
        # Always add testing and documentation
        tasks.extend([
            {
                "name": f"Test {feature_description}",
                "description": f"Write unit tests, integration tests, and perform QA",
                "estimated_hours": 6,
                "labels": ["feature", "testing", "qa"],
                "critical": False
            },
            {
                "name": f"Document {feature_description}",
                "description": f"Create user documentation and API documentation",
                "estimated_hours": 3,
                "labels": ["feature", "documentation"],
                "critical": False
            }
        ])
        
        return {"required_tasks": tasks}


# MCP Tool Functions remain the same
async def create_project_from_natural_language(
    description: str,
    project_name: str,
    state: Any = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    MCP tool to create a project from natural language description
    
    This is the main entry point that Claude will call.
    """
    try:
        # Validate required parameters
        if not description or not description.strip():
            return {
                "success": False,
                "error": "Description is required and cannot be empty"
            }
        
        if not project_name or not project_name.strip():
            return {
                "success": False,
                "error": "Project name is required and cannot be empty"
            }
        
        # Check if state was provided
        if state is None:
            raise ValueError("State parameter is required")
        
        # Initialize kanban client if needed
        if not state.kanban_client:
            try:
                await state.initialize_kanban()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to initialize kanban client: {str(e)}"
                }
        
        # Verify kanban client supports create_task
        if not hasattr(state.kanban_client, 'create_task'):
            return {
                "success": False,
                "error": "Kanban client does not support task creation. Please ensure KanbanClientWithCreate is being used."
            }
        
        # Initialize project creator
        creator = NaturalLanguageProjectCreator(
            kanban_client=state.kanban_client,
            ai_engine=state.ai_engine
        )
        
        # Create project
        result = await creator.create_project_from_description(
            description=description,
            project_name=project_name,
            options=options
        )
        
        # Update Marcus state if successful
        if result.get("success"):
            try:
                await state.refresh_project_state()
            except Exception as e:
                # Log but don't fail the operation
                logger.warning(f"Failed to refresh project state: {str(e)}")
        
        return result
        
    except Exception as e:
        # Log detailed traceback for debugging
        import traceback
        print(f"\n{'='*80}")
        print("ERROR IN create_project_from_natural_language")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"{'='*80}")
        traceback.print_exc()
        print(f"{'='*80}\n")
        
        logger.error(f"Unexpected error in create_project_from_natural_language: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def add_feature_natural_language(
    feature_description: str,
    integration_point: str = "auto_detect",
    state: Any = None
) -> Dict[str, Any]:
    """
    MCP tool to add a feature to existing project using natural language
    
    This is the main entry point that Claude will call.
    """
    try:
        # Validate required parameters
        if not feature_description or not feature_description.strip():
            return {
                "success": False,
                "error": "Feature description is required and cannot be empty"
            }
        
        # Check if state was provided
        if state is None:
            raise ValueError("State parameter is required")
        
        # Initialize kanban client if needed
        if not state.kanban_client:
            try:
                await state.initialize_kanban()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to initialize kanban client: {str(e)}"
                }
        
        # Verify kanban client supports create_task
        if not hasattr(state.kanban_client, 'create_task'):
            return {
                "success": False,
                "error": "Kanban client does not support task creation. Please ensure KanbanClientWithCreate is being used."
            }
        
        # Check if there are existing tasks (required for feature addition)
        if not state.project_tasks or len(state.project_tasks) == 0:
            return {
                "success": False,
                "error": "No existing project found. Please create a project first before adding features."
            }
        
        # Initialize feature adder
        adder = NaturalLanguageFeatureAdder(
            kanban_client=state.kanban_client,
            ai_engine=state.ai_engine,
            project_tasks=state.project_tasks
        )
        
        # Add feature
        result = await adder.add_feature_from_description(
            feature_description=feature_description,
            integration_point=integration_point
        )
        
        # Update Marcus state if successful
        if result.get("success"):
            try:
                await state.refresh_project_state()
            except Exception as e:
                # Log but don't fail the operation
                logger.warning(f"Failed to refresh project state: {str(e)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in add_feature_natural_language: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }