"""
Hybrid Dependency Inference Engine

Combines pattern-based rules with AI intelligence for robust and flexible
dependency detection. Uses patterns for common cases and AI for complex scenarios.
"""

import json
import logging
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from src.config.hybrid_inference_config import HybridInferenceConfig
from src.core.models import Task, TaskStatus
from src.core.resilience import RetryConfig, with_fallback, with_retry
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.integrations.enhanced_task_classifier import EnhancedTaskClassifier
from src.intelligence.dependency_inferer import (
    DependencyGraph,
    DependencyInferer,
    DependencyPattern,
    InferredDependency,
)

logger = logging.getLogger(__name__)


@dataclass
class HybridDependency(InferredDependency):
    """Extended dependency with hybrid inference metadata"""

    inference_method: str  # 'pattern', 'ai', 'both'
    pattern_confidence: float = 0.0
    ai_confidence: float = 0.0
    ai_reasoning: Optional[str] = None


class HybridDependencyInferer(DependencyInferer):
    """
    Hybrid dependency inference combining patterns and AI.

    Strategy:
    1. Use fast pattern matching for obvious dependencies
    2. Use AI for ambiguous or complex cases
    3. Combine both for validation and confidence scoring
    4. Cache AI results for performance
    """

    def __init__(
        self,
        ai_engine: Optional[AIAnalysisEngine] = None,
        config: Optional[HybridInferenceConfig] = None,
    ):
        super().__init__()
        self.ai_engine = ai_engine
        self.config = config or HybridInferenceConfig()
        self.config.validate()  # Ensure valid configuration

        # Check if AI is available and enabled
        self.ai_enabled = ai_engine is not None and self.config.enable_ai_inference
        self.inference_cache = {}  # Cache AI inferences
        self.cache_timestamps = {}  # Track cache age
        
        # Use enhanced task classifier for better task type detection
        self.task_classifier = EnhancedTaskClassifier()

        # Log configuration
        logger.info(
            f"Hybrid inference initialized with config: "
            f"pattern_threshold={self.config.pattern_confidence_threshold}, "
            f"ai_threshold={self.config.ai_confidence_threshold}, "
            f"ai_enabled={self.ai_enabled}"
        )

    async def infer_dependencies(self, tasks: List[Task]) -> DependencyGraph:
        """
        Infer dependencies using hybrid approach.

        Process:
        1. Run pattern-based inference (fast)
        2. Identify ambiguous cases
        3. Use AI for complex inference
        4. Combine and validate results
        """
        logger.info(f"Starting hybrid dependency inference for {len(tasks)} tasks")

        # Step 1: Pattern-based inference (from parent class)
        pattern_dependencies = await self._get_pattern_dependencies(tasks)

        # Step 2: Identify cases needing AI analysis
        ambiguous_pairs = await self._identify_ambiguous_pairs(
            tasks, pattern_dependencies
        )

        # Step 3: AI inference for complex cases
        ai_dependencies = {}
        if self.ai_enabled and ambiguous_pairs:
            ai_dependencies = await self._get_ai_dependencies(tasks, ambiguous_pairs)

        # Step 4: Combine results
        final_dependencies = await self._combine_dependencies(
            pattern_dependencies, ai_dependencies, tasks
        )

        # Step 5: Build dependency graph
        graph = self._build_dependency_graph(tasks, final_dependencies)

        # Log statistics
        self._log_inference_stats(
            pattern_dependencies, ai_dependencies, final_dependencies
        )

        return graph

    async def _get_pattern_dependencies(
        self, tasks: List[Task]
    ) -> Dict[Tuple[str, str], HybridDependency]:
        """Get dependencies using pattern matching"""
        dependencies = {}

        for dependent_task in tasks:
            for dependency_task in tasks:
                if dependent_task.id == dependency_task.id:
                    continue

                # Check each pattern
                for pattern in self.dependency_patterns:
                    dep = self._check_pattern(dependent_task, dependency_task, pattern)
                    if dep:
                        key = (dep.dependent_task_id, dep.dependency_task_id)

                        # Convert to hybrid dependency
                        hybrid_dep = HybridDependency(
                            dependent_task_id=dep.dependent_task_id,
                            dependency_task_id=dep.dependency_task_id,
                            dependency_type=dep.dependency_type,
                            confidence=dep.confidence,
                            reasoning=dep.reasoning,
                            inference_method="pattern",
                            pattern_confidence=dep.confidence,
                        )

                        # Keep highest confidence pattern
                        if (
                            key not in dependencies
                            or dependencies[key].confidence < hybrid_dep.confidence
                        ):
                            dependencies[key] = hybrid_dep

        return dependencies

    async def _identify_ambiguous_pairs(
        self,
        tasks: List[Task],
        pattern_dependencies: Dict[Tuple[str, str], HybridDependency],
    ) -> List[Tuple[Task, Task]]:
        """
        Identify task pairs that need AI analysis.

        Cases needing AI:
        1. No pattern match but similar components
        2. Low confidence pattern matches
        3. Conflicting pattern matches
        4. Complex multi-step workflows
        """
        ambiguous_pairs = []
        task_map = {task.id: task for task in tasks}

        # Check all pairs
        for i, task1 in enumerate(tasks):
            for j, task2 in enumerate(tasks):
                if i >= j:  # Skip self and already processed
                    continue

                key = (task1.id, task2.id)
                reverse_key = (task2.id, task1.id)

                # Case 1: No pattern match but potential relationship
                if (
                    key not in pattern_dependencies
                    and reverse_key not in pattern_dependencies
                ):
                    if self._might_be_related(task1, task2):
                        ambiguous_pairs.append((task1, task2))

                # Case 2: Low confidence pattern match
                elif key in pattern_dependencies:
                    if (
                        pattern_dependencies[key].confidence
                        < self.config.pattern_confidence_threshold
                    ):
                        ambiguous_pairs.append((task1, task2))

                # Case 3: Bidirectional dependencies (conflict)
                elif (
                    key in pattern_dependencies and reverse_key in pattern_dependencies
                ):
                    ambiguous_pairs.append((task1, task2))

        # Case 4: Complex workflows (multiple related tasks)
        workflow_groups = self._identify_workflow_groups(tasks)
        for group in workflow_groups:
            if len(group) > 3:  # Complex workflow
                for i, task1 in enumerate(group):
                    for j, task2 in enumerate(group):
                        if i < j and (task1, task2) not in ambiguous_pairs:
                            ambiguous_pairs.append((task1, task2))

        return ambiguous_pairs

    def _might_be_related(self, task1: Task, task2: Task) -> bool:
        """Check if tasks might be related based on shared context"""
        # Extract meaningful words
        words1 = set(self._extract_keywords(task1))
        words2 = set(self._extract_keywords(task2))

        # Check for shared components/features
        shared = words1.intersection(words2)
        
        # Also consider task phases - tasks in different phases of same feature are related
        if len(shared) >= self.config.min_shared_keywords:
            return True
            
        # Check if tasks are in same feature by labels
        if task1.labels and task2.labels:
            shared_labels = set(task1.labels) & set(task2.labels)
            if shared_labels:
                # Check if they're in different phases
                type1 = self.task_classifier.classify(task1)
                type2 = self.task_classifier.classify(task2)
                if type1 != type2:
                    return True
                    
        return False

    def _extract_keywords(self, task: Task) -> List[str]:
        """Extract meaningful keywords from task"""
        text = f"{task.name} {task.description or ''} {' '.join(task.labels or [])}".lower()

        # Remove stop words and common verbs
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
            "from",
            "about",
            "into",
            "through",
            "during",
            "create",
            "build",
            "implement",
            "add",
            "update",
            "fix",
            "test",
        }

        words = re.findall(r"\b\w+\b", text)
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _identify_workflow_groups(self, tasks: List[Task]) -> List[List[Task]]:
        """Group tasks that might be part of the same workflow"""
        groups = []
        used = set()

        for task in tasks:
            if task.id in used:
                continue

            # Find related tasks
            group = [task]
            keywords = set(self._extract_keywords(task))

            for other in tasks:
                if other.id != task.id and other.id not in used:
                    other_keywords = set(self._extract_keywords(other))
                    if len(keywords.intersection(other_keywords)) >= 2:
                        group.append(other)
                        used.add(other.id)

            if len(group) > 1:
                groups.append(group)
                used.add(task.id)

        return groups

    @with_retry(RetryConfig(max_attempts=2, base_delay=1.0))
    async def _get_ai_dependencies(
        self, tasks: List[Task], ambiguous_pairs: List[Tuple[Task, Task]]
    ) -> Dict[Tuple[str, str], HybridDependency]:
        """Use AI to analyze ambiguous dependency cases"""

        # Check cache first
        cache_key = self._get_cache_key(tasks, ambiguous_pairs)
        if cache_key in self.inference_cache:
            # Check if cache is still valid
            cache_time = self.cache_timestamps.get(cache_key, datetime.min)
            if (
                datetime.now() - cache_time
            ).total_seconds() < self.config.cache_ttl_hours * 3600:
                logger.info("Using cached AI inference results")
                return self.inference_cache[cache_key]
            else:
                # Cache expired
                del self.inference_cache[cache_key]
                del self.cache_timestamps[cache_key]

        # Prepare batch request for AI
        task_info = {
            task.id: {
                "name": task.name,
                "description": task.description or "",
                "labels": task.labels or [],
                "status": task.status.value,
                "priority": task.priority.value if task.priority else "medium",
            }
            for task in tasks
        }

        # Prepare pairs for analysis
        pairs_to_analyze = [
            {
                "task1_id": t1.id,
                "task2_id": t2.id,
                "task1_name": t1.name,
                "task2_name": t2.name,
            }
            for t1, t2 in ambiguous_pairs[: self.config.max_ai_pairs_per_batch]
        ]

        prompt = f"""Analyze these task pairs and determine if there are dependencies between them.
A dependency exists if one task must be completed before another can reasonably begin.

All tasks in the project:
{json.dumps(task_info, indent=2)}

Task pairs to analyze:
{json.dumps(pairs_to_analyze, indent=2)}

For each pair, determine:
1. Is there a dependency? (task1 depends on task2, task2 depends on task1, or no dependency)
2. How confident are you? (0.0-1.0)
3. What's the reasoning?

Return ONLY a JSON array with this structure:
[
    {{
        "task1_id": "id",
        "task2_id": "id",
        "dependency_direction": "1->2" | "2->1" | "none",
        "confidence": 0.0-1.0,
        "reasoning": "explanation",
        "dependency_type": "hard" | "soft" | "none"
    }}
]

Focus on logical dependencies based on:
- Technical requirements (can't test non-existent code)
- Data flow (need data model before business logic)
- User workflow (authentication before authorization)
- Architecture layers (database before API before UI)
"""

        try:
            response = await self.ai_engine._call_claude(prompt)
            results = json.loads(response)

            # Convert to hybrid dependencies
            ai_dependencies = {}
            for result in results:
                if result["dependency_direction"] != "none":
                    if result["dependency_direction"] == "1->2":
                        dep_id = result["task2_id"]
                        dependent_id = result["task1_id"]
                    else:  # 2->1
                        dep_id = result["task1_id"]
                        dependent_id = result["task2_id"]

                    key = (dependent_id, dep_id)
                    ai_dependencies[key] = HybridDependency(
                        dependent_task_id=dependent_id,
                        dependency_task_id=dep_id,
                        dependency_type=result["dependency_type"],
                        confidence=result["confidence"],
                        reasoning=f"AI: {result['reasoning']}",
                        inference_method="ai",
                        ai_confidence=result["confidence"],
                        ai_reasoning=result["reasoning"],
                    )

            # Cache results
            self.inference_cache[cache_key] = ai_dependencies
            self.cache_timestamps[cache_key] = datetime.now()
            return ai_dependencies

        except Exception as e:
            logger.error(f"AI dependency inference failed: {e}")
            return {}

    async def _combine_dependencies(
        self,
        pattern_deps: Dict[Tuple[str, str], HybridDependency],
        ai_deps: Dict[Tuple[str, str], HybridDependency],
        tasks: List[Task],
    ) -> List[HybridDependency]:
        """
        Combine pattern and AI dependencies intelligently.

        Rules:
        1. If both agree: boost confidence
        2. If only pattern (high confidence): use pattern
        3. If only AI (high confidence): use AI
        4. If conflict: use higher confidence or require human review
        """
        combined = {}

        # Process pattern dependencies
        for key, pattern_dep in pattern_deps.items():
            if key in ai_deps:
                # Both methods found dependency
                ai_dep = ai_deps[key]

                # Combine confidence
                combined_confidence = min(
                    1.0,
                    (pattern_dep.confidence + ai_dep.ai_confidence) / 2
                    + self.config.combined_confidence_boost,
                )

                combined[key] = HybridDependency(
                    dependent_task_id=pattern_dep.dependent_task_id,
                    dependency_task_id=pattern_dep.dependency_task_id,
                    dependency_type=pattern_dep.dependency_type,
                    confidence=combined_confidence,
                    reasoning=f"{pattern_dep.reasoning} | {ai_dep.ai_reasoning}",
                    inference_method="both",
                    pattern_confidence=pattern_dep.confidence,
                    ai_confidence=ai_dep.ai_confidence,
                    ai_reasoning=ai_dep.ai_reasoning,
                )
            elif pattern_dep.confidence >= self.config.pattern_confidence_threshold:
                # High confidence pattern only
                combined[key] = pattern_dep

        # Process AI-only dependencies
        for key, ai_dep in ai_deps.items():
            if (
                key not in combined
                and ai_dep.confidence >= self.config.ai_confidence_threshold
            ):
                combined[key] = ai_dep

        # Clean and validate
        final_deps = list(combined.values())
        final_deps = self._clean_dependencies(final_deps)

        return final_deps

    def _build_dependency_graph(
        self, tasks: List[Task], dependencies: List[HybridDependency]
    ) -> DependencyGraph:
        """Build dependency graph from hybrid dependencies"""
        nodes = {task.id: task for task in tasks}

        # Build adjacency lists
        adjacency_list = defaultdict(list)
        reverse_adjacency = defaultdict(list)

        for dep in dependencies:
            adjacency_list[dep.dependency_task_id].append(dep.dependent_task_id)
            reverse_adjacency[dep.dependent_task_id].append(dep.dependency_task_id)

        graph = DependencyGraph(
            nodes=nodes,
            edges=dependencies,
            adjacency_list=dict(adjacency_list),
            reverse_adjacency=dict(reverse_adjacency),
        )

        # Resolve cycles if needed
        if graph.has_cycle():
            logger.warning("Cycle detected, resolving based on confidence scores")
            graph = self._resolve_cycles(graph)

        return graph

    def _get_cache_key(self, tasks: List[Task], pairs: List[Tuple[Task, Task]]) -> str:
        """Generate cache key for AI inference results"""
        task_ids = sorted([t.id for t in tasks])
        pair_ids = sorted([(t1.id, t2.id) for t1, t2 in pairs])
        return f"{','.join(task_ids)}|{pair_ids}"

    def _log_inference_stats(self, pattern_deps, ai_deps, final_deps):
        """Log statistics about inference process"""
        pattern_count = len(pattern_deps)
        ai_count = len(ai_deps)
        final_count = len(final_deps)

        both_count = sum(1 for d in final_deps if d.inference_method == "both")
        pattern_only = sum(1 for d in final_deps if d.inference_method == "pattern")
        ai_only = sum(1 for d in final_deps if d.inference_method == "ai")

        logger.info(
            f"""
Dependency Inference Statistics:
- Pattern matches: {pattern_count}
- AI inferences: {ai_count}
- Final dependencies: {final_count}
  - Both methods: {both_count}
  - Pattern only: {pattern_only}
  - AI only: {ai_only}
- Average confidence: {sum(d.confidence for d in final_deps) / final_count if final_count > 0 else 0:.2f}
"""
        )

    async def explain_dependency(
        self, dependent_id: str, dependency_id: str, graph: DependencyGraph
    ) -> str:
        """
        Get detailed explanation for why a dependency exists.

        Combines pattern reasoning and AI insights.
        """
        # Find the dependency
        for dep in graph.edges:
            if (
                dep.dependent_task_id == dependent_id
                and dep.dependency_task_id == dependency_id
            ):
                if isinstance(dep, HybridDependency):
                    explanation = f"Dependency identified by: {dep.inference_method}\n"

                    if dep.pattern_confidence > 0:
                        explanation += f"Pattern match ({dep.pattern_confidence:.0%} confidence): {dep.reasoning}\n"

                    if dep.ai_reasoning:
                        explanation += f"AI analysis ({dep.ai_confidence:.0%} confidence): {dep.ai_reasoning}\n"

                    explanation += f"Overall confidence: {dep.confidence:.0%}"
                    return explanation
                else:
                    return dep.reasoning

        return "Dependency not found in graph"
