"""
LLM Abstraction Layer for Marcus AI.

Provides a unified interface across different LLM providers
(Anthropic, OpenAI, local models)
with intelligent fallback and provider switching capabilities.

This module implements the strategy pattern for LLM providers, allowing seamless
switching between providers and automatic fallback on failures.

Classes
-------
LLMAbstraction
    Multi-provider LLM abstraction with intelligent fallback

Notes
-----
Provider selection is controlled by the MARCUS_LLM_PROVIDER environment variable.
The system automatically falls back to alternative providers on failure.

Examples
--------
>>> llm = LLMAbstraction()
>>> analysis = await llm.analyze_task_semantics(task, context)
>>> if analysis.fallback_used:
...     print("Using fallback provider")
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.models import Priority, Task, TaskStatus

from .base_provider import (
    BaseLLMProvider,
    EffortEstimate,
    SemanticAnalysis,
    SemanticDependency,
)

logger = logging.getLogger(__name__)


class LLMAbstraction:
    """

    Multi-provider LLM abstraction with intelligent fallback.

    Supports multiple LLM providers with automatic fallback when primary fails.
    Provides a unified interface for all AI operations in Marcus.

    Attributes
    ----------
    providers : dict
        Available LLM provider instances
    current_provider : str
        Name of the primary provider to use
    fallback_providers : list of str
        Ordered list of providers to try on failure
    provider_stats : dict
        Performance statistics for each provider

    Methods
    -------
    analyze_task_semantics(task, context)
        Analyze task meaning and intent
    infer_dependencies_semantic(tasks)
        Infer logical dependencies between tasks
    generate_enhanced_description(task, context)
        Create improved task descriptions
    estimate_effort_intelligently(task, context)
        AI-powered effort estimation
    analyze_blocker_and_suggest_solutions(task, blocker, severity, agent)
        Analyze blockers and provide solutions

    Notes
    -----
    Providers are initialized lazily to avoid circular imports.
    Statistics are tracked for intelligent provider selection.
    """

    def __init__(self) -> None:
        self.providers: Dict[str, BaseLLMProvider] = {}

        # Get provider from config first, then env var as override
        from src.config.config_loader import get_config

        config = get_config()
        self.current_provider = config.get("ai.provider", "anthropic")

        # Build fallback list based on available providers
        self.fallback_providers: List[str] = []

        # Initialize providers (deferred to avoid circular imports)
        self.providers = {}
        self._providers_initialized = False

        # Performance tracking initialized after providers load
        self.provider_stats: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"LLM abstraction initialized with primary provider: "
            f"{self.current_provider}"
        )

    def _initialize_providers(self) -> None:
        """
        Initialize available LLM providers.

        Uses lazy loading to avoid circular imports. Providers are only
        initialized when first needed.

        Notes
        -----
        Failed provider initialization is logged but doesn't stop the system.
        At least one provider must initialize successfully.
        """
        if self._providers_initialized:
            return

        logger.debug("Starting provider initialization...")

        # Load config to get API keys directly
        try:
            from src.config.config_loader import get_config

            config = get_config()
            ai_config = config.get("ai", {})
        except Exception as e:
            logger.warning(f"Failed to load config, falling back to env vars: {e}")
            ai_config = {}

        # Check if user explicitly configured a provider
        # If so, only initialize that provider (no fallbacks to env vars)
        configured_provider = ai_config.get("provider", "").strip()

        # Try to initialize Anthropic provider
        anthropic_key = ai_config.get("anthropic_api_key", "").strip()
        # Only fall back to env var if no specific provider is configured
        # or if anthropic is the configured provider
        should_fallback_anthropic = (
            not configured_provider or configured_provider == "anthropic"
        )
        if not anthropic_key and should_fallback_anthropic:
            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

        if (
            anthropic_key
            and anthropic_key.startswith("sk-ant-")
            and len(anthropic_key) > 10
            and anthropic_key != "sk-ant-your-api-key-here"
        ):
            try:
                from .anthropic_provider import AnthropicProvider

                # Temporarily set env var for the provider
                os.environ["ANTHROPIC_API_KEY"] = anthropic_key
                self.providers["anthropic"] = AnthropicProvider()
                self.fallback_providers.append("anthropic")
                logger.info("Successfully initialized Anthropic provider")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {e}")
        else:
            logger.debug(
                f"Skipping Anthropic provider - no valid API key configured "
                f"(key present: {bool(anthropic_key)})"
            )

        # Only try OpenAI if we have a valid API key
        openai_key = ai_config.get("openai_api_key", "").strip()
        # Only fall back to env var if no specific provider is configured
        # or if openai is the configured provider
        should_fallback_openai = (
            not configured_provider or configured_provider == "openai"
        )
        if not openai_key and should_fallback_openai:
            openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        if (
            openai_key
            and openai_key.startswith("sk-")
            and len(openai_key) > 10
            and openai_key != "sk-your-openai-key-here"
        ):
            try:
                from .openai_provider import OpenAIProvider

                # Temporarily set env var for the provider
                os.environ["OPENAI_API_KEY"] = openai_key
                self.providers["openai"] = OpenAIProvider()
                self.fallback_providers.append("openai")
                logger.info("Successfully initialized OpenAI provider")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
        else:
            logger.debug(
                f"Skipping OpenAI provider - no valid API key configured "
                f"(key present: {bool(openai_key)})"
            )

        # Add local provider if configured
        local_model_path = ai_config.get("local_model", "").strip()
        # Only fall back to env var if no specific provider is configured
        # or if local is the configured provider
        should_fallback_local = (
            not configured_provider or configured_provider == "local"
        )
        if not local_model_path and should_fallback_local:
            local_model_path = os.getenv("MARCUS_LOCAL_LLM_PATH", "").strip()

        if local_model_path:
            try:
                from .local_provider import LocalLLMProvider

                self.providers["local"] = LocalLLMProvider(local_model_path)
                self.fallback_providers.append("local")
                logger.info(
                    f"Successfully initialized local LLM provider "
                    f"with model: {local_model_path}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize local LLM provider: {e}")

        # Initialize provider stats only for successfully loaded providers
        self.provider_stats = {
            provider: {"requests": 0, "failures": 0, "avg_response_time": 0.0}
            for provider in self.providers.keys()
        }

        # Ensure we have at least one provider
        if not self.providers:
            raise RuntimeError(
                "No LLM providers could be initialized. "
                "Please check your AI configuration."
            )

        # Ensure current provider is available, otherwise use first available
        if self.current_provider not in self.providers:
            self.current_provider = list(self.providers.keys())[0]
            logger.warning(
                f"Requested provider not available, using {self.current_provider}"
            )

        self._providers_initialized = True
        logger.info(f"Initialized providers: {list(self.providers.keys())}")

    async def analyze_task_semantics(
        self, task: Task, context: Dict[str, Any]
    ) -> SemanticAnalysis:
        """
        Analyze task semantics using the best available provider.

        Parameters
        ----------
        task : Task
            Task to analyze for semantic meaning
        context : dict
            Project context including related tasks

        Returns
        -------
        SemanticAnalysis
            Comprehensive semantic analysis including intent and risks

        Notes
        -----
        Automatically falls back to alternative providers on failure.
        """
        result = await self._execute_with_fallback(
            "analyze_task", task=task, context=context
        )
        return result  # type: ignore

    async def infer_dependencies_semantic(
        self, tasks: List[Task]
    ) -> List[SemanticDependency]:
        """
        Infer semantic dependencies between tasks.

        Parameters
        ----------
        tasks : list of Task
            All tasks to analyze for dependencies

        Returns
        -------
        list of SemanticDependency
            Inferred logical relationships between tasks

        Notes
        -----
        Complements rule-based dependency detection with semantic
        understanding.
        """
        result = await self._execute_with_fallback("infer_dependencies", tasks=tasks)
        return result  # type: ignore

    async def generate_enhanced_description(
        self, task: Task, context: Dict[str, Any]
    ) -> str:
        """
        Generate enhanced task description.

        Parameters
        ----------
        task : Task
            Task needing clearer description
        context : dict
            Project context for better understanding

        Returns
        -------
        str
            Enhanced description with more detail and clarity
        """
        result = await self._execute_with_fallback(
            "generate_enhanced_description", task=task, context=context
        )
        return result  # type: ignore

    async def estimate_effort_intelligently(
        self, task: Task, context: Dict[str, Any]
    ) -> EffortEstimate:
        """
        Estimate task effort using AI.

        Parameters
        ----------
        task : Task
            Task to estimate completion time for
        context : dict
            Project context with historical performance data

        Returns
        -------
        EffortEstimate
            AI-powered time estimate with confidence and factors
        """
        result = await self._execute_with_fallback(
            "estimate_effort", task=task, context=context
        )
        return result  # type: ignore

    async def analyze_blocker_and_suggest_solutions(
        self,
        task: Task,
        blocker_description: str,
        severity: str,
        agent: Optional[Dict[str, Any]],
    ) -> List[str]:
        """
        Analyze a blocker and suggest solutions.

        Parameters
        ----------
        task : Task
            The blocked task
        blocker_description : str
            Detailed description of the blocker
        severity : str
            Severity level: 'low', 'medium', or 'high'
        agent : dict, optional
            Agent information for context

        Returns
        -------
        list of str
            Prioritized list of solution suggestions

        Notes
        -----
        Higher severity blockers receive more detailed analysis.
        """
        context = {
            "blocker_description": blocker_description,
            "severity": severity,
            "agent": agent,
        }

        result = await self._execute_with_fallback(
            "analyze_blocker", task=task, blocker=blocker_description, context=context
        )
        return result  # type: ignore

    async def _execute_with_fallback(self, method_name: str, **kwargs: Any) -> Any:
        """
        Execute method with automatic provider fallback.

        Tries the primary provider first, then falls back to alternatives
        in order if the primary fails.

        Parameters
        ----------
        method_name : str
            Name of the provider method to call
        **kwargs
            Arguments to pass to the method

        Returns
        -------
        Any
            Result from the first successful provider

        Raises
        ------
        Exception
            If all providers fail with details of each failure

        Notes
        -----
        Updates provider statistics for intelligent future selection.
        Marks results with fallback_used=True when not using primary.
        """
        # Ensure providers are initialized
        self._initialize_providers()

        providers_to_try = [self.current_provider] + [
            p for p in self.fallback_providers if p != self.current_provider
        ]

        last_exception = None

        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                continue

            provider = self.providers[provider_name]

            try:
                logger.debug(f"Trying {method_name} with provider: {provider_name}")

                # Track request
                self.provider_stats[provider_name]["requests"] += 1

                # Execute method
                method = getattr(provider, method_name)
                result = await method(**kwargs)

                # Mark fallback usage if not primary
                if hasattr(result, "fallback_used"):
                    result.fallback_used = provider_name != self.current_provider

                logger.debug(
                    f"Successfully executed {method_name} with {provider_name}"
                )
                return result

            except Exception as e:
                logger.warning(
                    f"Provider {provider_name} failed for {method_name}: {e}"
                )
                self.provider_stats[provider_name]["failures"] += 1
                last_exception = e
                continue

        # All providers failed
        available_providers = list(self.providers.keys())
        logger.error(
            f"All available providers {available_providers} failed for {method_name}"
        )

        # Provide a more helpful error message
        if not available_providers:
            raise Exception(
                "No AI providers are configured. "
                "Please check your API keys in config_marcus.json. "
                "Make sure keys start with 'sk-ant-' for Anthropic or 'sk-' for OpenAI."
            )
        elif len(available_providers) == 1:
            provider_name = available_providers[0]
            error_msg = f"{provider_name.capitalize()} API error: {last_exception}"
            if "401" in str(last_exception):
                error_msg += (
                    f". Please check that your {provider_name} API key in "
                    f"config_marcus.json is valid and not expired."
                )
            elif "API key" in str(last_exception):
                error_msg = (
                    f"Invalid {provider_name} API key. Please check that your "
                    f"API key in config_marcus.json is correct and starts with "
                    f"'{'sk-ant-' if provider_name == 'anthropic' else 'sk-'}'."
                )
        else:
            error_msg = f"All LLM providers failed. Last error: {last_exception}"

        raise Exception(error_msg)

    async def analyze(self, prompt: str, context: Any) -> str:
        """
        Analyze content using LLM.

        Args
        ----
            prompt: The prompt to analyze
            context: Analysis context

        Returns
        -------
            Analysis result as string
        """
        # Ensure providers are initialized before trying to use them
        self._initialize_providers()

        result = await self._execute_with_fallback(
            "complete",
            prompt=prompt,
            max_tokens=context.max_tokens if hasattr(context, "max_tokens") else 2000,
        )
        return result  # type: ignore

    async def switch_provider(self, provider_name: str) -> bool:
        """
        Switch to a different provider.

        Args
        ----
            provider_name: Name of provider to switch to

        Returns
        -------
            True if switch successful, False otherwise
        """
        if provider_name not in self.providers:
            logger.error(f"Provider {provider_name} not available")
            return False

        old_provider = self.current_provider
        self.current_provider = provider_name

        logger.info(f"Switched LLM provider from {old_provider} to {provider_name}")
        return True

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all providers."""
        return {
            "current_provider": self.current_provider,
            "available_providers": list(self.providers.keys()),
            "stats": self.provider_stats.copy(),
        }

    def get_best_provider(self) -> str:
        """
        Determine the best performing provider based on success rate.

        Returns
        -------
            Name of best performing provider
        """
        best_provider = self.current_provider
        best_success_rate = 0.0

        for provider, stats in self.provider_stats.items():
            if provider not in self.providers:
                continue

            requests = stats["requests"]
            if requests == 0:
                continue

            success_rate = 1.0 - (stats["failures"] / requests)

            if success_rate > best_success_rate:
                best_success_rate = success_rate
                best_provider = provider

        return str(best_provider)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all providers.

        Returns
        -------
            Health status for each provider
        """
        health_status = {}

        for provider_name, provider in self.providers.items():
            try:
                # Simple test request
                test_task = Task(
                    id="health-check",
                    name="Test task",
                    description="Health check test",
                    status=TaskStatus.TODO,
                    priority=Priority.LOW,
                    assigned_to=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    due_date=None,
                    estimated_hours=1.0,
                )

                await asyncio.wait_for(
                    provider.analyze_task(test_task, {"project_type": "test"}),
                    timeout=10.0,
                )

                health_status[provider_name] = {
                    "status": "healthy",
                    "response_time": "< 10s",
                    "last_check": "now",
                }

            except asyncio.TimeoutError:
                health_status[provider_name] = {
                    "status": "timeout",
                    "error": "Request timed out after 10s",
                }
            except Exception as e:
                health_status[provider_name] = {"status": "error", "error": str(e)}

        return health_status
