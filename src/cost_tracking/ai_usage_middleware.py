"""
AI Usage Middleware for Token Tracking

Intercepts all AI provider calls to track token usage per project.
"""

import functools
from typing import Any, Dict, Optional, Callable
import asyncio
from datetime import datetime

from src.cost_tracking.token_tracker import token_tracker
from src.logging.conversation_logger import conversation_logger


class AIUsageMiddleware:
    """
    Middleware that wraps AI provider calls to track token usage.
    
    This intercepts all calls to AI providers (OpenAI, Anthropic, etc.)
    and tracks token consumption per project.
    """
    
    def __init__(self):
        self.current_project_context = {}
        self.token_tracker = token_tracker
        
    def set_project_context(self, agent_id: str, project_id: str, task_id: Optional[str] = None):
        """
        Set the current project context for an agent.
        
        This should be called when an agent starts working on a project/task.
        """
        self.current_project_context[agent_id] = {
            'project_id': project_id,
            'task_id': task_id,
            'start_time': datetime.now()
        }
    
    def clear_project_context(self, agent_id: str):
        """Clear project context when agent finishes."""
        if agent_id in self.current_project_context:
            del self.current_project_context[agent_id]
    
    def get_current_project(self, agent_id: str) -> Optional[str]:
        """Get current project for an agent."""
        context = self.current_project_context.get(agent_id, {})
        return context.get('project_id')
    
    def track_ai_usage(self, func: Callable) -> Callable:
        """
        Decorator to track AI usage for any AI provider method.
        
        This wraps AI provider methods to capture token usage.
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract agent context if available
            agent_id = kwargs.get('agent_id') or getattr(args[0], 'agent_id', None)
            project_id = None
            
            if agent_id:
                project_id = self.get_current_project(agent_id)
            
            # If no project context, try to extract from args
            if not project_id:
                # Check if project_id is in kwargs or context
                project_id = kwargs.get('project_id')
                if not project_id and len(args) > 1 and isinstance(args[1], dict):
                    project_id = args[1].get('project_id')
            
            # Call the original function
            start_time = datetime.now()
            result = await func(*args, **kwargs)
            end_time = datetime.now()
            
            # Extract token usage from result
            if isinstance(result, dict):
                usage = result.get('usage', {})
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
                model = result.get('model', 'unknown')
                
                if input_tokens > 0 or output_tokens > 0:
                    # Track tokens
                    if not project_id:
                        project_id = 'unassigned'
                    
                    stats = await self.token_tracker.track_tokens(
                        project_id=project_id,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        model=model,
                        metadata={
                            'agent_id': agent_id,
                            'task_id': self.current_project_context.get(agent_id, {}).get('task_id'),
                            'duration_ms': (end_time - start_time).total_seconds() * 1000,
                            'function': func.__name__
                        }
                    )
                    
                    # Log significant usage
                    if input_tokens + output_tokens > 1000:
                        conversation_logger.log_pm_thinking(
                            f"AI token usage for {project_id}: {input_tokens + output_tokens} tokens "
                            f"(${stats['total_cost']:.2f} total)",
                            {
                                'project_id': project_id,
                                'tokens': input_tokens + output_tokens,
                                'cost': stats['total_cost'],
                                'rate': stats['current_spend_rate']
                            }
                        )
            
            return result
        
        return wrapper
    
    def wrap_ai_provider(self, provider_instance: Any) -> Any:
        """
        Wrap an AI provider instance to track all its method calls.
        
        This modifies the provider instance to track token usage on all methods
        that make API calls.
        """
        # Methods that typically make AI API calls
        ai_methods = [
            'analyze', 'complete', 'chat', 'generate', 'call_model',
            'generate_task_instructions', 'analyze_blocker', 'generate_response',
            'classify', 'embed', 'summarize'
        ]
        
        for method_name in ai_methods:
            if hasattr(provider_instance, method_name):
                original_method = getattr(provider_instance, method_name)
                if asyncio.iscoroutinefunction(original_method):
                    wrapped_method = self.track_ai_usage(original_method)
                    setattr(provider_instance, method_name, wrapped_method)
        
        return provider_instance


# Global middleware instance
ai_usage_middleware = AIUsageMiddleware()


def track_project_tokens(project_id: str, agent_id: Optional[str] = None):
    """
    Context manager to track AI tokens for a specific project.
    
    Usage:
        with track_project_tokens("project_123", "agent_1"):
            # All AI calls in this block will be tracked to project_123
            await ai_engine.analyze(...)
    """
    class TokenTrackingContext:
        def __init__(self, project_id: str, agent_id: Optional[str]):
            self.project_id = project_id
            self.agent_id = agent_id or 'system'
            
        def __enter__(self):
            ai_usage_middleware.set_project_context(self.agent_id, self.project_id)
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            ai_usage_middleware.clear_project_context(self.agent_id)
            return False
    
    return TokenTrackingContext(project_id, agent_id)