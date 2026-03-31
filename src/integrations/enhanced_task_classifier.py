"""
Enhanced Task Type Classification System.

Provides robust task type identification with expanded keyword lists,
pattern matching, and context-aware classification for 95%+ accuracy.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Pattern, Tuple

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
                "add",  # For "add comments"
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
        TaskType.INTEGRATION: {
            "primary": [
                "integration verification",
                "build verification",
                "smoke test",
                "startup verification",
                "system verification",
            ],
            "secondary": [
                "health check",
                "port check",
                "endpoint verification",
                "runtime verification",
                "startup check",
            ],
            "verbs": [
                "verify integration",
                "verify build",
                "verify startup",
                "smoke test",
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
            r"design\s+(?:the\s+)?(?:data|database)\s+" r"(?:model|schema|structure)",
            r"(?:create|design)\s+(?:ui|ux|user\s+interface|" r"user\s+experience)",
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
            r"write.*tests?",  # Simplified pattern - put first
            r"(?:write|create|add)\s+(?:unit\s+)?tests?\s+(?:for|to)",
            r"(?:test|verify|validate)\s+(?:the\s+)?(?:\w+\s+)?"
            r"(?:functionality|feature|component)",
            r"(?:create|write)\s+(?:integration|e2e|end-to-end)\s+tests?",
            r"(?:ensure|verify|check)\s+(?:that|if)\s+(?:\w+\s+)?(?:works?|functions?)",
            r"(?:add|improve)\s+test\s+coverage",
        ],
        TaskType.DOCUMENTATION: [
            r"(?:document|write\s+documentation)\s+(?:for|about)",
            r"(?:create|write|update)\s+(?:the\s+)?(?:api|user|developer)\s+"
            r"(?:docs|documentation|guide)",
            r"(?:add|write)\s+(?:code\s+)?comments?\s+(?:to|for)",
            r"(?:create|update)\s+(?:the\s+)?readme(?:\.md)?",
            r"(?:write|create)\s+(?:a\s+)?(?:tutorial|guide|manual)",
        ],
        TaskType.DEPLOYMENT: [
            r"(?:deploy|release)\s+(?:to|on)\s+(?:production|staging|live)",
            r"(?:setup|configure)\s+(?:the\s+)?deployment\s+(?:pipeline|process)",
            r"(?:publish|ship)\s+(?:the\s+)?(?:application|app|service)",
            r"(?:rollout|launch)\s+(?:the\s+)?(?:feature|update|version)",
            r"(?:migrate|upgrade)\s+(?:the\s+)?(?:production|live)\s+"
            r"(?:environment|system)",
        ],
        TaskType.INTEGRATION: [
            r"(?:integration|build|startup)\s+verification",
            r"(?:verify|check)\s+(?:the\s+)?(?:build|startup|integration)",
            r"smoke\s+test\s+(?:the\s+)?(?:application|app|project)",
            r"(?:verify|check)\s+(?:the\s+)?(?:app|application)\s+"
            r"(?:works|runs|starts|responds)",
        ],
        TaskType.INFRASTRUCTURE: [
            r"(?:setup|configure)\s+(?:the\s+)?(?:ci/cd|pipeline|automation)",
            r"(?:provision|create)\s+(?:the\s+)?(?:infrastructure|environment)",
            r"(?:configure|setup)\s+(?:the\s+)?(?:monitoring|logging|alerts)",
            r"(?:install|setup)\s+(?:and\s+configure\s+)?(?:docker|kubernetes|k8s)",
            r"(?:create|setup)\s+(?:the\s+)?(?:server|network)"
            r"(?!\s+connection)",  # Exclude "connection"
            r"(?:setup|configure)\s+(?:the\s+)?database\s+"
            r"(?:cluster|infrastructure|environment|server)",  # More specific patterns
        ],
    }

    def __init__(self) -> None:
        """Initialize the enhanced classifier."""
        # Compile patterns for efficiency
        self._compiled_patterns: Dict[TaskType, List[Pattern[str]]] = {}
        for task_type, patterns in self.TASK_PATTERNS.items():
            self._compiled_patterns[task_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def classify(self, task: Task) -> TaskType:
        """
        Classify a task using enhanced logic.

        Args:
            task: Task to classify

        Returns
        -------
        TaskType
            TaskType enum value
        """
        result = self.classify_with_confidence(task)
        return result.task_type

    def classify_with_confidence(self, task: Task) -> ClassificationResult:
        """
        Classify a task and return detailed results with confidence.

        Args:
            task: Task to classify

        Returns
        -------
        ClassificationResult
            ClassificationResult with type, confidence, and reasoning
        """
        # Separate strong signals (name, labels) from weak signals (description)
        # This allows us to weight them appropriately
        task_name = task.name.lower()
        task_description = (task.description or "").lower()
        task_labels = task.labels or []

        # Score each task type
        scores = {}
        matched_keywords = {}
        matched_patterns = {}

        for task_type in TaskType:
            if task_type == TaskType.OTHER:
                continue

            score, keywords, patterns = self._score_task_type(
                task_name=task_name,
                task_description=task_description,
                task_labels=task_labels,
                task_type=task_type,
            )
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

        # GH-180: Removed ambiguous case handling that artificially boosted DESIGN
        # The new weighted scoring system (strong signals > weak signals) makes
        # this override unnecessary and was causing misclassification.
        # Task name and labels are now weighted more heavily than description,
        # so a task named "Implement X" with label "implement" will correctly
        # classify as IMPLEMENTATION even if description contains "design"
        ambiguous_case = False

        # Defensive check: ensure scores is not empty before calling max()
        if not scores:
            return ClassificationResult(
                task_type=TaskType.OTHER,
                confidence=0.0,
                matched_keywords=[],
                matched_patterns=[],
                reasoning="Scores dictionary became empty after processing",
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

        # Calculate base confidence - normalize score to a reasonable range
        if total_score > 0:
            # Better confidence calculation that considers both score and uniqueness
            score_ratio = best_score / total_score if total_score > 0 else 0
            base_confidence = min(best_score / 5.0, 1.0)  # Adjusted scaling
            uniqueness_bonus = score_ratio * 0.15  # Bonus for uniqueness
            confidence = max(0.85, base_confidence + uniqueness_bonus)  # Higher minimum

            # Reduce confidence if we have multiple competing scores
            # (conflicting indicators)
            competing_scores = [score for score in scores.values() if score > 1.0]
            if len(competing_scores) > 1:
                # Get competing scores that aren't the best score
                other_scores = [s for s in competing_scores if s != best_score]
                # Handle edge case where all competing scores equal best_score (ties)
                max_competing = max(other_scores) if other_scores else 0
                if (
                    max_competing > 0 and best_score / max_competing < 3.0
                ):  # More lenient threshold for conflict
                    confidence = min(
                        confidence * 0.6, 0.65
                    )  # Significantly reduce confidence
        else:
            confidence = 0.5

        # Boost confidence if we have strong indicators
        if matched_patterns[best_type]:
            confidence = min(confidence * 1.1, 0.95)

        # Extra boost for tasks with multiple matching keywords
        if len(matched_keywords[best_type]) >= 3:
            confidence = min(confidence * 1.05, 0.95)

        # Reduce confidence for ambiguous cases
        if ambiguous_case:
            confidence = min(confidence * 0.75, 0.75)  # Cap at 0.75 for ambiguous tasks

        # Ensure confidence never exceeds 1.0
        confidence = min(confidence, 1.0)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            best_type,
            matched_keywords[best_type],
            matched_patterns[best_type],
        )

        return ClassificationResult(
            task_type=best_type,
            confidence=confidence,
            matched_keywords=matched_keywords[best_type],
            matched_patterns=matched_patterns[best_type],
            reasoning=reasoning,
        )

    def _score_task_type(
        self,
        task_name: str,
        task_description: str,
        task_labels: list[str],
        task_type: TaskType,
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score how well a task matches a task type.

        Uses weighted scoring where strong signals (task name, labels) have
        higher weight than weak signals (description keywords).

        Args:
            task_name: Task name (strong signal)
            task_description: Task description (weak signal)
            task_labels: Task labels (very strong signal - explicit categorization)
            task_type: TaskType to score against

        Returns
        -------
        tuple
            Tuple of (score, matched_keywords, matched_patterns)
        """
        score = 0.0
        matched_keywords = []
        matched_patterns = []

        keywords_dict = self.TASK_KEYWORDS.get(task_type, {})

        # STRONGEST SIGNAL: Explicit labels (weight: 8.0)
        # Labels are explicit categorization by users/systems
        label_boost = 0.0
        for label in task_labels:
            label_lower = label.lower()
            # Check for direct task type matches
            if (
                label_lower in ["test", "testing", "qa"]
                and task_type == TaskType.TESTING
            ):
                label_boost += 8.0
                matched_keywords.append(label_lower)
            elif (
                label_lower in ["implement", "implementation"]
                and task_type == TaskType.IMPLEMENTATION
            ):
                label_boost += 8.0
                matched_keywords.append(label_lower)
            elif (
                label_lower in ["design", "architecture"]
                and task_type == TaskType.DESIGN
            ):
                label_boost += 8.0
                matched_keywords.append(label_lower)
            elif (
                label_lower in ["documentation", "docs", "readme"]
                and task_type == TaskType.DOCUMENTATION
            ):
                label_boost += 8.0
                matched_keywords.append(label_lower)
            elif (
                label_lower in ["deploy", "deployment", "release"]
                and task_type == TaskType.DEPLOYMENT
            ):
                label_boost += 8.0
                matched_keywords.append(label_lower)
            elif (
                label_lower in ["infrastructure", "devops", "setup"]
                and task_type == TaskType.INFRASTRUCTURE
            ):
                label_boost += 8.0
                matched_keywords.append(label_lower)
            elif (
                label_lower in ["integration", "integration verification"]
                and task_type == TaskType.INTEGRATION
            ):
                label_boost += 8.0
                matched_keywords.append(label_lower)

        score += label_boost

        # Combine name and description for keyword/pattern matching
        # But track which came from name (strong) vs description (weak)
        combined_text = f"{task_name} {task_description} {' '.join(task_labels)}"

        # STRONG SIGNAL: Primary keywords in task name (weight: 5.0-6.0)
        # Medium signal: Primary keywords in description (weight: 1.5-2.0)
        for keyword in keywords_dict.get("primary", []):
            pattern = rf"\b{re.escape(keyword)}s?\b"

            # Check task name first (strong signal)
            name_match = re.search(pattern, task_name)
            desc_match = re.search(pattern, task_description)

            if name_match:
                # Keyword in name is a STRONG signal
                position_weight = 1.2 if name_match.start() < 10 else 1.0

                # EDGE CASE: Database connections are IMPLEMENTATION
                combined_text = f"{task_name} {task_description}".lower()
                if (
                    task_type == TaskType.INFRASTRUCTURE
                    and keyword in ["setup", "configure"]
                    and "database" in combined_text
                    and "connection" in combined_text
                ):
                    # Much lower score to avoid infrastructure classification
                    score += 0.5
                # EDGE CASE: "code" with doc keywords is DOCUMENTATION
                elif (
                    task_type == TaskType.IMPLEMENTATION
                    and keyword == "code"
                    and ("comment" in combined_text or "document" in combined_text)
                ):
                    # Lower score when "code" appears with documentation keywords
                    score += 1.0
                # Special handling for certain keywords
                elif task_type == TaskType.TESTING and keyword in ["test", "testing"]:
                    score += 6.0 * position_weight
                elif task_type == TaskType.IMPLEMENTATION and keyword in [
                    "implement",
                    "build",
                ]:
                    score += 6.0 * position_weight
                elif task_type == TaskType.DESIGN and keyword in ["design", "plan"]:
                    score += 6.0 * position_weight
                else:
                    score += 5.0 * position_weight
                matched_keywords.append(keyword)
            elif desc_match:
                # Keyword only in description is a WEAK signal
                if task_type == TaskType.TESTING and keyword in ["test", "testing"]:
                    score += 2.0
                elif task_type == TaskType.DOCUMENTATION and keyword == "document":
                    score += 2.0
                else:
                    score += 1.5
                matched_keywords.append(keyword)

        # Secondary keywords: moderate weight for name, low weight for description
        for keyword in keywords_dict.get("secondary", []):
            pattern = rf"\b{re.escape(keyword)}s?\b"

            name_match = re.search(pattern, task_name)
            desc_match = re.search(pattern, task_description)

            if name_match:
                # Secondary keyword in name
                score += 2.0
                matched_keywords.append(keyword)
            elif desc_match:
                # Secondary keyword in description only
                if (
                    task_type == TaskType.DOCUMENTATION
                    and keyword == "comments"
                    and ("add" in combined_text or "annotate" in combined_text)
                ):
                    score += 1.5
                else:
                    score += 0.5
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)

        # Verb usage: higher weight in name, lower in description
        for verb in keywords_dict.get("verbs", []):
            name_match = re.search(rf"\b{verb}\b", task_name)
            desc_match = re.search(rf"\b{verb}\b", task_description)

            if name_match:
                # Verb in task name is a strong signal
                # EDGE CASE: Database connections are IMPLEMENTATION
                # "Setup database connections" is implementation, not infra
                combined_text = f"{task_name} {task_description}".lower()
                if (
                    task_type == TaskType.INFRASTRUCTURE
                    and verb in ["setup", "configure"]
                    and "database" in combined_text
                    and "connection" in combined_text
                ):
                    # Much lower score to avoid infrastructure classification
                    score += 0.3
                elif (
                    task_type == TaskType.IMPLEMENTATION
                    and verb in ["setup", "configure"]
                    and "database" in combined_text
                    and "connection" in combined_text
                ):
                    # Higher score to prefer IMPLEMENTATION
                    score += 3.0
                # EDGE CASE: Code comments should be DOCUMENTATION not IMPLEMENTATION
                # "Add code comments" is documentation work, not implementation
                elif (
                    task_type == TaskType.DOCUMENTATION
                    and verb == "add"
                    and "comment" in combined_text
                ):
                    # Very high score for adding comments
                    score += 4.0
                elif (
                    task_type == TaskType.DOCUMENTATION
                    and verb in ["document", "annotate", "comment"]
                    and ("function" in combined_text or "code" in combined_text)
                ):
                    # Higher score for documentation-specific verbs with code context
                    score += 3.5
                # Special handling for implementation verbs
                elif task_type == TaskType.IMPLEMENTATION and verb in [
                    "implement",
                    "build",
                    "create",
                    "develop",
                ]:
                    score += 4.0
                elif task_type == TaskType.TESTING and verb in [
                    "test",
                    "verify",
                    "validate",
                ]:
                    score += 4.0
                elif task_type == TaskType.DESIGN and verb in [
                    "design",
                    "plan",
                    "architect",
                ]:
                    score += 4.0
                else:
                    score += 3.0
                if verb not in matched_keywords:
                    matched_keywords.append(verb)
            elif desc_match:
                # Verb in description is a weak signal
                # Generic verbs in description get very low weight
                if verb in ["update", "create", "write", "add", "build"]:
                    score += 0.3
                elif task_type == TaskType.DOCUMENTATION and verb in [
                    "annotate",
                    "comment",
                    "document",
                ]:
                    score += 1.0
                else:
                    score += 0.5
                if verb not in matched_keywords:
                    matched_keywords.append(verb)

        # Pattern matching: higher weight in name, medium in combined
        for regex_pattern in self._compiled_patterns.get(task_type, []):
            name_match = regex_pattern.search(task_name)
            combined_match = regex_pattern.search(combined_text)

            if name_match:
                # Pattern match in name is very strong
                score += 5.0
                matched_patterns.append(regex_pattern.pattern)
            elif combined_match:
                # Pattern match in description is moderate
                score += 2.0
                if regex_pattern.pattern not in matched_patterns:
                    matched_patterns.append(regex_pattern.pattern)

        # Reduced penalty for conflicting keywords (only in name)
        # Description conflicts don't matter as much
        for other_type in TaskType:
            if other_type == task_type or other_type == TaskType.OTHER:
                continue
            other_keywords = self.TASK_KEYWORDS.get(other_type, {})
            # Only penalize if primary keywords of other types are in task NAME
            for keyword in other_keywords.get("primary", []):
                if keyword in task_name and keyword not in matched_keywords:
                    score -= 0.3  # Reduced penalty

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

        Returns
        -------
        dict
            Dict with suggestions for better task naming
        """
        result = self.classify_with_confidence(task)
        suggestions = {}

        # Only provide suggestions for unclear tasks
        if result.confidence < 0.8 or result.task_type == TaskType.OTHER:
            # For OTHER tasks, provide general suggestions
            if result.task_type == TaskType.OTHER:
                suggestions["improve_clarity"] = [
                    "Consider starting with action words like: design, "
                    "implement, test, document, deploy",
                    "Be more specific about the task type",
                    "Avoid ambiguous terms that could match multiple types",
                ]
            else:
                task_keywords = self.TASK_KEYWORDS.get(result.task_type, {})
                primary = task_keywords.get("primary", [])

                # Only add suggestions if we have keywords for this task type
                if primary:
                    suggestions["improve_clarity"] = [
                        f"Consider starting with: {', '.join(primary[:3])}",
                        "Be more specific about the task type",
                        "Avoid ambiguous terms that could match multiple types",
                    ]

                if not result.matched_patterns and primary:
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
