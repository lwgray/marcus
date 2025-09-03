"""
Basic Adaptive Mode for Marcus Hybrid Approach

Implements Adaptive Mode that respects dependencies and prevents illogical
task assignments like "Deploy to production" before development is complete.
"""

import logging
from typing import Any, Dict, List, Optional

from src.core.assignment_persistence import AssignmentPersistence
from src.core.models import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)


class BasicAdaptiveMode:
    """Basic Adaptive Mode that coordinates within existing structure"""

    def __init__(self) -> None:
        self.state = {"assignment_preferences": {}, "blocked_tasks": []}
        self.assignment_persistence = AssignmentPersistence()

        # Common dependency patterns to prevent illogical assignments
        self.LOGICAL_DEPENDENCY_PATTERNS = [
            # Setup must come before everything
            {
                "pattern": r"(setup|init|configure|install)",
                "blocks_until_complete": r"(implement|build|create|develop|test|deploy)",
            },
            # Design comes before implementation
            {
                "pattern": r"(design|architect|plan|schema)",
                "blocks_until_complete": r"(implement|build|create|code)",
            },
            # Models/Backend before Frontend
            {
                "pattern": r"(model|backend|api|server)",
                "blocks_until_complete": r"(frontend|ui|client|interface)",
            },
            # Implementation before testing
            {
                "pattern": r"(implement|build|create|develop)",
                "blocks_until_complete": r"(test|qa|verify)",
            },
            # Testing before deployment
            {
                "pattern": r"(test|qa|quality|verify)",
                "blocks_until_complete": r"(deploy|release|launch|production)",
            },
            # Basic features before advanced features
            {
                "pattern": r"(authentication|login|auth)",
                "blocks_until_complete": r"(permissions|roles|admin)",
            },
        ]

    async def initialize(self, saved_state: Dict[str, Any]):
        """Initialize mode with saved state"""
        if saved_state:
            self.state.update(saved_state)
            logger.info("Adaptive mode initialized with saved state")
        else:
            logger.info("Adaptive mode initialized with default state")

    async def get_state(self) -> Dict[str, Any]:
        """Get current mode state for saving"""
        return self.state.copy()

    async def get_status(self) -> Dict[str, Any]:
        """Get current mode status"""
        return {
            "mode": "adaptive",
            "assignment_preferences": len(self.state.get("assignment_preferences", {})),
            "blocked_tasks": len(self.state.get("blocked_tasks", [])),
        }

    async def find_optimal_task_for_agent(
        self,
        agent_id: str,
        agent_skills: List[str],
        available_tasks: List[Task],
        assigned_tasks: Dict[str, Task],
    ) -> Optional[Task]:
        """
        Find optimal task respecting dependencies and preventing illogical assignments

        Args:
            agent_id: ID of the agent requesting work
            agent_skills: Skills/capabilities of the agent
            available_tasks: Tasks available for assignment
            assigned_tasks: Currently assigned tasks (agent_id -> task)

        Returns:
            Best task for the agent or None
        """
        logger.info(
            f"Finding optimal task for agent {agent_id} with {len(available_tasks)} available tasks"
        )

        # Filter out tasks that are blocked by dependencies
        unblocked_tasks = await self._filter_unblocked_tasks(
            available_tasks, assigned_tasks
        )

        if not unblocked_tasks:
            logger.info("No unblocked tasks available")
            return None

        # Score tasks based on multiple factors
        scored_tasks = []
        for task in unblocked_tasks:
            score = await self._calculate_task_score(
                task=task,
                agent_id=agent_id,
                agent_skills=agent_skills,
                available_tasks=available_tasks,
            )
            scored_tasks.append((task, score))

        # Sort by score (highest first)
        scored_tasks.sort(key=lambda x: x[1], reverse=True)

        if scored_tasks:
            best_task, best_score = scored_tasks[0]
            logger.info(f"Selected task '{best_task.name}' with score {best_score:.2f}")
            return best_task

        return None

    async def _filter_unblocked_tasks(
        self, tasks: List[Task], assigned_tasks: Dict[str, Task]
    ) -> List[Task]:
        """
        Filter tasks to only include those not blocked by dependencies

        This is the core logic that prevents "Deploy to production" from being
        assigned before development is complete.
        """
        unblocked_tasks = []

        for task in tasks:
            if await self._is_task_unblocked(task, tasks, assigned_tasks):
                unblocked_tasks.append(task)
            else:
                logger.debug(f"Task '{task.name}' is blocked by dependencies")

        return unblocked_tasks

    async def _is_task_unblocked(
        self, task: Task, all_tasks: List[Task], assigned_tasks: Dict[str, Task]
    ) -> bool:
        """
        Check if a task is unblocked and ready for assignment

        Returns False for illogical assignments like deployment before development
        """
        # Check explicit dependencies first
        if task.dependencies:
            for dep_id in task.dependencies:
                dep_task = next((t for t in all_tasks if t.id == dep_id), None)
                if dep_task and dep_task.status != TaskStatus.DONE:
                    logger.debug(
                        f"Task '{task.name}' blocked by incomplete dependency '{dep_task.name}'"
                    )
                    return False

        # Check logical dependency patterns
        task_text = f"{task.name} {task.description or ''}".lower()

        for pattern in self.LOGICAL_DEPENDENCY_PATTERNS:
            blocking_pattern = pattern["pattern"]
            blocked_pattern = pattern["blocks_until_complete"]

            # If this task matches a blocked pattern
            import re

            if re.search(blocked_pattern, task_text):
                # Check if any blocking tasks are incomplete
                for other_task in all_tasks:
                    other_text = (
                        f"{other_task.name} {other_task.description or ''}".lower()
                    )

                    if (
                        re.search(blocking_pattern, other_text)
                        and other_task.status != TaskStatus.DONE
                        and other_task.id != task.id
                    ):
                        logger.info(
                            f"Task '{task.name}' blocked by logical dependency: "
                            f"'{other_task.name}' must complete first"
                        )
                        return False

        # Check for obvious illogical patterns
        if await self._is_obviously_illogical(task, all_tasks):
            return False

        return True

    async def _is_obviously_illogical(self, task: Task, all_tasks: List[Task]) -> bool:
        """
        Check for obviously illogical task assignments

        This prevents the core problem: deploying before building
        """
        task_lower = task.name.lower()

        # Deployment tasks
        if any(
            word in task_lower for word in ["deploy", "production", "release", "launch"]
        ):
            # Check if there are any incomplete implementation tasks
            for other_task in all_tasks:
                other_lower = other_task.name.lower()
                if (
                    any(
                        word in other_lower
                        for word in ["implement", "build", "create", "develop"]
                    )
                    and other_task.status != TaskStatus.DONE
                    and other_task.id != task.id
                ):
                    logger.warning(
                        f"Blocking deployment task '{task.name}' - implementation task "
                        f"'{other_task.name}' is not complete"
                    )
                    return True

        # Testing tasks
        if any(word in task_lower for word in ["test", "qa", "quality"]):
            # Check if there are any incomplete implementation tasks for the same component
            for other_task in all_tasks:
                other_lower = other_task.name.lower()
                if (
                    any(
                        word in other_lower for word in ["implement", "build", "create"]
                    )
                    and other_task.status != TaskStatus.DONE
                    and self._tasks_related(task, other_task)
                ):
                    logger.info(
                        f"Blocking test task '{task.name}' - related implementation "
                        f"'{other_task.name}' is not complete"
                    )
                    return True

        return False

    def _tasks_related(self, task1: Task, task2: Task) -> bool:
        """Check if two tasks are related (same component/feature)"""
        # Simple heuristic: check for common words in task names
        words1 = set(task1.name.lower().split())
        words2 = set(task2.name.lower().split())

        # Remove common words
        common_stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        words1 -= common_stopwords
        words2 -= common_stopwords

        # If they share significant words, they're probably related
        intersection = words1 & words2
        return (
            len(intersection) >= 1
            and len(intersection) >= min(len(words1), len(words2)) * 0.3
        )

    async def _calculate_task_score(
        self,
        task: Task,
        agent_id: str,
        agent_skills: List[str],
        available_tasks: List[Task],
    ) -> float:
        """
        Calculate a score for how well a task matches an agent

        Higher score = better match
        """
        score = 0.0

        # Skill matching (40% of score)
        skill_score = self._calculate_skill_match(task, agent_skills)
        score += skill_score * 0.4

        # Priority weight (30% of score)
        priority_scores = {
            Priority.LOW: 0.2,
            Priority.MEDIUM: 0.5,
            Priority.HIGH: 0.8,
            Priority.URGENT: 1.0,
        }
        score += priority_scores.get(task.priority, 0.5) * 0.3

        # Prefer tasks that unblock others (20% of score)
        unblocking_score = self._calculate_unblocking_value(task, available_tasks)
        score += unblocking_score * 0.2

        # Agent preference (10% of score)
        preference_score = self._get_agent_preference_score(agent_id, task)
        score += preference_score * 0.1

        return score

    def _calculate_skill_match(self, task: Task, agent_skills: List[str]) -> float:
        """Calculate how well agent skills match task requirements"""
        if not agent_skills:
            return 0.5  # Neutral score if no skills known

        # Extract skill indicators from task
        task_text = (
            f"{task.name} {task.description or ''} {' '.join(task.labels)}".lower()
        )

        skill_keywords = {
            "python": ["python", "django", "flask", "fastapi"],
            "javascript": ["javascript", "js", "node", "react", "vue", "angular"],
            "frontend": ["frontend", "ui", "css", "html", "react", "vue", "angular"],
            "backend": ["backend", "api", "server", "database", "db"],
            "devops": ["devops", "docker", "ci", "cd", "deploy", "infrastructure"],
            "testing": ["test", "qa", "quality", "junit", "pytest"],
            "database": ["database", "sql", "mysql", "postgresql", "mongodb"],
            "mobile": ["mobile", "ios", "android", "react-native", "flutter"],
        }

        # Count matching skills
        matches = 0
        total_possible = 0

        for skill in agent_skills:
            skill_lower = skill.lower()
            total_possible += 1

            # Direct skill match
            if skill_lower in task_text:
                matches += 1
                continue

            # Keyword match
            if skill_lower in skill_keywords:
                for keyword in skill_keywords[skill_lower]:
                    if keyword in task_text:
                        matches += 1
                        break

        return matches / max(total_possible, 1)

    def _calculate_unblocking_value(
        self, task: Task, available_tasks: List[Task]
    ) -> float:
        """Calculate how many other tasks this task would unblock"""
        if not task.id:
            return 0.0

        # Count tasks that depend on this one
        dependent_count = 0
        for other_task in available_tasks:
            if task.id in other_task.dependencies:
                dependent_count += 1

        # Normalize by total tasks
        if available_tasks:
            return dependent_count / len(available_tasks)

        return 0.0

    def _get_agent_preference_score(self, agent_id: str, task: Task) -> float:
        """Get preference score based on agent's history"""
        preferences = self.state.get("assignment_preferences", {}).get(agent_id, {})

        # Simple preference based on task labels
        score = 0.0
        for label in task.labels:
            if label in preferences:
                score += preferences[label] * 0.1

        return min(score, 1.0)  # Cap at 1.0

    async def record_assignment_outcome(
        self, agent_id: str, task: Task, outcome: str, feedback: Optional[str] = None
    ):
        """
        Record the outcome of a task assignment for learning

        Args:
            agent_id: Agent who worked on the task
            task: Task that was assigned
            outcome: 'completed', 'blocked', 'abandoned'
            feedback: Optional feedback from agent
        """
        # Update agent preferences based on outcome
        if agent_id not in self.state["assignment_preferences"]:
            self.state["assignment_preferences"][agent_id] = {}

        preferences = self.state["assignment_preferences"][agent_id]

        # Adjust preferences based on outcome
        weight_change = {"completed": 0.1, "blocked": -0.05, "abandoned": -0.1}.get(
            outcome, 0
        )

        for label in task.labels:
            if label not in preferences:
                preferences[label] = 0.5
            preferences[label] = max(0, min(1, preferences[label] + weight_change))

        logger.info(
            f"Recorded {outcome} outcome for agent {agent_id} on task '{task.name}'"
        )

    async def get_blocking_analysis(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Analyze what tasks are blocking others

        Returns:
            Analysis of blocking relationships
        """
        blocking_analysis = {
            "blocked_tasks": [],
            "blocking_tasks": [],
            "dependency_chains": [],
            "ready_tasks": [],
        }

        # Group tasks by status
        todo_tasks = [t for t in tasks if t.status == TaskStatus.TODO]
        [t for t in tasks if t.status == TaskStatus.DONE]

        for task in todo_tasks:
            if not await self._is_task_unblocked(task, tasks, {}):
                # Find what's blocking it
                blockers = []

                # Check explicit dependencies
                for dep_id in task.dependencies:
                    dep_task = next((t for t in tasks if t.id == dep_id), None)
                    if dep_task and dep_task.status != TaskStatus.DONE:
                        blockers.append(
                            {
                                "type": "explicit_dependency",
                                "blocking_task": dep_task.name,
                                "blocking_task_id": dep_task.id,
                            }
                        )

                # Check logical dependencies
                task_text = f"{task.name} {task.description or ''}".lower()
                import re

                for pattern in self.LOGICAL_DEPENDENCY_PATTERNS:
                    if re.search(pattern["blocks_until_complete"], task_text):
                        for other_task in tasks:
                            other_text = f"{other_task.name} {other_task.description or ''}".lower()
                            if (
                                re.search(pattern["pattern"], other_text)
                                and other_task.status != TaskStatus.DONE
                            ):
                                blockers.append(
                                    {
                                        "type": "logical_dependency",
                                        "blocking_task": other_task.name,
                                        "blocking_task_id": other_task.id,
                                        "reason": f"Must complete {pattern['pattern']} before {pattern['blocks_until_complete']}",
                                    }
                                )

                if blockers:
                    blocking_analysis["blocked_tasks"].append(
                        {"task": task.name, "task_id": task.id, "blocked_by": blockers}
                    )
            else:
                blocking_analysis["ready_tasks"].append(
                    {
                        "task": task.name,
                        "task_id": task.id,
                        "priority": task.priority.value,
                    }
                )

        return blocking_analysis
