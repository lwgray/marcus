"""
Complete Enricher Mode for Marcus Phase 2.

Enriches existing boards with metadata, structure, and organization.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.models import Task
from src.modes.enricher.board_organizer import BoardOrganizer, OrganizationStrategy
from src.modes.enricher.task_enricher import BoardContext, EnrichedTask, TaskEnricher

logger = logging.getLogger(__name__)


class EnricherMode:
    """Complete Enricher Mode for organizing and enriching existing boards."""

    def __init__(self) -> None:
        self.task_enricher = TaskEnricher()
        self.board_organizer = BoardOrganizer()
        self.state: Dict[str, Any] = {
            "current_enrichment": None,
            "organization_strategies": [],
            "applied_changes": [],
        }

    async def initialize(self, saved_state: Dict[str, Any]) -> None:
        """
        Initialize mode with saved state.

        Parameters
        ----------
        saved_state : Dict[str, Any]
            Previously saved state to restore
        """
        if saved_state:
            self.state.update(saved_state)
            logger.info("Enricher mode initialized with saved state")
        else:
            logger.info("Enricher mode initialized with default state")

    async def get_state(self) -> Dict[str, Any]:
        """
        Get current mode state for saving.

        Returns
        -------
        Dict[str, Any]
            Current state dictionary
        """
        return self.state.copy()

    async def get_status(self) -> Dict[str, Any]:
        """
        Get current mode status.

        Returns
        -------
        Dict[str, Any]
            Status information including current enrichment and strategies
        """
        return {
            "mode": "enricher",
            "current_enrichment": self.state.get("current_enrichment"),
            "available_strategies": len(self.state.get("organization_strategies", [])),
            "applied_changes": len(self.state.get("applied_changes", [])),
        }

    async def analyze_board_for_enrichment(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Analyze board and suggest enrichment opportunities.

        Parameters
        ----------
        tasks : List[Task]
            Current tasks on the board

        Returns
        -------
        Dict[str, Any]
            Analysis results with enrichment suggestions
        """
        if not tasks:
            return {
                "success": True,
                "message": (
                    "Board is empty - consider using Creator mode to " "generate tasks"
                ),
                "recommendations": [
                    "Switch to Creator mode",
                    "Import tasks from template",
                ],
            }

        # Analyze board context
        board_context = await self._analyze_board_context(tasks)

        # Analyze each task for enrichment opportunities
        enrichment_analysis = await self._analyze_tasks_for_enrichment(
            tasks, board_context
        )

        # Analyze organization opportunities
        organization_strategies = (
            await self.board_organizer.analyze_organization_options(tasks)
        )
        self.state["organization_strategies"] = [
            {
                "name": s.name,
                "description": s.description,
                "confidence": s.confidence,
                "reasoning": s.reasoning,
            }
            for s in organization_strategies
        ]

        # Generate overall recommendations
        recommendations = await self._generate_board_recommendations(
            tasks, board_context, enrichment_analysis, organization_strategies
        )

        return {
            "success": True,
            "board_analysis": {
                "total_tasks": len(tasks),
                "project_type": board_context.project_type,
                "detected_phases": board_context.detected_phases,
                "detected_components": board_context.detected_components,
                "workflow_pattern": board_context.workflow_pattern,
            },
            "enrichment_opportunities": enrichment_analysis,
            "organization_strategies": self.state["organization_strategies"],
            "recommendations": recommendations,
        }

    async def enrich_board_tasks(
        self, tasks: List[Task], enrichment_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Apply enrichments to board tasks.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to enrich
        enrichment_options : Optional[Dict[str, Any]], optional
            Specific enrichment options

        Returns
        -------
        Dict[str, Any]
            Results of enrichment process
        """
        board_context = await self._analyze_board_context(tasks)

        # Enrich tasks
        enriched_tasks = await self.task_enricher.enrich_task_batch(
            tasks, board_context
        )

        # Track changes
        changes_applied = []

        for enriched_task in enriched_tasks:
            task_changes = await self._apply_task_enrichments(
                enriched_task, enrichment_options or {}
            )
            if task_changes:
                changes_applied.append(task_changes)

        # Update state
        self.state["current_enrichment"] = {
            "timestamp": datetime.now().isoformat(),
            "tasks_enriched": len(enriched_tasks),
            "changes_applied": len(changes_applied),
        }
        self.state["applied_changes"].extend(changes_applied)

        return {
            "success": True,
            "tasks_enriched": len(enriched_tasks),
            "changes_applied": len(changes_applied),
            "enriched_tasks": [
                {
                    "task_id": et.original_task.id,
                    "task_name": et.original_task.name,
                    "enrichments": {
                        "description_enhanced": et.enriched_description
                        != et.original_task.description,
                        "labels_added": len(
                            set(et.suggested_labels) - set(et.original_task.labels)
                        ),
                        "estimate_added": et.estimated_hours
                        != et.original_task.estimated_hours,
                        "dependencies_suggested": len(et.suggested_dependencies),
                        "acceptance_criteria_added": len(et.acceptance_criteria),
                    },
                    "confidence": et.confidence_score,
                    "reasoning": et.enrichment_reasoning,
                }
                for et in enriched_tasks
            ],
        }

    async def organize_board(
        self,
        tasks: List[Task],
        strategy_name: str,
        organization_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Organize board using specified strategy.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to organize
        strategy_name : str
            Name of organization strategy to use
        organization_options : Optional[Dict[str, Any]], optional
            Additional organization options

        Returns
        -------
        Dict[str, Any]
            Results of organization process
        """
        # Find the strategy
        strategy = None
        for s in self.state.get("organization_strategies", []):
            if s["name"] == strategy_name:
                # Reconstruct strategy object
                strategy = OrganizationStrategy(
                    name=s["name"],
                    description=s["description"],
                    confidence=s["confidence"],
                    structure={},  # Will be recalculated
                    reasoning=s["reasoning"],
                )
                break

        if not strategy:
            return {
                "success": False,
                "error": f"Strategy '{strategy_name}' not found",
                "available_strategies": [
                    s["name"] for s in self.state.get("organization_strategies", [])
                ],
            }

        # Apply organization
        organization_result = await self._apply_organization_strategy(
            tasks, strategy, organization_options or {}
        )

        return organization_result

    async def get_enrichment_preview(
        self, tasks: List[Task], task_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Preview enrichments without applying them.

        Parameters
        ----------
        tasks : List[Task]
            All tasks on the board
        task_ids : Optional[List[str]], optional
            Specific task IDs to preview (None for all)

        Returns
        -------
        Dict[str, Any]
            Preview of what enrichments would be applied
        """
        board_context = await self._analyze_board_context(tasks)

        # Filter tasks if specific IDs provided
        tasks_to_preview = tasks
        if task_ids:
            tasks_to_preview = [t for t in tasks if t.id in task_ids]

        # Generate enrichment previews
        previews = []
        for task in tasks_to_preview:
            enrichments = await self.task_enricher.generate_enrichments(
                task, board_context
            )

            previews.append(
                {
                    "task_id": task.id,
                    "task_name": task.name,
                    "current_state": {
                        "description_length": len(task.description or ""),
                        "label_count": len(task.labels),
                        "has_estimate": bool(task.estimated_hours),
                        "has_dependencies": bool(task.dependencies),
                    },
                    "proposed_enrichments": {
                        "enhanced_description": enrichments.get("description"),
                        "suggested_labels": enrichments.get("labels", []),
                        "estimated_hours": enrichments.get("estimated_hours"),
                        "suggested_dependencies": enrichments.get("dependencies", []),
                        "acceptance_criteria": enrichments.get(
                            "acceptance_criteria", []
                        ),
                    },
                    "confidence": enrichments.get("confidence", 0.5),
                    "reasoning": enrichments.get("reasoning", ""),
                }
            )

        return {
            "success": True,
            "preview_count": len(previews),
            "task_previews": previews,
        }

    async def _analyze_board_context(self, tasks: List[Task]) -> BoardContext:
        """
        Analyze board context for enrichment.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to analyze

        Returns
        -------
        BoardContext
            Analyzed board context
        """
        # Detect project type
        project_type = self._detect_project_type(tasks)

        # Detect phases
        detected_phases = self._detect_phases(tasks)

        # Detect components
        detected_components = self._detect_components(tasks)

        # Extract common labels
        all_labels = []
        for task in tasks:
            all_labels.extend(task.labels)

        from collections import Counter

        label_counts = Counter(all_labels)
        common_labels = [label for label, count in label_counts.most_common(10)]

        # Detect workflow pattern
        workflow_pattern = self._detect_workflow_pattern(tasks)

        return BoardContext(
            project_type=project_type,
            detected_phases=detected_phases,
            detected_components=detected_components,
            common_labels=common_labels,
            workflow_pattern=workflow_pattern,
        )

    def _detect_project_type(self, tasks: List[Task]) -> str:
        """
        Detect type of project from tasks.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to analyze

        Returns
        -------
        str
            Detected project type
        """
        all_text = " ".join(
            [f"{task.name} {task.description or ''}" for task in tasks]
        ).lower()

        if any(word in all_text for word in ["mobile", "ios", "android", "app"]):
            return "mobile"
        elif any(
            word in all_text for word in ["api", "service", "endpoint", "microservice"]
        ):
            return "api"
        elif any(
            word in all_text for word in ["frontend", "ui", "react", "vue", "angular"]
        ):
            return "web"
        elif any(word in all_text for word in ["data", "analysis", "ml", "ai"]):
            return "data"
        else:
            return "general"

    def _detect_phases(self, tasks: List[Task]) -> List[str]:
        """
        Detect development phases from task content.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to analyze

        Returns
        -------
        List[str]
            Detected development phases
        """
        phases = []
        all_text = " ".join(
            [f"{task.name} {task.description or ''}" for task in tasks]
        ).lower()

        phase_indicators = {
            "planning": ["plan", "design", "architect", "spec"],
            "setup": ["setup", "init", "configure"],
            "development": ["implement", "build", "create", "develop"],
            "testing": ["test", "qa", "verify"],
            "deployment": ["deploy", "release", "launch"],
        }

        for phase, indicators in list(phase_indicators.items()):
            if any(indicator in all_text for indicator in indicators):
                phases.append(phase)

        return phases

    def _detect_components(self, tasks: List[Task]) -> List[str]:
        """
        Detect system components from task content.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to analyze

        Returns
        -------
        List[str]
            Detected system components
        """
        components = []
        all_text = " ".join(
            [f"{task.name} {task.description or ''}" for task in tasks]
        ).lower()

        component_indicators = {
            "frontend": ["frontend", "ui", "client", "react", "vue"],
            "backend": ["backend", "api", "server", "service"],
            "database": ["database", "db", "sql", "mongo"],
            "mobile": ["mobile", "ios", "android"],
            "infrastructure": ["infra", "devops", "docker", "k8s"],
        }

        for component, indicators in list(component_indicators.items()):
            if any(indicator in all_text for indicator in indicators):
                components.append(component)

        return components

    def _detect_workflow_pattern(self, tasks: List[Task]) -> str:
        """
        Detect workflow pattern from task statuses.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to analyze

        Returns
        -------
        str
            Detected workflow pattern
        """
        status_counts: Dict[str, int] = {}
        for task in tasks:
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        total = len(tasks)
        if not total:
            return "unknown"

        in_progress_ratio = status_counts.get("IN_PROGRESS", 0) / total

        if in_progress_ratio > 0.5:
            return "parallel"
        elif in_progress_ratio < 0.2:
            return "sequential"
        else:
            return "mixed"

    async def _analyze_tasks_for_enrichment(
        self, tasks: List[Task], board_context: BoardContext
    ) -> Dict[str, Any]:
        """
        Analyze tasks for enrichment opportunities.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to analyze
        board_context : BoardContext
            Board context information

        Returns
        -------
        Dict[str, Any]
            Analysis of enrichment opportunities
        """
        total_tasks = len(tasks)

        # Count missing metadata
        missing_descriptions = sum(
            1 for t in tasks if not t.description or len(t.description) < 20
        )
        missing_labels = sum(1 for t in tasks if len(t.labels) < 2)
        missing_estimates = sum(1 for t in tasks if not t.estimated_hours)
        missing_dependencies = sum(1 for t in tasks if not t.dependencies)

        # Calculate enrichment potential
        enrichment_score = (
            (
                (missing_descriptions / total_tasks) * 0.3
                + (missing_labels / total_tasks) * 0.2
                + (missing_estimates / total_tasks) * 0.3
                + (missing_dependencies / total_tasks) * 0.2
            )
            if total_tasks > 0
            else 0
        )

        return {
            "total_tasks": total_tasks,
            "missing_descriptions": missing_descriptions,
            "missing_labels": missing_labels,
            "missing_estimates": missing_estimates,
            "missing_dependencies": missing_dependencies,
            "enrichment_score": enrichment_score,
            "enrichment_potential": (
                "high"
                if enrichment_score > 0.6
                else "medium" if enrichment_score > 0.3 else "low"
            ),
        }

    async def _generate_board_recommendations(
        self,
        tasks: List[Task],
        board_context: BoardContext,
        enrichment_analysis: Dict[str, Any],
        organization_strategies: List[OrganizationStrategy],
    ) -> List[str]:
        """
        Generate recommendations for board improvement.

        Parameters
        ----------
        tasks : List[Task]
            Board tasks
        board_context : BoardContext
            Board context information
        enrichment_analysis : Dict[str, Any]
            Analysis of enrichment opportunities
        organization_strategies : List[OrganizationStrategy]
            Available organization strategies

        Returns
        -------
        List[str]
            List of recommendations
        """
        recommendations = []

        # Enrichment recommendations
        if enrichment_analysis["enrichment_score"] > 0.5:
            recommendations.append(
                "🔧 Board needs significant enrichment - add descriptions, "
                "labels, and estimates"
            )

        if enrichment_analysis["missing_descriptions"] > 0:
            recommendations.append(
                f"📝 {enrichment_analysis['missing_descriptions']} tasks need "
                f"better descriptions"
            )

        if enrichment_analysis["missing_estimates"] > 0:
            recommendations.append(
                f"⏱️ {enrichment_analysis['missing_estimates']} tasks need "
                f"time estimates"
            )

        # Organization recommendations
        if organization_strategies:
            best_strategy = organization_strategies[0]
            if best_strategy.confidence > 0.7:
                recommendations.append(
                    f"📊 Consider organizing by {best_strategy.description}"
                )

        # Project type specific recommendations
        if board_context.project_type == "web":
            recommendations.append("🌐 Add frontend/backend component labels")
        elif board_context.project_type == "mobile":
            recommendations.append("📱 Add platform-specific labels (iOS/Android)")
        elif board_context.project_type == "api":
            recommendations.append("🔌 Add endpoint-specific documentation")

        # Workflow recommendations
        if board_context.workflow_pattern == "parallel":
            recommendations.append(
                "⚡ High parallelism detected - ensure proper dependency " "management"
            )
        elif board_context.workflow_pattern == "sequential":
            recommendations.append(
                "📈 Sequential workflow - consider if more parallelism is " "possible"
            )

        return recommendations

    async def _apply_task_enrichments(
        self, enriched_task: EnrichedTask, options: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Apply enrichments to a task.

        Parameters
        ----------
        enriched_task : EnrichedTask
            Task with enrichment suggestions
        options : Dict[str, Any]
            Options controlling which enrichments to apply

        Returns
        -------
        Optional[Dict[str, Any]]
            Changes applied, or None if no changes
        """
        changes: Dict[str, Any] = {
            "task_id": enriched_task.original_task.id,
            "task_name": enriched_task.original_task.name,
            "changes": [],
            "timestamp": datetime.now().isoformat(),
        }

        # Check what to apply based on options
        apply_descriptions = options.get("apply_descriptions", True)
        apply_labels = options.get("apply_labels", True)
        apply_estimates = options.get("apply_estimates", True)

        # Apply description enhancement
        if (
            apply_descriptions
            and enriched_task.enriched_description
            != enriched_task.original_task.description
        ):
            changes["changes"].append(
                {
                    "type": "description",
                    "old_value": enriched_task.original_task.description,
                    "new_value": enriched_task.enriched_description,
                }
            )

        # Apply label suggestions
        if apply_labels:
            new_labels = set(enriched_task.suggested_labels) - set(
                enriched_task.original_task.labels
            )
            if new_labels:
                changes["changes"].append(
                    {
                        "type": "labels",
                        "old_value": enriched_task.original_task.labels,
                        "new_value": enriched_task.suggested_labels,
                    }
                )

        # Apply estimate
        if (
            apply_estimates
            and enriched_task.estimated_hours
            != enriched_task.original_task.estimated_hours
        ):
            changes["changes"].append(
                {
                    "type": "estimate",
                    "old_value": enriched_task.original_task.estimated_hours,
                    "new_value": enriched_task.estimated_hours,
                }
            )

        return changes if changes["changes"] else None

    async def _apply_organization_strategy(
        self, tasks: List[Task], strategy: OrganizationStrategy, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply organization strategy to tasks.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to organize
        strategy : OrganizationStrategy
            Organization strategy to apply
        options : Dict[str, Any]
            Additional options

        Returns
        -------
        Dict[str, Any]
            Results of organization
        """
        try:
            if strategy.name == "phase_based":
                phase_structure = await self.board_organizer.organize_by_phase(tasks)
                return {
                    "success": True,
                    "strategy": strategy.name,
                    "structure": {
                        "phases": {
                            k: len(v) for k, v in list(phase_structure.phases.items())
                        },
                        "phase_order": phase_structure.phase_order,
                        "cross_phase_dependencies": len(
                            phase_structure.cross_phase_dependencies
                        ),
                    },
                    "message": (
                        f"Organized {len(tasks)} tasks into "
                        f"{len(phase_structure.phases)} phases"
                    ),
                }

            elif strategy.name == "component_based":
                component_structure = await self.board_organizer.organize_by_component(
                    tasks
                )
                return {
                    "success": True,
                    "strategy": strategy.name,
                    "structure": {
                        "components": {
                            k: len(v)
                            for k, v in list(component_structure.components.items())
                        },
                        "integration_tasks": len(component_structure.integration_tasks),
                        "shared_tasks": len(component_structure.shared_tasks),
                    },
                    "message": f"Organized {len(tasks)} tasks by components",
                }

            else:
                return {
                    "success": False,
                    "error": f"Organization strategy '{strategy.name}' not implemented",
                }

        except Exception as e:
            logger.error(f"Error applying organization strategy: {e}")
            return {"success": False, "error": str(e)}
