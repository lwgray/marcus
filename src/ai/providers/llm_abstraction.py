"""
LLM Abstraction Layer for Marcus AI

Provides a unified interface across different LLM providers (Anthropic, OpenAI, local models)
with intelligent fallback and provider switching capabilities.
"""

import logging
import asyncio
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

from src.core.models import Task, Priority
from .base_provider import BaseLLMProvider, SemanticAnalysis, SemanticDependency, EffortEstimate

logger = logging.getLogger(__name__)


class LLMAbstraction:
    """
    Multi-provider LLM abstraction with intelligent fallback
    
    Supports multiple LLM providers with automatic fallback when primary fails.
    Provides a unified interface for all AI operations in Marcus.
    """
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.current_provider = os.getenv('MARCUS_LLM_PROVIDER', 'anthropic')
        self.fallback_providers = ['anthropic', 'openai']
        
        # Initialize providers (deferred to avoid circular imports)
        self.providers = {}
        self._providers_initialized = False
        
        # Performance tracking
        self.provider_stats = {
            provider: {'requests': 0, 'failures': 0, 'avg_response_time': 0.0}
            for provider in self.fallback_providers
        }
        
        logger.info(f"LLM abstraction initialized with primary provider: {self.current_provider}")
    
    def _initialize_providers(self):
        """Initialize available LLM providers (lazy loading to avoid circular imports)"""
        if self._providers_initialized:
            return
        
        try:
            from .anthropic_provider import AnthropicProvider
            self.providers['anthropic'] = AnthropicProvider()
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic provider: {e}")
        
        try:
            from .openai_provider import OpenAIProvider
            self.providers['openai'] = OpenAIProvider()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        # Add local provider if configured
        local_model_path = os.getenv('MARCUS_LOCAL_LLM_PATH')
        if local_model_path:
            try:
                from .local_provider import LocalLLMProvider
                self.providers['local'] = LocalLLMProvider(local_model_path)
            except Exception as e:
                logger.warning(f"Failed to initialize local LLM provider: {e}")
        
        self._providers_initialized = True
    
    async def analyze_task_semantics(self, task: Task, context: Dict[str, Any]) -> SemanticAnalysis:
        """
        Analyze task semantics using the best available provider
        
        Args:
            task: Task to analyze
            context: Project context
            
        Returns:
            Semantic analysis result
        """
        return await self._execute_with_fallback(
            'analyze_task',
            task=task,
            context=context
        )
    
    async def infer_dependencies_semantic(self, tasks: List[Task]) -> List[SemanticDependency]:
        """
        Infer semantic dependencies between tasks
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            List of inferred semantic dependencies
        """
        return await self._execute_with_fallback(
            'infer_dependencies',
            tasks=tasks
        )
    
    async def generate_enhanced_description(self, task: Task, context: Dict[str, Any]) -> str:
        """
        Generate enhanced task description
        
        Args:
            task: Task to enhance
            context: Project context
            
        Returns:
            Enhanced description
        """
        return await self._execute_with_fallback(
            'generate_enhanced_description',
            task=task,
            context=context
        )
    
    async def estimate_effort_intelligently(self, task: Task, context: Dict[str, Any]) -> EffortEstimate:
        """
        Estimate task effort using AI
        
        Args:
            task: Task to estimate
            context: Project context with historical data
            
        Returns:
            Effort estimate with confidence
        """
        return await self._execute_with_fallback(
            'estimate_effort',
            task=task,
            context=context
        )
    
    async def analyze_blocker_and_suggest_solutions(
        self, 
        task: Task, 
        blocker_description: str, 
        severity: str,
        agent: Optional[Dict[str, Any]]
    ) -> List[str]:
        """
        Analyze a blocker and suggest solutions
        
        Args:
            task: Blocked task
            blocker_description: Description of the blocker
            severity: Severity level
            agent: Agent encountering the blocker
            
        Returns:
            List of suggested solutions
        """
        context = {
            'blocker_description': blocker_description,
            'severity': severity,
            'agent': agent
        }
        
        return await self._execute_with_fallback(
            'analyze_blocker',
            task=task,
            blocker=blocker_description,
            context=context
        )
    
    async def _execute_with_fallback(self, method_name: str, **kwargs) -> Any:
        """
        Execute method with automatic provider fallback
        
        Args:
            method_name: Name of method to execute
            **kwargs: Arguments for the method
            
        Returns:
            Result from successful provider
            
        Raises:
            Exception: If all providers fail
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
                self.provider_stats[provider_name]['requests'] += 1
                
                # Execute method
                method = getattr(provider, method_name)
                result = await method(**kwargs)
                
                # Mark fallback usage if not primary
                if hasattr(result, 'fallback_used'):
                    result.fallback_used = provider_name != self.current_provider
                
                logger.debug(f"Successfully executed {method_name} with {provider_name}")
                return result
                
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed for {method_name}: {e}")
                self.provider_stats[provider_name]['failures'] += 1
                last_exception = e
                continue
        
        # All providers failed
        logger.error(f"All providers failed for {method_name}")
        raise Exception(f"All LLM providers failed: {last_exception}")
    
    async def analyze(self, prompt: str, context: Any) -> str:
        """
        Analyze content using LLM
        
        Args:
            prompt: The prompt to analyze
            context: Analysis context
            
        Returns:
            Analysis result as string
        """
        # Ensure providers are initialized before trying to use them
        self._initialize_providers()
        
        return await self._execute_with_fallback(
            'complete',
            prompt=prompt,
            max_tokens=context.max_tokens if hasattr(context, 'max_tokens') else 2000
        )
    
    async def switch_provider(self, provider_name: str) -> bool:
        """
        Switch to a different provider
        
        Args:
            provider_name: Name of provider to switch to
            
        Returns:
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
        """Get performance statistics for all providers"""
        return {
            'current_provider': self.current_provider,
            'available_providers': list(self.providers.keys()),
            'stats': self.provider_stats.copy()
        }
    
    def get_best_provider(self) -> str:
        """
        Determine the best performing provider based on success rate
        
        Returns:
            Name of best performing provider
        """
        best_provider = self.current_provider
        best_success_rate = 0.0
        
        for provider, stats in self.provider_stats.items():
            if provider not in self.providers:
                continue
            
            requests = stats['requests']
            if requests == 0:
                continue
            
            success_rate = 1.0 - (stats['failures'] / requests)
            
            if success_rate > best_success_rate:
                best_success_rate = success_rate
                best_provider = provider
        
        return best_provider
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all providers
        
        Returns:
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
                    status="TODO",
                    priority=Priority.LOW
                )
                
                result = await asyncio.wait_for(
                    provider.analyze_task(test_task, {'project_type': 'test'}),
                    timeout=10.0
                )
                
                health_status[provider_name] = {
                    'status': 'healthy',
                    'response_time': '< 10s',
                    'last_check': 'now'
                }
                
            except asyncio.TimeoutError:
                health_status[provider_name] = {
                    'status': 'timeout',
                    'error': 'Request timed out after 10s'
                }
            except Exception as e:
                health_status[provider_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return health_status