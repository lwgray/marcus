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

import functools
import json
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import mlflow
from mlflow.entities import SpanType

# Configure MLflow
mlflow.set_tracking_uri("file:./mlruns")


def trace_agent_task(
    task_name: str, metadata: Optional[Dict[str, Any]] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Trace an entire agent task execution.

    Decorator that automatically creates MLflow traces for agent tasks,
    capturing inputs, outputs, timing, and metadata.

    Parameters
    ----------
    task_name : str
        Name of the task being executed.
    metadata : dict, optional
        Additional metadata to attach to the trace.

    Returns
    -------
    Callable
        Decorated function with automatic tracing.

    Examples
    --------
    >>> @trace_agent_task("implement_login", {"priority": "high"})
    ... def implement_login(task_data):
    ...     return {"status": "completed"}
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Start the trace
            with mlflow.start_span(
                name=f"task_{task_name}", span_type=SpanType.AGENT
            ) as span:
                # Add metadata
                if metadata:
                    span.set_attributes(metadata)

                # Add task information
                span.set_attribute("task_name", task_name)
                span.set_attribute("start_time", datetime.now(timezone.utc).isoformat())

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
                    span.set_attribute(
                        "end_time", datetime.now(timezone.utc).isoformat()
                    )

                    # Add result summary
                    if isinstance(result, dict):
                        span.set_attribute(
                            "result_summary", json.dumps(result, default=str)[:500]
                        )

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


def trace_llm_call(
    model: str = "claude-sonnet-4-5", operation: str = "generate"
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Trace LLM API calls with detailed prompt/response tracking.

    Decorator that automatically tracks LLM calls, capturing prompts,
    responses, token usage, and latency.

    Parameters
    ----------
    model : str, optional
        Name of the LLM model being used, by default "claude-sonnet-4-5".
    operation : str, optional
        Type of operation (generate, chat, embed, etc.), by default "generate".

    Returns
    -------
    Callable
        Decorated function with automatic LLM call tracing.

    Examples
    --------
    >>> @trace_llm_call(model="claude-sonnet-4-5", operation="code_generation")
    ... def generate_code(prompt):
    ...     return {"content": "code", "usage": {"total_tokens": 150}}
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with mlflow.start_span(
                name=f"llm_{operation}", span_type=SpanType.LLM
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
                            span.set_attribute(
                                "prompt_tokens", result["usage"].get("prompt_tokens", 0)
                            )
                            span.set_attribute(
                                "completion_tokens",
                                result["usage"].get("completion_tokens", 0),
                            )
                            span.set_attribute(
                                "total_tokens", result["usage"].get("total_tokens", 0)
                            )

                        # Track response content
                        if "content" in result:
                            span.set_attribute(
                                "response_length", len(str(result["content"]))
                            )

                    return result

                except Exception as e:
                    span.set_attribute("error", str(e))
                    span.set_attribute("error_type", type(e).__name__)
                    raise

        return wrapper

    return decorator


def trace_tool_call(
    tool_name: str, tool_type: str = "function"
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Trace tool/function calls within agent workflows.

    Decorator that automatically tracks tool usage, capturing inputs,
    outputs, and execution time.

    Parameters
    ----------
    tool_name : str
        Name of the tool being called.
    tool_type : str, optional
        Type of tool (function, api, database, etc.), by default "function".

    Returns
    -------
    Callable
        Decorated function with automatic tool call tracing.

    Examples
    --------
    >>> @trace_tool_call("database_query", "database")
    ... def query_users(email):
    ...     return {"user_id": "123", "email": email}
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with mlflow.start_span(
                name=f"tool_{tool_name}", span_type=SpanType.TOOL
            ) as span:
                span.set_attribute("tool_name", tool_name)
                span.set_attribute("tool_type", tool_type)

                # Track inputs
                if args or kwargs:
                    inputs = {
                        "args": [str(arg) for arg in args] if args else [],
                        "kwargs": (
                            {k: str(v) for k, v in kwargs.items()} if kwargs else {}
                        ),
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
    """Context manager for MLflow traced experiments.

    Provides a convenient way to manage MLflow experiment lifecycle,
    automatically handling experiment creation, run management, and cleanup.

    Parameters
    ----------
    experiment_name : str
        Name of the MLflow experiment.
    run_name : str, optional
        Name for the specific run. Auto-generated if not provided.
    tags : dict, optional
        Tags to attach to the run.

    Examples
    --------
    >>> with TracedExperiment("my_experiment", run_name="test_run") as exp:
    ...     exp.log_param("learning_rate", 0.001)
    ...     result = my_traced_function()
    ...     exp.log_metric("accuracy", result)
    """

    def __init__(
        self,
        experiment_name: str,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize TracedExperiment context manager."""
        self.experiment_name = experiment_name
        self.run_name = (
            run_name or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )
        self.tags = tags or {}
        self.run: Optional[Any] = None

    def __enter__(self) -> "TracedExperiment":
        """Enter the context manager and start MLflow run."""
        # Set or create experiment
        mlflow.set_experiment(self.experiment_name)

        # Start run with tracing enabled
        self.run = mlflow.start_run(run_name=self.run_name, tags=self.tags)

        # Enable autologging for popular frameworks
        mlflow.autolog(disable=False)

        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Exit the context manager and end MLflow run."""
        if exc_type:
            # Log the error
            mlflow.log_param("error_occurred", True)
            mlflow.log_param("error_type", exc_type.__name__)
            mlflow.set_tag("status", "failed")
        else:
            mlflow.set_tag("status", "completed")

        mlflow.end_run()

    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter to MLflow.

        Parameters
        ----------
        key : str
            Parameter name.
        value : Any
            Parameter value.
        """
        mlflow.log_param(key, value)

    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        """Log a metric to MLflow.

        Parameters
        ----------
        key : str
            Metric name.
        value : float
            Metric value.
        step : int, optional
            Step number for the metric.
        """
        mlflow.log_metric(key, value, step=step)

    def log_artifact(self, local_path: str) -> None:
        """Log an artifact file to MLflow.

        Parameters
        ----------
        local_path : str
            Path to the artifact file to log.
        """
        mlflow.log_artifact(local_path)

    def set_tag(self, key: str, value: str) -> None:
        """Set a tag in MLflow.

        Parameters
        ----------
        key : str
            Tag name.
        value : str
            Tag value.
        """
        mlflow.set_tag(key, value)


def create_trace_example() -> None:
    """Demonstrate MLflow tracing with Marcus agents.

    Shows how to use MLflow Trace decorators and context managers
    with a simulated agent workflow including LLM calls and tool usage.
    """

    @trace_agent_task("example_task", metadata={"complexity": "medium"})
    def example_agent_workflow(task_description: str) -> Dict[str, Any]:
        """Execute a traced agent workflow.

        Parameters
        ----------
        task_description : str
            Description of the task to execute.

        Returns
        -------
        Dict[str, Any]
            Status and metrics from the workflow execution.
        """

        # Simulated LLM call
        @trace_llm_call(model="claude-sonnet-4-5", operation="code_generation")
        def generate_code(prompt: str) -> Dict[str, Any]:
            """Generate code using LLM (simulated)."""
            # In real usage, this would call the actual LLM
            return {
                "content": "# Generated code here",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            }

        # Simulated tool call
        @trace_tool_call("file_writer", "filesystem")
        def write_code_to_file(code: str, filename: str) -> str:
            """Write code to file (simulated)."""
            # In real usage, this would write the file
            return f"Written to {filename}"

        # Execute workflow
        code_result = generate_code(task_description)
        write_code_to_file(code_result["content"], "output.py")

        return {
            "status": "success",
            "files_created": 1,
            "tokens_used": code_result["usage"]["total_tokens"],
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
