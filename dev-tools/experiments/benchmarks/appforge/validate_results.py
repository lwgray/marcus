#!/usr/bin/env python3
"""
Validate AppForge benchmark results for submission.

Checks result format, calculates metrics, and ensures data integrity
before leaderboard submission.

Usage:
    python validate_results.py results/marcus_v1.0_appforge_results.json
"""

import json
import sys
from pathlib import Path
from typing import Any


def validate_submission_metadata(data: dict[str, Any]) -> list[str]:
    """
    Validate submission metadata section.

    Parameters
    ----------
    data : dict
        Full results dictionary

    Returns
    -------
    list[str]
        List of validation errors (empty if valid)
    """
    errors = []

    if "submission_metadata" not in data:
        errors.append("Missing 'submission_metadata' section")
        return errors

    metadata = data["submission_metadata"]
    required_fields = [
        "system_name",
        "system_version",
        "submission_date",
        "evaluator",
    ]

    for field in required_fields:
        if field not in metadata:
            errors.append(f"Missing required field: submission_metadata.{field}")

    return errors


def validate_system_configuration(data: dict[str, Any]) -> list[str]:
    """
    Validate system configuration section.

    Parameters
    ----------
    data : dict
        Full results dictionary

    Returns
    -------
    list[str]
        List of validation errors
    """
    errors = []

    if "system_configuration" not in data:
        errors.append("Missing 'system_configuration' section")
        return errors

    config = data["system_configuration"]
    required_fields = ["agent_count", "llm_model", "timeout_per_task_seconds"]

    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: system_configuration.{field}")

    return errors


def validate_task_results(data: dict[str, Any]) -> tuple[list[str], dict]:
    """
    Validate task results and calculate metrics.

    Parameters
    ----------
    data : dict
        Full results dictionary

    Returns
    -------
    tuple[list[str], dict]
        (validation errors, calculated metrics)
    """
    errors = []

    if "task_results" not in data:
        errors.append("Missing 'task_results' section")
        return errors, {}

    results = data["task_results"]

    # Check task count
    if len(results) != 101:
        errors.append(f"Expected 101 tasks, got {len(results)}")

    # Validate each task has required fields
    required_fields = [
        "task_id",
        "compile",
        "test_pass",
        "crash",
        "functional_success",
    ]

    for i, task in enumerate(results):
        for field in required_fields:
            if field not in task:
                errors.append(f"Task {i} missing field: {field}")

    # Calculate metrics
    total = len(results)
    compiled = sum(1 for r in results if r.get("compile", False))
    test_passed = sum(1 for r in results if r.get("test_pass", False))
    crashed = sum(1 for r in results if r.get("crash", False))
    fully_succeeded = sum(1 for r in results if r.get("functional_success", False))

    metrics = {
        "total_tasks": total,
        "compilation_rate": compiled / total if total > 0 else 0,
        "test_pass_rate": test_passed / total if total > 0 else 0,
        "crash_rate": crashed / total if total > 0 else 0,
        "functional_success_rate": fully_succeeded / total if total > 0 else 0,
    }

    return errors, metrics


def validate_aggregate_metrics(
    data: dict[str, Any], calculated_metrics: dict
) -> list[str]:
    """
    Validate that reported metrics match calculated values.

    Parameters
    ----------
    data : dict
        Full results dictionary
    calculated_metrics : dict
        Metrics calculated from task results

    Returns
    -------
    list[str]
        List of validation errors
    """
    errors = []

    if "aggregate_metrics" not in data:
        errors.append("Missing 'aggregate_metrics' section")
        return errors

    reported = data["aggregate_metrics"]

    # Check each metric with 1% tolerance
    tolerance = 0.01
    for metric in [
        "compilation_rate",
        "test_pass_rate",
        "crash_rate",
        "functional_success_rate",
    ]:
        if metric not in reported:
            errors.append(f"Missing aggregate metric: {metric}")
            continue

        reported_val = reported[metric]
        calculated_val = calculated_metrics.get(metric, 0)

        if abs(reported_val - calculated_val) > tolerance:
            errors.append(
                f"Metric mismatch for {metric}: "
                f"reported {reported_val:.3f} != calculated {calculated_val:.3f}"
            )

    return errors


def print_summary(calculated_metrics: dict) -> None:
    """
    Print results summary.

    Parameters
    ----------
    calculated_metrics : dict
        Calculated performance metrics
    """
    print("\n" + "=" * 60)
    print("AppForge Benchmark Results Summary")
    print("=" * 60)
    print(f"Total Tasks: {calculated_metrics['total_tasks']}")
    print(f"Compilation Rate: " f"{calculated_metrics['compilation_rate']:.1%}")
    print(f"Test Pass Rate: " f"{calculated_metrics['test_pass_rate']:.1%}")
    print(f"Crash Rate: " f"{calculated_metrics['crash_rate']:.1%}")
    print(
        f"Functional Success Rate: "
        f"{calculated_metrics['functional_success_rate']:.1%}"
    )
    print("=" * 60)


def validate_results(results_file: Path) -> bool:
    """
    Validate AppForge results JSON file.

    Parameters
    ----------
    results_file : Path
        Path to results JSON file

    Returns
    -------
    bool
        True if validation passed
    """
    if not results_file.exists():
        print(f"❌ File not found: {results_file}")
        return False

    print(f"Validating: {results_file}")
    print()

    try:
        with open(results_file) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False

    all_errors = []

    # Validate each section
    print("[1/4] Validating submission metadata...")
    errors = validate_submission_metadata(data)
    all_errors.extend(errors)
    if errors:
        for error in errors:
            print(f"  ❌ {error}")
    else:
        print("  ✅ Metadata valid")

    print("\n[2/4] Validating system configuration...")
    errors = validate_system_configuration(data)
    all_errors.extend(errors)
    if errors:
        for error in errors:
            print(f"  ❌ {error}")
    else:
        print("  ✅ Configuration valid")

    print("\n[3/4] Validating task results...")
    errors, calculated_metrics = validate_task_results(data)
    all_errors.extend(errors)
    if errors:
        for error in errors:
            print(f"  ❌ {error}")
    else:
        print("  ✅ Task results valid")

    print("\n[4/4] Validating aggregate metrics...")
    errors = validate_aggregate_metrics(data, calculated_metrics)
    all_errors.extend(errors)
    if errors:
        for error in errors:
            print(f"  ❌ {error}")
    else:
        print("  ✅ Aggregate metrics valid")

    # Print summary
    if calculated_metrics:
        print_summary(calculated_metrics)

    # Final verdict
    print()
    if all_errors:
        print(f"❌ Validation FAILED with {len(all_errors)} error(s)")
        print("\nFix the errors above before submission.")
        return False
    else:
        print("✅ Validation PASSED!")
        print("\nResults are ready for submission.")
        return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_results.py <results_file.json>")
        print()
        print("Example:")
        print("  python validate_results.py results/marcus_v1.0_appforge_results.json")
        sys.exit(1)

    results_file = Path(sys.argv[1])
    success = validate_results(results_file)

    sys.exit(0 if success else 1)
