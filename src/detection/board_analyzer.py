"""
Board State Analyzer for Marcus Hybrid Approach

Analyzes kanban board state to determine optimal Marcus mode and understand
project organization level.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.models import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)


class WorkflowPattern(Enum):
    """Detected workflow patterns"""

    SEQUENTIAL = "sequential"  # Tasks completed one by one
    PARALLEL = "parallel"  # Multiple tasks in progress
    PHASED = "phased"  # Clear phase boundaries
    AD_HOC = "ad_hoc"  # No clear pattern
    UNKNOWN = "unknown"


@dataclass
class BoardState:
    """Represents the analyzed state of a board"""

    task_count: int
    tasks_with_descriptions: int
    tasks_with_labels: int
    tasks_with_estimates: int
    tasks_with_dependencies: int
    structure_score: float
    workflow_pattern: WorkflowPattern
    phases_detected: List[str]
    components_detected: List[str]
    metadata_completeness: float
    is_empty: bool
    is_chaotic: bool
    is_well_structured: bool
    recommended_mode: str


class BoardAnalyzer:
    """Analyzes kanban board state to determine optimal Marcus mode"""

    # Common phase indicators
    PHASE_PATTERNS = {
        "setup": r"(setup|init|initialize|config|configure|scaffold)",
        "design": r"(design|architect|plan|model|schema)",
        "development": r"(implement|build|create|develop|code)",
        "testing": r"(test|qa|quality|verify|validate)",
        "deployment": r"(deploy|release|launch|ship|production)",
        "maintenance": r"(maintain|fix|bug|patch|update)",
    }

    # Common component indicators
    COMPONENT_PATTERNS = {
        "frontend": r"(frontend|ui|client|react|vue|angular)",
        "backend": r"(backend|api|server|endpoint|service)",
        "database": r"(database|db|sql|mongo|redis|cache)",
        "infrastructure": r"(infra|devops|ci|cd|docker|k8s)",
        "mobile": r"(mobile|ios|android|app|native)",
        "testing": r"(test|spec|e2e|unit|integration)",
    }

    async def analyze_board(self, board_id: str, tasks: List[Task]) -> BoardState:
        """
        Analyze board characteristics to determine state and recommended mode

        Args:
            board_id: The board identifier
            tasks: List of tasks on the board

        Returns:
            BoardState with analysis results
        """
        if not tasks:
            return self._empty_board_state()

        # Calculate basic metrics
        task_count = len(tasks)
        tasks_with_descriptions = sum(
            1 for t in tasks if t.description and len(t.description) > 20
        )
        tasks_with_labels = sum(1 for t in tasks if t.labels)
        tasks_with_estimates = sum(
            1 for t in tasks if t.estimated_hours and t.estimated_hours > 0
        )
        tasks_with_dependencies = sum(1 for t in tasks if t.dependencies)

        # Calculate structure score
        structure_score = await self.calculate_structure_score(tasks)

        # Detect workflow pattern
        workflow_pattern = await self.detect_workflow_patterns(tasks)

        # Detect phases and components
        phases_detected = await self._detect_phases(tasks)
        components_detected = await self._detect_components(tasks)

        # Calculate metadata completeness
        metadata_completeness = (
            (tasks_with_descriptions / task_count) * 0.3
            + (tasks_with_labels / task_count) * 0.2
            + (tasks_with_estimates / task_count) * 0.3
            + (tasks_with_dependencies / task_count) * 0.2
        )

        # Determine board characteristics
        is_empty = task_count == 0
        is_chaotic = structure_score < 0.3
        is_well_structured = structure_score >= 0.7

        # Recommend mode based on analysis
        recommended_mode = self._recommend_mode(
            is_empty=is_empty,
            is_chaotic=is_chaotic,
            is_well_structured=is_well_structured,
            task_count=task_count,
        )

        return BoardState(
            task_count=task_count,
            tasks_with_descriptions=tasks_with_descriptions,
            tasks_with_labels=tasks_with_labels,
            tasks_with_estimates=tasks_with_estimates,
            tasks_with_dependencies=tasks_with_dependencies,
            structure_score=structure_score,
            workflow_pattern=workflow_pattern,
            phases_detected=phases_detected,
            components_detected=components_detected,
            metadata_completeness=metadata_completeness,
            is_empty=is_empty,
            is_chaotic=is_chaotic,
            is_well_structured=is_well_structured,
            recommended_mode=recommended_mode,
        )

    async def calculate_structure_score(self, tasks: List[Task]) -> float:
        """
        Score 0-1 indicating how well-structured the board is:
        - 0.0-0.3: Chaotic (just task titles)
        - 0.3-0.6: Basic (some organization)
        - 0.6-0.8: Good (clear structure)
        - 0.8-1.0: Excellent (full metadata)

        Args:
            tasks: List of tasks to analyze

        Returns:
            Structure score between 0 and 1
        """
        if not tasks:
            return 0.0

        scores = []

        # Score based on descriptions
        desc_score = sum(
            1 for t in tasks if t.description and len(t.description) > 50
        ) / len(tasks)
        scores.append(desc_score * 0.25)

        # Score based on labels
        label_score = sum(1 for t in tasks if len(t.labels) >= 2) / len(tasks)
        scores.append(label_score * 0.20)

        # Score based on estimates
        estimate_score = sum(
            1 for t in tasks if t.estimated_hours and t.estimated_hours > 0
        ) / len(tasks)
        scores.append(estimate_score * 0.25)

        # Score based on priority distribution
        priorities = [t.priority for t in tasks if t.priority]
        if priorities:
            priority_diversity = len(set(priorities)) / len(Priority)
            scores.append(priority_diversity * 0.15)
        else:
            scores.append(0)

        # Score based on dependencies
        dep_score = sum(1 for t in tasks if t.dependencies) / len(tasks)
        scores.append(dep_score * 0.15)

        return sum(scores)

    async def detect_workflow_patterns(self, tasks: List[Task]) -> WorkflowPattern:
        """
        Detect how the team works based on task patterns

        Args:
            tasks: List of tasks to analyze

        Returns:
            Detected workflow pattern
        """
        if not tasks:
            return WorkflowPattern.UNKNOWN

        # Count tasks by status
        status_counts = Counter(t.status for t in tasks)

        # Count concurrent in-progress tasks
        in_progress = status_counts.get(TaskStatus.IN_PROGRESS, 0)
        total = len(tasks)

        # Detect phases from task names
        phases = await self._detect_phases(tasks)

        # Analyze patterns
        if in_progress == 0:
            return WorkflowPattern.AD_HOC
        elif in_progress == 1 and total > 5:
            return WorkflowPattern.SEQUENTIAL
        elif in_progress > 3:
            return WorkflowPattern.PARALLEL
        elif len(phases) >= 3:
            return WorkflowPattern.PHASED
        else:
            return WorkflowPattern.AD_HOC

    async def _detect_phases(self, tasks: List[Task]) -> List[str]:
        """Detect development phases from task names and descriptions"""
        phases_found = set()

        for task in tasks:
            text = f"{task.name} {task.description or ''}".lower()
            for phase, pattern in self.PHASE_PATTERNS.items():
                if re.search(pattern, text):
                    phases_found.add(phase)

        # Order phases logically
        phase_order = [
            "setup",
            "design",
            "development",
            "testing",
            "deployment",
            "maintenance",
        ]
        return [p for p in phase_order if p in phases_found]

    async def _detect_components(self, tasks: List[Task]) -> List[str]:
        """Detect system components from task names and labels"""
        components_found = set()

        for task in tasks:
            # Check task name and description
            text = f"{task.name} {task.description or ''}".lower()
            for component, pattern in self.COMPONENT_PATTERNS.items():
                if re.search(pattern, text):
                    components_found.add(component)

            # Check labels
            for label in task.labels:
                label_lower = label.lower()
                for component, pattern in self.COMPONENT_PATTERNS.items():
                    if re.search(pattern, label_lower):
                        components_found.add(component)

        return sorted(list(components_found))

    def _recommend_mode(
        self,
        is_empty: bool,
        is_chaotic: bool,
        is_well_structured: bool,
        task_count: int,
    ) -> str:
        """Recommend the best Marcus mode based on board state"""
        if is_empty:
            return "creator"  # Empty board - help create structure
        elif is_chaotic and task_count > 10:
            return "enricher"  # Chaotic board - help organize
        elif is_well_structured:
            return "adaptive"  # Well-structured - just coordinate
        elif task_count < 5:
            return "creator"  # Few tasks - might need more
        else:
            return "enricher"  # Default to helping organize

    def _empty_board_state(self) -> BoardState:
        """Return state for an empty board"""
        return BoardState(
            task_count=0,
            tasks_with_descriptions=0,
            tasks_with_labels=0,
            tasks_with_estimates=0,
            tasks_with_dependencies=0,
            structure_score=0.0,
            workflow_pattern=WorkflowPattern.UNKNOWN,
            phases_detected=[],
            components_detected=[],
            metadata_completeness=0.0,
            is_empty=True,
            is_chaotic=False,
            is_well_structured=False,
            recommended_mode="creator",
        )
