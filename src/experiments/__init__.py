"""
Marcus Experiment Tracking Module.

This module provides comprehensive experiment tracking capabilities
using MLflow for systematic testing and comparison of different
Marcus configurations and conditions.

Key Components
--------------
MarcusExperiment : class
    Main MLflow experiment tracker for Marcus

Usage Example
-------------
>>> from src.experiments import MarcusExperiment
>>>
>>> experiment = MarcusExperiment("50-agent-test")
>>> with experiment.start_run(
...     run_name="twitter-enterprise",
...     params={"num_agents": 50, "complexity": "enterprise"}
... ):
...     experiment.log_velocity(12.5)
...     experiment.log_blocker("agent-1", "task-123", "API timeout")
...     experiment.log_decision("agent-2", "task-456", "Chose PostgreSQL")
"""

from .mlflow_tracker import MarcusExperiment

__all__ = ["MarcusExperiment"]
