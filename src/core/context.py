"""
Context System for Marcus

Provides rich context for task assignments including previous implementations,
dependency awareness, and relevant patterns. Enhances agent effectiveness by
reducing time spent understanding existing code and architectural decisions.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.events import Events, EventTypes
from src.core.models import Priority, Task
from src.core.resilience import with_fallback

logger = logging.getLogger(__name__)

# Optional import for hybrid dependency inference
try:
    from src.intelligence.dependency_inferer_hybrid import HybridDependencyInferer

    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    logger.info(
        "Hybrid dependency inferer not available, using pattern-based inference"
    )


@dataclass
class TaskContext:
    """Complete context for a task assignment"""

    task_id: str
    previous_implementations: Dict[str, Any] = field(default_factory=dict)
    dependent_tasks: List[Dict[str, Any]] = field(default_factory=list)
    related_patterns: List[Dict[str, Any]] = field(default_factory=list)
    architectural_decisions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "previous_implementations": self.previous_implementations,
            "dependent_tasks": self.dependent_tasks,
            "related_patterns": self.related_patterns,
            "architectural_decisions": self.architectural_decisions,
        }


@dataclass
class DependentTask:
    """Information about a task that depends on another"""

    task_id: str
    task_name: str
    expected_interface: str
    dependency_type: str = "functional"  # functional, data, temporal


@dataclass
class Decision:
    """An architectural decision made during development"""

    decision_id: str
    task_id: str
    agent_id: str
    timestamp: datetime
    what: str  # What was decided
    why: str  # Why it was decided
    impact: str  # Impact on other components

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "decision_id": self.decision_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "what": self.what,
            "why": self.why,
            "impact": self.impact,
        }


class Context:
    """
    Manages context for task assignments.

    Features:
    - Tracks implementations from completed tasks
    - Identifies dependent tasks
    - Stores architectural decisions
    - Provides rich context for new assignments
    - Optional persistence for long-term storage
    """

    def __init__(
        self,
        events: Optional[Events] = None,
        persistence: Optional[Any] = None,
        use_hybrid_inference: bool = True,
        ai_engine: Optional[Any] = None,
    ):
        """
        Initialize the Context system.

        Args:
            events: Optional Events system for integration
            persistence: Optional Persistence instance for storing context
            use_hybrid_inference: Whether to use hybrid dependency inference if available
            ai_engine: Optional AI engine for hybrid inference
        """
        self.events = events
        self.persistence = persistence
        self.implementations: Dict[str, Dict[str, Any]] = (
            {}
        )  # task_id -> implementation details
        self.dependencies: Dict[str, List[DependentTask]] = (
            {}
        )  # task_id -> dependent tasks
        self.decisions: List[Decision] = []
        self.patterns: Dict[str, List[Dict[str, Any]]] = {}  # pattern_type -> examples
        self._decision_counter = 0
        self.default_infer_dependencies = (
            True  # Default setting for dependency inference
        )

        # Set up dependency inference strategy
        self.hybrid_inferer = None
        if use_hybrid_inference and HYBRID_AVAILABLE and ai_engine:
            self.hybrid_inferer = HybridDependencyInferer(ai_engine)
            logger.info("Using hybrid dependency inference for better accuracy")

        # Load persisted data if available
        if self.persistence:
            asyncio.create_task(self._load_persisted_data())

    async def _load_persisted_data(self) -> None:
        """Load persisted decisions from storage"""
        try:
            # Load recent decisions
            if self.persistence:
                persisted_decisions = await self.persistence.get_decisions(limit=100)
                for decision in persisted_decisions:
                    if decision not in self.decisions:
                        self.decisions.append(decision)

            # Update decision counter
            if self.decisions:
                max_id = max(int(d.decision_id.split("_")[1]) for d in self.decisions)
                self._decision_counter = max_id

            logger.info(f"Loaded {len(persisted_decisions)} decisions from persistence")
        except Exception as e:
            logger.error(f"Failed to load persisted data: {e}")

    async def add_implementation(
        self, task_id: str, implementation: Dict[str, Any]
    ) -> None:
        """
        Add implementation details from a completed task.

        Args:
            task_id: ID of the completed task
            implementation: Details about the implementation (APIs, models, patterns)
        """
        self.implementations[task_id] = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            **implementation,
        }

        # Persist implementation if available (with graceful degradation)
        if self.persistence:
            await self._persist_implementation_safe(task_id)

        # Extract patterns for future use
        if "patterns" in implementation:
            for pattern in implementation["patterns"]:
                pattern_type = pattern.get("type", "general")
                if pattern_type not in self.patterns:
                    self.patterns[pattern_type] = []
                self.patterns[pattern_type].append(
                    {"task_id": task_id, "pattern": pattern}
                )

        # Emit event if events system is available
        if self.events:
            await self.events.publish(
                EventTypes.IMPLEMENTATION_FOUND,
                "context",
                {"task_id": task_id, "implementation": implementation},
            )

        logger.debug(f"Added implementation context for task {task_id}")

    def add_dependency(self, task_id: str, dependent_task: DependentTask) -> None:
        """
        Record that one task depends on another.

        Args:
            task_id: The task being depended upon
            dependent_task: Information about the dependent task
        """
        if task_id not in self.dependencies:
            self.dependencies[task_id] = []
        self.dependencies[task_id].append(dependent_task)

        logger.debug(
            f"Added dependency: {dependent_task.task_name} depends on {task_id}"
        )

    async def log_decision(
        self, agent_id: str, task_id: str, what: str, why: str, impact: str
    ) -> Decision:
        """
        Log an architectural decision made by an agent.

        Args:
            agent_id: ID of the agent making the decision
            task_id: Current task ID
            what: What was decided
            why: Reasoning behind the decision
            impact: Expected impact on other components

        Returns:
            The logged Decision object
        """
        self._decision_counter += 1
        decision = Decision(
            decision_id=f"dec_{self._decision_counter}_{datetime.now().timestamp()}",
            task_id=task_id,
            agent_id=agent_id,
            timestamp=datetime.now(),
            what=what,
            why=why,
            impact=impact,
        )

        self.decisions.append(decision)

        # Persist decision if persistence is available (with graceful degradation)
        if self.persistence:
            await self._persist_decision_safe(decision)

        # Cross-reference to dependent tasks
        if task_id in self.dependencies:
            for dep_task in self.dependencies[task_id]:
                logger.info(f"Decision affects dependent task: {dep_task.task_name}")

        # Emit event
        if self.events:
            await self.events.publish(
                EventTypes.DECISION_LOGGED, agent_id, decision.to_dict()
            )

        return decision

    async def get_context(
        self, task_id: str, task_dependencies: List[str]
    ) -> TaskContext:
        """
        Get complete context for a task assignment.

        Args:
            task_id: The task being assigned
            task_dependencies: IDs of tasks this task depends on

        Returns:
            Complete context for the task
        """
        context = TaskContext(task_id=task_id)

        # Get implementations from dependencies
        for dep_id in task_dependencies:
            if dep_id in self.implementations:
                context.previous_implementations[dep_id] = self.implementations[dep_id]

        # Get tasks that depend on this one
        if task_id in self.dependencies:
            context.dependent_tasks = [
                {
                    "task_id": dep.task_id,
                    "task_name": dep.task_name,
                    "expected_interface": dep.expected_interface,
                    "dependency_type": dep.dependency_type,
                }
                for dep in self.dependencies[task_id]
            ]

        # Get relevant patterns
        # For now, include all patterns - could be smarter about filtering
        for pattern_type, examples in self.patterns.items():
            context.related_patterns.extend(examples[:3])  # Limit to 3 most recent

        # Get relevant architectural decisions
        relevant_decisions = []
        # Include decisions from dependencies
        for dep_id in task_dependencies:
            relevant_decisions.extend(
                [d.to_dict() for d in self.decisions if d.task_id == dep_id]
            )
        # Include decisions that might affect this task
        for decision in self.decisions:
            if task_id in decision.impact:
                relevant_decisions.append(decision.to_dict())

        context.architectural_decisions = relevant_decisions[-5:]  # Last 5 relevant

        # Emit event
        if self.events:
            await self.events.publish(
                EventTypes.CONTEXT_UPDATED,
                "context",
                {
                    "task_id": task_id,
                    "context_size": {
                        "implementations": len(context.previous_implementations),
                        "dependents": len(context.dependent_tasks),
                        "patterns": len(context.related_patterns),
                        "decisions": len(context.architectural_decisions),
                    },
                },
            )

        return context

    async def analyze_dependencies(
        self, tasks: List[Task], infer_implicit: bool = True
    ) -> Dict[str, List[str]]:
        """
        Analyze task list to identify dependencies (both explicit and implicit).

        Args:
            tasks: List of all tasks
            infer_implicit: Whether to infer implicit dependencies (default: True)

        Returns:
            Mapping of task_id to list of dependent task IDs
        """
        # Use hybrid inferer if available for better accuracy with fewer API calls
        if self.hybrid_inferer and infer_implicit:
            logger.info("Using hybrid dependency inference")
            # Get dependency graph from hybrid inferer
            dep_graph = await self.hybrid_inferer.infer_dependencies(tasks)

            # Convert to our format
            dependency_map: Dict[str, List[str]] = dep_graph.adjacency_list.copy()

            # Also include explicit dependencies
            for task in tasks:
                if task.dependencies:
                    for dep_id in task.dependencies:
                        if dep_id not in dependency_map:
                            dependency_map[dep_id] = []
                        if task.id not in dependency_map[dep_id]:
                            dependency_map[dep_id].append(task.id)

            return dependency_map

        # Fallback to pattern-based inference
        fallback_dependency_map: Dict[str, List[str]] = {}

        # First, map explicit dependencies
        for task in tasks:
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id not in fallback_dependency_map:
                        fallback_dependency_map[dep_id] = []
                    fallback_dependency_map[dep_id].append(task.id)

        # Then, infer implicit dependencies if enabled
        if infer_implicit:
            inferred_count = 0
            for i, task in enumerate(tasks):
                for j, other_task in enumerate(tasks):
                    if i >= j:  # Skip self and already processed pairs
                        continue

                    # Check if task depends on other_task
                    if self._infer_dependency(task, other_task):
                        if other_task.id not in fallback_dependency_map:
                            fallback_dependency_map[other_task.id] = []
                        if task.id not in fallback_dependency_map[other_task.id]:
                            fallback_dependency_map[other_task.id].append(task.id)
                            inferred_count += 1
                            logger.info(
                                f"Inferred: '{task.name}' depends on '{other_task.name}'"
                            )

            if inferred_count > 0:
                logger.info(f"Inferred {inferred_count} implicit dependencies")

        # Check for circular dependencies
        cycles = self._detect_circular_dependencies(fallback_dependency_map, tasks)
        if cycles:
            logger.warning(f"Circular dependencies detected: {cycles}")

        return fallback_dependency_map

    def _infer_dependency(self, task: Task, potential_dependency: Task) -> bool:
        """
        Infer if task depends on potential_dependency using multiple strategies.

        Args:
            task: The task to check
            potential_dependency: The potential dependency

        Returns:
            True if dependency is likely
        """
        # Extract task information
        task_labels = set(label.lower() for label in (task.labels or []))
        task_name_words = set(task.name.lower().split())
        dep_labels = set(label.lower() for label in (potential_dependency.labels or []))
        dep_name_words = set(potential_dependency.name.lower().split())

        logger.debug(
            f"Checking if '{task.name}' depends on '{potential_dependency.name}'"
        )
        logger.debug(f"Task labels: {task_labels}, words: {task_name_words}")
        logger.debug(f"Dep labels: {dep_labels}, words: {dep_name_words}")

        # Strategy 1: Pattern-based rules (enhanced)
        inference_rules = [
            # Frontend depends on backend
            (
                [
                    "frontend",
                    "ui",
                    "client",
                    "react",
                    "vue",
                    "angular",
                    "webapp",
                    "dashboard",
                ],
                ["backend", "api", "server", "endpoint", "rest", "graphql", "service"],
            ),
            # Mobile apps depend on backend
            (
                ["mobile", "ios", "android", "react-native", "flutter", "app"],
                ["backend", "api", "auth", "server", "endpoint"],
            ),
            # Tests depend on implementation
            (
                [
                    "test",
                    "spec",
                    "unittest",
                    "integration-test",
                    "e2e",
                    "qa",
                    "testing",
                ],
                [
                    "implement",
                    "feature",
                    "api",
                    "service",
                    "component",
                    "function",
                    "endpoint",
                ],
            ),
            # Deployment depends on build
            (
                ["deploy", "deployment", "release", "publish", "production", "staging"],
                ["build", "compile", "bundle", "package", "docker", "container"],
            ),
            # Documentation depends on implementation
            (
                ["docs", "documentation", "readme", "guide", "manual", "wiki"],
                ["implement", "feature", "api", "component", "interface", "service"],
            ),
            # Database migrations depend on schema
            (
                ["migration", "migrate", "update-db", "db-change", "alter-table"],
                ["schema", "database", "model", "entity", "table", "orm"],
            ),
            # Integration depends on components
            (
                ["integration", "integrate", "connect", "bridge", "adapter"],
                ["component", "service", "module", "api", "interface", "system"],
            ),
            # Configuration depends on infrastructure
            (
                ["config", "configure", "settings", "environment", "env"],
                ["infrastructure", "setup", "install", "provision", "initialize"],
            ),
            # Security depends on authentication
            (
                ["security", "secure", "protect", "authorize", "permission"],
                ["auth", "authentication", "user", "role", "identity"],
            ),
            # Monitoring depends on deployment
            (
                ["monitor", "monitoring", "metrics", "logging", "observability"],
                ["deploy", "service", "api", "application", "system"],
            ),
        ]

        for dependent_keywords, dependency_keywords in inference_rules:
            if any(
                kw in task_labels or kw in task_name_words for kw in dependent_keywords
            ) and any(
                kw in dep_labels or kw in dep_name_words for kw in dependency_keywords
            ):
                return True

        # Strategy 2: Action-based inference (verb analysis)
        task_action = self._extract_action(task.name)
        dep_action = self._extract_action(potential_dependency.name)

        action_dependencies = {
            "update": ["create", "implement", "build"],
            "test": ["implement", "create", "build"],
            "deploy": ["test", "build", "package"],
            "document": ["implement", "create", "design"],
            "refactor": ["implement", "create"],
            "optimize": ["implement", "measure"],
            "integrate": ["implement", "create", "build"],
            "configure": ["install", "setup", "create"],
        }

        if task_action in action_dependencies:
            if dep_action in action_dependencies[task_action]:
                return True

        # Strategy 3: Entity-based inference (same entity, different actions)
        task_entity = self._extract_entity(task.name)
        dep_entity = self._extract_entity(potential_dependency.name)

        if task_entity and dep_entity and task_entity == dep_entity:
            # Same entity - check if actions have natural order
            action_order = [
                "design",
                "plan",
                "create",
                "implement",
                "build",
                "test",
                "document",
                "deploy",
                "monitor",
            ]

            try:
                task_order = (
                    action_order.index(task_action)
                    if task_action in action_order
                    else -1
                )
                dep_order = (
                    action_order.index(dep_action) if dep_action in action_order else -1
                )

                # If both have known actions and task comes after dependency
                if task_order > dep_order >= 0:
                    return True
            except ValueError:
                pass

        # Special case: API depends on schema/database
        if ("api" in task_labels or "api" in task_name_words) and (
            "schema" in dep_labels
            or "schema" in dep_name_words
            or "database" in dep_labels
            or "database" in dep_name_words
        ):
            logger.info(
                f"Special rule matched: {task.name} depends on {potential_dependency.name}"
            )
            return True

        # Strategy 4: Technical stack dependencies (enhanced)
        tech_dependencies = {
            "frontend": ["api", "backend", "auth", "database", "websocket", "graphql"],
            "mobile": ["api", "backend", "auth", "push-notification", "sync"],
            "cli": ["api", "core", "library", "config", "auth"],
            "api": ["database", "auth", "model", "validation", "middleware"],
            "auth": ["database", "user", "model", "session", "token"],
            "admin": ["api", "auth", "role", "permission", "user-management"],
            "analytics": ["database", "api", "data", "aggregation", "metrics"],
            "notification": ["queue", "email", "sms", "push", "template"],
            "payment": ["api", "security", "validation", "gateway", "transaction"],
            "search": ["index", "database", "api", "filter", "ranking"],
        }

        for tech, deps in tech_dependencies.items():
            if tech in task_labels or tech in task_name_words:
                if any(d in dep_labels or d in dep_name_words for d in deps):
                    return True

        # Strategy 5: Cross-functional dependencies
        cross_functional_patterns = [
            # Admin interfaces need user management
            (["admin", "management", "dashboard"], ["user", "role", "permission"]),
            # Real-time features need websockets
            (
                ["realtime", "live", "chat", "collaboration"],
                ["websocket", "pubsub", "stream"],
            ),
            # File handling needs storage
            (
                ["upload", "file", "document", "image"],
                ["storage", "s3", "cdn", "bucket"],
            ),
            # Email features need templates
            (["email", "mail", "notification"], ["template", "smtp", "mailer"]),
            # Search needs indexing
            (["search", "find", "query"], ["index", "elasticsearch", "lucene"]),
            # Reports need data aggregation
            (["report", "analytics", "dashboard"], ["aggregation", "query", "data"]),
            # Import/export needs data processing
            (["import", "export", "etl"], ["process", "transform", "validate"]),
        ]

        for feature_keywords, required_keywords in cross_functional_patterns:
            if any(
                kw in task_labels or kw in task_name_words for kw in feature_keywords
            ):
                if any(
                    kw in dep_labels or kw in dep_name_words for kw in required_keywords
                ):
                    return True

        # Strategy 6: Semantic similarity for compound tasks
        # If tasks share significant keywords, they might be related
        common_words = task_name_words & dep_name_words
        # Filter out common stop words
        stop_words = {"the", "a", "an", "and", "or", "for", "to", "in", "of", "with"}
        meaningful_common = common_words - stop_words

        # If they share 2+ meaningful words, consider it a potential dependency
        if len(meaningful_common) >= 2:
            # Check if the dependency comes "before" in the development flow
            if dep_action in [
                "create",
                "implement",
                "build",
                "setup",
            ] and task_action in ["test", "use", "integrate", "deploy"]:
                logger.info(
                    f"Semantic similarity: '{task.name}' likely depends on '{potential_dependency.name}'"
                )
                return True

        return False

    def _extract_action(self, task_name: str) -> Optional[str]:
        """Extract the primary action verb from a task name"""
        words = task_name.lower().split()
        common_actions = {
            "create",
            "build",
            "implement",
            "design",
            "test",
            "deploy",
            "update",
            "refactor",
            "optimize",
            "document",
            "integrate",
            "configure",
            "setup",
            "install",
            "add",
            "remove",
            "fix",
        }

        for word in words:
            if word in common_actions:
                return word
        return None

    def _extract_entity(self, task_name: str) -> Optional[str]:
        """Extract the primary entity/component from a task name"""
        # Remove common actions to find entity
        words = task_name.lower().split()
        action_words = {
            "create",
            "build",
            "implement",
            "design",
            "test",
            "deploy",
            "update",
            "refactor",
            "optimize",
            "document",
            "integrate",
            "configure",
            "setup",
            "install",
            "add",
            "remove",
            "fix",
            "for",
        }

        entity_words = [w for w in words if w not in action_words and len(w) > 2]

        # Common entities to look for
        common_entities = {
            "api",
            "database",
            "auth",
            "user",
            "login",
            "dashboard",
            "payment",
            "notification",
            "email",
            "search",
            "report",
        }

        for word in entity_words:
            if word in common_entities:
                return word

        # Return first non-action word as entity
        return entity_words[0] if entity_words else None

    def _detect_circular_dependencies(
        self, dependency_map: Dict[str, List[str]], tasks: List[Task]
    ) -> List[List[str]]:
        """
        Detect circular dependencies using depth-first search.

        Args:
            dependency_map: Mapping of task_id to dependent task_ids
            tasks: List of all tasks

        Returns:
            List of circular dependency chains
        """
        # Build task lookup for names
        task_lookup = {task.id: task.name for task in tasks}

        # Track visited nodes and recursion stack
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(task_id: str, path: List[str]) -> None:
            """Depth-first search to find cycles"""
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            # Check all dependencies
            if task_id in dependency_map:
                for dependent_id in dependency_map[task_id]:
                    if dependent_id not in visited:
                        dfs(dependent_id, path.copy())
                    elif dependent_id in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(dependent_id)
                        cycle = path[cycle_start:] + [dependent_id]
                        # Convert to task names for readability
                        cycle_names = [task_lookup.get(tid, tid) for tid in cycle]
                        cycles.append(cycle_names)

            rec_stack.remove(task_id)

        # Check all tasks
        all_task_ids = set(task.id for task in tasks)
        for task_id in all_task_ids:
            if task_id not in visited:
                dfs(task_id, [])

        return cycles

    def infer_needed_interface(
        self, dependent_task: Task, dependency_task_id: str
    ) -> str:
        """
        Infer what interface or functionality a dependent task needs from its dependency.

        Args:
            dependent_task: The task that depends on another
            dependency_task_id: The ID of the task it depends on

        Returns:
            String describing the expected interface/functionality
        """
        # Extract task information for dependent task
        dep_name = dependent_task.name.lower()
        dep_labels = [label.lower() for label in (dependent_task.labels or [])]

        # Try to find the dependency task to get its information
        dependency_task = None
        # Look in implementations first
        if dependency_task_id in self.implementations:
            # Get task info from implementation if available
            impl = self.implementations[dependency_task_id]
            dep_task_name = impl.get("task_name", "").lower()
            dep_task_labels = [l.lower() for l in impl.get("labels", [])]
        else:
            # For now, infer from the task ID and name patterns
            dep_task_name = dependency_task_id.lower()
            dep_task_labels = []
            # Infer labels from common patterns in task names/IDs
            if "api" in dep_task_name:
                dep_task_labels.append("api")
            if "backend" in dep_task_name:
                dep_task_labels.append("backend")
            if "frontend" in dep_task_name:
                dep_task_labels.append("frontend")

        # Common interface patterns based on task types
        interface_patterns = {
            # Frontend needs from backend
            ("frontend", "api"): "REST API endpoints with JSON responses",
            ("frontend", "backend"): "REST API endpoints with JSON responses",
            (
                "frontend",
                "auth",
            ): "Authentication endpoints (/login, /logout, /verify) and JWT token validation",
            (
                "ui",
                "api",
            ): "Well-documented API endpoints with consistent response formats",
            (
                "client",
                "backend",
            ): "API endpoints, authentication middleware, and CORS configuration",
            # Mobile app needs
            (
                "mobile",
                "api",
            ): "RESTful API with mobile-optimized responses and token-based auth",
            ("ios", "backend"): "API endpoints with Swift-compatible JSON structures",
            (
                "android",
                "backend",
            ): "API endpoints with Kotlin/Java-compatible responses",
            # Testing needs
            (
                "test",
                "api",
            ): "Documented endpoints with example requests/responses for testing",
            (
                "test",
                "frontend",
            ): "UI components with stable interfaces and test IDs",
            (
                "integration-test",
                "service",
            ): "Service interfaces and test data endpoints",
            (
                "e2e",
                "frontend",
            ): "Stable UI elements with test IDs and predictable states",
            # ML patterns (must come before general deployment patterns)
            (
                "deployment",
                "training",
            ): "Trained model artifacts with performance metrics and configuration",
            (
                "deployment",
                "model",
            ): "Model file with metadata and deployment configuration",
            (
                "production",
                "model",
            ): "Model file with metadata and deployment configuration",
            # General deployment needs
            ("deploy", "build"): "Build artifacts, Docker images, or compiled bundles",
            (
                "deployment",
                "config",
            ): "Environment configuration files and deployment scripts",
            ("release", "package"): "Versioned packages with dependency specifications",
            # Documentation needs
            (
                "docs",
                "api",
            ): "OpenAPI/Swagger specs, endpoint descriptions, and examples",
            (
                "documentation",
                "implementation",
            ): "Code comments, architectural decisions, and usage examples",
            # Database/data needs
            ("api", "database"): "Database schema, models, and migration scripts",
            (
                "service",
                "schema",
            ): "Data models with validation rules and relationships",
            ("migration", "model"): "Entity definitions and database change scripts",
            # Data processing patterns
            (
                "transformation",
                "extraction",
            ): "Extracted data in standardized format with clear schema",
            (
                "data",
                "data",
            ): "Processed data format with documented structure",
            # Integration needs
            (
                "integration",
                "service",
            ): "Service interfaces, data contracts, and connection configs",
            ("connector", "api"): "API client libraries or SDK implementations",
        }

        # Check for pattern matches - match both dependent and dependency types
        for (dep_type, prereq_type), interface in interface_patterns.items():
            # Check if dependent task matches the pattern (support variations)
            dep_match = (
                dep_type in dep_labels
                or dep_type in dep_name
                or (
                    dep_type == "test"
                    and ("testing" in dep_labels or "integration" in dep_labels)
                )
            )
            # Check if dependency task matches the prerequisite pattern (support variations)
            prereq_match = (
                prereq_type in dep_task_labels
                or prereq_type in dep_task_name
                or (
                    prereq_type == "training"
                    and ("training" in dep_task_labels or "model" in dep_task_labels)
                )
            )

            if dep_match and prereq_match:
                return interface

        # Fallback: check just dependent task type for common patterns
        for (dep_type, prereq_type), interface in interface_patterns.items():
            dep_match = (
                dep_type in dep_labels
                or dep_type in dep_name
                or (
                    dep_type == "test"
                    and ("testing" in dep_labels or "integration" in dep_labels)
                )
            )
            if dep_match:
                return interface

        # Specific keyword-based interfaces
        if "admin" in dep_name or "admin" in dep_labels:
            return "User authentication with role-based access control (admin role required)"

        if "payment" in dep_name or "payment" in dep_labels:
            return "Payment processing API with secure transaction handling"

        if "notification" in dep_name or "notification" in dep_labels:
            return "Message queue or notification service interface"

        if "search" in dep_name or "search" in dep_labels:
            return "Search API with filtering, pagination, and relevance scoring"

        if "report" in dep_name or "analytics" in dep_name:
            return "Data aggregation endpoints and analytics APIs"

        # Default based on common patterns
        if any(frontend in dep_labels for frontend in ["frontend", "ui", "client"]):
            return "Backend API endpoints with authentication and data operations"

        if any(test in dep_labels for test in ["test", "spec", "qa"]):
            return "Testable interfaces with clear contracts and error handling"

        # Generic default
        return "Implementation that can be integrated by dependent components"

    async def suggest_task_order(self, tasks: List[Task]) -> List[Task]:
        """
        Suggest an optimal order for tasks based on dependencies.

        Uses topological sort with priority consideration.

        Args:
            tasks: List of tasks to order

        Returns:
            Ordered list of tasks
        """
        # Build dependency graph
        dep_map = await self.analyze_dependencies(tasks)

        # Build reverse map (task -> its dependencies)
        # This combines explicit dependencies with inferred ones
        task_deps = {}
        for task in tasks:
            task_deps[task.id] = set(task.dependencies or [])

        # Add inferred dependencies from dep_map
        # dep_map format: {dependency_id: [dependent_ids]}
        for dependency_id, dependents in dep_map.items():
            for dependent_id in dependents:
                if dependent_id in task_deps:
                    task_deps[dependent_id].add(dependency_id)

        # Count incoming edges (how many dependencies each task has)
        in_degree = {task.id: len(task_deps.get(task.id, set())) for task in tasks}

        # Priority queue for tasks with no dependencies
        # Use negative priority for max heap behavior
        import heapq

        ready: List[Tuple[int, Any, Task]] = []
        for task in tasks:
            if in_degree[task.id] == 0:
                # Sort by priority then by creation date
                priority_value = {
                    Priority.URGENT: 0,
                    Priority.HIGH: 1,
                    Priority.MEDIUM: 2,
                    Priority.LOW: 3,
                }.get(task.priority, 2)
                heapq.heappush(
                    ready, (priority_value, task.created_at.timestamp(), task)
                )

        ordered = []
        while ready:
            _, _, task = heapq.heappop(ready)
            ordered.append(task)

            # Reduce in-degree for tasks that depend on this one
            # Check both explicit dependencies and inferred ones
            for other_task_id, deps in task_deps.items():
                if task.id in deps:
                    in_degree[other_task_id] -= 1
                    if in_degree[other_task_id] == 0:
                        # Find task object
                        dependent_task = next(
                            (t for t in tasks if t.id == other_task_id), None
                        )
                        if dependent_task:
                            priority_value = {
                                Priority.URGENT: 0,
                                Priority.HIGH: 1,
                                Priority.MEDIUM: 2,
                                Priority.LOW: 3,
                            }.get(dependent_task.priority, 2)
                            heapq.heappush(
                                ready,
                                (
                                    priority_value,
                                    dependent_task.created_at.timestamp(),
                                    dependent_task,
                                ),
                            )

        # If not all tasks were ordered, there's a cycle
        if len(ordered) < len(tasks):
            logger.warning("Could not order all tasks due to circular dependencies")
            # Add remaining tasks at the end
            ordered_ids = {t.id for t in ordered}
            for task in tasks:
                if task.id not in ordered_ids:
                    ordered.append(task)

        return ordered

    def get_decisions_for_task(self, task_id: str) -> List[Decision]:
        """
        Get all decisions related to a specific task.

        Args:
            task_id: The task ID

        Returns:
            List of related decisions
        """
        return [d for d in self.decisions if d.task_id == task_id]

    @with_fallback(
        lambda self, task_id: logger.warning(
            f"Failed to persist implementation for {task_id}"
        )
    )
    async def _persist_implementation_safe(self, task_id: str) -> None:
        """Persist implementation with graceful degradation"""
        if self.persistence:
            await self.persistence.store(
                "implementations", task_id, self.implementations[task_id]
            )

    @with_fallback(
        lambda self, decision: logger.warning(
            f"Failed to persist decision {decision.decision_id}"
        )
    )
    async def _persist_decision_safe(self, decision: Decision) -> None:
        """Persist decision with graceful degradation"""
        if self.persistence:
            await self.persistence.store(
                "decisions", decision.decision_id, decision.__dict__
            )

    def get_implementation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tracked implementations.

        Returns:
            Summary statistics and recent implementations
        """
        return {
            "total_implementations": len(self.implementations),
            "total_decisions": len(self.decisions),
            "pattern_types": list(self.patterns.keys()),
            "recent_implementations": list(self.implementations.values())[-5:],
            "tasks_with_dependents": len(self.dependencies),
        }

    def clear_old_data(self, days: int = 30) -> None:
        """
        Clear context data older than specified days.

        Args:
            days: Number of days to retain
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        # Clear old implementations
        self.implementations = {
            k: v
            for k, v in self.implementations.items()
            if datetime.fromisoformat(v["timestamp"]).timestamp() > cutoff
        }

        # Clear old decisions
        self.decisions = [d for d in self.decisions if d.timestamp.timestamp() > cutoff]

        logger.info(f"Cleared context data older than {days} days")
