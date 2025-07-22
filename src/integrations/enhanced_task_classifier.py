"""
Enhanced Task Type Classification System.

Provides robust task type identification with expanded keyword lists,
pattern matching, and context-aware classification for 95%+ accuracy.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from src.core.models import Task
from src.integrations.nlp_task_utils import TaskType


@dataclass
class ClassificationResult:
    """Result of task type classification with confidence."""

    task_type: TaskType
    confidence: float
    matched_keywords: List[str]
    matched_patterns: List[str]
    reasoning: str


class EnhancedTaskClassifier:
    """
    Enhanced task classifier with expanded keywords and pattern matching.

    Improvements over basic classifier:
    - Expanded keyword lists based on real-world usage
    - Regular expression pattern matching
    - Context-aware classification
    - Confidence scoring
    - Support for compound task names
    """

    # Expanded keyword mappings with categories
    TASK_KEYWORDS = {
        TaskType.DESIGN: {
            "primary": [
                "design",
                "architect",
                "plan",
                "planning",
                "architecture",
                "blueprint",
                "specification",
                "spec",
                "specs",
                "research",
                "analyze",
                "analysis",
                "study",
                "investigate",
            ],
            "secondary": [
                "wireframe",
                "mockup",
                "prototype",
                "diagram",
                "model",
                "schema",
                "structure",
                "layout",
                "interface",
                "ui/ux",
                "ux",
                "ui",
                "workflow",
                "concept",
                "draft",
                "outline",
                "framework",
                "pattern",
                "template",
            ],
            "verbs": [
                "design",
                "plan",
                "architect",
                "draft",
                "outline",
                "conceptualize",
                "define",
                "specify",
                "model",
            ],
        },
        TaskType.IMPLEMENTATION: {
            "primary": [
                "implement",
                "build",
                "develop",
                "code",
                "program",
                "construct",
                "engineer",
                "fix",
                "bug",
                "bugfix",
                "patch",
                "repair",
            ],
            "secondary": [
                "feature",
                "functionality",
                "component",
                "module",
                "service",
                "api",
                "endpoint",
                "integration",
                "backend",
                "frontend",
                "database",
                "logic",
                "algorithm",
                "function",
                "class",
                "handler",
                "controller",
                "middleware",
            ],
            "verbs": [
                "implement",
                "build",
                "create",
                "develop",
                "code",
                "write",
                "add",
                "integrate",
                "setup",
                "configure",
                "establish",
                "construct",
                "generate",
                "produce",
            ],
        },
        TaskType.TESTING: {
            "primary": [
                "test",
                "testing",
                "qa",
                "quality",
                "verify",
                "validate",
                "check",
                "assert",
            ],
            "secondary": [
                "unit",
                "integration",
                "e2e",
                "end-to-end",
                "functional",
                "regression",
                "smoke",
                "acceptance",
                "performance",
                "load",
                "stress",
                "coverage",
                "suite",
                "scenario",
                "case",
                "cases",
                "spec",
                "specification",
                "behavior",
            ],
            "verbs": [
                "test",
                "verify",
                "validate",
                "check",
                "ensure",
                "confirm",
                "assert",
                "examine",
                "inspect",
                "audit",
            ],
        },
        TaskType.DOCUMENTATION: {
            "primary": [
                "document",
                "documentation",
                "docs",
                "readme",
                "guide",
                "manual",
                "wiki",
                "tutorial",
            ],
            "secondary": [
                "howto",
                "how-to",
                "reference",
                "api-docs",
                "changelog",
                "notes",
                "instructions",
                "help",
                "faq",
                "examples",
                "samples",
                "comments",
                "annotations",
                "description",
                "explanation",
                "onboarding",
            ],
            "verbs": [
                "document",
                "write",
                "annotate",
                "comment",
                "describe",
                "explain",
                "detail",
            ],
        },
        TaskType.DEPLOYMENT: {
            "primary": [
                "deploy",
                "deployment",
                "release",
                "launch",
                "rollout",
                "publish",
            ],
            "secondary": [
                "production",
                "staging",
                "live",
                "go-live",
                "ship",
                "deliver",
                "distribution",
                "installation",
                "setup",
                "migration",
                "upgrade",
                "rollback",
                "hotfix",
            ],
            "verbs": [
                "deploy",
                "release",
                "launch",
                "publish",
                "ship",
                "deliver",
                "distribute",
                "install",
                "migrate",
            ],
        },
        TaskType.INFRASTRUCTURE: {
            "primary": [
                "infrastructure",
                "setup",
                "configure",
                "provision",
                "environment",
                "devops",
            ],
            "secondary": [
                "server",
                "database",
                "network",
                "docker",
                "kubernetes",
                "k8s",
                "container",
                "vm",
                "cloud",
                "aws",
                "azure",
                "gcp",
                "ci/cd",
                "pipeline",
                "monitoring",
                "logging",
                "security",
                "firewall",
                "ssl",
                "dns",
                "cdn",
            ],
            "verbs": [
                "setup",
                "configure",
                "provision",
                "install",
                "initialize",
                "bootstrap",
                "orchestrate",
                "manage",
            ],
        },
    }

    # Pattern matching for more complex task names
    TASK_PATTERNS = {
        TaskType.DESIGN: [
            r"(?:create|define|plan)\s+(?:the\s+)?"
            r"(?:system|application|software)\s+(?:architecture|design)",
            r"design\s+(?:the\s+)?(?:data|database)\s+"
            r"(?:model|schema|structure)",
            r"(?:create|design)\s+(?:ui|ux|user\s+interface|user\s+experience)",
            r"(?:define|specify)\s+(?:api|interface)\s+"
            r"(?:contracts?|specifications?)",
            r"(?:plan|design)\s+(?:the\s+)?(?:workflow|process|flow)",
        ],
        TaskType.IMPLEMENTATION: [
            r"(?:implement|build|create)\s+(?:the\s+)?(?:\w+\s+)?"
            r"(?:feature|functionality|component)",
            r"(?:add|integrate)\s+(?:\w+\s+)?(?:support|integration)\s+"
            r"(?:for|with)",
            r"(?:develop|code|write)\s+(?:the\s+)?(?:\w+\s+)?"
            r"(?:api|service|endpoint)",
            r"(?:create|build)\s+(?:the\s+)?(?:\w+\s+)?(?:backend|frontend|ui)",
            r"(?:implement|add)\s+(?:\w+\s+)?(?:logic|algorithm|handler)",
        ],
        TaskType.TESTING: [
            r"(?:write|create|add)\s+(?:unit\s+)?tests?\s+(?:for|to)",
            r"(?:test|verify|validate)\s+(?:the\s+)?(?:\w+\s+)?(?:functionality|feature|component)",
            r"(?:create|write)\s+(?:integration|e2e|end-to-end)\s+tests?",
            r"(?:ensure|verify|check)\s+(?:that|if)\s+(?:\w+\s+)?(?:works?|functions?)",
            r"(?:add|improve)\s+test\s+coverage",
        ],
        TaskType.DOCUMENTATION: [
            r"(?:document|write\s+documentation)\s+(?:for|about)",
            r"(?:create|write|update)\s+(?:the\s+)?(?:api|user|developer)\s+(?:docs|documentation|guide)",
            r"(?:add|write)\s+(?:code\s+)?comments?\s+(?:to|for)",
            r"(?:create|update)\s+(?:the\s+)?readme(?:\.md)?",
            r"(?:write|create)\s+(?:a\s+)?(?:tutorial|guide|manual)",
        ],
        TaskType.DEPLOYMENT: [
            r"(?:deploy|release)\s+(?:to|on)\s+(?:production|staging|live)",
            r"(?:setup|configure)\s+(?:the\s+)?deployment\s+(?:pipeline|process)",
            r"(?:publish|ship)\s+(?:the\s+)?(?:application|app|service)",
            r"(?:rollout|launch)\s+(?:the\s+)?(?:feature|update|version)",
            r"(?:migrate|upgrade)\s+(?:the\s+)?(?:production|live)\s+(?:environment|system)",
        ],
        TaskType.INFRASTRUCTURE: [
            r"(?:setup|configure)\s+(?:the\s+)?(?:ci/cd|pipeline|automation)",
            r"(?:provision|create)\s+(?:the\s+)?(?:infrastructure|environment)",
            r"(?:configure|setup)\s+(?:the\s+)?(?:monitoring|logging|alerts)",
            r"(?:install|setup)\s+(?:and\s+configure\s+)?(?:docker|kubernetes|k8s)",
            r"(?:create|setup)\s+(?:the\s+)?(?:database|server|network)",
        ],
    }

    def __init__(self) -> None:
        """Initialize the enhanced classifier."""
        # Compile patterns for efficiency
        self._compiled_patterns = {}
        for task_type, patterns in self.TASK_PATTERNS.items():
            self._compiled_patterns[task_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def classify(self, task: Task) -> TaskType:
        """
        Classify a task using enhanced logic.

        Args:
            task: Task to classify

        Returns:
            TaskType enum value
        """
        result = self.classify_with_confidence(task)
        return result.task_type

    def classify_with_confidence(self, task: Task) -> ClassificationResult:
        """
        Classify a task and return detailed results with confidence.

        Args:
            task: Task to classify

        Returns:
            ClassificationResult with type, confidence, and reasoning
        """
        # Combine text sources
        text = f"{task.name} {task.description or ''} {' '.join(task.labels or [])}".lower()

        # Score each task type
        scores = {}
        matched_keywords = {}
        matched_patterns = {}

        for task_type in TaskType:
            if task_type == TaskType.OTHER:
                continue

            score, keywords, patterns = self._score_task_type(text, task_type)
            scores[task_type] = score
            matched_keywords[task_type] = keywords
            matched_patterns[task_type] = patterns

        # Find best match
        if not scores:
            return ClassificationResult(
                task_type=TaskType.OTHER,
                confidence=0.0,
                matched_keywords=[],
                matched_patterns=[],
                reasoning="No matching keywords or patterns found",
            )

        best_type = max(scores.items(), key=lambda x: x[1])[0]
        best_score = scores[best_type]

        # Calculate confidence based on score and uniqueness
        total_score = sum(scores.values())
        
        # If score is too low, treat as OTHER with 0 confidence
        if best_score < 1.0:
            return ClassificationResult(
                task_type=TaskType.OTHER,
                confidence=0.0,
                matched_keywords=[],
                matched_patterns=[],
                reasoning="Insufficient evidence for classification",
            )
            
        # Ensure minimum confidence if we have matches
        if best_score > 0:
            confidence = max(0.5, best_score / total_score) if total_score > 0 else 0.8
        else:
            confidence = 0.0

        # Boost confidence if we have strong indicators
        if matched_patterns[best_type]:
            confidence = min(confidence * 1.2, 0.95)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            best_type, matched_keywords[best_type], matched_patterns[best_type]
        )

        return ClassificationResult(
            task_type=best_type,
            confidence=confidence,
            matched_keywords=matched_keywords[best_type],
            matched_patterns=matched_patterns[best_type],
            reasoning=reasoning,
        )

    def _score_task_type(
        self, text: str, task_type: TaskType
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score how well text matches a task type.

        Returns:
            Tuple of (score, matched_keywords, matched_patterns)
        """
        score = 0.0
        matched_keywords = []
        matched_patterns = []

        keywords_dict = self.TASK_KEYWORDS.get(task_type, {})

        # Check primary keywords (higher weight)
        for keyword in keywords_dict.get("primary", []):
            # Use word boundary matching for better accuracy
            # Also check for plural forms
            pattern = rf"\b{re.escape(keyword)}s?\b"
            match = re.search(pattern, text)
            if match:
                # Give extra weight if keyword appears at the beginning
                position_weight = 1.5 if match.start() < 10 else 1.0
                
                # Give testing keywords extra weight to avoid misclassification
                if task_type == TaskType.TESTING and keyword in ["test", "testing"]:
                    score += 3.0 * position_weight  # Higher weight for testing keywords
                else:
                    score += 2.0 * position_weight
                matched_keywords.append(keyword)

        # Check secondary keywords
        for keyword in keywords_dict.get("secondary", []):
            # Use word boundary matching for better accuracy
            # Also check for plural forms
            pattern = rf"\b{re.escape(keyword)}s?\b"
            if re.search(pattern, text):
                score += 1.0
                matched_keywords.append(keyword)

        # Check verb usage
        for verb in keywords_dict.get("verbs", []):
            if re.search(rf"\b{verb}\b", text):
                # Special case: generic verbs need more context
                if verb in ["update", "create", "write", "add", "build"] and len(text.split()) <= 3:
                    # Very short task names with generic verbs get lower scores
                    score += 0.5
                    # Skip if the verb is the entire classification basis for testing
                    if task_type == TaskType.TESTING and "test" in text:
                        continue  # Don't let "write" override "test"
                else:
                    score += 1.5
                if verb not in matched_keywords:
                    matched_keywords.append(verb)

        # Check patterns (highest weight)
        for pattern in self._compiled_patterns.get(task_type, []):
            match = pattern.search(text)
            if match:
                score += 3.0
                matched_patterns.append(pattern.pattern)

        # Penalty for conflicting keywords
        for other_type in TaskType:
            if other_type == task_type or other_type == TaskType.OTHER:
                continue
            other_keywords = self.TASK_KEYWORDS.get(other_type, {})
            # Only penalize if primary keywords of other types are present
            for keyword in other_keywords.get("primary", []):
                if keyword in text and keyword not in matched_keywords:
                    score -= 0.5

        return score, matched_keywords, matched_patterns

    def _generate_reasoning(
        self, task_type: TaskType, keywords: List[str], patterns: List[str]
    ) -> str:
        """Generate human-readable reasoning for classification."""
        reasons = []

        if patterns:
            reasons.append(f"matched patterns: {', '.join(patterns[:2])}")

        if keywords:
            primary_keywords = [
                k
                for k in keywords
                if k in self.TASK_KEYWORDS[task_type].get("primary", [])
            ]
            if primary_keywords:
                reasons.append(
                    f"contains primary keywords: {', '.join(primary_keywords[:3])}"
                )
            else:
                reasons.append(f"contains keywords: {', '.join(keywords[:3])}")

        if not reasons:
            reasons.append("default classification based on context")

        return f"Classified as {task_type.value} because task {' and '.join(reasons)}"

    def get_suggestions(self, task: Task) -> Dict[str, List[str]]:
        """
        Get suggestions for improving task classification.

        Returns:
            Dict with suggestions for better task naming
        """
        result = self.classify_with_confidence(task)
        suggestions = {}

        if result.confidence < 0.8:
            task_keywords = self.TASK_KEYWORDS.get(result.task_type, {})
            primary = task_keywords.get("primary", [])

            suggestions["improve_clarity"] = [
                f"Consider starting with: {', '.join(primary[:3])}",
                f"Be more specific about the task type",
                "Avoid ambiguous terms that could match multiple types",
            ]

            if not result.matched_patterns:
                suggestions["use_patterns"] = [
                    f"For {result.task_type.value} tasks, try patterns like:",
                    f"- '{primary[0]} [component name]'",
                    f"- '{primary[0]} [feature] for [purpose]'",
                ]

        return suggestions

    def is_type(self, task: Task, task_type: TaskType) -> bool:
        """Check if a task is of a specific type."""
        return self.classify(task) == task_type

    def filter_by_type(self, tasks: List[Task], task_type: TaskType) -> List[Task]:
        """Filter tasks by type."""
        return [task for task in tasks if self.classify(task) == task_type]
