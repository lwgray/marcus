"""
MCP Tools for Marcus Hybrid Approach

Provides MCP tools for mode switching, project creation, and intelligent coordination.
"""

import logging
from typing import Any, Dict, List

from src.detection.board_analyzer import BoardAnalyzer
from src.detection.context_detector import ContextDetector, MarcusMode
from src.modes.creator.template_library import ProjectSize
from src.orchestration.mode_registry import ModeRegistry

logger = logging.getLogger(__name__)


class HybridMarcusTools:
    """MCP tools for the hybrid Marcus approach"""

    def __init__(self, kanban_client):
        self.kanban_client = kanban_client
        self.board_analyzer = BoardAnalyzer()
        self.context_detector = ContextDetector(self.board_analyzer)
        self.mode_registry = ModeRegistry()

    async def switch_mode(
        self, mode: str, reason: str = None, user_id: str = None
    ) -> Dict[str, Any]:
        """
        Switch Marcus to a different operating mode

        Args:
            mode: Target mode ("creator", "enricher", or "adaptive")
            reason: Optional reason for the switch
            user_id: Optional user who triggered the switch

        Returns:
            Result of the mode switch
        """
        try:
            # Validate mode
            mode_enum = MarcusMode(mode.lower())
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid mode '{mode}'. Available modes: creator, enricher, adaptive",
                "available_modes": [m.value for m in MarcusMode],
            }

        result = await self.mode_registry.switch_mode(
            mode=mode_enum, reason=reason, user_id=user_id
        )

        # Record the switch in context detector
        if result.get("success") and user_id:
            self.context_detector.record_mode_switch(user_id, mode_enum)

        return result

    async def get_current_mode(self) -> Dict[str, Any]:
        """
        Get information about the current Marcus mode

        Returns:
            Current mode information and capabilities
        """
        return await self.mode_registry.get_current_mode()

    async def analyze_board_context(
        self, board_id: str = None, user_id: str = None
    ) -> Dict[str, Any]:
        """
        Analyze board context and recommend optimal mode

        Args:
            board_id: Board to analyze (uses default if not provided)
            user_id: User requesting analysis

        Returns:
            Board analysis and mode recommendation
        """
        try:
            # Get tasks from kanban
            all_tasks = await self.kanban_client.get_all_tasks()

            # Analyze board state
            board_state = await self.board_analyzer.analyze_board(
                board_id or "default", all_tasks
            )

            # Get mode recommendation
            recommendation = await self.context_detector.detect_optimal_mode(
                user_id=user_id or "anonymous",
                board_id=board_id or "default",
                tasks=all_tasks,
            )

            # Get suggestions
            suggestions = self.context_detector.get_mode_suggestions(board_state)

            return {
                "success": True,
                "board_analysis": {
                    "task_count": board_state.task_count,
                    "structure_score": board_state.structure_score,
                    "metadata_completeness": board_state.metadata_completeness,
                    "workflow_pattern": board_state.workflow_pattern.value,
                    "phases_detected": board_state.phases_detected,
                    "components_detected": board_state.components_detected,
                    "is_empty": board_state.is_empty,
                    "is_chaotic": board_state.is_chaotic,
                    "is_well_structured": board_state.is_well_structured,
                },
                "mode_recommendation": {
                    "recommended_mode": recommendation.recommended_mode.value,
                    "confidence": recommendation.confidence,
                    "reasoning": recommendation.reasoning,
                    "alternative_modes": [
                        m.value for m in recommendation.alternative_modes
                    ],
                },
                "suggestions": suggestions,
                "current_mode": self.mode_registry.current_mode.value,
            }

        except Exception as e:
            logger.error(f"Error analyzing board context: {e}")
            return {"success": False, "error": str(e)}

    async def create_project_from_template(
        self,
        template_name: str,
        project_name: str,
        size: str = "medium",
        excluded_phases: List[str] = None,
        additional_labels: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new project from a template (Creator Mode)

        Args:
            template_name: Template to use ("web", "api", "mobile")
            project_name: Name for the new project
            size: Project size ("mvp", "small", "medium", "large", "enterprise")
            excluded_phases: Phases to exclude
            additional_labels: Additional labels to add to all tasks

        Returns:
            Generated project information
        """
        # Ensure we're in creator mode
        if self.mode_registry.current_mode != MarcusMode.CREATOR:
            switch_result = await self.mode_registry.switch_mode(
                MarcusMode.CREATOR,
                reason="Switching to creator mode for project generation",
            )
            if not switch_result.get("success"):
                return switch_result

        # Get creator mode handler
        creator_mode = self.mode_registry.get_mode_handler(MarcusMode.CREATOR)
        if not creator_mode:
            return {"success": False, "error": "Creator mode is not available"}

        # Prepare customizations
        try:
            project_size = ProjectSize(size.lower())
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid project size '{size}'. Available sizes: mvp, small, medium, large, enterprise",
            }

        customizations = {
            "size": project_size,
            "excluded_phases": excluded_phases or [],
            "labels": additional_labels or [],
        }

        # Generate project
        result = await creator_mode.create_project_from_template(
            template_name=template_name,
            project_name=project_name,
            customizations=customizations,
        )

        # If successful, create tasks on the kanban board
        if result.get("success") and result.get("tasks"):
            await self._create_tasks_on_board(result["tasks"])
            result["tasks_created_on_board"] = True

        return result

    async def create_project_from_description(
        self, description: str, project_name: str
    ) -> Dict[str, Any]:
        """
        Create a project from natural language description (Creator Mode)

        Args:
            description: Natural language description of the project
            project_name: Name for the new project

        Returns:
            Generated project information
        """
        # Ensure we're in creator mode
        if self.mode_registry.current_mode != MarcusMode.CREATOR:
            await self.mode_registry.switch_mode(
                MarcusMode.CREATOR,
                reason="Switching to creator mode for project generation from description",
            )

        # Get creator mode handler
        creator_mode = self.mode_registry.get_mode_handler(MarcusMode.CREATOR)
        if not creator_mode:
            return {"success": False, "error": "Creator mode is not available"}

        # Generate project
        result = await creator_mode.create_from_description(
            description=description, project_name=project_name
        )

        # If successful, create tasks on the kanban board
        if result.get("success") and result.get("tasks"):
            await self._create_tasks_on_board(result["tasks"])
            result["tasks_created_on_board"] = True

        return result

    async def get_available_templates(self) -> Dict[str, Any]:
        """
        Get list of available project templates

        Returns:
            Available templates with their information
        """
        # Get creator mode handler
        creator_mode = self.mode_registry.get_mode_handler(MarcusMode.CREATOR)
        if not creator_mode:
            return {"success": False, "error": "Creator mode is not available"}

        return await creator_mode.get_available_templates()

    async def preview_template(
        self, template_name: str, size: str = "medium"
    ) -> Dict[str, Any]:
        """
        Preview what a template would generate

        Args:
            template_name: Template to preview
            size: Project size to preview

        Returns:
            Preview of tasks that would be generated
        """
        # Get creator mode handler
        creator_mode = self.mode_registry.get_mode_handler(MarcusMode.CREATOR)
        if not creator_mode:
            return {"success": False, "error": "Creator mode is not available"}

        return await creator_mode.preview_template(
            template_name=template_name, size=size
        )

    async def get_next_task_intelligent(
        self, agent_id: str, agent_skills: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get next task using intelligent assignment (Adaptive Mode)

        Args:
            agent_id: ID of the agent requesting work
            agent_skills: Skills/capabilities of the agent

        Returns:
            Recommended task or explanation of why no task is available
        """
        # Ensure we're in adaptive mode
        if self.mode_registry.current_mode != MarcusMode.ADAPTIVE:
            await self.mode_registry.switch_mode(
                MarcusMode.ADAPTIVE,
                reason="Switching to adaptive mode for intelligent task assignment",
            )

        # Get adaptive mode handler
        adaptive_mode = self.mode_registry.get_mode_handler(MarcusMode.ADAPTIVE)
        if not adaptive_mode:
            return {"success": False, "error": "Adaptive mode is not available"}

        try:
            # Get current tasks
            all_tasks = await self.kanban_client.get_all_tasks()
            available_tasks = [t for t in all_tasks if t.status.value == "TODO"]

            # Get currently assigned tasks
            assigned_tasks = {}  # This would come from assignment persistence

            # Find optimal task
            optimal_task = await adaptive_mode.find_optimal_task_for_agent(
                agent_id=agent_id,
                agent_skills=agent_skills or [],
                available_tasks=available_tasks,
                assigned_tasks=assigned_tasks,
            )

            if optimal_task:
                return {
                    "success": True,
                    "task": {
                        "id": optimal_task.id,
                        "name": optimal_task.name,
                        "description": optimal_task.description,
                        "priority": optimal_task.priority.value,
                        "estimated_hours": optimal_task.estimated_hours,
                        "labels": optimal_task.labels,
                    },
                    "assignment_reasoning": "Selected based on skills, dependencies, and priority",
                }
            else:
                # Get blocking analysis to explain why no tasks are available
                analysis = await adaptive_mode.get_blocking_analysis(all_tasks)

                return {
                    "success": False,
                    "reason": "no_available_tasks",
                    "message": "No tasks are currently unblocked and available",
                    "blocking_analysis": analysis,
                }

        except Exception as e:
            logger.error(f"Error getting next task: {e}")
            return {"success": False, "error": str(e)}

    async def get_blocking_analysis(self) -> Dict[str, Any]:
        """
        Get analysis of what tasks are blocking others

        Returns:
            Analysis of blocking relationships
        """
        # Get adaptive mode handler
        adaptive_mode = self.mode_registry.get_mode_handler(MarcusMode.ADAPTIVE)
        if not adaptive_mode:
            return {"success": False, "error": "Adaptive mode is not available"}

        try:
            all_tasks = await self.kanban_client.get_all_tasks()
            analysis = await adaptive_mode.get_blocking_analysis(all_tasks)

            return {"success": True, "analysis": analysis}

        except Exception as e:
            logger.error(f"Error getting blocking analysis: {e}")
            return {"success": False, "error": str(e)}

    async def _create_tasks_on_board(self, tasks: List[Dict[str, Any]]):
        """Create tasks on the kanban board"""
        for task_data in tasks:
            try:
                # Create task on kanban board
                await self.kanban_client.create_task(
                    {
                        "name": task_data["name"],
                        "description": task_data["description"],
                        "labels": task_data.get("labels", []),
                        "estimated_hours": task_data.get("estimated_hours", 0),
                        "priority": task_data.get("priority", "medium"),
                    }
                )

            except Exception as e:
                logger.error(f"Error creating task '{task_data['name']}' on board: {e}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get MCP tool definitions for the hybrid approach"""
        return [
            {
                "name": "switch_mode",
                "description": "Switch Marcus to a different operating mode (creator, enricher, adaptive)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["creator", "enricher", "adaptive"],
                            "description": "Mode to switch to",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Optional reason for switching modes",
                        },
                    },
                    "required": ["mode"],
                },
            },
            {
                "name": "analyze_board_context",
                "description": "Analyze board state and get mode recommendations",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "create_project_from_template",
                "description": "Create a new project using a template (web, api, mobile)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "template_name": {
                            "type": "string",
                            "enum": ["web", "api", "mobile"],
                            "description": "Template to use",
                        },
                        "project_name": {
                            "type": "string",
                            "description": "Name for the project",
                        },
                        "size": {
                            "type": "string",
                            "enum": ["mvp", "small", "medium", "large", "enterprise"],
                            "description": "Project size",
                        },
                        "excluded_phases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Phases to exclude",
                        },
                    },
                    "required": ["template_name", "project_name"],
                },
            },
            {
                "name": "create_project_from_description",
                "description": "Create a project from natural language description",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Description of the project to create",
                        },
                        "project_name": {
                            "type": "string",
                            "description": "Name for the project",
                        },
                    },
                    "required": ["description", "project_name"],
                },
            },
            {
                "name": "get_available_templates",
                "description": "Get list of available project templates",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_next_task_intelligent",
                "description": "Get next task using intelligent assignment with dependency checking",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent requesting work",
                        },
                        "agent_skills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Skills/capabilities of the agent",
                        },
                    },
                    "required": ["agent_id"],
                },
            },
            {
                "name": "get_blocking_analysis",
                "description": "Get analysis of task dependencies and blocking relationships",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
        ]
