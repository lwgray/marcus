"""
Test infrastructure utilities for Marcus.

This module provides utilities for test execution, flaky test handling,
performance baselines, and test health monitoring.
"""

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionMetrics:
    """Metrics collected during test execution."""

    test_name: str
    execution_time: float
    memory_usage: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MetricsCollector:
    """Collects and stores test execution metrics."""

    def __init__(self, metrics_file: str = "tests/test_metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(exist_ok=True)
        self.current_metrics: List[ExecutionMetrics] = []

    def record_test_execution(
        self,
        test_name: str,
        execution_time: float,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """Record metrics for a test execution."""
        metric = ExecutionMetrics(
            test_name=test_name,
            execution_time=execution_time,
            success=success,
            error_message=error_message,
        )
        self.current_metrics.append(metric)

    def save_metrics(self):
        """Save collected metrics to file."""
        existing_data = []
        if self.metrics_file.exists():
            with open(self.metrics_file, "r") as f:
                existing_data = json.load(f)

        # Append new metrics
        new_data = [asdict(metric) for metric in self.current_metrics]
        existing_data.extend(new_data)

        with open(self.metrics_file, "w") as f:
            json.dump(existing_data, f, indent=2)

        self.current_metrics.clear()

    def get_baseline_metrics(self, test_name: str) -> Optional[Dict[str, Any]]:
        """Get baseline metrics for a test."""
        if not self.metrics_file.exists():
            return None

        with open(self.metrics_file, "r") as f:
            data = json.load(f)

        # Find recent successful runs for this test
        recent_runs = [
            metric
            for metric in data
            if metric["test_name"] == test_name and metric["success"]
        ]

        if not recent_runs:
            return None

        # Calculate averages from recent runs
        recent_runs = recent_runs[-10:]  # Last 10 successful runs
        avg_time = sum(run["execution_time"] for run in recent_runs) / len(recent_runs)

        return {
            "average_execution_time": avg_time,
            "sample_size": len(recent_runs),
            "last_updated": recent_runs[-1]["timestamp"],
        }


class FlakyHandler:
    """Handles flaky test detection and retry logic."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.flaky_tests_file = Path("tests/flaky_tests.json")

    def is_flaky_test(self, test_name: str) -> bool:
        """Check if a test is marked as flaky."""
        if not self.flaky_tests_file.exists():
            return False

        with open(self.flaky_tests_file, "r") as f:
            flaky_tests = json.load(f)

        return test_name in flaky_tests.get("flaky_tests", [])

    def mark_as_flaky(self, test_name: str, reason: str = ""):
        """Mark a test as flaky."""
        flaky_data = {"flaky_tests": {}, "last_updated": datetime.now().isoformat()}

        if self.flaky_tests_file.exists():
            with open(self.flaky_tests_file, "r") as f:
                flaky_data = json.load(f)

        flaky_data["flaky_tests"][test_name] = {
            "reason": reason,
            "marked_at": datetime.now().isoformat(),
        }

        with open(self.flaky_tests_file, "w") as f:
            json.dump(flaky_data, f, indent=2)

    def execute_with_retry(self, test_func, test_name: str):
        """Execute a test with retry logic for flaky tests."""
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                result = test_func()
                execution_time = time.time() - start_time

                # Record successful execution
                metrics_collector.record_test_execution(
                    test_name, execution_time, success=True
                )
                return result

            except Exception as e:
                execution_time = time.time() - start_time

                if attempt == self.max_retries:
                    # Final attempt failed
                    metrics_collector.record_test_execution(
                        test_name, execution_time, success=False, error_message=str(e)
                    )
                    raise

                # Wait before retry with exponential backoff
                wait_time = self.backoff_factor * (2**attempt)
                time.sleep(wait_time)


class PerformanceBaseline:
    """Manages performance baselines for tests."""

    def __init__(self, baseline_file: str = "tests/performance_baselines.json"):
        self.baseline_file = Path(baseline_file)
        self.baseline_file.parent.mkdir(exist_ok=True)

    def set_baseline(
        self, test_name: str, metric_name: str, value: float, tolerance: float = 0.2
    ):
        """Set a performance baseline for a test."""
        baselines = {}
        if self.baseline_file.exists():
            with open(self.baseline_file, "r") as f:
                baselines = json.load(f)

        if test_name not in baselines:
            baselines[test_name] = {}

        baselines[test_name][metric_name] = {
            "value": value,
            "tolerance": tolerance,
            "set_at": datetime.now().isoformat(),
        }

        with open(self.baseline_file, "w") as f:
            json.dump(baselines, f, indent=2)

    def check_baseline(
        self, test_name: str, metric_name: str, current_value: float
    ) -> Dict[str, Any]:
        """Check current value against baseline."""
        if not self.baseline_file.exists():
            return {"status": "no_baseline", "message": "No baseline set"}

        with open(self.baseline_file, "r") as f:
            baselines = json.load(f)

        if test_name not in baselines or metric_name not in baselines[test_name]:
            return {"status": "no_baseline", "message": "No baseline set for this test"}

        baseline = baselines[test_name][metric_name]
        baseline_value = baseline["value"]
        tolerance = baseline["tolerance"]

        # Calculate acceptable range
        lower_bound = baseline_value * (1 - tolerance)
        upper_bound = baseline_value * (1 + tolerance)

        if lower_bound <= current_value <= upper_bound:
            return {
                "status": "pass",
                "message": "Performance within baseline",
                "baseline": baseline_value,
                "current": current_value,
                "tolerance": tolerance,
            }
        else:
            return {
                "status": "fail",
                "message": f"Performance outside baseline tolerance",
                "baseline": baseline_value,
                "current": current_value,
                "tolerance": tolerance,
                "deviation": (current_value - baseline_value) / baseline_value,
            }


# Global instances
metrics_collector = MetricsCollector()
flaky_handler = FlakyHandler()
baseline_manager = PerformanceBaseline()


def performance_test(baseline_metric: str = "execution_time", tolerance: float = 0.2):
    """Decorator for performance tests with baseline checking."""

    def decorator(test_func):
        def wrapper(*args, **kwargs):
            test_name = f"{test_func.__module__}.{test_func.__name__}"

            start_time = time.time()
            try:
                result = test_func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Check against baseline
                baseline_result = baseline_manager.check_baseline(
                    test_name, baseline_metric, execution_time
                )

                if baseline_result["status"] == "fail":
                    print(f"⚠️  Performance regression detected in {test_name}")
                    print(f"   Baseline: {baseline_result['baseline']:.3f}s")
                    print(f"   Current:  {baseline_result['current']:.3f}s")
                    print(f"   Deviation: {baseline_result['deviation']:.2%}")

                elif baseline_result["status"] == "no_baseline":
                    # Set new baseline
                    baseline_manager.set_baseline(
                        test_name, baseline_metric, execution_time, tolerance
                    )
                    print(
                        f"📊 Set new performance baseline for {test_name}: {execution_time:.3f}s"
                    )

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                raise

        return wrapper

    return decorator
