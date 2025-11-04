"""
Dependency Inference Engine for Marcus Phase 2.

Smart dependency detection to prevent illogical task assignments like
"Deploy to production" before development is complete.
"""

import logging
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from src.core.models import Task, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class DependencyPattern:
    """Pattern for inferring dependencies."""

    name: str
    description: str
    condition_pattern: str  # Regex pattern to match dependent task
    dependency_pattern: str  # Regex pattern to match dependency task
    confidence: float
    mandatory: bool  # Whether this dependency is strictly required


@dataclass
class InferredDependency:
    """Inferred dependency between tasks."""

    dependent_task_id: str
    dependency_task_id: str
    dependency_type: str  # 'hard', 'soft', 'logical'
    confidence: float
    reasoning: str
    source: (
        str  # Source of dependency: pattern_matching, prd_bundled_design, manual, etc.
    )


@dataclass
class DependencyGraph:
    """Graph representation of task dependencies."""

    nodes: Dict[str, Task]
    edges: List[InferredDependency]
    adjacency_list: Dict[str, List[str]]
    reverse_adjacency: Dict[str, List[str]]

    def has_cycle(self) -> bool:
        """Check if the dependency graph has cycles."""
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            if node_id in rec_stack:
                return True
            if node_id in visited:
                return False

            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in self.adjacency_list.get(node_id, []):
                if dfs(neighbor):
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    def get_critical_path(self) -> List[str]:
        """Get the critical path (longest dependency chain)."""
        # Topological sort to find longest path
        in_degree: Dict[str, int] = defaultdict(int)
        for node_id in self.nodes:
            for dep in self.adjacency_list.get(node_id, []):
                in_degree[dep] += 1

        # Initialize distances
        distances: Dict[str, float] = {node_id: 0.0 for node_id in self.nodes}

        # BFS-like approach for longest path
        queue = deque([node_id for node_id in self.nodes if in_degree[node_id] == 0])

        while queue:
            current = queue.popleft()

            for neighbor in self.adjacency_list.get(current, []):
                # Calculate distance based on estimated hours
                current_task = self.nodes[current]
                new_distance = distances[current] + (current_task.estimated_hours or 1)

                if new_distance > distances[neighbor]:
                    distances[neighbor] = new_distance

                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Find path to node with maximum distance
        # Handle empty task graph case
        if not distances:
            return []

        max(distances.values())
        end_node = max(distances.items(), key=lambda x: x[1])[0]

        # Reconstruct path
        path = []
        current_node: Optional[str] = end_node

        while current_node:
            path.append(current_node)
            # Find predecessor with maximum distance
            predecessors = self.reverse_adjacency.get(current_node, [])
            if predecessors:
                current_node = max(predecessors, key=lambda p: distances[p])
            else:
                current_node = None

        path.reverse()
        return path


class DependencyInferer:
    """Infers dependencies between tasks to prevent illogical assignments."""

    def __init__(self) -> None:
        # Core dependency patterns that prevent illogical assignments
        self.dependency_patterns = [
            # Setup/Configuration comes before everything
            DependencyPattern(
                name="setup_blocks_all",
                description="Setup tasks must complete before development",
                condition_pattern=r"(implement|build|create|develop|test|deploy)",
                dependency_pattern=r"(setup|init|configure|install|scaffold)",
                confidence=0.95,
                mandatory=True,
            ),
            # Design comes before implementation
            # (unified pattern with specific task prefixes)
            DependencyPattern(
                name="design_before_implementation",
                description="Design must complete before implementation",
                condition_pattern=r"\b(implement|build|create|code|develop)\b",
                dependency_pattern=r"\b(design|architect|plan|wireframe|spec)\b",
                confidence=0.95,
                mandatory=True,
            ),
            # Models/Backend before Frontend
            DependencyPattern(
                name="backend_before_frontend",
                description="Backend/API must exist before frontend integration",
                condition_pattern=r"\b(frontend|ui|client|interface)\b",
                dependency_pattern=r"\b(backend|api|server|endpoint|service)\b",
                confidence=0.85,
                mandatory=False,
            ),
            # Implementation before testing
            DependencyPattern(
                name="implementation_before_testing",
                description="Implementation must complete before testing",
                condition_pattern=r"\b(test|qa|quality|verify|testing)\b",
                dependency_pattern=r"\b(implement|build|create|develop)\b",
                confidence=0.95,
                mandatory=True,
            ),
            # Testing before deployment
            DependencyPattern(
                name="testing_before_deployment",
                description="Testing must complete before deployment",
                condition_pattern=r"\b(deploy|release|launch|production)\b",
                dependency_pattern=r"\b(test|qa|quality|verify|testing)\b",
                confidence=0.95,
                mandatory=True,
            ),
            # Database schema before models
            DependencyPattern(
                name="schema_before_models",
                description="Database schema must be designed before models",
                condition_pattern=r"(model|entity|orm)",
                dependency_pattern=r"(schema|database.*design)",
                confidence=0.85,
                mandatory=False,
            ),
            # Authentication before authorization
            DependencyPattern(
                name="auth_before_authz",
                description="Authentication must exist before authorization",
                condition_pattern=r"(authorization|permission|role|access)",
                dependency_pattern=r"(authentication|login|signin)",
                confidence=0.90,
                mandatory=True,
            ),
            # Basic features before advanced features
            DependencyPattern(
                name="basic_before_advanced",
                description="Basic CRUD before advanced features",
                condition_pattern=r"(advanced|complex|optimization|caching)",
                dependency_pattern=r"(basic|crud|create|read|update|delete)",
                confidence=0.75,
                mandatory=False,
            ),
            # Component-specific dependencies
            DependencyPattern(
                name="component_implementation_order",
                description="Component implementation before component testing",
                condition_pattern=r"test",
                dependency_pattern=r"(implement|build|create|develop)",
                confidence=0.90,
                mandatory=True,
            ),
        ]

        # Technology-specific patterns
        self.tech_patterns = {
            "react": [
                {
                    "condition": r"component.*test",
                    "dependency": r"component.*implement",
                    "confidence": 0.90,
                }
            ],
            "database": [
                {
                    "condition": r"migration",
                    "dependency": r"schema.*design",
                    "confidence": 0.85,
                }
            ],
        }

    async def infer_dependencies(self, tasks: List[Task]) -> DependencyGraph:
        """
        Infer dependencies from task names and descriptions.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to analyze

        Returns
        -------
        DependencyGraph
            Dependency graph with inferred dependencies
        """
        logger.info(f"Inferring dependencies for {len(tasks)} tasks")

        # Create nodes mapping
        nodes = {task.id: task for task in tasks}

        # Infer dependencies using patterns
        inferred_dependencies = []

        for dependent_task in tasks:
            for dependency_task in tasks:
                if dependent_task.id == dependency_task.id:
                    continue

                # Check each pattern
                for pattern in self.dependency_patterns:
                    dependency = self._check_pattern(
                        dependent_task, dependency_task, pattern
                    )
                    if dependency:
                        inferred_dependencies.append(dependency)

        # Remove duplicates and conflicts
        cleaned_dependencies = self._clean_dependencies(inferred_dependencies)

        # Build adjacency lists
        adjacency_list = defaultdict(list)
        reverse_adjacency = defaultdict(list)

        for dep in cleaned_dependencies:
            adjacency_list[dep.dependency_task_id].append(dep.dependent_task_id)
            reverse_adjacency[dep.dependent_task_id].append(dep.dependency_task_id)

        # Create dependency graph
        graph = DependencyGraph(
            nodes=nodes,
            edges=cleaned_dependencies,
            adjacency_list=dict(adjacency_list),
            reverse_adjacency=dict(reverse_adjacency),
        )

        # Check for cycles and resolve if necessary
        if graph.has_cycle():
            logger.warning("Cycle detected in dependency graph, attempting to resolve")
            graph = self._resolve_cycles(graph)

        logger.info(f"Inferred {len(cleaned_dependencies)} dependencies")

        return graph

    def _check_pattern(
        self, dependent_task: Task, dependency_task: Task, pattern: DependencyPattern
    ) -> Optional[InferredDependency]:
        """Check if a dependency pattern matches between two tasks."""
        # Get task text for analysis
        dependent_text = (
            f"{dependent_task.name} {dependent_task.description or ''}".lower()
        )
        dependency_text = (
            f"{dependency_task.name} {dependency_task.description or ''}".lower()
        )

        # Check if dependent task matches the condition pattern
        if not re.search(pattern.condition_pattern, dependent_text):
            return None

        # Check if dependency task matches the dependency pattern
        if not re.search(pattern.dependency_pattern, dependency_text):
            return None

        # Additional logical checks
        if not self._is_logical_dependency(dependent_task, dependency_task, pattern):
            return None

        # Create dependency
        dependency_type = "hard" if pattern.mandatory else "soft"

        return InferredDependency(
            dependent_task_id=dependent_task.id,
            dependency_task_id=dependency_task.id,
            dependency_type=dependency_type,
            confidence=pattern.confidence,
            reasoning=f"Pattern: {pattern.description}",
            source="pattern_matching",
        )

    def _is_logical_dependency(
        self, dependent_task: Task, dependency_task: Task, pattern: DependencyPattern
    ) -> bool:
        """Perform additional logical checks for dependency validity."""
        # Don't create dependencies between completed tasks and new tasks
        if (
            dependency_task.status == TaskStatus.DONE
            and dependent_task.status == TaskStatus.TODO
        ):
            return False

        # Check for component/feature matching
        dependent_words = set(dependent_task.name.lower().split())
        dependency_words = set(dependency_task.name.lower().split())

        # Remove common stop words
        stop_words = {
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
        dependent_words -= stop_words
        dependency_words -= stop_words

        # Must share at least one meaningful word for component-specific patterns
        if pattern.name == "component_implementation_order":
            intersection = dependent_words & dependency_words
            if len(intersection) == 0:
                return False

        # Prevent circular dependencies by enforcing logical task ordering
        dependent_task_type = self._classify_task_type(dependent_task.name)
        dependency_task_type = self._classify_task_type(dependency_task.name)

        # Define logical task ordering: design < implementation < testing < deployment
        task_order = {
            "design": 1,
            "implementation": 2,
            "testing": 3,
            "deployment": 4,
            "other": 2.5,  # Default to implementation level
        }

        dependent_order = task_order.get(dependent_task_type, task_order["other"])
        dependency_order = task_order.get(dependency_task_type, task_order["other"])

        # Dependency task should come before dependent task in logical order
        if dependency_order >= dependent_order:
            return False

        # Check temporal logic - dependency should typically come before dependent
        if (
            hasattr(dependency_task, "created_at")
            and hasattr(dependent_task, "created_at")
            and dependency_task.created_at
            and dependent_task.created_at
        ):
            # If dependency was created much later, it might not be a real dependency
            time_diff = (dependency_task.created_at - dependent_task.created_at).days
            if time_diff > 7:  # More than a week later
                return False

        return True

    def _classify_task_type(self, task_name: str) -> str:
        """
        Classify task into type based on name patterns.

        Returns: 'design', 'implementation', 'testing', 'deployment', or 'other'
        """
        name_lower = task_name.lower()

        # Design/planning tasks
        if any(
            word in name_lower
            for word in [
                "design",
                "plan",
                "architect",
                "wireframe",
                "spec",
                "research",
                "analyze",
            ]
        ):
            return "design"

        # Testing tasks
        if any(
            word in name_lower
            for word in ["test", "qa", "quality", "verify", "validation", "check"]
        ):
            return "testing"

        # Deployment tasks
        if any(
            word in name_lower
            for word in ["deploy", "release", "launch", "production", "publish"]
        ):
            return "deployment"

        # Implementation tasks (check last since many contain these words)
        if any(
            word in name_lower
            for word in ["implement", "build", "create", "develop", "code", "write"]
        ):
            return "implementation"

        return "other"

    def _clean_dependencies(
        self, dependencies: List[InferredDependency]
    ) -> List[InferredDependency]:
        """Remove duplicate and conflicting dependencies."""
        # Group by task pair
        dependency_groups = defaultdict(list)
        for dep in dependencies:
            key = (dep.dependent_task_id, dep.dependency_task_id)
            dependency_groups[key].append(dep)

        # Keep the highest confidence dependency for each pair
        cleaned = []
        for deps in list(dependency_groups.values()):
            best_dep = max(deps, key=lambda d: d.confidence)
            cleaned.append(best_dep)

        # Remove circular dependencies
        cleaned = self._remove_circular_dependencies(cleaned)

        # Remove transitive dependencies that are implied by other dependencies
        # (A -> B -> C implies A -> C, so we can remove direct A -> C)
        cleaned = self._remove_transitive_dependencies(cleaned)

        return cleaned

    def _remove_circular_dependencies(
        self, dependencies: List[InferredDependency]
    ) -> List[InferredDependency]:
        """
        Remove circular dependencies by breaking cycles.

        Strategy: Build a graph, detect cycles, and remove the lowest confidence
        dependency from each cycle to break it.
        """
        # Build adjacency list
        graph = defaultdict(list)
        dep_map = {}  # (from_id, to_id) -> dependency

        for dep in dependencies:
            graph[dep.dependency_task_id].append(dep.dependent_task_id)
            dep_map[(dep.dependency_task_id, dep.dependent_task_id)] = dep

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        cycles_found = []

        def detect_cycle(node: str, path: List[str]) -> Optional[List[str]]:
            if node in rec_stack:
                # Found cycle - extract it
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles_found.append(cycle)
                return cycle

            if node in visited:
                return None

            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph[node]:
                if detect_cycle(neighbor, path + [neighbor]):
                    break  # Only need to find one cycle per path

            rec_stack.remove(node)
            return None

        # Find cycles
        for node in list(
            graph.keys()
        ):  # Convert to list to avoid dictionary size change during iteration
            if node not in visited:
                detect_cycle(node, [node])

        # Remove lowest confidence dependency from each cycle
        dependencies_to_remove = set()

        for cycle in cycles_found:
            if len(cycle) < 2:
                continue

            logger.warning(f"Detected circular dependency: {' -> '.join(cycle)}")

            # Find the lowest confidence dependency in the cycle
            cycle_deps = []
            for i in range(len(cycle) - 1):
                from_task = cycle[i]
                to_task = cycle[i + 1]
                if (from_task, to_task) in dep_map:
                    cycle_deps.append(dep_map[(from_task, to_task)])

            if cycle_deps:
                # Remove the dependency with lowest confidence
                weakest_dep = min(cycle_deps, key=lambda d: d.confidence)
                dependencies_to_remove.add(
                    (weakest_dep.dependency_task_id, weakest_dep.dependent_task_id)
                )
                logger.info(
                    f"Breaking circular dependency by removing: "
                    f"{weakest_dep.dependency_task_id} -> "
                    f"{weakest_dep.dependent_task_id} "
                    f"(confidence: {weakest_dep.confidence})"
                )

        # Filter out the dependencies we decided to remove
        cleaned = []
        for dep in dependencies:
            key = (dep.dependency_task_id, dep.dependent_task_id)
            if key not in dependencies_to_remove:
                cleaned.append(dep)

        logger.info(
            f"Removed {len(dependencies) - len(cleaned)} dependencies to "
            f"break circular references"
        )
        return cleaned

    def _remove_transitive_dependencies(
        self, dependencies: List[InferredDependency]
    ) -> List[InferredDependency]:
        """Remove dependencies that are implied by transitive relationships."""
        # Build adjacency map
        adjacency = defaultdict(set)
        dep_map = {}

        for dep in dependencies:
            adjacency[dep.dependency_task_id].add(dep.dependent_task_id)
            dep_map[(dep.dependency_task_id, dep.dependent_task_id)] = dep

        # Find transitive closures
        def find_transitive_paths(start: str, end: str, visited: Set[str]) -> bool:
            if start == end:
                return True
            if start in visited:
                return False

            visited.add(start)
            for neighbor in adjacency[start]:
                if find_transitive_paths(neighbor, end, visited.copy()):
                    return True

            return False

        # Keep only non-transitive dependencies
        filtered = []
        for dep in dependencies:
            # Check if there's an indirect path
            has_indirect_path = False
            for intermediate in list(adjacency):
                if (
                    intermediate != dep.dependency_task_id
                    and intermediate != dep.dependent_task_id
                ):
                    path_to_intermediate = find_transitive_paths(
                        dep.dependency_task_id, intermediate, set()
                    )
                    path_from_intermediate = find_transitive_paths(
                        intermediate, dep.dependent_task_id, set()
                    )

                    if path_to_intermediate and path_from_intermediate:
                        has_indirect_path = True
                        break

            # Keep if no indirect path or if it's a mandatory dependency
            if not has_indirect_path or dep.dependency_type == "hard":
                filtered.append(dep)

        return filtered

    def _resolve_cycles(self, graph: DependencyGraph) -> DependencyGraph:
        """Resolve cycles in dependency graph by removing lowest confidence edges."""
        while graph.has_cycle():
            # Find cycles using DFS
            cycles = self._find_cycles(graph)

            if not cycles:
                break

            # Remove the lowest confidence edge from the first cycle
            cycle = cycles[0]
            min_confidence = float("inf")
            edge_to_remove = None

            for i in range(len(cycle)):
                current = cycle[i]
                next_node = cycle[(i + 1) % len(cycle)]

                # Find the edge
                for edge in graph.edges:
                    if (
                        edge.dependency_task_id == current
                        and edge.dependent_task_id == next_node
                    ):
                        if edge.confidence < min_confidence:
                            min_confidence = edge.confidence
                            edge_to_remove = edge
                        break

            if edge_to_remove:
                graph.edges.remove(edge_to_remove)

                # Rebuild adjacency lists
                adjacency_list = defaultdict(list)
                reverse_adjacency = defaultdict(list)

                for dep in graph.edges:
                    adjacency_list[dep.dependency_task_id].append(dep.dependent_task_id)
                    reverse_adjacency[dep.dependent_task_id].append(
                        dep.dependency_task_id
                    )

                graph.adjacency_list = dict(adjacency_list)
                graph.reverse_adjacency = dict(reverse_adjacency)

                logger.info(
                    f"Removed edge to break cycle: "
                    f"{edge_to_remove.dependency_task_id} -> "
                    f"{edge_to_remove.dependent_task_id}"
                )
            else:
                break

        return graph

    def _find_cycles(self, graph: DependencyGraph) -> List[List[str]]:
        """Find all cycles in the dependency graph."""
        cycles = []
        visited = set()

        def dfs(node: str, path: List[str], visited_in_path: Set[str]) -> None:
            if node in visited_in_path:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            visited_in_path.add(node)
            path.append(node)

            for neighbor in graph.adjacency_list.get(node, []):
                dfs(neighbor, path.copy(), visited_in_path.copy())

        for node in graph.nodes:
            if node not in visited:
                dfs(node, [], set())

        return cycles

    async def validate_dependencies(self, graph: DependencyGraph) -> Dict[str, Any]:
        """
        Validate dependency graph for correctness.

        Returns
        -------
        Dict[str, Any]
            Validation results with any issues found
        """
        issues = []
        warnings = []

        # Check for cycles
        if graph.has_cycle():
            issues.append("Dependency graph contains cycles")

        # Check for isolated components
        all_nodes = set(graph.nodes.keys())
        connected_nodes = set()

        for edge in graph.edges:
            connected_nodes.add(edge.dependency_task_id)
            connected_nodes.add(edge.dependent_task_id)

        isolated_nodes = all_nodes - connected_nodes
        if isolated_nodes:
            warnings.append(f"{len(isolated_nodes)} tasks have no dependencies")

        # Check for unrealistic dependency chains
        critical_path = graph.get_critical_path()
        if len(critical_path) > 20:
            warnings.append(
                f"Very long dependency chain detected ({len(critical_path)} tasks)"
            )

        # Check for mandatory patterns
        missing_mandatory = []
        for task in list(graph.nodes.values()):
            task_text = f"{task.name} {task.description or ''}".lower()

            # Check if deployment tasks have testing dependencies
            if re.search(r"(deploy|release|launch|production)", task_text):
                has_test_dependency = any(
                    re.search(r"(test|qa|quality)", graph.nodes[dep_id].name.lower())
                    for dep_id in graph.reverse_adjacency.get(task.id, [])
                )
                if not has_test_dependency:
                    missing_mandatory.append(
                        f"Deployment task '{task.name}' missing test dependency"
                    )

        if missing_mandatory:
            issues.extend(missing_mandatory)

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "statistics": {
                "total_tasks": len(graph.nodes),
                "total_dependencies": len(graph.edges),
                "isolated_tasks": len(isolated_nodes),
                "critical_path_length": len(critical_path),
                "has_cycles": graph.has_cycle(),
            },
        }
