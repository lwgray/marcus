"""
PRD Parser for Marcus Phase 2 Intelligence.

Extracts structured requirements from various PRD formats using AI.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class PRDFormat(Enum):
    """Supported PRD formats."""

    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    USER_STORIES = "user_stories"
    TECHNICAL_SPEC = "technical_spec"


@dataclass
class Feature:
    """Represents a feature extracted from PRD."""

    name: str
    description: str
    priority: str
    user_stories: List[str]
    acceptance_criteria: List[str]
    technical_notes: List[str]
    estimated_complexity: str  # low, medium, high


@dataclass
class TechStack:
    """Technology stack requirements."""

    frontend: List[str]
    backend: List[str]
    database: List[str]
    infrastructure: List[str]
    mobile: List[str]
    external_services: List[str]


@dataclass
class ProjectConstraints:
    """Project constraints and requirements."""

    timeline: Optional[str]
    budget: Optional[str]
    team_size: Optional[int]
    performance_requirements: List[str]
    security_requirements: List[str]
    compliance_requirements: List[str]


@dataclass
class ParsedPRD:
    """Complete parsed PRD structure."""

    title: str
    overview: str
    goals: List[str]
    features: List[Feature]
    tech_stack: TechStack
    constraints: ProjectConstraints
    assumptions: List[str]
    risks: List[str]
    success_metrics: List[str]
    format_detected: PRDFormat


class PRDParser:
    """Extracts structured requirements from various PRD formats."""

    def __init__(self) -> None:
        # Patterns for extracting different types of information
        self.feature_patterns = [
            r"(?i)feature[:\s]*(.+?)(?=\n|feature|requirement|user story|$)",
            r"(?i)requirement[:\s]*(.+?)(?=\n|feature|requirement|user story|$)",
            r"(?i)epic[:\s]*(.+?)(?=\n|epic|feature|requirement|$)",
        ]

        self.user_story_patterns = [
            (
                r"(?i)as\s+a\s+(.+?),?\s+i\s+want\s+(.+?)"
                r"(?:\s+so\s+that\s+(.+?))?(?=\n|as\s+a|$)"
            ),
            r"(?i)user\s+story[:\s]*(.+?)(?=\n|user\s+story|acceptance|$)",
        ]

        self.tech_patterns = {
            "frontend": (
                r"(?i)(react|vue|angular|html|css|javascript|typescript|"
                r"svelte|next\.js)"
            ),
            "backend": (
                r"(?i)(node|express|django|flask|spring|rails|laravel|"
                r"fastapi|.net|java|python|php)"
            ),
            "database": (
                r"(?i)(mysql|postgresql|mongodb|redis|sqlite|dynamodb|"
                r"firestore|cassandra)"
            ),
            "mobile": (
                r"(?i)(ios|android|react\s*native|flutter|swift|kotlin|" r"xamarin)"
            ),
            "infrastructure": (
                r"(?i)(aws|azure|gcp|docker|kubernetes|heroku|vercel|" r"netlify)"
            ),
        }

    async def parse_prd(self, content: str, format_hint: str = "auto") -> ParsedPRD:
        """
        Parse PRD from various formats.

        Parameters
        ----------
        content : str
            PRD text content
        format_hint : str, optional
            Format hint ("auto", "markdown", "plain_text", etc.)

        Returns
        -------
        ParsedPRD
            Parsed PRD structure
        """
        # Detect format if auto
        if format_hint == "auto":
            format_detected = self._detect_format(content)
        else:
            try:
                format_detected = PRDFormat(format_hint)
            except ValueError:
                format_detected = PRDFormat.PLAIN_TEXT

        logger.info(f"Parsing PRD with detected format: {format_detected.value}")

        # Extract basic structure
        title = self._extract_title(content)
        overview = self._extract_overview(content)
        goals = self._extract_goals(content)
        features = await self._extract_features(content)
        tech_stack = self._extract_tech_stack(content)
        constraints = self._extract_constraints(content)
        assumptions = self._extract_assumptions(content)
        risks = self._extract_risks(content)
        success_metrics = self._extract_success_metrics(content)

        return ParsedPRD(
            title=title,
            overview=overview,
            goals=goals,
            features=features,
            tech_stack=tech_stack,
            constraints=constraints,
            assumptions=assumptions,
            risks=risks,
            success_metrics=success_metrics,
            format_detected=format_detected,
        )

    def _detect_format(self, content: str) -> PRDFormat:
        """Detect PRD format from content."""
        content_lower = content.lower()

        # Check for markdown indicators
        if re.search(r"#{1,6}\s", content) or "```" in content:
            return PRDFormat.MARKDOWN

        # Check for user story format
        if re.search(r"as\s+a\s+.+i\s+want", content_lower):
            return PRDFormat.USER_STORIES

        # Check for technical spec indicators
        if any(
            word in content_lower
            for word in ["api", "endpoint", "database", "architecture"]
        ):
            return PRDFormat.TECHNICAL_SPEC

        return PRDFormat.PLAIN_TEXT

    def _extract_title(self, content: str) -> str:
        """Extract project title."""
        lines = content.split("\n")

        # Look for markdown heading
        for line in lines[:10]:  # Check first 10 lines
            match = re.match(r"^#{1,2}\s+(.+)", line)
            if match:
                return match.group(1).strip()

        # Look for title patterns
        title_patterns = [
            r"(?i)title[:\s]*(.+)",
            r"(?i)project[:\s]*(.+)",
            r"(?i)product[:\s]*(.+)",
        ]

        for pattern in title_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()

        # Use first non-empty line as fallback
        for line in lines:
            if line.strip():
                return line.strip()[:100]  # Limit length

        return "Untitled Project"

    def _extract_overview(self, content: str) -> str:
        """Extract project overview/description."""
        overview_patterns = [
            r"(?i)overview[:\n](.*?)(?=\n\n|\n#|\ngoals?|\nfeatures?|$)",
            r"(?i)description[:\n](.*?)(?=\n\n|\n#|\ngoals?|\nfeatures?|$)",
            r"(?i)summary[:\n](.*?)(?=\n\n|\n#|\ngoals?|\nfeatures?|$)",
        ]

        for pattern in overview_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return self._clean_text(match.group(1))

        # Fallback: use first paragraph
        paragraphs = content.split("\n\n")
        if len(paragraphs) > 1:
            return self._clean_text(paragraphs[1])

        return "No overview provided"

    def _extract_goals(self, content: str) -> List[str]:
        """Extract project goals."""
        goals = []

        # Look for goals section
        goals_match = re.search(
            r"(?i)goals?[:\n](.*?)(?=\n\n|\n#|\nfeatures?|\nrequirements?|$)",
            content,
            re.DOTALL,
        )

        if goals_match:
            goals_text = goals_match.group(1)
            # Extract bullet points or numbered lists
            goal_items = re.findall(
                r"(?:^\s*[-*]\s*(.+)|^\s*\d+\.\s*(.+))", goals_text, re.MULTILINE
            )
            for match in goal_items:
                goal = match[0] or match[1]
                if goal.strip():
                    goals.append(self._clean_text(goal))

        return goals

    async def _extract_features(self, content: str) -> List[Feature]:
        """Extract features from PRD."""
        features = []

        # Look for features section
        features_section = self._extract_section(
            content, ["features?", "requirements?", "functionality"]
        )

        if features_section:
            # Split into individual features
            feature_blocks = self._split_features(features_section)

            for block in feature_blocks:
                feature = await self._parse_feature_block(block)
                if feature:
                    features.append(feature)

        return features

    async def _parse_feature_block(self, block: str) -> Optional[Feature]:
        """Parse an individual feature block."""
        lines = block.strip().split("\n")
        if not lines:
            return None

        # First line is usually the feature name
        name = re.sub(r"^\s*[-*\d.]\s*", "", lines[0]).strip()

        description = ""
        user_stories = []
        acceptance_criteria = []
        technical_notes = []
        priority = "medium"

        current_section = "description"

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()

            # Detect section changes
            if any(keyword in line_lower for keyword in ["user story", "user stories"]):
                current_section = "user_stories"
                continue
            elif any(keyword in line_lower for keyword in ["acceptance", "criteria"]):
                current_section = "acceptance"
                continue
            elif any(
                keyword in line_lower for keyword in ["technical", "implementation"]
            ):
                current_section = "technical"
                continue
            elif any(keyword in line_lower for keyword in ["priority"]):
                # Extract priority
                if "high" in line_lower:
                    priority = "high"
                elif "low" in line_lower:
                    priority = "low"
                continue

            # Add to appropriate section
            clean_line = re.sub(r"^\s*[-*]\s*", "", line)

            if current_section == "description":
                description += clean_line + " "
            elif current_section == "user_stories":
                user_stories.append(clean_line)
            elif current_section == "acceptance":
                acceptance_criteria.append(clean_line)
            elif current_section == "technical":
                technical_notes.append(clean_line)

        # Estimate complexity based on content
        complexity = self._estimate_feature_complexity(name + " " + description)

        return Feature(
            name=name,
            description=description.strip(),
            priority=priority,
            user_stories=user_stories,
            acceptance_criteria=acceptance_criteria,
            technical_notes=technical_notes,
            estimated_complexity=complexity,
        )

    def _split_features(self, features_text: str) -> List[str]:
        """Split features section into individual feature blocks."""
        # Split by markdown headers or bullet points

        # Try splitting by headers first
        header_splits = re.split(r"\n#+\s+", features_text)
        if len(header_splits) > 1:
            return [block.strip() for block in header_splits if block.strip()]

        # Split by numbered lists
        numbered_splits = re.split(r"\n\d+\.\s+", features_text)
        if len(numbered_splits) > 1:
            return [block.strip() for block in numbered_splits if block.strip()]

        # Split by bullet points with empty lines
        bullet_splits = re.split(r"\n\s*\n\s*[-*]\s+", features_text)
        if len(bullet_splits) > 1:
            return [block.strip() for block in bullet_splits if block.strip()]

        # Fallback: treat as single feature
        return [features_text.strip()]

    def _extract_tech_stack(self, content: str) -> TechStack:
        """Extract technology stack from content."""
        tech_stack = TechStack(
            frontend=[],
            backend=[],
            database=[],
            infrastructure=[],
            mobile=[],
            external_services=[],
        )

        content_lower = content.lower()

        for category, pattern in self.tech_patterns.items():
            matches = re.findall(pattern, content_lower)
            if matches:
                setattr(tech_stack, category, list(set(matches)))

        # Look for external services
        external_patterns = [
            r"(?i)(stripe|paypal|twilio|sendgrid|aws\s+s3|google\s+analytics|firebase)",
            r"(?i)(auth0|okta|github|google|facebook|twitter)\s+(?:api|oauth|login)",
        ]

        for pattern in external_patterns:
            matches = re.findall(pattern, content_lower)
            tech_stack.external_services.extend(matches)

        # Remove duplicates
        for attr in [
            "frontend",
            "backend",
            "database",
            "infrastructure",
            "mobile",
            "external_services",
        ]:
            current_list = getattr(tech_stack, attr)
            setattr(tech_stack, attr, list(set(current_list)))

        return tech_stack

    def _extract_constraints(self, content: str) -> ProjectConstraints:
        """Extract project constraints."""
        timeline = self._extract_timeline(content)
        budget = self._extract_budget(content)
        team_size = self._extract_team_size(content)

        # Extract requirements
        performance_reqs = self._extract_requirements(
            content, ["performance", "speed", "latency"]
        )
        security_reqs = self._extract_requirements(
            content, ["security", "authentication", "encryption"]
        )
        compliance_reqs = self._extract_requirements(
            content, ["compliance", "gdpr", "hipaa", "sox"]
        )

        return ProjectConstraints(
            timeline=timeline,
            budget=budget,
            team_size=team_size,
            performance_requirements=performance_reqs,
            security_requirements=security_reqs,
            compliance_requirements=compliance_reqs,
        )

    def _extract_timeline(self, content: str) -> Optional[str]:
        """Extract timeline from content."""
        timeline_patterns = [
            r"(?i)timeline[:\s]*(.+?)(?=\n|$)",
            r"(?i)deadline[:\s]*(.+?)(?=\n|$)",
            r"(?i)launch\s+date[:\s]*(.+?)(?=\n|$)",
            r"(?i)(\d+\s+(?:days?|weeks?|months?))",
            r"(?i)(by\s+\w+\s+\d+)",
        ]

        for pattern in timeline_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()

        return None

    def _extract_budget(self, content: str) -> Optional[str]:
        """Extract budget information."""
        budget_patterns = [
            r"(?i)budget[:\s]*(.+?)(?=\n|$)",
            r"(?i)\$[\d,]+",
            r"(?i)(\d+k?)\s+budget",
        ]

        for pattern in budget_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1 if "budget" in pattern else 0).strip()

        return None

    def _extract_team_size(self, content: str) -> Optional[int]:
        """Extract team size."""
        team_patterns = [
            r"(?i)team\s+size[:\s]*(\d+)",
            r"(?i)(\d+)\s+developers?",
            r"(?i)(\d+)\s+people?",
        ]

        for pattern in team_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        return None

    def _extract_requirements(self, content: str, keywords: List[str]) -> List[str]:
        """Extract requirements based on keywords."""
        requirements = []

        for keyword in keywords:
            pattern = rf'(?i){keyword}[:\s]*(.+?)(?=\n|{"|".join(keywords)}|$)'
            matches = re.findall(pattern, content)
            requirements.extend([self._clean_text(match) for match in matches])

        return list(set(requirements))  # Remove duplicates

    def _extract_assumptions(self, content: str) -> List[str]:
        """Extract project assumptions."""
        return self._extract_list_section(content, ["assumptions?", "assume"])

    def _extract_risks(self, content: str) -> List[str]:
        """Extract project risks."""
        return self._extract_list_section(
            content, ["risks?", "challenges?", "concerns?"]
        )

    def _extract_success_metrics(self, content: str) -> List[str]:
        """Extract success metrics."""
        return self._extract_list_section(
            content, [r"success\s+metrics?", "kpis?", "measurements?"]
        )

    def _extract_section(self, content: str, section_names: List[str]) -> Optional[str]:
        """Extract a section by name."""
        for section_name in section_names:
            # Look for section header and extract until next major section or end
            pattern = (
                rf"(?i){section_name}[:\n](.*?)(?=\n\n\n|\n#+\\s|"
                rf"\n[A-Z][^:\n]*:(?:\\s|$)|$)"
            )
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return None

    def _extract_list_section(
        self, content: str, section_names: List[str]
    ) -> List[str]:
        """Extract a list from a section."""
        section_text = self._extract_section(content, section_names)
        if not section_text:
            return []

        # Extract list items
        items = re.findall(
            r"(?:^\s*[-*]\s*(.+)|^\s*\d+\.\s*(.+))", section_text, re.MULTILINE
        )
        return [
            self._clean_text(item[0] or item[1])
            for item in items
            if (item[0] or item[1]).strip()
        ]

    def _estimate_feature_complexity(self, text: str) -> str:
        """Estimate feature complexity based on text."""
        text_lower = text.lower()

        high_complexity_indicators = [
            "integration",
            "api",
            "real-time",
            "performance",
            "scalability",
            "machine learning",
            "ai",
            "complex",
            "advanced",
            "enterprise",
        ]

        low_complexity_indicators = [
            "simple",
            "basic",
            "display",
            "show",
            "list",
            "view",
            "static",
        ]

        high_count = sum(
            1 for indicator in high_complexity_indicators if indicator in text_lower
        )
        low_count = sum(
            1 for indicator in low_complexity_indicators if indicator in text_lower
        )

        if high_count > low_count and high_count >= 2:
            return "high"
        elif low_count > high_count and low_count >= 2:
            return "low"
        else:
            return "medium"

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text.strip())

        # Remove markdown formatting
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # Bold
        text = re.sub(r"\*(.+?)\*", r"\1", text)  # Italic
        text = re.sub(r"`(.+?)`", r"\1", text)  # Code

        return text.strip()
