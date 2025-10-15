#!/usr/bin/env python3
"""
MLflow Trace Integration for Marcus Experiments

This module provides decorators and utilities for tracking LLM-based
agent interactions using MLflow Trace.

Features:
- Automatic trace creation for agent tasks
- Prompt/response tracking
- Token usage monitoring
- Error handling and debugging
- Nested spans for complex workflows

Usage:
    from mlflow_tracing import trace_agent_task, trace_llm_call

    @trace_agent_task("user_registration")
    def implement_user_registration(task_data):
        # Your agent logic here
        pass
"""

import mlflow
from mlflow.entities import SpanType
import functools
import time
import json
from typing import Any, Dict, Optional, Callable
from datetime import datetime
import traceback


# Configure MLflow
mlflow.set_tracking_uri("file:./mlruns")


def trace_agent_task(task_name: str, metadata: Optional[Dict] = None):
    """
    Decorator to trace an entire agent task execution.

    Args:
        task_name: Name of the task being executed
        metadata: Additional metadata to attach to the trace

    Example:
        @trace_agent_task("implement_login", {"priority": "high"})
        def implement_login(task_data):
            # Agent implementation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Start the trace
            with mlflow.start_span(
                name=f"task_{task_name}",
                span_type=SpanType.AGENT
            ) as span:
                # Add metadata
                if metadata:
                    span.set_attributes(metadata)

                # Add task information
                span.set_attribute("task_name", task_name)
                span.set_attribute("start_time", datetime.now().isoformat())

                # Add function arguments
                if args:
                    span.set_attribute("args", str(args))
                if kwargs:
                    span.set_attribute("kwargs", json.dumps(kwargs, default=str))

                try:
                    start_time = time.time()

                    # Execute the function
                    result = func(*args, **kwargs)

                    # Track success metrics
                    duration = time.time() - start_time
                    span.set_attribute("duration_seconds", duration)
                    span.set_attribute("status", "success")
                    span.set_attribute("end_time", datetime.now().isoformat())

                    # Add result summary
                    if isinstance(result, dict):
                        span.set_attribute("result_summary", json.dumps(result, default=str)[:500])

                    return result

                except Exception as e:
                    # Track errors
                    span.set_attribute("status", "error")
                    span.set_attribute("error_type", type(e).__name__)
                    span.set_attribute("error_message", str(e))
                    span.set_attribute("traceback", traceback.format_exc())
                    raise

        return wrapper
    return decorator


def trace_llm_call(model: str = "claude-sonnet-4-5", operation: str = "generate"):
    """
    Decorator to trace LLM API calls with detailed prompt/response tracking.

    Args:
        model: Name of the LLM model being used
        operation: Type of operation (generate, chat, embed, etc.)

    Example:
        @trace_llm_call(model="claude-sonnet-4-5", operation="code_generation")
        def generate_code(prompt):
            response = llm.generate(prompt)
            return response
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with mlflow.start_span(
                name=f"llm_{operation}",
                span_type=SpanType.LLM
            ) as span:
                # Track model info
                span.set_attribute("model", model)
                span.set_attribute("operation", operation)

                # Extract prompt from arguments
                prompt = None
                if args:
                    prompt = args[0] if isinstance(args[0], str) else str(args[0])
                elif "prompt" in kwargs:
                    prompt = kwargs["prompt"]

                if prompt:
                    span.set_inputs({"prompt": prompt})
                    span.set_attribute("prompt_length", len(prompt))

                try:
                    start_time = time.time()

                    # Execute LLM call
                    result = func(*args, **kwargs)

                    # Track response metrics
                    duration = time.time() - start_time
                    span.set_attribute("latency_seconds", duration)

                    # Extract response details
                    if isinstance(result, dict):
                        span.set_outputs({"response": result})

                        # Track token usage if available
                        if "usage" in result:
                            span.set_attribute("prompt_tokens", result["usage"].get("prompt_tokens", 0))
                            span.set_attribute("completion_tokens", result["usage"].get("completion_tokens", 0))
                            span.set_attribute("total_tokens", result["usage"].get("total_tokens", 0))

                        # Track response content
                        if "content" in result:
                            span.set_attribute("response_length", len(str(result["content"])))

                    return result

                except Exception as e:
                    span.set_attribute("error", str(e))
                    span.set_attribute("error_type", type(e).__name__)
                    raise

        return wrapper
    return decorator


def trace_tool_call(tool_name: str, tool_type: str = "function"):
    """
    Decorator to trace tool/function calls within agent workflows.

    Args:
        tool_name: Name of the tool being called
        tool_type: Type of tool (function, api, database, etc.)

    Example:
        @trace_tool_call("database_query", "database")
        def query_users(email):
            return db.query(User).filter_by(email=email).first()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with mlflow.start_span(
                name=f"tool_{tool_name}",
                span_type=SpanType.TOOL
            ) as span:
                span.set_attribute("tool_name", tool_name)
                span.set_attribute("tool_type", tool_type)

                # Track inputs
                if args or kwargs:
                    inputs = {
                        "args": [str(arg) for arg in args] if args else [],
                        "kwargs": {k: str(v) for k, v in kwargs.items()} if kwargs else {}
                    }
                    span.set_inputs(inputs)

                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time

                    span.set_attribute("duration_seconds", duration)
                    span.set_attribute("status", "success")

                    # Track outputs
                    if result is not None:
                        output_str = str(result)[:1000]  # Limit output size
                        span.set_outputs({"result": output_str})

                    return result

                except Exception as e:
                    span.set_attribute("error", str(e))
                    span.set_attribute("status", "error")
                    raise

        return wrapper
    return decorator


class TracedExperiment:
    """
    Context manager for MLflow traced experiments.

    Usage:
        with TracedExperiment("my_experiment", run_name="test_run") as exp:
            exp.log_param("learning_rate", 0.001)
            result = my_traced_function()
            exp.log_metric("accuracy", result)
    """

    def __init__(self, experiment_name: str, run_name: Optional[str] = None, tags: Optional[Dict] = None):
        self.experiment_name = experiment_name
        self.run_name = run_name or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.tags = tags or {}
        self.run = None

    def __enter__(self):
        # Set or create experiment
        mlflow.set_experiment(self.experiment_name)

        # Start run with tracing enabled
        self.run = mlflow.start_run(run_name=self.run_name, tags=self.tags)

        # Enable autologging for popular frameworks
        mlflow.autolog(disable=False)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Log the error
            mlflow.log_param("error_occurred", True)
            mlflow.log_param("error_type", exc_type.__name__)
            mlflow.set_tag("status", "failed")
        else:
            mlflow.set_tag("status", "completed")

        mlflow.end_run()

        # Don't suppress exceptions
        return False

    def log_param(self, key: str, value: Any):
        """Log a parameter."""
        mlflow.log_param(key, value)

    def log_metric(self, key: str, value: float, step: Optional[int] = None):
        """Log a metric."""
        mlflow.log_metric(key, value, step=step)

    def log_artifact(self, local_path: str):
        """Log an artifact file."""
        mlflow.log_artifact(local_path)

    def set_tag(self, key: str, value: str):
        """Set a tag."""
        mlflow.set_tag(key, value)


def create_trace_example():
    """
    Example showing how to use MLflow tracing with Marcus agents.
    """

    @trace_agent_task("example_task", metadata={"complexity": "medium"})
    def example_agent_workflow(task_description: str):
        """Example of a traced agent workflow."""

        # Simulated LLM call
        @trace_llm_call(model="claude-sonnet-4-5", operation="code_generation")
        def generate_code(prompt: str):
            # In real usage, this would call the actual LLM
            return {
                "content": "# Generated code here",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            }

        # Simulated tool call
        @trace_tool_call("file_writer", "filesystem")
        def write_code_to_file(code: str, filename: str):
            # In real usage, this would write the file
            return f"Written to {filename}"

        # Execute workflow
        code_result = generate_code(task_description)
        file_result = write_code_to_file(code_result["content"], "output.py")

        return {
            "status": "success",
            "files_created": 1,
            "tokens_used": code_result["usage"]["total_tokens"]
        }

    # Run the example
    with TracedExperiment("tracing_example", run_name="demo") as exp:
        exp.log_param("task_type", "code_generation")
        result = example_agent_workflow("Create a user registration function")
        exp.log_metric("tokens_used", result["tokens_used"])
        print(f"Example completed: {result}")


if __name__ == "__main__":
    print("Running MLflow Trace example...")
    create_trace_example()
    print("\nExample completed! View traces at http://localhost:5000")
    print("Navigate to the 'tracing_example' experiment to see detailed traces.")
