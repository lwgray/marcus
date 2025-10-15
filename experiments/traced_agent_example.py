#!/usr/bin/env python3
"""
MLflow Traced Agent Example for Marcus Experiments

This example shows how to integrate MLflow Trace into your
agent spawning experiments.

Usage:
    python experiments/traced_agent_example.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mlflow
from mlflow.entities import SpanType
import time
import asyncio
from src.utils.mlflow_tracing import trace_agent_task, trace_llm_call, TracedExperiment


class TracedMarcusAgent:
    """
    Example Marcus agent with MLflow Trace integration.

    This demonstrates how to add tracing to agent workflows
    in the experiments/ directory.
    """

    def __init__(self, agent_id: str, skills: list):
        self.agent_id = agent_id
        self.skills = skills
        self.tasks_completed = 0

    @trace_agent_task("task_execution")
    def execute_task(self, task: dict):
        """
        Execute a task with automatic tracing.

        This method is decorated to automatically create MLflow traces
        for each task execution, capturing inputs, outputs, and timing.
        """
        print(f"\n🤖 Agent {self.agent_id} executing: {task['name']}")

        with mlflow.start_span(
            name="task_analysis",
            span_type=SpanType.CHAIN
        ) as span:
            # Analyze task
            span.set_attribute("task_id", task.get("id", "unknown"))
            span.set_attribute("task_name", task["name"])
            span.set_attribute("task_description", task.get("description", ""))

            # Check if agent has required skills
            required_skills = task.get("required_skills", [])
            has_skills = all(skill in self.skills for skill in required_skills)
            span.set_attribute("has_required_skills", has_skills)

            if not has_skills:
                span.set_attribute("skip_reason", "missing_skills")
                return {"status": "skipped", "reason": "Missing required skills"}

        # Simulate LLM call for implementation
        implementation = self._generate_implementation(task)

        # Simulate code writing
        files_written = self._write_files(implementation)

        # Simulate testing
        test_results = self._run_tests(files_written)

        self.tasks_completed += 1

        return {
            "status": "completed",
            "implementation": implementation,
            "files_written": files_written,
            "test_results": test_results,
            "tasks_completed": self.tasks_completed
        }

    @trace_llm_call(model="claude-sonnet-4-5", operation="implementation_generation")
    def _generate_implementation(self, task: dict):
        """Generate code implementation using LLM."""
        prompt = f"Implement: {task['name']}\nDescription: {task.get('description', '')}"

        # Simulate LLM call (in real use, call actual LLM API)
        time.sleep(0.5)  # Simulate API latency

        implementation = {
            "code": f"# Implementation for {task['name']}\npass",
            "explanation": f"This implements {task['name']}",
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 50,
                "total_tokens": len(prompt.split()) + 50
            }
        }

        return implementation

    @trace_agent_task("file_writing")
    def _write_files(self, implementation: dict):
        """Write implementation to files."""
        with mlflow.start_span(
            name="filesystem_operations",
            span_type=SpanType.TOOL
        ) as span:
            files = ["main.py", "test_main.py"]
            span.set_attribute("files_to_write", len(files))

            # Simulate file writing
            time.sleep(0.2)

            span.set_outputs({"files_written": files})
            return files

    @trace_agent_task("testing")
    def _run_tests(self, files: list):
        """Run tests on implementation."""
        with mlflow.start_span(
            name="test_execution",
            span_type=SpanType.TOOL
        ) as span:
            span.set_attribute("test_files", len(files))

            # Simulate test execution
            time.sleep(0.3)

            results = {
                "tests_run": 5,
                "tests_passed": 5,
                "tests_failed": 0,
                "coverage": 85.5
            }

            span.set_outputs(results)
            return results


def run_traced_experiment():
    """
    Run a complete traced experiment with multiple agents.

    This example shows how to structure experiments with MLflow Trace
    to capture the entire workflow including agent interactions.
    """

    experiment_name = "traced_multi_agent_experiment"

    with TracedExperiment(
        experiment_name=experiment_name,
        run_name=f"multi_agent_run_{int(time.time())}",
        tags={
            "experiment_type": "traced_agents",
            "framework": "marcus_mcp",
            "agent_count": "3"
        }
    ) as exp:

        print(f"\n{'='*80}")
        print(f"Starting Traced Experiment: {experiment_name}")
        print(f"{'='*80}\n")

        # Log experiment parameters
        exp.log_param("agent_count", 3)
        exp.log_param("task_count", 4)
        exp.log_param("model", "claude-sonnet-4-5")

        # Create agents
        agents = [
            TracedMarcusAgent("agent-1", ["python", "fastapi", "testing"]),
            TracedMarcusAgent("agent-2", ["javascript", "react", "ui"]),
            TracedMarcusAgent("agent-3", ["database", "sql", "postgresql"])
        ]

        # Define tasks
        tasks = [
            {
                "id": "task-1",
                "name": "Create API endpoint",
                "description": "Build REST API for user registration",
                "required_skills": ["python", "fastapi"]
            },
            {
                "id": "task-2",
                "name": "Create UI components",
                "description": "Build React components for user interface",
                "required_skills": ["javascript", "react"]
            },
            {
                "id": "task-3",
                "name": "Design database schema",
                "description": "Create tables for user data",
                "required_skills": ["database", "sql"]
            },
            {
                "id": "task-4",
                "name": "Write integration tests",
                "description": "Test API and UI integration",
                "required_skills": ["python", "testing"]
            }
        ]

        # Execute tasks with tracing
        total_tokens = 0
        total_tests_passed = 0

        for task in tasks:
            # Create a span for each task assignment
            with mlflow.start_span(
                name=f"assign_task_{task['id']}",
                span_type=SpanType.AGENT
            ) as span:

                span.set_attribute("task_name", task["name"])

                # Find best agent for task
                best_agent = None
                for agent in agents:
                    if all(skill in agent.skills for skill in task.get("required_skills", [])):
                        best_agent = agent
                        break

                if best_agent:
                    span.set_attribute("assigned_to", best_agent.agent_id)

                    # Execute task
                    result = best_agent.execute_task(task)

                    # Log metrics
                    if result["status"] == "completed":
                        tokens = result["implementation"]["usage"]["total_tokens"]
                        tests_passed = result["test_results"]["tests_passed"]
                        coverage = result["test_results"]["coverage"]

                        total_tokens += tokens
                        total_tests_passed += tests_passed

                        # Log per-task metrics
                        exp.log_metric(f"task_{task['id']}_tokens", tokens)
                        exp.log_metric(f"task_{task['id']}_coverage", coverage)

                        span.set_attribute("result_status", "completed")
                        span.set_attribute("tokens_used", tokens)
                        span.set_attribute("tests_passed", tests_passed)
                    else:
                        span.set_attribute("result_status", "skipped")
                else:
                    span.set_attribute("assigned_to", "none")
                    span.set_attribute("skip_reason", "no_suitable_agent")

        # Log aggregate metrics
        exp.log_metric("total_tokens_used", total_tokens)
        exp.log_metric("total_tests_passed", total_tests_passed)
        exp.log_metric("tasks_completed", sum(a.tasks_completed for a in agents))

        # Log agent performance
        for agent in agents:
            exp.log_metric(f"agent_{agent.agent_id}_tasks_completed", agent.tasks_completed)

        print(f"\n{'='*80}")
        print(f"Experiment Complete!")
        print(f"Total tokens used: {total_tokens}")
        print(f"Total tests passed: {total_tests_passed}")
        print(f"{'='*80}\n")


def run_async_traced_experiment():
    """
    Example of tracing async agent workflows.

    Shows how to use MLflow Trace with async/await patterns
    common in agent systems.
    """

    async def async_agent_task(agent_id: str, task: dict):
        """Simulated async agent task."""
        with mlflow.start_span(
            name=f"async_task_{task['id']}",
            span_type=SpanType.AGENT
        ) as span:
            span.set_attribute("agent_id", agent_id)
            span.set_attribute("task_name", task["name"])

            # Simulate async work
            await asyncio.sleep(0.5)

            result = {"status": "completed", "agent": agent_id}
            span.set_outputs(result)
            return result

    async def run_async_agents():
        """Run multiple agents concurrently."""
        with TracedExperiment("async_agent_experiment") as exp:
            exp.log_param("execution_mode", "async")

            tasks = [
                {"id": "t1", "name": "Task 1"},
                {"id": "t2", "name": "Task 2"},
                {"id": "t3", "name": "Task 3"}
            ]

            # Run agents concurrently
            results = await asyncio.gather(*[
                async_agent_task(f"agent-{i}", task)
                for i, task in enumerate(tasks)
            ])

            exp.log_metric("tasks_completed", len(results))
            print(f"Async execution completed: {len(results)} tasks")

    # Run the async example
    asyncio.run(run_async_agents())


if __name__ == "__main__":
    print("🔬 MLflow Traced Agent Example\n")

    # Run synchronous traced experiment
    run_traced_experiment()

    # Run async traced experiment
    print("\n" + "="*80)
    print("Running Async Experiment...")
    print("="*80 + "\n")
    run_async_traced_experiment()

    print("\n✅ All experiments complete!")
    print("📊 View traces at: http://localhost:5000")
    print("\nNavigate to:")
    print("  - 'traced_multi_agent_experiment' for the main example")
    print("  - 'async_agent_experiment' for async patterns")
