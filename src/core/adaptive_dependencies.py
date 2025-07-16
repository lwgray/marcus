"""
Adaptive Dependency Inference System for Marcus

Enhances Marcus's template-based dependency system with adaptive learning.
Works alongside existing templates to:
1. Suggest additional dependencies templates might miss
2. Learn from successful project completions
3. Enable better agent communication through the kanban board
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.models import Task, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class DependencySignal:
    """A signal indicating potential dependency"""

    signal_type: str
    strength: float  # 0.0 to 1.0
    reason: str


@dataclass
class RelationshipPattern:
    """A learned pattern of task relationships"""

    pattern_id: str
    feature_weights: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.5
    examples_count: int = 0
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class DependencyFeedback:
    """User feedback on a dependency inference"""

    task_a_id: str
    task_b_id: str
    is_dependency: bool
    confidence: float
    user_confirmed: Optional[bool] = None
    feedback_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class UserRelationship:
    """User-defined relationship between tasks"""

    task_a_id: str
    task_b_id: str
    relationship_type: str  # "depends_on", "blocks", "related", "unrelated"
    user_confidence: float  # How sure the user is
    reason: Optional[str] = None
    created_by: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowPattern:
    """User-defined workflow pattern"""

    pattern_id: str
    name: str
    description: str
    stages: List[Dict[str, Any]]  # Ordered stages with metadata
    relationships: List[Dict[str, str]]  # How stages connect
    domain: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    created_by_user: bool = True
    usage_count: int = 0


@dataclass
class DependencyInterface:
    """Defines what a task produces and what dependents need"""

    task_id: str
    produces: List[str]  # What this task outputs
    requires: List[str]  # What this task needs from dependencies
    interface_type: str  # API, data, UI, config, etc.
    documentation: Optional[str] = None


class AdaptiveDependencyInferer:
    """
    Adaptive system for inferring task dependencies based on multiple signals
    and learned patterns rather than hard-coded rules.
    """

    def __init__(self, initial_confidence_threshold: float = 0.6):
        """
        Initialize the adaptive dependency inferer.

        Args:
            initial_confidence_threshold: Minimum confidence to suggest dependency
        """
        self.confidence_threshold = initial_confidence_threshold
        self.patterns: Dict[str, RelationshipPattern] = {}
        self.feedback_history: List[DependencyFeedback] = []
        self.user_relationships: List[UserRelationship] = []
        self.workflow_patterns: Dict[str, WorkflowPattern] = {}
        self.user_preferences = {
            "auto_infer": True,  # Whether to automatically infer dependencies
            "require_confirmation_below": 0.7,  # Confidence threshold for user confirmation
            "respect_explicit_only": False,  # Only use user-defined dependencies
        }

        # Feature weights (will be adapted based on feedback)
        self.feature_weights = {
            "temporal_order": 0.3,  # Tasks created in sequence
            "naming_similarity": 0.2,  # Shared words/concepts
            "shared_entities": 0.2,  # Common nouns/objects
            "action_sequence": 0.15,  # Verb relationships
            "label_overlap": 0.15,  # Common labels/tags
        }

        # Action relationships (not prescriptive, just common patterns)
        self.action_relationships = {
            # Format: (action_before, action_after) -> strength
            ("create", "test"): 0.8,
            ("build", "deploy"): 0.7,
            ("design", "implement"): 0.8,
            ("gather", "analyze"): 0.7,
            ("prepare", "execute"): 0.6,
            ("extract", "transform"): 0.8,
            ("transform", "load"): 0.8,
            ("train", "evaluate"): 0.9,
            ("write", "review"): 0.7,
            ("implement", "document"): 0.6,
        }

    def infer_dependency(
        self, task_a: Task, task_b: Task
    ) -> Tuple[bool, float, List[DependencySignal]]:
        """
        Infer if task_a depends on task_b using multiple signals.

        Returns:
            Tuple of (is_dependency, confidence, signals)
        """
        signals = []

        # 1. Temporal ordering signal
        temporal_signal = self._check_temporal_order(task_a, task_b)
        if temporal_signal:
            signals.append(temporal_signal)

        # 2. Naming similarity signal
        naming_signal = self._check_naming_similarity(task_a, task_b)
        if naming_signal:
            signals.append(naming_signal)

        # 3. Shared entities signal
        entity_signal = self._check_shared_entities(task_a, task_b)
        if entity_signal:
            signals.append(entity_signal)

        # 4. Action sequence signal
        action_signal = self._check_action_sequence(task_a, task_b)
        if action_signal:
            signals.append(action_signal)

        # 5. Label relationship signal
        label_signal = self._check_label_relationships(task_a, task_b)
        if label_signal:
            signals.append(label_signal)

        # 6. Learned pattern signal
        pattern_signal = self._check_learned_patterns(task_a, task_b)
        if pattern_signal:
            signals.append(pattern_signal)

        # Calculate weighted confidence
        if not signals:
            return False, 0.0, []

        total_weight = sum(
            self.feature_weights.get(s.signal_type, 0.1) for s in signals
        )
        weighted_confidence = (
            sum(
                s.strength * self.feature_weights.get(s.signal_type, 0.1)
                for s in signals
            )
            / total_weight
            if total_weight > 0
            else 0
        )

        is_dependency = weighted_confidence >= self.confidence_threshold

        return is_dependency, weighted_confidence, signals

    def _check_temporal_order(
        self, task_a: Task, task_b: Task
    ) -> Optional[DependencySignal]:
        """Check if temporal ordering suggests dependency"""
        if task_a.created_at and task_b.created_at:
            # Task A created after Task B suggests potential dependency
            if task_a.created_at > task_b.created_at:
                time_diff = (
                    task_a.created_at - task_b.created_at
                ).total_seconds() / 3600

                # Stronger signal if created close in time (within 24 hours)
                if time_diff <= 24:
                    strength = 0.8
                elif time_diff <= 168:  # 1 week
                    strength = 0.5
                else:
                    strength = 0.2

                return DependencySignal(
                    signal_type="temporal_order",
                    strength=strength,
                    reason=f"Created {time_diff:.1f} hours after",
                )
        return None

    def _check_naming_similarity(
        self, task_a: Task, task_b: Task
    ) -> Optional[DependencySignal]:
        """Check if task names share significant words"""
        # Extract meaningful words (ignore common words)
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "for",
            "to",
            "in",
            "of",
            "with",
            "on",
            "at",
        }

        words_a = set(task_a.name.lower().split()) - stop_words
        words_b = set(task_b.name.lower().split()) - stop_words

        if not words_a or not words_b:
            return None

        # Calculate Jaccard similarity
        intersection = words_a & words_b
        union = words_a | words_b

        if len(intersection) >= 2:  # At least 2 common words
            similarity = len(intersection) / len(union)
            return DependencySignal(
                signal_type="naming_similarity",
                strength=min(similarity * 2, 1.0),  # Scale up
                reason=f"Shared concepts: {', '.join(intersection)}",
            )
        return None

    def _check_shared_entities(
        self, task_a: Task, task_b: Task
    ) -> Optional[DependencySignal]:
        """Check for shared entities (nouns) between tasks"""
        # Simple noun detection (words that are likely entities)
        # In production, you'd use NLP libraries

        def extract_potential_entities(text: str) -> Set[str]:
            words = text.lower().split()
            entities = set()

            # Look for capitalized words (potential proper nouns)
            for word in text.split():
                if word[0].isupper() and len(word) > 2:
                    entities.add(word.lower())

            # Look for compound words (e.g., "user-profile")
            for word in words:
                if "-" in word or "_" in word:
                    entities.add(word)

            return entities

        entities_a = extract_potential_entities(task_a.name)
        entities_b = extract_potential_entities(task_b.name)

        shared = entities_a & entities_b
        if shared:
            return DependencySignal(
                signal_type="shared_entities",
                strength=min(len(shared) * 0.3, 1.0),
                reason=f"Shared entities: {', '.join(shared)}",
            )
        return None

    def _check_action_sequence(
        self, task_a: Task, task_b: Task
    ) -> Optional[DependencySignal]:
        """Check if actions suggest a natural sequence"""

        def extract_action(task_name: str) -> Optional[str]:
            words = task_name.lower().split()
            # Common action verbs (first word is often the verb)
            if words:
                first_word = words[0]
                # Check if it's a verb-like word
                if first_word.endswith(
                    ("ate", "ify", "ize", "ing", "ed")
                ) or first_word in [
                    "create",
                    "build",
                    "test",
                    "deploy",
                    "implement",
                    "design",
                    "analyze",
                    "prepare",
                    "setup",
                    "configure",
                    "write",
                    "review",
                    "train",
                    "evaluate",
                    "extract",
                    "transform",
                    "load",
                    "gather",
                    "process",
                ]:
                    return first_word
            return None

        action_a = extract_action(task_a.name)
        action_b = extract_action(task_b.name)

        if action_a and action_b:
            # Check if this action sequence exists in our patterns
            key = (action_b, action_a)
            if key in self.action_relationships:
                strength = self.action_relationships[key]
                return DependencySignal(
                    signal_type="action_sequence",
                    strength=strength,
                    reason=f"Common pattern: {action_b} → {action_a}",
                )
        return None

    def _check_label_relationships(
        self, task_a: Task, task_b: Task
    ) -> Optional[DependencySignal]:
        """Check if labels suggest relationship (without being prescriptive)"""
        if not task_a.labels or not task_b.labels:
            return None

        labels_a = set(label.lower() for label in task_a.labels)
        labels_b = set(label.lower() for label in task_b.labels)

        # Look for complementary labels (not prescriptive pairs)
        complementary_patterns = [
            # These are observed patterns, not rules
            ({"input", "source", "raw"}, {"output", "processed", "refined"}),
            ({"design", "plan", "spec"}, {"implementation", "build", "code"}),
            ({"data", "dataset"}, {"analysis", "model", "insight"}),
            ({"draft", "initial"}, {"review", "final", "approved"}),
        ]

        for set_before, set_after in complementary_patterns:
            if labels_b & set_before and labels_a & set_after:
                return DependencySignal(
                    signal_type="label_overlap",
                    strength=0.6,
                    reason=f"Complementary labels: {labels_b & set_before} → {labels_a & set_after}",
                )

        # Simple overlap check
        overlap = labels_a & labels_b
        if overlap:
            return DependencySignal(
                signal_type="label_overlap",
                strength=min(len(overlap) * 0.25, 0.5),
                reason=f"Shared labels: {', '.join(overlap)}",
            )
        return None

    def _check_learned_patterns(
        self, task_a: Task, task_b: Task
    ) -> Optional[DependencySignal]:
        """Check against learned patterns from user feedback"""
        if not self.patterns:
            return None

        # Extract features for this task pair
        features = self._extract_features(task_a, task_b)

        # Find best matching pattern
        best_match = None
        best_score = 0.0

        for pattern_id, pattern in self.patterns.items():
            score = self._calculate_pattern_match(features, pattern)
            if score > best_score and score > 0.5:  # Minimum match threshold
                best_score = score
                best_match = pattern

        if best_match:
            return DependencySignal(
                signal_type="learned_pattern",
                strength=best_score * best_match.confidence,
                reason=f"Matches learned pattern (confidence: {best_match.confidence:.0%})",
            )
        return None

    def _extract_features(self, task_a: Task, task_b: Task) -> Dict[str, float]:
        """Extract features from a task pair for pattern matching"""
        features = {}

        # Word overlap ratio
        words_a = set(task_a.name.lower().split())
        words_b = set(task_b.name.lower().split())
        features["word_overlap"] = len(words_a & words_b) / max(
            len(words_a | words_b), 1
        )

        # Temporal distance (normalized)
        if task_a.created_at and task_b.created_at:
            time_diff = abs(
                (task_a.created_at - task_b.created_at).total_seconds() / 86400
            )  # days
            features["temporal_distance"] = 1.0 / (
                1.0 + time_diff
            )  # Closer in time = higher score

        # Label similarity
        if task_a.labels and task_b.labels:
            labels_a = set(task_a.labels)
            labels_b = set(task_b.labels)
            features["label_similarity"] = len(labels_a & labels_b) / max(
                len(labels_a | labels_b), 1
            )

        # Length similarity
        features["length_ratio"] = min(len(task_a.name), len(task_b.name)) / max(
            len(task_a.name), len(task_b.name)
        )

        return features

    def _calculate_pattern_match(
        self, features: Dict[str, float], pattern: RelationshipPattern
    ) -> float:
        """Calculate how well features match a learned pattern"""
        if not pattern.feature_weights:
            return 0.0

        score = 0.0
        total_weight = 0.0

        for feature, value in features.items():
            if feature in pattern.feature_weights:
                weight = pattern.feature_weights[feature]
                score += value * weight
                total_weight += weight

        return score / total_weight if total_weight > 0 else 0.0

    def record_feedback(
        self,
        task_a_id: str,
        task_b_id: str,
        is_dependency: bool,
        original_confidence: float,
        user_confirmed: bool,
        reason: Optional[str] = None,
    ) -> None:
        """
        Record user feedback on a dependency inference.

        This is used to improve future predictions.
        """
        feedback = DependencyFeedback(
            task_a_id=task_a_id,
            task_b_id=task_b_id,
            is_dependency=is_dependency,
            confidence=original_confidence,
            user_confirmed=user_confirmed,
            feedback_reason=reason,
        )

        self.feedback_history.append(feedback)

        # Adjust feature weights based on feedback
        if user_confirmed != is_dependency:
            # We were wrong - adjust weights
            self._adjust_weights_from_feedback(feedback, decrease=True)
        else:
            # We were right - reinforce weights
            self._adjust_weights_from_feedback(feedback, decrease=False)

        # Learn new patterns from confirmed dependencies
        if user_confirmed and is_dependency:
            self._learn_pattern_from_feedback(task_a_id, task_b_id)

        logger.info(
            f"Recorded feedback: {task_a_id} {'depends on' if is_dependency else 'independent of'} {task_b_id} "
            f"(confidence: {original_confidence:.2f}, confirmed: {user_confirmed})"
        )

    def _adjust_weights_from_feedback(
        self, feedback: DependencyFeedback, decrease: bool
    ) -> None:
        """Adjust feature weights based on feedback"""
        # Simple weight adjustment (in production, use more sophisticated ML)
        adjustment = 0.05 if not decrease else -0.05

        # Adjust all weights slightly
        for feature in self.feature_weights:
            self.feature_weights[feature] = max(
                0.1, min(0.9, self.feature_weights[feature] + adjustment)
            )

        # Normalize weights
        total = sum(self.feature_weights.values())
        self.feature_weights = {k: v / total for k, v in self.feature_weights.items()}

    def _learn_pattern_from_feedback(self, task_a_id: str, task_b_id: str) -> None:
        """Learn a new pattern from confirmed dependency"""
        # In a real implementation, this would extract features from the actual tasks
        # and create/update a pattern
        pattern_id = f"learned_{len(self.patterns)}"

        # Create new pattern (simplified - would extract from actual tasks)
        pattern = RelationshipPattern(
            pattern_id=pattern_id,
            confidence=0.6,  # Start with moderate confidence
            examples_count=1,
        )

        self.patterns[pattern_id] = pattern

    def get_confidence_explanation(self, signals: List[DependencySignal]) -> str:
        """Generate human-readable explanation of confidence calculation"""
        if not signals:
            return "No dependency signals detected."

        explanations = []
        for signal in sorted(signals, key=lambda s: s.strength, reverse=True):
            explanations.append(f"• {signal.reason} (strength: {signal.strength:.0%})")

        return "Dependency signals found:\n" + "\n".join(explanations)

    def suggest_dependencies(
        self, task: Task, all_tasks: List[Task], min_confidence: float = 0.5
    ) -> List[Tuple[Task, float, str]]:
        """
        Suggest potential dependencies for a task.

        Returns:
            List of (dependent_task, confidence, explanation) tuples
        """
        suggestions = []

        for other_task in all_tasks:
            if other_task.id == task.id:
                continue

            # Check if task might depend on other_task
            is_dep, confidence, signals = self.infer_dependency(task, other_task)

            if confidence >= min_confidence:
                explanation = self.get_confidence_explanation(signals)
                suggestions.append((other_task, confidence, explanation))

        # Sort by confidence
        suggestions.sort(key=lambda x: x[1], reverse=True)

        return suggestions

    def learn_from_kanban_board(self, tasks: List[Task]) -> None:
        """
        Learn dependency patterns from tasks on the kanban board.

        The kanban board (Seneca) is the source of truth for user-defined
        dependencies. We learn from:
        1. Explicit dependencies set by users in Seneca
        2. Task ordering and column placement
        3. Task completion patterns

        Args:
            tasks: All tasks from the kanban board with their dependencies
        """
        # Track explicit dependencies as ground truth
        for task in tasks:
            if task.dependencies:
                for dep_id in task.dependencies:
                    # Find the dependency task
                    dep_task = next((t for t in tasks if t.id == dep_id), None)
                    if dep_task:
                        # This is a user-confirmed dependency
                        self._learn_from_confirmed_dependency(task, dep_task)

        # Learn from task completion order
        completed_tasks = [t for t in tasks if t.status == TaskStatus.DONE]
        completed_tasks.sort(key=lambda t: t.updated_at)

        # Tasks completed in sequence might have implicit dependencies
        for i in range(len(completed_tasks) - 1):
            task_before = completed_tasks[i]
            task_after = completed_tasks[i + 1]

            # If completed close in time, might indicate workflow
            time_diff = (
                task_after.updated_at - task_before.updated_at
            ).total_seconds() / 3600
            if time_diff < 4:  # Within 4 hours
                # Weak signal of potential dependency
                features = self._extract_features(task_after, task_before)
                self._update_pattern_weights(features, strength=0.3)

    def _learn_from_confirmed_dependency(
        self, dependent: Task, dependency: Task
    ) -> None:
        """Learn patterns from a user-confirmed dependency"""
        # Extract features from this confirmed relationship
        features = self._extract_features(dependent, dependency)

        # Check which of our signals were present
        _, _, signals = self.infer_dependency(dependent, dependency)

        # Strengthen weights for signals that were correct
        for signal in signals:
            if signal.signal_type in self.feature_weights:
                # Increase weight for this feature
                self.feature_weights[signal.signal_type] = min(
                    0.9, self.feature_weights[signal.signal_type] * 1.1
                )

        # Create or update pattern
        pattern_key = self._generate_pattern_key(features)
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = RelationshipPattern(
                pattern_id=pattern_key,
                feature_weights=features,
                confidence=0.7,
                examples_count=1,
            )
        else:
            pattern = self.patterns[pattern_key]
            pattern.examples_count += 1
            pattern.confidence = min(0.95, pattern.confidence * 1.05)
            pattern.last_seen = datetime.now()

        logger.info(
            f"Learned from confirmed dependency: {dependent.name} depends on {dependency.name}"
        )

    def _generate_pattern_key(self, features: Dict[str, float]) -> str:
        """Generate a key for a pattern based on its features"""
        # Simple key based on feature presence
        key_parts = []
        for feature, value in sorted(features.items()):
            if value > 0.5:
                key_parts.append(f"{feature}:high")
            elif value > 0.2:
                key_parts.append(f"{feature}:med")
        return "_".join(key_parts) if key_parts else "general"

    def _update_pattern_weights(
        self, features: Dict[str, float], strength: float = 1.0
    ) -> None:
        """Update pattern weights based on observed features"""
        for feature, value in features.items():
            if feature in self.feature_weights:
                # Slightly adjust weight based on observation
                adjustment = 0.01 * strength * value
                self.feature_weights[feature] = max(
                    0.1, min(0.9, self.feature_weights[feature] + adjustment)
                )

    def get_inference_mode(self) -> str:
        """Get current inference mode based on user preferences"""
        if self.user_preferences.get("respect_explicit_only"):
            return "explicit_only"
        elif not self.user_preferences.get("auto_infer"):
            return "manual"
        else:
            return "adaptive"

    def should_require_confirmation(self, confidence: float) -> bool:
        """Check if user confirmation is needed for this confidence level"""
        threshold = self.user_preferences.get("require_confirmation_below", 0.7)
        return confidence < threshold
