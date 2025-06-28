"""
Natural Language MCP Tools for Marcus

These tools expose Marcus's AI capabilities for:
1. Creating projects from natural language descriptions
2. Adding features to existing projects
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
from src.detection.context_detector import ContextDetector
from src.modes.adaptive.basic_adaptive import BasicAdaptiveMode
from src.modes.enricher.enricher_mode import EnricherMode
from src.ai.core.ai_engine import MarcusAIEngine
from src.ai.types import AnalysisContext
from src.core.models import Task, TaskStatus, Priority

logger = logging.getLogger(__name__)


class NaturalLanguageProjectCreator:
    """Handles creation of projects from natural language descriptions"""
    
    def __init__(self, kanban_client, ai_engine):
        self.kanban_client = kanban_client
        self.ai_engine = ai_engine
        self.prd_parser = AdvancedPRDParser()
        self.board_analyzer = BoardAnalyzer()
        self.context_detector = ContextDetector(self.board_analyzer)
        
    async def create_project_from_description(
        self,
        description: str,
        project_name: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete project from natural language description
        
        Uses Phase 1-4 capabilities:
        - Phase 1: Context detection (empty board → Creator Mode)
        - Phase 2: Dependency inference
        - Phase 3: AI-powered task enrichment
        - Phase 4: PRD parsing
        """
        try:
            logger.info(f"Creating project '{project_name}' from natural language")
            
            # Step 1: Detect context (Phase 1)
            board_state = self.board_analyzer.analyze_board("default", [])
            context = await self.context_detector.detect_optimal_mode(
                user_id="system",
                board_id="default",
                tasks=[]
            )
            
            if context.primary_mode != "creator":
                logger.warning(f"Expected creator mode but got {context.primary_mode}")
            
            # Step 2: Parse PRD with AI (Phase 4)
            constraints = self._build_constraints(options)
            logger.info(f"Parsing PRD with constraints: {constraints}")
            
            prd_result = await self.prd_parser.parse_prd_to_tasks(description, constraints)
            
            # Step 3: Safety check - ensure no premature deployment (Phase 1 + 3)
            safe_tasks = await self._apply_safety_checks(prd_result.tasks)
            
            # Step 4: Create tasks on board
            created_tasks = []
            for task in safe_tasks:
                # Create task on kanban board
                kanban_task = await self.kanban_client.create_task({
                    "name": task.name,
                    "description": task.description,
                    "priority": task.priority.value,
                    "labels": task.labels,
                    "estimated_hours": task.estimated_hours,
                    "dependencies": task.dependencies
                })
                created_tasks.append(kanban_task)
            
            # Step 5: Create project metadata
            result = {
                "success": True,
                "project_name": project_name,
                "tasks_created": len(created_tasks),
                "phases": list(prd_result.task_hierarchy.keys()),
                "estimated_days": prd_result.estimated_timeline.get("estimated_duration_days", 0),
                "dependencies_mapped": len(prd_result.dependencies),
                "risk_level": prd_result.risk_assessment.get("overall_risk_level", "unknown"),
                "confidence": prd_result.generation_confidence,
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully created project with {len(created_tasks)} tasks")
            return result
            
        except Exception as e:
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
            # Parse deadline string to datetime
            try:
                constraints.deadline = datetime.fromisoformat(options["deadline"])
            except:
                pass
                
        return constraints
    
    async def _apply_safety_checks(self, tasks: List[Task]) -> List[Task]:
        """Apply safety checks to ensure logical task ordering"""
        # Find deployment tasks
        deployment_tasks = [t for t in tasks if self._is_deployment_task(t)]
        
        for deploy_task in deployment_tasks:
            # Ensure deployment depends on ALL implementation and testing tasks
            impl_tasks = [t for t in tasks if self._is_implementation_task(t)]
            test_tasks = [t for t in tasks if self._is_testing_task(t)]
            
            # Add dependencies if not already present
            for impl_task in impl_tasks:
                if impl_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(impl_task.id)
            
            for test_task in test_tasks:
                if test_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(test_task.id)
        
        return tasks
    
    def _is_deployment_task(self, task: Task) -> bool:
        """Check if task is deployment-related"""
        keywords = ["deploy", "release", "production", "launch"]
        task_lower = task.name.lower()
        return any(keyword in task_lower for keyword in keywords)
    
    def _is_implementation_task(self, task: Task) -> bool:
        """Check if task is implementation-related"""
        keywords = ["implement", "build", "create", "develop", "code"]
        task_lower = task.name.lower()
        return any(keyword in task_lower for keyword in keywords)
    
    def _is_testing_task(self, task: Task) -> bool:
        """Check if task is testing-related"""
        keywords = ["test", "qa", "quality", "verify"]
        task_lower = task.name.lower()
        return any(keyword in task_lower for keyword in keywords)


class NaturalLanguageFeatureAdder:
    """Handles adding features to existing projects using natural language"""
    
    def __init__(self, kanban_client, ai_engine, project_tasks):
        self.kanban_client = kanban_client
        self.ai_engine = ai_engine
        self.project_tasks = project_tasks
        self.adaptive_mode = BasicAdaptiveMode()
        self.enricher = BasicEnricher()
        
    async def add_feature_from_description(
        self,
        feature_description: str,
        integration_point: str = "auto_detect"
    ) -> Dict[str, Any]:
        """
        Add a feature to existing project from natural language
        
        Uses Phase 1-4 capabilities:
        - Phase 1: Context detection (existing project → Adaptive Mode)
        - Phase 2: Dependency mapping to existing tasks
        - Phase 3: AI-powered integration point detection
        """
        try:
            logger.info(f"Adding feature: {feature_description}")
            
            # Step 1: Parse feature into tasks
            feature_tasks = await self._parse_feature_to_tasks(feature_description)
            
            # Step 2: Detect integration points
            if integration_point == "auto_detect":
                integration_info = await self._detect_integration_points(
                    feature_tasks, 
                    self.project_tasks
                )
            else:
                integration_info = {"tasks": [], "phase": integration_point}
            
            # Step 3: Map dependencies to existing tasks
            for feature_task in feature_tasks:
                # Add dependencies on integration points
                for integration_task_id in integration_info.get("tasks", []):
                    if integration_task_id not in feature_task.dependencies:
                        feature_task.dependencies.append(integration_task_id)
            
            # Step 4: Apply safety checks
            safe_tasks = await self._apply_feature_safety_checks(feature_tasks)
            
            # Step 5: Create tasks on board
            created_tasks = []
            for task in safe_tasks:
                kanban_task = await self.kanban_client.create_task({
                    "name": task.name,
                    "description": task.description,
                    "priority": task.priority.value,
                    "labels": task.labels,
                    "estimated_hours": task.estimated_hours,
                    "dependencies": task.dependencies
                })
                created_tasks.append(kanban_task)
            
            result = {
                "success": True,
                "tasks_created": len(created_tasks),
                "integration_points": integration_info.get("tasks", []),
                "integration_detected": integration_point == "auto_detect",
                "confidence": integration_info.get("confidence", 0.8),
                "feature_phase": integration_info.get("phase", "current")
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
        # Use AI to understand the feature
        feature_analysis = await self.ai_engine.analyze_feature_request(feature_description)
        
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
                dependencies=[]
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
        # Use AI to analyze integration points
        integration_analysis = await self.ai_engine.analyze_integration_points(
            feature_tasks,
            existing_tasks
        )
        
        # Find related existing tasks
        integration_tasks = []
        for existing_task in existing_tasks:
            # Check if feature needs this functionality
            if self._is_integration_dependency(feature_tasks, existing_task):
                integration_tasks.append(existing_task.id)
        
        return {
            "tasks": integration_tasks,
            "phase": integration_analysis.get("suggested_phase", "current"),
            "confidence": integration_analysis.get("confidence", 0.8)
        }
    
    def _is_integration_dependency(self, feature_tasks: List[Task], existing_task: Task) -> bool:
        """Check if feature tasks depend on existing task"""
        # Simple heuristic - can be enhanced with AI
        existing_keywords = set(existing_task.labels + [existing_task.name.lower()])
        
        for feature_task in feature_tasks:
            feature_keywords = set(feature_task.labels + [feature_task.name.lower()])
            
            # Check for common concepts
            if existing_keywords & feature_keywords:
                return True
                
            # Specific checks
            if "auth" in existing_keywords and any(
                keyword in feature_task.name.lower() 
                for keyword in ["user", "permission", "secure", "private"]
            ):
                return True
                
        return False
    
    async def _apply_feature_safety_checks(self, tasks: List[Task]) -> List[Task]:
        """Apply safety checks to feature tasks"""
        # Same safety logic as project creation
        deployment_tasks = [t for t in tasks if "deploy" in t.name.lower()]
        
        for deploy_task in deployment_tasks:
            impl_tasks = [t for t in tasks if any(
                keyword in t.name.lower() 
                for keyword in ["implement", "build", "create"]
            )]
            test_tasks = [t for t in tasks if "test" in t.name.lower()]
            
            for impl_task in impl_tasks:
                if impl_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(impl_task.id)
            
            for test_task in test_tasks:
                if test_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(test_task.id)
        
        return tasks


# MCP Tool Functions (to be added to marcus_mcp_server.py)

async def create_project_from_natural_language(
    description: str,
    project_name: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    MCP tool to create a project from natural language description
    
    This is the main entry point that Claude will call.
    """
    from marcus_mcp_server import state
    
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
    if result["success"]:
        await state.refresh_project_state()
    
    return result


async def add_feature_natural_language(
    feature_description: str,
    integration_point: str = "auto_detect"
) -> Dict[str, Any]:
    """
    MCP tool to add a feature to existing project using natural language
    
    This is the main entry point that Claude will call.
    """
    from marcus_mcp_server import state
    
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
    if result["success"]:
        await state.refresh_project_state()
    
    return result