"""
PRD analysis functionality.

This module handles deep analysis of PRD documents to extract requirements,
objectives, and constraints.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.ai.providers.llm_abstraction import LLMAbstraction
from src.ai.types import AnalysisContext

from .models import PRDAnalysis

logger = logging.getLogger(__name__)


class PRDAnalyzer:
    """Handles deep analysis of PRD documents."""

    def __init__(self, llm_provider: LLMAbstraction):
        """
        Initialize PRD analyzer.

        Parameters
        ----------
        llm_provider : LLMAbstraction
            LLM provider for AI-powered analysis
        """
        self.llm_provider = llm_provider

    async def analyze_prd_deeply(self, prd_content: str) -> PRDAnalysis:
        """
        Perform deep AI-powered analysis of PRD content.

        Parameters
        ----------
        prd_content : str
            Raw PRD document content

        Returns
        -------
        PRDAnalysis
            Comprehensive analysis results
        """
        logger.info("Starting deep PRD analysis")

        # Import error handling utilities at the top
        from src.core.error_framework import AIProviderError, ErrorContext
        from src.core.error_monitoring import record_error_for_monitoring

        # Extract project context first
        project_context = self._extract_project_context(prd_content)

        analysis_prompt = f"""
        Analyze this Product Requirements Document (PRD) and extract comprehensive information.

        PRD Content:
        {prd_content[:8000]}  # Limit for context window

        Extract and structure the following:

        1. Functional Requirements:
           - Core features and capabilities
           - User interactions and workflows
           - Data processing requirements
           - Integration points

        2. Non-Functional Requirements:
           - Performance targets
           - Security requirements
           - Scalability needs
           - Reliability standards
           - Usability requirements

        3. Technical Constraints:
           - Technology limitations
           - Platform requirements
           - API constraints
           - Infrastructure limitations

        4. Business Objectives:
           - Primary goals
           - Success metrics
           - Market positioning
           - ROI expectations

        5. User Personas:
           - Target users
           - Use cases
           - Pain points
           - Expected benefits

        6. Implementation Approach:
           - Recommended architecture
           - Development methodology
           - Phasing strategy
           - Risk mitigation

        7. Complexity Assessment:
           - Technical complexity (1-10)
           - Business complexity (1-10)
           - Integration complexity (1-10)
           - Timeline risk (1-10)

        8. Risk Factors:
           - Technical risks
           - Business risks
           - Resource risks
           - External dependencies

        Return as structured JSON with clear categorization.
        """

        try:
            # Create a simple context object with max_tokens
            class SimpleContext:
                max_tokens = 2000

            result = await self.llm_provider.analyze(
                analysis_prompt,
                context=SimpleContext(),
            )

            # Check for None or empty result
            if result is None or (isinstance(result, str) and not result.strip()):
                error = AIProviderError(
                    provider_name="LLM",
                    operation="prd_analysis",
                    context=ErrorContext(
                        operation="prd_analysis",
                        custom_context={
                            "prd_length": len(prd_content),
                            "prd_preview": (
                                prd_content[:200] + "..."
                                if len(prd_content) > 200
                                else prd_content
                            ),
                            "original_error": "Empty or None response from AI provider",
                            "troubleshooting_steps": [
                                "Check AI provider API credentials and configuration",
                                "Verify network connectivity to AI provider",
                                "Try simplifying the project description",
                                "Check AI provider service status",
                                "Ensure project description is in English and well-structured",
                            ],
                            "details": "AI analysis of project requirements failed. This prevents automatic task generation. Please check your AI configuration and try again.",
                        },
                    ),
                )
                record_error_for_monitoring(error)
                raise error

            # Handle different result types
            if hasattr(result, "parsed_data"):
                analysis_data = result.parsed_data
            elif isinstance(result, str):
                # Parse JSON from string result
                import json

                try:
                    analysis_data = json.loads(result)
                except json.JSONDecodeError as je:
                    # Handle JSON parsing errors
                    error = AIProviderError(
                        provider_name="LLM",
                        operation="prd_analysis",
                        context=ErrorContext(
                            operation="prd_analysis",
                            custom_context={
                                "prd_length": len(prd_content),
                                "prd_preview": (
                                    prd_content[:200] + "..."
                                    if len(prd_content) > 200
                                    else prd_content
                                ),
                                "original_error": f"JSON parsing error: {str(je)}",
                                "troubleshooting_steps": [
                                    "Check AI provider API credentials and configuration",
                                    "Verify network connectivity to AI provider",
                                    "Try simplifying the project description",
                                    "Check AI provider service status",
                                    "Ensure project description is in English and well-structured",
                                ],
                                "details": "AI analysis of project requirements failed. This prevents automatic task generation. Please check your AI configuration and try again.",
                            },
                        ),
                    )
                    record_error_for_monitoring(error)
                    raise error
            else:
                analysis_data = result

            # Create PRDAnalysis object
            analysis = PRDAnalysis(
                functional_requirements=self._extract_functional_requirements(
                    analysis_data
                ),
                non_functional_requirements=self._extract_nfr(analysis_data),
                technical_constraints=analysis_data.get("technical_constraints", []),
                business_objectives=analysis_data.get("business_objectives", []),
                user_personas=analysis_data.get("user_personas", []),
                success_metrics=analysis_data.get("success_metrics", []),
                implementation_approach=analysis_data.get(
                    "implementation_approach", "Agile iterative development"
                ),
                complexity_assessment=analysis_data.get("complexity_assessment", {}),
                risk_factors=analysis_data.get("risk_factors", []),
                confidence=analysis_data.get("confidence", 0.8),
            )

            # Filter by project size if context available
            if project_context.get("project_size"):
                analysis = self._filter_analysis_by_size(
                    analysis, project_context["project_size"]
                )

            return analysis

        except ConnectionError as e:
            # Handle connection errors specifically
            error = AIProviderError(
                provider_name="LLM",
                operation="prd_analysis",
                context=ErrorContext(
                    operation="prd_analysis",
                    custom_context={
                        "prd_length": len(prd_content),
                        "prd_preview": (
                            prd_content[:200] + "..."
                            if len(prd_content) > 200
                            else prd_content
                        ),
                        "original_error": str(e),
                        "troubleshooting_steps": [
                            "Check AI provider API credentials and configuration",
                            "Verify network connectivity to AI provider",
                            "Try simplifying the project description",
                            "Check AI provider service status",
                            "Ensure project description is in English and well-structured",
                        ],
                        "details": "AI analysis of project requirements failed. This prevents automatic task generation. Please check your AI configuration and try again.",
                    },
                ),
            )
            record_error_for_monitoring(error)
            raise error
        except TimeoutError as e:
            # Handle timeout errors
            error = AIProviderError(
                provider_name="LLM",
                operation="prd_analysis",
                context=ErrorContext(
                    operation="prd_analysis",
                    custom_context={
                        "prd_length": len(prd_content),
                        "prd_preview": (
                            prd_content[:200] + "..."
                            if len(prd_content) > 200
                            else prd_content
                        ),
                        "original_error": str(e),
                        "troubleshooting_steps": [
                            "Check AI provider API credentials and configuration",
                            "Verify network connectivity to AI provider",
                            "Try simplifying the project description",
                            "Check AI provider service status",
                            "Ensure project description is in English and well-structured",
                        ],
                        "details": "AI analysis of project requirements failed. This prevents automatic task generation. Please check your AI configuration and try again.",
                    },
                ),
            )
            record_error_for_monitoring(error)
            raise error
        except (ValueError, PermissionError, RuntimeError) as e:
            # Handle other specific errors
            error = AIProviderError(
                provider_name="LLM",
                operation="prd_analysis",
                context=ErrorContext(
                    operation="prd_analysis",
                    custom_context={
                        "prd_length": len(prd_content),
                        "prd_preview": (
                            prd_content[:200] + "..."
                            if len(prd_content) > 200
                            else prd_content
                        ),
                        "original_error": str(e),
                        "troubleshooting_steps": [
                            "Check AI provider API credentials and configuration",
                            "Verify network connectivity to AI provider",
                            "Try simplifying the project description",
                            "Check AI provider service status",
                            "Ensure project description is in English and well-structured",
                        ],
                        "details": "AI analysis of project requirements failed. This prevents automatic task generation. Please check your AI configuration and try again.",
                    },
                ),
            )
            record_error_for_monitoring(error)
            raise error
        except AIProviderError:
            # Re-raise AIProviderError so it propagates properly
            raise
        except Exception as e:
            logger.error(f"PRD analysis failed: {e}")
            # For unexpected errors, still return minimal analysis
            return PRDAnalysis(
                functional_requirements=[],
                non_functional_requirements=[],
                technical_constraints=[],
                business_objectives=[],
                user_personas=[],
                success_metrics=[],
                implementation_approach="Standard development",
                complexity_assessment={"overall": 5},
                risk_factors=[],
                confidence=0.3,
            )

    def _extract_project_context(self, prd_content: str) -> Dict[str, Any]:
        """
        Extract project context from PRD content.

        Parameters
        ----------
        prd_content : str
            Raw PRD content

        Returns
        -------
        Dict[str, Any]
            Extracted project context
        """
        context = {
            "project_size": "medium",  # default
            "deployment_target": "local",
            "team_size": 3,
            "duration": "3-6 months",
            "tech_stack": [],
            "is_mvp": False,
            "has_existing_codebase": False,
        }

        # Convert to lowercase for pattern matching
        content_lower = prd_content.lower()

        # Detect project size
        if any(
            word in content_lower
            for word in ["mvp", "prototype", "poc", "proof of concept"]
        ):
            context["project_size"] = "small"
            context["is_mvp"] = True
        elif any(
            word in content_lower
            for word in ["enterprise", "large-scale", "mission-critical"]
        ):
            context["project_size"] = "large"

        # Detect deployment target
        if "production" in content_lower or "prod " in content_lower:
            context["deployment_target"] = "prod"
        elif "staging" in content_lower or "development" in content_lower:
            context["deployment_target"] = "dev"
        elif "remote" in content_lower or "cloud" in content_lower:
            context["deployment_target"] = "remote"

        # Extract team size
        team_match = re.search(r"team\s*(?:of|size)?\s*(\d+)", content_lower)
        if team_match:
            context["team_size"] = int(team_match.group(1))

        # Extract duration
        duration_patterns = [
            (r"(\d+)\s*weeks?", lambda x: f"{x} weeks"),
            (r"(\d+)\s*months?", lambda x: f"{x} months"),
            (r"(\d+)-(\d+)\s*months?", lambda x, y: f"{x}-{y} months"),
        ]

        for pattern, formatter in duration_patterns:
            match = re.search(pattern, content_lower)
            if match:
                context["duration"] = formatter(*match.groups())
                break

        # Extract tech stack
        tech_keywords = [
            "python",
            "javascript",
            "typescript",
            "react",
            "vue",
            "angular",
            "node",
            "django",
            "flask",
            "fastapi",
            "postgresql",
            "mysql",
            "mongodb",
            "redis",
            "docker",
            "kubernetes",
            "aws",
            "gcp",
            "azure",
        ]

        found_tech = []
        for tech in tech_keywords:
            if tech in content_lower:
                found_tech.append(tech)

        context["tech_stack"] = found_tech

        # Check for existing codebase
        if any(
            phrase in content_lower
            for phrase in ["existing", "legacy", "refactor", "migrate"]
        ):
            context["has_existing_codebase"] = True

        return context

    def _extract_functional_requirements(
        self, analysis_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract and structure functional requirements."""
        requirements = analysis_data.get("functional_requirements", [])

        # Ensure each requirement has required fields
        structured_reqs = []
        for req in requirements:
            if isinstance(req, str):
                req = {"description": req}

            structured_req = {
                "id": req.get("id", f"FR-{len(structured_reqs) + 1}"),
                "description": req.get("description", ""),
                "category": req.get("category", "feature"),
                "priority": req.get("priority", "medium"),
                "complexity": req.get("complexity", "medium"),
            }
            structured_reqs.append(structured_req)

        return structured_reqs

    def _extract_nfr(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and structure non-functional requirements."""
        nfrs = analysis_data.get("non_functional_requirements", [])

        structured_nfrs = []
        for nfr in nfrs:
            if isinstance(nfr, str):
                nfr = {"description": nfr}

            structured_nfr = {
                "id": nfr.get("id", f"NFR-{len(structured_nfrs) + 1}"),
                "description": nfr.get("description", ""),
                "category": nfr.get("category", "quality"),
                "metric": nfr.get("metric", ""),
                "target": nfr.get("target", ""),
            }
            structured_nfrs.append(structured_nfr)

        return structured_nfrs

    def _filter_analysis_by_size(
        self, analysis: PRDAnalysis, project_size: str
    ) -> PRDAnalysis:
        """
        Filter analysis results based on project size.

        Parameters
        ----------
        analysis : PRDAnalysis
            Original analysis
        project_size : str
            Project size (small, medium, large)

        Returns
        -------
        PRDAnalysis
            Filtered analysis
        """
        if project_size == "small":
            # For small projects, focus on core requirements
            analysis.functional_requirements = self._filter_requirements_by_size(
                analysis.functional_requirements, project_size
            )
            analysis.non_functional_requirements = self._filter_nfrs_by_size(
                analysis.non_functional_requirements, project_size
            )

        return analysis

    def _filter_requirements_by_size(
        self, requirements: List[Dict[str, Any]], project_size: str
    ) -> List[Dict[str, Any]]:
        """Filter functional requirements based on project size."""
        if project_size == "small":
            # For small projects, only include high priority and low complexity
            return [
                req
                for req in requirements
                if req.get("priority") in ["critical", "high"]
                or req.get("complexity") == "low"
            ]
        return requirements

    def _filter_nfrs_by_size(
        self, nfrs: List[Dict[str, Any]], project_size: str
    ) -> List[Dict[str, Any]]:
        """Filter non-functional requirements based on project size."""
        if project_size == "small":
            # For small projects, focus on essential NFRs
            essential_categories = ["security", "usability", "reliability"]
            return [nfr for nfr in nfrs if nfr.get("category") in essential_categories]
        return nfrs
