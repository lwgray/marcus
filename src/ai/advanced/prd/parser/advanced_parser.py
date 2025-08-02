"""
Advanced PRD Parser main orchestrator.

This module provides the main AdvancedPRDParser class that orchestrates
all the specialized parsing modules.
"""

import logging
from typing import List, Optional

from src.config.hybrid_inference_config import HybridInferenceConfig
from src.intelligence.dependency_inferer_hybrid import HybridDependencyInferer

from .dependency_analyzer import DependencyAnalyzer
from .models import PRDAnalysis, ProjectConstraints, TaskGenerationResult
from .prd_analyzer import PRDAnalyzer
from .resource_analyzer import ResourceAnalyzer
from .risk_assessor import RiskAssessor
from .success_criteria_generator import SuccessCriteriaGenerator
from .task_generator import TaskGenerator
from .task_hierarchy_builder import TaskHierarchyBuilder
from .timeline_predictor import TimelinePredictor

logger = logging.getLogger(__name__)


class AdvancedPRDParser:
    """
    Advanced PRD parser that transforms requirements into actionable tasks.

    This class orchestrates the parsing process using specialized modules
    for different aspects of PRD analysis and task generation.
    """

    def __init__(self, hybrid_config: Optional[HybridInferenceConfig] = None):
        """
        Initialize the PRD parser with all necessary components.

        Parameters
        ----------
        hybrid_config : Optional[HybridInferenceConfig]
            Configuration for hybrid inference
        """
        # Initialize hybrid config
        if hybrid_config is None:
            # Use default HybridInferenceConfig
            hybrid_config = HybridInferenceConfig()

        self.hybrid_config = hybrid_config

        # Initialize dependency inferer
        self.dependency_inferer = HybridDependencyInferer(hybrid_config)

        # Get LLM provider
        llm_provider = self._get_llm_provider()

        # Initialize all specialized modules
        self.prd_analyzer = PRDAnalyzer(llm_provider)
        self.hierarchy_builder = TaskHierarchyBuilder(llm_provider)
        self.task_generator = TaskGenerator(llm_provider)
        self.dependency_analyzer = DependencyAnalyzer(
            llm_provider, self.dependency_inferer
        )
        self.risk_assessor = RiskAssessor(llm_provider)
        self.timeline_predictor = TimelinePredictor(llm_provider)
        self.resource_analyzer = ResourceAnalyzer(llm_provider)
        self.success_generator = SuccessCriteriaGenerator(llm_provider)

        logger.info("Advanced PRD Parser initialized successfully")

    def _get_llm_provider(self):
        """Get LLM provider from hybrid config."""
        from src.ai.providers.llm_abstraction import LLMAbstraction

        # For now, return a default LLM provider
        # This will be mocked in tests anyway
        return LLMAbstraction()

    async def parse_prd_to_tasks(
        self,
        prd_content: str,
        constraints: Optional[ProjectConstraints] = None,
    ) -> TaskGenerationResult:
        """
        Parse PRD content and generate comprehensive task list.

        Parameters
        ----------
        prd_content : str
            Raw PRD document content
        constraints : Optional[ProjectConstraints]
            Project constraints for task generation

        Returns
        -------
        TaskGenerationResult
            Comprehensive task generation results
        """
        logger.info("Starting PRD parsing process")

        # Use default constraints if none provided
        if constraints is None:
            constraints = ProjectConstraints()

        try:
            # Step 1: Deep PRD analysis
            logger.info("Step 1: Analyzing PRD content")
            analysis = await self.prd_analyzer.analyze_prd_deeply(prd_content)

            # Step 2: Generate task hierarchy
            logger.info("Step 2: Generating task hierarchy")
            task_list, hierarchy = await self.hierarchy_builder.generate_task_hierarchy(
                analysis, constraints
            )

            # Step 3: Create detailed tasks
            logger.info("Step 3: Creating detailed tasks")
            project_context = self.prd_analyzer._extract_project_context(prd_content)
            tasks = await self.task_generator.create_detailed_tasks(
                task_list, project_context, constraints
            )

            # Step 4: Infer dependencies
            logger.info("Step 4: Inferring smart dependencies")
            dependencies = await self.dependency_analyzer.infer_smart_dependencies(
                tasks, analysis, constraints
            )

            # Step 5: Assess risks
            logger.info("Step 5: Assessing implementation risks")
            risk_assessment = await self.risk_assessor.assess_implementation_risks(
                analysis, tasks, constraints
            )

            # Step 6: Predict timeline
            logger.info("Step 6: Predicting project timeline")
            timeline = await self.timeline_predictor.predict_timeline(
                tasks, dependencies, constraints
            )

            # Step 7: Analyze resources
            logger.info("Step 7: Analyzing resource requirements")
            resources = await self.resource_analyzer.analyze_resource_requirements(
                analysis, tasks, constraints
            )

            # Step 8: Generate success criteria
            logger.info("Step 8: Generating success criteria")
            success_criteria = await self.success_generator.generate_success_criteria(
                analysis, tasks
            )

            # Calculate confidence
            confidence = self._calculate_generation_confidence(
                analysis, tasks, dependencies
            )

            logger.info(
                f"PRD parsing completed successfully. "
                f"Generated {len(tasks)} tasks with {confidence:.0%} confidence"
            )

            return TaskGenerationResult(
                tasks=tasks,
                task_hierarchy=hierarchy,
                dependencies=dependencies,
                risk_assessment=risk_assessment,
                estimated_timeline=timeline,
                resource_requirements=resources,
                success_criteria=success_criteria,
                generation_confidence=confidence,
            )

        except Exception as e:
            logger.error(f"PRD parsing failed: {e}", exc_info=True)
            raise

    def _calculate_generation_confidence(
        self,
        analysis: PRDAnalysis,
        tasks: List,
        dependencies: List,
    ) -> float:
        """
        Calculate overall confidence in the generated tasks.

        Parameters
        ----------
        analysis : PRDAnalysis
            PRD analysis results
        tasks : List
            Generated tasks
        dependencies : List
            Inferred dependencies

        Returns
        -------
        float
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from analysis
        confidence = analysis.confidence

        # Adjust based on completeness
        if len(tasks) > 0:
            # Task coverage
            avg_task_completeness = sum(
                1 for task in tasks if task.description and task.acceptance_criteria
            ) / len(tasks)
            confidence *= avg_task_completeness

            # Dependency coverage
            if dependencies:
                dep_ratio = len(dependencies) / max(len(tasks) - 1, 1)
                confidence *= min(1.0, 0.8 + 0.2 * dep_ratio)
        else:
            confidence *= 0.1

        # Complexity penalty
        complexity = analysis.complexity_assessment.get("overall", 5)
        confidence *= 1.0 - (complexity - 5) * 0.05

        return max(0.1, min(1.0, confidence))
